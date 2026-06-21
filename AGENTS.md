# AGENTS.md

# ESG报告软件 Codex开发规则 v0.1

本文件是 Codex 或其他代码代理在本仓库中工作的最高优先级工程说明。任何开发任务开始前，必须先阅读本文件、README.md、OpenAPI契约、数据库DDL和当前任务卡。

---

## 1. 项目定位

本项目是 ESG 报告智能编制与披露管理平台。系统围绕“标准库 + 同行库 + 企业知识库 + AI Agent + 人工审核”支撑 ESG 报告编制全流程。

核心流程：

```text
创建企业与报告项目
→ 识别GICS行业
→ 推荐同行企业
→ 上传并解析同行ESG报告
→ 人工审核AI解析结果
→ 推荐标准、议题、指标
→ 用户确认项目标准/议题/指标
→ 分配部门采集任务
→ 部门提交文字、数据、文件、访谈材料
→ 审核通过形成ESG数据表和知识库
→ AI生成章节草稿
→ 来源引用匹配
→ AI校对
→ 用户确认章节
→ 全文校对
→ 导出Word/PDF/Excel
```

---

## 2. 当前MVP边界

MVP优先实现以下能力：

1. 租户、企业、用户、角色、项目；
2. ESG标准库、议题库、指标库；
3. GICS行业识别与同行公司池；
4. 同行报告上传与异步解析任务框架；
5. AI解析结果候选表与人工审核；
6. 标准/议题/指标推荐；
7. 部门采集任务、提交、审核；
8. ESG数据表；
9. 知识库文件和切片；
10. 报告章节、材料包、AI写作、来源引用、AI校对；
11. Word、Excel导出；
12. 审计日志、错误码、权限校验。

暂不优先实现：

1. 复杂扫描PDF OCR高精度解析；
2. 交易所网站自动爬取；
3. XBRL或监管机读格式；
4. 完整信创适配；
5. 高级排版级PDF；
6. 生产级多区域高可用；
7. 自动替代人工发布正式报告。

---

## 3. 仓库结构约定

建议使用 Monorepo：

