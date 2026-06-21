# Task: 知识库文件与检索模块

## Goal

实现企业/项目知识库文档、文件入库、文本切片、基础检索、按部门/议题/指标/年份筛选，并为报告写作材料包提供可引用来源。

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
- 实现知识库文件上传和登记。
- 实现 knowledge_documents 创建。
- 实现 knowledge_chunks 生成或Mock切片。
- 实现关键词检索接口。
- 支持部门、议题、指标、年份、文件类型筛选。

### Worker
- 实现 knowledge_index job 框架。
- 生成切片和基础元数据。

### Frontend
- 知识库列表。
- 文件上传。
- 搜索和筛选。
- 原文定位占位展示。

### Tests
- 上传知识库文件。
- 创建索引任务。
- 检索返回结果。
- 越权不能访问知识库文件。

## Out of Scope

- 不要求生产级向量检索。
- 不要求音频转写真实接入。
- 不要求复杂权限继承UI。

## Required Behaviors

- 知识库材料必须区分企业级和项目级。
- AI写作只能使用授权且审核通过/确认可用材料。
- 文件下载必须鉴权。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 知识库文件可上传。
- [ ] 知识文档可查询。
- [ ] 知识切片可检索。
- [ ] 筛选条件可用。
- [ ] 文件和检索权限隔离通过。

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
