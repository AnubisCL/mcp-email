"""
Email MCP Server

A Model Context Protocol (MCP) server that provides email functionality
for various email providers (163.com, Gmail, Outlook, etc.).
"""

__version__ = "1.0.0"
__author__ = "chai lei"
__email__ = "anubiscl@163.com"

from email_mcp.server import mcp

__all__ = ["mcp"]
