# Task 000: Sprint 0 工程启动与仓库骨架

## 1. Goal

初始化 ESG报告软件 MVP 代码仓库，使 Codex 和开发团队可以在统一工程结构下开始开发。

本任务只做工程骨架、开发环境、基础依赖、文档放置、健康检查和CI基础检查，不实现完整业务功能。

---

## 2. Files to Read First

Codex开始前必须阅读：

1. `AGENTS.md`
2. `README.md`
3. `docs/architecture/TECH_STACK_DECISION.md`
4. `docs/dev-tasks/MVP_BUILD_ORDER.md`
5. `contracts/openapi/ESG_P0_OpenAPI_v0.1.yaml`，如果已存在
6. `db/ddl/ESG_PostgreSQL_DDL_v0.1.sql`，如果已存在
7. `db/seed/ESG_PostgreSQL_Seed_Data_v0.1.sql`，如果已存在

---

## 3. Scope

本任务范围：

1. 创建推荐目录结构；
2. 添加 `.env.example`；
3. 添加 `docker-compose.dev.yml`；
4. 添加 `Makefile`；
5. 初始化 `apps/api` FastAPI基础服务；
6. 初始化 `apps/web` React + Vite基础服务；
7. 初始化 `apps/worker` 基础Worker占位；
8. 初始化 `apps/ai-gateway` Mock AI占位；
9. 放置 OpenAPI、DDL、Seed Data、Mock Data 目录；
10. 添加健康检查接口；
11. 添加基础CI配置；
12. 添加基础测试占位。

---

## 4. Out of Scope

本任务不做：

1. 完整登录注册；
2. 业务模块CRUD；
3. AI真实模型接入；
4. 文档解析；
5. 报告导出；
6. 完整权限系统；
7. 前端业务页面；
8. 生产部署配置；
9. 高级安全扫描；
10. 客户演示数据。

---

## 5. Required Directory Structure

应创建或确认以下目录：

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

## 6. Required Root Files

必须创建或确认：

```text
README.md
AGENTS.md
.env.example
docker-compose.dev.yml
Makefile
.gitignore
VERSION
```

---

## 7. .env.example Requirements

`.env.example` 至少包含：

```bash
APP_ENV=local
APP_PORT=8080
WEB_PORT=3000
DATABASE_URL=postgresql://esg_user:esg_password@localhost:5432/esg_dev
POSTGRES_DB=esg_dev
POSTGRES_USER=esg_user
POSTGRES_PASSWORD=esg_password
REDIS_URL=redis://localhost:6379/0
OBJECT_STORAGE_ENDPOINT=http://localhost:9000
OBJECT_STORAGE_ACCESS_KEY=minioadmin
OBJECT_STORAGE_SECRET_KEY=minioadmin
OBJECT_STORAGE_BUCKET_FILES=esg-files
OBJECT_STORAGE_BUCKET_EXPORTS=esg-exports
OBJECT_STORAGE_BUCKET_TEMP=esg-temp
JWT_SECRET=local_dev_jwt_secret_change_me
AI_PROVIDER=mock
AI_API_BASE_URL=http://localhost:9002
AI_API_KEY=local_mock_key
LOG_LEVEL=DEBUG
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

---

## 8. docker-compose.dev.yml Requirements

必须包含：

1. PostgreSQL 15+；
2. Redis；
3. MinIO；
4. 必要的数据卷；
5. 合理的本地端口映射。

推荐端口：

| 服务 | 端口 |
|---|---:|
| PostgreSQL | 5432 |
| Redis | 6379 |
| MinIO API | 9000 |
| MinIO Console | 9001 |

---

## 9. Makefile Requirements

至少提供：

```bash
make install
make dev-up
make dev-down
make web
make api
make worker
make ai-gateway
make migrate
make seed
make db-reset
make storage-init
make lint
make typecheck
make test
make test-api
make test-e2e
make schema-check
make openapi-check
```

如果某些命令暂未实现，应提供明确占位，不得静默成功掩盖问题。

---

## 10. Backend Health Check

后端必须提供：

```http
GET /health
```

预期响应：

```json
{
  "success": true,
  "data": {
    "status": "ok"
  },
  "message": "ok",
  "request_id": "req_xxx"
}
```

---

## 11. Frontend Bootstrap

前端必须至少能：

1. 启动开发服务；
2. 显示项目名称；
3. 调用 `/health` 或显示API连接状态；
4. 保留后续路由目录。

首页可显示：

```text
ESG Report Platform
API Status: OK / Failed
```

---

## 12. Worker Bootstrap

Worker必须至少能启动，并提供一个ping任务或占位任务。

要求：

1. 能连接Redis；
2. 能打印启动日志；
3. 任务日志包含 `job_id`；
4. 后续可扩展文档解析、AI写作、导出任务。

---

## 13. AI Gateway Bootstrap

AI Gateway MVP可以是Mock服务。

必须提供：

```http
POST /mock/chat
```

输入：

```json
{
  "agent_type": "ping",
  "input": "hello"
}
```

输出：

```json
{
  "output": "ok",
  "model": "mock-model",
  "usage": {
    "input_tokens": 1,
    "output_tokens": 1
  }
}
```

---

## 14. CI Requirements

基础CI至少检查：

1. Python lint 或占位；
2. 前端lint 或占位；
3. OpenAPI格式校验；
4. JSON Schema校验；
5. 单元测试占位；
6. 密钥扫描占位或配置。

CI文件建议位置：

```text
.github/workflows/ci.yml
```

---

## 15. Acceptance Criteria

本任务完成后必须满足：

1. 仓库目录结构存在；
2. `.env.example` 存在；
3. `docker-compose.dev.yml` 存在；
4. `make dev-up` 可启动 PostgreSQL、Redis、MinIO；
5. `make api` 可启动后端；
6. `GET /health` 返回成功；
7. `make web` 可启动前端；
8. `make worker` 可启动Worker或占位Worker；
9. `make ai-gateway` 可启动Mock AI或占位AI服务；
10. `make openapi-check` 可执行；
11. `make schema-check` 可执行；
12. 不提交任何真实密钥；
13. README中的启动步骤与实际命令一致。

---

## 16. Test Commands

Codex完成后应运行：

```bash
make dev-up
make api
make web
make worker
make ai-gateway
make openapi-check
make schema-check
make test
```

如果某条命令无法运行，必须在回复中说明原因。

---

## 17. Expected Final Response from Codex

完成任务后，Codex必须回复：

```text
## Changed Files
- ...

## Implementation Summary
- ...

## Tests Run
- make dev-up: pass/fail
- make api: pass/fail
- make web: pass/fail
- make openapi-check: pass/fail

## Not Completed
- ...

## Risks / Notes
- ...
```
