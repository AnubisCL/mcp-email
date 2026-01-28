# Email MCP Server

基于 Model Context Protocol 的多用户邮件服务器，支持 163.com、Gmail、Outlook、QQ、iCloud、阿里云等 IMAP/SMTP 邮件服务。

## ✨ 特性

- 🔐 **多用户支持**：每个邮箱配置独立 API 密钥，安全隔离
- 📧 **多邮箱服务商**：支持 163、126、Yeah、QQ、Gmail、Outlook、iCloud、阿里云及自定义 IMAP/SMTP
- 🛠️ **Web 配置界面**：可视化管理邮箱配置和测试连接
- 🔍 **连接测试**：实时测试 IMAP/SMTP 连接状态
- 📊 **邮件列表**：支持按类型筛选（未读/已读/已标记等）
- 📎 **附件支持**：自动下载附件到本地目录
- 🚀 **流式 HTTP 传输**：基于 FastMCP 的高性能 MCP 服务器

## 🏗️ 架构

Email MCP Server 采用双服务器架构：

```
┌─────────────────────────────────────────────────────────┐
│                   Email MCP Server                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────┐        ┌─────────────────────┐   │
│  │  MCP Server      │        │  Configuration API  │   │
│  │  (Port 8001)     │        │  (Port 8002)        │   │
│  │                  │        │                     │   │
│  │  • email_list    │        │  • 邮箱配置管理     │   │
│  │  • email_send    │        │  • API 密钥生成     │   │
│  │  • MCP 协议      │        │  • 连接测试         │   │
│  └──────────────────┘        │  • Web 配置界面     │   │
│         │                   └─────────────────────┘   │
│         │                            │                 │
│         └────────────┬───────────────┘                 │
│                      │                                 │
│              ┌───────▼────────┐                        │
│              │  SQLite 数据库  │                        │
│              │  多用户配置     │                        │
│              └────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

## ⚡ 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

**终端 1 - 启动 MCP 服务器：**

```bash
./start.sh
```

**终端 2 - 启动配置管理 API：**

```bash
python -m email_mcp.api_server
```

### 3. 配置邮箱账号

打开浏览器访问：http://127.0.0.1:8002/config-ui/index.html

**配置界面功能**：

1. **邮箱配置管理**
   - 支持的邮箱提供商：
     - 163 网易邮箱
     - 126 网易邮箱
     - Yeah 网易邮箱
     - QQ 邮箱
     - Gmail
     - Outlook
     - iCloud
     - 阿里云邮箱
     - 自定义 IMAP/SMTP 服务器

2. **连通性测试**
   - IMAP 连接测试
   - SMTP 连接测试
   - 详细的错误信息和状态反馈

3. **配置操作**
   - 创建、编辑、删除邮箱配置
   - 激活/停用配置
   - 查看测试历史记录
   - 自动生成并复制 API 密钥

**配置步骤**：
1. 点击"添加邮箱配置"
2. 选择邮箱服务商
3. 填写邮箱地址和授权码（**注意：使用授权码，不是登录密码**）
4. 点击"测试连接"验证配置
5. 保存后会自动生成 API 密钥
6. 复制 API 密钥用于 MCP 客户端配置

### 4. 配置 MCP 客户端

在 Claude Desktop 或其他 MCP 客户端配置中使用生成的 API 密钥：

```json
{
  "mcpServers": {
    "email-work": {
      "url": "http://localhost:8001/mcp",
      "transport": "streamable-http",
      "headers": {
        "X-API-Key": "your-generated-api-key-here"
      }
    },
    "email-personal": {
      "url": "http://localhost:8001/mcp",
      "transport": "streamable-http",
      "headers": {
        "X-API-Key": "another-api-key"
      }
    }
  }
}
```

## 📁 项目结构

```
email-mcp/
├── src/email_mcp/          # 💻 源代码
│   ├── server.py           # MCP 服务器（端口 8001）
│   ├── api_server.py       # 配置管理 API（端口 8002）
│   ├── client.py           # IMAP/SMTP 客户端
│   ├── models.py           # MCP 工具输入模型
│   ├── schemas.py          # API 请求/响应模型
│   ├── database.py         # 数据库模型
│   ├── connectivity.py     # 连接测试工具
│   ├── utils.py            # 工具函数
│   └── logging_config.py   # 日志配置
├── data/
│   └── email_mcp.db        # SQLite 数据库（自动创建）
├── .well-known/mcp/        # MCP 管理发现
│   └── server-management.json
├── start.sh                # 🚀 MCP 服务器启动脚本
├── requirements.txt        # 📦 依赖
├── CLAUDE.md               # 📖 Claude Code 开发指南
└── README.md               # 📖 本文档
```

## 🛠️ 可用工具

| 工具 | 说明 |
|------|------|
| `email_list_messages` | 列出邮件（支持过滤、分页） |
| `email_send_message` | 发送邮件（支持附件） |

## 🔌 API 端点

### 配置管理 API (http://127.0.0.1:8002)

#### 邮箱配置管理
- `GET /api/configs` - 获取所有邮箱配置
- `POST /api/configs` - 创建新的邮箱配置（自动生成 API Key）
- `GET /api/configs/{id}` - 获取指定配置详情
- `PUT /api/configs/{id}` - 更新邮箱配置
- `DELETE /api/configs/{id}` - 删除邮箱配置
- `POST /api/configs/{id}/test` - 测试邮箱连通性

#### 其他端点
- `GET /api/providers` - 获取支持的邮箱提供商列表
- `GET /.well-known/mcp/server-management.json` - Server Management Discovery
- `GET /health` - 健康检查
- `GET /` - 重定向到配置界面

### MCP 服务器 (http://127.0.0.1:8001)

- `POST /mcp` - MCP 协议端点（需要 `X-API-Key` 请求头）
- 支持 MCP 协议操作：`initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`

## 💾 数据库架构

项目使用 SQLite 存储多用户配置（生产环境建议使用 PostgreSQL 或 MySQL）。

### EmailConfig 表

```sql
CREATE TABLE email_configs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key         VARCHAR(64) UNIQUE NOT NULL,      -- API 密钥
    name            VARCHAR(100) NOT NULL,            -- 配置名称
    provider        VARCHAR(50) NOT NULL,             -- 邮箱提供商
    imap_server     VARCHAR(255) NOT NULL,            -- IMAP 服务器
    imap_port       INTEGER DEFAULT 993 NOT NULL,     -- IMAP 端口
    username        VARCHAR(255) NOT NULL,            -- 邮箱用户名
    password        VARCHAR(255) NOT NULL,            -- 邮箱密码/授权码
    smtp_server     VARCHAR(255) NOT NULL,            -- SMTP 服务器
    smtp_port       INTEGER DEFAULT 465 NOT NULL,     -- SMTP 端口
    is_active       BOOLEAN DEFAULT TRUE NOT NULL,    -- 是否激活
    last_tested     DATETIME,                         -- 最后测试时间
    last_test_status VARCHAR(20),                     -- 最后测试状态
    created_at      DATETIME NOT NULL,                -- 创建时间
    updated_at      DATETIME NOT NULL                 -- 更新时间
);
```

**索引**：`api_key` 字段有唯一索引，确保查询性能。

## ⚙️ 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `MCP_HOST` | ❌ | `127.0.0.1` | MCP 服务器监听地址 |
| `MCP_PORT` | ❌ | `8001` | MCP 服务器端口 |
| `MCP_LOG_LEVEL` | ❌ | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |

**注意**：邮箱配置不再使用环境变量，而是通过 Web 配置界面管理。

## 🔧 高级选项

### MCP 服务器命令行选项

```bash
# 自定义端口
python src/email_mcp/server.py --port 9000

