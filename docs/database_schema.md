# 数据库 Schema 设计说明

## 概述

竞彩足球购买助手后端使用 PostgreSQL 数据库，通过 SQLAlchemy ORM 管理。共包含 4 张核心表，支持赛程查询、赔率分析和投注推荐。

## 表结构

### 1. leagues (联赛表)

存储足球联赛/赛事信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AI | 自增主键 |
| league_id | VARCHAR(50) | UNIQUE, NOT NULL, INDEX | 外部联赛ID |
| name_cn | VARCHAR(100) | NOT NULL | 中文名称 |
| name_en | VARCHAR(100) | NULL | 英文名称 |
| country | VARCHAR(50) | NULL | 所属国家 |
| logo_url | TEXT | NULL | 联赛Logo URL |
| season | VARCHAR(20) | NULL | 当前赛季 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

**索引**: `league_id` (唯一索引)

---

### 2. teams (球队表)

存储足球队信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AI | 自增主键 |
| team_id | VARCHAR(50) | UNIQUE, NOT NULL, INDEX | 外部球队ID |
| name_cn | VARCHAR(100) | NOT NULL | 中文名称 |
| name_en | VARCHAR(100) | NULL | 英文名称 |
| short_name | VARCHAR(50) | NULL | 简称 |
| league_id | INTEGER | FK(leagues.id), NULL, INDEX | 所属联赛 |
| logo_url | TEXT | NULL | 球队Logo URL |
| founded | INTEGER | NULL | 成立年份 |
| stadium | VARCHAR(100) | NULL | 主场 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

**索引**: `team_id` (唯一索引), `league_id` (外键索引)

---

### 3. fixtures (赛程表)

存储比赛/赛程信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AI | 自增主键 |
| fixture_id | VARCHAR(50) | UNIQUE, NOT NULL, INDEX | 外部比赛ID |
| league_id | INTEGER | FK(leagues.id), NOT NULL, INDEX | 所属联赛 |
| home_team_id | INTEGER | FK(teams.id), NOT NULL, INDEX | 主队 |
| away_team_id | INTEGER | FK(teams.id), NOT NULL, INDEX | 客队 |
| match_date | TIMESTAMP | NOT NULL, INDEX | 比赛时间 |
| round_info | VARCHAR(50) | NULL | 轮次/阶段 |
| venue | VARCHAR(100) | NULL | 比赛场地 |
| referee | VARCHAR(100) | NULL | 裁判 |
| status | ENUM | DEFAULT 'SCHEDULED', NOT NULL, INDEX | 状态 |
| status_short | VARCHAR(20) | NULL | 状态短文本 |
| elapsed | INTEGER | NULL | 已进行分钟 |
| home_score | INTEGER | NULL | 主队比分 |
| away_score | INTEGER | NULL | 客队比分 |
| home_halftime_score | INTEGER | NULL | 主队半场比分 |
| away_halftime_score | INTEGER | NULL | 客队半场比分 |
| is_jc | INTEGER | DEFAULT 0, NOT NULL | 是否竞彩 (0/1) |
| jc_issue_no | VARCHAR(20) | NULL | 竞彩期号 |
| is_hot | INTEGER | DEFAULT 0, NOT NULL | 是否热门 (0/1) |
| source | VARCHAR(50) | NULL | 数据来源 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

**状态枚举 (FixtureStatus)**:
- `SCHEDULED` - 未开始
- `LIVE` - 进行中
- `HALFTIME` - 半场休息
- `FINISHED` - 已结束
- `POSTPONED` - 推迟
- `CANCELLED` - 取消
- `SUSPENDED` - 中断

**索引**:
- `fixture_id` (唯一索引)
- `league_id` (外键索引)
- `home_team_id` (外键索引)
- `away_team_id` (外键索引)
- `match_date` (时间索引)
- `status` (状态索引)
- `idx_fixture_date_league` (复合索引: match_date + league_id)
- `idx_fixture_date_status` (复合索引: match_date + status)
- `idx_fixture_jc` (复合索引: is_jc + match_date)

---

### 4. odds (赔率表)

存储各场比赛的投注赔率。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AI | 自增主键 |
| fixture_id | INTEGER | FK(fixtures.id), NOT NULL, INDEX | 所属比赛 |
| odds_type | ENUM | NOT NULL, INDEX | 玩法类型 |
| option_code | VARCHAR(20) | NOT NULL | 选项代码 |
| option_name | VARCHAR(50) | NULL | 选项中文名 |
| odds_value | FLOAT | NOT NULL | 赔率值 |
| handicap | VARCHAR(20) | NULL | 让球值 |
| is_stopped | INTEGER | DEFAULT 0, NOT NULL | 是否停售 (0/1) |
| is_recommended | INTEGER | DEFAULT 0, NOT NULL | AI推荐 (0/1) |
| confidence | FLOAT | NULL | AI置信度 (0-1) |
| source | VARCHAR(50) | NULL | 赔率来源 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

**玩法类型枚举 (OddsType)**:
- `SP_WDW` - 胜平负 (Win/Draw/Loss)
- `SP_HDP` - 让球胜平负 (Handicap)
- `SP_SCORE` - 比分 (Correct Score)
- `SP_TOTAL` - 总进球 (Total Goals)
- `SP_HALF` - 半全场 (Half-time/Full-time)
- `SP_BQ` - 单双 (Odd/Even)

**索引**:
- `fixture_id` (外键索引)
- `odds_type` (类型索引)
- `idx_odds_fixture_type` (复合索引: fixture_id + odds_type)
- `idx_odds_fixture_option` (唯一复合索引: fixture_id + odds_type + option_code)

## ER 关系图

```
leagues (1) ----< (*) teams
  |                  |
  |                  |
  +----< (*) fixtures >----(*) teams (home_team)
  |         |      |
  |         |      +----< (*) teams (away_team)
  |         |
  |         +----< (*) odds
  |
  +----< (*) fixtures
```

## 关系说明

1. **leagues -> teams**: 一个联赛有多个球队 (1:N)
2. **leagues -> fixtures**: 一个联赛有多场比赛 (1:N)
3. **teams -> fixtures (home)**: 一个球队作为主队参加多场比赛 (1:N)
4. **teams -> fixtures (away)**: 一个球队作为客队参加多场比赛 (1:N)
5. **fixtures -> odds**: 一场比赛有多种赔率 (1:N)

## 常用查询示例

### 查询今日竞彩赛程
```sql
SELECT f.*, 
       ht.name_cn as home_team_name, 
       at.name_cn as away_team_name,
       l.name_cn as league_name
FROM fixtures f
JOIN teams ht ON f.home_team_id = ht.id
JOIN teams at ON f.away_team_id = at.id
JOIN leagues l ON f.league_id = l.id
WHERE f.is_jc = 1
  AND f.match_date >= CURRENT_DATE
  AND f.match_date < CURRENT_DATE + INTERVAL '1 day'
ORDER BY f.match_date;
```

### 查询某场比赛的所有赔率
```sql
SELECT o.*, f.fixture_id
FROM odds o
JOIN fixtures f ON o.fixture_id = f.id
WHERE f.id = ?
ORDER BY o.odds_type, o.odds_value;
```

### 查询热门比赛
```sql
SELECT f.*, ht.name_cn as home, at.name_cn as away
FROM fixtures f
JOIN teams ht ON f.home_team_id = ht.id
JOIN teams at ON f.away_team_id = at.id
WHERE f.is_hot = 1
  AND f.match_date >= CURRENT_DATE
ORDER BY f.match_date
LIMIT 20;
```
