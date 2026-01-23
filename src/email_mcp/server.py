#!/usr/bin/env python3
"""
Email MCP Server - Streamable HTTP Mode

A Model Context Protocol server that provides email functionality for
various email providers including 163.com, Gmail, Outlook, etc.

API Key authentication (REQUIRED):
- Each email configuration has its own unique API key
- Client MUST send X-API-Key header to identify which email config to use
- API keys are generated when creating email configurations via the config API
- Without a valid API key, the server will reject all requests

Configuration API:
- Manage email configurations at http://127.0.0.1:8002/config-ui/index.html
- Each configuration automatically gets a unique API key upon creation
"""

import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Dict, Any, Optional

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware
from pydantic import BaseModel
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from email_mcp.models import (
    EmailConfig,
    ListMessagesInput,
    SendMessageInput,
    ResponseFormat
)
from email_mcp.client import EmailClient
from email_mcp.logging_config import get_logger, get_log_level_from_env

# Context variable for storing current request's email config
_current_config: ContextVar[Optional[EmailConfig]] = ContextVar("current_config", default=None)


# Initialize logger with log level from env
logger = get_logger("server")


# API Key middleware to extract X-API-Key header and set email config context
class APIKeyMiddleware(Middleware):
    """Middleware to extract API key from request metadata and set email config context."""

    async def on_request(self, context, call_next):
        """Handle incoming requests - validate API key and set email config context."""
        # Get API key from request metadata
        api_key = None
        if hasattr(context, 'request') and context.request:
            api_key = context.request.headers.get('X-API-Key')

        if not api_key:
            logger.error("Request missing X-API-Key header")
            # Return error response for MCP requests
            if context.method in ["initialize", "tools/call", "tools/list", "resources/list", "resources/read"]:
                return {
                    "jsonrpc": "2.0",
                    "id": getattr(context, 'request_id', None),
                    "error": {
                        "code": -32600,
                        "message": "Unauthorized: X-API-Key header is required"
                    }
                }
            return await call_next(context)

        logger.debug(f"Request with API key: {api_key[:8]}...")
        config = _get_email_config_from_db(api_key)

        if not config:
            logger.warning(f"Invalid API key: {api_key[:8]}...")
            if context.method in ["initialize", "tools/call", "tools/list", "resources/list", "resources/read"]:
                return {
                    "jsonrpc": "2.0",
                    "id": getattr(context, 'request_id', None),
                    "error": {
                        "code": -32600,
                        "message": "Unauthorized: Invalid API key"
                    }
                }
            return await call_next(context)

        # Set email config context for this request
        token = _current_config.set(config)
        try:
            response = await call_next(context)
        finally:
            _current_config.reset(token)
        return response


# Create MCP middleware instance
api_key_middleware = APIKeyMiddleware()

# Initialize MCP server with middleware (MCP protocol layer)
mcp = FastMCP("email_mcp", middleware=[api_key_middleware])
logger.info("✓ API Key middleware configured (API key required for all requests)")


# HTTP-level middleware for API key validation (runs before MCP layer)
class HTTPAPIKeyMiddleware(BaseHTTPMiddleware):
    """HTTP middleware to validate API key at HTTP layer."""

    async def dispatch(self, request: StarletteRequest, call_next):
        """Validate API key from X-API-Key header."""
        # Only check MCP endpoint
        if not request.url.path.startswith('/mcp'):
            return await call_next(request)

        api_key = request.headers.get('X-API-Key')

        if not api_key:
            logger.error("Request missing X-API-Key header")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "X-API-Key header is required"}
            )

        logger.debug(f"Request with API key: {api_key[:8]}...")
        config = _get_email_config_from_db(api_key)

        if not config:
            logger.warning(f"Invalid API key: {api_key[:8]}...")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "Invalid API key"}
            )

        # Set email config context for this request
        token = _current_config.set(config)
        try:
            response = await call_next(request)
        finally:
            _current_config.reset(token)
        return response