# 自定义主机和端口
python src/email_mcp/server.py --host 0.0.0.0 --port 8001

# 设置日志级别
export MCP_LOG_LEVEL=DEBUG
./start.sh
```

### 配置 API 服务器选项

```bash
# 使用 uvicorn 启动（支持热重载）
uvicorn email_mcp.api_server:app --host 127.0.0.1 --port 8002 --reload

# 自定义端口
uvicorn email_mcp.api_server:app --port 9000
```

## 🔍 日志级别

| 级别 | 用途 |
|------|------|
| `DEBUG` | 详细调试信息（连接、消息ID、附件、API 密钥） |
| `INFO` | 一般操作信息（工具调用、认证、结果） |
| `WARNING` | 警告信息（跳过的消息） |
| `ERROR` | 错误信息（认证失败、连接失败） |

## 🔒 安全提醒

- ⚠️ **永远不要**将 API 密钥分享给他人
- ⚠️ **永远不要**提交 `data/email_mcp.db` 到版本控制
- ⚠️ **永远不要**在代码中硬编码密码或 API 密钥
- ✅ 使用邮箱授权码而不是登录密码
- ✅ 定期更换授权码和 API 密钥
- ✅ 生产环境建议使用 PostgreSQL 或 MySQL 替代 SQLite
- ✅ 配置 API 服务器不应暴露到公网

## 📚 开发文档

- `CLAUDE.md` - Claude Code 开发指南（架构详解）
- `.well-known/mcp/server-management.json` - MCP 管理发现配置

## 🐛 故障排查

### MCP 服务器无法启动

```bash
# 检查端口占用
lsof -i :8001

