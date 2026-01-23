"""
Database models for Email MCP Server multi-user configuration management.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey,
    create_engine, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class EmailConfig(Base):
    """Email configuration model with per-config API key."""
    __tablename__ = "email_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key = Column(String(64), unique=True, nullable=False, index=True)  # Unique API key for this config
    name = Column(String(100), nullable=False)  # User-defined name for this config
    provider = Column(String(50), nullable=False)  # 163, gmail, outlook, qq, custom

    # IMAP configuration
    imap_server = Column(String(255), nullable=False)
    imap_port = Column(Integer, default=993, nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)  # Encrypted in production

    # SMTP configuration
    smtp_server = Column(String(255), nullable=False)
    smtp_port = Column(Integer, default=465, nullable=False)

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    last_tested = Column(DateTime, nullable=True)
    last_test_status = Column(String(20), nullable=True)  # success, failed, pending
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database engine and session
def get_database_url(db_path: str = None) -> str:
    """Get database URL."""
    if db_path is None:
        import os
        db_path = os.path.join(os.path.dirname(__file__), "../../../data/email_mcp.db")
    # Add check_same_thread=False for SQLite to work with FastAPI's async threads
    return f"sqlite:///{db_path}?check_same_thread=False"


def init_database(db_path: str = None):
    """Initialize database and create tables."""
    import os
    if db_path is None:
        db_dir = os.path.join(os.path.dirname(__file__), "../../data")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "email_mcp.db")

    engine = create_engine(get_database_url(db_path), echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def get_session_factory(engine=None):
    """Get session factory with scoped session for thread safety."""
    if engine is None:
        engine = init_database()
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)