def _get_email_config_from_db(api_key: str) -> Optional[EmailConfig]:
    """
    Load email configuration from database using API key.

    Each email config has its own API key - direct lookup.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        EmailConfig object or None if not found
    """
    try:
        from email_mcp.database import get_session_factory
        from email_mcp.database import EmailConfig as DBEmailConfig

        session_factory = get_session_factory()
        db = session_factory()

        try:
            # Direct lookup: API key belongs to EmailConfig
            db_config = db.query(DBEmailConfig).filter(
                DBEmailConfig.api_key == api_key,
                DBEmailConfig.is_active == True
            ).first()

            if not db_config:
                logger.warning(f"No active email config found for API key: {api_key[:8]}...")
                return None

            # Convert to EmailConfig model
            config = EmailConfig(
                protocol="imap",
                imap_server=db_config.imap_server,
                imap_port=db_config.imap_port,
                smtp_server=db_config.smtp_server,
                smtp_port=db_config.smtp_port,
                username=db_config.username,
                password=db_config.password,
                save_path=os.path.expanduser('~/email-attachments')
            )

            logger.info(f"✓ Email configured from DB for: {config.username}")
            logger.debug(f"  IMAP: {config.imap_server}:{config.imap_port}")
            logger.debug(f"  SMTP: {config.smtp_server}:{config.smtp_port}")

            return config
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error loading config from database: {type(e).__name__}: {e}")
        return None


def _get_current_email_config() -> EmailConfig:
    """
    Get current request's email configuration from context.

    The context is set by APIKeyMiddleware from X-API-Key header.

    Returns:
        EmailConfig object

    Raises:
        ValueError: If no configuration is available (should not happen if middleware works)
    """
    config = _current_config.get()
    if config:
        return config

    # This should not happen if middleware is working correctly
    logger.error("No email config found in context - API key middleware should have caught this")
    raise ValueError(
        "No email configuration available. "
        "Make sure you are sending X-API-Key header with a valid API key."
    )


@contextmanager
def set_email_config_context(api_key: Optional[str]):
    """
    Context manager to set email config from API key.

    Args:
        api_key: API key from request header
    """
    if api_key:
        config = _get_email_config_from_db(api_key)
        token = _current_config.set(config) if config else None
        try:
            yield
        finally:
            if token:
                _current_config.reset(token)
    else:
        yield


def _get_email_config() -> EmailConfig:
    """Get email configuration - alias for _get_current_email_config for backward compatibility."""
    return _get_current_email_config()


