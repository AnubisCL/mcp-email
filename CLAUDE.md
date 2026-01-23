# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that provides email functionality for 163.com email accounts. It allows reading and sending emails through the MCP protocol using the FastMCP framework.

## Architecture

The project consists of a single-file MCP server (`mcp_email_service_sdk.py`) that:

1. **EmailService Class** - Core business logic for email operations:
   - `login_imap()` - Connects to IMAP server with 163.com-specific ID extension handling to prevent "Unsafe Login" errors
   - `login_smtp()` - Connects to SMTP server
   - `read_emails()` - Fetches emails from INBOX with filtering (All/Unseen/Seen/Recent/Answered/Flagged)
   - `send_email()` - Sends emails with optional attachments

2. **MCP Tools** - Two FastMCP-decorated tools exposed to MCP clients:
   - `read_emails` - Parameters: count, type, latest (reads newest or oldest emails)
   - `send_email` - Parameters: to, subject, content, content_type, attachments

3. **Configuration** - Environment variable based config via `EmailConfig` model (see MCP Config Files section below)

### Key Implementation Details

- **163.com ID Extension**: Lines 83-85 implement the IMAP ID extension to prevent 163.com "Unsafe Login" errors
- **Attachment Handling**: Attachments are automatically saved to `MCP_SAVE_PATH` when reading emails
- **Encoding Fallback**: Multiple charset attempts (utf-8, gbk, gb2312, latin-1) for email content decoding

## Configuration

The MCP server is configured via environment variables (passed through MCP client config):

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_EMAIL_PROTOCOL` | `imap` | Email protocol |
| `MCP_EMAIL_SERVER` | `imap.163.com` | IMAP server |
| `MCP_EMAIL_PORT` | `993` | IMAP port |
| `MCP_SMTP_SERVER` | `smtp.163.com` | SMTP server |
| `MCP_SMTP_PORT` | `465` | SMTP port |
| `MCP_EMAIL_USERNAME` | *(required)* | Email address |
| `MCP_EMAIL_PASSWORD` | *(required)* | Email password or app-specific password |
| `MCP_SAVE_PATH` | `/Users/anubis/404net/mcp-read-email-py/attachments` | Attachment save directory |

### MCP Config Files

Two MCP client configuration files are provided:

- `mcp-config-163.json` - Runs server via `fastmcp run` (Python source)
- `mcp-config-binary.json` - Runs compiled binary at `./dist/mcp_email_service_sdk`

Note: The config files contain placeholder paths that should be updated to match the actual installation location.

## Running the Server

### Development Mode (via FastMCP)
```bash
fastmcp run mcp_email_service_sdk.py
```

### As Compiled Binary
```bash
./dist/mcp_email_service_sdk
```

### Testing
```bash
# Test the packaged binary
python test_packaged_service.py
```

## Dependencies

- `fastmcp` - MCP server framework
- `pydantic` - Data validation
- Standard library: `imaplib`, `smtplib`, `email`

No `requirements.txt`, `pyproject.toml`, or `setup.py` exists in the repository. Dependencies must be installed manually.
