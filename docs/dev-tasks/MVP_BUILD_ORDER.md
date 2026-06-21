# ESG报告软件 MVP开发顺序 v0.1

## 1. 文档目标

本文档定义 Codex 和开发团队实现 ESG报告软件 MVP 的推荐顺序。任何任务应尽量按照本文顺序推进，避免依赖倒置、提前开发后置能力或反复返工。

---

## 2. 总体开发原则

1. 先搭工程骨架，再做业务模块；
2. 先做权限和租户隔离，再做业务数据；
3. 先锁定OpenAPI和数据库，再做前后端联调；
4. 先实现Mock AI，再接真实AI；
5. 先实现候选结果和人工审核，再实现推荐统计；
6. 先实现结构化数据和来源，再实现AI写作；
7. 先实现Word/Excel导出，再做PDF和ZIP；
8. 每个阶段都必须有测试和验收标准。

---

## 3. MVP阶段划分

| Phase | 名称 | 目标 |
|---:|---|---|
| 0 | Sprint 0 工程启动 | 仓库、环境、CI、基础依赖 |
| 1 | Auth + Tenant + RBAC | 登录、租户、用户、角色、权限 |
| 2 | Enterprise + Project | 企业与报告项目 |
| 3 | Standard Library | 标准库、议题库、指标库 |
| 4 | GICS + Peer Company | 行业识别和同行池 |
| 5 | Peer Report Upload + Async Job | 文件上传和异步任务框架 |
| 6 | AI Parse Mock Pipeline | AI解析Mock流水线 |
| 7 | Recommendation | 标准/议题/指标推荐 |
| 8 | Collection Task | 部门采集、提交、审核 |
| 9 | ESG Data Records | 审核通过数据入正式数据表 |
| 10 | Knowledge Base | 文件、切片、检索基础 |
| 11 | Report Chapter Writing | 材料包、章节、AI写作 |
| 12 | Citation + AI Review | 来源引用和AI校对 |
| 13 | Export | Word/Excel/PDF导出 |
| 14 | Hardening | 安全、日志、监控、回归 |

---

## 4. Phase 0：Sprint 0 工程启动

### 目标

完成仓库骨架、本地开发环境、数据库初始化、OpenAPI放置、Mock数据放置和CI基础检查。

### 任务

1. 初始化目录结构；
2. 添加 AGENTS.md、README.md；
3. 添加 `.env.example`；
4. 添加 `docker-compose.dev.yml`；
5. 添加 Makefile；
6. 放入 OpenAPI、DDL、Seed Data、Mock数据；
7. 配置FastAPI基础应用；
8. 配置React/Vite基础应用；
9. 配置PostgreSQL、Redis、MinIO；
10. 配置基础CI。

### 验收

1. `make dev-up` 成功；
2. `make migrate` 成功；
3. `make seed` 成功；
4. `make api` 成功；
5. `make web` 成功；
6. `GET /health` 返回ok；
7. CI至少能跑 lint/openapi-check/schema-check。

---

## 5. Phase 1：Auth + Tenant + RBAC

### 目标

实现基础登录、用户、租户、角色、权限校验。

### 任务

1. 用户登录接口；
2. JWT签发和校验；
3. 当前用户接口；
4. 租户上下文中间件；
5. 角色与权限表读取；
6. 后端权限装饰器或依赖；
7. 前端登录页；
8. 前端路由守卫；
9. 审计日志基础能力。

### 验收

1. 未登录访问业务接口返回 `AUTH_UNAUTHORIZED`；
2. Token过期返回 `AUTH_TOKEN_EXPIRED`；
3. 跨租户访问被拒绝；
4. 前端登录后可进入工作台；
5. 权限拒绝写安全日志。

---

## 6. Phase 2：Enterprise + Project

### 目标

实现企业管理和报告项目管理。

### 任务

1. 企业列表、创建、详情、更新；
2. 项目创建、列表、详情、状态流转；
3. 项目成员；
4. 项目状态机；
5. 项目工作台页面；
6. 项目审计日志。

### 验收

1. 项目负责人可创建项目；
2. 无权限用户不能访问项目；
3. 项目状态合法流转；
4. 所有项目查询带tenant_id和enterprise_id；
5. 创建项目写审计日志。

---

## 7. Phase 3：Standard Library

### 目标

实现ESG标准、版本、条款、议题、指标和映射关系的查询与维护基础能力。

### 任务

1. 标准列表和详情；
2. 标准版本；
3. 标准条款；
4. 议题库；
5. 指标库；
6. 标准-议题映射；
7. 议题-指标映射；
8. 标准库导入预留；
9. 标准库页面。

### 验收

1. 可查询标准、议题、指标；
2. 可按标准查看条款；
3. 可查看议题下指标；
4. 平台公共标准和租户私有标准可区分；
5. 无管理权限不能编辑标准库。

---

## 8. Phase 4：GICS + Peer Company

### 目标

实现企业行业识别和同行公司池推荐/确认。

### 任务

1. GICS行业表查询；
2. 企业GICS候选结果；
3. 人工确认GICS；
4. 同行公司列表；
5. 项目同行推荐；
6. 用户选择/取消同行；
7. 同行池确认。

### 验收

1. 创建项目后可识别/确认GICS；
2. 可生成同行池；
3. 用户可手动添加同行；
4. 同行池确认后写入项目同行表；
5. 未确认GICS时阻断同行推荐。

---

## 9. Phase 5：Peer Report Upload + Async Job

### 目标

实现文件上传、同行报告记录和异步任务框架。

