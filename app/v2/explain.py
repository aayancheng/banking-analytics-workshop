"""Per-loan read path: assemble what one screen needs, on demand.

Each function takes the FastAPI app.state and a business_id and returns a plain dict.
The on-book functions return None for an applicant that was never booked, which the
UI renders as "never funded" rather than as an error.
"""
from __future__ import annotations


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
