"""Deterministic tie-break: the Critic ranks competing drivers by the documented
sequence, and when it cannot separate two equally-supported drivers it labels both
as possible contributors and escalates to analyst review (no forced winner)."""
from skills import tot_skill as tot
from workflows.investigation import run_investigation

ANCHOR = "Why did digital conversion drop yesterday compared with the prior 7-day average?"


def _branch(driver, scores, signal):
    b = tot.Branch(driver=driver, label=driver, owner="X")
    b.scores = scores
    b.signal = signal
    b.total = sum(scores.values())
    return b


def test_tie_break_key_orders_by_evidence_then_freshness():
    base = {"metric_validated_yaml": 2, "approved_graph_path": 2, "sql_safety_template": 2,
            "duckdb_evidence_strength": 3, "freshness_row_quality": 2,
            "business_relevance_owner": 2, "caveats_manageable": 1}
    strong = _branch("a", base, 0.5)
    weak = _branch("b", {**base, "duckdb_evidence_strength": 1}, 0.2)
    assert tot.tie_break_key(strong) > tot.tie_break_key(weak)


def test_is_unresolved_tie_true_when_identical():
    s = {"metric_validated_yaml": 2, "approved_graph_path": 2, "sql_safety_template": 2,
         "duckdb_evidence_strength": 3, "freshness_row_quality": 2,
         "business_relevance_owner": 2, "caveats_manageable": 1}
    a, b = _branch("a", dict(s), 0.5), _branch("b", dict(s), 0.5)
    assert tot.is_unresolved_tie(a, b) is True


def test_is_unresolved_tie_false_when_evidence_differs():
    # Same total (13) but a leads on DuckDB evidence while b leads on the caveat dim,
    # so the tie-break separates them at criterion 1 -> not an unresolved tie.
    common = {"metric_validated_yaml": 2, "approved_graph_path": 2, "sql_safety_template": 2,
              "freshness_row_quality": 2, "business_relevance_owner": 2}
    a = _branch("a", {**common, "duckdb_evidence_strength": 3, "caveats_manageable": 0}, 0.5)
    b = _branch("b", {**common, "duckdb_evidence_strength": 2, "caveats_manageable": 1}, 0.5)
    assert a.total == b.total == 13
    assert tot.is_unresolved_tie(a, b) is False
    assert tot.tie_break_key(a) > tot.tie_break_key(b)


def test_injected_tie_downgrades_both_and_escalates():
    t = run_investigation(ANCHOR, use_index=False, inject_tie=True)
    a = t["answer"]
    tie = a.get("tie")
    assert tie and len(tie["drivers"]) == 2
    # both tied drivers are possible contributors; none left as "likely driver"
    labels = {d["confidence"] for d in a["drivers"]}
    assert labels == {"possible contributor"}
    # high-risk review mentioning the tie
    assert a["review"]["risk_level"] == "high"
    assert "tie-break" in a["review"]["reason"]
    # action log routes each owner to analyst review, and an audit event is logged
    needs_review = [x for x in t["audit"].actions if x["priority"] == "needs review"]
    assert len(needs_review) >= 2
    assert any(e["decision_type"] == "tie_unresolved" for e in t["audit"].events)


def test_normal_run_has_no_tie():
    t = run_investigation(ANCHOR, use_index=False)
    assert t["answer"].get("tie") is None
    assert t["answer"]["drivers"]  # drivers still resolve normally
