# v2 Loan Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a loan-level workbench at `/v2` — pick one loan through a filtered dropdown, then see its decision, its pricing and profitability, and its early-warning history on four tabs, every parameter live and recomputed server-side — while the v1 portal keeps working verbatim for side-by-side demo.

**Architecture:** A new `app/v2/` package and `app/static/v2/` page mounted into the *existing* FastAPI service. `app/main.py` gains four statements and is not otherwise touched. Read endpoints assemble per-loan explanations on demand (2–3ms); what-if endpoints take an overrides body and call **the same module function the batch pipeline calls**, so the two can never drift. No client-side financial arithmetic, no build step, no CDN.

**Tech Stack:** Python 3.13, FastAPI + Pydantic, pandas, joblib, shap, optbinning (all already in `requirements.txt` — this plan adds no dependency). Front end is hand-written HTML/CSS/JS with inline SVG, no framework.

**Spec:** `docs/superpowers/specs/2026-09-22-v2-loan-workbench-design.md` — read it first; this plan argues from it.

## Global Constraints

Every task's requirements implicitly include all of these.

- **No financial arithmetic in JavaScript.** Every computed number on screen comes from a server response. The browser formats and draws; it never calculates ROE, PD, a threshold comparison, or a waterfall line.
- **Never re-implement a module.** v2 calls `price_loan`, `policy.decide`, `flag_triggers`, `risk_tier`, `recommended_amount`, `incremental_roe`, `feature_contributions`. If v2 and the batch pipeline disagree, that is a bug (repo invariant 5).
- **v1 is untouchable.** `app/main.py` gains exactly four statements: the import, one lifespan line, `include_router`, and the `/static/v2` mount. No refactor, no reformat, no reordering. `verify.py:350` imports `app.main:app` and must keep working.
- **No new dependency.** Not in `requirements.txt`, not from a CDN. The page must work offline in a devcontainer/Codespace.
- **No new model, gate, or committed artifact.** v2 reads what the modules already produce.
- **`app/v2/` is `main`-only.** Stage tags never move (repo invariant 1). Anything added to `verify.py` must be guarded on `(ROOT / "app" / "v2").exists()` so stage-0..stage-5 are unaffected.
- **Wrap every `localStorage` access in try/catch.** It throws rather than returning null in restricted contexts; an unguarded access already killed a handler once in `run-of-show-app.html`. Slider state is a convenience, never a dependency.
- **No attendee data, no real email addresses, anywhere.** This repo is public (repo invariant 6).
- **Quote metadata numbers, never recomputed ones**, when displaying model performance — `metadata.json` nests them under `["metrics"]`, not top level.
- **Every file under ~150 lines.** Split by responsibility if one grows past it.
- Commit messages: what changed and *why*, plus what was verified, ending with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. **Do not push or tag.**

## Reference values (measured, use these in tests)

| Thing | Value |
|---|---|
| Applicants / booked | 12,000 / 8,336 |
| `policy_config.json` | `t_low` 0.0955, `t_high` 0.4943, `dscr_floor` 1.0, `dscr_refer_hi` 1.2, `public_records_cap` 0, `prior_delinq_cap` 3, `leverage_cap` 6.0, `req_to_rev_cap` 0.75, `score_floor` 600 |
| `MARKET` | `cost_of_funds` 0.035, `lgd` 0.45, `opex_rate` 0.010, `tax_rate` 0.25, `capital_ratio` 0.12, `base_margin` 0.020, `roe_hurdle` 0.15, `fee_rate` 0.0 |
| `EWS_TRIGGERS` | `high_utilization` 0.90, `rising_utilization` 0.15, `dpd_severe` 30, `deposit_decline` 0.30, `overdraft_recent` 3 |
| EWS metadata | tiers `t_high` 0.5073 / `t_med` 0.1649; `base_rate` 0.1802; metrics auc 0.6622, top_decile_capture 0.2159 |
| LI metadata | `offer_threshold` 0.3121, `offer_max_pd` 0.0741, `cohort.n_offered` 95 |
| Panel | `panel.parquet`, 200,064 rows, 24 months per booked account |
| A known booked loan | `BIZ100002` (Transport, LLC, requested 209,000, rate 0.0922) |

**Additivity identities — both verified exact on this data, assert them:**
- Scorecard: `scorecard.estimator_.intercept_[0] + sum(feature_contributions) == logit(pd)` (gap 0.00e+00).
- Adjudication LightGBM: `explainer.expected_value + sum(shap_values) == logit(predict_proba)` (gap 1.3e-15).

---

### Task 1: v2 package, state, and wiring

**Files:**
- Create: `app/v2/__init__.py`, `app/v2/state.py`, `app/v2/router.py`
- Modify: `app/main.py` (four statements only)
- Test: `tests/test_app_v2.py`

