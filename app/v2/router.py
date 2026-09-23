"""v2 loan workbench API. All endpoints under /api/v2.

Read endpoints assemble one loan's explanation on demand. What-if endpoints take an
overrides body and call the same module function the batch pipeline calls, so an
empty override body must reproduce the batch numbers exactly.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.v2 import explain, ews, ews_whatif, line_increase, loans, pricing, whatif

router = APIRouter(prefix="/api/v2", tags=["v2"])

# A second, prefix-less router for the page itself: include_router applies the
# parent's prefix, so /v2 cannot hang off the /api/v2 router above.
_STATIC = Path(__file__).resolve().parent.parent / "static" / "v2"

page_router = APIRouter(tags=["v2"])


@page_router.get("/v2", include_in_schema=False)
def v2_page():
    return FileResponse(_STATIC / "index.html")


def _guard(fn, app_state, business_id, *rest):
    """Every loan endpoint turns an unknown id into a 404 the same way. The extra
    args carry a what-if overrides body once Task 5 adds one.

    Catches only UnknownLoan, never bare KeyError: a KeyError from anywhere else in a
    detail function is a bug and must reach the client as a 500 with a traceback.
    Reporting it as 404 would tell the demo audience a loan does not exist while it
    sits in the dropdown in front of them.
    """
    try:
        return fn(app_state, business_id, *rest)
    except explain.UnknownLoan:
        raise HTTPException(404, f"unknown business_id {business_id}")
    except whatif.InvalidOverride as e:
        raise HTTPException(422, str(e))


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


@router.get("/loan/{business_id}/decision")
def loan_decision(request: Request, business_id: str):
    return _guard(explain.decision_detail, request.app.state, business_id)


@router.post("/loan/{business_id}/decision/whatif")
def decision_whatif(request: Request, business_id: str,
                    overrides: whatif.DecisionOverrides):
    return _guard(whatif.decision_whatif, request.app.state, business_id, overrides)


@router.get("/loan/{business_id}/pricing")
def loan_pricing(request: Request, business_id: str):
    return _guard(pricing.pricing_detail, request.app.state, business_id)


@router.post("/loan/{business_id}/pricing/whatif")
def pricing_whatif(request: Request, business_id: str,
                   overrides: whatif.PricingOverrides):
    return _guard(whatif.pricing_whatif, request.app.state, business_id, overrides)


@router.get("/loan/{business_id}/ews")
def loan_ews(request: Request, business_id: str):
    return _guard(ews.ews_detail, request.app.state, business_id)


@router.post("/loan/{business_id}/ews/whatif")
def ews_whatif_endpoint(request: Request, business_id: str,
                        overrides: ews_whatif.EwsOverrides):
    # Named _endpoint, not ews_whatif: that name is the imported module's, and a
    # module-level def would shadow it, breaking the ews_whatif.ews_whatif call below.
    return _guard(ews_whatif.ews_whatif, request.app.state, business_id, overrides)


@router.get("/loan/{business_id}/line-increase")
def loan_line_increase(request: Request, business_id: str):
    return _guard(line_increase.line_increase_detail, request.app.state, business_id)
