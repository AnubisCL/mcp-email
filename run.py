#!/usr/bin/env python3
"""
Entry point script for Email MCP Server.
Run this directly to start the MCP server.
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    from email_mcp.server import mcp
    mcp.run()
