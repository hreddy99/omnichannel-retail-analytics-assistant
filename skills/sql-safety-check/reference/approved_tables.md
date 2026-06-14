# Approved tables (read-only)

The SQL validator (`src.guardrails.check_sql`) permits SELECT/WITH over only these
tables, sourced from `catalog/tables.yaml`:

- `fact_sessions`, `fact_events`, `fact_orders`, `fact_order_items`
- `fact_inventory_daily`, `fact_fulfillment`, `fact_customer_contacts`, `fact_finance_daily`
- `dim_product`, `dim_category`, `dim_campaign`

Blocked: any write/DDL keyword (insert, update, delete, drop, alter, create, truncate,
replace, merge, grant, attach, copy, pragma), multiple statements, or any table not above.
The authoritative list is whatever `catalog.approved_tables()` returns at runtime.
