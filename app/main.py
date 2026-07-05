"""Workshop decision platform — one FastAPI service, all modules (stage-4+).

Reference-build pattern: a lifespan hook scores each module's population ONCE at
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
from ews.src import watchlist as ews_watchlist
from line_increase.src import candidates as li_candidates

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

    # early-warning watchlist + line-increase candidates (booked subset)
    ews_pop = ews_watchlist.score_population()
    li_pop = li_candidates.score_population()

    profiles = biz.set_index("business_id")
    app.state.scores = sp.set_axis(profiles.index, axis=0)
    app.state.decisions = decisions.set_axis(profiles.index, axis=0)
    app.state.profiles = profiles
    app.state.priced = priced
    app.state.pricing_summary = portfolio_summary(priced.reset_index())
    app.state.ews = ews_pop
    app.state.li = li_pop
    app.state.li_meta = json.loads(
        (ROOT / "line_increase" / "models" / "metadata.json").read_text())
    app.state.ews_meta = json.loads(
        (ROOT / "ews" / "models" / "metadata.json").read_text())
    yield


app = FastAPI(title="Banking Analytics Workshop — decision platform", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "stage": "4+",
            "applicants": int(len(app.state.profiles)),
            "booked_priced": int(len(app.state.priced)),
            "ews_scored": int(len(app.state.ews)),
            "li_scored": int(len(app.state.li))}


@app.get("/api/examples")
def examples():
    """Interesting IDs for the lookup boxes: one per decision, plus EWS High and an
    eligible line-increase candidate."""
    d = app.state.decisions
    out = []
    for decision in ["Approve", "Refer", "Decline"]:
        ids = d.index[d["decision"] == decision][:2]
        out += [{"business_id": i, "hint": decision} for i in ids]
    high = app.state.ews[app.state.ews["risk_tier"] == "High"]["business_id"].head(2)
    out += [{"business_id": i, "hint": "EWS High"} for i in high]
    elig = app.state.li[app.state.li["eligible"]]["business_id"].head(2)
    out += [{"business_id": i, "hint": "LI candidate"} for i in elig]
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


@app.get("/api/ews/summary")
def ews_summary():
    df = app.state.ews
    tiers = df["risk_tier"].value_counts().to_dict()
    trig = {}
    for lst in df["triggers"]:
        for t in lst:
            trig[t] = trig.get(t, 0) + 1
    return {"n": int(len(df)), "tiers": {k: int(v) for k, v in tiers.items()},
            "trigger_counts": dict(sorted(trig.items(), key=lambda kv: -kv[1])),
            "base_rate": app.state.ews_meta["base_rate"],
            "metrics": app.state.ews_meta["metrics"]}


@app.get("/api/ews/watchlist")
def ews_watchlist_endpoint(n: int = 25):
    return ews_watchlist.watchlist(app.state.ews, top_n=n)


@app.get("/api/ews/{business_id}")
def ews_row(business_id: str):
    try:
        r = app.state.ews.loc[business_id]
    except KeyError:
        raise HTTPException(404, f"{business_id} is not on the monitored book")
    return {"business_id": business_id, "prob": float(r["prob"]),
            "risk_tier": r["risk_tier"], "triggers": list(r["triggers"]),
            "top_shap_reasons": list(r["top_shap_reasons"]),
            "util_recent": float(r["util_recent"]), "util_drift": float(r["util_drift"]),
            "dpd_max": float(r["dpd_max"])}


@app.get("/api/line-increase/summary")
def li_summary():
    return {"cohort": app.state.li_meta["cohort"],
            "metrics": app.state.li_meta["metrics"],
            "offer_threshold": app.state.li_meta["offer_threshold"],
            "segments": li_candidates.segments(app.state.li)}


@app.get("/api/line-increase/candidates")
def li_candidates_endpoint(n: int = 25):
    return li_candidates.candidates(app.state.li, top_n=n)


@app.get("/api/line-increase/{business_id}")
def li_row(business_id: str):
    try:
        r = app.state.li.loc[business_id]
    except KeyError:
        raise HTTPException(404, f"{business_id} is not on the book")
    return {"business_id": business_id, "prob": float(r["prob"]),
            "eligible": bool(r["eligible"]),
            "recommended_amount": float(r["recommended_amount"]),
            "incremental_roe": float(r["incremental_roe"]),
            "clears_hurdle": bool(r["clears_hurdle"])}


@app.get("/api/dashboard/summary")
def dashboard():
    """One KPI per module — the S4 portal view."""
    d = app.state.decisions["decision"].value_counts(normalize=True).round(4).to_dict()
    ps = app.state.pricing_summary
    ews_high = int((app.state.ews["risk_tier"] == "High").sum())
    li = app.state.li_meta["cohort"]
    return {
        "score": {"applicants": int(len(app.state.profiles)),
                  "mean_score": int(app.state.scores["business_score"].mean())},
        "adjudication": {"mix": d},
        "pricing": {"share_clears": ps["share_clears"], "mispriced_ead": ps["mispriced_ead"]},
        "ews": {"high_risk": ews_high, "monitored": int(len(app.state.ews))},
        "line_increase": {"offered": li["n_offered"],
                          "agg_incremental_roe": li["agg_incremental_roe"]},
    }


@app.get("/api/customer/{business_id}")
def customer_360(business_id: str):
    """Everything the platform knows about one business. Non-booked applicants
    return null for the on-book modules — that's correct, not a bug."""
    try:
        p = app.state.profiles.loc[business_id]
    except KeyError:
        raise HTTPException(404, f"unknown business_id {business_id}")
    s = app.state.scores.loc[business_id]
    d = app.state.decisions.loc[business_id]
    booked = business_id in app.state.priced.index
    modules = ["score", "adjudication"] + (
        ["pricing", "ews", "line_increase"] if booked else [])
    out = {
        "business_id": business_id,
        "profile": {"industry": p["industry"], "region": p["region"],
                    "entity_type": p["entity_type"],
                    "annual_revenue": float(p["annual_revenue"]),
                    "years_in_business": float(p["years_in_business"])},
        "modules_present": modules,
        "score": {"business_score": int(s["business_score"]),
                  "pd": round(float(s["pd"]), 4), "score_band": s["score_band"]},
        "adjudication": {"decision": d["decision"], "rule_hits": list(d["decision_reasons"])},
        "pricing": None, "ews": None, "line_increase": None,
    }
    if booked:
        r = app.state.priced.loc[business_id]
        out["pricing"] = {"roe_at_quoted": float(r["roe_at_quoted"]),
                          "clears_hurdle": bool(r["clears_hurdle"]),
                          "recommended_rate": float(r["recommended_rate"])}
        e = app.state.ews.loc[business_id]
        out["ews"] = {"risk_tier": e["risk_tier"], "prob": float(e["prob"]),
                      "triggers": list(e["triggers"])}
        li = app.state.li.loc[business_id]
        out["line_increase"] = {"eligible": bool(li["eligible"]),
                                "recommended_amount": float(li["recommended_amount"]),
                                "incremental_roe": float(li["incremental_roe"])}
    return out


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
