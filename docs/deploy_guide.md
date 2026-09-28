# CloudBase 部署指南

## 前置条件

1. 腾讯云账号（需实名认证）
2. 安装 CloudBase CLI: `npm install -g @cloudbase/cli`
3. 安装 Docker（用于本地构建镜像）

## 步骤 1: 创建 CloudBase 环境

1. 访问 https://tcb.cloud.tencent.com/
2. 登录腾讯云账号
3. 点击「新建环境」
4. 选择「免费体验版」（每月 3000 资源点）
5. 记录环境 ID（如 `football-assistant-xxx`）

## 步骤 2: 开通 PostgreSQL 数据库

1. 在 CloudBase 控制台 -> 「数据库」-> 「PostgreSQL」
2. 点击「开通」
3. 等待初始化完成
4. 获取连接信息:
   - 主机地址
   - 端口（默认 5432）
   - 数据库名
   - 用户名
   - 密码

## 步骤 3: 配置环境变量

在 CloudBase 控制台 -> 「云托管」-> 「服务设置」-> 「环境变量」中设置:

```
DATABASE_URL=postgresql+asyncpg://用户名:密码@主机:端口/数据库名
DATABASE_URL_SYNC=postgresql://用户名:密码@主机:端口/数据库名
CORS_ORIGINS=https://jqhuv828m4q.feishu.cn,http://localhost:3000,http://localhost:5173
ENV_ID=你的环境ID
```

## 步骤 4: 部署（云托管 - 推荐）

### 4.1 使用 CloudBase CLI 部署

```bash
# 登录
tcb login

# 进入项目目录
cd football-assistant

# 修改 cloudbase-container.json 中的 {{ENV_ID}} 和数据库连接信息

# 构建并部署
tcb framework:deploy
```

### 4.2 手动构建镜像部署

```bash
# 构建镜像
docker build -t football-assistant:latest .

# 推送镜像到腾讯云镜像仓库（或使用 CloudBase 自动构建）
# 在 CloudBase 控制台手动创建服务，选择镜像部署
```

## 步骤 5: 初始化数据库

部署完成后，需要运行数据库迁移:

```bash
# 本地执行迁移（需要能访问 CloudBase PostgreSQL）
# 修改 .env 中的 DATABASE_URL_SYNC 为 CloudBase 数据库连接
alembic upgrade head

# 或在 CloudBase 控制台使用「云函数」执行一次性初始化脚本
```

## 步骤 6: 验证部署

1. 访问 `https://你的服务域名/health`
2. 确认返回: `{"status":"healthy","version":"1.0.0",...}`
3. 访问 `https://你的服务域名/docs` 查看 Swagger UI
4. 从前端应用测试 API 调用

## 前端配置

在前端应用中配置后端 API 地址:

```javascript
const API_BASE_URL = 'https://你的服务域名/api';
```

## 常见问题

### Q: 云函数 vs 云托管怎么选？

- **云托管（推荐）**: 容器化部署，超时可达 60 秒，适合 API 服务
- **云函数**: Serverless，免费版超时 3 秒，适合简单触发器

### Q: 免费版资源够用吗？

- 每月 3000 资源点
- 云托管: 约可运行 1 个 0.25CPU/0.5GB 实例 720 小时/月
- 建议设置 minNum=0（无请求时缩容到 0，节省资源）

### Q: 数据库连接失败？

- 确认 CloudBase PostgreSQL 已开通
- 检查 DATABASE_URL 格式是否正确
- 确认数据库白名单允许 CloudBase 服务访问

### Q: CORS 跨域错误？

- 检查 CORS_ORIGINS 环境变量是否包含前端域名
- 前端域名必须精确匹配（包括协议 http/https）
