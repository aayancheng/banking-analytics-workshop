"""Pure, deterministic line-increase amount rules + incremental-ROE gate.

The recommended amount is headroom-to-target-utilization, capped by a percentage of the
current limit and a revenue-based ceiling. The incremental-ROE gate prices the incremental
exposure with the shared pricing engine. NOTE: pricing ROE/RAROC are EAD-invariant (depend
only on pd & rate), so the drawdown assumption scales the *dollar* figures, not the ROE
ratio. No ML here; no engine logic redefined."""
from __future__ import annotations

from shared.config import LINE_INCREASE, MARKET
from pricing.src.engine import MarketAssumptions, profit_waterfall, hurdle_clearing_rate

CFG = LINE_INCREASE
_MARKET = MarketAssumptions.from_market(MARKET)

_WATERFALL_KEYS = (
    "interest_income", "cost_of_funds", "expected_loss", "operating_cost",
    "pre_tax_profit", "tax", "net_income", "allocated_equity", "roe", "raroc",
)


def recommended_amount(current_balance: float, credit_limit: float,
                       annual_revenue: float, cfg: dict = CFG) -> float:
    """Increase (Δlimit) that brings utilization to cfg['target_util'], capped by
    cfg['pct_cap']*limit and a revenue ceiling, floored at 0, rounded to cfg['round_to']."""
    if credit_limit <= 0:
        return 0.0
    target_limit = current_balance / cfg["target_util"]
    raw_delta = target_limit - credit_limit
    pct_cap = cfg["pct_cap"] * credit_limit
    revenue_ceiling = cfg["revenue_mult_cap"] * annual_revenue - credit_limit
    delta = min(raw_delta, pct_cap, revenue_ceiling)
    if delta <= 0:
        return 0.0
    rnd = cfg["round_to"]
    return float(round(delta / rnd) * rnd)


def incremental_exposure(delta_amount: float, utilization_onbook: float) -> float:
    """EAD of the incremental limit: drawn at current on-book utilization (clipped 0-1)."""
    util = min(max(float(utilization_onbook), 0.0), 1.0)
    return float(delta_amount) * util


def waterfall_or_zero(pd_: float, ead: float, rate: float,
                      market: MarketAssumptions = _MARKET) -> dict:
    """profit_waterfall when ead > 0, else an all-zero waterfall (engine rejects ead<=0)."""
    if ead > 0:
        return profit_waterfall(pd_, ead, rate, market)
    return {k: 0.0 for k in _WATERFALL_KEYS}


def incremental_roe(pd_: float, delta_amount: float, utilization_onbook: float,
                    rate: float, market: MarketAssumptions = _MARKET) -> dict:
    """Price the incremental exposure. Returns incremental_ead, roe (EAD-invariant),
    clears_hurdle, incremental_net_income, hurdle_clearing_rate, and the waterfall."""
    ead = incremental_exposure(delta_amount, utilization_onbook)
    w = waterfall_or_zero(pd_, ead, rate, market)
    return {
        "incremental_ead": ead,
        "roe": w["roe"],
        "clears_hurdle": bool(ead > 0 and w["roe"] >= market.roe_hurdle),
        "incremental_net_income": w["net_income"],
        "hurdle_clearing_rate": hurdle_clearing_rate(pd_, max(ead, 1.0), market),
        "waterfall": w,
    }
