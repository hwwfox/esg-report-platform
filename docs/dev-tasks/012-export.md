# Task: 报告与数据导出模块

## Goal

实现Word报告初稿、ESG数据表Excel、来源引用表Excel、AI校对问题表Excel和导出任务记录。PDF和ZIP可作为P1或占位能力。

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
- 实现 report_exports 创建和查询。
- 实现Word初稿导出。
- 实现ESG数据表Excel导出。
- 实现来源引用表Excel导出。
- 实现AI校对问题表Excel导出。
- 导出文件写入 file_objects。
- 下载接口鉴权。

### Worker
- 实现 export job。
- 记录导出状态、失败原因、file_ids。

### Frontend
- 导出页面。
- 导出选项。
- 导出记录。
- 下载按钮。
- 正式稿阻断提示。

### Tests
- 有权限用户导出成功。
- 无权限用户导出失败。
- 有高风险问题阻断正式稿。
- 导出文件可下载。
- 导出审计记录存在。

## Out of Scope

- 不实现印刷级PDF排版。
- 不实现复杂客户品牌模板。
- 不实现XBRL。

## Required Behaviors

- 正式稿导出必须要求章节确认、全文校对、高风险问题清零。
- 初稿可包含风险提示。
- 文件下载必须后端鉴权。
- 导出必须写审计日志。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 可导出Word初稿。
- [ ] 可导出ESG数据Excel。
- [ ] 可导出来源引用Excel。
- [ ] 可导出校对问题Excel。
- [ ] 导出文件记录在 file_objects。
- [ ] 下载权限和审计通过。

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
