#!/usr/bin/env python3
"""
Email MCP Server

A Model Context Protocol server that provides email functionality for
various email providers including 163.com, Gmail, Outlook, etc.
"""

import os
import json
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
        raise ValueError("MCP_EMAIL_USERNAME environment variable is required")
    if not config.password:
        raise ValueError("MCP_EMAIL_PASSWORD environment variable is required")

    return config


def _format_messages_markdown(messages: list, total_count: int = 0) -> str:
    """
    Format email messages as Markdown.

    Args:
        messages: List of EmailMessage dictionaries
        total_count: Total number of messages matching filter

    Returns:
        Markdown formatted string
    """
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
            # Truncate long content for readability
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
    """
    Format email messages as JSON.

    Args:
        messages: List of EmailMessage dictionaries
        total_count: Total number of messages matching filter

    Returns:
        JSON formatted string
    """
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
        str: Formatted response containing email messages.

        Markdown format (default):
        Human-readable text with headers, preview of content, and attachment list.

        JSON format:
        {
            "total": int,           # Total matching emails
            "count": int,           # Number of emails returned
            "messages": [           # Array of email objects
                {
                    "date": str,    # Formatted date string
                    "subject": str, # Email subject
                    "sender": str,  # Sender address
                    "receiver": str,# Recipient address
                    "content": str, # Email body (optional)
                    "content_type": str, # MIME type
                    "files": [str] # Attachment filenames
                }
            ]
        }

        Error response:
        "Error: <error message with actionable guidance>"

    Examples:
        - List latest 10 unread emails: params with count=10, message_type="UNSEEN"
        - Get 5 recent emails in JSON: params with count=5, response_format="json"
        - Fetch oldest 20 seen emails: params with count=20, message_type="SEEN", latest_first=False

    Error Handling:
        - Authentication errors suggest checking credentials and using app passwords
        - Connection errors provide server/port configuration guidance
        - Invalid parameters are validated by Pydantic model before execution

    Environment Variables Required:
        - MCP_EMAIL_USERNAME: Email account username
        - MCP_EMAIL_PASSWORD: Email password or app-specific password
        - MCP_EMAIL_SERVER: IMAP server (default: imap.163.com)
        - MCP_EMAIL_PORT: IMAP port (default: 993)
    """
    try:
        # Load configuration
        config = _get_email_config()
        client = EmailClient(config)

        # Fetch messages
        messages = client.list_messages(
            count=params.count,
            message_type=params.message_type.value,
            latest_first=params.latest_first
        )

        # Format response
        if params.response_format == ResponseFormat.JSON:
            return _format_messages_json(messages, total_count=len(messages))
        else:
            return _format_messages_markdown(messages, total_count=len(messages))

    except Exception as e:
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
    and HTML content, and can attach multiple files. The email is sent from
    the configured account (via environment variables).

    Args:
        params (SendMessageInput): Validated input parameters containing:
            - to (str): Recipient email address
            - subject (str): Email subject line
            - content (str): Email body content
            - content_type (ContentType): 'plain' or 'html' (default: 'plain')
            - attachments (List[str]): List of file paths to attach (max 10)

    Returns:
        str: Success confirmation or error message.

        Success response:
        "Email sent successfully to <recipient>"

        Error response:
        "Error: <error message with actionable guidance>"

    Examples:
        - Send plain text email: params with to="user@example.com", subject="Hello", content="Hi there"
        - Send HTML email: params with to="user@example.com", subject="Newsletter", content_type="html", content="<h1>Welcome</h1>"
        - Send with attachments: params with to="user@example.com", attachments=["/path/to/file.pdf"]

    Error Handling:
        - Invalid email addresses return validation errors
        - Missing attachment files report the specific file path
        - Authentication errors provide credential configuration guidance
        - Network errors suggest checking server settings and firewall

    Environment Variables Required:
        - MCP_EMAIL_USERNAME: Email account username
        - MCP_EMAIL_PASSWORD: Email password or app-specific password
        - MCP_SMTP_SERVER: SMTP server (default: smtp.163.com)
        - MCP_SMTP_PORT: SMTP port (default: 465)

    Note:
        This tool is NOT idempotent - calling it multiple times will send
        multiple emails with the same content.
    """
    try:
        # Load configuration
        config = _get_email_config()
        client = EmailClient(config)

        # Send message
        success = client.send_message(
            to=params.to,
            subject=params.subject,
            content=params.content,
            content_type=params.content_type.value,
            attachments=params.attachments
        )

        if success:
            return f"Email sent successfully to {params.to}"
        else:
            return "Failed to send email"

    except Exception as e:
        from email_mcp.utils import format_error_message
        return format_error_message(e, "sending email message")


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Email MCP Server - Provides email functionality via MCP protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with stdio transport (default)
  python src/email_mcp/server.py

  # Run with HTTP transport
  python src/email_mcp/server.py --transport streamable-http --port 8000

  # Run with environment variables
  MCP_EMAIL_USERNAME=user@163.com MCP_EMAIL_PASSWORD=auth-code \\
      python src/email_mcp/server.py --transport streamable-http
        """
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport protocol: stdio (default) or streamable-http"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP port for streamable-http transport (default: 8000)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP host for streamable-http transport (default: 127.0.0.1)"
    )

    args = parser.parse_args()

    # Support --help flag
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Email MCP Server")
        print("")
        print("Transport Modes:")
        print("  stdio              - For local MCP clients (default)")
        print("  streamable-http    - For remote/web MCP clients")
        print("")
        print("Environment Variables:")
        print("  MCP_EMAIL_USERNAME  - Email account username (required)")
        print("  MCP_EMAIL_PASSWORD  - Email password or app password (required)")
        print("  MCP_EMAIL_SERVER    - IMAP server (default: imap.163.com)")
        print("  MCP_EMAIL_PORT      - IMAP port (default: 993)")
        print("  MCP_SMTP_SERVER     - SMTP server (default: smtp.163.com)")
        print("  MCP_SMTP_PORT       - SMTP port (default: 465)")
        print("  MCP_SAVE_PATH       - Attachment save path (default: ~/email-attachments)")
        print("")
        print("See STREAMABLE_HTTP_GUIDE.md for detailed deployment options.")
        sys.exit(0)

    # Run server with selected transport
    if args.transport == "streamable-http":
        print(f"Starting Email MCP Server with streamable-http on {args.host}:{args.port}")
        print(f"MCP endpoint: http://{args.host}:{args.port}/mcp")
        mcp.run(transport="streamable-http", port=args.port, host=args.host)
    else:
        print("Starting Email MCP Server with stdio transport")
        mcp.run()
