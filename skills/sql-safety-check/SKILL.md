---
name: sql-safety-check
description: Validate that a SQL statement is read-only and uses only catalog-approved
  tables. Use before any query is executed against the DuckDB analytics database.
---
# SQL Safety Check

Enforces the read-only, governed contract: SELECT/WITH only, no write/DDL keywords, a
single statement, and only tables approved in the YAML catalog.

## Instructions
1. Call `src.guardrails.check_sql(sql)` → returns `(ok, reason)`.
2. If `ok` is False, do **not** execute; revise the plan (e.g. drop the unapproved table).
3. Approved tables are listed in `reference/approved_tables.md` and derived live from
   `catalog/tables.yaml` via `catalog.approved_tables()`.

This is the same guard the workflow runs before every DuckDB query.
