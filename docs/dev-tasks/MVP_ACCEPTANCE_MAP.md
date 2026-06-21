# MVP Acceptance Map v0.1

本文件用于汇总 12 张 Codex 任务卡的验收重点。

| Task | 模块 | 最关键验收 |
|---|---|---|
| 001 | Auth/Tenant/RBAC | 无Token、Token过期、跨租户访问必须失败 |
| 002 | Enterprise/Project | 可创建项目，项目级权限隔离正确 |
| 003 | Standard Library | 标准、条款、议题、指标、映射可查询 |
| 004 | GICS/Peer | GICS确认后才能生成同行池 |
| 005 | Peer Report Parse | 上传、异步任务、解析结果审核链路跑通 |
| 006 | Recommendation | 采用率由系统计算，AI不得编造统计数字 |
| 007 | Collection | 采集、校验、审核、退回、通过流程跑通 |
| 008 | ESG Data | 只有审核通过数据进入正式ESG数据表 |
| 009 | Knowledge Base | 文件入库、切片、检索、权限隔离跑通 |
| 010 | Report Writing | 材料包确认后AI生成章节版本 |
| 011 | Citation/Review | 来源缺失/矛盾/高风险问题可阻断正式确认 |
| 012 | Export | Word/Excel导出、下载鉴权、审计记录跑通 |

## Release Gate

MVP试点前至少要求：

- Task 001-008 全部完成并通过接口测试。
- Task 009-012 至少完成主路径。
- E2E能跑通：登录 → 创建项目 → 确认同行 → 上传报告 → 生成推荐 → 确认议题 → 采集审核 → AI写作 → 校对 → 导出。
