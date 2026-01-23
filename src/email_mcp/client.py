"""
Email client for IMAP and SMTP operations.
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email.mime.base
import email.encoders
import os
from typing import List, Optional

from email_mcp.models import EmailConfig, EmailMessage
from email_mcp.utils import format_date, decode_header_value, parse_email_message, format_error_message


class EmailClient:
    """
    Email client for IMAP (reading) and SMTP (sending) operations.
    """

    def __init__(self, config: EmailConfig):
        """
        Initialize email client with configuration.

        Args:
            config: EmailConfig object with server settings
        """
        self.config = config
        # Ensure save path exists
        if self.config.save_path:
            os.makedirs(self.config.save_path, exist_ok=True)

    def _connect_imap(self) -> imaplib.IMAP4_SSL:
        """
        Connect and authenticate to IMAP server.

        Returns:
            Authenticated IMAP4_SSL connection

        Raises:
            Exception: If connection or authentication fails
        """
        try:
            imap_server = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)
            imap_server.login(self.config.username, self.config.password)

            # Fix for 163.com "Unsafe Login" error
            imaplib.Commands["ID"] = ('AUTH',)
            id_args = (
                "name", self.config.username,
                "contact", self.config.username,
                "version", "1.0.0",
                "vendor", "email-mcp"
            )
            imap_server._simple_command("ID", str(id_args).replace(",", "").replace("'", '"'))

            return imap_server
        except Exception as e:
            raise Exception(format_error_message(e, "IMAP connection"))

    def _connect_smtp(self) -> smtplib.SMTP_SSL:
        """
        Connect and authenticate to SMTP server.

        Returns:
            Authenticated SMTP_SSL connection

        Raises:
            Exception: If connection or authentication fails
        """
        try:
            smtp_server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
            smtp_server.login(self.config.username, self.config.password)
            return smtp_server
        except Exception as e:
            raise Exception(format_error_message(e, "SMTP connection"))

    def list_messages(
        self,
        count: int = 10,
        message_type: str = "UNSEEN",
        latest_first: bool = True
    ) -> List[EmailMessage]:
        """
        List email messages from INBOX.

        Args:
            count: Number of emails to retrieve (1-100)
            message_type: Filter by type (ALL, UNSEEN, SEEN, etc.)
            latest_first: True for newest first, False for oldest first

        Returns:
            List of EmailMessage objects

        Raises:
            Exception: If retrieval fails
        """
        imap_server = None
        try:
            imap_server = self._connect_imap()

            # Select INBOX
            status, info = imap_server.select(mailbox='INBOX')
            if status != 'OK':
                raise Exception(f"Failed to select INBOX: {info}")

            # Search for messages
            search_status, items = imap_server.search(None, message_type)
            if search_status != 'OK':
                raise Exception(f"Failed to search messages: {items}")

            message_ids = items[0].split()
            total = len(message_ids)

            if total == 0:
                return []

            # Select message range
            if latest_first:
                # Get newest emails
                message_list = message_ids[-count:] if count <= total else message_ids
            else:
                # Get oldest emails
                message_list = message_ids[:count] if count <= total else message_ids

            emails = []
            for message_id in message_list:
                fetch_status, data = imap_server.fetch(message_id, "(RFC822)")
                if fetch_status != 'OK':
                    continue

                msg = email.message_from_bytes(data[0][1])

                # Extract email data
                email_msg = EmailMessage(
                    date=format_date(msg['Date']),
                    subject=decode_header_value(msg["Subject"]),
                    sender=decode_header_value(msg["From"]),
                    receiver=decode_header_value(msg["To"]),
                    **parse_email_message(msg, save_path=self.config.save_path)
                )

                emails.append(email_msg)

            return emails

        except Exception as e:
            raise Exception(format_error_message(e, "listing messages"))
        finally:
            if imap_server:
                try:
                    imap_server.logout()
                except Exception:
                    pass

    def send_message(
        self,
        to: str,
        subject: str,
        content: str,
        content_type: str = 'plain',
        attachments: Optional[List[str]] = None
    ) -> bool:
        """
        Send email message.

        Args:
            to: Recipient email address
            subject: Email subject
            content: Email body content
            content_type: 'plain' or 'html'
            attachments: List of file paths to attach

        Returns:
            True if sent successfully

        Raises:
            Exception: If sending fails
        """
        if attachments is None:
            attachments = []

        smtp_server = None
        try:
            smtp_server = self._connect_smtp()

            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.username
            msg['To'] = to
            msg['Subject'] = email.header.Header(subject, 'utf-8').encode()

            # Attach body
            msg.attach(MIMEText(content, content_type, 'utf-8'))

            # Attach files
            for attachment_path in attachments:
                if not os.path.exists(attachment_path):
                    raise Exception(f"Attachment file not found: {attachment_path}")

                with open(attachment_path, 'rb') as f:
                    part = email.mime.base.MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    email.encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={os.path.basename(attachment_path)}'
                    )
                    msg.attach(part)

            # Send
            smtp_server.send_message(msg)
            return True

        except Exception as e:
            raise Exception(format_error_message(e, "sending message"))
        finally:
            if smtp_server:
                try:
                    smtp_server.quit()
                except Exception:
                    pass
