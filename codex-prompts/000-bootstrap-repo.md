# Codex Prompt 000: Bootstrap Repository

Use this prompt when asking Codex to initialize the ESG Report Platform repository.

---

## Prompt

Read `AGENTS.md` first.

Then read these files:

1. `README.md`
2. `docs/architecture/TECH_STACK_DECISION.md`
3. `docs/dev-tasks/MVP_BUILD_ORDER.md`
4. `docs/dev-tasks/000-sprint-0-bootstrap.md`

Your task is to implement **Task 000: Sprint 0 工程启动与仓库骨架**.

Scope:

1. Create or verify the required monorepo directory structure.
2. Add `.env.example`.
3. Add `docker-compose.dev.yml` with PostgreSQL, Redis, and MinIO.
4. Add a root `Makefile` with the commands listed in the task card.
5. Initialize a minimal FastAPI app in `apps/api` with `GET /health`.
6. Initialize a minimal React + Vite + TypeScript app in `apps/web`.
7. Initialize a minimal worker placeholder in `apps/worker`.
8. Initialize a minimal mock AI gateway in `apps/ai-gateway`.
9. Add placeholders for OpenAPI, schemas, migrations, seed data, prompts, and tests.
10. Add `.gitignore`, `VERSION`, and basic CI config.

Do not implement full business modules yet.
Do not add authentication yet.
Do not connect to a real AI provider yet.
Do not commit secrets.
Do not remove or ignore any constraints from `AGENTS.md`.

After implementation, run or attempt to run:

```bash
make dev-up
make api
make web
make worker
make ai-gateway
make openapi-check
make schema-check
make test
```

If a command cannot run because dependencies are not installed or the environment is unavailable, report it honestly and explain what remains.

Final response format:

```text
## Changed Files
- ...

## Implementation Summary
- ...

## Tests Run
- make dev-up: pass/fail/not run, reason
- make api: pass/fail/not run, reason
- make web: pass/fail/not run, reason
- make worker: pass/fail/not run, reason
- make ai-gateway: pass/fail/not run, reason
- make openapi-check: pass/fail/not run, reason
- make schema-check: pass/fail/not run, reason
- make test: pass/fail/not run, reason

## Not Completed
- ...

## Risks / Notes
- ...
```
