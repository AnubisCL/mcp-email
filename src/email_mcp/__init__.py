"""
Email MCP Server

A Model Context Protocol (MCP) server that provides email functionality
for various email providers (163.com, Gmail, Outlook, etc.).
"""

__version__ = "1.0.0"
__author__ = "Vibe Team"
__email__ = "dev@vibe-team.com"

from email_mcp.server import mcp

__all__ = ["mcp"]
