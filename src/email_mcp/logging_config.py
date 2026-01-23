"""
Logging configuration for Email MCP Server.
"""

import os
import logging
import sys
from typing import Optional


def get_log_level_from_env() -> int:
    """
    Get logging level from environment variable MCP_LOG_LEVEL.

    Returns:
        Logging level (default: INFO)
    """
    level_str = os.getenv('MCP_LOG_LEVEL', 'INFO').upper()
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return level_map.get(level_str, logging.INFO)


def setup_logger(
    name: str = "email_mcp",
    level: Optional[int] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up and configure logger for the Email MCP server.

    Args:
        name: Logger name
        level: Logging level (if None, reads from MCP_LOG_LEVEL env var, default: INFO)
        log_file: Optional file path to write logs to

    Returns:
        Configured logger instance
    """
    if level is None:
        level = get_log_level_from_env()

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler (stderr for MCP stdio mode)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Create default logger instance
logger = setup_logger()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Optional logger name (defaults to "email_mcp")

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"email_mcp.{name}")
    return logger
