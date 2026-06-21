# ESG Report Platform

ESG报告智能编制与披露管理平台。

本仓库用于开发一个面向上市公司、集团企业、ESG咨询机构和审计/鉴证机构的 ESG 报告软件。系统通过标准库、同行库、企业知识库、AI Agent 和人工审核机制，支撑 ESG 报告从同行分析、议题推荐、部门采集、知识库沉淀、AI写作、来源追溯、AI校对到 Word/PDF/Excel 导出的完整流程。

---

## 1. 文档入口

开发前请按顺序阅读：

1. `AGENTS.md`：Codex与开发代理工作规则；
2. `docs/architecture/TECH_STACK_DECISION.md`：技术栈决策；
3. `docs/dev-tasks/MVP_BUILD_ORDER.md`：MVP开发顺序；
4. 当前任务卡：`docs/dev-tasks/*.md`；
5. `contracts/openapi/ESG_P0_OpenAPI_v0.1.yaml`：接口契约；
6. `db/ddl/ESG_PostgreSQL_DDL_v0.1.sql`：数据库DDL；
7. `db/seed/ESG_PostgreSQL_Seed_Data_v0.1.sql`：种子数据。

---

## 2. 推荐目录结构

```text
apps/
  web/
  api/
  worker/
  ai-gateway/

contracts/
  openapi/
  schemas/
  mock-data/

db/
  ddl/
  migrations/
  seed/

ai/
  prompts/
  schemas/
  eval/
  samples/

docs/
  architecture/
  dev-tasks/
  product/
  api/
  test/
  devops/

codex-prompts/

tests/
  api/
  e2e/
  acceptance/

deploy/
  compose/
  docker/
  scripts/
```

---

## 3. 技术栈摘要

默认MVP技术栈：

| 层 | 技术 |
|---|---|
| 前端 | React + Vite + TypeScript |
| UI | Ant Design 或企业级组件库 |
| 状态/请求 | TanStack Query + Zustand |
| 后端API | FastAPI + Python 3.11 |
| Worker | Celery 或 RQ，基于 Redis |
| 数据库 | PostgreSQL 15+ |
| 对象存储 | MinIO / S3 |
| AI网关 | Python服务或API内模块，支持Mock和真实Provider |
| 文档导出 | python-docx / openpyxl / LibreOffice转换PDF |
| API契约 | OpenAPI 3.0 |
| E2E测试 | Playwright |
| CI | GitHub Actions |

详细说明见 `docs/architecture/TECH_STACK_DECISION.md`。

---

## 4. 本地启动

### 4.1 复制环境变量

```bash
cp .env.example .env
```

### 4.2 启动依赖服务

```bash
make dev-up
```

等价服务：

```text
PostgreSQL
Redis
MinIO
```

### 4.3 初始化对象存储

```bash
make storage-init
```

### 4.4 数据库迁移和种子数据

```bash
make migrate
make seed
```

### 4.5 启动后端API

```bash
make api
```

健康检查：

```bash
curl http://localhost:8080/health
```

### 4.6 启动Worker

```bash
make worker
```

### 4.7 启动前端

```bash
make web
```

访问：

```text
http://localhost:3000
```

---

## 5. 常用命令

```bash
make install           # 安装依赖
make dev-up            # 启动PostgreSQL/Redis/MinIO
make dev-down          # 停止依赖服务
make web               # 启动前端
make api               # 启动后端API
make worker            # 启动Worker
make ai-gateway        # 启动AI网关或Mock AI
make mock-server       # 启动Mock接口服务
make migrate           # 执行数据库迁移
make seed              # 导入种子数据
make db-reset          # 重置本地数据库
make storage-init      # 初始化MinIO Bucket
make lint              # 代码检查
make typecheck         # 类型检查
make test              # 单元测试
make test-api          # API测试
make test-e2e          # E2E测试
make schema-check      # JSON Schema校验
make openapi-check     # OpenAPI校验
make openapi-generate  # 生成前端接口类型
```

---

## 6. 环境变量

本地 `.env` 示例：

```bash
APP_ENV=local
APP_PORT=8080
WEB_PORT=3000
DATABASE_URL=postgresql://esg_user:esg_password@localhost:5432/esg_dev
REDIS_URL=redis://localhost:6379/0
OBJECT_STORAGE_ENDPOINT=http://localhost:9000
OBJECT_STORAGE_ACCESS_KEY=minioadmin
OBJECT_STORAGE_SECRET_KEY=minioadmin
OBJECT_STORAGE_BUCKET_FILES=esg-files
OBJECT_STORAGE_BUCKET_EXPORTS=esg-exports
JWT_SECRET=local_dev_jwt_secret_change_me
AI_PROVIDER=mock
AI_API_BASE_URL=http://localhost:9002
AI_API_KEY=local_mock_key
LOG_LEVEL=DEBUG
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

不得提交 `.env`、密钥、Token、真实客户数据。

---

## 7. API契约

OpenAPI文件位置：

```text
contracts/openapi/ESG_P0_OpenAPI_v0.1.yaml
```

接口变更规则：

1. 先改 OpenAPI；
2. 更新 Mock 数据；
3. 后端实现；
4. 前端重新生成类型；
5. 更新测试。

---

## 8. 数据库

DDL快照：

```text
db/ddl/ESG_PostgreSQL_DDL_v0.1.sql
```

Migration目录：

```text
db/migrations/
```

Seed Data目录：

```text
db/seed/
```

Migration命名示例：

```text
V001__init_schema.sql
V002__add_ai_call_logs.sql
V003__add_knowledge_chunks.sql
```

---

## 9. 多租户与权限

所有业务数据必须至少按以下字段隔离：

```text
tenant_id
enterprise_id
project_id
```

后端必须强制校验权限。前端只做展示控制，不作为真实权限判断依据。

---

## 10. AI开发规则

1. AI输出必须通过 Schema 校验；
2. AI输出先进入候选记录，不直接进入正式业务表；
3. Prompt必须版本化；
4. AI调用必须写日志和成本；
5. 推荐采用率必须由系统计算；
6. 无来源事实必须标记；
7. 同行案例不能写成本企业事实。

---

## 11. 测试要求

每个PR至少说明：

```text
已运行的测试命令：
测试结果：
未运行原因：
```

建议提交前运行：

```bash
make lint
make typecheck
make test
make test-api
make schema-check
make openapi-check
```

---

## 12. Codex工作方式

给Codex执行任务时，应使用 `codex-prompts/` 中的Prompt，并指定任务卡。

示例：

```text
Read AGENTS.md first.
Then read docs/dev-tasks/000-sprint-0-bootstrap.md.
Implement only the requested scope.
Run the listed test commands.
Return changed files and test results.
```
