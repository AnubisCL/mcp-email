# Email MCP Server

基于 Model Context Protocol 的邮件服务器，支持 163.com、Gmail、Outlook 等 IMAP/SMTP 邮件服务。

## ⚡ 快速开始

### 1. 配置 `.env` 文件

```bash
# 编辑 .env 文件
vim .env
```

```env
# 必需配置
MCP_EMAIL_USERNAME=your@email.com
MCP_EMAIL_PASSWORD=your_auth_code

# 可选配置（已有默认值）
MCP_HOST=127.0.0.1
MCP_PORT=8001
MCP_LOG_LEVEL=INFO
```

**重要**：使用邮箱授权码，不是登录密码！

- **163 邮箱**：设置 → POP3/SMTP/IMAP → 授权码
- **Gmail**：账户安全 → 两步验证 → 应用专用密码
- **Outlook**：账户安全 → 应用密码

### 2. 启动服务器

```bash
./start.sh
```

你会看到：

```
✓ Loaded environment from: /path/to/.env
============================================================
  Email MCP Server - Streamable HTTP Mode
============================================================
  Host: 127.0.0.1
  Port: 8001
  Endpoint: http://127.0.0.1:8001/mcp
  Log Level: INFO
============================================================

Press Ctrl+C to stop the server
```

### 3. 配置 MCP 客户端

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

## 📁 项目结构

```
email-mcp/
├── .env                    # 🔑 环境变量配置
├── .env.example            # 📋 配置模板
├── start.sh                # 🚀 启动脚本
├── src/email_mcp/          # 💻 源代码
│   ├── server.py           # MCP 服务器
│   ├── client.py           # IMAP/SMTP 客户端
│   ├── models.py           # Pydantic 模型
│   ├── utils.py            # 工具函数
│   └── logging_config.py   # 日志配置
├── requirements.txt        # 📦 依赖
└── README.md               # 📖 本文档
```

## 🛠️ 可用工具

| 工具 | 说明 |
|------|------|
| `email_list_messages` | 列出邮件（支持过滤、分页） |
| `email_send_message` | 发送邮件（支持附件） |

## ⚙️ 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `MCP_EMAIL_USERNAME` | ✅ | - | 邮箱地址 |
| `MCP_EMAIL_PASSWORD` | ✅ | - | 授权码（非登录密码） |
| `MCP_EMAIL_SERVER` | ❌ | `imap.163.com` | IMAP 服务器 |
| `MCP_EMAIL_PORT` | ❌ | `993` | IMAP 端口 |
| `MCP_SMTP_SERVER` | ❌ | `smtp.163.com` | SMTP 服务器 |
| `MCP_SMTP_PORT` | ❌ | `465` | SMTP 端口 |
| `MCP_SAVE_PATH` | ❌ | `~/email-attachments` | 附件路径 |
| `MCP_HOST` | ❌ | `127.0.0.1` | HTTP 监听地址 |
| `MCP_PORT` | ❌ | `8001` | HTTP 端口 |
| `MCP_LOG_LEVEL` | ❌ | `INFO` | 日志级别 |

## 🔍 日志级别

| 级别 | 用途 |
|------|------|
| `DEBUG` | 详细调试信息（连接、消息ID、附件） |
| `INFO` | 一般操作信息（工具调用、认证、结果） |
| `WARNING` | 警告信息（跳过的消息） |
| `ERROR` | 错误信息（认证失败、连接失败） |

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

## 🔧 命令行选项

```bash
# 默认启动（使用 .env 配置）
./start.sh

# 自定义端口
python src/email_mcp/server.py --port 9000

# 自定义主机和端口
python src/email_mcp/server.py --host 0.0.0.0 --port 8001
```

## 🔒 安全提醒

- ⚠️ **永远不要**提交 `.env` 文件到版本控制
- ⚠️ **永远不要**在代码中硬编码密码
- ✅ 使用授权码而不是登录密码
- ✅ 定期更换授权码

## 📚 开发文档

- `CLAUDE.md` - Claude Code 开发指南
- `.well-known/mcp/server-management.json` - MCP 管理发现配置

## 🐛 故障排查

### 服务器无法启动

```bash
# 检查端口占用
lsof -i :8001

# 查看详细日志
export MCP_LOG_LEVEL=DEBUG
./start.sh
```

### 认证失败

- 使用**授权码**，不是登录密码
- 确认 IMAP/SMTP 服务已开启
- 检查防火墙设置

### MCP 客户端无法连接

```bash
# 测试 MCP 端点
curl http://localhost:8001/mcp

# 检查服务器状态
lsof -i :8001
```

## 📄 License

MIT License
