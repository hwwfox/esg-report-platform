# AI Prompts

每个Agent的Prompt必须单独目录、版本化存放：

```text
standard_identification/v0.1.md
topic_extraction/v0.1.md
chapter_writing/v0.1.md
```

Prompt变更必须更新 `prompt_version`，并跑小样本回归。
