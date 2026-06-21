# GitHub 分支保护配置清单 v0.1

## 1. 需要保护的分支

- `main`
- `develop`

## 2. main 分支保护建议

在 GitHub Repository → Settings → Branches → Branch protection rules 中配置：

- [ ] Require a pull request before merging
- [ ] Require approvals: 1 或以上
- [ ] Dismiss stale pull request approvals when new commits are pushed
- [ ] Require review from Code Owners
- [ ] Require status checks to pass before merging
- [ ] Required status checks: `quality-gate`
- [ ] Require branches to be up to date before merging
- [ ] Require conversation resolution before merging
- [ ] Restrict who can push to matching branches
- [ ] Do not allow bypassing the above settings

## 3. develop 分支保护建议

- [ ] Require a pull request before merging
- [ ] Require status checks to pass before merging
- [ ] Required status checks: `quality-gate`
- [ ] Require conversation resolution before merging

## 4. Codex开发建议

Codex 可以在 feature 分支提交代码，但不得直接提交到 `main` 或 `develop`。

推荐分支命名：

```text
feature/001-auth-tenant-rbac
feature/002-enterprise-project
bugfix/BUG-xxx-description
codex/001-auth-tenant-rbac
```
