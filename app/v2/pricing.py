"""Per-loan pricing read path: the full profit waterfall, in dollars and bps.

price_population (pricing/src/portfolio.py) keeps only scalars -- roe_at_quoted,
recommended_rate, clears_hurdle -- and throws the rest of the waterfall away.
price_loan already computes all of it, so this module just stops discarding it.

price_one is shared by the read path (pricing_detail, below) and Task 7's what-if
path, so the two cannot diverge -- an empty override must reproduce this exactly.
"""
from __future__ import annotations

from shared.config import MARKET
from pricing.src.engine import (
    MarketAssumptions, price_loan, break_even_rate, hurdle_clearing_rate,
)
from app.v2.explain import _booked_row

_MARKET = MarketAssumptions.from_market(MARKET)

WATERFALL_LINES = ["interest_income", "cost_of_funds", "expected_loss",
                   "operating_cost", "pre_tax_profit", "tax", "net_income",
                   "allocated_equity"]


def price_one(app_state, business_id: str, market: MarketAssumptions,
              quoted_rate: float | None = None) -> dict:
    """Price one loan through the shared engine. Used by both the read path and the
    what-if path so they cannot diverge."""
    p = app_state.profiles.loc[business_id]
    pd_value = float(app_state.scores.loc[business_id, "pd"])
    ead = float(p["requested_amount"])
    rate = float(p["risk_based_rate"]) if quoted_rate is None else float(quoted_rate)
    r = price_loan(pd_=pd_value, ead=ead, quoted_rate=rate, market=market)
    w = r["waterfall_quoted"]
    return {
        "business_id": business_id,
        "ead": ead,
        "pd": round(pd_value, 6),
        "rates": {
            "quoted": rate,
            "break_even": break_even_rate(pd_value, ead, market),
            "hurdle_clearing": r["hurdle_clearing_rate"],
            "recommended": r["recommended_rate"],
        },
        "waterfall": [{"line": k, "dollars": float(w[k]),
                       "bps": float(w[k]) / ead * 10_000} for k in WATERFALL_LINES],
        "verdict": {
            "roe": r["roe_at_quoted"],
            "raroc": r["raroc_at_quoted"],
            "clears_hurdle": r["clears_hurdle"],
            "rate_shortfall_bps": r["rate_shortfall"] * 10_000,
            "roe_hurdle": market.roe_hurdle,
        },
        "market": market.to_dict(),
    }


def pricing_detail(app_state, business_id: str):
    _, booked = _booked_row(app_state, business_id)
    if not booked:
        return None
    return price_one(app_state, business_id, _MARKET)
