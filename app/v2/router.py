"""v2 loan workbench API. All endpoints under /api/v2.

Read endpoints assemble one loan's explanation on demand. What-if endpoints take an
overrides body and call the same module function the batch pipeline calls, so an
empty override body must reproduce the batch numbers exactly.
"""
from fastapi import APIRouter, HTTPException, Request

from app.v2 import explain, loans

router = APIRouter(prefix="/api/v2", tags=["v2"])


def _guard(fn, app_state, business_id, *rest):
    """Every loan endpoint turns an unknown id into a 404 the same way. The extra
    args carry a what-if overrides body once Task 5 adds one."""
    try:
        return fn(app_state, business_id, *rest)
    except KeyError:
        raise HTTPException(404, f"unknown business_id {business_id}")


@router.get("/health")
def health(request: Request):
    st = request.app.state
    return {
        "applicants": int(len(st.profiles)),
        "booked": int(len(st.priced)),
        "panel_accounts": int(st.v2.panel.index.nunique()),
        "panel_months": int(st.v2.panel["month_index"].nunique()),
    }


@router.get("/filters")
def filters(request: Request):
    return loans.facets(request.app.state.v2.index)


@router.get("/loans")
def loan_list(request: Request, decision: str | None = None, score_band: str | None = None,
              industry: str | None = None, region: str | None = None,
              booked: str | None = None, ews_tier: str | None = None,
              mispriced: str | None = None, li_eligible: str | None = None,
              q: str | None = None, limit: int = 200):
    return loans.search(request.app.state.v2.index, decision=decision,
                        score_band=score_band, industry=industry, region=region,
                        booked=booked, ews_tier=ews_tier, mispriced=mispriced,
                        li_eligible=li_eligible, q=q, limit=min(limit, 500))


@router.get("/loan/{business_id}")
def loan_header(request: Request, business_id: str):
    return _guard(explain.header, request.app.state, business_id)
