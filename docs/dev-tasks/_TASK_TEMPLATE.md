# Task: <任务名称>

## Goal

<用 2-4 句话说明本任务的业务目标和工程目标。>

## Files to Read First

- AGENTS.md
- README.md
- contracts/openapi/ESG_P0_OpenAPI_v0.1.yaml
- db/ddl/ESG_PostgreSQL_DDL_v0.1.sql
- docs/dev-tasks/MVP_BUILD_ORDER.md

## Scope

### Backend

- 

### Frontend

- 

### Database

- 

### AI / Worker

- 

### Tests

- 

## Out of Scope

- 

## Required Behaviors

- 

## Permission and Security Requirements

- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 文件、知识库、AI日志、导出文件必须通过后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。

## Acceptance Criteria

- [ ] 

## Test Commands

```bash
make lint
make test
make test-api
```

## Final Response Requirements for Codex

完成后必须返回：

1. Changed files
2. Implemented behavior
3. Test commands run
4. Test results
5. Known limitations
6. Follow-up tasks