# 查看详细日志
export MCP_LOG_LEVEL=DEBUG
./start.sh
```

### 配置 API 服务器无法启动

```bash
# 检查端口占用
lsof -i :8002

# 查看详细日志
uvicorn email_mcp.api_server:app --log-level debug
```

### 401 Unauthorized 错误

- **原因**：缺少或无效的 `X-API-Key` 请求头
- **解决**：确保 MCP 客户端配置中包含正确的 API 密钥
- **获取密钥**：访问 http://127.0.0.1:8002/config-ui/index.html 查看或生成 API 密钥

### 邮箱认证失败

- 使用**授权码**，不是登录密码
- 确认 IMAP/SMTP 服务已开启
- 检查防火墙设置
- 在配置界面点击"测试连接"验证配置

### MCP 客户端无法连接

```bash
# 测试 MCP 端点（需要 API 密钥）
curl -H "X-API-Key: your-api-key" http://localhost:8001/mcp

# 检查服务器状态
lsof -i :8001

# 测试配置 API
curl http://localhost:8002/health
```

### 数据库问题

```bash
# 重置数据库（会删除所有配置）
rm data/email_mcp.db

# 检查数据库权限
ls -la data/email_mcp.db
```

## 📧 邮箱服务商配置指南

### 163 / 126 / Yeah 邮箱

1. 登录网页版邮箱
2. 设置 → POP3/SMTP/IMAP
3. 开启 IMAP/SMTP 服务
4. 生成授权码
5. 使用授权码作为密码

### QQ 邮箱

1. 登录网页版邮箱
2. 设置 → 账户
3. 开启 IMAP/SMTP 服务
4. 生成授权码
5. 使用授权码作为密码

### Gmail

1. 启用两步验证
2. 账户安全 → 应用专用密码
3. 生成应用密码
4. 使用应用密码作为密码

### Outlook

1. 账户安全 → 应用密码
2. 生成应用密码
3. 使用应用密码作为密码

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 🔮 未来计划

- [ ] 邮箱密码加密存储
- [ ] OAuth2 支持 (Gmail, Outlook)
- [ ] 配置导入/导出功能
- [ ] 使用统计和日志记录
- [ ] Webhook 通知支持
- [ ] PostgreSQL/MySQL 支持
- [ ] 多语言支持

## 📖 API 使用示例

### 使用 curl 测试 API

```bash
# 测试配置 API 健康状态
curl http://localhost:8002/health

# 获取支持的邮箱提供商列表
curl http://localhost:8002/api/providers

# 创建新的邮箱配置
curl -X POST http://localhost:8002/api/configs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的工作邮箱",
    "provider": "163",
    "username": "your@email.com",
    "password": "your-auth-code"
  }'

# 测试邮箱连通性
curl -X POST http://localhost:8002/api/configs/1/test \
  -H "Content-Type: application/json"

# 使用 MCP 工具（需要 API Key）
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "email_list_messages",
      "arguments": {
        "count": 5,
        "message_type": "UNSEEN"
      }
    }
  }'
```

## 📄 License

MIT License
