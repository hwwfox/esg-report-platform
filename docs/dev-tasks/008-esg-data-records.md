# Task: ESG正式数据表模块

## Goal

将审核通过的采集提交转化为正式 ESG 数据记录，支持查询、筛选、来源追溯、报告引用状态更新和Excel导出基础数据。

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
- 审核通过后写入 esg_data_records。
- 实现ESG数据列表、筛选、详情接口。
- 实现按议题、指标、部门、期间查询。
- 记录 source_task_id、source_submission_id、source_file_ids。
- 实现报告引用状态更新接口或服务。

### Frontend
- ESG数据表页面。
- 筛选条件：议题、指标、部门、期间、审核状态。
- 数据详情和来源查看。

### Tests
- 审核通过后生成数据记录。
- 退回任务不生成数据记录。
- 来源字段完整。
- 无权限不能查看其他项目数据。

## Out of Scope

- 不实现高级BI图表。
- 不实现跨年度复杂同比分析。
- 不实现第三方鉴证流程。

## Required Behaviors

- esg_data_records 只能来自已审核通过数据。
- source_* 字段必须可追溯。
- 数据被报告引用后修改需有审计或限制。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 审核通过数据进入 esg_data_records。
- [ ] 可按项目查询ESG数据。
- [ ] 可查看来源任务和来源文件。
- [ ] 权限校验通过。
- [ ] 基础导出数据准备就绪。

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
