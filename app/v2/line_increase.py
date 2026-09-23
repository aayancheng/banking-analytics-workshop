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

from line_increase.src import amount_rules
from line_increase.src.amount_rules import incremental_roe
from app.v2.display import display_precision
from app.v2.li_amounts import amount_steps, caps
from app.v2.explain import _booked_row

_LI_WATERFALL = ["interest_income", "cost_of_funds", "expected_loss",
                 "operating_cost", "pre_tax_profit", "tax", "net_income",
                 "allocated_equity"]


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
    # Fix round 1 (display-precision review): candidates.score_population decides
    # eligibility on the model's UNROUNDED probability but persists `prob` rounded to
    # 4dp -- reading that column here made this clause disagree with the verdict it
    # exists to explain, the same defect pd_within_appetite already had for the same
    # reason. app_state.v2.li_prob_raw (app/v2/state.py) is that unrounded value,
    # computed the same way candidates.py computes it.
    prob_raw = float(app_state.v2.li_prob_raw.loc[business_id])
    r = incremental_roe(pd_exact, float(li["recommended_amount"]),
                        float(li["utilization_onbook"]), float(li["rate"]))
    w = r["waterfall"]
    ead = float(r["incremental_ead"])
    hurdle = float(amount_rules._MARKET.roe_hurdle)
    cap_rows = caps(float(li["current_balance"]), float(li["credit_limit"]),
                    float(app_state.profiles.loc[business_id, "annual_revenue"]))

    def _clause(name, value, threshold, comparator, passed):
        # display_precision (app/v2/display.py) picks the fewest decimals that keep
        # `value` and `threshold` from printing identically next to a strict
        # comparator -- the fix for the same class of defect EWS's RISING_UTILIZATION
        # had (a fired trigger reading "0.15 > 0.15"). `pass` is always the argument
        # passed in, never derived from the precision it returns.
        prec = display_precision(value, threshold)
        return {"name": name, "value": value, "threshold": threshold,
                "comparator": comparator, "pass": bool(passed),
                "dp": prec["dp"], "tied": prec["tied"]}

    clauses = [
        _clause("prob_above_threshold", prob_raw, meta["offer_threshold"], ">=",
                prob_raw >= meta["offer_threshold"]),
        # Unrounded, for the same reason as prob above: candidates tests the
        # unrounded pd_score against this cap, so using the persisted 4dp value makes
        # the clause disagree with the module. On BIZ101719 (exact 0.0741049689, cap
        # 0.0741) the rounded value reads as PASS while the batch excluded the loan
        # for precisely this reason -- and `eligible == all(pass)` cannot catch it,
        # because two other clauses also fail, so the verdict stays right while the
        # REASON is wrong. A tab whose whole job is to say which clause stopped the
        # offer must not name the wrong one.
        _clause("pd_within_appetite", pd_exact, meta["offer_max_pd"], "<=",
                pd_exact <= meta["offer_max_pd"]),
        _clause("amount_positive", float(li["recommended_amount"]), 0.0, ">",
                float(li["recommended_amount"]) > 0),
        # The hurdle incremental_roe's verdict actually tested: its default market,
        # amount_rules._MARKET (built from MARKET), not LINE_INCREASE["roe_hurdle"]
        # -- equal today, but a threshold printed from a different source than the
        # verdict is a disagreement waiting for the first config edit.
        _clause("clears_hurdle", float(r["roe"]), hurdle, ">=", r["clears_hurdle"]),
    ]
    roe_prec = display_precision(float(r["roe"]), hurdle)
    return {
        "business_id": business_id,
        "optional_module": True,
        "prob": float(li["prob"]),
        "credit_limit": float(li["credit_limit"]),
        "current_balance": float(li["current_balance"]),
        "utilization_onbook": float(li["utilization_onbook"]),
        "caps": cap_rows,
        "amount_steps": amount_steps(cap_rows, float(li["recommended_amount"])),
        "recommended_amount": float(li["recommended_amount"]),
        "incremental": {
            "ead": ead,
            "waterfall": ([{"line": k, "dollars": float(w[k])} for k in _LI_WATERFALL]
                          if ead > 0 else []),
            "roe": float(r["roe"]),
            "roe_hurdle": hurdle, "dp": roe_prec["dp"], "tied": roe_prec["tied"],
            "clears_hurdle": bool(r["clears_hurdle"]),
        },
        "eligibility": {"clauses": clauses,
                        "eligible": bool(li["eligible"])},
        "drivers": [{"feature": x["feature"], "impact": x["impact"]}
                    for x in li["top_shap_reasons"]],
        "cohort": meta["cohort"],
    }
