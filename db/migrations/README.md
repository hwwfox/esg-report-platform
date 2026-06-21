# Database Migrations

MVP初始DDL放在 `db/ddl/ESG_PostgreSQL_DDL_v0.1.sql`。

后续结构变更必须新增Migration，不得直接修改已发布DDL：

```text
V001__init_schema.sql
V002__add_ai_call_logs.sql
V003__add_export_template_version.sql
```
