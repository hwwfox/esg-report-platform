# Task: 企业与报告项目模块

## Goal

实现企业管理、项目创建、项目列表、项目详情、项目状态流转和项目成员管理。这是业务主流程的入口，后续同行分析、采集、写作、导出都依赖项目上下文。

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
- 实现企业列表、创建、详情、更新接口。
- 实现报告项目创建、列表、详情、更新接口。
- 实现项目成员添加、移除、列表接口。
- 实现项目状态流转的基础服务。
- 每个项目接口必须校验 tenant_id、enterprise_id、project_id。

### Frontend
- 企业列表/选择入口。
- 项目列表页。
- 项目创建表单。
- 项目详情/工作台基础页。
- 项目成员管理基础交互。

### Database
- 使用 enterprises、report_projects、project_members。
- 必要时增加 migration。

### Tests
- 创建企业。
- 创建项目。
- 查询项目列表。
- 项目状态非法流转阻断。
- 无权限用户不能访问项目。

## Out of Scope

- 不实现完整ESG报告写作。
- 不实现复杂项目模板。
- 不实现客户级商务合同。

## Required Behaviors

- 项目默认状态为 `draft`。
- 项目年度必须合法。
- 项目负责人必填。
- 项目状态流转必须集中定义，不允许前端直接改状态。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 可以创建企业。
- [ ] 可以创建ESG报告项目。
- [ ] 可以查看项目工作台基础信息。
- [ ] 可以添加项目成员。
- [ ] 项目权限隔离通过测试。
- [ ] `make test-api` 和相关前端测试通过。

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
