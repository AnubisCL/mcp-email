# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Email MCP (Model Context Protocol) server that provides multi-user email functionality for various email providers including 163.com, Gmail, Outlook, QQ, iCloud, Aliyun, and other IMAP/SMTP compatible services. The server follows MCP best practices with proper naming conventions, tool annotations, and error handling.

**Key Architecture Feature**: Multi-user configuration management with per-user API keys. The server runs as a single HTTP service (port 8001) with integrated:
1. **MCP Protocol Layer** (`/mcp`): Handles email operations via MCP protocol
2. **Configuration Management API** (`/api`): Manages email accounts and API keys
3. **Web Configuration UI** (`/config-ui`): Visual interface for configuration

## Architecture

The project uses a unified server architecture with clear separation of concerns:

### Directory Structure

```
src/email_mcp/
├── __init__.py          # Package initialization, exports mcp server
├── server.py            # Main server - mounts MCP, Config API, and Web UI
├── api_server.py        # FastAPI app for configuration management
├── client.py            # EmailClient for IMAP/SMTP operations
├── models.py            # Pydantic models for MCP input validation
├── schemas.py           # Pydantic models for API request/response
├── database.py          # SQLAlchemy database models and session management
├── connectivity.py      # Email connection testing utilities
├── logging_config.py    # Logging configuration
└── utils.py             # Utility functions (formatting, error handling)

data/
└── email_mcp.db         # SQLite database for multi-user configurations
```

### Key Components

**`server.py`** - Main Unified Server (Port 8001)
- Integrates MCP protocol, Configuration API, and Web UI in one server
- Two middleware layers for API key authentication:
  - `HTTPAPIKeyMiddleware`: HTTP-level validation (Starlette)
  - `APIKeyMiddleware`: MCP protocol-level validation (FastMCP)
- Mounts FastAPI app at `/api` path for configuration management
- Mounts static files at `/config-ui` for web interface
- Context management: Each request's email config is stored in `_current_config` ContextVar
- Two MCP tools: `email_list_messages` and `email_send_message`
- Tool annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- Handles multiple parameter formats: dict, JSON string, or Pydantic models

**`api_server.py`** - Configuration Management API
- FastAPI app that gets mounted to main server at `/api`
- Endpoints for email configuration CRUD operations
- REST API for managing multiple email accounts
- Auto-generates unique API keys for each configuration
- Provides connection testing via `/api/configs/{id}/test`
- Routes defined without `/api` prefix (added when mounted)
- CORS enabled for cross-origin requests

**`database.py`** - SQLAlchemy Models
- `EmailConfig`: Email configuration model with per-config API key
- SQLite database with `check_same_thread=False` for FastAPI compatibility
- Session factory pattern for thread-safe database access
- Database auto-initialization with `data/` directory creation

**`schemas.py`** - API Validation Models
- `ProviderType`: Enum of supported email providers (163, 126, yeah, qq, gmail, outlook, icloud, aliyun, custom)
- `PROVIDER_CONFIGS`: Predefined server configurations for each provider
- Request/Response models for configuration API
- Field validators for data sanitization

**`connectivity.py`** - Connection Testing
- `test_imap_connection()`: Tests IMAP server connectivity and authentication
- `test_smtp_connection()`: Tests SMTP server connectivity (SSL and STARTTLS)
- `test_email_connection()`: Tests both protocols and returns detailed results
- Handles various error types: timeout, DNS failure, auth failure, connection refused

**`client.py`** - EmailClient Class
- `_connect_imap()`: IMAP connection with 163.com ID extension support
- `_connect_smtp()`: SMTP connection
- `list_messages()`: Retrieve emails from INBOX with filtering
- `send_message()`: Send email with attachments

**`models.py`** - MCP Tool Input Validation
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

### Server Environment Variables

The server uses these environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_HOST` | No | `127.0.0.1` | Server HTTP host |
| `MCP_PORT` | No | `8001` | Server HTTP port |
| `MCP_LOG_LEVEL` | No | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

### Multi-User Configuration

**IMPORTANT**: This server uses a multi-user architecture where each email configuration has its own API key. Configuration is managed via the Web UI or API.

1. Start the server: `./start.sh` (runs on port 8001)
2. Open http://127.0.0.1:8001/config-ui/index.html to configure email accounts
3. Each configuration automatically gets a unique API key
4. Use the API key in MCP client requests via `X-API-Key` header

### Email Provider Authorization

For most email providers, use an **authorization code** (not login password):

- **163/126/Yeah**: 设置 → POP3/SMTP/IMAP → 授权码
- **Gmail**: Account security → 2-Step Verification → App passwords
- **Outlook**: Account security → App passwords
- **QQ Mail**: Settings → Account → POP3/SMTP/IMAP → Authorization code

## Running the Server

```bash
# Via start script (recommended)
./start.sh

# Direct execution with custom host/port
python src/email_mcp/server.py --host 0.0.0.0 --port 8001

# Set log level
export MCP_LOG_LEVEL=DEBUG
./start.sh
```

The server will display:
```
============================================================
  Email MCP Server - All-in-One Mode
============================================================
  Host: 127.0.0.1
  Port: 8001
  MCP Endpoint: http://127.0.0.1:8001/mcp
  Config API:   http://127.0.0.1:8001/api
  Config UI:    http://127.0.0.1:8001/config-ui/index.html
  Log Level: INFO
