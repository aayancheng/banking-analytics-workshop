"""Pricing engine math — machine-precision identities (the reference build's
9-test pattern, condensed). No ML anywhere in these."""
import pytest

from shared.config import MARKET
from pricing.src.engine import (
    MarketAssumptions, break_even_rate, hurdle_clearing_rate,
    price_loan, profit_waterfall, recommended_rate,
)

M = MarketAssumptions.from_market(MARKET)
PD, EAD = 0.05, 250_000.0


def test_waterfall_identities():
    w = profit_waterfall(PD, EAD, 0.10, M)
    assert w["pre_tax_profit"] == pytest.approx(
        w["interest_income"] - w["cost_of_funds"] - w["expected_loss"] - w["operating_cost"])
    assert w["net_income"] == pytest.approx(w["pre_tax_profit"] * (1 - M.tax_rate))
    assert w["roe"] == pytest.approx(w["net_income"] / w["allocated_equity"])
    assert w["raroc"] == pytest.approx(w["pre_tax_profit"] / w["allocated_equity"])


def test_break_even_rate_gives_zero_roe():
    r = break_even_rate(PD, EAD, M)
    assert profit_waterfall(PD, EAD, r, M)["roe"] == pytest.approx(0.0, abs=1e-12)


def test_hurdle_clearing_rate_hits_hurdle_exactly():
    r = hurdle_clearing_rate(PD, EAD, M)
    assert profit_waterfall(PD, EAD, r, M)["roe"] == pytest.approx(M.roe_hurdle, abs=1e-12)


def test_roe_is_ead_invariant():
    r = 0.11
    assert (profit_waterfall(PD, 1e4, r, M)["roe"]
            == pytest.approx(profit_waterfall(PD, 1e7, r, M)["roe"]))


def test_price_loan_flags_mispricing():
    hc = hurdle_clearing_rate(PD, EAD, M)
    below = price_loan(PD, EAD, hc - 0.01, M)
    above = price_loan(PD, EAD, hc + 0.01, M)
    assert below["mispriced"] and not above["mispriced"]
    assert below["rate_shortfall"] == pytest.approx(0.01)
    assert above["rate_shortfall"] == 0.0
    assert recommended_rate(PD, EAD, M) == pytest.approx(hc + M.base_margin)


def test_ead_must_be_positive():
    with pytest.raises(ValueError):
        profit_waterfall(PD, 0.0, 0.10, M)
