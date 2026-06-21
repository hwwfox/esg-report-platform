# Task: 标准库、议题库与指标库模块

## Goal

实现标准、标准版本、条款、ESG议题、ESG指标以及标准-议题-指标映射的基础CRUD和查询能力。该模块为推荐、采集、写作和披露检查提供基础数据。

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
- 实现标准列表、详情、版本、条款查询。
- 实现议题列表、详情查询。
- 实现指标列表、详情查询。
- 实现标准-议题、议题-指标、条款-指标映射查询。
- 实现标准库导入任务的接口占位或基础导入。

### Frontend
- 标准库列表页。
- 标准详情页。
- 议题库列表页。
- 指标库列表页。
- 映射关系查看页。

### Database
- 使用 esg_standards、standard_versions、standard_clauses、esg_topics、esg_metrics 等基础库表。

### Tests
- 查询标准。
- 查询标准条款。
- 查询议题指标映射。
- 标准库权限校验。

## Out of Scope

- 不实现完整标准在线编辑审批流。
- 不实现复杂版本diff。
- 不实现监管标准自动更新。

## Required Behaviors

- 公共标准和租户私有标准必须区分。
- 项目锁定后的标准快照不能因基础库修改自动变化。
- 标准库管理权限必须受控。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 标准、条款、议题、指标可以查询。
- [ ] 映射关系可以查询。
- [ ] 前端可展示基础库数据。
- [ ] 租户私有标准不会被其他租户访问。
- [ ] `make test-api` 通过。

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