### 任务

1. file_objects；
2. MinIO上传；
3. 文件下载鉴权；
4. peer_report_files；
5. async_jobs；
6. Worker ping任务；
7. 报告解析任务创建；
8. 任务状态查询页面。

### 验收

1. 可上传PDF文件；
2. 文件写入file_objects；
3. 下载必须鉴权；
4. 创建解析任务返回job_id；
5. Worker可把任务状态改为succeeded或failed。

---

## 10. Phase 6：AI Parse Mock Pipeline

### 目标

先用Mock AI跑通标准识别、议题提取、指标提取、案例提取和人工审核流程。

### 任务

1. ai_models；
2. ai_call_logs；
3. ai_output_records；
4. Mock AI Provider；
5. JSON Schema校验；
6. report_extracted_standards；
7. report_extracted_topics；
8. report_extracted_metrics；
9. report_extracted_cases；
10. 人工审核页面。

### 验收

1. AI调用写日志；
2. 输出Schema校验失败不入候选表；
3. 候选结果可人工接受/编辑/拒绝；
4. 审核通过后可进入统计；
5. 原始AI输出可追溯。

---

## 11. Phase 7：Recommendation

### 目标

基于已审核同行解析结果生成标准、议题、指标推荐。

### 任务

1. 推荐统计计算；
2. project_recommendations；
3. 推荐理由生成；
4. 推荐限制说明；
5. 推荐来源引用；
6. 推荐结果确认；
7. 项目标准/议题/指标快照。

### 验收

1. 采用率由系统计算；
2. 样本不足时提示限制；
3. 用户可选择/忽略推荐；
4. 确认后生成project_topics和project_topic_metrics；
5. AI不编造统计数字。

---

## 12. Phase 8：Collection Task

### 目标

实现议题分配、部门采集、提交和审核。

### 任务

1. 组织架构；
2. 项目组织快照；
3. 议题分配；
4. 采集任务生成；
5. 采集表单；
6. 附件上传；
7. 数据校验；
8. 审核通过/退回。

### 验收

1. 项目负责人可分配议题；
2. 采集员只看自己的任务；
3. 审核员可审核对应任务；
4. 必填数据缺失不能提交；
5. 审核通过后进入正式数据表。

---

## 13. Phase 9：ESG Data Records

### 目标

沉淀审核通过的正式ESG数据表。

### 任务

1. esg_data_records；
2. 审核通过数据入表；
3. 来源任务追溯；
4. 数据列表；
5. 数据筛选；
6. 数据导出基础。

### 验收

1. 未审核数据不入正式表；
2. 每条数据可追溯到任务、提交和文件；
3. 用户可按议题/部门/年度筛选；
4. 无权限用户不能查看其他部门数据。

---

## 14. Phase 10：Knowledge Base

### 目标

实现知识库文档、切片、检索基础。

### 任务

1. knowledge_documents；
2. knowledge_chunks；
3. 文档入库；
4. 文本切片；
5. 元数据标签；
6. 基础关键词检索；
7. 后续向量检索预留。

### 验收

1. 文件可进入知识库；
2. 可按部门/议题/指标/年度筛选；
3. 可查看原文位置；
4. 无权限用户不能访问知识库文件。

---

## 15. Phase 11：Report Chapter Writing

### 目标

实现章节结构、材料包、章节版本和AI写作。

### 任务

1. report_chapters；
2. chapter_material_packages；
3. chapter_versions；
4. 材料包构建；
5. AI章节写作；
6. 人工编辑；
7. 章节确认。

### 验收

1. 章节可生成材料包；
2. 缺失信息被标记；
3. AI写作基于材料包；
4. 章节版本可追溯；
5. 确认章节写审计。

---

## 16. Phase 12：Citation + AI Review

### 目标

实现事实声明、来源引用、章节校对和全文校对。

### 任务

1. chapter_claims；
2. source_references；
3. citation_results；
4. chapter_review_issues；
5. full_report_reviews；
6. 来源缺失提示；
7. 高风险问题阻断确认。

### 验收

1. 事实声明可匹配来源；
2. 来源支持状态可见；
3. 高风险问题不能直接确认；
4. 强制确认必须写原因和审计；
5. 同行事实误用可被标记。

---

## 17. Phase 13：Export

### 目标

实现Word、Excel、来源引用表和校对问题表导出。

### 任务

1. report_exports；
2. Word导出；
3. ESG数据表Excel导出；
4. 来源引用Excel导出；
5. AI校对问题Excel导出；
6. 文件写入file_objects；
7. 导出下载鉴权；
8. 导出审计。

### 验收

1. 可导出Word初稿；
2. 可导出ESG数据表；
3. 可导出来源引用表；
4. 无权限不能下载；
5. 正式稿导出受项目状态和高风险问题控制。

---

## 18. Phase 14：Hardening

### 目标

完成安全、日志、监控、性能和回归测试加固。

### 任务

1. 权限矩阵回归；
2. 多租户隔离测试；
3. 文件下载越权测试；
4. AI输出异常测试；
5. 导出异常测试；
6. 日志和监控埋点；
7. 关键告警；
8. Go/No-Go检查。

---

## 19. Codex执行建议

每次只给 Codex 一个任务卡。不要让 Codex 同时开发多个阶段。

推荐Prompt：

```text
Read AGENTS.md first.
Then read docs/dev-tasks/MVP_BUILD_ORDER.md.
Then read the specific task card.
Implement only the task scope.
Do not expand scope.
Run the listed tests.
Return changed files, test results, and remaining risks.
```
