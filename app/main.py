"""Workshop decision apps — one FastAPI service, stage-3 checkpoint.

Reference-build pattern: a lifespan hook scores the whole population ONCE at
startup and caches it in app.state; routes are cache lookups, never re-scoring.
Frontend is a no-build static page (app/static) — students never need Node.

Run:  make run   →  http://localhost:8100
"""
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import json
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from shared.config import RAW
from score.src.predict import predict_score_pd
from adjudication.src.feature_engineering import (
    ADJ_FEATURE_COLUMNS, compute_adjudication_features,
)
from adjudication.src.policy import PolicyConfig, decide
from pricing.src.portfolio import price_population, portfolio_summary

ROOT = Path(__file__).resolve().parent.parent
ADJ_MODELS = ROOT / "adjudication" / "models"


@asynccontextmanager
async def lifespan(app: FastAPI):
    biz = pd.read_parquet(RAW / "businesses.parquet")

    # score spine for everyone
    sp = predict_score_pd(biz)

    # adjudication decisions for everyone
    model = joblib.load(ADJ_MODELS / "adjudication_model.pkl")
    config = PolicyConfig.from_dict(
        json.loads((ADJ_MODELS / "policy_config.json").read_text()))
    X_all = compute_adjudication_features(biz)
    pd_hat = model.predict_proba(X_all[ADJ_FEATURE_COLUMNS])[:, 1]
    decisions = decide(X_all, pd_hat, config)

    # priced book + summary
    priced = price_population().set_index("business_id")

    profiles = biz.set_index("business_id")
    app.state.scores = sp.set_axis(profiles.index, axis=0)
    app.state.decisions = decisions.set_axis(profiles.index, axis=0)
    app.state.profiles = profiles
    app.state.priced = priced
    app.state.pricing_summary = portfolio_summary(priced.reset_index())
    yield


app = FastAPI(title="Banking Analytics Workshop — decision apps", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "stage": "3",
            "applicants": int(len(app.state.profiles)),
            "booked_priced": int(len(app.state.priced))}


@app.get("/api/examples")
def examples():
    """A few interesting IDs for the lookup box, one per decision/band mix."""
    d = app.state.decisions
    out = []
    for decision in ["Approve", "Refer", "Decline"]:
        ids = d.index[d["decision"] == decision][:3]
        out += [{"business_id": i, "hint": decision} for i in ids]
    return out


@app.get("/api/score/{business_id}")
def score(business_id: str):
    try:
        s = app.state.scores.loc[business_id]
    except KeyError:
        raise HTTPException(404, f"unknown business_id {business_id}")
    return {"business_id": business_id, "business_score": int(s["business_score"]),
            "pd": round(float(s["pd"]), 4), "score_band": s["score_band"]}


@app.get("/api/adjudicate/{business_id}")
def adjudicate(business_id: str):
    try:
        d = app.state.decisions.loc[business_id]
        p = app.state.profiles.loc[business_id]
        s = app.state.scores.loc[business_id]
    except KeyError:
        raise HTTPException(404, f"unknown business_id {business_id}")
    return {
        "business_id": business_id,
        "decision": d["decision"],
        "rule_hits": list(d["decision_reasons"]),
        "pd_model": round(float(d["pd"]), 4),
        "business_score": int(s["business_score"]),
        "score_band": s["score_band"],
        "requested_amount": float(p["requested_amount"]),
        "industry": p["industry"],
    }


@app.get("/api/pricing/summary")
def pricing_summary():
    return app.state.pricing_summary


@app.get("/api/pricing/{business_id}")
def pricing_row(business_id: str):
    try:
        r = app.state.priced.loc[business_id]
    except KeyError:
        raise HTTPException(404, f"{business_id} is not in the booked/priced book")
    return {"business_id": business_id,
            **{k: (float(v) if hasattr(v, "item") or isinstance(v, (int, float)) else v)
               for k, v in r.items()}}


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
