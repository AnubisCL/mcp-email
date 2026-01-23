"""
FastAPI configuration management server for Email MCP Server.
Provides REST API for user authentication and email configuration management.
"""
import secrets
import os
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from email_mcp.database import (
    Base, EmailConfig, init_database, get_session_factory, get_database_url
)
from email_mcp.schemas import (
    RegisterRequest, CreateEmailConfigRequest, UpdateEmailConfigRequest,
    UserResponse, EmailConfigResponse, TestConnectionResponse, ErrorResponse,
    ProviderType, PROVIDER_CONFIGS
)
from email_mcp.connectivity import test_email_connection


# Global session factory
_session_factory = None


def get_db():
    """Get database session."""
    global _session_factory
    if _session_factory is None:
        engine = init_database()
        _session_factory = get_session_factory(engine)
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()


def verify_api_key(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> EmailConfig:
    """Verify API key and return email config."""
    config = db.query(EmailConfig).filter(
        EmailConfig.api_key == x_api_key,
        EmailConfig.is_active == True
    ).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    return config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager."""
    # Initialize database on startup
    engine = init_database()
    global _session_factory
    _session_factory = get_session_factory(engine)
    yield
    # Cleanup on shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="Email MCP Configuration API",
    description="Configuration management API for Email MCP Server",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "email-mcp-config"}


# Root endpoint - redirect to config UI
@app.get("/")
async def root():
    """Root endpoint - redirect to configuration UI."""
    return RedirectResponse(url="/config-ui/index.html")


# Mount static files for configuration UI
# Get the absolute path to config-ui directory
_config_ui_path = os.path.join(os.path.dirname(__file__), "../../config-ui")
if os.path.exists(_config_ui_path):
    app.mount("/config-ui", StaticFiles(directory=_config_ui_path), name="config-ui")


# Email configuration endpoints
@app.get("/api/config", response_model=List[EmailConfigResponse], tags=["Email Configuration"])
async def get_email_configs(db: Session = Depends(get_db)):
    """Get all email configurations."""
    configs = db.query(EmailConfig).order_by(EmailConfig.created_at.desc()).all()
    return configs


@app.post("/api/config", response_model=EmailConfigResponse, status_code=status.HTTP_201_CREATED, tags=["Email Configuration"])
async def create_email_config(
    config: CreateEmailConfigRequest,
    db: Session = Depends(get_db)
):
    """Create a new email configuration with unique API key."""
    # Generate unique API key for this config
    api_key = secrets.token_urlsafe(32)
    existing = db.query(EmailConfig).filter(EmailConfig.api_key == api_key).first()
    while existing:
        api_key = secrets.token_urlsafe(32)
        existing = db.query(EmailConfig).filter(EmailConfig.api_key == api_key).first()

    # Get provider defaults if not custom
    provider_config = PROVIDER_CONFIGS.get(config.provider)

    if config.provider == ProviderType.CUSTOM:
        # Validate custom provider has required fields
        if not all([config.imap_server, config.smtp_server]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom provider requires imap_server and smtp_server"
            )
        imap_server = config.imap_server
        imap_port = config.imap_port or 993
        smtp_server = config.smtp_server
        smtp_port = config.smtp_port or 465
        provider_name = "Custom"
    else:
        # Use predefined provider config
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider: {config.provider}"
            )
        imap_server = provider_config.imap_server
        imap_port = provider_config.imap_port
        smtp_server = provider_config.smtp_server
        smtp_port = provider_config.smtp_port
        provider_name = provider_config.name

    # Create configuration with API key
    email_config = EmailConfig(
        api_key=api_key,
        name=config.name,
        provider=config.provider.value,
        imap_server=imap_server,
        imap_port=imap_port,
        username=config.username,
        password=config.password,
        smtp_server=smtp_server,
        smtp_port=smtp_port
    )

    db.add(email_config)
    db.commit()
    db.refresh(email_config)

    return email_config


@app.put("/api/config/{config_id}", response_model=EmailConfigResponse, tags=["Email Configuration"])
async def update_email_config(
    config_id: int,
    config_update: UpdateEmailConfigRequest,
    current_config: EmailConfig = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Update an email configuration (only config owner can update)."""
    # Verify the API key matches the config being updated
    if current_config.id != config_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not match this configuration"
        )

    # Update fields
    update_data = config_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_config, field, value)

    current_config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_config)

    return current_config


@app.delete("/api/config/{config_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Email Configuration"])
async def delete_email_config(
    config_id: int,
    current_config: EmailConfig = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Delete an email configuration (only config owner can delete)."""
    # Verify the API key matches the config being deleted
    if current_config.id != config_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not match this configuration"
        )

    db.delete(current_config)
    db.commit()


@app.post("/api/config/{config_id}/test", response_model=TestConnectionResponse, tags=["Email Configuration"])
async def test_connection(
    config_id: int,
    current_config: EmailConfig = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Test email configuration connectivity (only config owner can test)."""
    # Verify the API key matches the config being tested
    if current_config.id != config_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not match this configuration"
        )

    # Test connection
    result = test_email_connection(
        imap_server=current_config.imap_server,
        imap_port=current_config.imap_port,
        smtp_server=current_config.smtp_server,
        smtp_port=current_config.smtp_port,
        username=current_config.username,
        password=current_config.password
    )

    # Update last test status
    current_config.last_tested = datetime.utcnow()
    current_config.last_test_status = result["status"]
    db.commit()

    return TestConnectionResponse(**result)


# Provider info endpoint
@app.get("/api/providers", tags=["Info"])
async def get_providers():
    """Get list of supported email providers."""
    return {
        "providers": [
            {
                "id": provider.value,
                "name": config.name,
                "imap_server": config.imap_server,
                "imap_port": config.imap_port,
                "smtp_server": config.smtp_server,
                "smtp_port": config.smtp_port
            }
            for provider, config in PROVIDER_CONFIGS.items()
        ]
    }


# Server management discovery endpoint
@app.get("/.well-known/mcp/server-management.json", tags=["Discovery"])
async def server_management_discovery():
    """Server management discovery endpoint."""
    import os

    # Get server URL from environment or use default
    server_host = os.getenv("MCP_HOST", "127.0.0.1")
    server_port = os.getenv("MCP_PORT", "8001")
    base_url = f"http://{server_host}:{server_port}"

    return {
        "metadata": {
            "mcpId": "mcp-server-email",
            "name": "Email MCP Server",
            "description": "Multi-user email service with support for 163, Gmail, Outlook, QQ, and custom IMAP/SMTP servers",
            "version": "1.0.0"
        },
        "contact": {
            "author": "Vibe Team",
            "email": "dev@vibe-team.com",
            "documentation": "https://docs.vibe-team.com/mcp/email"
        },
        "managementEndpoints": [
            {
                "id": "config-manager",
                "name": "Email Configuration Manager",
                "description": "Configure email accounts and API keys",
                "type": "iframe",
                "endpoint": f"{base_url}/config-ui/index.html"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv

    # Load .env file
    load_dotenv()

    # Get config
    host = os.getenv("CONFIG_API_HOST", "127.0.0.1")
    port = int(os.getenv("CONFIG_API_PORT", "8002"))

    print(f"Starting Email MCP Configuration API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
