# Task: 认证、多租户与RBAC基础

## Goal

实现登录认证、租户上下文、用户角色、权限校验中间件和基础审计能力，为后续所有业务模块提供安全边界。该任务不追求复杂企业SSO，先实现MVP可用的账号密码/JWT/角色权限模型。

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
- 实现登录、登出、获取当前用户、刷新Token接口。
- 实现 JWT 认证中间件。
- 实现 tenant context 解析与注入。
- 实现 RBAC 权限校验工具。
- 实现角色、用户角色、企业访问范围的基础查询。
- 关键操作写入 audit_logs。

### Frontend
- 实现登录页。
- 实现登录态存储和失效处理。
- 实现基础路由守卫。
- 实现无权限页面或错误提示。

### Database
- 使用现有 users、roles、user_roles、enterprise_user_access、audit_logs 等表。
- 如缺少字段，通过 migration 添加，不得直接改DDL快照。

### Tests
- 登录成功/失败。
- Token过期。
- 无Token访问接口。
- 无权限访问项目接口。
- 跨租户访问拒绝。

## Out of Scope

- 不实现SSO/SAML/OIDC。
- 不实现复杂组织级审批流。
- 不实现生产级MFA。

## Required Behaviors

- 所有受保护API无Token必须返回 `AUTH_UNAUTHORIZED`。
- Token过期必须返回 `AUTH_TOKEN_EXPIRED`。
- 跨租户访问必须拒绝，不能返回其他租户数据。
- 权限拒绝必须记录安全日志或审计日志。
- 前端不得仅靠隐藏按钮作为权限控制。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 用户可登录并获取Token。
- [ ] 当前用户接口返回用户、角色、租户、企业访问范围。
- [ ] 未登录访问受保护接口失败。
- [ ] 无权限访问项目或文件失败。
- [ ] audit_logs 记录登录、权限拒绝、权限变更相关事件。
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
