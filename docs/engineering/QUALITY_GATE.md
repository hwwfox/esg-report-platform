# ESG Report Platform 代码质量门禁 v0.1

## 1. 目标

本文件定义 `esg-report-platform` 仓库在合并 Pull Request 前必须满足的质量门禁。适用于人工开发和 Codex 生成代码。

## 2. 合并前必须通过的检查

| 门禁 | 必须性 | 说明 |
|---|---:|---|
| CI通过 | 必须 | GitHub Actions `ci` 成功 |
| PR模板完整 | 必须 | 自测结果和风险说明已填写 |
| 关联Issue | 必须 | PR必须关联任务或Bug |
| 无密钥泄露 | 必须 | 通过 `check-no-secrets.sh` |
| OpenAPI一致 | 必须 | 接口变更必须更新契约和Mock |
| Migration合规 | 必须 | 数据库变更必须有migration |
| 权限校验 | 必须 | tenant/enterprise/project隔离不可绕过 |
| AI Schema校验 | 必须 | AI输出不得直接进入正式业务表 |
| 审计日志 | 必须 | 关键操作必须有审计 |
| 测试覆盖 | 必须 | 至少覆盖主路径和权限拒绝路径 |

## 3. Codex专用约束

Codex 每次提交应满足：

1. 只修改任务卡范围内的文件；
2. 不私自更换技术栈；
3. 不删除安全、权限、审计、Schema校验逻辑；
4. 不用 mock 结果冒充真实业务闭环；
5. 不提交 `.env`、密钥、真实客户数据；
6. 不能跑测试时，应在 PR 中明确说明原因和替代验证方式。

## 4. Blocker级问题

出现以下情况 PR 不得合并：

- 跨租户或跨项目越权；
- 文件下载无鉴权；
- AI输出绕过Schema校验；
- 数据库表结构手工更改但无migration；
- OpenAPI与后端返回不一致；
- CI失败；
- 密钥泄露；
- 正式导出绕过章节确认或高风险问题处理。
