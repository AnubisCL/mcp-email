"""
Utility functions for Email MCP Server.
"""

import os
import email
import email.header
import email.utils
from typing import Dict, Any, List, Optional, Tuple


def format_date(date_str: str) -> str:
    """
    Format email date string to human-readable format.

    Args:
        date_str: Raw date string from email header

    Returns:
        Formatted date string (YYYY-MM-DD HH:MM:SS)
    """
    try:
        date_obj = email.utils.parsedate_to_datetime(date_str)
        return date_obj.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return date_str


def decode_header_value(header_value: str) -> str:
    """
    Decode email header value (subject, from, to, etc.).

    Args:
        header_value: Raw header value from email

    Returns:
        Decoded string
    """
    decoded_parts = email.header.decode_header(header_value)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or 'utf-8')
        else:
            result += part
    return result


def parse_email_message(msg, save_path: str = '') -> Dict[str, Any]:
    """
    Parse email message and extract content, attachments.

    Args:
        msg: Email.message.Message object
        save_path: Path to save attachments

    Returns:
        Dictionary containing:
            - content: Email body text
            - content_type: MIME content type
            - files: List of attachment filenames
    """
    message_content = None
    content_type = None
    files = []

    for part in msg.walk():
        if not part.is_multipart():
            content_type = part.get_content_type()
            filename = part.get_filename()

            # Handle attachments
            if filename:
                decode_header = email.header.decode_header(filename)
                file_name = decode_header[0][0]
                file_encoding = decode_header[0][1]

                if isinstance(file_name, bytes):
                    file_name = file_name.decode(file_encoding or 'utf-8')

                data = part.get_payload(decode=True)

                # Save attachment if path provided
                if file_name and save_path:
                    save_path_dir = save_path
                    os.makedirs(save_path_dir, exist_ok=True)
                    file_path = os.path.join(save_path_dir, file_name)
                    with open(file_path, 'wb') as fp:
                        fp.write(data)
                    files.append(file_name)
            else:
                # Handle email body
                charsets = part.get_charsets()
                if charsets is None or None in charsets:
                    charset = 'utf-8'
                else:
                    charset = charsets[0] or 'utf-8'

                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        message_content = payload.decode(charset)
                except Exception:
                    # Fallback encoding attempts
                    for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1', 'iso-8859-1']:
                        try:
                            if payload:
                                message_content = payload.decode(enc)
                                break
                        except Exception:
                            continue

    return {
        'content': message_content,
        'content_type': content_type,
        'files': files
    }


def format_error_message(error: Exception, context: str = "") -> str:
    """
    Format error message with actionable guidance.

    Args:
        error: The exception that occurred
        context: Additional context about the operation

    Returns:
        Formatted error message string
    """
    error_type = type(error).__name__
    error_msg = str(error)

    # Common error patterns
    if "Authentication" in error_msg or "login" in error_msg.lower():
        return (
            f"Error: Email authentication failed. {error_msg}\n"
            f"Please verify:\n"
            f"  1. Username and password are correct\n"
            f"  2. For 163.com, use an authorization code instead of login password\n"
            f"  3. IMAP/SMTP services are enabled in your email settings"
        )
    elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        return (
            f"Error: Connection timed out. {error_msg}\n"
            f"Please check:\n"
            f"  1. Network connection is stable\n"
            f"  2. Firewall allows IMAP/SMTP connections\n"
            f"  3. Email server address is correct"
        )
    elif "connection" in error_msg.lower():
        return (
            f"Error: Could not connect to email server. {error_msg}\n"
            f"Please verify:\n"
            f"  1. IMAP/SMTP server addresses are correct\n"
            f"  2. Port numbers are correct (IMAP: 993, SMTP: 465 for SSL)\n"
            f"  3. Network allows connections to these servers"
        )
    else:
        return f"Error: {error_type} - {error_msg}"