def _format_messages_markdown(messages: list, total_count: int = 0) -> str:
    """Format email messages as Markdown."""
    if not messages:
        return "No emails found matching the specified criteria."

    lines = ["# Email Messages", ""]
    lines.append(f"Found {total_count} emails (showing {len(messages)})")
    lines.append("")

    for i, msg in enumerate(messages, 1):
        lines.append(f"## Email {i}")
        lines.append(f"**Date**: {msg.date}")
        lines.append(f"**From**: {msg.sender}")
        lines.append(f"**To**: {msg.receiver}")
        lines.append(f"**Subject**: {msg.subject}")
        lines.append("")

        if msg.content:
            content_preview = msg.content[:500]
            if len(msg.content) > 500:
                content_preview += "..."
            lines.append(f"**Content Preview**:\n{content_preview}")
            lines.append("")

        if msg.files:
            lines.append(f"**Attachments**: {', '.join(msg.files)}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _format_messages_json(messages: list, total_count: int = 0) -> str:
    """Format email messages as JSON."""
    import json
    response = {
        "total": total_count,
        "count": len(messages),
        "messages": [msg.model_dump() for msg in messages]
    }
    return json.dumps(response, indent=2, ensure_ascii=False)


@mcp.tool(
    name="email_list_messages",
    annotations={
        "title": "List Email Messages",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
def email_list_messages(params: dict | str | ListMessagesInput) -> str:
    """
    List email messages from INBOX with optional filtering.

    This tool retrieves emails from the configured email account using IMAP protocol.
    It supports filtering by message type (read/unseen/flagged/etc.) and pagination
    control. The tool does NOT modify any emails - it only reads and lists them.

    Args:
        params: Validated input parameters containing:
            - count (int): Number of emails to retrieve, 1-100 (default: 10)
            - message_type (EmailMessageType): Filter by ALL/UNSEEN/SEEN/RECENT/ANSWERED/FLAGGED
            - latest_first (bool): Retrieve newest first (True) or oldest first (False)
            - response_format (ResponseFormat): 'markdown' or 'json' output

    Returns:
        str: Formatted response containing email messages
    """
    import json

    # Handle both string and dict inputs
    if isinstance(params, str):
        logger.debug("Parsing arguments from JSON string")
        params_dict = json.loads(params)
    elif isinstance(params, dict):
        params_dict = params
    else:
        params_dict = params.model_dump()

    # Validate with Pydantic model
    validated_params = ListMessagesInput(**params_dict)

    logger.info(f"Tool 'email_list_messages' called: count={validated_params.count}, "
                f"type={validated_params.message_type.value}, format={validated_params.response_format.value}")

    try:
        config = _get_email_config()
        client = EmailClient(config)

        logger.debug(f"Fetching {validated_params.count} messages of type '{validated_params.message_type.value}'")
        messages = client.list_messages(
            count=validated_params.count,
            message_type=validated_params.message_type.value,
            latest_first=validated_params.latest_first
        )

        logger.info(f"✓ Retrieved {len(messages)} messages")

        if validated_params.response_format == ResponseFormat.JSON:
            return _format_messages_json(messages, total_count=len(messages))
        else:
            return _format_messages_markdown(messages, total_count=len(messages))

    except Exception as e:
        logger.error(f"Error in email_list_messages: {type(e).__name__}: {str(e)}")
        from email_mcp.utils import format_error_message
        return format_error_message(e, "listing email messages")


@mcp.tool(
    name="email_send_message",
    annotations={
        "title": "Send Email Message",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
def email_send_message(params: dict | str | SendMessageInput) -> str:
    """
    Send an email message to specified recipients.

    This tool sends an email using SMTP protocol. It supports both plain text
    and HTML content, and can attach multiple files.

    Args:
        params: Validated input parameters containing:
            - to (str): Recipient email address
            - subject (str): Email subject line
            - content (str): Email body content
            - content_type (ContentType): 'plain' or 'html' (default: 'plain')
            - attachments (List[str]): List of file paths to attach (max 10)

    Returns:
        str: Success confirmation or error message
    """
    import json

    # Handle both string and dict inputs
    if isinstance(params, str):
        logger.debug("Parsing arguments from JSON string")
        params_dict = json.loads(params)
    elif isinstance(params, dict):
        params_dict = params
    else:
        params_dict = params.model_dump()

    # Validate with Pydantic model
    validated_params = SendMessageInput(**params_dict)

    content_preview = validated_params.content[:100] + "..." if len(validated_params.content) > 100 else validated_params.content

    logger.info(f"Tool 'email_send_message' called: to={validated_params.to}, "
                f"subject={validated_params.subject}, attachments={len(validated_params.attachments)}")

    try:
        config = _get_email_config()
        client = EmailClient(config)

        logger.debug(f"Sending email to {validated_params.to} via {config.smtp_server}:{config.smtp_port}")
        success = client.send_message(
            to=validated_params.to,
            subject=validated_params.subject,
            content=validated_params.content,
            content_type=validated_params.content_type.value,
            attachments=validated_params.attachments
        )

        if success:
            logger.info(f"✓ Email sent successfully to {validated_params.to}")
            return f"Email sent successfully to {validated_params.to}"
        else:
            logger.warning(f"Email send returned False for {validated_params.to}")
            return "Failed to send email"

    except Exception as e:
        logger.error(f"Error in email_send_message: {type(e).__name__}: {str(e)}")
        from email_mcp.utils import format_error_message
        return format_error_message(e, "sending email message")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Email MCP Server - Streamable HTTP Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv('MCP_PORT', '8001')),
        help="HTTP port (default: 8001 or from MCP_PORT env var)"
    )
    parser.add_argument(
        "--host",
        default=os.getenv('MCP_HOST', '127.0.0.1'),
        help="HTTP host (default: 127.0.0.1 or from MCP_HOST env var)"
    )

    args = parser.parse_args()

    # Set log level from environment
    import logging
    log_level = get_log_level_from_env()
    logger.setLevel(log_level)
    for handler in logger.handlers:
        handler.setLevel(log_level)

    # Get the HTTP app instance and add middleware
    # Note: http_app() returns a new instance each time, so we cache it
    if not hasattr(mcp, '_cached_http_app'):
        mcp._cached_http_app = mcp.http_app()
        mcp._cached_http_app.add_middleware(HTTPAPIKeyMiddleware)
        logger.info("✓ HTTP API Key middleware added to Starlette app")

        # Patch http_app method to return cached instance
        original_http_app = mcp.http_app
        def cached_http_app(**kwargs):
            return mcp._cached_http_app
        mcp.http_app = cached_http_app

    print()
    print("=" * 60)
    print("  Email MCP Server - Streamable HTTP Mode")
    print("=" * 60)
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Endpoint: http://{args.host}:{args.port}/mcp")
    print(f"  Log Level: {logging.getLevelName(log_level)}")
    print("=" * 60)
    print()
    print("Press Ctrl+C to stop the server")
    print()

    mcp.run(transport="streamable-http", port=args.port, host=args.host)
