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
from app.v2.display import display_precision
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
    hc = r["hurdle_clearing_rate"]
    # Final review T13: the engine's rate_shortfall is max(0, hc - quoted), so a
    # clearing loan always read "Shortfall 0 bps" (2,534 of them) and BIZ103012,
    # short by a true 0.04 bps, read "short by 0 bps". rate_margin_bps is SIGNED
    # (positive = quoted above the hurdle-clearing rate), computed here without
    # touching pricing/src/engine.py; rate_shortfall_bps stays for compatibility.
    margin_bps = (rate - hc) * 10_000
    # Every comparison this payload prints gets a server-chosen precision (I3):
    # ROE vs hurdle, quoted vs hurdle-clearing on the ladder, and the margin vs 0
    # -- the fewest decimals at which a non-zero margin cannot print as "0 bps".
    roe_prec = display_precision(r["roe_at_quoted"], market.roe_hurdle)
    margin_prec = display_precision(margin_bps, 0.0, base_dp=0)
    return {
        "business_id": business_id,
        "ead": ead,
        "pd": round(pd_value, 6),
        "rates": {
            "quoted": rate,
            "break_even": break_even_rate(pd_value, ead, market),
            "hurdle_clearing": hc,
            "recommended": r["recommended_rate"],
            "dp": display_precision(rate, hc)["dp"],
        },
        "waterfall": [{"line": k, "dollars": float(w[k]),
                       "bps": float(w[k]) / ead * 10_000} for k in WATERFALL_LINES],
        "verdict": {
            "roe": r["roe_at_quoted"],
            "raroc": r["raroc_at_quoted"],
            "clears_hurdle": r["clears_hurdle"],
            "rate_shortfall_bps": r["rate_shortfall"] * 10_000,
            "rate_margin_bps": margin_bps,
            "margin_dp": margin_prec["dp"], "margin_tied": margin_prec["tied"],
            "roe_hurdle": market.roe_hurdle,
            "roe_dp": roe_prec["dp"], "roe_tied": roe_prec["tied"],
        },
        "market": market.to_dict(),
    }


def pricing_detail(app_state, business_id: str):
    _, booked = _booked_row(app_state, business_id)
    if not booked:
        return None
    return price_one(app_state, business_id, _MARKET)
