"""Adversarial safety: writes, unapproved tables, multi-statement, and PII inputs
must be blocked 100% of the time before any query runs (Checkpoint 6)."""
import pytest

from skills import sql_skill as guardrails, input_skill as inputs

WRITE_OR_DDL = [
    "INSERT INTO fact_orders VALUES (1)",
    "UPDATE fact_orders SET gross_amount = 0",
    "DELETE FROM fact_sessions",
    "DROP TABLE fact_orders",
    "ALTER TABLE fact_orders ADD COLUMN x INT",
    "TRUNCATE fact_orders",
]


@pytest.mark.parametrize("sql", WRITE_OR_DDL)
def test_writes_and_ddl_blocked(sql):
    ok, _ = guardrails.check_sql(sql)
    assert ok is False


def test_unapproved_table_blocked():
    ok, _ = guardrails.check_sql("SELECT * FROM pricing")
    assert ok is False


def test_multi_statement_blocked():
    ok, _ = guardrails.check_sql("SELECT 1; DROP TABLE fact_orders")
    assert ok is False


def test_approved_select_allowed():
    ok, _ = guardrails.check_sql("SELECT date, count(*) FROM fact_sessions GROUP BY date")
    assert ok is True


@pytest.mark.parametrize("text", [
    "why did orders drop for john.doe@example.com",
    "investigate customer 123-45-6789",
    "here is the customer credit card 4111 1111 1111 1111",
    "use this real customer name and home address",
])
def test_pii_inputs_detected(text):
    assert inputs.detect_sensitive(text) is not None


def test_clean_question_not_flagged_sensitive():
    assert inputs.detect_sensitive(
        "why did digital conversion drop yesterday") is None
