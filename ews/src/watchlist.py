"""EWS risk tiers + scored population + watchlist. Reuses the trained model, features,
triggers, and adverse-SHAP reason codes."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from shared.config import RAW
from ews.src.feature_engineering import EWS_FEATURE_COLUMNS, compute_ews_features
from ews.src.triggers import flag_triggers
from adjudication.src.reason_codes import top_adverse_shap

MODELS = Path("ews/models")
KEY_METRICS = ["util_recent", "util_drift", "dpd_max", "deposit_decline_pct", "overdraft_recent"]


def _load():
    model = joblib.load(MODELS / "ews_model.pkl")
    meta = json.loads((MODELS / "metadata.json").read_text())
    return model, meta


def risk_tier(prob, tiers: dict) -> str:
    if prob >= tiers["t_high"]:
        return "High"
    if prob >= tiers["t_med"]:
        return "Medium"
    return "Low"


def score_population() -> pd.DataFrame:
    model, meta = _load()
    tiers = meta["tiers"]
    port = pd.read_parquet(RAW / "portfolio.parquet")
    feats = compute_ews_features(port)
    X = feats[EWS_FEATURE_COLUMNS]
    prob = model.predict_proba(X)[:, 1]
    triggers = flag_triggers(feats)
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X)
    sv = sv[1] if isinstance(sv, list) else sv
    shap_reasons = top_adverse_shap(sv, EWS_FEATURE_COLUMNS, k=3)

    out = pd.DataFrame({
        "business_id": port["business_id"].astype(str).to_numpy(),
        "industry": port["industry"].to_numpy(),
        "score_band": feats["score_band"].astype(str).to_numpy(),
        "tenure_months": feats["tenure_months"].astype(float).to_numpy(),
        "prob": np.round(prob, 4),
        "risk_tier": [risk_tier(p, tiers) for p in prob],
        "triggers": triggers,
        "top_shap_reasons": shap_reasons,
    })
    for c in KEY_METRICS:
        out[c] = feats[c].astype(float).round(4).to_numpy()
    out.index = out["business_id"]
    return out


def watchlist(df: pd.DataFrame, top_n: int = 100) -> list[dict]:
    ranked = df.sort_values("prob", ascending=False).head(top_n)
    return [{"business_id": r["business_id"], "industry": r["industry"],
             "prob": float(r["prob"]), "risk_tier": r["risk_tier"],
             "triggers": list(r["triggers"])} for _, r in ranked.iterrows()]
