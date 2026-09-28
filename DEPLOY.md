# Football Betting Assistant - Render 部署指南

## 方案一：使用 Render Blueprint 一键部署（推荐）

### 前置准备
1. 注册 [Render](https://render.com/) 账号（支持 GitHub/Google 登录）
2. 将本项目代码推送到你的 GitHub/GitLab 仓库

### 部署步骤

1. 访问 Render Blueprint 部署链接：
   ```
   https://render.com/blueprints
   ```

2. 点击 **"New Blueprint Instance"**

3. 连接你的 GitHub 仓库，选择 `football-assistant` 项目

4. Render 会自动识别 `render.yaml` 并创建：
   - **Web Service**: `football-assistant-api`（Docker 部署）
   - **PostgreSQL**: `football-assistant-db`（免费实例，90 天有效期）

5. 等待部署完成（约 3-5 分钟）

6. 部署完成后，你会获得一个类似以下的 API 地址：
   ```
   https://football-assistant-api-xxxx.onrender.com
   ```

### 部署后配置

1. 在 Render Dashboard 中找到你的 Web Service
2. 进入 **Environment** 标签页
3. 确认以下环境变量已正确设置：
   - `DATABASE_URL_SYNC`：自动从 PostgreSQL 实例获取
   - `CORS_ORIGINS`：`https://jqhuv828m4q.feishu.cn,http://localhost:3000,http://localhost:5173`

4. 如需添加前端地址到 CORS，编辑 `CORS_ORIGINS` 并添加你的前端域名

---

## 方案二：手动创建服务

如果你不想使用 Blueprint，可以手动创建：

### 1. 创建 PostgreSQL 数据库

1. 进入 Render Dashboard → **New** → **PostgreSQL**
2. 选择 **Free** 计划
3. 命名：`football-assistant-db`
4. 创建后复制 **Internal Database URL**（格式：`postgresql://...`）

### 2. 创建 Web Service

1. Render Dashboard → **New** → **Web Service**
2. 连接 GitHub 仓库
3. 配置：
   - **Name**: `football-assistant-api`
   - **Runtime**: `Docker`
   - **Branch**: `main`
   - **Root Directory**: `./`
   - **Dockerfile Path**: `./Dockerfile`

4. 在 **Environment Variables** 中添加：
   ```
   DATABASE_URL_SYNC = postgresql://用户名:密码@主机:端口/数据库名
   CORS_ORIGINS = https://jqhuv828m4q.feishu.cn,http://localhost:3000,http://localhost:5173
   ```

5. 点击 **Create Web Service**

---

## 验证部署

部署完成后，访问以下端点验证：

```bash
# 健康检查
GET https://your-service.onrender.com/health

# API 文档（Swagger UI）
GET https://your-service.onrender.com/docs

# OpenAPI 规范
GET https://your-service.onrender.com/openapi.json
```

### 可用 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/fixtures` | GET | 获取赛程列表 |
| `/api/fixtures/{id}` | GET | 获取单场赛程详情 |
| `/api/leagues` | GET | 获取联赛列表 |
| `/api/leagues/{id}` | GET | 获取联赛详情 |
| `/api/teams` | GET | 获取球队列表 |
| `/api/teams/{id}` | GET | 获取球队详情 |
| `/api/odds` | GET | 获取赔率列表 |
| `/api/odds/{fixture_id}` | GET | 获取单场赔率 |

---

## 注意事项

### Render 免费版限制
- **Web Service**: 15 分钟无请求后进入休眠，下次请求需等待 30-60 秒冷启动
- **PostgreSQL**: 免费实例 90 天后过期，数据量限制 1GB
- **建议**: 生产环境或需要稳定服务的场景，建议升级到付费计划

### 数据库初始化
首次部署后，FastAPI 的 `lifespan` 会自动执行 `init_db()` 创建数据表。如果数据库连接失败，服务仍会启动但会记录错误日志。

### 更新前端 CORS
如果前端地址变更，在 Render Dashboard 的 Environment 中修改 `CORS_ORIGINS` 环境变量，多个地址用英文逗号分隔。

---

## 故障排查

### 服务启动失败
1. 查看 Render Dashboard → Logs 标签页
2. 常见原因：
   - 数据库连接字符串错误
   - 端口冲突（确保 Dockerfile 中使用了 `${PORT:-8080}`）

### 数据库连接失败
1. 确认 `DATABASE_URL_SYNC` 格式正确：`postgresql://user:pass@host:port/db`
2. 在 Render 中检查 PostgreSQL 实例状态是否为 **Available**
3. 确认数据库实例和 Web Service 在同一区域

### API 返回 500
1. 查看 Render Logs 中的错误堆栈
2. 确认数据库表已创建（可通过 `/health` 端点检查）