============================================================
```

### MCP Client Configuration

Example for Claude Desktop or other MCP clients:

```json
{
  "mcpServers": {
    "email": {
      "url": "http://localhost:8001/mcp",
      "transport": "streamable-http",
      "headers": {
        "X-API-Key": "your-api-key-here"
      }
    }
  }
}
```

**CRITICAL**: The `X-API-Key` header is required for all requests. Each email configuration has its own unique API key generated by the Configuration API.

## Development Commands

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Code Quality

```bash
# Format code (line length: 100)
black src/

# Lint
ruff check src/

# Type check
mypy src/
```

### Testing

```bash
# Test with MCP Inspector (requires X-API-Key header)
npx @modelcontextprotocol/inspector src/email_mcp/server.py

# Test MCP server endpoint
curl -H "X-API-Key: your-api-key" http://localhost:8001/mcp

# Test configuration API
curl http://localhost:8001/api/health
curl http://localhost:8001/api/configs -H "X-API-Key: your-api-key"

# Test web interface
curl http://localhost:8001/
```

### Database Management

```bash
# Database is auto-created on first run at data/email_mcp.db
# To reset:
rm data/email_mcp.db
```

## MCP Best Practices Followed

- **Server Naming**: `email_mcp` (Python convention: `{service}_mcp`)
- **Tool Naming**: `email_list_messages`, `email_send_message` (snake_case with prefix)
- **Pydantic v2**: Uses `model_config` instead of nested `Config` class
- **Tool Annotations**: All tools have proper hints set (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`)
- **Error Handling**: Actionable error messages with specific guidance
- **Response Formats**: Supports both Markdown and JSON outputs
- **Type Safety**: Full type hints throughout
- **Docstrings**: Comprehensive documentation with schema structures
- **Multi-tenancy**: Per-user API keys for secure multi-user access
- **Management Discovery**: `.well-known/mcp/server-management.json` for MCP client auto-discovery

## Dependencies

Core dependencies:
- `fastmcp` - MCP server framework with streamable HTTP transport
- `pydantic` - Data validation (v2+)
- `fastapi` - Configuration API server
- `sqlalchemy` - Database ORM for multi-user configuration
- `python-dotenv` - Environment variable loading
- `uvicorn` - ASGI server for Configuration API

Python standard library: `imaplib`, `smtplib`, `email`, `sqlite3`

## Architecture Patterns

### API Key Authentication Flow

1. Client sends request with `X-API-Key` header
2. `HTTPAPIKeyMiddleware` validates key at HTTP layer (Starlette)
3. API key is used to fetch email config from database
4. Email config is stored in `_current_config` ContextVar
5. `APIKeyMiddleware` validates at MCP protocol layer (FastMCP)
6. MCP tools access config via `_get_email_config()`

### Context Management

The server uses Python's `contextvars.ContextVar` for thread-safe context management:

```python
# Set context (in middleware)
_current_config.set(config)

# Get context (in tools)
config = _current_config.get()

# Reset context (in middleware finally block)
_current_config.reset(token)
```

This ensures each request gets its own isolated email configuration, even in async/concurrent scenarios.

### Database Session Management

The Configuration API uses dependency injection for database sessions:

```python
def get_db():
    global _session_factory
    if _session_factory is None:
        engine = init_database()
        _session_factory = get_session_factory(engine)
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()
```

This pattern ensures proper session cleanup and thread safety with SQLAlchemy.

### Tool Parameter Handling

MCP tools accept three parameter formats for flexibility:
1. **Pydantic model**: `ListMessagesInput(count=10)`
2. **Dict**: `{"count": 10, "message_type": "UNSEEN"}`
3. **JSON string**: `'{"count": 10, "message_type": "UNSEEN"}'`

All formats are normalized to Pydantic models for validation:
```python
if isinstance(params, str):
    params_dict = json.loads(params)
elif isinstance(params, dict):
    params_dict = params
else:
    params_dict = params.model_dump()

validated_params = ListMessagesInput(**params_dict)
```

## Common Issues

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Missing or invalid `X-API-Key` header in request |
| Authentication failed | Use authorization code, not login password |
| Connection timeout | Check firewall allows IMAP/SMTP ports (993/465) |
| "Unsafe Login" error | Fixed by IMAP ID extension in `client.py` (163.com specific) |
| SQLite thread error | Already handled with `check_same_thread=False` in database URL |
| Database locked | SQLite handles concurrent reads, but writes are serialized |
| Config UI 404 | Ensure server is running and check /config-ui path |

## API Endpoints

All endpoints are served from the same port (8001):

### Configuration Management API (/api)

- `GET /api/configs` - List all email configurations
- `POST /api/configs` - Create new email configuration (auto-generates API key)
- `GET /api/configs/{id}` - Get specific configuration
- `PUT /api/configs/{id}` - Update configuration
- `DELETE /api/configs/{id}` - Delete configuration
- `POST /api/configs/{id}/test` - Test email connectivity
- `GET /api/providers` - List supported email providers
- `GET /api/health` - Health check

### MCP Protocol

- `POST /mcp` - MCP protocol endpoint (requires `X-API-Key` header)
- All MCP protocol operations: initialize, tools/list, tools/call, resources/list, resources/read

### Web Interface

- `GET /` - Redirect to configuration UI
- `GET /config-ui/index.html` - Configuration management UI
- `GET /.well-known/mcp/server-management.json` - Server management discovery
