"""Per-loan read path: assemble what one screen needs, on demand.

Each function takes the FastAPI app.state and a business_id and returns a plain dict.
The on-book functions return None for an applicant that was never booked, which the
UI renders as "never funded" rather than as an error.
"""
from __future__ import annotations

import math

import numpy as np

from score.src.reason_codes import feature_contributions
from score.src.feature_engineering import FEATURE_COLUMNS
from adjudication.src.feature_engineering import ADJ_FEATURE_COLUMNS
from app.v2 import rules


class UnknownLoan(KeyError):
    """The business_id is not in the population.

    A dedicated type, rather than a bare KeyError, because the router turns this into
    a 404. Every other KeyError raised inside a detail function -- a renamed column, a
    typo in a metadata path -- is a bug and must surface as a 500 with a traceback, not
    as "unknown business_id" for a loan the user can see in the dropdown.
    """


def _row(app_state, business_id: str):
    """The profile row, or UnknownLoan. Every entry point looks a loan up through
    this, which is what makes the narrow catch in the router safe."""
    try:
        return app_state.profiles.loc[business_id]
    except KeyError:
        raise UnknownLoan(business_id) from None


def header(app_state, business_id: str) -> dict:
    p = _row(app_state, business_id)
    s = app_state.scores.loc[business_id]
    d = app_state.decisions.loc[business_id]
    booked = bool(p["booked"])
    return {
        "business_id": business_id,
        "identity": {
            "industry": str(p["industry"]), "region": str(p["region"]),
            "entity_type": str(p["entity_type"]),
            "years_in_business": float(p["years_in_business"]),
        },
        "terms": {
            "requested_amount": float(p["requested_amount"]),
            "term_months": int(p["term_months"]),
            "loan_purpose": str(p["loan_purpose"]),
            "collateral_flag": bool(p["collateral_flag"]),
        },
        "score": {
            "business_score": int(s["business_score"]),
            "score_band": str(s["score_band"]),
            "pd": round(float(s["pd"]), 4),
        },
        "decision": str(d["decision"]),
        "booked": booked,
        "modules_present": ["score", "adjudication"] + (
            ["pricing", "ews", "line_increase"] if booked else []),
    }


def _logit(p: float) -> float:
    p = min(max(float(p), 1e-12), 1 - 1e-12)
    return math.log(p / (1 - p))


def _zone(pd_value: float, config) -> str:
    if pd_value <= config.t_low:
        return "Approve"
    if pd_value >= config.t_high:
        return "Decline"
    return "Refer"


def _jsonable_value(v):
    if v is None:
        return None
    if isinstance(v, (np.integer, np.floating)):
        v = v.item()
    return v if isinstance(v, (int, float, str, bool)) else str(v)


def score_ledger(app_state, business_id: str) -> dict:
    """intercept + sum(WoE x beta) == logit(pd), exactly. contribution/intercept/
    logit_pd stay at full float precision -- rounding each of the 16 addends to 6dp
    before summing breaks the identity by ~1e-6, past a 1e-9 exactness test."""
    v2 = app_state.v2
    X = v2.score_X.loc[[business_id]]
    contrib = feature_contributions(v2.scorecard, X).iloc[0]
    raw = app_state.profiles.loc[business_id]
    pd_value = float(app_state.scores.loc[business_id, "pd"])
    rows = [{"feature": str(f),
             "contribution": float(contrib[f]),
             "value": _jsonable_value(raw.get(f, X.iloc[0].get(f)))}
            for f in FEATURE_COLUMNS]
    rows.sort(key=lambda r: -r["contribution"])
    return {
        "intercept": float(v2.scorecard.estimator_.intercept_[0]),
        "contributions": rows,
        "pd": round(pd_value, 6),
        "logit_pd": _logit(pd_value),
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
    rows = [{"feature": str(f), "contribution": round(float(c), 6),
             "value": _jsonable_value(X.iloc[0][f])}
            for f, c in zip(ADJ_FEATURE_COLUMNS, sv)]
    rows.sort(key=lambda r: -r["contribution"])
    return {"base_value": round(base, 6), "contributions": rows,
            "pd_model": round(pd_model, 6),
            "logit_pd_model": round(_logit(pd_model), 6)}


def decision_detail(app_state, business_id: str) -> dict:
    p = _row(app_state, business_id)
    s = app_state.scores.loc[business_id]
    d = app_state.decisions.loc[business_id]
    config = app_state.policy_config
    pd_model = float(d["pd"])
    zone = _zone(pd_model, config)
    led = rules.ledger(p, s, config, zone)
    return {
        "business_id": business_id,
        "decision": str(d["decision"]),
        "rule_hits": list(d["decision_reasons"]),
        "pd_zones": {"t_low": float(config.t_low), "t_high": float(config.t_high),
                     "pd": round(pd_model, 6), "zone": zone},
        "rules": led,
        "score_ledger": score_ledger(app_state, business_id),
        "shap": shap_ledger(app_state, business_id),
        "nearest_flip": rules.nearest_flip(led, pd_model, config),
    }
