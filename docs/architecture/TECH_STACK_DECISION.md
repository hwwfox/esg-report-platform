# ESG报告软件 技术栈决策 v0.1

## 1. 文档目标

本文档用于锁定 ESG报告软件 MVP 阶段的默认技术栈，避免 Codex 或开发人员在实现过程中自行选择框架、目录、测试工具和中间件。

本技术栈优先考虑：

1. MVP开发速度；
2. AI工程适配；
3. 文档解析和Office导出能力；
4. 多租户业务系统可维护性；
5. 私有化部署可行性；
6. Codex代码生成友好度。

---

## 2. 总体技术路线

MVP采用：

```text
React + TypeScript 前端
FastAPI + Python 后端
PostgreSQL 主数据库
Redis 队列和缓存
MinIO/S3 对象存储
Python Worker 处理AI、解析、导出任务
OpenAPI 作为前后端契约
Docker Compose 本地开发
GitHub Actions CI
```

选择 Python 后端的主要原因：

1. AI Agent、文档解析、JSON Schema校验、Excel/Word导出生态成熟；
2. ESG报告软件中AI任务、解析任务、导出任务比传统CRUD更重；
3. FastAPI对OpenAPI和类型提示支持较好；
4. 便于快速实现Worker和AI评估脚本；
5. Codex对Python/FastAPI代码生成和测试补全较稳定。

---

## 3. 前端技术栈

| 项目 | 决策 |
|---|---|
| 框架 | React |
| 构建工具 | Vite |
| 语言 | TypeScript |
| UI组件 | Ant Design |
| 请求管理 | TanStack Query |
| 本地状态 | Zustand |
| 表单 | React Hook Form 或 Ant Design Form，MVP优先AntD Form |
| 路由 | React Router |
| 图表 | ECharts 或 Recharts，MVP优先ECharts |
| E2E | Playwright |
| 单元测试 | Vitest |

### 前端目录建议

```text
apps/web/src/
  app/
    router/
    layout/
    providers/
  pages/
  components/
    common/
    business/
    ai/
    forms/
    tables/
  services/
    api/
    generated/
    mock/
  stores/
  constants/
  utils/
  types/
```

### 前端规则

1. API类型从OpenAPI生成；
2. 页面不直接拼复杂业务规则；
3. 枚举和UI文案集中管理；
4. 权限判断前端仅控制展示，后端必须强校验；
5. 表格列配置尽量模块化；
6. AI输出、来源引用、校对问题必须有明确状态展示。

---

## 4. 后端技术栈

| 项目 | 决策 |
|---|---|
| 框架 | FastAPI |
| 语言 | Python 3.11+ |
| ORM | SQLAlchemy 2.x |
| Migration | Alembic |
| 数据校验 | Pydantic v2 |
| API文档 | OpenAPI 3.0 |
| 鉴权 | JWT，后续可扩展OIDC/SAML |
| 权限 | RBAC + 资源范围校验 |
| 日志 | structlog 或标准logging JSON化 |
| 测试 | pytest + httpx |

### 后端目录建议

```text
apps/api/app/
  main.py
  core/
    config.py
    security.py
    logging.py
    errors.py
  middleware/
    request_id.py
    auth.py
    tenant_context.py
  modules/
    auth/
    tenant/
    enterprise/
    project/
    org/
    standard/
    peer/
    recommendation/
    collection/
    knowledge/
    report/
    ai/
    export/
    audit/
  db/
    session.py
    models/
    repositories/
  schemas/
  tests/
```

### 后端规则

1. Controller负责请求解析；
2. Service负责业务流程、权限、状态机；
3. Repository负责数据库访问；
4. 所有Repository默认带tenant_id；
5. 所有接口返回统一响应结构；
6. 所有错误返回稳定错误码；
7. 所有关键操作写审计日志。

---

## 5. Worker技术栈

| 项目 | 决策 |
|---|---|
| Worker框架 | Celery 或 RQ，MVP优先RQ简化 |
| Broker | Redis |
| 任务状态 | async_jobs表为准 |
| 任务类型 | 文档解析、AI解析、推荐、知识库索引、章节写作、校对、导出 |
| 重试 | 按错误码判断是否可重试 |
| 日志 | job_id + request_id + tenant_id + project_id |

