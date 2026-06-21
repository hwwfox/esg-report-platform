## 变更内容

- 

## 关联 Issue

Closes #

## 影响范围

- [ ] 前端 Web
- [ ] 后端 API
- [ ] Worker / 异步任务
- [ ] AI Prompt / Schema / Agent
- [ ] 数据库 Migration / Seed
- [ ] OpenAPI / Mock Data
- [ ] 文件上传下载 / 导出
- [ ] 权限 / 安全 / 审计
- [ ] 文档

## 自测结果

请填写实际执行结果，不要只勾选。

- [ ] `bash scripts/ci-local.sh`
- [ ] `make lint`
- [ ] `make typecheck`
- [ ] `make test`
- [ ] `make test-api`
- [ ] `make schema-check`
- [ ] `make openapi-check`

## 权限与安全检查

- [ ] 所有项目级查询均校验 `tenant_id + enterprise_id + project_id`
- [ ] 文件下载通过后端鉴权，不暴露永久对象存储 URL
- [ ] 未将 API Key、Token、密码、客户敏感数据写入代码或日志
- [ ] 关键操作写入审计日志
- [ ] AI 输出未绕过 Schema 校验和人工审核状态

## 数据库检查

- [ ] 如涉及表结构变更，已新增 migration 文件
- [ ] migration 可重复执行或具备明确前置条件
- [ ] seed/demo 数据无真实客户敏感信息

## OpenAPI / Mock 检查

- [ ] 如接口变化，已更新 OpenAPI
- [ ] 如接口变化，已更新 Mock 数据
- [ ] 前端类型或 API Client 已同步更新

## 截图或录屏

如涉及 UI，请附截图或录屏。

## 风险说明

- 

## 需要重点 Review 的点

-
