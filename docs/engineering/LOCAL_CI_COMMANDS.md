# 本地 CI 命令说明 v0.1

## 一键本地检查

```bash
bash scripts/ci-local.sh
```

## 分项检查

```bash
bash scripts/check-no-secrets.sh
bash scripts/check-openapi-mock-sync.sh
bash scripts/check-migrations.sh
```

如果项目已实现 Makefile 命令，可执行：

```bash
make lint
make typecheck
make test
make test-api
make schema-check
make openapi-check
```

## Codex提交前要求

Codex 每次完成任务后，应在 PR 中说明：

1. 实际运行了哪些命令；
2. 哪些命令通过；
3. 哪些命令无法运行以及原因；
4. 是否修改了 OpenAPI、DB、Prompt、Schema；
5. 是否存在风险或后续任务。
