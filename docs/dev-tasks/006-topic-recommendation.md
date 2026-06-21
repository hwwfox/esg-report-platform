# Task: 推荐标准与推荐议题模块

## Goal

基于已审核同行报告解析结果，生成推荐标准、推荐议题、同行采用率、样本数、重要性分布和推荐理由，支持用户接受、忽略、编辑并形成项目标准/议题快照。

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
- 实现推荐生成接口。
- 统计标准采用率、议题采用率、样本数量。
- 生成 project_recommendations。
- 实现推荐结果确认接口。
- 生成 project_standards、project_topics、project_topic_metrics 快照。

### AI
- AI仅生成推荐理由和限制说明。
- 采用率、公司数、样本数必须由系统计算。

### Frontend
- 推荐标准页面。
- 推荐议题页面。
- 采用率、样本数、重要性信息展示。
- 接受、忽略、编辑、新增议题。

### Tests
- 样本不足阻断。
- 采用率计算正确。
- AI不得编造统计数字。
- 用户确认后生成项目快照。

## Out of Scope

- 不实现高级统计可视化。
- 不实现复杂行业权重模型。
- 不实现自动双重重要性最终结论审批。

## Required Behaviors

- 推荐来源必须可追溯。
- 样本不足必须写limitations。
- 选定议题锁定后不得被基础库更新影响。

## Permission and Security Requirements

- 所有接口必须返回统一响应结构和 `request_id`。
- 所有项目级数据访问必须校验 `tenant_id`、`enterprise_id`、`project_id`。
- 对象存储文件下载必须走后端鉴权。
- 不得在日志中输出密钥、Token、客户敏感原文。
- 业务错误必须使用错误码规范，不得返回裸异常。

## Acceptance Criteria

- [ ] 已审核同行数据可生成推荐。
- [ ] adoption_rate、adopted_company_count、analyzed_report_count 正确。
- [ ] 推荐结果可确认。
- [ ] 项目标准、议题、指标快照生成。
- [ ] 样本不足时返回明确错误码。

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