**Interfaces:**
- Consumes: v1's `app.state.profiles` (DataFrame indexed by `business_id`), `app.state.scores`, `app.state.decisions`, `app.state.priced`, `app.state.ews`, `app.state.li`.
- Produces: `app.v2.state.V2State` dataclass with fields `scorecard`, `score_X`, `adj_X`, `adj_explainer`, `panel`; `app.v2.state.build_state(profiles: pd.DataFrame) -> V2State`; `app.v2.router.router` (an `APIRouter` with prefix `/api/v2`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_app_v2.py
"""v2 loan workbench — API tests.

TestClient boots the whole platform (~7.4s), so the client is module-scoped and
every test shares it.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_v1_still_works(client):
    """v2 is additive. If this breaks, v2 has damaged the side-by-side demo."""
    assert client.get("/health").json()["applicants"] == 12000
    assert client.get("/api/dashboard/summary").status_code == 200


def test_v2_health(client):
    r = client.get("/api/v2/health")
    assert r.status_code == 200
    body = r.json()
    assert body["applicants"] == 12000
    assert body["booked"] == 8336
    assert body["panel_accounts"] == 8336
    assert body["panel_months"] == 24
```

- [ ] **Step 2: Run it and watch it fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: `test_v1_still_works` PASSES, `test_v2_health` FAILS with 404.

- [ ] **Step 3: Write `app/v2/state.py`**

```python
"""v2 workbench state: the extra objects loan-level explanation needs, built once.

v1's app.state already holds the scored populations, and v2 reuses them rather than
re-scoring. v2 adds only what per-loan explanation needs: the scorecard object (for
the WoE x beta ledger), a SHAP explainer over the adjudication model, the feature
matrices to index into, and the 24-month behavioural panel.

Nothing is precomputed across the population — a per-loan explanation is 2-3ms, so
precomputing 12,000 of them would cost seconds of boot to save nothing. Measured
cost of this build: ~0.15s on top of v1's 7.4s.

adj_X is recomputed here rather than shared out of v1's lifespan. It costs 0.05s and
it keeps app/main.py at four added statements, which is the point of v2 being a
side-by-side demo rather than a rewrite.
"""
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
import shap

from shared.config import RAW
from score.src.feature_engineering import FEATURE_COLUMNS, compute_features
from adjudication.src.feature_engineering import (
    ADJ_FEATURE_COLUMNS, compute_adjudication_features,
)

ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class V2State:
    scorecard: object
    score_X: pd.DataFrame
    adj_X: pd.DataFrame
    adj_explainer: object
    panel: pd.DataFrame


def build_state(profiles: pd.DataFrame) -> V2State:
    """profiles is v1's app.state.profiles: businesses.parquet indexed by business_id."""
    scorecard = joblib.load(ROOT / "score" / "models" / "scorecard.pkl")
    score_X = compute_features(profiles)[FEATURE_COLUMNS]
    adj_X = compute_adjudication_features(profiles)[ADJ_FEATURE_COLUMNS]
    adj_model = joblib.load(ROOT / "adjudication" / "models" / "adjudication_model.pkl")
    adj_explainer = shap.TreeExplainer(adj_model)
    panel = pd.read_parquet(RAW / "panel.parquet").set_index("business_id")
    return V2State(scorecard, score_X, adj_X, adj_explainer, panel)
```

- [ ] **Step 4: Write `app/v2/router.py` with just the health endpoint**

```python
"""v2 loan workbench API. All endpoints under /api/v2.

Read endpoints assemble one loan's explanation on demand. What-if endpoints take an
overrides body and call the same module function the batch pipeline calls, so an
empty override body must reproduce the batch numbers exactly.
"""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v2", tags=["v2"])


@router.get("/health")
def health(request: Request):
    st = request.app.state
    return {
        "applicants": int(len(st.profiles)),
        "booked": int(len(st.priced)),
        "panel_accounts": int(st.v2.panel.index.nunique()),
        "panel_months": int(st.v2.panel["month_index"].nunique()),
    }
```

- [ ] **Step 5: Write `app/v2/__init__.py`**

```python
"""v2 loan workbench — loan-level screens over the same modules v1 summarises."""
```

- [ ] **Step 6: Add exactly four statements to `app/main.py`**

Add the import beside the other `app`-local imports at the top:

```python
from app.v2 import state as v2_state, router as v2_router
```

Add one line at the end of the lifespan body, immediately before `yield`:

```python
    app.state.v2 = v2_state.build_state(profiles)
```

Add after the `app = FastAPI(...)` line:

```python
app.include_router(v2_router.router)
```

Add beside the existing `app.mount(...)` at the bottom:

```python
app.mount("/static/v2", StaticFiles(directory=ROOT / "app" / "static" / "v2"), name="static_v2")
```

Create `app/static/v2/.gitkeep` so the mount has a directory to bind to before Task 11 adds the page.

- [ ] **Step 7: Run the tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: both PASS.

- [ ] **Step 8: Confirm v1 is undamaged and measure the boot cost**

Run: `PYTHONPATH=. .venv/bin/python verify.py | tail -3`
Expected: the same result as before this task — no new failures.

Run: `git diff --stat HEAD -- app/main.py`
Expected: `4 insertions(+)`, 0 deletions. Diff against `HEAD` explicitly — bare
`git diff` compares the working tree to the index, so once anything is staged or
committed it prints nothing and this check passes no matter what you changed.
If deletions appear, v1 was modified — revert and redo.

- [ ] **Step 9: Commit**

```bash
git add app/v2 app/static/v2/.gitkeep app/main.py tests/test_app_v2.py
git commit -m "v2: package skeleton, state, and wiring into the existing service

Verified: /api/v2/health returns 12000/8336/8336/24; v1 /health and
/api/dashboard/summary unchanged; app/main.py diff is 4 insertions 0 deletions;
python verify.py unchanged.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Loan index, facets, and filtered search

**Files:**
- Create: `app/v2/loans.py`
- Modify: `app/v2/router.py`, `tests/test_app_v2.py`

**Interfaces:**
- Consumes: `V2State`; v1's `app.state` frames.
- Produces: `build_index(app_state) -> pd.DataFrame` (one row per applicant, indexed by `business_id`, columns `industry, region, entity_type, score_band, decision, booked, ews_tier, mispriced, li_eligible, requested_amount, pd, business_score`); `facets(index) -> dict`; `search(index, **filters, limit=200) -> dict` returning `{"total": int, "shown": int, "loans": [...]}`. The index is built once in `build_state` and stored on `V2State` as a new field `index`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_app_v2.py
def test_facets_cover_every_filter(client):
    f = client.get("/api/v2/filters").json()
    assert set(f) == {"decision", "score_band", "industry", "region",
                      "booked", "ews_tier", "mispriced", "li_eligible"}
    assert {o["value"] for o in f["decision"]} == {"Approve", "Refer", "Decline"}
    assert {o["value"] for o in f["score_band"]} == {"AAA", "A", "B", "C", "D"}
    assert sum(o["count"] for o in f["decision"]) == 12000
    # On-book facets are scoped to the booked population, not the applicant one.
    for on_book in ("mispriced", "ews_tier", "li_eligible"):
        assert sum(o["count"] for o in f[on_book]) == 8336, on_book


def test_on_book_filters_return_the_count_their_facet_advertises(client):
    """The bug this guards: coercing the unbooked null to False made
    mispriced=false return 6,198 while its own facet said 2,534."""
    f = client.get("/api/v2/filters").json()
    for facet, values in (("mispriced", (True, False)), ("li_eligible", (True, False))):
        advertised = {str(o["value"]).lower(): o["count"] for o in f[facet]}
        for v in values:
            got = client.get("/api/v2/loans",
                             params={facet: str(v).lower()}).json()["total"]
            assert got == advertised[str(v).lower()], f"{facet}={v}"
        assert sum(advertised.values()) == 8336, facet


def test_search_unfiltered_reports_true_total_and_caps_the_list(client):
    r = client.get("/api/v2/loans").json()
    assert r["total"] == 12000
    assert r["shown"] == 200
    assert len(r["loans"]) == 200


def test_filters_compose(client):
    """The demo path: mispriced D-band loans on the High watchlist."""
    r = client.get("/api/v2/loans", params={
        "score_band": "D", "mispriced": "true", "ews_tier": "High"}).json()
    assert 0 < r["total"] < 12000
    assert all(x["score_band"] == "D" for x in r["loans"])


def test_search_counts_match_pandas(client):
    """The endpoint must not invent its own filtering semantics."""
    import pandas as pd
    from shared.config import RAW
    biz = pd.read_parquet(RAW / "businesses.parquet")
    expected = int((biz["industry"] == "Retail").sum())
    assert client.get("/api/v2/loans", params={"industry": "Retail"}).json()["total"] == expected


def test_free_text_id_search(client):
    r = client.get("/api/v2/loans", params={"q": "BIZ100002"}).json()
    assert r["total"] == 1
    assert r["loans"][0]["business_id"] == "BIZ100002"
```

- [ ] **Step 2: Run and watch them fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v -k "facets or search or filters or free_text"`
Expected: all FAIL with 404.

- [ ] **Step 3: Write `app/v2/loans.py`**

```python
"""The selectable loan universe: one row per applicant with every filter facet on it.

Built once from the frames v1 already computed, so a filter can never disagree with
the module that produced the column. On-book facets (ews_tier, mispriced,
li_eligible) are None for the 3,664 applicants that were never booked — that null is
correct and the UI says so rather than hiding them.
"""
from __future__ import annotations

import pandas as pd

FACETS = ["decision", "score_band", "industry", "region",
          "booked", "ews_tier", "mispriced", "li_eligible"]

LIST_COLUMNS = ["business_id", "decision", "score_band", "industry",
                "region", "requested_amount", "booked"]


def build_index(app_state) -> pd.DataFrame:
    p, s, d = app_state.profiles, app_state.scores, app_state.decisions
    idx = pd.DataFrame({
        "industry": p["industry"].astype(str),
        "region": p["region"].astype(str),
        "entity_type": p["entity_type"].astype(str),
        "requested_amount": p["requested_amount"].astype(float),
        "booked": p["booked"].astype(bool),
        "score_band": s["score_band"].astype(str),
        "business_score": s["business_score"].astype(int),
        "pd": s["pd"].astype(float),
        "decision": d["decision"].astype(str),
    }, index=p.index)
    idx["mispriced"] = app_state.priced["mispriced"].astype(bool).reindex(idx.index)
    idx["ews_tier"] = app_state.ews["risk_tier"].astype(str).reindex(idx.index)
    idx["li_eligible"] = app_state.li["eligible"].astype(bool).reindex(idx.index)
    idx.index.name = "business_id"
    return idx


def facets(index: pd.DataFrame) -> dict:
    """Distinct values and counts per facet. NaN (not booked) is dropped, so an
    on-book facet's counts sum to 8,336 and an application facet's to 12,000."""
    out = {}
    for f in FACETS:
        counts = index[f].dropna().value_counts()
        out[f] = [{"value": _jsonable(k), "count": int(v)}
                  for k, v in counts.sort_index().items()]
    return out


def _jsonable(v):
    return bool(v) if isinstance(v, bool) else str(v)


def _as_bool(v: str | None):
    if v is None:
        return None
    return str(v).lower() in ("true", "1", "yes")


def search(index: pd.DataFrame, *, decision=None, score_band=None, industry=None,
           region=None, booked=None, ews_tier=None, mispriced=None,
           li_eligible=None, q=None, limit: int = 200) -> dict:
    m = pd.Series(True, index=index.index)
    for col, val in (("decision", decision), ("score_band", score_band),
                     ("industry", industry), ("region", region),
                     ("ews_tier", ews_tier)):
        if val:
            m &= index[col] == val
    for col, val in (("booked", booked), ("mispriced", mispriced),
                     ("li_eligible", li_eligible)):
        b = _as_bool(val)
        if b is not None:
            # NOT fillna(False): an unbooked applicant was never priced and is
            # neither mispriced nor correctly priced. Coercing that null to False
            # would make `mispriced=false` partition all 12,000 applicants while the
            # facet endpoint reports it over the 8,336 booked -- the dropdown would
            # read "False (2,534)" and return 6,198. A filter must return the count
            # its own facet advertises.
            vals = index[col]
            m &= vals.notna() & (vals.fillna(False).astype(bool) == b)
    if q:
        m &= index.index.str.contains(str(q).strip(), case=False, regex=False)

    hits = index[m].sort_index()
    shown = hits.head(limit).reset_index()
    return {
        "total": int(len(hits)),
        "shown": int(len(shown)),
        "limit": limit,
        "loans": shown[LIST_COLUMNS].to_dict(orient="records"),
    }
```

- [ ] **Step 4: Store the index on `V2State`**

In `app/v2/state.py`, add `index: pd.DataFrame` as the last field of `V2State`, change `build_state` to take the whole app state, and build the index at the end:

```python
def build_state(app_state) -> V2State:
    """app_state is the FastAPI app.state, after v1's lifespan has populated it."""
    profiles = app_state.profiles
    ...
    index = loans.build_index(app_state)
    return V2State(scorecard, score_X, adj_X, adj_explainer, panel, index)
```

Add `from app.v2 import loans` to the imports. In `app/main.py`, change the one lifespan line to `app.state.v2 = v2_state.build_state(app.state)`.

- [ ] **Step 5: Add the two endpoints to `app/v2/router.py`**

```python
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
```

Add `from app.v2 import loans` at the top.

- [ ] **Step 6: Run the tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add app/v2 app/main.py tests/test_app_v2.py
git commit -m "v2: loan index, facets, and composable filtered search

The index is assembled from the frames v1 already computed, so a filter can never
disagree with the module that produced the column. Unbooked applicants carry null
on-book facets rather than being dropped.

Verified: facet counts sum to 12,000 (application facets) and 8,336 (on-book);
industry=Retail total matches a direct pandas count; unfiltered search reports
total 12,000 while showing 200.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Loan header endpoint

**Files:**
- Create: `app/v2/explain.py`
- Modify: `app/v2/router.py`, `tests/test_app_v2.py`

**Interfaces:**
- Produces: `explain.header(app_state, business_id) -> dict` with keys `business_id, identity{industry,region,entity_type,years_in_business}, terms{requested_amount,term_months,loan_purpose,collateral_flag}, score{business_score,score_band,pd}, decision, booked, modules_present`. Raises `KeyError` for an unknown id; the router turns that into a 404.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_app_v2.py
def test_header_of_a_booked_loan(client):
    h = client.get("/api/v2/loan/BIZ100002").json()
    assert h["business_id"] == "BIZ100002"
    assert h["identity"]["industry"] == "Transport"
    assert h["terms"]["requested_amount"] == 209000.0
    assert h["booked"] is True
    assert h["decision"] in ("Approve", "Refer", "Decline")
    assert 300 <= h["score"]["business_score"] <= 850
    assert set(h["modules_present"]) == {"score", "adjudication", "pricing",
                                         "ews", "line_increase"}


def test_header_of_an_unbooked_applicant(client):
    """Not booked is not an error. Only the two application-time modules apply."""
    unbooked = client.get("/api/v2/loans", params={"booked": "false"}).json()["loans"][0]
    h = client.get(f"/api/v2/loan/{unbooked['business_id']}").json()
    assert h["booked"] is False
    assert set(h["modules_present"]) == {"score", "adjudication"}


def test_unknown_id_is_404_not_500(client):
    assert client.get("/api/v2/loan/NOPE").status_code == 404
```

- [ ] **Step 2: Run and watch them fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v -k header or unknown`
Expected: FAIL with 404 on the first two, and `test_unknown_id_is_404_not_500` passing for the wrong reason (no route). Both are resolved by Step 3.

- [ ] **Step 3: Write `app/v2/explain.py`**

```python
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
```

- [ ] **Step 4: Add the endpoint and a shared 404 helper to `app/v2/router.py`**

```python
from fastapi import APIRouter, HTTPException, Request
from app.v2 import explain, loans


def _guard(fn, app_state, business_id, *rest):
    """Every loan endpoint turns an unknown id into a 404 the same way. The extra
    args carry a what-if overrides body once Task 5 adds one.

    Catches only UnknownLoan, never bare KeyError: a KeyError from anywhere else in a
    detail function is a bug and must reach the client as a 500 with a traceback.
    Reporting it as 404 would tell the demo audience a loan does not exist while it
    sits in the dropdown in front of them."""
    try:
        return fn(app_state, business_id, *rest)
    except explain.UnknownLoan:
        raise HTTPException(404, f"unknown business_id {business_id}")
    except whatif.InvalidOverride as e:
        raise HTTPException(422, str(e))


@router.get("/loan/{business_id}")
def loan_header(request: Request, business_id: str):
    return _guard(explain.header, request.app.state, business_id)
```

- [ ] **Step 5: Run the tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add app/v2 tests/test_app_v2.py
git commit -m "v2: loan header endpoint with honest nulls for unbooked applicants

An applicant that was never booked reports two modules present, not an error --
matching customer_360's existing behaviour and making the gap visible on screen.

Verified: BIZ100002 header matches the parquet (Transport, 209,000); an unbooked
applicant reports score+adjudication only; an unknown id is 404 not 500.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Decision tab read path

**Files:**
- Create: `app/v2/rules.py`, `app/v2/ledgers.py`
- Modify: `app/v2/explain.py`, `app/v2/router.py`, `tests/test_app_v2.py`

**File structure note.** `score_ledger`, `shap_ledger` and their helpers (`_logit`,
`_jsonable_value`) live in `app/v2/ledgers.py`, not in `explain.py`. They are a
self-contained "model rationale" concern, unrelated to `explain.py`'s orchestration
role, and `explain.py` is already at its ceiling with three more detail functions still
to come (Tasks 6, 8, 10). This establishes the pattern those tasks follow: one module
per concern, and `explain.py`'s `*_detail()` functions call into them — exactly as
`decision_detail()` already delegates to `rules.ledger()` instead of inlining policy.

**Interfaces:**
- Produces: `rules.ledger(profile_row, score_row, config) -> dict` with `knockouts` and `refer_overrides` lists of `{rule, label, threshold, value, comparator, fired, applicable}`, and `nearest_flip(ledger, pd_value, config) -> dict`. `explain.decision_detail(app_state, business_id) -> dict` with `pd_zones`, `rules`, `score_ledger`, `shap`, `nearest_flip`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_app_v2.py
def test_decision_detail_rules_ledger(client):
    d = client.get("/api/v2/loan/BIZ100002/decision").json()
    names = {r["rule"] for r in d["rules"]["knockouts"]}
    assert names == {"dscr_floor", "public_records_cap",
                     "prior_delinq_cap", "leverage_cap"}
    dscr = next(r for r in d["rules"]["knockouts"] if r["rule"] == "dscr_floor")
    assert dscr["threshold"] == 1.0
    assert dscr["value"] == pytest.approx(1.78)
    assert dscr["fired"] is False


def test_pd_zones_match_the_committed_policy(client):
    d = client.get("/api/v2/loan/BIZ100002/decision").json()
    assert d["pd_zones"]["t_low"] == 0.0955
    assert d["pd_zones"]["t_high"] == 0.4943
    assert d["pd_zones"]["zone"] in ("Approve", "Refer", "Decline")


@pytest.fixture(scope="module")
def sample_ids(client):
    """A numeric identity asserted on ONE hardcoded loan passes by luck. BIZ100002's
    SHAP gap happens to be exactly 0.0 and its PD sits nowhere near the tails, which
    is why a single-loan version of these tests stayed green while 62 of 120 loans
    breached the tolerance. Always sample."""
    return [l["business_id"] for l in
            client.get("/api/v2/loans", params={"limit": 40}).json()["loans"]]


def test_score_ledger_is_exactly_additive(client, sample_ids):
    """intercept + sum(WoE x beta) == logit(pd). This identity is the whole reason a
    scorecard is explainable, and the screen claims it -- so assert it, on many loans."""
    import math
    for bid in sample_ids:
        led = client.get(f"/api/v2/loan/{bid}/decision").json()["score_ledger"]
        total = led["intercept"] + sum(c["contribution"] for c in led["contributions"])
        assert len(led["contributions"]) == 15, bid
        assert total == pytest.approx(led["logit_pd"], abs=1e-9), bid
        assert led["logit_pd"] == pytest.approx(
            math.log(led["pd"] / (1 - led["pd"])), abs=1e-6), bid


def test_shap_is_exactly_additive(client, sample_ids):
    for bid in sample_ids:
        sh = client.get(f"/api/v2/loan/{bid}/decision").json()["shap"]
        total = sh["base_value"] + sum(c["contribution"] for c in sh["contributions"])
        assert len(sh["contributions"]) == 21, bid
        assert total == pytest.approx(sh["logit_pd_model"], abs=1e-6), bid


def test_ledger_identities_hold_at_the_pd_extremes(client):
    """The tails are where rounding a PD before recomputing its logit does the most
    damage -- 5.85e-4 on the lowest-PD applicant, 585x the tolerance.

    The IDs are hardcoded because they ARE the measured extremes: BIZ101650 has the
    population's minimum modelled PD (0.000419) and BIZ111827 its maximum (0.991464).
    Do not swap these for the first and last rows of /api/v2/loans -- that endpoint
    sorts by business_id and does not even return pd, so it would silently test two
    ordinary mid-book loans while claiming to test the tails.
    """
    import math
    for bid in ("BIZ101650", "BIZ111827"):
        led = client.get(f"/api/v2/loan/{bid}/decision").json()["score_ledger"]
        assert led["logit_pd"] == pytest.approx(
            math.log(led["pd"] / (1 - led["pd"])), abs=1e-6), bid


def test_nearest_flip_can_rank_a_zero_threshold_rule(client):
    """public_records_cap is committed at 0 and 11,041 of 12,000 applicants sit exactly
    on it. An earlier version skipped every zero threshold, so the tightest margin a
    rule can have was invisible on 92% of the book."""
    nf = client.get("/api/v2/loan/BIZ100002/decision").json()["nearest_flip"]
    levers = {c["lever"] for c in nf["candidates"]}
    assert "public_records_cap" in levers
    pr = next(c for c in nf["candidates"] if c["lever"] == "public_records_cap")
    assert pr["at_threshold"] is True          # value 0, cap 0
    assert pr["distance_to_cross"] == 1.0      # one whole record, not zero
    gaps = [c["gap"] for c in nf["candidates"]]
    assert gaps == sorted(gaps)                 # candidates come back ranked
    assert nf["lever"] == nf["candidates"][0]["lever"]


def test_ledger_fired_flags_agree_with_the_module_on_every_applicant(client):
    """`fired` must mean "this rule contributed", the same as everywhere else.

    Whole book. Computing it from the comparator alone disagreed with
    policy.decide's own rule_hits on 43.4% of applicants: a refer override whose
    condition is true but which cannot bite (the loan is already outside the Approve
    zone) is not a rule that fired. BIZ100052 -- v1 reports "rule hits: none" while
    the ledger claimed two. A UI painting `fired` red would have shown two red rows
    on a decision that came purely from the PD zones."""
    from app.v2 import explain
    st = client.app.state
    for bid in st.profiles.index:
        d = explain.decision_detail(st, bid)
        rows = d["rules"]["knockouts"] + d["rules"]["refer_overrides"]
        assert sum(1 for r in rows if r["fired"]) == len(d["rule_hits"]), (bid, rows)
        for r in rows:
            assert not (r["fired"] and not r["applicable"]), (bid, r["rule"])


def test_decision_endpoint_matches_the_batch_pipeline(client, sample_ids):
    """v2's DECISION endpoint -- not just the header -- must agree with what v1
    already decided, and must report the same reasons."""
    for bid in sample_ids:
        v1 = client.get(f"/api/adjudicate/{bid}").json()
        v2 = client.get(f"/api/v2/loan/{bid}/decision").json()
        assert v1["decision"] == v2["decision"], bid
        assert sorted(v1["rule_hits"]) == sorted(v2["rule_hits"]), bid
```

- [ ] **Step 2: Run and watch them fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v -k "decision or ledger or shap or zones"`
Expected: FAIL with 404 (except `test_decision_matches_the_batch_pipeline`, which needs Task 3's endpoint and the new one).

- [ ] **Step 3: Write `app/v2/rules.py`**

```python
"""The policy layer as a per-loan ledger: every rule, its threshold, this loan's
value, and whether it fired.

policy.decide() returns only the reasons that fired. A screen that is trying to
explain a decision needs the rules that did NOT fire just as much -- that is the
difference between "declined for leverage" and "passed everything except leverage".
The thresholds and comparators here are read from the same PolicyConfig the batch
pipeline uses; only the presentation is new.
"""
from __future__ import annotations

KNOCKOUTS = [
    ("dscr_floor", "DSCR below floor", "dscr", "<", "dscr_floor"),
    ("public_records_cap", "Public records present", "public_records", ">", "public_records_cap"),
    ("prior_delinq_cap", "Prior delinquencies at cap", "prior_delinquencies", ">=", "prior_delinq_cap"),
    ("leverage_cap", "Leverage above cap", "leverage", ">", "leverage_cap"),
]

REFER_OVERRIDES = [
    ("dscr_refer_hi", "Thin affordability margin", "dscr", "<", "dscr_refer_hi"),
    ("score_floor", "Weak credit score", "business_score", "<", "score_floor"),
    ("req_to_rev_cap", "Large request vs revenue", "req_to_rev", ">", "req_to_rev_cap"),
]

_OPS = {"<": lambda a, b: a < b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}


def loan_values(profile_row, score_row) -> dict:
    """The seven numbers the policy layer looks at, for one loan."""
    rev = max(float(profile_row["annual_revenue"]), 1.0)
    return {
        "dscr": float(profile_row["dscr"]),
        "leverage": float(profile_row["leverage"]),
        "public_records": float(profile_row["public_records"]),
        "prior_delinquencies": float(profile_row["prior_delinquencies"]),
        "business_score": float(score_row["business_score"]),
        "req_to_rev": float(profile_row["requested_amount"]) / rev,
    }


def _rows(specs, values, config, applicable) -> list[dict]:
    """Three distinct facts per rule, because conflating them makes the screen lie.

      condition_met -- the comparator is true for this loan
      applicable    -- this rule can bite this loan at all
      fired         -- it actually contributed to the decision (both of the above)

    A refer override only downgrades a loan the PD zones would have APPROVED. On a
    loan already in the Refer zone its comparator can be true while it changed
    nothing. Reporting that as `fired` disagreed with policy.decide's own rule_hits
    on 43.4% of applicants -- BIZ100052 is the case: v1 says "rule hits: none" while
    the ledger claimed two fired. `fired` means "this rule contributed" everywhere
    else in this codebase (Task 8 fixed the identical confusion for EWS triggers), so
    it has to mean that here too.
    """
    out = []
    for rule, label, value_key, comparator, config_key in specs:
        threshold = float(getattr(config, config_key))
        value = values[value_key]
        condition_met = bool(_OPS[comparator](value, threshold))
        out.append({
            "rule": rule, "label": label, "value_key": value_key,
            "comparator": comparator, "threshold": threshold,
            "value": round(value, 4),
            "condition_met": condition_met,
            "applicable": applicable,
            "fired": bool(condition_met and applicable),
        })
    return out


def ledger(profile_row, score_row, config, decision_zone: str) -> dict:
    """decision_zone is the PD-zone verdict BEFORE overrides, because a refer
    override only applies to a loan the PD zones would have approved."""
    values = loan_values(profile_row, score_row)
    # dscr_refer_hi only bites above the floor -- below it the knockout already fired.
    refer = _rows(REFER_OVERRIDES, values, config, applicable=decision_zone == "Approve")
    for r in refer:
        if r["rule"] == "dscr_refer_hi":
            # the band is two-sided: below the floor the knockout already fired
            r["condition_met"] = bool(r["condition_met"]
                                      and values["dscr"] >= float(config.dscr_floor))
            r["fired"] = bool(r["condition_met"] and r["applicable"])
            r["label"] = (f"Thin affordability margin "
                          f"({config.dscr_floor} <= DSCR < {config.dscr_refer_hi})")
    return {
        "knockouts": _rows(KNOCKOUTS, values, config, applicable=True),
        "refer_overrides": refer,
    }


def nearest_flip(led: dict, pd_value: float, config) -> dict:
    """Which single lever is closest to changing this decision.

    Ranked by distance-to-cross divided by the rule's own scale, so thresholds on
    different scales compare. Distance-to-cross is how far this loan's value must move
    to trip the rule -- for an integer count rule with a `>` comparator sitting exactly
    on its cap, that is one whole record, not zero.

    A threshold of exactly 0 has no meaningful relative scale, so it falls back to unit
    scale. It is NEVER dropped. An earlier version skipped every zero threshold, which
    silently made `public_records_cap` unrankable on 11,041 of the 12,000 applicants --
    every loan sitting exactly on the cap, which is the tightest margin a rule can have.
    """
    INTEGER_COUNT_RULES = {"public_records_cap"}
    candidates = []
    for r in led["knockouts"] + led["refer_overrides"]:
        if not r["applicable"]:
            continue
        distance = abs(r["value"] - r["threshold"])
        if r["rule"] in INTEGER_COUNT_RULES and r["comparator"] == ">" and not r["fired"]:
            distance = max(distance, 1.0)   # only trips at the next whole record
        scale = abs(r["threshold"]) or 1.0
        candidates.append({
            "lever": r["rule"], "label": r["label"], "value": r["value"],
            "threshold": r["threshold"], "distance_to_cross": round(distance, 4),
            "gap": round(distance / scale, 4), "at_threshold": r["value"] == r["threshold"],
            "currently_firing": r["fired"],
        })
    for name, t in (("t_low", float(config.t_low)), ("t_high", float(config.t_high))):
        candidates.append({
            "lever": name, "label": f"PD zone cutoff {name}", "value": pd_value,
            "threshold": t, "distance_to_cross": round(abs(pd_value - t), 6),
            "gap": round(abs(pd_value - t) / (abs(t) or 1.0), 4),
            "at_threshold": False, "currently_firing": None,
        })
    if not candidates:
        return {}
    ranked = sorted(candidates, key=lambda c: c["gap"])
    return {**ranked[0], "candidates": ranked}
```

- [ ] **Step 4: Add `decision_detail` to `app/v2/explain.py`**

```python
import math

import numpy as np

from score.src.reason_codes import feature_contributions
from score.src.feature_engineering import FEATURE_COLUMNS
from adjudication.src.feature_engineering import ADJ_FEATURE_COLUMNS
from app.v2 import rules


def _logit(p: float) -> float:
    p = min(max(float(p), 1e-12), 1 - 1e-12)
    return math.log(p / (1 - p))


def _zone(pd_value: float, config) -> str:
    if pd_value <= config.t_low:
        return "Approve"
    if pd_value >= config.t_high:
        return "Decline"
    return "Refer"


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
    return {
        "intercept": float(v2.scorecard.estimator_.intercept_[0]),
        "contributions": rows,
        "pd": float(pd_value),
        "logit_pd": _logit(pd_value),
    }


def _jsonable_value(v):
    if v is None:
        return None
    if isinstance(v, (np.integer, np.floating)):
        v = v.item()
    return v if isinstance(v, (int, float, str, bool)) else str(v)


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
    return {"base_value": float(base), "contributions": rows,
            "pd_model": float(pd_model),
            "logit_pd_model": _logit(pd_model)}


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
```

- [ ] **Step 5: Stash the PolicyConfig on app.state**

v1's lifespan builds `config` as a local. `decision_detail` needs it. Add one line to `app/v2/state.py`'s `build_state` instead of touching v1 further:

```python
    import json
    from adjudication.src.policy import PolicyConfig
    app_state.policy_config = PolicyConfig.from_dict(
        json.loads((ROOT / "adjudication" / "models" / "policy_config.json").read_text()))
```

Move the `json` and `PolicyConfig` imports to the top of the module rather than inlining them.

- [ ] **Step 6: Add the endpoint**

```python
@router.get("/loan/{business_id}/decision")
def loan_decision(request: Request, business_id: str):
    return _guard(explain.decision_detail, request.app.state, business_id)
```

- [ ] **Step 7: Run the tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: all PASS, including both additivity assertions.

- [ ] **Step 8: Commit**

```bash
git add app/v2 tests/test_app_v2.py
git commit -m "v2: decision tab read path -- rules ledger, PD zones, two rationales

policy.decide returns only the reasons that fired; explaining a decision needs the
rules that did not fire just as much, so the ledger carries every rule with its
threshold and this loan's value.

Verified: intercept + sum(WoE x beta) == logit(pd) to 1e-9 (15 features);
SHAP base + sum == logit(model PD) to 1e-6 (21 features); v2's decision agrees
with v1's /api/adjudicate for the same loan.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Decision what-if

**Files:**
- Create: `app/v2/whatif.py`
- Modify: `app/v2/router.py`, `tests/test_app_v2.py`

**Interfaces:**
- Produces: `whatif.DecisionOverrides` (Pydantic model, all fields optional with bounds); `whatif.decision_whatif(app_state, business_id, overrides) -> dict` with `decision`, `zone`, `rules`, `rule_hits`, `book_mix`, `flipped_count`, `config`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_app_v2.py
def test_decision_whatif_with_no_overrides_reproduces_the_batch_pipeline(client):
    """THE invariant test. If this ever fails, the demo is lying: the what-if and the
    production pipeline have drifted apart."""
    ids = [l["business_id"] for l in
           client.get("/api/v2/loans", params={"limit": 25}).json()["loans"]]
    for bid in ids:
        batch = client.get(f"/api/adjudicate/{bid}").json()
        live = client.post(f"/api/v2/loan/{bid}/decision/whatif", json={}).json()
        assert live["decision"] == batch["decision"], bid
        assert sorted(live["rule_hits"]) == sorted(batch["rule_hits"]), bid


def test_decision_whatif_book_mix_sums_to_the_population(client):
    r = client.post("/api/v2/loan/BIZ100002/decision/whatif", json={}).json()
    assert sum(r["book_mix"].values()) == 12000


def test_dragging_t_low_to_zero_removes_every_approval(client):
    r = client.post("/api/v2/loan/BIZ100002/decision/whatif",
                    json={"t_low": 0.0}).json()
    assert r["book_mix"].get("Approve", 0) == 0
    assert r["flipped_count"] > 0


def test_whatif_rejects_out_of_range_overrides(client):
    """A slider that silently clamps produces a number that looks real and is not."""
    assert client.post("/api/v2/loan/BIZ100002/decision/whatif",
                       json={"t_low": 1.5}).status_code == 422
    assert client.post("/api/v2/loan/BIZ100002/decision/whatif",
                       json={"dscr_floor": -1}).status_code == 422


def test_whatif_rejects_an_inverted_pd_band(client):
    """Per-field bounds are not enough. t_low=0.9 is in range on its own, but merged
    with the committed t_high of 0.4943 it inverts the band: decide() tests
    `pd <= t_low` first, so the Refer zone vanishes and 643 loans change decision
    while the response still looks like an ordinary book."""
    r = client.post("/api/v2/loan/BIZ100002/decision/whatif", json={"t_low": 0.9})
    assert r.status_code == 422, r.json()
    assert "t_high" in r.json()["detail"]
    # Explicitly-paired values that are coherent must still be accepted.
    ok = client.post("/api/v2/loan/BIZ100002/decision/whatif",
                     json={"t_low": 0.20, "t_high": 0.60})
    assert ok.status_code == 200
    assert sum(ok.json()["book_mix"].values()) == 12000


def test_whatif_rejects_an_inverted_dscr_band(client):
    r = client.post("/api/v2/loan/BIZ100002/decision/whatif", json={"dscr_floor": 5.0})
    assert r.status_code == 422, r.json()
```

- [ ] **Step 2: Run and watch them fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v -k whatif`
Expected: FAIL with 405/404.

- [ ] **Step 3: Write `app/v2/whatif.py`**

```python
"""The write path: overrides in, recomputed numbers out.

Every function here does the same three things -- take the committed configuration,
apply the caller's overrides, and hand the result to the module function the batch
pipeline calls. It never re-implements the calculation. That is what makes the
guarantee testable: an empty override body must reproduce the batch numbers exactly.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from adjudication.src.policy import PolicyConfig, decide


class InvalidOverride(ValueError):
    """A combination of overrides that is individually in range but jointly
    incoherent. The router turns this into a 422, never a 200 with a wrong number."""
from adjudication.src.feature_engineering import ADJ_FEATURE_COLUMNS


class DecisionOverrides(BaseModel):
    t_low: float | None = Field(default=None, ge=0.0, le=1.0)
    t_high: float | None = Field(default=None, ge=0.0, le=1.0)
    dscr_floor: float | None = Field(default=None, ge=0.0, le=10.0)
    dscr_refer_hi: float | None = Field(default=None, ge=0.0, le=10.0)
    public_records_cap: int | None = Field(default=None, ge=0, le=20)
    prior_delinq_cap: int | None = Field(default=None, ge=0, le=20)
    leverage_cap: float | None = Field(default=None, ge=0.0, le=50.0)
    req_to_rev_cap: float | None = Field(default=None, ge=0.0, le=10.0)
    score_floor: float | None = Field(default=None, ge=300, le=850)

    def apply_to(self, config: PolicyConfig) -> PolicyConfig:
        """Merge overrides onto the committed config, then check the pair-wise
        constraints Pydantic cannot see.

        Per-field bounds are not enough: `{"t_low": 0.9}` is in range on its own, but
        merged with the committed t_high of 0.4943 it inverts the PD band. decide()
        tests `pd <= t_low` first, so the Refer zone silently disappears and the book
        mix comes back plausible-looking and wrong. The whole point of rejecting an
        out-of-range slider is to refuse numbers that look real and are not, so the
        same rule has to cover the combination, not just each field alone.
        """
        d = config.to_dict()
        d.update({k: v for k, v in self.model_dump().items() if v is not None})
        if d["t_low"] > d["t_high"]:
            raise InvalidOverride(
                f"t_low ({d['t_low']:.4f}) must not exceed t_high ({d['t_high']:.4f}): "
                "an inverted PD band erases the Refer zone")
        if d["dscr_floor"] > d["dscr_refer_hi"]:
            raise InvalidOverride(
                f"dscr_floor ({d['dscr_floor']}) must not exceed dscr_refer_hi "
                f"({d['dscr_refer_hi']}): the refer band would be empty")
        return PolicyConfig.from_dict(d)


def decision_whatif(app_state, business_id: str, overrides: DecisionOverrides) -> dict:
    from app.v2 import explain, rules

    base_config = app_state.policy_config
    config = overrides.apply_to(base_config)

    X = app_state.v2.adj_X
    pd_model = app_state.decisions["pd"].to_numpy()
    redecided = decide(app_state.profiles.assign(
        business_score=app_state.scores["business_score"]), pd_model, config)

    row = redecided.loc[business_id]
    p = app_state.profiles.loc[business_id]
    s = app_state.scores.loc[business_id]
    pd_value = float(pd_model[app_state.profiles.index.get_loc(business_id)])
    zone = explain._zone(pd_value, config)
    flipped = int((redecided["decision"].to_numpy()
                   != app_state.decisions["decision"].to_numpy()).sum())
    return {
        "business_id": business_id,
        "decision": str(row["decision"]),
        "zone": zone,
        "rule_hits": list(row["decision_reasons"]),
        "rules": rules.ledger(p, s, config, zone),
        "nearest_flip": rules.nearest_flip(
            rules.ledger(p, s, config, zone), pd_value, config),
        "book_mix": {k: int(v) for k, v in
                     redecided["decision"].value_counts().items()},
        "flipped_count": flipped,
        "config": config.to_dict(),
    }
```

Note the `decide()` call must be given the same frame v1 gave it. v1 passes
`X_all = compute_adjudication_features(biz)`, which carries `business_score`.
Confirm in Step 4 which frame reproduces v1 exactly and use that one; the
`assign` above is a starting point, not a guess to leave unverified.

- [ ] **Step 4: Verify which frame reproduces the batch decision, before wiring**

Run this probe and use whichever frame matches v1 in `decision_whatif`:

```bash
PYTHONPATH=. .venv/bin/python - <<'EOF'
import warnings; warnings.filterwarnings("ignore")
import json, joblib, pandas as pd
from pathlib import Path
from shared.config import RAW
from score.src.predict import predict_score_pd
from adjudication.src.feature_engineering import ADJ_FEATURE_COLUMNS, compute_adjudication_features
from adjudication.src.policy import PolicyConfig, decide

biz = pd.read_parquet(RAW/"businesses.parquet").set_index("business_id")
cfg = PolicyConfig.from_dict(json.loads(Path("adjudication/models/policy_config.json").read_text()))
m = joblib.load("adjudication/models/adjudication_model.pkl")
X = compute_adjudication_features(biz)
pd_hat = m.predict_proba(X[ADJ_FEATURE_COLUMNS])[:,1]
ref = decide(X, pd_hat, cfg)
alt = decide(biz.assign(business_score=predict_score_pd(biz)["business_score"].to_numpy()), pd_hat, cfg)
print("identical:", (ref["decision"].to_numpy() == alt["decision"].to_numpy()).all())
print("ref mix:", ref["decision"].value_counts().to_dict())
EOF
```

Expected: prints whether the simpler frame is equivalent. **If it prints `False`, use `compute_adjudication_features(profiles)` (i.e. cache it on `V2State` as `adj_full` and pass that) — do not ship the cheaper frame.**

- [ ] **Step 5: Add the endpoint**

```python
from app.v2 import whatif


@router.post("/loan/{business_id}/decision/whatif")
def decision_whatif(request: Request, business_id: str,
                    overrides: whatif.DecisionOverrides):
    return _guard(whatif.decision_whatif, request.app.state, business_id, overrides)
```

`_guard` already takes `*rest`, so the overrides body passes straight through — no
call-site changes needed.

- [ ] **Step 6: Run the tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: all PASS. The 25-loan invariant test is the one that matters.

- [ ] **Step 7: Commit**

```bash
git add app/v2 tests/test_app_v2.py
git commit -m "v2: decision what-if -- drag the PD cutoffs, recompute the whole book

Overrides are applied to the committed PolicyConfig and handed to policy.decide,
the same function the batch pipeline calls, so the two cannot drift. Out-of-range
overrides are rejected (422) rather than clamped into a number that looks real.

Verified: 25 loans, empty override body reproduces /api/adjudicate's decision and
rule hits exactly; book mix sums to 12,000; t_low=0 removes every approval.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Pricing tab read path

**Files:**
- Create: `app/v2/pricing.py`
- Modify: `app/v2/explain.py`, `app/v2/router.py`, `tests/test_app_v2.py`

**File structure.** `price_one` and `pricing_detail` live in `app/v2/pricing.py`,
following the pattern Task 4 set with `ledgers.py`: one module per concern. `explain.py`
keeps the shared primitives (`UnknownLoan`, `_row`, `_booked_row`, `header`) and
`decision_detail`. Tasks 8 and 10 follow with `ews.py` and `line_increase.py`. Without
this, `explain.py` would take three more detail functions and land near 300 lines.

**Add `_booked_row` to `explain.py`** — Tasks 8 and 10 reuse it rather than repeating
the fetch-row / check-booked / return-None dance a third and fourth time:

```python
def _booked_row(app_state, business_id: str):
    """(profile_row, booked). Unknown id raises UnknownLoan so the router answers 404;
    an applicant that was never funded returns booked=False, which every on-book detail
    function turns into a null payload rather than an error."""
    p = _row(app_state, business_id)
    return p, bool(p["booked"])
```

**Interfaces:**
- Produces: `pricing.pricing_detail(app_state, business_id) -> dict | None` with `ead`, `pd`, `rates{quoted,break_even,hurdle_clearing,recommended}`, `waterfall[]` (each line as `{line, dollars, bps}`), `verdict{roe,raroc,clears_hurdle,rate_shortfall_bps,roe_hurdle}`, `market`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_app_v2.py
WATERFALL_LINES = ["interest_income", "cost_of_funds", "expected_loss",
                   "operating_cost", "pre_tax_profit", "tax", "net_income",
                   "allocated_equity"]


def test_pricing_detail_has_every_waterfall_line_in_dollars_and_bps(client):
    p = client.get("/api/v2/loan/BIZ100002/pricing").json()
    assert [w["line"] for w in p["waterfall"]] == WATERFALL_LINES
    ead = p["ead"]
    for w in p["waterfall"]:
        assert w["bps"] == pytest.approx(w["dollars"] / ead * 10_000, abs=1e-6)


def test_pricing_detail_matches_the_batch_priced_book(client):
    v1 = client.get("/api/pricing/BIZ100002").json()
    v2 = client.get("/api/v2/loan/BIZ100002/pricing").json()
    assert v2["verdict"]["roe"] == pytest.approx(v1["roe_at_quoted"], abs=1e-9)
    assert v2["rates"]["recommended"] == pytest.approx(v1["recommended_rate"], abs=1e-9)
    assert v2["verdict"]["clears_hurdle"] == v1["clears_hurdle"]


def test_rate_ladder_is_ordered(client):
    r = client.get("/api/v2/loan/BIZ100002/pricing").json()["rates"]
    assert r["break_even"] < r["hurdle_clearing"] < r["recommended"]


def test_pricing_is_null_for_an_unbooked_applicant(client):
    unbooked = client.get("/api/v2/loans", params={"booked": "false"}).json()["loans"][0]
    r = client.get(f"/api/v2/loan/{unbooked['business_id']}/pricing")
    assert r.status_code == 200
    assert r.json() is None
```

- [ ] **Step 2: Run and watch them fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v -k pricing or ladder`
Expected: FAIL with 404.

- [ ] **Step 3: Write `app/v2/pricing.py`** (`price_one` + `pricing_detail`; see the file-structure note above — these do NOT go in `explain.py`)

```python
from shared.config import MARKET
from pricing.src.engine import (
    MarketAssumptions, price_loan, break_even_rate, hurdle_clearing_rate,
)

_MARKET = MarketAssumptions.from_market(MARKET)

WATERFALL_LINES = ["interest_income", "cost_of_funds", "expected_loss",
                   "operating_cost", "pre_tax_profit", "tax", "net_income",
                   "allocated_equity"]


def price_one(app_state, business_id: str, market: MarketAssumptions,
              quoted_rate: float | None = None) -> dict:
    """Price one loan through the shared engine. Used by both the read path and the
    what-if path so they cannot diverge."""
    p = app_state.profiles.loc[business_id]
    pd_value = float(app_state.scores.loc[business_id, "pd"])
    ead = float(p["requested_amount"])
    rate = float(p["risk_based_rate"]) if quoted_rate is None else float(quoted_rate)
    r = price_loan(pd_=pd_value, ead=ead, quoted_rate=rate, market=market)
    w = r["waterfall_quoted"]
    return {
        "business_id": business_id,
        "ead": ead,
        "pd": round(pd_value, 6),
        "rates": {
            "quoted": rate,
            "break_even": break_even_rate(pd_value, ead, market),
            "hurdle_clearing": r["hurdle_clearing_rate"],
            "recommended": r["recommended_rate"],
        },
        "waterfall": [{"line": k, "dollars": float(w[k]),
                       "bps": float(w[k]) / ead * 10_000} for k in WATERFALL_LINES],
        "verdict": {
            "roe": r["roe_at_quoted"],
            "raroc": r["raroc_at_quoted"],
            "clears_hurdle": r["clears_hurdle"],
            "rate_shortfall_bps": r["rate_shortfall"] * 10_000,
            "roe_hurdle": market.roe_hurdle,
        },
        "market": market.to_dict(),
    }


def pricing_detail(app_state, business_id: str):
    p = _row(app_state, business_id)
    if not bool(p["booked"]):
        return None
    return price_one(app_state, business_id, _MARKET)
```

- [ ] **Step 4: Add the endpoint**

```python
@router.get("/loan/{business_id}/pricing")
def loan_pricing(request: Request, business_id: str):
    return _guard(pricing.pricing_detail, request.app.state, business_id)
```

- [ ] **Step 5: Run the tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add app/v2 tests/test_app_v2.py
git commit -m "v2: pricing tab read path -- the full waterfall in dollars and bps

price_population keeps only scalars; the engine already returns the whole waterfall,
so the loan-level screen just stops throwing it away. Both read and what-if paths
go through one price_one() helper so they cannot diverge.

Verified: ROE and recommended rate match /api/pricing/<id> to 1e-9; every waterfall
line's bps equals dollars/EAD*10,000; break-even < hurdle-clearing < recommended;
an unbooked applicant returns 200 with null.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Pricing what-if

**Files:**
- Modify: `app/v2/whatif.py`, `app/v2/router.py`, `tests/test_app_v2.py`

**Interfaces:**
- Produces: `whatif.PricingOverrides` (Pydantic, bounded); `whatif.pricing_whatif(app_state, business_id, overrides) -> dict` — the `pricing_detail` shape plus `book{n, n_clears, share_clears, mispriced_ead}`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_app_v2.py
def test_pricing_whatif_with_no_overrides_reproduces_the_batch_pipeline(client):
    """The invariant test for pricing."""
    ids = [l["business_id"] for l in client.get(
        "/api/v2/loans", params={"booked": "true", "limit": 25}).json()["loans"]]
    for bid in ids:
        batch = client.get(f"/api/pricing/{bid}").json()
        live = client.post(f"/api/v2/loan/{bid}/pricing/whatif", json={}).json()
        assert live["verdict"]["roe"] == pytest.approx(batch["roe_at_quoted"], abs=1e-9), bid
        assert live["verdict"]["clears_hurdle"] == batch["clears_hurdle"], bid


def test_pricing_whatif_book_matches_the_committed_summary(client):
    """All four fields, not just the two that are easiest to compare. n_clears and
    mispriced_ead currently match exactly, and nothing would catch a regression in
    either -- an off-by-one in _book_under's clears mask would move both and leave
    n and share_clears looking fine."""
    summary = client.get("/api/pricing/summary").json()
    live = client.post("/api/v2/loan/BIZ100002/pricing/whatif", json={}).json()["book"]
    assert live["n"] == summary["n"]
    assert live["n_clears"] == summary["n_clears"]
    assert live["share_clears"] == pytest.approx(summary["share_clears"], abs=1e-4)
    assert live["mispriced_ead"] == pytest.approx(summary["mispriced_ead"], rel=1e-9)


def test_raising_lgd_hurts_the_book(client):
    base = client.post("/api/v2/loan/BIZ100002/pricing/whatif", json={}).json()
    worse = client.post("/api/v2/loan/BIZ100002/pricing/whatif",
                        json={"lgd": 0.90}).json()
    assert worse["book"]["share_clears"] < base["book"]["share_clears"]
    assert worse["waterfall"][2]["line"] == "expected_loss"
    assert abs(worse["waterfall"][2]["dollars"]) > abs(base["waterfall"][2]["dollars"])


def test_raising_the_quoted_rate_lifts_roe(client):
    base = client.post("/api/v2/loan/BIZ100002/pricing/whatif", json={}).json()
    up = client.post("/api/v2/loan/BIZ100002/pricing/whatif",
                     json={"quoted_rate": 0.15}).json()
    assert up["verdict"]["roe"] > base["verdict"]["roe"]


def test_pricing_whatif_rejects_out_of_range(client):
    assert client.post("/api/v2/loan/BIZ100002/pricing/whatif",
                       json={"lgd": 1.5}).status_code == 422
    assert client.post("/api/v2/loan/BIZ100002/pricing/whatif",
                       json={"capital_ratio": 0.0}).status_code == 422
```

- [ ] **Step 2: Run and watch them fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v -k "pricing_whatif or lgd or quoted_rate"`
Expected: FAIL with 405/404.

- [ ] **Step 3: Write `app/v2/ews_whatif.py`**

```python
import numpy as np

from shared.config import MARKET
from pricing.src.engine import MarketAssumptions, price_loan

_MARKET = MarketAssumptions.from_market(MARKET)


class PricingOverrides(BaseModel):
    quoted_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    cost_of_funds: float | None = Field(default=None, ge=0.0, le=1.0)
    lgd: float | None = Field(default=None, ge=0.0, le=1.0)
    opex_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    tax_rate: float | None = Field(default=None, ge=0.0, lt=1.0)
    capital_ratio: float | None = Field(default=None, gt=0.0, le=1.0)
    base_margin: float | None = Field(default=None, ge=0.0, le=1.0)
    roe_hurdle: float | None = Field(default=None, ge=0.0, le=2.0)
    fee_rate: float | None = Field(default=None, ge=0.0, le=1.0)

    def market(self) -> MarketAssumptions:
        d = self.model_dump(exclude={"quoted_rate"})
        return _MARKET.replace(**{k: v for k, v in d.items() if v is not None})


def _book_under(app_state, market: MarketAssumptions) -> dict:
    """Re-price the whole booked book under these assumptions. ~8ms for 8,336 loans,
    so this can run on every slider tick. Uses the same price_loan the batch uses."""
    priced = app_state.priced
    pds = priced["pd"].to_numpy(dtype=float)
    eads = priced["ead"].to_numpy(dtype=float)
    rates = priced["quoted_rate"].to_numpy(dtype=float)
    clears = np.empty(len(priced), dtype=bool)
    for i in range(len(priced)):
        clears[i] = price_loan(pds[i], eads[i], rates[i], market)["clears_hurdle"]
    n = int(len(priced))
    n_clears = int(clears.sum())
    return {
        "n": n,
        "n_clears": n_clears,
        "share_clears": round(n_clears / n, 4) if n else 0.0,
        "mispriced_ead": round(float(eads[~clears].sum()), 2),
    }


def pricing_whatif(app_state, business_id: str, overrides: PricingOverrides):
    from app.v2 import explain, pricing

    # via _row(), so an unknown id raises UnknownLoan and the router answers 404.
    # price_one does a raw .loc[] and would raise a bare KeyError, which _guard
    # deliberately does not catch -- so the lookup MUST happen first.
    if not bool(explain._row(app_state, business_id)["booked"]):
        return None
    market = overrides.market()
    out = pricing.price_one(app_state, business_id, market, overrides.quoted_rate)
    out["book"] = _book_under(app_state, market)
    return out
```

- [ ] **Step 4: Add the endpoint**

```python
@router.post("/loan/{business_id}/pricing/whatif")
def pricing_whatif(request: Request, business_id: str,
                   overrides: whatif.PricingOverrides):
    return _guard(whatif.pricing_whatif, request.app.state, business_id, overrides)
```

- [ ] **Step 5: Run the tests and time the book re-price**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: all PASS.

Then confirm the slider will feel live:

```bash
PYTHONPATH=. .venv/bin/python - <<'EOF'
import warnings, time; warnings.filterwarnings("ignore")
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as c:
    c.post("/api/v2/loan/BIZ100002/pricing/whatif", json={})   # warm
    t0 = time.time()
    for lgd in [0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.45,0.55,0.65]:
        c.post("/api/v2/loan/BIZ100002/pricing/whatif", json={"lgd": lgd})
    print(f"10 slider ticks (book re-priced each): {time.time()-t0:.3f}s")
EOF
```

Expected: well under 1s for 10 ticks. If not, the UI must debounce the book recompute — note the measured number in the commit message either way.

- [ ] **Step 6: Commit**

```bash
git add app/v2 tests/test_app_v2.py
git commit -m "v2: pricing what-if -- sliders that re-price the loan and the book

Market overrides replace fields on the committed MarketAssumptions and go to
price_loan, so an empty override body reproduces the priced book exactly. The
whole booked book is re-priced on every tick.

Verified: 25 booked loans, empty overrides reproduce /api/pricing/<id> ROE to 1e-9
and clears_hurdle exactly; book totals match /api/pricing/summary; LGD 0.90 lowers
share_clears and raises expected loss; 10 slider ticks in <TIME>s.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Early-warning tab read path

**Files:**
- Create: `app/v2/ews.py`
- Modify: `app/v2/router.py`, `tests/test_app_v2.py`

**Interfaces:**
- Produces: `ews.ews_detail(app_state, business_id) -> dict | None` with `prob`, `risk_tier`, `tiers`, `triggers[]` (`{name, threshold, value, fired}`), `panel{months[], series{utilization,balance,deposit_inflow,days_past_due,overdraft_count}}`, `drivers[]`, `model_caveat`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_app_v2.py
TRIGGER_NAMES = ["HIGH_UTILIZATION", "RISING_UTILIZATION", "DELINQUENCY",
                 "DEPOSIT_DECLINE", "FREQUENT_OVERDRAFTS"]


def test_ews_detail_returns_the_full_24_month_panel(client):
    e = client.get("/api/v2/loan/BIZ100002/ews").json()
    assert e["panel"]["months"] == list(range(24))
    for name in ["utilization", "balance", "deposit_inflow",
                 "days_past_due", "overdraft_count"]:
        assert len(e["panel"]["series"][name]) == 24


def test_ews_triggers_show_thresholds_and_values_not_just_names(client):
    e = client.get("/api/v2/loan/BIZ100002/ews").json()
    assert [t["name"] for t in e["triggers"]] == TRIGGER_NAMES
    hu = next(t for t in e["triggers"] if t["name"] == "HIGH_UTILIZATION")
    assert hu["clauses"][0]["threshold"] == 0.90
    assert isinstance(hu["fired"], bool)
    delinq = next(t for t in e["triggers"] if t["name"] == "DELINQUENCY")
    assert [c["metric"] for c in delinq["clauses"]] == ["dpd_max", "dpd_recent"]


def test_every_fired_trigger_can_explain_itself(client):
    """`fired` is the module's verdict; `met` on each clause is the explanation the
    screen shows. If they ever disagree the screen contradicts itself.

    This is not hypothetical. Representing DELINQUENCY as its dpd_max clause alone
    made all 4,225 fired accounts -- 50.7% of the book -- render as
    "value 2, threshold 30, FIRED", because every one of them trips the
    `dpd_recent > 0` clause instead. A banker who sees that stops believing every
    other number on the screen.

    WHOLE BOOK, not a sample, and called directly rather than over HTTP. A
    self-consistency check is only worth having if it covers the rare states, and
    8,336 accounts x 5 triggers costs 0.5s this way."""
    from shared.config import EWS_TRIGGERS
    from app.v2 import ews as ews_mod
    st = client.app.state
    for bid in st.ews.index:
        rows = ews_mod.trigger_rows(st.v2.ews_feats.loc[bid], EWS_TRIGGERS,
                                    set(st.ews.loc[bid, "triggers"]))
        for t in rows:
            assert t["fired"] == any(c["met"] for c in t["clauses"]), (bid, t["name"])


def test_ews_fired_triggers_match_the_batch_watchlist(client):
    v1 = client.get("/api/ews/BIZ100002").json()
    v2 = client.get("/api/v2/loan/BIZ100002/ews").json()
    assert v2["prob"] == pytest.approx(v1["prob"], abs=1e-9)
    assert v2["risk_tier"] == v1["risk_tier"]
    assert sorted(t["name"] for t in v2["triggers"] if t["fired"]) == sorted(v1["triggers"])


def test_ews_quotes_the_metadata_numbers_not_recomputed_ones(client):
    """Held-out capture, not the in-sample figure. AUC is reported, never gated."""
    c = client.get("/api/v2/loan/BIZ100002/ews").json()["model_caveat"]
    assert c["top_decile_capture"] == 0.2159
    assert c["auc"] == 0.6622
    assert c["auc_is_gated"] is False


def test_ews_is_null_for_an_unbooked_applicant(client):
    unbooked = client.get("/api/v2/loans", params={"booked": "false"}).json()["loans"][0]
    assert client.get(f"/api/v2/loan/{unbooked['business_id']}/ews").json() is None
```

- [ ] **Step 2: Run and watch them fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v -k ews`
Expected: FAIL with 404.

- [ ] **Step 3: Write `app/v2/ews.py`** (`_trigger_rows` + `ews_detail`; one module per concern, as Tasks 4 and 6 established — these do NOT go in `explain.py`)

```python
from shared.config import EWS_TRIGGERS

# Each trigger is a LIST of clauses joined by OR, because flag_triggers' DELINQUENCY
# rule is compound: (dpd_max >= dpd_severe) | (dpd_recent > 0). Representing it as the
# single dpd_max clause made the screen contradict itself on every account where it
# fires -- all 4,225 of them (50.7% of the book) trip the recent clause with dpd_max
# below 30, so the row read "value 2, threshold 30, FIRED". A threshold source is a
# config key, or a literal number where the rule has one (dpd_recent > 0).
_TRIGGER_SPECS = [
    ("HIGH_UTILIZATION",    [("util_recent", ">", "high_utilization")]),
    ("RISING_UTILIZATION",  [("util_drift", ">", "rising_utilization")]),
    ("DELINQUENCY",         [("dpd_max", ">=", "dpd_severe"),
                             ("dpd_recent", ">", 0)]),
    ("DEPOSIT_DECLINE",     [("deposit_decline_pct", ">", "deposit_decline")]),
    ("FREQUENT_OVERDRAFTS", [("overdraft_recent", ">=", "overdraft_recent")]),
]

_CLAUSE_OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b}

_PANEL_SERIES = ["utilization", "balance", "deposit_inflow",
                 "days_past_due", "overdraft_count"]


def _trigger_rows(feat_row, cfg: dict, fired_names: set[str]) -> list[dict]:
    """Every trigger's clauses with their thresholds and this account's values, and
    `fired` taken from flag_triggers -- never recomputed here.

    `fired` is the module's verdict. `met` on each clause is display metadata that
    EXPLAINS that verdict. They must always agree (a fired trigger has at least one
    met clause); a test asserts it across the whole book, because a screen showing
    "value 2, threshold 30, FIRED" destroys trust in every other number on it.

    feat_row comes from the EWS FEATURE frame, not the scored watchlist row: the
    watchlist carries only KEY_METRICS, which excludes dpd_recent, so reading clause
    values off it would silently show 0.0 for the clause that actually fired.
    """
    rows = []
    for name, clauses in _TRIGGER_SPECS:
        spelled = []
        for metric, comparator, source in clauses:
            threshold = float(cfg[source]) if isinstance(source, str) else float(source)
            value = float(feat_row.get(metric, 0.0))
            spelled.append({
                "metric": metric, "comparator": comparator, "threshold": threshold,
                "value": round(value, 4),
                "met": bool(_CLAUSE_OPS[comparator](value, threshold)),
            })
        rows.append({"name": name, "join": "OR", "clauses": spelled,
                     "fired": name in fired_names})
    return rows


def ews_detail(app_state, business_id: str):
    p = _row(app_state, business_id)
    if not bool(p["booked"]):
        return None
    e = app_state.ews.loc[business_id]
    meta = app_state.ews_meta
    panel = app_state.v2.panel.loc[[business_id]].sort_values("month_index")
    return {
        "business_id": business_id,
        "prob": float(e["prob"]),
        "risk_tier": str(e["risk_tier"]),
        "tiers": meta["tiers"],
        "triggers": _trigger_rows(app_state.v2.ews_feats.loc[business_id],
                                  EWS_TRIGGERS, set(e["triggers"])),
        "panel": {
            "months": [int(m) for m in panel["month_index"]],
            "series": {c: [float(v) for v in panel[c]] for c in _PANEL_SERIES},
        },
        "drivers": [{"feature": r["feature"], "impact": r["impact"]}
                    for r in e["top_shap_reasons"]],
        "model_caveat": {
            "top_decile_capture": meta["metrics"]["top_decile_capture"],
            "top_decile_lift": meta["metrics"]["top_decile_lift"],
            "auc": meta["metrics"]["auc"],
            "auc_is_gated": False,
            "base_rate": meta["base_rate"],
            "note": ("Gated on top-decile capture, not AUC: the data-generating "
                     "process puts a real ceiling on separability. Held-out numbers."),
        },
    }
```

Note `_trigger_rows` reads `util_recent`, `util_drift`, `dpd_max`,
`deposit_decline_pct` and `overdraft_recent` off the EWS row.
`watchlist.score_population` writes `KEY_METRICS` onto the frame, which is exactly
these five — confirm before relying on it:

```bash
PYTHONPATH=. .venv/bin/python -c "from ews.src.watchlist import KEY_METRICS; print(KEY_METRICS)"
```

Expected: `['util_recent', 'util_drift', 'dpd_max', 'deposit_decline_pct', 'overdraft_recent']`.

- [ ] **Step 4: Add the endpoint**

```python
@router.get("/loan/{business_id}/ews")
def loan_ews(request: Request, business_id: str):
    return _guard(ews.ews_detail, request.app.state, business_id)
```

- [ ] **Step 5: Run the tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add app/v2 tests/test_app_v2.py
git commit -m "v2: early-warning tab read path -- the real 24-month panel per account

'What happened to this loan' is answered with the account's actual behavioural
series, which the EWS module already aggregates but never surfaces. Trigger rows
carry threshold and value; fired comes from flag_triggers, never recomputed here.

Verified: 24 months on all five series; prob, tier and fired triggers match
/api/ews/<id> exactly; the caveat quotes metadata (capture 0.2159, AUC 0.6622
reported not gated) rather than recomputing; unbooked returns null.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Early-warning what-if

**Files:**
- Create: `app/v2/ews_whatif.py`
- Modify: `app/v2/ews.py` (promote one helper), `app/v2/router.py`, `tests/test_app_v2.py`

**Where this code goes.** `EwsOverrides` and `ews_whatif` go in a new
`app/v2/ews_whatif.py`. They cannot go in `whatif.py` (145 of ~150 lines after Task 7),
and putting them in `ews.py` pushes that file to 181 — over the ceiling, which was
tried and rejected. The new module imports `InvalidOverride` from `app.v2.whatif` and
`trigger_rows` from `app.v2.ews`; `_guard` already turns `InvalidOverride` into a 422,
so no new routing is needed.

`ews.py` renames `_trigger_rows` to **`trigger_rows`** — it is now a genuine public
interface consumed by another module, and the leading underscore would misdescribe it.
`_TRIGGER_SPECS` and `_CLAUSE_OPS` stay private; only `trigger_rows` crosses the
boundary.

**The cross-field trap applies here too.** Task 5 found that per-field Pydantic bounds
let `{"t_low": 0.9}` through, because it is only incoherent once merged with the
committed `t_high`. `EwsOverrides` has the same shape: `t_med > t_high` empties the
Medium tier entirely. Validate the **merged** tiers in `tiers()` and raise
`InvalidOverride`, exactly as `DecisionOverrides.apply_to` does.

**Interfaces:**
- Produces: `ews_whatif.EwsOverrides` (Pydantic, bounded); `ews_whatif.ews_whatif(app_state, business_id, overrides) -> dict | None` with `risk_tier`, `triggers[]`, `book_tiers{High,Medium,Low}`, `tiers`, `trigger_config`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_app_v2.py
def test_ews_whatif_with_no_overrides_reproduces_the_batch_pipeline(client):
    ids = [l["business_id"] for l in client.get(
        "/api/v2/loans", params={"booked": "true", "limit": 25}).json()["loans"]]
    for bid in ids:
        batch = client.get(f"/api/ews/{bid}").json()
        live = client.post(f"/api/v2/loan/{bid}/ews/whatif", json={}).json()
        assert live["risk_tier"] == batch["risk_tier"], bid
        assert sorted(t["name"] for t in live["triggers"] if t["fired"]) == \
               sorted(batch["triggers"]), bid


def test_ews_whatif_book_tiers_match_the_batch_summary(client):
    summary = client.get("/api/ews/summary").json()
    live = client.post("/api/v2/loan/BIZ100002/ews/whatif", json={}).json()
    assert live["book_tiers"] == summary["tiers"]


def test_lowering_the_high_cutoff_grows_the_high_tier(client):
    base = client.post("/api/v2/loan/BIZ100002/ews/whatif", json={}).json()
    loose = client.post("/api/v2/loan/BIZ100002/ews/whatif",
                        json={"t_high": 0.25}).json()
    assert loose["book_tiers"]["High"] > base["book_tiers"]["High"]


def test_lowering_a_trigger_threshold_fires_it_for_more_accounts(client):
    loose = client.post("/api/v2/loan/BIZ100002/ews/whatif",
                        json={"high_utilization": 0.10}).json()
    hu = next(t for t in loose["triggers"] if t["name"] == "HIGH_UTILIZATION")
    assert hu["threshold"] == 0.10
    assert loose["book_trigger_counts"]["HIGH_UTILIZATION"] > 0


def test_ews_whatif_rejects_out_of_range(client):
    assert client.post("/api/v2/loan/BIZ100002/ews/whatif",
                       json={"t_high": 2.0}).status_code == 422
```

- [ ] **Step 2: Run and watch them fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v -k "ews_whatif or cutoff or trigger_threshold"`
Expected: FAIL with 405/404.

- [ ] **Step 3: Write `app/v2/ews_whatif.py`**

```python
from shared.config import EWS_TRIGGERS
from ews.src.triggers import flag_triggers
from ews.src.watchlist import risk_tier


class EwsOverrides(BaseModel):
    t_high: float | None = Field(default=None, ge=0.0, le=1.0)
    t_med: float | None = Field(default=None, ge=0.0, le=1.0)
    high_utilization: float | None = Field(default=None, ge=0.0, le=2.0)
    rising_utilization: float | None = Field(default=None, ge=-1.0, le=2.0)
    dpd_severe: int | None = Field(default=None, ge=0, le=180)
    deposit_decline: float | None = Field(default=None, ge=0.0, le=1.0)
    overdraft_recent: int | None = Field(default=None, ge=0, le=50)

    def tiers(self, base: dict) -> dict:
        d = dict(base)
        for k in ("t_high", "t_med"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        return d

    def trigger_cfg(self) -> dict:
        d = dict(EWS_TRIGGERS)
        d.update({k: v for k, v in self.model_dump(
            exclude={"t_high", "t_med"}).items() if v is not None})
        return d


def ews_whatif(app_state, business_id: str, overrides: EwsOverrides):
    from app.v2 import explain

    # via _row(), so an unknown id raises UnknownLoan and the router answers 404
    if not bool(explain._row(app_state, business_id)["booked"]):
        return None
    ews = app_state.ews
    tiers = overrides.tiers(app_state.ews_meta["tiers"])
    cfg = overrides.trigger_cfg()

    # score_population() derives risk_tier from the model's UNROUNDED probability but
    # persists prob rounded to 4dp. Two accounts (BIZ103657 0.16486203 -> 0.1649 and
    # BIZ108170 0.50725440 -> 0.5073) round exactly ONTO a cutoff, and risk_tier uses
    # >=, so re-deriving from the stored number flips both. With no tier override the
    # batch's own column is therefore the authority; risk_tier() is only re-run when
    # the caller actually moved a cutoff, which is the one case where the committed
    # column cannot answer. The residual 2-in-8,336 imprecision under an override is
    # inherent to the artifact, not introduced here.
    overrode = overrides.t_high is not None or overrides.t_med is not None
    retiered = ([risk_tier(p, tiers) for p in ews["prob"].to_numpy(dtype=float)]
                if overrode else list(ews["risk_tier"]))
    refired = flag_triggers(ews, cfg)

    pos = ews.index.get_loc(business_id)
    fired = set(refired[pos])
    counts: dict[str, int] = {}
    for lst in refired:
        for t in lst:
            counts[t] = counts.get(t, 0) + 1

    book_tiers: dict[str, int] = {}
    for t in retiered:
        book_tiers[t] = book_tiers.get(t, 0) + 1

    return {
        "business_id": business_id,
        "prob": float(ews.loc[business_id, "prob"]),
        "risk_tier": retiered[pos],
        "tiers": tiers,
        "triggers": ews._trigger_rows(ews.loc[business_id], cfg, fired),
        "trigger_config": cfg,
        "book_tiers": book_tiers,
        "book_trigger_counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
    }
```

`flag_triggers` reads `util_recent`, `util_drift`, `dpd_max`, `dpd_recent`,
`deposit_decline_pct` and `overdraft_recent` off the frame it is given. `dpd_recent`
is **not** in `KEY_METRICS`, so passing `app_state.ews` makes `flag_triggers` fall
back to zeros for it and `DELINQUENCY` could differ from the batch run. Step 4
resolves this before the code ships.

- [ ] **Step 4: Verify DELINQUENCY still matches, and fix it if not**

Run:

```bash
PYTHONPATH=. .venv/bin/python - <<'EOF'
import warnings; warnings.filterwarnings("ignore")
import pandas as pd
from shared.config import RAW
from ews.src.watchlist import score_population
from ews.src.feature_engineering import compute_ews_features
from ews.src.triggers import flag_triggers

# Probe the frame ews_whatif ACTUALLY passes -- the cached EWS feature frame, which
# carries dpd_recent. Running this against score_population()'s output instead gives
# 4111/8336, because the watchlist row only carries KEY_METRICS and flag_triggers
# then reads dpd_recent as 0.0. That is the frame's limitation, not a regression.
ews = score_population()
feats = compute_ews_features(pd.read_parquet(RAW / "portfolio.parquet"))
feats.index = feats["business_id"].astype(str)
refired = flag_triggers(feats.loc[ews.index])
same = sum(sorted(a) == sorted(b) for a, b in zip(ews["triggers"], refired))
print(f"rows whose triggers reproduce exactly: {same} / {len(ews)}")
EOF
```

Expected: `8336 / 8336`. **If it is lower, `dpd_recent` is the cause.** Fix by
caching the EWS feature frame on `V2State` in `build_state`:

```python
    from ews.src.feature_engineering import compute_ews_features
    ews_feats = compute_ews_features(pd.read_parquet(RAW / "portfolio.parquet"))
    ews_feats.index = ews_feats["business_id"].astype(str)
    # ews_whatif re-tiers positionally against app_state.ews, so the two frames must
    # stay in the same ORDER, not merely hold the same ids. They do today because both
    # derive from this one call, but nothing else enforces it and a silent reorder
    # would return another loan's tier under the right business_id.
    assert ews_feats.index.equals(app_state.ews.index), (
        "ews_feats and app.state.ews are misaligned; v2 would report the wrong "
        "loan's risk tier")
```

add `ews_feats: pd.DataFrame` to `V2State`, and pass `app_state.v2.ews_feats` to
`flag_triggers` instead of `app_state.ews`. Re-run the probe until it prints
`8336 / 8336`.

- [ ] **Step 5: Add the endpoint**

```python
@router.post("/loan/{business_id}/ews/whatif")
def ews_whatif(request: Request, business_id: str, overrides: whatif.EwsOverrides):
    return _guard(whatif.ews_whatif, request.app.state, business_id, overrides)
```

- [ ] **Step 6: Run the tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add app/v2 tests/test_app_v2.py
git commit -m "v2: early-warning what-if -- drag tier cutoffs and trigger thresholds

Re-tiering calls risk_tier and re-flagging calls flag_triggers, the same functions
the batch run uses, so an empty override body reproduces the watchlist exactly.

Verified: 25 booked loans, empty overrides reproduce /api/ews/<id> tier and fired
triggers exactly; book tier counts match /api/ews/summary; t_high 0.25 grows the
High tier; trigger re-flagging reproduces all 8,336 rows.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: Line-increase tab read path

**Files:**
- Create: `app/v2/line_increase.py`
- Modify: `app/v2/router.py`, `tests/test_app_v2.py`

**Interfaces:**
- Produces: `line_increase.line_increase_detail(app_state, business_id) -> dict | None` with `prob`, `caps[]` (`{name, amount, binding}`), `recommended_amount`, `incremental{ead, waterfall[], roe, clears_hurdle}`, `eligibility{clauses[], eligible}`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_app_v2.py
def test_line_increase_shows_which_cap_binds(client):
    li = client.get("/api/v2/loan/BIZ100002/line-increase").json()
    assert [c["name"] for c in li["caps"]] == [
        "headroom_to_target_util", "pct_cap", "revenue_ceiling"]
    binding = [c for c in li["caps"] if c["binding"]]
    assert len(binding) == 1


def test_exactly_one_cap_binds_on_every_booked_account(client):
    """Whole book. Two caps can tie exactly -- BIZ111364's pct_cap and
    revenue_ceiling are both 5,000.00 -- and a single-loan test cannot see it. Same
    shape as every other defect this file has produced: a silent contract violation
    on one rare row."""
    from app.v2 import line_increase as li_mod
    st = client.app.state
    for bid in st.li.index:
        caps = li_mod.line_increase_detail(st, bid)["caps"]
        if not caps:                      # credit_limit <= 0 returns no caps
            continue
        assert sum(1 for c in caps if c["binding"]) == 1, (bid, caps)


def test_eligibility_explains_itself_on_every_booked_account(client):
    """`eligible` is candidates()' verdict; the clauses explain it. They must agree.

    WHOLE BOOK, not a sample. The 40-loan `booked_sample_ids` fixture contains ZERO
    eligible accounts and only 2 with a positive recommended amount, so a sampled
    version of this test is structurally blind to the exact states it exists to
    check -- a comparator flip on one clause surfaces on 57 of 8,336 rows and the
    sample misses all of them. Called directly rather than over HTTP, all 8,336
    cost 0.6s."""
    from app.v2 import line_increase as li_mod
    st = client.app.state
    for bid in st.li.index:
        e = li_mod.line_increase_detail(st, bid)["eligibility"]
        assert e["eligible"] == all(c["pass"] for c in e["clauses"]), (bid, e)


def test_eligibility_is_four_clauses_not_one_number(client):
    """The documented trap: 95 accounts are eligible, 1,243 have a positive
    recommended amount. Showing the clauses is what makes the gap legible."""
    li = client.get("/api/v2/loan/BIZ100002/line-increase").json()
    names = [c["name"] for c in li["eligibility"]["clauses"]]
    assert names == ["prob_above_threshold", "pd_within_appetite",
                     "amount_positive", "clears_hurdle"]
    assert li["eligibility"]["eligible"] == all(
        c["pass"] for c in li["eligibility"]["clauses"])


def test_line_increase_matches_the_batch_pipeline(client, booked_sample_ids):
    """Tolerance 6e-5, not 1e-4: the batch rounds incremental_roe to 4dp, so half an
    ulp (5e-5) is the tightest honest bound and anything looser stops catching the
    real failure -- recomputing ROE from the PERSISTED 4dp pd instead of the unrounded
    scorecard pd, which differs by up to 1.4e-4.

    clears_hurdle is compared exactly, because that is where the difference bites: on
    one of the 1,243 loans with a positive amount the rounded pd flips it, and it is
    the fourth eligibility clause."""
    for bid in booked_sample_ids:
        v1 = client.get(f"/api/line-increase/{bid}").json()
        v2 = client.get(f"/api/v2/loan/{bid}/line-increase").json()
        assert v2["recommended_amount"] == pytest.approx(v1["recommended_amount"], abs=1e-6), bid
        assert v2["eligibility"]["eligible"] == v1["eligible"], bid
        assert v2["incremental"]["clears_hurdle"] == v1["clears_hurdle"], bid
        assert v2["incremental"]["roe"] == pytest.approx(v1["incremental_roe"], abs=6e-5), bid


def test_every_clause_agrees_with_the_module_that_computed_it(client):
    """Whole book, clause by clause -- not just the verdict.

    `eligible == all(pass)` is necessary but NOT sufficient: on BIZ101719 the
    pd_within_appetite clause read PASS from the rounded pd while candidates had
    excluded the loan for exactly that reason, and the test stayed green because two
    other clauses also failed. The verdict was right and the REASON was wrong, which
    on a reason-code screen is the defect that matters."""
    from app.v2 import line_increase as li_mod
    st = client.app.state
    meta = st.li_meta
    for bid in st.li.index:
        e = li_mod.line_increase_detail(st, bid)["eligibility"]
        by = {c["name"]: c for c in e["clauses"]}
        exact_pd = float(st.scores.loc[bid, "pd"])
        assert by["pd_within_appetite"]["pass"] == (exact_pd <= meta["offer_max_pd"]), bid
        assert by["prob_above_threshold"]["pass"] == (
            float(st.li.loc[bid, "prob"]) >= meta["offer_threshold"]), bid
        assert by["amount_positive"]["pass"] == (
            float(st.li.loc[bid, "recommended_amount"]) > 0), bid


def test_clears_hurdle_matches_the_batch_on_every_loan_with_an_amount(client):
    """Whole book. The flip this guards happens on exactly ONE of 1,243 loans, so a
    40-loan sample cannot see it -- the same blindness that let the eligibility
    comparator bug through."""
    from app.v2 import line_increase as li_mod
    st = client.app.state
    for bid in st.li.index:
        if float(st.li.loc[bid, "recommended_amount"]) <= 0:
            continue
        v2 = li_mod.line_increase_detail(st, bid)
        assert v2["incremental"]["clears_hurdle"] == bool(st.li.loc[bid, "clears_hurdle"]), bid


def test_eligible_count_is_95_not_the_positive_amount_count(client):
    """Guards the gotcha directly."""
    eligible = client.get("/api/v2/loans", params={"li_eligible": "true"}).json()
    assert eligible["total"] == 95


def test_line_increase_is_null_for_an_unbooked_applicant(client):
    unbooked = client.get("/api/v2/loans", params={"booked": "false"}).json()["loans"][0]
    assert client.get(
        f"/api/v2/loan/{unbooked['business_id']}/line-increase").json() is None
```

- [ ] **Step 2: Run and watch them fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v -k "line_increase or eligib or cap"`
Expected: FAIL with 404.

- [ ] **Step 3: Write `app/v2/line_increase.py`** (`_caps` + `line_increase_detail`; one module per concern — these do NOT go in `explain.py`)

```python
from shared.config import LINE_INCREASE
from line_increase.src.amount_rules import incremental_roe

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
    # min() over the KEYS, not a value comparison: two caps can tie exactly.
    # BIZ111364 (balance 10,180 · limit 10,000 · revenue 50,000) gives pct_cap
    # 0.50*10,000 = 5,000.00 and revenue_ceiling 0.30*50,000-10,000 = 5,000.00 --
    # an exact float tie, not a rounding artifact. Comparing `v == lowest` marks both
    # binding, and the tab's whole claim is that ONE cap binds. First key wins, which
    # is deterministic because `values` is built in a fixed order.
    binding_key = min(values, key=values.get)
    return [{"name": k, "amount": round(float(v), 2), "binding": k == binding_key}
            for k, v in values.items()]


def line_increase_detail(app_state, business_id: str):
    p = _row(app_state, business_id)
    if not bool(p["booked"]):
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
```

- [ ] **Step 4: Add the endpoint**

```python
@router.get("/loan/{business_id}/line-increase")
def loan_line_increase(request: Request, business_id: str):
    return _guard(line_increase.line_increase_detail, request.app.state, business_id)
```

- [ ] **Step 5: Run the tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v`
Expected: all PASS, including `test_eligible_count_is_95_not_the_positive_amount_count`.

- [ ] **Step 6: Commit**

```bash
git add app/v2 tests/test_app_v2.py
git commit -m "v2: line-increase tab -- binding cap and four-clause eligibility

Eligibility is an AND of four clauses; showing them separately is what makes the
documented gap legible (95 eligible vs 1,243 with a positive recommended amount)
instead of a footnote. The three amount caps are shown with the binding one marked.

Verified: recommended amount, eligibility and incremental ROE match
/api/line-increase/<id>; the eligible filter totals 95; exactly one cap binds;
unbooked returns null.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11: Front-end shell — selector, header, tab chrome

**Files:**
- Create: `app/static/v2/index.html`, `app/static/v2/styles.css`, `app/static/v2/svg.js`, `app/static/v2/app.js`
- Delete: `app/static/v2/.gitkeep`
- Modify: `app/v2/router.py` (add the `/v2` page route)

**Interfaces:**
- Consumes: `GET /api/v2/filters`, `GET /api/v2/loans`, `GET /api/v2/loan/{id}`.
- Produces: `app.js` globals `state` (`{loanId, tab, filters}`), `api(path, body)` fetch helper, `renderHeader(h)`, `renderSelector()`, `selectTab(name)`. Later tasks add `renderDecision`, `renderPricing`, `renderEws`, `renderLineIncrease` and register them in the `TABS` map.

**Verification method for all front-end tasks:** the page has no build step and no
JS test runner, so verification is a real browser against a real server. Start it
with `make run` in the background, drive it with the built-in browser tools
(`mcp__Claude_Browser__navigate`, `get_page_text`, `find`, `computer`), assert on
extracted text, and take one screenshot per task. Stop the server with `make stop`.

- [ ] **Step 1: Add the page route to `app/v2/router.py`**

`include_router` applies the parent's prefix, so the `/v2` page cannot hang off the
`/api/v2` router. Use a second, prefix-less router in the same module:

```python
from pathlib import Path

from fastapi.responses import FileResponse

_STATIC = Path(__file__).resolve().parent.parent / "static" / "v2"

page_router = APIRouter(tags=["v2"])


@page_router.get("/v2", include_in_schema=False)
def v2_page():
    return FileResponse(_STATIC / "index.html")
```

Both routers are included from the single `include_router` statement already budgeted
in `app/main.py` — change that one line to:

```python
for r in (v2_router.router, v2_router.page_router): app.include_router(r)
```

which keeps `app/main.py` at four added statements.

- [ ] **Step 2: Write `app/static/v2/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Loan Workbench — Banking Analytics Workshop</title>
<link rel="stylesheet" href="/static/v2/styles.css">
</head>
<body>
<header>
  <div>
    <h1>Loan Workbench <span class="badge">v2</span></h1>
    <p>One loan, every ingredient — decision, price, and early warning.</p>
  </div>
  <a class="v1link" href="/">← v1 portal</a>
</header>

<section id="selector">
  <div class="filters" id="filters"></div>
  <div class="pick">
    <input id="q" placeholder="business_id, e.g. BIZ100002" autocomplete="off">
    <select id="loanpick"><option>Loading…</option></select>
    <span class="count" id="matchcount"></span>
    <button id="clearfilters" type="button">Clear filters</button>
  </div>
</section>

<section id="loanheader" class="hidden"></section>

<nav id="tabs" class="hidden">
  <button data-tab="decision" class="active">Decision</button>
  <button data-tab="pricing">Pricing &amp; Profitability</button>
  <button data-tab="ews">Early Warning</button>
  <button data-tab="line_increase">Line Increase <span class="opt">optional</span></button>
</nav>

<main id="panel" class="hidden"></main>
<p id="empty" class="muted">Pick a loan to begin.</p>

<script src="/static/v2/svg.js"></script>
<script src="/static/v2/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Write `app/static/v2/styles.css`**

Sized for a projected screen on Zoom: base font 16px, table text no smaller than
14px, no hover-only information, colour never the sole carrier of meaning (every
fired/passed state also carries a glyph).

```css
:root {
  --ink:#1a2332; --line:#d8dee9; --ok:#1a7f4b; --warn:#b7791f;
  --bad:#b3372e; --accent:#245bb2; --bg:#f6f8fb; --panel:#fff; --muted:#5b6572;
}
* { box-sizing:border-box; }
body { font-family:-apple-system,"Segoe UI",Roboto,sans-serif; color:var(--ink);
       margin:0; background:var(--bg); font-size:16px; }
header { background:var(--ink); color:#fff; padding:14px 24px;
         display:flex; justify-content:space-between; align-items:center; }
header h1 { font-size:20px; margin:0; font-weight:600; }
header p { margin:2px 0 0; font-size:13px; opacity:.75; }
.badge { background:var(--accent); border-radius:4px; padding:1px 7px; font-size:13px; }
.v1link { color:#cfe0ff; font-size:14px; text-decoration:none; }
section, main { background:var(--panel); border:1px solid var(--line);
                border-radius:8px; margin:16px 24px; padding:16px 20px; }
.filters { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:10px; }
.filters label { font-size:12px; color:var(--muted); display:block; }
select, input { padding:7px 9px; border:1px solid var(--line);
                border-radius:6px; font-size:15px; background:#fff; color:var(--ink); }
#loanpick { min-width:280px; }
.count { font-size:13px; color:var(--muted); }
button { padding:7px 13px; border:0; border-radius:6px; background:var(--accent);
         color:#fff; font-size:14px; cursor:pointer; }
button:hover { filter:brightness(1.1); }
nav#tabs { display:flex; gap:6px; margin:0 24px; padding:0; border:0; background:none; }
nav#tabs button { background:#e7ecf4; color:var(--ink); border-radius:8px 8px 0 0; }
nav#tabs button.active { background:var(--panel); font-weight:600;
                         border:1px solid var(--line); border-bottom-color:var(--panel); }
.opt { font-size:11px; opacity:.7; }
.hidden { display:none; }
.muted { color:var(--muted); margin:16px 24px; }
.hdr-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }
.hdr-grid .lbl { font-size:12px; color:var(--muted); }
.hdr-grid .val { font-size:17px; font-weight:600; }
.chip { display:inline-block; padding:3px 12px; border-radius:12px;
        font-weight:700; font-size:16px; color:#fff; }
.chip.Approve { background:var(--ok); } .chip.Refer { background:var(--warn); }
.chip.Decline { background:var(--bad); }
table { border-collapse:collapse; font-size:14px; width:100%; margin-top:10px; }
td, th { border:1px solid var(--line); padding:5px 10px; text-align:right; }
th:first-child, td:first-child { text-align:left; }
.fired { color:var(--bad); font-weight:600; }
.passed { color:var(--ok); }
```

- [ ] **Step 4: Write `app/static/v2/app.js` — shell only**

```javascript
"use strict";
/* Loan Workbench v2.
   This file formats and draws. It never calculates a financial number: every value
   on screen came from a server response, because the server calls the same module
   function the batch pipeline calls. */

const FACETS = ["decision", "score_band", "industry", "region",
                "booked", "ews_tier", "mispriced", "li_eligible"];
const TABS = {};   // tab name -> render function, filled by later files/tasks

const state = { loanId: null, tab: "decision", filters: {} };

async function api(path, body) {
  const opts = body === undefined
    ? {} : {method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)};
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(path + " -> " + r.status);
  return r.json();
}

const fmt = {
  money: v => "$" + Math.round(v).toLocaleString(),
  pct: (v, d = 1) => (v * 100).toFixed(d) + "%",
  bps: v => Math.round(v).toLocaleString() + " bps",
  num: (v, d = 2) => Number(v).toFixed(d),
};

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else n.setAttribute(k, v);
  }
  for (const kid of kids) n.append(kid?.nodeType ? kid : document.createTextNode(kid));
  return n;
}

/* localStorage throws rather than returning null in restricted contexts, so every
   access is guarded. Remembered filters are a convenience, never a dependency. */
function remember(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* fine */ }
}
function recall(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch (e) { return fallback; }
}

async function renderSelector() {
  const facets = await api("/api/v2/filters");
  const box = document.getElementById("filters");
  box.innerHTML = "";
  for (const f of FACETS) {
    const sel = el("select", {id: "f_" + f});
    sel.append(el("option", {value: ""}, "any"));
    for (const o of facets[f]) {
      sel.append(el("option", {value: String(o.value)},
                    `${o.value} (${o.count.toLocaleString()})`));
    }
    sel.value = state.filters[f] || "";
    sel.onchange = () => {
      state.filters[f] = sel.value;
      remember("v2.filters", state.filters);
      refreshMatches();
    };
    const wrap = el("div");
    wrap.append(el("label", {}, f.replace(/_/g, " ")), sel);
    box.append(wrap);
  }
  document.getElementById("q").oninput = debounce(refreshMatches, 250);
  document.getElementById("clearfilters").onclick = () => {
    state.filters = {};
    remember("v2.filters", {});
    document.getElementById("q").value = "";
    renderSelector().then(refreshMatches);
  };
  await refreshMatches();
}

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

async function refreshMatches() {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(state.filters)) if (v) params.set(k, v);
  const q = document.getElementById("q").value.trim();
  if (q) params.set("q", q);
  const r = await api("/api/v2/loans?" + params.toString());
  const pick = document.getElementById("loanpick");
  pick.innerHTML = "";
  for (const l of r.loans) {
    pick.append(el("option", {value: l.business_id},
      `${l.business_id} · ${l.decision} · band ${l.score_band} · ${l.industry} · ${fmt.money(l.requested_amount)}`));
  }
  document.getElementById("matchcount").textContent =
    r.total === r.shown ? `${r.total.toLocaleString()} matches`
                        : `${r.shown} of ${r.total.toLocaleString()} shown`;
  pick.onchange = () => loadLoan(pick.value);
  if (r.loans.length) await loadLoan(r.loans[0].business_id);
}

async function loadLoan(id) {
  state.loanId = id;
  const h = await api("/api/v2/loan/" + id);
  renderHeader(h);
  for (const n of ["loanheader", "tabs", "panel"])
    document.getElementById(n).classList.remove("hidden");
  document.getElementById("empty").classList.add("hidden");
  await selectTab(state.tab);
}

function renderHeader(h) {
  const box = document.getElementById("loanheader");
  box.innerHTML = "";
  const cells = [
    ["business", h.business_id],
    ["industry / region", `${h.identity.industry} · ${h.identity.region}`],
    ["entity / age", `${h.identity.entity_type} · ${fmt.num(h.identity.years_in_business, 1)} yrs`],
    ["requested", `${fmt.money(h.terms.requested_amount)} · ${h.terms.term_months}mo`],
    ["purpose", `${h.terms.loan_purpose}${h.terms.collateral_flag ? " · secured" : ""}`],
    ["score", `${h.score.business_score} (band ${h.score.score_band})`],
    ["model PD", fmt.pct(h.score.pd, 2)],
    ["booked", h.booked ? "yes" : "no — never funded"],
  ];
  const grid = el("div", {class: "hdr-grid"});
  for (const [lbl, val] of cells) {
    const d = el("div");
    d.append(el("div", {class: "lbl"}, lbl), el("div", {class: "val"}, val));
    grid.append(d);
  }
  const dec = el("div");
  dec.append(el("div", {class: "lbl"}, "decision"),
             el("span", {class: "chip " + h.decision}, h.decision));
  grid.append(dec);
  box.append(grid);
  state.header = h;
}

async function selectTab(name) {
  state.tab = name;
  remember("v2.tab", name);
  for (const b of document.querySelectorAll("#tabs button"))
    b.classList.toggle("active", b.dataset.tab === name);
  const panel = document.getElementById("panel");
  if (!TABS[name]) { panel.innerHTML = "<p class='muted'>Not built yet.</p>"; return; }
  panel.innerHTML = "<p class='muted'>Loading…</p>";
  await TABS[name](panel, state.loanId);
}

function start() {
  state.filters = recall("v2.filters", {});
  state.tab = recall("v2.tab", "decision");
  for (const b of document.querySelectorAll("#tabs button"))
    b.onclick = () => selectTab(b.dataset.tab);
  renderSelector().catch(e => {
    document.getElementById("empty").textContent = "Failed to load: " + e.message;
  });
}
document.addEventListener("DOMContentLoaded", start);
```

- [ ] **Step 5: Write `app/static/v2/svg.js` — the drawing primitives**

Four tabs need the same four shapes. Writing them once here is why Tasks 12–15 are
composition rather than four reinventions of pointer-drag maths.

```javascript
"use strict";
/* Inline-SVG primitives for the workbench. No library, no CDN -- the page must work
   offline in a devcontainer. These draw; they never decide anything. Every value
   passed in came from a server response. */

const NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs = {}) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
}

function svgRoot(width, height) {
  const s = svgEl("svg", {viewBox: `0 0 ${width} ${height}`, width: "100%",
                          height: height, role: "img"});
  return s;
}

/* A 24-point series. y is scaled to the series' own min/max, so a flat series does
   not become noise. `threshold` draws a dashed rule in the series' own units. */
function sparkline(values, {width = 620, height = 68, threshold = null,
                            label = "", format = v => v.toFixed(2)} = {}) {
  const pad = {l: 8, r: 96, t: 10, b: 10};
  const s = svgRoot(width, height);
  const lo = Math.min(...values, threshold === null ? Infinity : threshold);
  const hi = Math.max(...values, threshold === null ? -Infinity : threshold);
  const span = (hi - lo) || 1;
  const x = i => pad.l + i * (width - pad.l - pad.r) / (values.length - 1);
  const y = v => pad.t + (hi - v) * (height - pad.t - pad.b) / span;

  if (threshold !== null) {
    s.append(svgEl("line", {x1: pad.l, x2: width - pad.r, y1: y(threshold),
                            y2: y(threshold), stroke: "var(--bad)",
                            "stroke-dasharray": "4 3", "stroke-width": 1}));
  }
  s.append(svgEl("polyline", {
    points: values.map((v, i) => `${x(i)},${y(v)}`).join(" "),
    fill: "none", stroke: "var(--accent)", "stroke-width": 2,
    "stroke-linejoin": "round"}));
  s.append(svgEl("circle", {cx: x(values.length - 1), cy: y(values[values.length - 1]),
                            r: 3.5, fill: "var(--accent)"}));
  const t = svgEl("text", {x: width - pad.r + 8, y: height / 2 + 4,
                           "font-size": 13, fill: "var(--ink)"});
  t.textContent = `${label} ${format(values[values.length - 1])}`;
  s.append(t);
  return s;
}

/* Signed contributions around a zero line. Right = pushes PD up. */
function divergingBars(rows, {width = 620, rowHeight = 20,
                              labelWidth = 190, format = v => v.toFixed(3)} = {}) {
  const height = rows.length * rowHeight + 12;
  const s = svgRoot(width, height);
  const mid = labelWidth + (width - labelWidth - 90) / 2;
  const max = Math.max(...rows.map(r => Math.abs(r.contribution))) || 1;
  const scale = (width - labelWidth - 90) / 2 / max;

  s.append(svgEl("line", {x1: mid, x2: mid, y1: 4, y2: height - 4,
                          stroke: "var(--line)"}));
  rows.forEach((r, i) => {
    const yTop = 6 + i * rowHeight;
    const w = Math.abs(r.contribution) * scale;
    const up = r.contribution > 0;
    s.append(svgEl("rect", {x: up ? mid : mid - w, y: yTop, width: w,
                            height: rowHeight - 6, rx: 2,
                            fill: up ? "var(--bad)" : "var(--ok)"}));
    const lab = svgEl("text", {x: 0, y: yTop + rowHeight - 10, "font-size": 12,
                               fill: "var(--ink)"});
    lab.textContent = `${r.feature}  ${r.value ?? ""}`;
    s.append(lab);
    const val = svgEl("text", {x: width - 84, y: yTop + rowHeight - 10,
                               "font-size": 12, fill: "var(--muted)"});
    val.textContent = format(r.contribution);
    s.append(val);
  });
  return s;
}

/* Horizontal bars for the three line-increase caps; the binding one is filled. */
function hbars(rows, {width = 560, rowHeight = 26, labelWidth = 200} = {}) {
  const height = rows.length * rowHeight + 10;
  const s = svgRoot(width, height);
  const max = Math.max(...rows.map(r => Math.abs(r.amount))) || 1;
  rows.forEach((r, i) => {
    const y = 6 + i * rowHeight;
    const w = Math.max(0, r.amount) / max * (width - labelWidth - 110);
    s.append(svgEl("rect", {
      x: labelWidth, y, width: w, height: rowHeight - 10, rx: 2,
      fill: r.binding ? "var(--accent)" : "none",
      stroke: "var(--accent)", "stroke-width": 1}));
    const lab = svgEl("text", {x: 0, y: y + rowHeight - 14, "font-size": 12});
    lab.textContent = r.name.replace(/_/g, " ") + (r.binding ? "  (binds)" : "");
    s.append(lab);
  });
  return s;
}

/* An axis carrying draggable threshold handles and one fixed pin.
   `handles` is [{key, value, label}]; onChange({key: value, ...}) fires on drag,
   debounced by the caller. The axis NEVER decides anything -- it reports a number
   and the server recomputes. */
function axisWithHandles(
    {min = 0, max = 1, pin = null, pinLabel = "", handles = [], bands = [],
     width = 640, height = 76, format = v => v.toFixed(4)}, onChange) {
  const pad = {l: 20, r: 20, t: 26, b: 22};
  const s = svgRoot(width, height);
  const innerW = width - pad.l - pad.r;
  const toX = v => pad.l + (v - min) / (max - min) * innerW;
  const toV = x => Math.min(max, Math.max(min,
                     min + (x - pad.l) / innerW * (max - min)));

  for (const b of bands) {
    s.append(svgEl("rect", {x: toX(b.from), y: pad.t - 10,
                            width: Math.max(0, toX(b.to) - toX(b.from)),
                            height: 20, fill: b.fill, opacity: 0.25}));
  }
  s.append(svgEl("line", {x1: pad.l, x2: width - pad.r, y1: pad.t,
                          y2: pad.t, stroke: "var(--ink)", "stroke-width": 2}));

  if (pin !== null) {
    s.append(svgEl("line", {x1: toX(pin), x2: toX(pin), y1: pad.t - 14,
                            y2: pad.t + 14, stroke: "var(--ink)", "stroke-width": 3}));
    const pt = svgEl("text", {x: toX(pin), y: pad.t - 18, "font-size": 12,
                              "text-anchor": "middle", "font-weight": "600"});
    pt.textContent = `${pinLabel} ${format(pin)}`;
    s.append(pt);
  }

  const values = Object.fromEntries(handles.map(h => [h.key, h.value]));
  for (const h of handles) {
    const g = svgEl("g", {style: "cursor:ew-resize"});
    const tri = svgEl("polygon", {fill: "var(--accent)"});
    const txt = svgEl("text", {"font-size": 12, "text-anchor": "middle",
                               fill: "var(--accent)", y: pad.t + 34});
    const place = v => {
      const x = toX(v);
      tri.setAttribute("points", `${x},${pad.t + 2} ${x - 7},${pad.t + 18} ${x + 7},${pad.t + 18}`);
      txt.setAttribute("x", x);
      txt.textContent = `${h.label} ${format(v)}`;
    };
    place(h.value);
    g.append(tri, txt);

    let dragging = false;
    const move = ev => {
      if (!dragging) return;
      const box = s.getBoundingClientRect();
      const x = (ev.clientX - box.left) / box.width * width;
      const v = toV(x);
      values[h.key] = v;
      place(v);
      onChange({...values});
    };
    g.addEventListener("pointerdown", ev => {
      dragging = true; g.setPointerCapture(ev.pointerId); ev.preventDefault();
    });
    g.addEventListener("pointermove", move);
    g.addEventListener("pointerup", ev => {
      dragging = false;
      try { g.releasePointerCapture(ev.pointerId); } catch (e) { /* already gone */ }
    });
    s.append(g);
  }
  return s;
}
```

- [ ] **Step 6: Delete the placeholder and start the server**

```bash
git rm --cached app/static/v2/.gitkeep && rm -f app/static/v2/.gitkeep
make run
```

Run `make run` in the background so the browser steps can drive it.

- [ ] **Step 7: Verify in a real browser**

Navigate to `http://localhost:8100/v2`. Then assert, via page text:

- the heading reads `Loan Workbench v2`
- eight filter dropdowns are present
- the match count reads `200 of 12,000 shown`
- a loan header appears with a decision chip
- setting the `score_band` filter to `D` changes the match count and every option shows `band D`

Take one screenshot. Then check the console is clean:
`mcp__Claude_Browser__read_console_messages` with `onlyErrors: true` → expect zero entries.

- [ ] **Step 8: Run the Python tests and stop the server**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -v && make stop`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add app/static/v2 app/v2/router.py app/main.py
git commit -m "v2: front-end shell -- filtered selector, persistent loan header, tabs

The header never scrolls away, so the audience cannot lose which loan is on screen.
Filters compose and the count reports the true total rather than silently
truncating. Every localStorage access is wrapped: it throws rather than returning
null in restricted contexts.

Verified in a real browser at /v2: eight facets render, count reads '200 of 12,000
shown', band=D narrows correctly, header and decision chip populate, console clean.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 12: Decision tab UI with the draggable PD ruler

**Files:**
- Create: `app/static/v2/tab-decision.js`
- Modify: `app/static/v2/index.html` (one `<script>` tag), `app/static/v2/styles.css`

**Interfaces:**
- Consumes: `GET /api/v2/loan/{id}/decision`, `POST /api/v2/loan/{id}/decision/whatif`; `api`, `fmt`, `el`, `debounce` from `app.js`; `divergingBars`, `axisWithHandles` from `svg.js`.
- Produces: registers `TABS.decision`.

- [ ] **Step 1: Write `app/static/v2/tab-decision.js`**

Compose the `svg.js` primitives. Write these four pieces in order, each small:

1. `rulesTable(rows, caption)` — columns rule / this loan / comparator / threshold / status. Status renders the three flags **distinctly**, because collapsing them is what made the payload lie: `fired` → `✗ fired` in `.fired`; `applicable` but not met → `✓ clear` in `.passed`; **not applicable** → `— n/a (zone)` in muted text, with the row's `condition_met` shown as a quiet parenthetical when it is true, e.g. `— n/a (condition true, but the PD zones already decided)`. Never paint a non-applicable row red: on 43.4% of applicants its condition is true while it changed nothing.
2. `ledgerBars(ledger)` — `divergingBars(ledger.contributions)` plus a footer line reading `intercept {x} + contributions {y} = log-odds {z}`, every one of those three numbers taken **from the response**. Do not sum the contributions in JS: the server already did, and a JS sum that drifts would be invisible.
3. `pdRuler(zones, onChange)` — `axisWithHandles` configured for PD:

```javascript
function pdRuler(z, onChange) {
  return axisWithHandles({
    min: 0, max: Math.max(0.6, z.pd * 1.2), pin: z.pd, pinLabel: "this loan PD",
    bands: [{from: 0, to: z.t_low, fill: "var(--ok)"},
            {from: z.t_low, to: z.t_high, fill: "var(--warn)"},
            {from: z.t_high, to: Math.max(0.6, z.pd * 1.2), fill: "var(--bad)"}],
    handles: [{key: "t_low", value: z.t_low, label: "t_low"},
              {key: "t_high", value: z.t_high, label: "t_high"}],
  }, debounce(onChange, 120));
}
```
4. `TABS.decision = async (panel, id) => {...}` — fetch the detail, draw decision chip + ruler + book-mix tiles + both rule tables + both ledgers + the nearest-flip line, then wire the ruler's `onChange` to POST the what-if and re-render **only** the chip, the rule tables, the book mix and the flipped count.

Rules for this file, enforced by review:
- Nothing computes a threshold comparison in JS. `fired` comes from the response.
- The book mix tiles read `book_mix` from the response.
- `flipped_count` is displayed as `N loans change decision`.

- [ ] **Step 2: Add the script tag**

In `index.html`, immediately after the `app.js` tag:

```html
<script src="/static/v2/tab-decision.js"></script>
```

- [ ] **Step 3: Verify in a real browser**

`make run`, navigate to `http://localhost:8100/v2`, select `BIZ100002`, Decision tab. Assert via page text:

- the rules table lists all four knockouts with thresholds `1`, `0`, `3`, `6`
- the ledger footer's three numbers satisfy `intercept + contributions = log-odds` when you read them off the page
- dragging the `t_low` handle to the far left changes the book mix tile for Approve to `0` and the flipped count to a non-zero number

Drag by computing the handle's coordinates from a screenshot and using
`mcp__Claude_Browser__computer` with `left_click_drag`. Screenshot before and after.
Console errors: zero.

- [ ] **Step 4: Run the Python tests and stop the server**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -q && make stop`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/static/v2
git commit -m "v2: decision tab -- rules ledger, two rationales, draggable PD ruler

Dragging a cutoff re-decides the whole book server-side and reports how many loans
changed. Every fired/clear state comes from the response; nothing compares a value
to a threshold in JavaScript.

Verified in a real browser: four knockouts with their thresholds render; the
additive footer reads correctly off the page; dragging t_low to zero empties the
Approve tile and shows a non-zero flipped count; console clean.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 13: Pricing tab UI — waterfall, rate ladder, sliders

**Files:**
- Create: `app/static/v2/tab-pricing.js`
- Modify: `app/static/v2/index.html`, `app/static/v2/styles.css`

**Interfaces:**
- Consumes: `GET /api/v2/loan/{id}/pricing`, `POST /api/v2/loan/{id}/pricing/whatif`.
- Produces: registers `TABS.pricing`.

- [ ] **Step 1: Write `app/static/v2/tab-pricing.js`**

1. `waterfallTable(lines, ead)` — one row per line with dollars and bps, both from
   the response. Income positive, costs shown negative with a leading `−`. A rule
   above `pre_tax_profit` and above `net_income` so it reads as a waterfall.
2. `rateLadder(rates, verdict)` — a horizontal SVG axis with four labelled ticks
   (break-even, hurdle-clearing, recommended, quoted) and the quoted rate as a pin
   coloured by `verdict.clears_hurdle`. Shortfall annotated in bps from the response.
3. `sliders(market, quotedRate, onChange)` — nine range inputs: quoted rate, cost of
   funds, LGD, opex, capital ratio, tax, base margin, ROE hurdle, fee rate. Each
   shows its current value as text. All nine post together as one overrides body so
   the server always sees a complete picture. Debounce 120ms.
4. `TABS.pricing` — if the response is `null`, render *"This applicant was never
   funded, so there is nothing to price."* and stop. Otherwise draw verdict tiles
   (ROE at quoted, hurdle, clears yes/no, shortfall bps), the ladder, the waterfall,
   the sliders, and a book strip (`share_clears`, `mispriced_ead`) that updates with
   the market sliders.
5. A **Reset to book assumptions** button that clears every override and re-POSTs `{}`.

- [ ] **Step 2: Add the script tag**

```html
<script src="/static/v2/tab-pricing.js"></script>
```

- [ ] **Step 3: Verify in a real browser**

`make run`, go to `/v2`, `BIZ100002`, Pricing tab. Assert:

- all eight waterfall lines render, each with a dollars and a bps column
- `break-even < hurdle-clearing < recommended` reading left to right on the ladder
- dragging LGD up visibly lowers the book's share-clearing figure
- **Reset to book assumptions** returns ROE to the value `/api/pricing/BIZ100002` reports
- an unbooked applicant (pick one via the `booked = false` filter) shows the "never funded" message and no sliders

Screenshot. Console errors: zero.

- [ ] **Step 4: Run the Python tests and stop the server**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -q && make stop`

- [ ] **Step 5: Commit**

```bash
git add app/static/v2
git commit -m "v2: pricing tab -- full waterfall, rate ladder, live market sliders

Every waterfall line is shown in dollars and in bps on EAD, the way a banker reads
one. Market sliders re-price the loan and the whole booked book server-side.

Verified in a real browser: eight lines in both units; ladder ordered break-even <
hurdle-clearing < recommended; raising LGD lowers the book's share-clearing; reset
returns ROE to /api/pricing/<id>'s value; an unbooked applicant shows the 'never
funded' state instead of sliders; console clean.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 14: Early-warning tab UI — 24-month small multiples

**Files:**
- Create: `app/static/v2/tab-ews.js`
- Modify: `app/static/v2/index.html`, `app/static/v2/styles.css`

**Interfaces:**
- Consumes: `GET /api/v2/loan/{id}/ews`, `POST /api/v2/loan/{id}/ews/whatif`.
- Produces: registers `TABS.ews`. Uses `sparkline` and `axisWithHandles` from `svg.js`.

- [ ] **Step 1: Write `app/static/v2/tab-ews.js`**

1. Use `sparkline` from `svg.js` directly — it already takes `{threshold, label, format}`.
2. `smallMultiples(panel, triggers)` — five stacked sparklines: utilization (with
   the `HIGH_UTILIZATION` threshold as its dashed rule), balance, deposit inflow,
   days past due, overdraft count. Shared x-axis labelled `month 0 … 23` once at the
   bottom.
3. `triggerTable(rows)` — name / this account / comparator / threshold / status,
   same glyph convention as the decision tab.
4. `tierBar(prob, tiers, onChange)` — `axisWithHandles` again:

```javascript
function tierBar(prob, tiers, onChange) {
  return axisWithHandles({
    min: 0, max: 1, pin: prob, pinLabel: "p(deterioration)",
    bands: [{from: 0, to: tiers.t_med, fill: "var(--ok)"},
            {from: tiers.t_med, to: tiers.t_high, fill: "var(--warn)"},
            {from: tiers.t_high, to: 1, fill: "var(--bad)"}],
    handles: [{key: "t_med", value: tiers.t_med, label: "t_med"},
              {key: "t_high", value: tiers.t_high, label: "t_high"}],
  }, debounce(onChange, 120));
}
```
5. `TABS.ews` — null → *"This applicant was never funded, so there is no behaviour
   to monitor."* Otherwise: tier chip, probability, tier bar, small multiples,
   trigger table with draggable thresholds, SHAP drivers, and **the model caveat
   rendered as visible body text, not a tooltip** — capture 0.2159 held out, AUC
   0.6622 reported not gated, base rate 0.1802, plus the note from the response.
   Tier and trigger drags POST the what-if and update the tier chip, the trigger
   table and the book tier counts.

- [ ] **Step 2: Add the script tag**

```html
<script src="/static/v2/tab-ews.js"></script>
```

- [ ] **Step 3: Verify in a real browser**

`make run`, `/v2`, `BIZ100002`, Early Warning tab. Assert:

- five sparklines render, each with 24 points (check the polyline's `points`
  attribute has 24 pairs via `mcp__Claude_Browser__javascript_tool`)
- the caveat text `0.2159` and `reported, not gated` appear in the page text
- dragging `t_high` down raises the book's High count
- an unbooked applicant shows the "no behaviour to monitor" state

Screenshot. Console errors: zero.

- [ ] **Step 4: Run the Python tests and stop the server**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -q && make stop`

- [ ] **Step 5: Commit**

```bash
git add app/static/v2
git commit -m "v2: early-warning tab -- the account's real 24-month behaviour

Five inline-SVG sparklines over the actual panel, with the utilization trigger drawn
as a dashed rule on its own series. The model's limits are body text next to its
output, not a footnote: capture 0.2159 held out, AUC 0.6622 reported not gated.

Verified in a real browser: 24 points per series; the caveat numbers appear in page
text; lowering t_high raises the book's High count; unbooked shows the 'no behaviour
to monitor' state; console clean.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 15: Line-increase tab UI

**Files:**
- Create: `app/static/v2/tab-line-increase.js`
- Modify: `app/static/v2/index.html`, `app/static/v2/styles.css`

**Interfaces:**
- Consumes: `GET /api/v2/loan/{id}/line-increase`. Registers `TABS.line_increase`.

- [ ] **Step 1: Write `app/static/v2/tab-line-increase.js`**

1. An "optional module" ribbon at the top of the panel, so skipping it live reads as
   deliberate rather than broken.
2. `capsChart(caps)` — `hbars(caps)` from `svg.js` (it already fills the binding bar and appends `(binds)`), plus a caption naming the binding cap in words.
3. `clauseList(eligibility)` — the four clauses as rows: name, this loan's value,
   comparator, threshold, pass/fail glyph; then a footer line
   `eligible = clause₁ AND clause₂ AND clause₃ AND clause₄ → yes/no`, with the verdict
   taken from `eligibility.eligible` in the response.
4. The incremental waterfall table (dollars only — the incremental EAD is the scale,
   and ROE is EAD-invariant, which the caption should say).
5. A cohort strip from `cohort`: 95 offered, cohort PD 0.0363 vs book 0.1171,
   aggregate incremental ROE 0.2153 against the 0.15 hurdle.

- [ ] **Step 2: Add the script tag**

```html
<script src="/static/v2/tab-line-increase.js"></script>
```

- [ ] **Step 3: Verify in a real browser**

`make run`, `/v2`. Use the `li_eligible = true` filter (should read `95 matches`),
pick the first loan, Line Increase tab. Assert:

- three cap bars render with exactly one marked `binds`
- four clauses render, all four passing for an eligible loan
- filter `li_eligible = false` and pick a loan with a positive recommended amount:
  at least one clause fails while the amount is still positive — the documented trap,
  visible on screen
- an unbooked applicant shows a "never funded" state

Screenshot. Console errors: zero.

- [ ] **Step 4: Run the Python tests and stop the server**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_app_v2.py -q && make stop`

- [ ] **Step 5: Commit**

```bash
git add app/static/v2
git commit -m "v2: line-increase tab -- binding cap and eligibility as four clauses

Marked optional so it can be skipped live without leaving a hole. The four-clause
view puts the documented trap on screen: a positive recommended amount is not an
offer, and you can see which clause stopped it.

Verified in a real browser: the eligible filter reads 95 matches; exactly one cap
binds; an eligible loan passes all four clauses; a loan with a positive amount but
no offer shows which clause failed; console clean.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 16: verify.py smoke, Makefile, and documentation

**Files:**
- Modify: `verify.py` (inside `check_apps`), `Makefile`, `README.md`, `CLAUDE.md`

**Interfaces:** none — this task makes v2 discoverable and keeps the one promise intact at every stage tag.

- [ ] **Step 1: Add the guarded v2 smoke to `verify.py`**

Inside `check_apps`, within the existing `with TestClient(app) as client:` block,
after the stage>=4 section:

```python
            # v2 workbench lives on main only -- stage tags never move, so this block
            # is silent at stage-0..stage-5 and only runs where app/v2 exists.
            if (ROOT / "app" / "v2").exists():
                v2h = client.get("/api/v2/health").json()
                assert v2h["applicants"] == len(app.state.profiles), "v2 health wrong"
                first = client.get("/api/v2/loans?limit=1").json()["loans"][0]
                bid = first["business_id"]
                assert client.get(f"/api/v2/loan/{bid}").status_code == 200, \
                    "v2 loan header broken"
                wi = client.post(f"/api/v2/loan/{bid}/decision/whatif", json={}).json()
                batch = client.get(f"/api/adjudicate/{bid}").json()
                assert wi["decision"] == batch["decision"], \
                    "v2 what-if disagrees with the batch pipeline"
```

- [ ] **Step 2: Confirm the guard actually protects the tags**

Run on `main`:
```bash
PYTHONPATH=. .venv/bin/python verify.py | tail -2
```
Expected: passes, same as before.

Then prove the guard holds where `app/v2` is absent, in a clean clone at a tag —
a worktree is not good enough, it carries `main`'s files:

Clone the **main repository path**, not this worktree: a worktree's `.git` is a file
and its HEAD is the feature branch, so `git clone .` here would sweep the wrong tree
and leave the stage-tag guarantee unverified.

```bash
rm -rf /tmp/v2sweep
git clone "$(git rev-parse --path-format=absolute --git-common-dir | sed 's;/\.git$;;')" /tmp/v2sweep
cd /tmp/v2sweep
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
for t in stage-3 stage-4 stage-5; do
  git checkout -q $t && echo -n "$t: " && .venv/bin/python verify.py | tail -1
done
git checkout -q main && echo -n "main: " && .venv/bin/python verify.py | tail -1
```

Expected: every line reports the same result it did before this work. If any tag
regresses, the guard is wrong — fix it before continuing.

- [ ] **Step 3: Point `make run` at both portals**

`make run` already serves both — v2 needs no second server and no second target. It
needs a banner, so nobody hunts for the URL mid-demo. Replace the `run` recipe body
(leave `run: stop` and its comment alone):

```make
run: stop
	@echo "v1 portal → http://localhost:8100/     v2 workbench → http://localhost:8100/v2"
	$(PY) -m uvicorn app.main:app --port 8100
```

- [ ] **Step 4: Document it in `README.md`**

Add to whichever section lists what `make run` gives you:

```markdown
`make run` serves two front ends on port 8100:

- **`/`** — the v1 portal: one number per module, portfolio-level.
- **`/v2`** — the Loan Workbench: pick one loan, then see its decision (with every
  policy rule and both model rationales), its pricing waterfall, and its 24-month
  behavioural history. Every parameter on screen is a live control; moving one
  recomputes through the same module function the batch pipeline calls.

Both are running the same models on the same data. Open them side by side.
```

- [ ] **Step 5: Add the gotchas to `CLAUDE.md`**

Under **Gotchas discovered the hard way**:

```markdown
- **`app/v2/` is main-only, like `notebooks/` and `workshop/`.** A stage jump deletes
  it. `verify.py`'s v2 smoke is guarded on `(ROOT/"app"/"v2").exists()` so every tag
  is unaffected — verified in a clean clone at stage-3/4/5. The S3 handoff command is
  `git checkout main -- app notebooks workshop`.
- **v2's what-if must equal the batch pipeline.** Every slider calls the same module
  function the batch run calls; `tests/test_app_v2.py` asserts that an empty override
  body reproduces `/api/adjudicate`, `/api/pricing/<id>` and `/api/ews/<id>` exactly,
  over 25 loans each. If that test fails, the demo is lying — fix the drift, never the
  test.
- **No financial arithmetic in the v2 JavaScript.** Every number on screen came from a
  server response. A threshold comparison done in JS is a bug even when it agrees.
```

Under **Where things stand**, note that Sessions 3 and 4 are merging into one new
Session 3 (adjudication + pricing + early warning, line increase optional) and that
v2 is the demo artifact for it.

- [ ] **Step 6: Full verification sweep**

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q tests
PYTHONPATH=. .venv/bin/python verify.py | tail -2
git diff --stat $(git merge-base main HEAD) HEAD -- app/main.py
```

Expected: all tests pass; `verify.py` reports `Stage 5 verified` exactly as the
pre-v2 baseline did; `app/main.py` shows 4 insertions and 0 deletions **across the
whole branch**. The explicit merge-base range matters: bare `git diff` compares the
working tree to the index and prints nothing once the work is committed, so it would
pass however badly v1 had been mangled.

- [ ] **Step 7: Commit**

```bash
git add verify.py Makefile README.md CLAUDE.md
git commit -m "v2: guarded verify smoke, run banner, and the docs that keep it honest

The v2 smoke asserts the what-if agrees with the batch pipeline, and is guarded on
app/v2 existing so stage-0..stage-5 are untouched -- verified in a clean clone at
stage-3, stage-4 and stage-5, not a worktree.

Verified: full pytest suite passes; verify.py matches its pre-v2 result on main and
at every tag; app/main.py diff across the whole branch is 4 insertions 0 deletions.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Deferred to the curriculum work (not this plan)

These follow from v2 but belong to the session rewrite, not the build:

- Stubbing Tab 3 (Early Warning) as the S3 lab exercise, with the shell shipped and
  the tab's render function left as a documented stub.
- The prompt that produced v2, preserved verbatim in `workshop/prompt-cards/`.
- Updating every printed stage-jump command to `git checkout main -- app notebooks workshop`.
- S3 run of show, deck, notebook and lab sheet for the merged session.
