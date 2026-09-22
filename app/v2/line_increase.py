"""Per-loan line-increase read path: the recommended amount with its three ceilings
so the binding one is visible, and eligibility spelled out as four ANDed clauses
instead of a single number.

This module is optional in the curriculum -- skippable live without leaving a hole --
but its job is exactly the documented gap: 95 accounts are `eligible`, 1,243 have
`recommended_amount > 0`. candidates() (line_increase/src/candidates.py) is the
authority on `eligible`; a positive amount is not. Showing the four clauses that make
up `eligible` -- prob_above_threshold, pd_within_appetite, amount_positive,
clears_hurdle -- in the same order candidates() ANDs them is what makes that gap
legible instead of a footnote.

`eligible` is always app_state.li's own verdict, never recomputed here -- the clauses
explain it, they never decide it, mirroring ews.py's fired/met split for triggers.
"""
from __future__ import annotations

from shared.config import LINE_INCREASE
from line_increase.src.amount_rules import incremental_roe
from app.v2.explain import _booked_row

_LI_WATERFALL = ["interest_income", "cost_of_funds", "expected_loss",
                 "operating_cost", "pre_tax_profit", "tax", "net_income",
                 "allocated_equity"]


def _caps(current_balance: float, credit_limit: float, annual_revenue: float,
          cfg: dict = LINE_INCREASE) -> list[dict]:
    """The three ceilings recommended_amount() takes the min of, each shown so the
    binding one is visible instead of inferred."""
    if credit_limit <= 0:
        return []
    values = {
        "headroom_to_target_util": current_balance / cfg["target_util"] - credit_limit,
        "pct_cap": cfg["pct_cap"] * credit_limit,
        "revenue_ceiling": cfg["revenue_mult_cap"] * annual_revenue - credit_limit,
    }
    lowest = min(values.values())
    return [{"name": k, "amount": round(float(v), 2), "binding": v == lowest}
            for k, v in values.items()]


def line_increase_detail(app_state, business_id: str):
    _, booked = _booked_row(app_state, business_id)
    if not booked:
        return None
    li = app_state.li.loc[business_id]
    meta = app_state.li_meta
    # The UNROUNDED scorecard PD, not li["pd"]. candidates.score_population computes
    # the incremental ROE from the unrounded pd_score but persists `pd` rounded to
    # 4dp, so recomputing from the stored column silently disagrees with the batch by
    # up to 1.4e-4 -- and on one of the 1,243 loans with a positive amount that is
    # enough to flip clears_hurdle, which is the fourth eligibility clause. Same
    # family as the EWS tier-rounding defect: the persisted number is a display
    # value, and reusing it as an input is how a screen quietly stops matching the
    # pipeline it claims to mirror.
    pd_exact = float(app_state.scores.loc[business_id, "pd"])
    r = incremental_roe(pd_exact, float(li["recommended_amount"]),
                        float(li["utilization_onbook"]), float(li["rate"]))
    w = r["waterfall"]
    ead = float(r["incremental_ead"])
    clauses = [
        {"name": "prob_above_threshold", "value": float(li["prob"]),
         "threshold": meta["offer_threshold"], "comparator": ">=",
         "pass": bool(float(li["prob"]) >= meta["offer_threshold"])},
        # Unrounded, for the same reason as the ROE above: candidates tests the
        # unrounded pd_score against this cap, so using the persisted 4dp value makes
        # the clause disagree with the module. On BIZ101719 (exact 0.0741049689, cap
        # 0.0741) the rounded value reads as PASS while the batch excluded the loan
        # for precisely this reason -- and `eligible == all(pass)` cannot catch it,
        # because two other clauses also fail, so the verdict stays right while the
        # REASON is wrong. A tab whose whole job is to say which clause stopped the
        # offer must not name the wrong one.
        {"name": "pd_within_appetite", "value": pd_exact,
         "threshold": meta["offer_max_pd"], "comparator": "<=",
         "pass": bool(pd_exact <= meta["offer_max_pd"])},
        {"name": "amount_positive", "value": float(li["recommended_amount"]),
         "threshold": 0.0, "comparator": ">",
         "pass": bool(float(li["recommended_amount"]) > 0)},
        {"name": "clears_hurdle", "value": float(r["roe"]),
         "threshold": LINE_INCREASE["roe_hurdle"], "comparator": ">=",
         "pass": bool(r["clears_hurdle"])},
    ]
    return {
        "business_id": business_id,
        "optional_module": True,
        "prob": float(li["prob"]),
        "credit_limit": float(li["credit_limit"]),
        "current_balance": float(li["current_balance"]),
        "utilization_onbook": float(li["utilization_onbook"]),
        "caps": _caps(float(li["current_balance"]), float(li["credit_limit"]),
                      float(app_state.profiles.loc[business_id, "annual_revenue"])),
        "recommended_amount": float(li["recommended_amount"]),
        "incremental": {
            "ead": ead,
            "waterfall": ([{"line": k, "dollars": float(w[k])} for k in _LI_WATERFALL]
                          if ead > 0 else []),
            "roe": float(r["roe"]),
            "clears_hurdle": bool(r["clears_hurdle"]),
        },
        "eligibility": {"clauses": clauses,
                        "eligible": bool(li["eligible"])},
        "drivers": [{"feature": x["feature"], "impact": x["impact"]}
                    for x in li["top_shap_reasons"]],
        "cohort": meta["cohort"],
    }
