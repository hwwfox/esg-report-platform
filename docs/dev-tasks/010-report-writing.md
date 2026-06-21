# Task: 报告章节与AI写作模块

## Goal

实现报告章节结构、章节材料包、AI章节生成任务、章节版本管理、人工编辑和章节确认。MVP可以使用Mock AI或真实AI网关，但必须保留材料包、版本和审计链路。

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
- 实现 report_chapters CRUD和排序。
- 实现 chapter_material_packages 准备与确认。
- 实现章节生成任务创建。
- 实现 chapter_versions 保存。
- 实现章节确认接口。

### Worker / AI
- 实现 chapter_writing job。
- 基于材料包生成章节。
- 保存AI调用日志和输出记录。
- 生成章节版本。

### Frontend
- 报告章节树。
- 材料包确认页面。
- AI生成按钮和任务进度。
- 章节编辑器基础能力。
- 章节确认按钮。

### Tests
- 未确认材料包阻断正式生成。
- 生成章节版本。
- 人工编辑生成新版本。
- 确认章节。

## Out of Scope

- 不实现复杂在线协同编辑。
- 不实现高级排版。
- 不实现最终报告导出。

## Required Behaviors

- AI写作不得使用未确认材料包。
- 同行案例必须标记为参考，不能写成本企业事实。
- 每次AI调用必须记录 prompt_version 和 model_name。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 可创建章节结构。
- [ ] 可准备并确认材料包。
- [ ] 可生成章节草稿。
- [ ] 可保存章节版本。
- [ ] 可确认章节。
- [ ] AI日志和输出记录完整。

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
