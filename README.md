# Email MCP Server

A Model Context Protocol (MCP) server that provides email functionality for various email providers including 163.com, Gmail, Outlook, and other IMAP/SMTP compatible services.

## Features

- **List Messages**: Retrieve emails from INBOX with filtering (read/unseen/flagged/etc.)
- **Send Messages**: Send emails with plain text or HTML content
- **Attachments**: Support for downloading and sending email attachments
- **Multiple Formats**: Return data in either Markdown (human-readable) or JSON (machine-readable)
- **Provider Support**: Works with any IMAP/SMTP compatible email service

## Installation

### Requirements

- Python 3.10 or higher
- IMAP and SMTP access enabled on your email account

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

Set the following environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_EMAIL_USERNAME` | Yes | - | Email account username |
| `MCP_EMAIL_PASSWORD` | Yes | - | Email password or app-specific password |
| `MCP_EMAIL_SERVER` | No | `imap.163.com` | IMAP server address |
| `MCP_EMAIL_PORT` | No | `993` | IMAP port |
| `MCP_SMTP_SERVER` | No | `smtp.163.com` | SMTP server address |
| `MCP_SMTP_PORT` | No | `465` | SMTP port |
| `MCP_SAVE_PATH` | No | `~/email-attachments` | Path to save attachments |

### 163.com Setup

For 163.com email accounts:
1. Enable IMAP/SMTP services in your email settings
2. Generate an **authorization code** (not your login password):
   - Go to Settings -> POP3/SMTP/IMAP
   - Enable IMAP/SMTP service
   - Click "Authorization Code" to generate
   - Use this code as `MCP_EMAIL_PASSWORD`

## Usage

### Running the Server

```bash
# Using FastMCP (recommended for development)
fastmcp run src/email_mcp/server.py

# Direct execution
python src/email_mcp/server.py

# With help flag
python src/email_mcp/server.py --help
```

### MCP Client Configuration

#### Using FastMCP (stdio transport)

```json
{
  "mcpServers": {
    "email": {
      "command": "fastmcp",
      "args": ["run", "/path/to/email-mcp/src/email_mcp/server.py"],
      "env": {
        "MCP_EMAIL_USERNAME": "your@email.com",
        "MCP_EMAIL_PASSWORD": "your-password-or-auth-code",
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

#### Using Compiled Binary

After building with PyInstaller (see `dist/mcp_email_service_sdk`):

```json
{
  "mcpServers": {
    "email": {
      "command": "/path/to/email-mcp/dist/email_mcp",
      "args": [],
      "env": {
        "MCP_EMAIL_USERNAME": "your@email.com",
        "MCP_EMAIL_PASSWORD": "your-password-or-auth-code",
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

## Available Tools

### `email_list_messages`

List email messages from INBOX with optional filtering.

**Parameters:**
- `count` (int, default=10): Number of emails to retrieve (1-100)
- `message_type` (enum): Filter by type (ALL, UNSEEN, SEEN, RECENT, ANSWERED, FLAGGED)
- `latest_first` (bool, default=true): Retrieve newest or oldest first
- `response_format` (enum): 'markdown' or 'json' output

**Example:**
```
List latest 10 unread emails in markdown format
```

### `email_send_message`

Send an email message to specified recipients.

**Parameters:**
- `to` (string, required): Recipient email address
- `subject` (string, required): Email subject line
- `content` (string, required): Email body content
- `content_type` (enum): 'plain' or 'html' (default='plain')
- `attachments` (array): List of file paths to attach (max 10)

**Example:**
```
Send email to john@example.com with subject "Meeting Update" and plain text content
```

## Architecture

```
src/email_mcp/
├── __init__.py    # Package initialization
├── server.py      # FastMCP server and tool definitions
├── client.py      # EmailClient for IMAP/SMTP operations
├── models.py      # Pydantic models for validation
└── utils.py       # Utility functions
```

## Development

### Code Quality

```bash
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

## Security Notes

- Never commit email credentials to version control
- Use app-specific passwords when available
- Store credentials in environment variables only
- For 163.com, use authorization codes instead of login passwords

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/email-mcp/issues
- Email: dev@vibe-team.com
