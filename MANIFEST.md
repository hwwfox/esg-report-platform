# ESG Codex CI Quality Gate Pack v0.1

本包用于 `esg-report-platform` 仓库的代码质量门禁、CI检查、PR评审和分支保护配置。

## 文件清单

```text
.github/workflows/ci.yml
.github/pull_request_template.md
.github/ISSUE_TEMPLATE/bug_report.md
.github/ISSUE_TEMPLATE/task_request.md
CODEOWNERS
docs/engineering/QUALITY_GATE.md
docs/engineering/BRANCH_PROTECTION_CHECKLIST.md
docs/engineering/LOCAL_CI_COMMANDS.md
scripts/ci-local.sh
scripts/check-no-secrets.sh
scripts/check-openapi-mock-sync.sh
scripts/check-migrations.sh
```

## 使用方式

将本包内容复制到 `esg-report-platform` 仓库根目录，然后执行：

```bash
chmod +x scripts/*.sh
git add .
git commit -m "chore(ci): add quality gate and CI configuration"
git push
```

随后在 GitHub 仓库设置中配置分支保护规则，要求 `ci` workflow 通过后才允许合并 PR。
