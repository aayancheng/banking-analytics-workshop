"""Scored line-increase population: candidate probability + recommended amount +
incremental-ROE result + positive SHAP reason codes per account, plus the ranked
candidates list and segment rollups. Reuses the trained model, features, amount rules,
pricing engine, and the shared top-positive SHAP helper."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from shared.config import RAW, MARKET
from line_increase.src.feature_engineering import (
    LI_FEATURE_COLUMNS, compute_line_increase_features,
)
from line_increase.src.amount_rules import recommended_amount, incremental_roe
from pricing.src.engine import MarketAssumptions
from adjudication.src.reason_codes import top_adverse_shap

MODELS = Path("line_increase/models")
_MARKET = MarketAssumptions.from_market(MARKET)


def _load():
    model = joblib.load(MODELS / "line_increase_model.pkl")
    meta = json.loads((MODELS / "metadata.json").read_text())
    return model, meta


def score_population() -> pd.DataFrame:
    model, meta = _load()
    threshold = meta["offer_threshold"]
    max_pd = meta["offer_max_pd"]  # risk-appetite ceiling (book-median modeled PD)
    port = pd.read_parquet(RAW / "portfolio.parquet")
    feats = compute_line_increase_features(port)
    X = feats[LI_FEATURE_COLUMNS]
    prob = model.predict_proba(X)[:, 1]

    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X)
    sv = sv[1] if isinstance(sv, list) else sv
    reasons = top_adverse_shap(sv, LI_FEATURE_COLUMNS, k=3)

    recs = []
    for i in range(len(port)):
        pd_i = float(feats["pd_score"].iloc[i])
        rate_i = float(port["risk_based_rate"].iloc[i])
        amt = recommended_amount(float(port["current_balance"].iloc[i]),
                                 float(port["credit_limit"].iloc[i]),
                                 float(port["annual_revenue"].iloc[i]))
        r = incremental_roe(pd_i, amt, float(port["utilization_onbook"].iloc[i]),
                            rate_i, _MARKET)
        eligible = bool(prob[i] >= threshold and pd_i <= max_pd
                        and amt > 0 and r["clears_hurdle"])
        recs.append({
            "business_id": str(port["business_id"].iloc[i]),
            "industry": str(port["industry"].iloc[i]),
            "score_band": str(feats["score_band"].iloc[i]),
            "pd": round(pd_i, 4),
            "rate": rate_i,
            "prob": round(float(prob[i]), 4),
            "credit_limit": float(port["credit_limit"].iloc[i]),
            "current_balance": float(port["current_balance"].iloc[i]),
            "utilization_onbook": float(port["utilization_onbook"].iloc[i]),
            "recommended_amount": amt,
            "incremental_ead": round(r["incremental_ead"], 2),
            "incremental_roe": round(r["roe"], 4),
            "incremental_net_income": round(r["incremental_net_income"], 2),
            "clears_hurdle": r["clears_hurdle"],
            "eligible": eligible,
            "top_shap_reasons": reasons[i],
        })
    out = pd.DataFrame(recs)
    out.index = out["business_id"]
    return out


def candidates(df: pd.DataFrame, top_n: int | None = None) -> list[dict]:
    ranked = df[df["eligible"]].sort_values("prob", ascending=False)
    if top_n is not None:
        ranked = ranked.head(top_n)
    return [{"business_id": r["business_id"], "industry": r["industry"],
             "score_band": r["score_band"], "prob": float(r["prob"]),
             "recommended_amount": float(r["recommended_amount"]),
             "incremental_ead": float(r["incremental_ead"]),
             "incremental_roe": float(r["incremental_roe"]),
             "clears_hurdle": bool(r["clears_hurdle"])}
            for _, r in ranked.iterrows()]


def segments(df: pd.DataFrame) -> dict:
    def seg(col):
        rows = []
        for key, g in df.groupby(col):
            rows.append({
                "key": str(key),
                "offer_rate": round(float(g["eligible"].mean()), 4),
                "expected_incremental_exposure": round(
                    float(g.loc[g["eligible"], "incremental_ead"].sum()), 2),
                "count": int(len(g)),
            })
        return sorted(rows, key=lambda r: r["key"])
    return {"by_band": seg("score_band"), "by_industry": seg("industry")}
