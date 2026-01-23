#!/bin/bash
# Email MCP Configuration API Server 启动脚本

cd "$(dirname "$0")"

# 添加 src 到 Python 路径
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

echo "Starting Email MCP Configuration API Server..."
python src/email_mcp/api_server.py