### Worker目录建议

```text
apps/worker/app/
  main.py
  queues/
  jobs/
    parse_peer_report.py
    generate_recommendation.py
    build_material_package.py
    generate_chapter.py
    rebuild_citations.py
    review_chapter.py
    export_report.py
  services/
  common/
```

---

## 6. 数据库技术栈

| 项目 | 决策 |
|---|---|
| 数据库 | PostgreSQL 15+ |
| UUID | gen_random_uuid() |
| JSON扩展 | jsonb |
| 全文检索 | PostgreSQL全文检索，后续可接Elasticsearch |
| 向量检索 | MVP可jsonb占位，生产建议pgvector或独立向量库 |
| Migration | Alembic |
| Seed Data | SQL或Python脚本，MVP优先SQL |

### 数据库规则

1. 所有业务表保留tenant_id；
2. 项目级表保留enterprise_id和project_id；
3. AI输出与正式业务结果分离；
4. 文件统一写入file_objects；
5. 来源引用统一写入source_references；
6. 审计日志不可随意删除。

---

## 7. 对象存储

| 项目 | 决策 |
|---|---|
| 本地 | MinIO |
| 生产 | S3兼容对象存储 |
| Bucket | esg-files、esg-exports、esg-temp |
| 下载方式 | 后端鉴权后生成短期URL或流式下载 |

文件元数据必须写入 `file_objects`。

---

## 8. AI技术栈

| 项目 | 决策 |
|---|---|
| 本地开发 | Mock AI Provider |
| 真实模型 | 通过AI Gateway适配 |
| Prompt | Markdown文件版本化 |
| Schema | JSON Schema |
| 日志 | ai_call_logs |
| 输出记录 | ai_output_records |
| 评估 | pytest或独立Python脚本 |

AI Agent类型：

1. gics_identification；
2. standard_identification；
3. topic_extraction；
4. metric_extraction；
5. topic_mapping；
6. recommendation_reasoning；
7. material_package_builder；
8. chapter_writing；
9. citation_matching；
10. chapter_review；
11. full_report_review；
12. interview_summary。

---

## 9. 文档导出技术栈

| 导出物 | 技术建议 |
|---|---|
| Word | python-docx 或 docxtpl |
| Excel | openpyxl |
| PDF | LibreOffice headless 转换 |
| ZIP | Python zipfile |

MVP优先级：

1. Excel ESG数据表；
2. Word报告初稿；
3. 来源引用表Excel；
4. AI校对问题表Excel；
5. PDF转换；
6. ZIP导出包。

---

## 10. 测试技术栈

| 类型 | 工具 |
|---|---|
| 后端单元测试 | pytest |
| API测试 | pytest + httpx |
| 前端单元测试 | Vitest |
| E2E测试 | Playwright |
| Schema测试 | jsonschema |
| OpenAPI校验 | spectral 或 openapi-spec-validator |
| 安全测试 | pytest + 手工检查表 |

---

## 11. CI/CD技术栈

| 项目 | 决策 |
|---|---|
| CI | GitHub Actions |
| 本地容器 | Docker Compose |
| 镜像 | Docker |
| 部署 | MVP可Docker Compose，生产建议Kubernetes |

CI必须检查：

1. lint；
2. typecheck；
3. unit tests；
4. API tests；
5. OpenAPI validity；
6. JSON Schema validity；
7. migration check；
8. secret scan。

---

## 12. 后续可重新评估的技术点

| 技术点 | 当前决策 | 后续评估条件 |
|---|---|---|
| 后端框架 | FastAPI | 如果客户强Java生态，可评估Spring Boot |
| Worker | RQ/Celery | 任务复杂后倾向Celery |
| 向量库 | jsonb占位 | 进入生产知识库后使用pgvector或Milvus |
| PDF | LibreOffice | 复杂排版后评估专业服务 |
| SSO | JWT预留 | 企业版接OIDC/SAML |
| 私有模型 | AI Gateway预留 | 客户要求私有部署时接入 |
