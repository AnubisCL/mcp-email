"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ProviderType(str, Enum):
    """Supported email providers."""
    CUSTOM = "custom"
    NETEASE_163 = "163"
    NETEASE_126 = "126"
    NETEASE_YEAH = "yeah"
    QQ = "qq"
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    ICLOUD = "icloud"
    ALIYUN = "aliyun"


class ProviderConfig(BaseModel):
    """Predefined provider configurations."""
    name: str
    imap_server: str
    imap_port: int
    smtp_server: str
    smtp_port: int


# Predefined provider configurations
PROVIDER_CONFIGS = {
    ProviderType.NETEASE_163: ProviderConfig(
        name="163网易邮箱",
        imap_server="imap.163.com",
        imap_port=993,
        smtp_server="smtp.163.com",
        smtp_port=465
    ),
    ProviderType.NETEASE_126: ProviderConfig(
        name="126网易邮箱",
        imap_server="imap.126.com",
        imap_port=993,
        smtp_server="smtp.126.com",
        smtp_port=465
    ),
    ProviderType.NETEASE_YEAH: ProviderConfig(
        name="Yeah网易邮箱",
        imap_server="imap.yeah.net",
        imap_port=993,
        smtp_server="smtp.yeah.net",
        smtp_port=465
    ),
    ProviderType.QQ: ProviderConfig(
        name="QQ邮箱",
        imap_server="imap.qq.com",
        imap_port=993,
        smtp_server="smtp.qq.com",
        smtp_port=465
    ),
    ProviderType.GMAIL: ProviderConfig(
        name="Gmail",
        imap_server="imap.gmail.com",
        imap_port=993,
        smtp_server="smtp.gmail.com",
        smtp_port=465
    ),
    ProviderType.OUTLOOK: ProviderConfig(
        name="Outlook",
        imap_server="outlook.office365.com",
        imap_port=993,
        smtp_server="smtp-mail.outlook.com",
        smtp_port=587
    ),
    ProviderType.ICLOUD: ProviderConfig(
        name="iCloud",
        imap_server="imap.mail.me.com",
        imap_port=993,
        smtp_server="smtp.mail.me.com",
        smtp_port=587
    ),
    ProviderType.ALIYUN: ProviderConfig(
        name="阿里云邮箱",
        imap_server="imap.aliyun.com",
        imap_port=993,
        smtp_server="smtp.aliyun.com",
        smtp_port=465
    ),
}


# Request schemas
class RegisterRequest(BaseModel):
    """Request to register a new user."""
    pass  # Just generates an API key


class CreateEmailConfigRequest(BaseModel):
    """Request to create email configuration."""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    provider: ProviderType = Field(..., description="Email provider")
    username: str = Field(..., min_length=1, max_length=255, description="Email username")
    password: str = Field(..., min_length=1, max_length=255, description="Email password or auth code")
    imap_server: Optional[str] = Field(None, description="Custom IMAP server (for custom provider)")
    imap_port: Optional[int] = Field(None, ge=1, le=65535, description="Custom IMAP port")
    smtp_server: Optional[str] = Field(None, description="Custom SMTP server (for custom provider)")
    smtp_port: Optional[int] = Field(None, ge=1, le=65535, description="Custom SMTP port")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()


class UpdateEmailConfigRequest(BaseModel):
    """Request to update email configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=1, max_length=255)
    imap_server: Optional[str] = Field(None, max_length=255)
    imap_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_server: Optional[str] = Field(None, max_length=255)
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    is_active: Optional[bool] = None


# Response schemas
class UserResponse(BaseModel):
    """User response."""
    api_key: str
    created_at: datetime
    is_active: bool


class EmailConfigResponse(BaseModel):
    """Email configuration response."""
    id: int
    api_key: str
    name: str
    provider: str
    imap_server: str
    imap_port: int
    username: str
    smtp_server: str
    smtp_port: int
    is_active: bool
    last_tested: Optional[datetime] = None
    last_test_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TestConnectionResponse(BaseModel):
    """Test connection response."""
    status: str  # success, failed
    message: str
    imap_test: dict
    smtp_test: dict


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
