"""
Email MCP Server

A Model Context Protocol (MCP) server that provides email functionality
for various email providers (163.com, Gmail, Outlook, etc.).
"""

__version__ = "1.0.0"
__author__ = "chai lei"
__email__ = "anubiscl@163.com"

# Lazy import to avoid initialization at import time
def get_mcp_server():
    """Get the MCP server instance."""
    from email_mcp.server import mcp
    return mcp

__all__ = ["get_mcp_server", "mcp"]

# For backward compatibility, also export mcp directly
# But this will trigger initialization
from email_mcp.server import mcp  # noqa: E402
