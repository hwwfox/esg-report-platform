# Task: GICS识别与同行池模块

## Goal

实现企业GICS行业识别候选、人工确认、同行公司推荐、同行池确认和手动增删同行能力。该模块为同行报告解析和议题推荐提供样本范围。

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
- 实现GICS候选查询与确认接口。
- 实现企业GICS历史记录。
- 实现同行公司搜索接口。
- 实现基于GICS四级行业的同行推荐接口。
- 实现项目同行池增删改查与确认。

### Frontend
- GICS识别确认页。
- 同行推荐列表。
- 同行手动搜索选择。
- 同行池确认操作。

### Database
- 使用 gics_industries、enterprise_gics_history、peer_company_profiles、project_peer_companies。

### Tests
- 未确认GICS时阻断同行推荐。
- 确认GICS后可生成同行池。
- 可手动添加同行。
- 无权限不能修改同行池。

## Out of Scope

- 不实现外部交易所实时抓取。
- 不实现复杂相似度模型训练。
- 不实现自动行业重新分类。

## Required Behaviors

- 默认使用GICS四级行业。
- 同行推荐需要用户确认。
- 推荐理由必须可解释。
- 不能把未确认同行纳入后续统计。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 可以确认企业GICS。
- [ ] 可以生成同行推荐。
- [ ] 可以手动选择同行。
- [ ] 可以确认项目同行池。
- [ ] 权限和状态阻断测试通过。

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
