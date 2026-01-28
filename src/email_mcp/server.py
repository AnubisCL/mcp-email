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
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional

from email_mcp.client import EmailClient
from email_mcp.logging_config import get_logger, get_log_level_from_env
from email_mcp.models import (
    EmailConfig,
    ListMessagesInput,
    SendMessageInput,
    ResponseFormat
)
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Context variable for storing current request's email config
_current_config: ContextVar[Optional[EmailConfig]] = ContextVar("current_config", default=None)

# Context variable for storing current request's API key (set by HTTP middleware, read by MCP middleware)
_current_api_key: ContextVar[Optional[str]] = ContextVar("current_api_key", default=None)


# Initialize logger with log level from env
logger = get_logger("server")


# Starlette HTTP middleware for API key validation (HTTP layer)
class HTTPAPIKeyMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware to extract X-API-Key header and store in app state.

    This middleware runs at the HTTP layer and extracts the API key from the
    request headers, storing it in the app.state for later access by the MCP
    middleware layer.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and extract API key."""
        # Extract API key from headers
        api_key = request.headers.get('X-API-Key')

        # Get the path and method for logging
        path = request.url.path
        method = request.method

        # Log the request with API key (truncated for security)
        if api_key:
            logger.debug(f"{method} {path} - API-Key: {api_key[:8]}...")
        else:
            logger.debug(f"{method} {path} - No API-Key")

        # Store API key in context variable for MCP middleware
        token = _current_api_key.set(api_key)

        try:
            # Continue processing
            response = await call_next(request)
        finally:
            # Clean up context
            _current_api_key.reset(token)

        return response


# API Key middleware to extract X-API-Key header and set email config context
class APIKeyMiddleware(Middleware):
    """Middleware to extract API key from request metadata and set email config context."""

    async def on_request(self, context, call_next):
        """Handle incoming requests - validate API key and set email config context."""
        # Get API key from context variable (set by HTTP middleware)
        api_key = _current_api_key.get()

        # Allow initialize and tools/list methods without API key (for discovery)
        # These methods don't access email configuration
        method = getattr(context, 'method', None)
        if method in ['initialize', 'tools/list', 'resources/list']:
            logger.debug(f"Allowing {method} without API key")
            return await call_next(context)

        if not api_key:
            logger.error(f"Request missing X-API-Key header")
            raise ValueError(
                "Unauthorized: X-API-Key header is required to call email tools. "
                "Please obtain an API key from the configuration UI at http://127.0.0.1:8001/config-ui/index.html"
            )

        logger.debug(f"Request with API key: {api_key[:8]}...")
        config = _get_email_config_from_db(api_key)

        if not config:
            logger.warning(f"Invalid API key: {api_key[:8]}...")
            raise ValueError(
                f"Unauthorized: Invalid API key. "
                f"Please check your API key in the configuration UI."
            )

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
logger.info("✓ API Key middleware configured (API key required for tool calls)")


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
def email_list_messages(
    count: int = 10,
    message_type: str = "ALL",
    latest_first: bool = True,
    response_format: str = "markdown"
) -> str:
    """
    List email messages from INBOX with optional filtering.

    This tool retrieves emails from the configured email account using IMAP protocol.
    It supports filtering by message type (read/unseen/flagged/etc.) and pagination
    control. The tool does NOT modify any emails - it only reads and lists them.

    Args:
        count: Number of emails to retrieve, 1-100 (default: 10)
        message_type: Filter by ALL/UNSEEN/SEEN/RECENT/ANSWERED/FLAGGED (default: ALL)
        latest_first: Retrieve newest first (True) or oldest first (False) (default: True)
        response_format: Output format - 'markdown' or 'json' (default: markdown)

    Returns:
        str: Formatted response containing email messages
    """
    # Create params dict and validate with Pydantic model
    params_dict = {
        "count": count,
        "message_type": message_type,
        "latest_first": latest_first,
        "response_format": response_format
    }

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
def email_send_message(
    to: str,
    subject: str,
    content: str,
    content_type: str = "plain",
    attachments: list = []
) -> str:
    """
    Send an email message to specified recipients.

    This tool sends an email using SMTP protocol. It supports both plain text
    and HTML content, and can attach multiple files.

    Args:
        to: Recipient email address
        subject: Email subject line
        content: Email body content
        content_type: Content type - 'plain' or 'html' (default: 'plain')
        attachments: List of file paths to attach (default: [])

    Returns:
        str: Success confirmation or error message
    """
    # Create params dict and validate with Pydantic model
    params_dict = {
        "to": to,
        "subject": subject,
        "content": content,
        "content_type": content_type,
        "attachments": attachments
    }

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

    # Get the HTTP app instance and mount additional apps
    # Note: http_app() returns a new instance each time, so we cache it
    if not hasattr(mcp, '_cached_http_app'):
        mcp._cached_http_app = mcp.http_app()

        # Add HTTP middleware for API key extraction (HTTP layer)
        mcp._cached_http_app.add_middleware(HTTPAPIKeyMiddleware)
        logger.info("✓ HTTP API Key middleware added")

        # Import and mount FastAPI configuration app
        from email_mcp.api_server import app as fastapi_app, mount_server_management_route
        from starlette.routing import Mount
        from email_mcp.database import init_database, get_session_factory

        # Initialize database for configuration API
        logger.info("✓ Initializing database...")
        engine = init_database()
        session_factory = get_session_factory(engine)

        # Mount FastAPI app at /api path
        # This allows all configuration API endpoints to be accessible under /api
        mcp._cached_http_app.routes.append(
            Mount("/api", app=fastapi_app, name="api")
        )
        logger.info("✓ Configuration API mounted at /api")

        # Mount server-management discovery endpoint
        mount_server_management_route(mcp._cached_http_app, f"http://{args.host}:{args.port}")
        logger.info("✓ Server management discovery endpoint mounted")

        # Mount static files for config UI at /config-ui path
        import os
        from starlette.staticfiles import StaticFiles
        config_ui_path = os.path.join(os.path.dirname(__file__), "../../config-ui")
        if os.path.exists(config_ui_path):
            mcp._cached_http_app.routes.append(
                Mount("/config-ui", app=StaticFiles(directory=config_ui_path), name="config-ui")
            )
            logger.info("✓ Configuration UI mounted at /config-ui")

        # Add root redirect to config UI
        from starlette.responses import RedirectResponse
        from starlette.routing import Route

        async def root_redirect(request):
            return RedirectResponse(url="/config-ui/index.html")

        # Insert root route at the beginning of routes list
        mcp._cached_http_app.routes.insert(0, Route("/", root_redirect))

        # Patch http_app method to return cached instance
        original_http_app = mcp.http_app
        def cached_http_app(**kwargs):
            return mcp._cached_http_app
        mcp.http_app = cached_http_app

    print()
    print("=" * 60)
    print("  Email MCP Server - All-in-One Mode")
    print("=" * 60)
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  MCP Endpoint: http://{args.host}:{args.port}/mcp")
    print(f"  Config API:   http://{args.host}:{args.port}/api")
    print(f"  Config UI:    http://{args.host}:{args.port}/config-ui/index.html")
    print(f"  Log Level: {logging.getLevelName(log_level)}")
    print("=" * 60)
    print()
    print("Press Ctrl+C to stop the server")
    print()

    mcp.run(transport="streamable-http", port=args.port, host=args.host)
