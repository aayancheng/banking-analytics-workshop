"""Per-loan read path: assemble what one screen needs, on demand.

Each function takes the FastAPI app.state and a business_id and returns a plain dict.
The on-book functions return None for an applicant that was never booked, which the
UI renders as "never funded" rather than as an error.
"""
from __future__ import annotations


def _row(app_state, business_id: str):
    return app_state.profiles.loc[business_id]   # raises KeyError if unknown


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
