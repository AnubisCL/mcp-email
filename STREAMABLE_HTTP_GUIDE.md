# Streamable HTTP 迁移指南

## 环境变量传递方案对比

### 方案 1: 服务器环境变量（单用户场景）

适用于：个人服务器，单一邮箱账户

```bash
# 启动服务器时设置环境变量
export MCP_EMAIL_USERNAME="your@email.com"
export MCP_EMAIL_PASSWORD="authorization-code"
export MCP_EMAIL_SERVER="imap.163.com"
export MCP_EMAIL_PORT="993"
export MCP_SMTP_SERVER="smtp.163.com"
export MCP_SMTP_PORT="465"
export MCP_SAVE_PATH="/path/to/attachments"

# 启动 HTTP 服务器
python src/email_mcp/server.py --transport streamable-http --port 8001
```

**MCP 客户端配置：**
```json
{
  "mcpServers": {
    "email": {
      "url": "http://localhost:8001/mcp",
      "transport": "streamable-http"
    }
  }
}
```

---

### 方案 2: 请求头传递（多用户场景）

适用于：多用户共享服务器，每个用户有自己的邮箱

**服务端改造：**
```python
# src/email_mcp/server.py
from fastmcp import FastMCP, Context

@mcp.tool()
async def email_list_messages(params: ListMessagesInput, ctx: Context) -> str:
    """从请求头获取凭证"""

    # 从请求头获取认证信息
    auth_header = ctx.request.headers.get("X-Email-Auth")
    if not auth_header:
        return "Error: Missing X-Email-Auth header"

    # 解析凭证（格式: base64(username:password)）
    import base64
    decoded = base64.b64decode(auth_header).decode()
    username, password = decoded.split(":", 1)

    # 创建配置
    config = EmailConfig(
        username=username,
        password=password,
        imap_server=os.getenv("MCP_EMAIL_SERVER", "imap.163.com"),
        imap_port=int(os.getenv("MCP_EMAIL_PORT", "993")),
        smtp_server=os.getenv("MCP_SMTP_SERVER", "smtp.163.com"),
        smtp_port=int(os.getenv("MCP_SMTP_PORT", "465")),
        save_path=os.getenv("MCP_SAVE_PATH", "/tmp/attachments")
    )

    client = EmailClient(config)
    # ... 处理请求
```

**MCP 客户端配置：**
```json
{
  "mcpServers": {
    "email": {
      "url": "http://localhost:8001/mcp",
      "transport": "streamable-http",
      "headers": {
        "X-Email-Auth": "base64(username:password)"
      }
    }
  }
}
```

---

### 方案 3: API Key + 数据库（企业场景）

适用于：企业级部署，需要完整的用户管理

**架构：**
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   MCP 客户端 │────▶│  HTTP 服务器 │────▶│  用户数据库  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  邮件服务器   │
                    └─────────────┘
```

**服务端实现：**
```python
# src/email_mcp/auth.py
import sqlite3
from typing import Optional

class UserAuthStore:
    """用户凭证存储"""

    def get_user_credentials(self, api_key: str) -> Optional[dict]:
        """根据 API Key 获取用户凭证"""
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT email_username, email_password, imap_server, smtp_server "
            "FROM users WHERE api_key = ?",
            (api_key,)
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "username": result[0],
                "password": result[1],
                "imap_server": result[2],
                "smtp_server": result[3]
            }
        return None

# 全局认证存储
auth_store = UserAuthStore()

# src/email_mcp/server.py
@mcp.tool()
async def email_list_messages(
    params: ListMessagesInput,
    ctx: Context,
    api_key: str = None  # 从请求头或查询参数获取
) -> str:
    """使用 API Key 认证"""

    credentials = auth_store.get_user_credentials(api_key)
    if not credentials:
        return "Error: Invalid API key"

    config = EmailConfig(**credentials)
    client = EmailClient(config)
    # ...
```

**MCP 客户端配置：**
```json
{
  "mcpServers": {
    "email": {
      "url": "http://mcp.example.com/email-mcp?api_key=your-api-key",
      "transport": "streamable-http"
    }
  }
}
```

---

## FastMCP Streamable HTTP 配置

### 启动 HTTP 服务器

```python
# src/email_mcp/server.py
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Email MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport protocol"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="HTTP port (for streamable-http)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP host (for streamable-http)"
    )

    args = parser.parse_args()

    if args.transport == "streamable-http":
        # Streamable HTTP 模式
        mcp.run(transport="streamable-http", port=args.port, host=args.host)
    else:
        # stdio 模式（默认）
        mcp.run()
```

### 启动命令

```bash
# stdio 模式（当前默认）
python src/email_mcp/server.py

# HTTP 模式
python src/email_mcp/server.py --transport streamable-http --port 8001 --host 0.0.0.0

# 使用环境变量配置
MCP_EMAIL_USERNAME="user@163.com" \
MCP_EMAIL_PASSWORD="auth-code" \
python src/email_mcp/server.py --transport streamable-http --port 8001
```

---

## 推荐方案总结

| 场景 | 推荐方案 | 认证方式 |
|------|----------|----------|
| **个人本地使用** | 保持 stdio | 环境变量 |
| **个人云服务器** | Streamable HTTP | 环境变量 |
| **团队共享（3-10人）** | Streamable HTTP | 请求头认证 |
| **企业级（10+人）** | Streamable HTTP | API Key + 数据库 |
| **SaaS 服务** | Streamable HTTP | OAuth 2.1 + 租户隔离 |

---

## 安全注意事项

### ⚠️ 重要安全警告

1. **永远不要在 URL 中传递密码**
   ```json
   // ❌ 错误
   {"url": "http://server/?password=secret"}

   // ✅ 正确
   {"url": "http://server/", "headers": {"X-Auth": "base64(...)"}}
   ```

2. **使用 HTTPS 生产环境**
   ```bash
   # 开发环境
   python src/email_mcp/server.py --port 8001

   # 生产环境（使用反向代理）
   # Nginx/Caddy 配置 HTTPS → 转发到 localhost:8001
   ```

3. **敏感数据加密存储**
   ```python
   # 使用加密存储凭证
   from cryptography.fernet import Fernet

   key = os.getenv("ENCRYPTION_KEY")
   cipher = Fernet(key)
   encrypted_password = cipher.encrypt(password.encode())
   ```

4. **API Key 轮换**
   - 定期更换 API Key
   - 设置 API Key 过期时间
   - 记录审计日志

---

## 下一步改造建议

1. **立即可做：**
   - 保持当前 stdio 模式
   - 适合个人使用和开发

2. **短期目标：**
   - 添加 `--transport streamable-http` 选项
   - 使用环境变量配置（方案1）

3. **长期规划：**
   - 实现用户认证系统（方案2或3）
   - 添加 API Key 管理
   - 实现多租户隔离
   - 添加使用配额限制
