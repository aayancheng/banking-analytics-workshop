"""Analytical pricing & profitability engine: expected-loss pricing + ROE/RAROC profit
waterfall + hurdle-clearing rate solver + mispricing detection. Pure, deterministic;
no ML. EAD is a positive scale factor; ROE/RAROC are EAD-invariant ratios."""
from __future__ import annotations
from dataclasses import dataclass, replace, fields


@dataclass(frozen=True)
class MarketAssumptions:
    cost_of_funds: float
    lgd: float
    opex_rate: float
    tax_rate: float
    capital_ratio: float
    base_margin: float
    roe_hurdle: float
    fee_rate: float = 0.0

    @classmethod
    def from_market(cls, market: dict) -> "MarketAssumptions":
        names = {f.name for f in fields(cls)}
        return cls(**{k: market[k] for k in names if k in market})

    def replace(self, **kw) -> "MarketAssumptions":
        return replace(self, **kw)

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}


def profit_waterfall(pd_: float, ead: float, rate: float, market: MarketAssumptions) -> dict:
    if ead <= 0:
        raise ValueError("ead must be > 0")
    m = market
    interest_income = (rate + m.fee_rate) * ead
    cost_of_funds = m.cost_of_funds * ead
    expected_loss = pd_ * m.lgd * ead
    operating_cost = m.opex_rate * ead
    pre_tax = interest_income - cost_of_funds - expected_loss - operating_cost
    net_income = pre_tax * (1 - m.tax_rate)
    allocated_equity = m.capital_ratio * ead
    return {
        "interest_income": interest_income,
        "cost_of_funds": cost_of_funds,
        "expected_loss": expected_loss,
        "operating_cost": operating_cost,
        "pre_tax_profit": pre_tax,
        "tax": pre_tax * m.tax_rate,
        "net_income": net_income,
        "allocated_equity": allocated_equity,
        "roe": net_income / allocated_equity,
        "raroc": pre_tax / allocated_equity,
    }


def break_even_rate(pd_: float, ead: float, market: MarketAssumptions) -> float:
    """Rate where ROE == 0 (covers COF + EL + opex, net of fees)."""
    m = market
    return m.cost_of_funds + pd_ * m.lgd + m.opex_rate - m.fee_rate


def hurdle_clearing_rate(pd_: float, ead: float, market: MarketAssumptions) -> float:
    """Rate where ROE == roe_hurdle."""
    m = market
    return (m.cost_of_funds + pd_ * m.lgd + m.opex_rate - m.fee_rate
            + m.roe_hurdle * m.capital_ratio / (1 - m.tax_rate))


def recommended_rate(pd_: float, ead: float, market: MarketAssumptions) -> float:
    """Hurdle-clearing rate plus the risk-based base margin cushion."""
    return hurdle_clearing_rate(pd_, ead, market) + market.base_margin


def price_loan(pd_: float, ead: float, quoted_rate: float, market: MarketAssumptions) -> dict:
    rec = recommended_rate(pd_, ead, market)
    hc = hurdle_clearing_rate(pd_, ead, market)
    w_quoted = profit_waterfall(pd_, ead, quoted_rate, market)
    w_rec = profit_waterfall(pd_, ead, rec, market)
    clears = w_quoted["roe"] >= market.roe_hurdle
    return {
        "pd": pd_,
        "ead": ead,
        "quoted_rate": quoted_rate,
        "recommended_rate": rec,
        "hurdle_clearing_rate": hc,
        "roe_at_quoted": w_quoted["roe"],
        "raroc_at_quoted": w_quoted["raroc"],
        "roe_at_recommended": w_rec["roe"],
        "clears_hurdle": bool(clears),
        "mispriced": bool(not clears),
        "rate_shortfall": max(0.0, hc - quoted_rate),
        "waterfall_quoted": w_quoted,
        "waterfall_recommended": w_rec,
    }
