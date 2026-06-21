# Task: 部门采集任务与审核模块

## Goal

实现项目议题分配、部门采集任务生成、采集员填报、附件上传、数据校验、审核员审核、退回和通过流程。

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
- 实现议题分配接口。
- 生成 collection_tasks。
- 实现采集任务列表、详情、提交。
- 实现 task_submission_items 保存。
- 实现审核通过/退回。
- 实现数据质量校验规则。

### Frontend
- 项目议题分配页。
- 部门采集任务列表。
- 采集表单。
- 审核页面。
- 校验问题提示。

### Database
- 使用 project_topic_assignments、collection_tasks、task_submissions、task_submission_items、task_reviews。

### Tests
- 生成采集任务。
- 必填指标缺失阻断。
- 证据缺失阻断或警告。
- 审核通过。
- 审核退回。

## Out of Scope

- 不实现复杂工作流引擎。
- 不实现移动端采集。
- 不实现自动从ERP/EHS拉取数据。

## Required Behaviors

- 采集员只能访问自己的任务或部门授权任务。
- 审核员不能越权审核其他部门任务。
- 审核通过前不得进入 ESG正式数据表。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 项目负责人可分配议题。
- [ ] 采集员可提交数据和附件。
- [ ] 审核员可通过或退回。
- [ ] 校验规则生效。
- [ ] 权限隔离通过测试。

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
