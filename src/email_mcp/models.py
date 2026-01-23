"""
Pydantic models for Email MCP Server input validation and data structures.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class EmailMessageType(str, Enum):
    """Email message types for filtering."""
    ALL = "ALL"
    UNSEEN = "UNSEEN"
    SEEN = "SEEN"
    RECENT = "RECENT"
    ANSWERED = "ANSWERED"
    FLAGGED = "FLAGGED"


class ContentType(str, Enum):
    """Email content type."""
    PLAIN = "plain"
    HTML = "html"


class EmailMessage(BaseModel):
    """Email message model."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    date: str = Field(..., description="Email date in formatted string")
    subject: str = Field(..., description="Email subject")
    sender: str = Field(..., description="Sender email address")
    receiver: str = Field(..., description="Receiver email address")
    content: Optional[str] = Field(default=None, description="Email body content")
    content_type: Optional[str] = Field(default=None, description="MIME content type")
    files: List[str] = Field(default_factory=list, description="List of attachment filenames")


class EmailConfig(BaseModel):
    """Email server configuration."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    protocol: str = Field(default="imap", description="Email protocol (imap)")
    imap_server: str = Field(..., description="IMAP server address")
    imap_port: int = Field(default=993, description="IMAP port", ge=1, le=65535)
    smtp_server: str = Field(..., description="SMTP server address")
    smtp_port: int = Field(default=465, description="SMTP port", ge=1, le=65535)
    username: str = Field(..., description="Email username")
    password: str = Field(..., description="Email password or app-specific password")
    save_path: str = Field(..., description="Path to save attachments")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Password cannot be empty")
        return v


class ListMessagesInput(BaseModel):
    """Input model for listing email messages."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    count: int = Field(
        default=10,
        description="Number of emails to retrieve",
        ge=1,
        le=100
    )
    message_type: EmailMessageType = Field(
        default=EmailMessageType.UNSEEN,
        description="Filter emails by type: ALL, UNSEEN, SEEN, RECENT, ANSWERED, FLAGGED"
    )
    latest_first: bool = Field(
        default=True,
        description="Retrieve newest emails first (True) or oldest first (False)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

    @field_validator('count')
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Count must be at least 1")
        if v > 100:
            raise ValueError("Count cannot exceed 100")
        return v


class SendMessageInput(BaseModel):
    """Input model for sending email messages."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    to: str = Field(..., description="Recipient email address", min_length=1, max_length=200)
    subject: str = Field(..., description="Email subject", min_length=1, max_length=500)
    content: str = Field(..., description="Email body content", min_length=1)
    content_type: ContentType = Field(
        default=ContentType.PLAIN,
        description="Content type: 'plain' for text or 'html' for HTML content"
    )
    attachments: List[str] = Field(
        default_factory=list,
        description="List of file paths to attach (max 10)"
    )

    @field_validator('to')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        v = v.strip()
        if '@' not in v:
            raise ValueError("Invalid email address format")
        return v

    @field_validator('subject')
    @classmethod
    def validate_subject(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Subject cannot be empty")
        return v.strip()

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()

    @field_validator('attachments')
    @classmethod
    def validate_attachments(cls, v: List[str]) -> List[str]:
        if len(v) > 10:
            raise ValueError("Cannot attach more than 10 files")
        return v
