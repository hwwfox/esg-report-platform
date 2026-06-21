# Task: 来源引用与AI校对模块

## Goal

实现章节事实声明抽取、来源引用匹配、引用支持状态、章节校对问题、全文校对结果和高风险阻断规则。

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
- 实现 chapter_claims 创建或抽取接口。
- 实现 citation_results 保存和查询。
- 实现 source_references 查询。
- 实现 chapter_review_issues 查询和处理。
- 实现 full_report_reviews 创建和确认。

### Worker / AI
- 实现 citation_rebuild job。
- 实现 chapter_review job。
- 实现 full_report_review job。
- 高风险问题必须可阻断章节确认或正式导出。

### Frontend
- 来源引用查看。
- 章节校对问题列表。
- 问题处理状态。
- 全文校对结果页面。

### Tests
- 来源缺失标记 source_missing。
- 来源矛盾标记 contradicted。
- 高风险问题阻断确认。
- 用户处理问题后可继续。

## Out of Scope

- 不实现复杂法律合规审查自动结论。
- 不实现外部审计工作流。
- 不实现百分百事实自动验证承诺。

## Required Behaviors

- 所有事实声明必须可追踪至章节版本。
- unsupported/contradicted/source_missing 不得进入正式稿导出。
- 强制确认必须要求原因并写审计。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 可重建章节来源引用。
- [ ] 可查看事实声明和来源状态。
- [ ] 可生成章节校对问题。
- [ ] 高风险问题会阻断正式确认/导出。
- [ ] 全文校对结果可保存。

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
