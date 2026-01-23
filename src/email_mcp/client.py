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
from email_mcp.logging_config import get_logger

# Initialize logger
logger = get_logger("client")


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
        logger.debug(f"EmailClient initialized with IMAP: {config.imap_server}:{config.imap_port}, "
                    f"SMTP: {config.smtp_server}:{config.smtp_port}")

        # Ensure save path exists
        if self.config.save_path:
            os.makedirs(self.config.save_path, exist_ok=True)
            logger.debug(f"Attachment save path: {self.config.save_path}")

    def _connect_imap(self) -> imaplib.IMAP4_SSL:
        """
        Connect and authenticate to IMAP server.

        Returns:
            Authenticated IMAP4_SSL connection

        Raises:
            Exception: If connection or authentication fails
        """
        logger.debug(f"Connecting to IMAP server {self.config.imap_server}:{self.config.imap_port}")
        try:
            imap_server = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)
            logger.debug("IMAP SSL connection established")

            imap_server.login(self.config.username, self.config.password)
            logger.info(f"IMAP authentication successful for {self.config.username}")

            # Fix for 163.com "Unsafe Login" error
            imaplib.Commands["ID"] = ('AUTH',)
            id_args = (
                "name", self.config.username,
                "contact", self.config.username,
                "version", "1.0.0",
                "vendor", "email-mcp"
            )
            imap_server._simple_command("ID", str(id_args).replace(",", "").replace("'", '"'))
            logger.debug("IMAP ID extension sent")

            return imap_server
        except Exception as e:
            logger.error(f"IMAP connection failed: {type(e).__name__}: {str(e)}")
            raise Exception(format_error_message(e, "IMAP connection"))

    def _connect_smtp(self) -> smtplib.SMTP_SSL:
        """
        Connect and authenticate to SMTP server.

        Returns:
            Authenticated SMTP_SSL connection

        Raises:
            Exception: If connection or authentication fails
        """
        logger.debug(f"Connecting to SMTP server {self.config.smtp_server}:{self.config.smtp_port}")
        try:
            smtp_server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
            logger.debug("SMTP SSL connection established")

            smtp_server.login(self.config.username, self.config.password)
            logger.info(f"SMTP authentication successful for {self.config.username}")

            return smtp_server
        except Exception as e:
            logger.error(f"SMTP connection failed: {type(e).__name__}: {str(e)}")
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
        logger.debug(f"list_messages called: count={count}, type={message_type}, latest_first={latest_first}")
        imap_server = None
        try:
            imap_server = self._connect_imap()

            # Select INBOX
            logger.debug("Selecting INBOX mailbox")
            status, info = imap_server.select(mailbox='INBOX')
            if status != 'OK':
                logger.error(f"Failed to select INBOX: {info}")
                raise Exception(f"Failed to select INBOX: {info}")

            # Search for messages
            logger.debug(f"Searching for messages with filter: {message_type}")
            search_status, items = imap_server.search(None, message_type)
            if search_status != 'OK':
                logger.error(f"Failed to search messages: {items}")
                raise Exception(f"Failed to search messages: {items}")

            message_ids = items[0].split()
            total = len(message_ids)
            logger.info(f"Found {total} messages matching filter '{message_type}'")

            if total == 0:
                logger.info("No messages to retrieve")
                return []

            # Select message range
            if latest_first:
                # Get newest emails
                message_list = message_ids[-count:] if count <= total else message_ids
                logger.debug(f"Retrieving newest {min(count, total)} messages")
            else:
                # Get oldest emails
                message_list = message_ids[:count] if count <= total else message_ids
                logger.debug(f"Retrieving oldest {min(count, total)} messages")

            emails = []
            for i, message_id in enumerate(message_list, 1):
                logger.debug(f"Fetching message {i}/{len(message_list)}: ID {message_id.decode()}")
                fetch_status, data = imap_server.fetch(message_id, "(RFC822)")
                if fetch_status != 'OK':
                    logger.warning(f"Failed to fetch message {message_id}, skipping")
                    continue

                msg = email.message_from_bytes(data[0][1])

                # Extract email data
                subject = decode_header_value(msg["Subject"])
                sender = decode_header_value(msg["From"])
                logger.debug(f"Processing email: '{subject}' from {sender}")

                email_msg = EmailMessage(
                    date=format_date(msg['Date']),
                    subject=subject,
                    sender=sender,
                    receiver=decode_header_value(msg["To"]),
                    **parse_email_message(msg, save_path=self.config.save_path)
                )

                # Log attachments if any
                if email_msg.files:
                    logger.debug(f"Email has {len(email_msg.files)} attachment(s): {email_msg.files}")

                emails.append(email_msg)

            logger.info(f"Successfully retrieved {len(emails)} messages")
            return emails

        except Exception as e:
            logger.error(f"Error in list_messages: {type(e).__name__}: {str(e)}")
            raise Exception(format_error_message(e, "listing messages"))
        finally:
            if imap_server:
                try:
                    imap_server.logout()
                    logger.debug("IMAP connection closed")
                except Exception as e:
                    logger.warning(f"Error closing IMAP connection: {e}")

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

        logger.debug(f"send_message called: to={to}, subject={subject}, "
                    f"attachments={len(attachments)} files")

        smtp_server = None
        try:
            smtp_server = self._connect_smtp()

            # Create message
            logger.debug("Creating email message")
            msg = MIMEMultipart()
            msg['From'] = self.config.username
            msg['To'] = to
            msg['Subject'] = email.header.Header(subject, 'utf-8').encode()

            # Attach body
            content_length = len(content)
            logger.debug(f"Attaching email body ({content_length} bytes, type={content_type})")
            msg.attach(MIMEText(content, content_type, 'utf-8'))

            # Attach files
            if attachments:
                logger.debug(f"Processing {len(attachments)} attachment(s)")
                for i, attachment_path in enumerate(attachments, 1):
                    logger.debug(f"Attaching file {i}/{len(attachments)}: {attachment_path}")
                    if not os.path.exists(attachment_path):
                        logger.error(f"Attachment file not found: {attachment_path}")
                        raise Exception(f"Attachment file not found: {attachment_path}")

                    file_size = os.path.getsize(attachment_path)
                    logger.debug(f"Reading attachment: {os.path.basename(attachment_path)} ({file_size} bytes)")

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
            logger.debug(f"Sending email via SMTP to {to}")
            smtp_server.send_message(msg)
            logger.info(f"Email sent successfully to {to}")
            return True

        except Exception as e:
            logger.error(f"Error in send_message: {type(e).__name__}: {str(e)}")
            raise Exception(format_error_message(e, "sending message"))
        finally:
            if smtp_server:
                try:
                    smtp_server.quit()
                    logger.debug("SMTP connection closed")
                except Exception as e:
                    logger.warning(f"Error closing SMTP connection: {e}")
