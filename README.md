# 竞彩足球购买助手 - 后端服务 (Football Betting Assistant Backend)

基于 FastAPI + PostgreSQL 构建的竞彩足球数据后端服务，部署于腾讯云开发 CloudBase。

## 技术栈

- **框架**: FastAPI 0.109.2
- **数据库**: PostgreSQL (CloudBase 内置)
- **ORM**: SQLAlchemy 2.0 (异步)
- **部署**: CloudBase 云托管 (容器化)
- **API 文档**: Swagger UI (/docs) + ReDoc (/redoc)

## 项目结构

```
football-assistant/
├── app/
│   ├── core/           # 核心配置 (config, database, logging)
│   ├── models/         # SQLAlchemy 数据模型
│   ├── schemas/        # Pydantic 请求/响应模型
│   ├── services/       # 业务逻辑层
│   ├── routers/        # API 路由
│   ├── utils/          # 工具函数
│   └── main.py         # FastAPI 入口
├── migrations/         # Alembic 数据库迁移
├── tests/              # 测试用例
├── deployments/        # 部署配置
├── Dockerfile          # 容器镜像
├── docker-compose.yml  # 本地开发环境
├── requirements.txt    # Python 依赖
└── alembic.ini         # Alembic 配置
```

## 快速开始

### 1. 本地开发 (Docker Compose)

```bash
# 启动 PostgreSQL + API 服务
docker-compose up -d

# 访问 API 文档
open http://localhost:8080/docs

# 查看日志
docker-compose logs -f api
```

### 2. 本地开发 (手动)

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库连接信息

# 运行迁移 (首次)
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 3. 运行测试

```bash
pytest tests/ -v
```

## API 接口

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 服务健康状态 |
| GET | `/health/ready` | 就绪探针 |
| GET | `/health/live` | 存活探针 |

### 赛程 (Fixtures)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/fixtures` | 查询赛程列表 (支持筛选) |
| GET | `/api/fixtures/{id}` | 单场比赛详情 (含赔率) |
| POST | `/api/fixtures` | 创建赛程 |
| POST | `/api/fixtures/batch` | 批量创建赛程 |

### 联赛 (Leagues)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/leagues` | 查询联赛列表 |
| GET | `/api/leagues/{id}` | 联赛详情 |
| POST | `/api/leagues` | 创建联赛 |

### 球队 (Teams)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/teams` | 查询球队列表 |
| GET | `/api/teams/{id}` | 球队详情 |
| POST | `/api/teams` | 创建球队 |

### 赔率 (Odds)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/odds/fixture/{id}` | 查询比赛赔率 |
| GET | `/api/odds/recommended/{id}` | AI 推荐赔率 |
| POST | `/api/odds` | 创建/更新赔率 |
| POST | `/api/odds/batch` | 批量创建赔率 |

## 部署到 CloudBase

### 方式一: 云托管 (推荐)

1. 安装 CloudBase CLI:
   ```bash
   npm install -g @cloudbase/cli
   ```

2. 登录并初始化:
   ```bash
   tcb login
   tcb env:list
   ```

3. 配置环境变量:
   ```bash
   # 在 CloudBase 控制台设置环境变量
   DATABASE_URL=postgresql+asyncpg://...
   DATABASE_URL_SYNC=postgresql://...
   CORS_ORIGINS=https://jqhuv828m4q.feishu.cn
   ```

4. 部署:
   ```bash
   # 使用 CloudBase CLI 部署容器
   tcb framework:deploy
   ```

### 方式二: 云函数 (Serverless)

适用于轻量级场景，注意免费版超时限制 3 秒。

1. 安装额外依赖:
   ```bash
   pip install mangum
   ```

2. 打包并部署到 CloudBase 云函数。

## 数据库 Schema

详见 `docs/database_schema.md`

## 注意事项

- CloudBase 免费版每月 3000 资源点，注意监控用量
- 云函数超时 3 秒，复杂查询建议使用云托管
- 数据库连接信息请妥善保管，不要提交到代码仓库
- CORS 已配置允许前端域名 `https://jqhuv828m4q.feishu.cn`

## License

MIT
