# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Email MCP (Model Context Protocol) server that provides email functionality for various email providers including 163.com, Gmail, Outlook, and other IMAP/SMTP compatible services. The server follows MCP best practices with proper naming conventions, tool annotations, and error handling.

## Architecture

The project uses a modular structure with clear separation of concerns:

### Directory Structure

```
src/email_mcp/
├── __init__.py    # Package initialization, exports mcp server
├── server.py      # FastMCP server with tool definitions
├── client.py      # EmailClient for IMAP/SMTP operations
├── models.py      # Pydantic models for input validation
└── utils.py       # Utility functions (formatting, error handling)
```

### Key Components

**`server.py`** - MCP Server and Tools
- Defines two MCP tools: `email_list_messages` and `email_send_message`
- Loads configuration from environment variables
- Handles response formatting (Markdown/JSON)
- Tool annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`

**`client.py`** - EmailClient Class
- `_connect_imap()`: IMAP connection with 163.com ID extension support
- `_connect_smtp()`: SMTP connection
- `list_messages()`: Retrieve emails from INBOX
- `send_message()`: Send email with attachments

**`models.py`** - Pydantic Models
- `EmailConfig`: Server configuration with validation
- `ListMessagesInput`: Parameters for listing emails
- `SendMessageInput`: Parameters for sending emails
- `EmailMessage`: Email data model
- Enums: `ResponseFormat`, `EmailMessageType`, `ContentType`

**`utils.py`** - Utility Functions
- `format_date()`: Format email date strings
- `decode_header_value()`: Decode MIME headers
- `parse_email_message()`: Extract content and attachments
- `format_error_message()`: Actionable error formatting

### MCP Tools

| Tool | Description | Read-only | Idempotent |
|------|-------------|-----------|------------|
| `email_list_messages` | List emails from INBOX with filtering | Yes | Yes |
| `email_send_message` | Send email to recipients | No | No |

## Configuration

Configuration is via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_EMAIL_USERNAME` | Yes | - | Email account username |
| `MCP_EMAIL_PASSWORD` | Yes | - | Email password or **authorization code** |
| `MCP_EMAIL_SERVER` | No | `imap.163.com` | IMAP server |
| `MCP_EMAIL_PORT` | No | `993` | IMAP port (SSL) |
| `MCP_SMTP_SERVER` | No | `smtp.163.com` | SMTP server |
| `MCP_SMTP_PORT` | No | `465` | SMTP port (SSL) |
| `MCP_SAVE_PATH` | No | `~/email-attachments` | Attachment save directory |

### Important: 163.com Authorization

For 163.com accounts, use an **authorization code** (not login password):
1. Enable IMAP/SMTP in email settings
2. Generate authorization code in POP3/SMTP/IMAP settings
3. Use the code as `MCP_EMAIL_PASSWORD`

## MCP Client Configuration

Example for Claude Desktop or other MCP clients:

```json
{
  "mcpServers": {
    "email": {
      "command": "fastmcp",
      "args": ["run", "src/email_mcp/server.py"],
      "env": {
        "MCP_EMAIL_USERNAME": "your@email.com",
        "MCP_EMAIL_PASSWORD": "authorization-code",
        "MCP_EMAIL_SERVER": "imap.163.com",
        "MCP_EMAIL_PORT": "993",
        "MCP_SMTP_SERVER": "smtp.163.com",
        "MCP_SMTP_PORT": "465",
        "MCP_SAVE_PATH": "/path/to/attachments"
      }
    }
  }
}
```

## Development Commands

### Running the Server

```bash
# Via FastMCP (recommended)
fastmcp run src/email_mcp/server.py

# Direct execution
python src/email_mcp/server.py --help
```

### Code Quality

```bash
# Install dev dependencies
pip install -r requirements.txt

# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/
```

### Testing

```bash
# Run tests
pytest

# Test with MCP Inspector
npx @modelcontextprotocol/inspector src/email_mcp/server.py
```

## MCP Best Practices Followed

- **Server Naming**: `email_mcp` (Python convention: `{service}_mcp`)
- **Tool Naming**: `email_list_messages`, `email_send_message` (snake_case with prefix)
- **Pydantic v2**: Uses `model_config` instead of nested `Config` class
- **Tool Annotations**: All tools have proper hints set
- **Error Handling**: Actionable error messages with specific guidance
- **Response Formats**: Supports both Markdown and JSON outputs
- **Type Safety**: Full type hints throughout
- **Docstrings**: Comprehensive documentation with schema structures

## Management Discovery

The server includes a `.well-known/mcp/server-management.json` file for MCP client auto-discovery, following the management endpoint specification.

## Dependencies

- `fastmcp` - MCP server framework
- `pydantic` - Data validation (v2+)
- Python standard library: `imaplib`, `smtplib`, `email`

## Common Issues

| Issue | Solution |
|-------|----------|
| Authentication failed | Use authorization code, not login password (163.com) |
| Connection timeout | Check firewall allows IMAP/SMTP ports |
| "Unsafe Login" error | Fixed by IMAP ID extension in `client.py:82-85` |
| Missing attachments | Verify `MCP_SAVE_PATH` directory exists and is writable |
