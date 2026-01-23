#!/usr/bin/env python3
"""
Email MCP Server - Streamable HTTP Mode

A Model Context Protocol server that provides email functionality for
various email providers including 163.com, Gmail, Outlook, etc.

Environment variables (loaded from .env file):
    MCP_EMAIL_USERNAME: Email account username (required)
    MCP_EMAIL_PASSWORD: Email password or app-specific password (required)
    MCP_EMAIL_SERVER: IMAP server (default: imap.163.com)
    MCP_EMAIL_PORT: IMAP port (default: 993)
    MCP_SMTP_SERVER: SMTP server (default: smtp.163.com)
    MCP_SMTP_PORT: SMTP port (default: 465)
    MCP_SAVE_PATH: Attachment save path (default: ~/email-attachments)
    MCP_LOG_LEVEL: Log level - DEBUG, INFO, WARNING, ERROR (default: INFO)
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

from fastmcp import FastMCP
from pydantic import BaseModel

from email_mcp.models import (
    EmailConfig,
    ListMessagesInput,
    SendMessageInput,
    ResponseFormat
)
from email_mcp.client import EmailClient
from email_mcp.logging_config import get_logger, get_log_level_from_env


def load_env_file():
    """Load .env file from project root if it exists."""
    current_path = Path(__file__).resolve()
    project_root = current_path.parent.parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"✓ Loaded environment from: {env_file}")
        except ImportError:
            print("⚠️  python-dotenv not installed, run: pip install python-dotenv")
        except Exception as e:
            print(f"⚠️  Failed to load .env: {e}")


# Load .env at import time
load_env_file()

# Initialize logger with log level from env
logger = get_logger("server")

# Initialize MCP server
mcp = FastMCP("email_mcp")


def _get_email_config() -> EmailConfig:
    """
    Load email configuration from environment variables.

    Returns:
        EmailConfig object

    Raises:
        ValueError: If required environment variables are missing
    """
    logger.info("Loading email configuration from environment")

    config = EmailConfig(
        protocol=os.getenv('MCP_EMAIL_PROTOCOL', 'imap'),
        imap_server=os.getenv('MCP_EMAIL_SERVER', 'imap.163.com'),
        imap_port=int(os.getenv('MCP_EMAIL_PORT', '993')),
        smtp_server=os.getenv('MCP_SMTP_SERVER', 'smtp.163.com'),
        smtp_port=int(os.getenv('MCP_SMTP_PORT', '465')),
        username=os.getenv('MCP_EMAIL_USERNAME', ''),
        password=os.getenv('MCP_EMAIL_PASSWORD', ''),
        save_path=os.getenv('MCP_SAVE_PATH', os.path.expanduser('~/email-attachments'))
    )

    # Validate required fields
    if not config.username:
        logger.error("MCP_EMAIL_USERNAME not set in .env")
        raise ValueError("MCP_EMAIL_USERNAME environment variable is required")
    if not config.password:
        logger.error("MCP_EMAIL_PASSWORD not set in .env")
        raise ValueError("MCP_EMAIL_PASSWORD environment variable is required")

    logger.info(f"✓ Email configured for: {config.username}")
    logger.debug(f"  IMAP: {config.imap_server}:{config.imap_port}")
    logger.debug(f"  SMTP: {config.smtp_server}:{config.smtp_port}")

    return config


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
def email_list_messages(params: ListMessagesInput) -> str:
    """
    List email messages from INBOX with optional filtering.

    This tool retrieves emails from the configured email account using IMAP protocol.
    It supports filtering by message type (read/unseen/flagged/etc.) and pagination
    control. The tool does NOT modify any emails - it only reads and lists them.

    Args:
        params (ListMessagesInput): Validated input parameters containing:
            - count (int): Number of emails to retrieve, 1-100 (default: 10)
            - message_type (EmailMessageType): Filter by ALL/UNSEEN/SEEN/RECENT/ANSWERED/FLAGGED
            - latest_first (bool): Retrieve newest first (True) or oldest first (False)
            - response_format (ResponseFormat): 'markdown' or 'json' output

    Returns:
        str: Formatted response containing email messages
    """
    logger.info(f"Tool 'email_list_messages' called: count={params.count}, "
                f"type={params.message_type.value}, format={params.response_format.value}")

    try:
        config = _get_email_config()
        client = EmailClient(config)

        logger.debug(f"Fetching {params.count} messages of type '{params.message_type.value}'")
        messages = client.list_messages(
            count=params.count,
            message_type=params.message_type.value,
            latest_first=params.latest_first
        )

        logger.info(f"✓ Retrieved {len(messages)} messages")

        if params.response_format == ResponseFormat.JSON:
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
def email_send_message(params: SendMessageInput) -> str:
    """
    Send an email message to specified recipients.

    This tool sends an email using SMTP protocol. It supports both plain text
    and HTML content, and can attach multiple files.

    Args:
        params (SendMessageInput): Validated input parameters containing:
            - to (str): Recipient email address
            - subject (str): Email subject line
            - content (str): Email body content
            - content_type (ContentType): 'plain' or 'html' (default: 'plain')
            - attachments (List[str]): List of file paths to attach (max 10)

    Returns:
        str: Success confirmation or error message
    """
    content_preview = params.content[:100] + "..." if len(params.content) > 100 else params.content

    logger.info(f"Tool 'email_send_message' called: to={params.to}, "
                f"subject={params.subject}, attachments={len(params.attachments)}")

    try:
        config = _get_email_config()
        client = EmailClient(config)

        logger.debug(f"Sending email to {params.to} via {config.smtp_server}:{config.smtp_port}")
        success = client.send_message(
            to=params.to,
            subject=params.subject,
            content=params.content,
            content_type=params.content_type.value,
            attachments=params.attachments
        )

        if success:
            logger.info(f"✓ Email sent successfully to {params.to}")
            return f"Email sent successfully to {params.to}"
        else:
            logger.warning(f"Email send returned False for {params.to}")
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
