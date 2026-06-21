# Codex Prompt: 企业与报告项目模块

Read `AGENTS.md` first. Then read this task card:

`docs/dev-tasks/002-enterprise-project.md`

Implement only the scope described in that task card.

Hard constraints:

- Do not skip permission checks.
- Do not change public contracts silently.
- If OpenAPI changes, update mock data and tests.
- If database schema changes, add a migration instead of editing historical DDL.
- If AI output shape changes, update JSON Schema and tests.
- Do not commit secrets or real customer data.
- Do not implement out-of-scope features.

Before finishing, run the relevant commands from the task card. If a command cannot run in the current environment, say exactly why and provide the closest validation performed.

Final response must include:

1. Summary
2. Changed files
3. Tests run
4. Test results
5. Known risks
6. Suggested next task
