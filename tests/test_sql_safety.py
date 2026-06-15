"""Safety contract: the SQL guardrail allows read-only queries over approved
tables and blocks everything else."""
import pytest

from skills import sql_skill as guardrails


def test_select_over_approved_table_ok():
    ok, _ = guardrails.check_sql("SELECT count(*) FROM fact_sessions")
    assert ok is True


def test_with_cte_ok():
    ok, _ = guardrails.check_sql(
        "WITH s AS (SELECT * FROM fact_orders) SELECT count(*) FROM s")
    assert ok is True


@pytest.mark.parametrize("sql", [
    "INSERT INTO fact_sessions VALUES (1)",
    "UPDATE fact_orders SET total = 0",
    "DELETE FROM fact_orders",
    "DROP TABLE fact_sessions",
    "CREATE TABLE x (a int)",
    "ALTER TABLE fact_orders ADD COLUMN x int",
    "SELECT 1; SELECT 2",                         # multiple statements
    "SELECT * FROM not_a_real_table",             # unapproved table
])
def test_unsafe_sql_blocked(sql):
    ok, reason = guardrails.check_sql(sql)
    assert ok is False
    assert reason  # a human-readable reason is always returned
