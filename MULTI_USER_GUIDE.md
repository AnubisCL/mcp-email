# Email MCP Server 多用户配置管理系统

## 系统架构

系统现在支持两种运行模式：

### 1. 单用户模式（环境变量模式）
- 使用 `.env` 文件配置
- 适合个人使用
- 向后兼容原有配置

### 2. 多用户模式（API Key 模式）
- 每个用户拥有独立的 API Key
- 通过 Vue.js 界面配置邮箱
- 支持多个邮箱平台
- 支持多用户、多邮箱

## 启动服务

### 启动配置管理 API 服务器（端口 8002）
```bash
./start-config.sh
```

### 启动 MCP 服务器（端口 8001）
```bash
./start.sh
```

## API 端点

### 配置管理 API (http://127.0.0.1:8002)

#### 用户认证
- `POST /api/auth/register` - 注册新用户并生成 API Key
- `GET /api/auth/me` - 获取当前用户信息

#### 邮箱配置
- `GET /api/config` - 获取所有邮箱配置
- `POST /api/config` - 创建新的邮箱配置
- `PUT /api/config/{id}` - 更新邮箱配置
- `DELETE /api/config/{id}` - 删除邮箱配置
- `POST /api/config/{id}/test` - 测试邮箱连通性

#### 其他
- `GET /api/providers` - 获取支持的邮箱提供商列表
- `GET /.well-known/mcp/server-management.json` - Server Management Discovery
- `GET /health` - 健康检查

## MCP 客户端使用

### 使用 API Key 访问

在请求头中添加 `X-API-Key`：
```bash
curl -X POST http://127.0.0.1:8001/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -d '{...}'
```

## 配置界面

访问 http://127.0.0.1:8002/config-ui/index.html 使用可视化配置界面。

### 功能
1. **API Key 管理**
   - 生成 API Key
   - 复制 API Key

2. **邮箱配置**
   - 支持的提供商：
     - 163网易邮箱
     - 126网易邮箱
     - Yeah网易邮箱
     - QQ邮箱
     - Gmail
     - Outlook
     - iCloud
     - 阿里云邮箱
     - 自定义（Custom）

3. **连通性测试**
   - IMAP 连接测试
   - SMTP 连接测试
   - 详细错误信息

4. **配置管理**
   - 激活/停用配置
   - 删除配置
   - 查看测试历史

## 项目结构

```
email-mcp/
├── .env                        # 单用户模式配置
├── .env.example                # 配置示例
├── start.sh                    # 启动 MCP 服务器
├── start-config.sh             # 启动配置 API 服务器
├── data/
│   └── email_mcp.db           # SQLite 数据库（多用户配置）
├── config-ui/
│   └── index.html             # Vue.js 配置界面
├── src/email_mcp/
│   ├── server.py              # MCP 服务器（支持 API Key）
│   ├── api_server.py          # FastAPI 配置管理服务
│   ├── database.py            # 数据库模型
│   ├── schemas.py             # Pydantic 模型
│   ├── connectivity.py        # 邮箱连通性测试
│   ├── models.py              # 原有模型
│   ├── client.py              # 原有客户端
│   └── utils.py               # 工具函数
└── .well-known/mcp/
    └── server-management.json # Server Management Discovery
```

## 数据库模式

### User 表
```sql
- id: Integer (主键)
- api_key: String (唯一, 64字符)
- created_at: DateTime
- is_active: Boolean
```

### EmailConfig 表
```sql
- id: Integer (主键)
- user_id: Integer (外键 -> users.id)
- name: String (配置名称)
- provider: String (邮箱提供商)
- imap_server: String
- imap_port: Integer
- username: String
- password: String
- smtp_server: String
- smtp_port: Integer
- is_active: Boolean
- last_tested: DateTime
- last_test_status: String
- created_at: DateTime
- updated_at: DateTime
```

## 安全注意事项

1. **生产环境部署**
   - 使用 PostgreSQL/MySQL 替代 SQLite
   - 加密存储密码
   - 使用 HTTPS
   - 配置防火墙

2. **API Key 管理**
   - 定期轮换 API Key
   - 不要在代码中硬编码
   - 使用环境变量传递

## MCP 客户端配置示例

### Claude Desktop 配置
```json
{
  "mcpServers": {
    "email": {
      "url": "http://localhost:8001/mcp",
      "transport": "streamable-http",
      "headers": {
        "X-API-Key": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

## 故障排查

### 1. 配置 API 无法启动
```bash
# 检查端口占用
lsof -i :8002

# 查看日志
export MCP_LOG_LEVEL=DEBUG
./start-config.sh
```

### 2. MCP 服务器无法连接数据库
```bash
# 检查数据库文件
ls -la data/email_mcp.db

# 重新初始化数据库
rm data/email_mcp.db
./start-config.sh
```

### 3. API Key 无效
```bash
# 重新生成 API Key
curl -X POST http://127.0.0.1:8002/api/auth/register
```

## 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| MCP_HOST | 否 | 127.0.0.1 | MCP 服务器地址 |
| MCP_PORT | 否 | 8001 | MCP 服务器端口 |
| CONFIG_API_HOST | 否 | 127.0.0.1 | 配置 API 服务器地址 |
| CONFIG_API_PORT | 否 | 8002 | 配置 API 服务器端口 |
| MCP_LOG_LEVEL | 否 | INFO | 日志级别 |

## 下一步功能

- [ ] 邮箱密码加密存储
- [ ] OAuth2 支持 (Gmail, Outlook)
- [ ] 配置导入/导出
- [ ] 使用统计和日志
- [ ] Webhook 通知
- [ ] PostgreSQL/MySQL 支持
