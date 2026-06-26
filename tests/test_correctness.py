"""Answer correctness vs the seeded ground truth: the anchor investigation must
identify the isolated supported drivers, land the drop in the seeded band, not
overstate the funnel (which tracks the overall drop rather than independently
causing it), and prune the ungoverned price-increase hypothesis."""
import pytest

from workflows.investigation import run_investigation

ANCHOR = "Why did digital conversion drop yesterday compared with the prior 7-day average?"


@pytest.fixture(scope="module")
def anchor_trace():
    return run_investigation(ANCHOR, use_index=False)


def test_expected_seeded_drivers_identified(anchor_trace):
    # The three genuinely isolated seeded drivers: paid-social mix shift, the Electronics
    # stockout, and the West fulfillment delay.
    conf = {b.driver: b.confidence for b in anchor_trace["depth1"]}
    for key in ("campaign_mix", "inventory_availability", "fulfillment_constraints"):
        assert conf.get(key) == "likely driver", f"{key} not identified (got {conf.get(key)})"


def test_funnel_not_overstated(anchor_trace):
    # Cart->purchase fell roughly in line with the overall drop (no isolated funnel
    # defect), so the funnel must NOT be promoted to a likely driver.
    conf = {b.driver: b.confidence for b in anchor_trace["depth1"]}
    assert conf.get("funnel_behavior") != "likely driver", \
        f"funnel overstated as {conf.get('funnel_behavior')}"


def test_drop_lands_in_seeded_band(anchor_trace):
    assert -0.25 <= anchor_trace["baseline"]["pct_change"] <= -0.15


def test_ungoverned_hypothesis_is_pruned(anchor_trace):
    conf = {b.driver: b.confidence for b in anchor_trace["depth1"]}
    assert conf.get("price_increase") not in ("likely driver", "possible contributor")