```text
apps/
  web/              # 前端Web应用
  api/              # 后端API服务
  worker/           # 异步任务Worker
  ai-gateway/       # AI模型网关或Mock AI服务

contracts/
  openapi/          # OpenAPI契约
  schemas/          # JSON Schema、AI输出Schema
  mock-data/        # 接口Mock数据

db/
  migrations/       # 数据库迁移脚本
  seed/             # 种子数据
  ddl/              # DDL快照

ai/
  prompts/          # Prompt模板
  schemas/          # AI输出Schema
  eval/             # AI评估脚本
  samples/          # AI样本

docs/
  architecture/     # 架构和技术决策
  dev-tasks/        # Codex任务卡
  product/          # 产品文档
  api/              # API文档
  test/             # 测试文档
  devops/           # 部署文档

codex-prompts/      # 给Codex的可执行Prompt

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

## 4. 工作前必须阅读的文件

每次任务开始前，Codex 必须按顺序阅读：

1. `AGENTS.md`
2. `README.md`
3. `docs/architecture/TECH_STACK_DECISION.md`
4. `docs/dev-tasks/MVP_BUILD_ORDER.md`
5. 当前任务卡，例如 `docs/dev-tasks/000-sprint-0-bootstrap.md`
6. 如涉及接口，阅读 `contracts/openapi/ESG_P0_OpenAPI_v0.1.yaml`
7. 如涉及数据库，阅读 `db/ddl/ESG_PostgreSQL_DDL_v0.1.sql`
8. 如涉及AI输出，阅读 `contracts/schemas/` 和 `ai/prompts/`

---

## 5. 开发硬约束

### 5.1 多租户和权限

严禁绕过以下权限边界：

1. 所有业务查询必须校验 `tenant_id`；
2. 企业级数据必须校验 `enterprise_id`；
3. 项目级数据必须校验 `project_id`；
4. 部门级数据必须校验 `org_unit_id` 或任务分配关系；
5. 文件下载必须经过后端鉴权；
6. 前端隐藏按钮不是权限控制，后端必须强校验；
7. 跨租户访问不得泄露资源是否存在；
8. 权限拒绝必须记录安全日志或审计日志。

不得出现：

```text
where id = :id
```

必须包含租户/项目上下文，例如：

```text
where tenant_id = :tenant_id and project_id = :project_id and id = :id
```

---

### 5.2 AI输出规则

1. AI输出必须先写入 `ai_output_records` 或候选表；
2. AI输出必须通过 JSON Schema 校验；
3. AI输出不得直接写入正式业务表；
4. AI解析结果必须经过人工审核后才能进入统计；
5. AI不得编造同行采用率、样本数、公司数量等确定性统计；
6. 推荐采用率必须由系统基于已审核数据计算；
7. AI写作必须基于已确认材料包；
8. 无来源事实必须标记为 `source_missing`；
9. 同行案例只能作为参考，不得写成本企业事实；
10. Prompt修改必须保留版本，不得覆盖旧版本。

---

### 5.3 数据库规则

1. 不得直接手工修改数据库结构而不提交 migration；
2. 所有结构变更必须放入 `db/migrations/`；
3. 初始DDL快照放入 `db/ddl/`；
4. 种子数据放入 `db/seed/`；
5. 演示数据不得混入生产种子数据；
6. 删除字段必须谨慎，优先废弃不用；
7. 新增非空字段必须考虑历史数据默认值；
8. migration 必须可在干净数据库上执行；
9. migration 失败不得留下半完成状态；
10. 每个 migration 文件必须有明确编号和说明。

---

### 5.4 OpenAPI规则

1. 后端接口必须遵守 OpenAPI 契约；
2. 修改接口必须同步更新 OpenAPI；
3. 修改 OpenAPI 必须同步更新 Mock 数据；
4. 前端接口类型应从 OpenAPI 生成；
5. 不允许前端猜字段；
6. 不允许同一字段在不同接口命名不一致；
7. 所有接口响应必须包含 `request_id`；
8. 错误响应必须包含稳定的 `error.code`。

---

### 5.5 文件与对象存储规则

1. 文件必须写入 `file_objects`；
2. 文件必须绑定 `tenant_id`；
3. 项目文件必须绑定 `enterprise_id` 和 `project_id`；
4. 不得向前端返回永久对象存储URL；
5. 下载必须通过后端生成短期授权链接或受控流式下载；
6. 文件上传必须校验大小、MIME类型、业务类型；
7. 文件操作必须写审计日志；
8. 不得提交真实客户文件到仓库。

---

### 5.6 日志与敏感信息

日志中不得打印：

1. API Key；
2. Token；
3. 密码或密码哈希；
4. 完整客户敏感原文；
5. 数据库连接串；
6. 对象存储Secret；
7. 服务器真实路径；
8. 第三方供应商完整错误响应。

日志应包含：

1. `request_id`；
2. `tenant_id`；
3. `enterprise_id`；
4. `project_id`；
5. `user_id`；
6. `job_id`；
7. `agent_type`；
8. `duration_ms`；
9. `error_code`。

---

## 6. 代码风格要求

### 6.1 前端

1. 使用 TypeScript；
2. 避免 `any`；
3. 页面、业务组件、基础组件分层；
4. 接口类型从 OpenAPI 生成；
5. UI文案和状态枚举集中管理；
6. 权限仅用于前端展示控制，真实权限以后端为准；
7. 表格、表单、状态标签必须统一组件化。

### 6.2 后端

1. 使用清晰分层：Router/Controller、Service、Repository、Domain；
2. 所有接口使用统一响应结构；
3. 所有接口必须带 request_id；
4. 业务异常使用统一错误码；
5. Repository 默认要求 tenant_id；
6. Service 层负责权限和状态机；
7. 异步任务必须幂等；
8. 关键操作必须写审计日志。

### 6.3 Worker

1. 任务必须可重试；
2. 任务必须记录状态、进度、错误；
3. 任务日志必须包含 job_id；
4. AI任务必须记录 prompt_version、schema_version、model_name；
5. 任务失败必须写入 `async_jobs.error_payload`。

---

## 7. 测试要求

提交前至少运行与变更相关的测试：

```bash
make lint
make typecheck
make test
make test-api
make schema-check
make openapi-check
```

如果改动前端页面，还应运行：

```bash
make test-e2e
```

如果改动数据库：

```bash
make migrate
make seed
```

如果改动AI输出：

```bash
make schema-check
make ai-eval-smoke
```

---

## 8. PR输出要求

Codex完成任务后，回复必须包含：

1. 修改文件列表；
2. 关键实现摘要；
3. 已运行的测试命令；
4. 测试结果；
5. 未完成事项；
6. 风险说明；
7. 是否修改 OpenAPI、DDL、Prompt、Schema、Mock。

---

## 9. 禁止事项

严禁：

1. 直接修改 `main` 分支；
2. 提交 `.env` 或任何密钥；
3. 提交真实客户数据；
4. 绕过权限校验；
5. 跳过 AI Schema 校验；
6. AI输出直接入正式表；
7. 后端私自改字段不更新 OpenAPI；
8. 修改数据库不提交 migration；
9. 删除重要业务字段而不做兼容；
10. 文件下载绕过后端鉴权；
11. 在日志中输出敏感信息；
12. 为了让测试通过而删除测试或降低安全校验。

---

## 10. 不确定时的处理方式

如果任务存在不确定项，Codex 应：

1. 优先查看文档和现有代码；
2. 不擅自扩大范围；
3. 保持最小可用改动；
4. 在回复中列出假设；
5. 对高风险改动给出待确认事项；
6. 不凭空引入大型依赖；
7. 不改变既定技术栈。
