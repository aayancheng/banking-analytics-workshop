"""EWS trigger rules + line-increase amount rules — pure-logic tests."""
import pandas as pd
import pytest

from ews.src.triggers import flag_triggers
from line_increase.src.amount_rules import (
    incremental_exposure, incremental_roe, recommended_amount,
)
from shared.config import LINE_INCREASE, MARKET


def test_triggers_fire_by_name():
    feats = pd.DataFrame([
        {"util_recent": 0.95, "util_drift": 0.0, "dpd_max": 0, "dpd_recent": 0,
         "deposit_decline_pct": 0.0, "overdraft_recent": 0},
        {"util_recent": 0.10, "util_drift": 0.20, "dpd_max": 45, "dpd_recent": 0,
         "deposit_decline_pct": 0.5, "overdraft_recent": 4},
    ])
    t = flag_triggers(feats)
    assert t[0] == ["HIGH_UTILIZATION"]
    assert set(t[1]) == {"RISING_UTILIZATION", "DELINQUENCY",
                         "DEPOSIT_DECLINE", "FREQUENT_OVERDRAFTS"}


def test_recommended_amount_caps():
    # headroom-to-target binds when it is the smallest term:
    # 95,000/0.65 - 100,000 = 46,154 -> rounds to 46,000 (below the 50,000 pct cap)
    amt = recommended_amount(current_balance=95_000, credit_limit=100_000,
                             annual_revenue=10_000_000)
    assert amt == pytest.approx(46_000)
    # pct cap binds when target-util headroom is larger:
    # 95,000/0.65 - 80,000 = 66,154 vs pct cap 0.5*80,000 = 40,000
    capped = recommended_amount(95_000, 80_000, 10_000_000)
    assert capped == pytest.approx(LINE_INCREASE["pct_cap"] * 80_000)
    # low utilization -> no increase needed
    assert recommended_amount(10_000, 100_000, 10_000_000) == 0.0
    # revenue ceiling binds for a small business
    small = recommended_amount(95_000, 100_000, annual_revenue=400_000)
    assert small <= LINE_INCREASE["revenue_mult_cap"] * 400_000 - 100_000 + LINE_INCREASE["round_to"]


def test_incremental_roe_is_gated_by_hurdle():
    # generous rate on a low-PD account clears; punitive PD at same rate does not
    good = incremental_roe(0.01, 50_000, 0.8, 0.12)
    bad = incremental_roe(0.30, 50_000, 0.8, 0.12)
    assert good["clears_hurdle"] and not bad["clears_hurdle"]
    assert good["incremental_ead"] == pytest.approx(incremental_exposure(50_000, 0.8))


def test_zero_amount_yields_zero_waterfall():
    r = incremental_roe(0.05, 0.0, 0.5, 0.10)
    assert r["incremental_ead"] == 0.0 and not r["clears_hurdle"]
    assert r["waterfall"]["net_income"] == 0.0
