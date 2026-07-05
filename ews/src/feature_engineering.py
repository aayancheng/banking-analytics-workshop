"""EWS feature engineering: aggregate the 24-month behavioral panel into per-account
trend features, then join modeled score/PD + on-book/firmographic columns. Leakage-safe."""
from functools import lru_cache

import pandas as pd

from shared.config import RAW, LEAKAGE_COLUMNS
from score.src.predict import predict_score_pd

EWS_CATEGORICAL = ["industry", "entity_type"]

PANEL_FEATURES = [
    "util_recent", "balance_recent", "deposit_recent",
    "util_drift", "deposit_decline_pct", "balance_trend", "util_volatility",
    "dpd_months", "dpd_max", "dpd_recent", "overdraft_total", "overdraft_recent",
]

EWS_FEATURE_COLUMNS = [
    *PANEL_FEATURES,
    "utilization_onbook", "current_balance", "credit_limit", "tenure_months",
    "dscr", "leverage", "current_ratio", "prior_delinquencies",
    "business_score", "pd_score",
    "industry", "entity_type",
]


def _agg_one(df: pd.DataFrame) -> pd.Series:
    df = df.sort_values("month_index")
    last3, first6, last6 = df.tail(3), df.head(6), df.tail(6)
    first6_dep = max(float(first6["deposit_inflow"].mean()), 1.0)
    return pd.Series({
        "util_recent": float(last3["utilization"].mean()),
        "balance_recent": float(last3["balance"].mean()),
        "deposit_recent": float(last3["deposit_inflow"].mean()),
        "util_drift": float(last6["utilization"].mean() - first6["utilization"].mean()),
        "deposit_decline_pct": float((first6_dep - last6["deposit_inflow"].mean()) / first6_dep),
        "balance_trend": float(last6["balance"].mean() - first6["balance"].mean()),
        "util_volatility": float(df["utilization"].std(ddof=0)),
        "dpd_months": int((df["days_past_due"] > 0).sum()),
        "dpd_max": float(df["days_past_due"].max()),
        "dpd_recent": float(last3["days_past_due"].max()),
        "overdraft_total": float(df["overdraft_count"].sum()),
        "overdraft_recent": float(last6["overdraft_count"].sum()),
    })


def compute_panel_features(panel: pd.DataFrame) -> pd.DataFrame:
    cols = ["business_id", "month_index", "utilization", "balance",
            "deposit_inflow", "days_past_due", "overdraft_count"]
    pf = (panel[cols].groupby("business_id", sort=True)
          .apply(_agg_one, include_groups=False).reset_index())
    return pf


@lru_cache(maxsize=1)
def _cached_panel_features() -> pd.DataFrame:
    """panel.parquet is static; the groupby is the hot path (~30s+). Prefer the
    committed cache written by train.py — verify.py and the app must stay fast.
    Editing the cache doesn't help anyone: predictions shift and gates fail."""
    from shared.config import ROOT
    cache = ROOT / "ews" / "models" / "panel_features.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    return compute_panel_features(pd.read_parquet(RAW / "panel.parquet"))


def compute_ews_features(portfolio: pd.DataFrame) -> pd.DataFrame:
    pf = _cached_panel_features()
    out = portfolio.merge(pf, on="business_id", how="left")

    sp = predict_score_pd(out)
    out["business_score"] = sp["business_score"].to_numpy()
    out["pd_score"] = sp["pd"].to_numpy()
    out["score_band"] = sp["score_band"].to_numpy()  # kept for segments (not a model feature)

    for c in EWS_FEATURE_COLUMNS:
        if c in EWS_CATEGORICAL:
            out[c] = out[c].astype("category")
        else:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    leaked = [c for c in EWS_FEATURE_COLUMNS if c in LEAKAGE_COLUMNS]
    if leaked:
        raise ValueError(f"Leakage columns in EWS features: {leaked}")
    return out
