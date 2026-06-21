# Task: 同行报告上传与解析任务模块

## Goal

实现同行ESG报告上传、文件存储、解析任务创建、异步任务状态查询、AI解析结果候选表写入和人工审核入口。MVP可以先使用Mock解析或简单文本解析。

## Files to Read First

- AGENTS.md
- README.md
- docs/architecture/TECH_STACK_DECISION.md
- docs/dev-tasks/MVP_BUILD_ORDER.md
- contracts/openapi/ESG_P0_OpenAPI_v0.1.yaml
- db/ddl/ESG_PostgreSQL_DDL_v0.1.sql
- db/seed/ESG_PostgreSQL_Seed_Data_v0.1.sql


## Scope

### Backend
- 实现同行报告上传接口。
- 实现文件对象 file_objects 记录。
- 实现 peer_report_files 记录。
- 实现解析任务 async_jobs 创建。
- 实现解析状态查询。
- 实现解析结果列表和审核接口。

### Worker / AI
- 实现 peer_report_parse job 框架。
- 先支持Mock AI输出或文本PDF占位解析。
- 写入 report_extracted_standards/topics/metrics/cases 候选结果。
- AI输出必须走Schema校验。

### Frontend
- 同行报告上传页。
- 解析任务进度展示。
- 解析结果人工审核页。

### Tests
- 文件上传。
- 文件类型限制。
- 任务创建。
- Worker执行。
- Schema失败不入正式候选结果。

## Out of Scope

- 不要求复杂OCR。
- 不要求全量PDF高精度解析。
- 不实现交易所网站自动抓取。

## Required Behaviors

- 文件必须绑定tenant_id、enterprise_id、project_id。
- 文件下载必须鉴权。
- 扫描PDF需返回清晰错误或提示。
- 解析结果必须人工审核后才能纳入推荐统计。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 可上传同行报告文件。
- [ ] 可创建解析任务并查询状态。
- [ ] Worker可执行解析任务。
- [ ] 解析结果可审核。
- [ ] 未审核结果不进入推荐统计。
- [ ] 文件越权访问被拒绝。

## Test Commands

```bash
make lint
make typecheck
make test
make test-api
```

若涉及前端页面，额外运行：

```bash
make test-e2e
```

## Final Response Requirements for Codex

完成后必须返回：

1. Changed files
2. Implemented behavior
3. Test commands run
4. Test results
5. Known limitations
6. Follow-up tasks
