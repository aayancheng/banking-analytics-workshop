"""Adjudication policy decision layer: model PD + affordability + bureau signals ->
Approve / Refer / Decline, with rule-hit reason strings. Pure and vectorized.

Decision order:
  1. Hard knockouts -> force Decline (record every rule that fires).
  2. PD zones: pd<=t_low -> Approve, pd>=t_high -> Decline, else Refer.
  3. Refer overrides: only downgrade an Approve to Refer (never upgrade a Decline).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PolicyConfig:
    t_low: float
    t_high: float
    dscr_floor: float
    dscr_refer_hi: float
    public_records_cap: int
    prior_delinq_cap: int
    leverage_cap: float
    req_to_rev_cap: float
    score_floor: float

    @classmethod
    def from_dict(cls, d: dict) -> "PolicyConfig":
        return cls(**{f: d[f] for f in cls.__dataclass_fields__})

    def to_dict(self) -> dict:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}


def decide(df: pd.DataFrame, pd_model, config: PolicyConfig) -> pd.DataFrame:
    """Return DataFrame[decision, decision_reasons, pd] aligned to df.index."""
    n = len(df)
    pd_model = np.asarray(pd_model, dtype=float)
    reasons = [[] for _ in range(n)]

    g = lambda col, default=0.0: (
        pd.to_numeric(df[col], errors="coerce").fillna(default).to_numpy()
        if col in df.columns else np.full(n, default)
    )
    dscr = g("dscr"); lev = g("leverage")
    pubrec = g("public_records"); delinq = g("prior_delinquencies")
    score = g("business_score", config.score_floor)
    req = g("requested_amount"); rev = np.maximum(g("annual_revenue"), 1.0)

    # --- 1. hard knockouts ---
    knockout = np.zeros(n, dtype=bool)
    def fire(mask, msg):
        for i in np.nonzero(mask)[0]:
            reasons[i].append(msg)
    m = dscr < config.dscr_floor; fire(m, f"dscr<{config.dscr_floor}"); knockout |= m
    m = pubrec > config.public_records_cap; fire(m, "public_records present"); knockout |= m
    m = delinq >= config.prior_delinq_cap; fire(m, f"prior_delinquencies>={config.prior_delinq_cap}"); knockout |= m
    m = lev > config.leverage_cap; fire(m, f"leverage>{config.leverage_cap}"); knockout |= m

    # --- 2. PD zones ---
    decision = np.where(pd_model <= config.t_low, "Approve",
               np.where(pd_model >= config.t_high, "Decline", "Refer")).astype(object)

    # --- 3. refer overrides (only on current Approve) ---
    appr = decision == "Approve"
    thin_dscr = appr & (dscr >= config.dscr_floor) & (dscr < config.dscr_refer_hi)
    fire(thin_dscr, "thin affordability margin (dscr)")
    low_score = appr & (score < config.score_floor)
    fire(low_score, "weak credit score")
    big_req = appr & (req / rev > config.req_to_rev_cap)
    fire(big_req, "large request vs revenue")
    decision[thin_dscr | low_score | big_req] = "Refer"

    # knockouts win over everything
    decision[knockout] = "Decline"

    return pd.DataFrame(
        {"decision": decision, "decision_reasons": reasons, "pd": pd_model},
        index=df.index,
    )
