"""Model rationale: the two additive ledgers a decision explanation is built from.

score_ledger explains the scorecard's PD (intercept + sum(WoE x beta) == logit(pd),
exactly). shap_ledger explains the adjudication model's PD (SHAP base value + sum ==
logit(model PD), exactly). A self-contained concern, unrelated to explain.py's
orchestration role -- and explain.py has three more detail functions still to land
(Tasks 6, 8, 10), so this split happens now rather than being discovered later.
"""
from __future__ import annotations

import math

import numpy as np

from score.src.reason_codes import feature_contributions
from score.src.feature_engineering import FEATURE_COLUMNS
from adjudication.src.feature_engineering import ADJ_FEATURE_COLUMNS


def _logit(p: float) -> float:
    p = min(max(float(p), 1e-12), 1 - 1e-12)
    return math.log(p / (1 - p))


def display_triple(intercept: float, logit: float, dp: int = 4) -> dict:
    """The three numbers the ledger footer prints, rounded ON THE SERVER so they
    reconcile on screen.

    Rounding the intercept, the contributions total and the log-odds independently to
    4dp leaves the printed equation off by one in the last place on 30.5% of loans
    (measured) -- on a screen whose entire claim is that the contributions ADD UP, a
    room checking the sum by eye reads that as a bug.

    `contributions_total` is the RECONCILING RESIDUAL, round(logit) - round(intercept)
    -- not the sum of the displayed contribution bars. Each bar is rounded on its
    own for display, so adding the bars up by hand can differ from this figure in
    the last place; the unrounded contributions DO sum exactly to logit - intercept
    (tests assert 1e-9 for the scorecard, 1e-6 for SHAP). Say so if a room adds
    the bars.

    The browser must not fix that itself. Deriving a displayed number in JS is what
    this project forbids, because the number can no longer be traced to the server and
    nothing would catch it drifting. So the server does the reconciliation and hands
    over three values that print correctly as they are.
    """
    a = round(intercept, dp)
    t = round(logit, dp)
    return {"intercept": a, "contributions_total": round(t - a, dp), "logit": t, "dp": dp}


def _jsonable_value(v):
    if v is None:
        return None
    if isinstance(v, (np.integer, np.floating)):
        v = v.item()
    return v if isinstance(v, (int, float, str, bool)) else str(v)


def score_ledger(app_state, business_id: str) -> dict:
    """The scorecard's rationale: intercept + sum(WoE x beta) == logit(pd), exactly."""
    v2 = app_state.v2
    X = v2.score_X.loc[[business_id]]
    contrib = feature_contributions(v2.scorecard, X).iloc[0]
    raw = app_state.profiles.loc[business_id]
    pd_value = float(app_state.scores.loc[business_id, "pd"])
    # NOTHING here is rounded. Rounding 15 addends to 6dp and then summing them
    # breaks the identity by ~1e-6, and rounding `pd` breaks the logit recomputation
    # by up to 5.85e-4 near the tails, where d(logit)/d(pd) blows up. Rounding is a
    # DISPLAY concern and the browser already owns display -- it formats and draws but
    # never calculates.
    rows = [{"feature": str(f),
             "contribution": float(contrib[f]),
             "value": _jsonable_value(raw.get(f, X.iloc[0].get(f)))}
            for f in FEATURE_COLUMNS]
    rows.sort(key=lambda r: -r["contribution"])
    intercept = float(v2.scorecard.estimator_.intercept_[0])
    logit_pd = _logit(pd_value)
    return {
        "intercept": intercept,
        "contributions": rows,
        "pd": float(pd_value),
        "logit_pd": logit_pd,
        "display": display_triple(intercept, logit_pd),
    }


def shap_ledger(app_state, business_id: str) -> dict:
    """The LightGBM's rationale. Also exactly additive: base + sum == logit(p)."""
    v2 = app_state.v2
    X = v2.adj_X.loc[[business_id]]
    sv = v2.adj_explainer.shap_values(X)
    sv = sv[1] if isinstance(sv, list) else sv
    sv = np.asarray(sv).reshape(-1)
    base = v2.adj_explainer.expected_value
    base = float(np.ravel(base)[-1]) if np.ndim(base) > 0 else float(base)
    pd_model = float(app_state.decisions.loc[business_id, "pd"])
    # Unrounded, for the same reason as score_ledger: 21 addends rounded to 6dp and
    # then summed breach the 1e-6 identity on 62 of 120 sampled loans (worst 3.0e-6).
    rows = [{"feature": str(f), "contribution": float(c),
             "value": _jsonable_value(X.iloc[0][f])}
            for f, c in zip(ADJ_FEATURE_COLUMNS, sv)]
    rows.sort(key=lambda r: -r["contribution"])
    logit_pd_model = _logit(pd_model)
    return {"base_value": float(base), "contributions": rows,
            "pd_model": float(pd_model),
            "logit_pd_model": logit_pd_model,
            "display": display_triple(float(base), logit_pd_model)}
