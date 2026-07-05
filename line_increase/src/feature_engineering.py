"""Feature engineering for Proactive Line Increase.

On-book behavioral/capacity features from portfolio.parquet + firmographic/financial
fields + the *modeled* PD reused from Module 0 (never pd_default_origination). Categorical
features use pandas 'category' dtype for LightGBM. Guaranteed leakage-free against the
shared LEAKAGE_COLUMNS (which includes the target line_increase_good)."""
import numpy as np
import pandas as pd

from shared.config import LEAKAGE_COLUMNS
from score.src.predict import predict_score_pd

LI_CATEGORICAL = ["industry", "entity_type", "loan_purpose"]

LI_FEATURE_COLUMNS = [
    # on-book behavioral / capacity
    "utilization_onbook", "util_headroom", "credit_limit", "current_balance", "tenure_months",
    # firmographic / capacity
    "years_in_business", "employees", "annual_revenue", "log_revenue",
    # financial ratios
    "dscr", "leverage", "current_ratio",
    # bureau-like
    "credit_history_months", "prior_delinquencies", "trade_lines", "public_records",
    # reused modeled signal from Module 0
    "pd_score",
    # categorical (kept last)
    "industry", "entity_type", "loan_purpose",
]


def compute_line_increase_features(df: pd.DataFrame) -> pd.DataFrame:
    """df = portfolio.parquet rows. Returns a frame carrying LI_FEATURE_COLUMNS plus
    business_id / score_band / pd_score for the service & segments (non-feature)."""
    out = df.copy()
    out["util_headroom"] = (1.0 - out["utilization_onbook"]).clip(lower=0.0).round(4)
    out["log_revenue"] = np.log(np.maximum(out["annual_revenue"], 1.0)).round(4)

    sp = predict_score_pd(df)
    out["pd_score"] = sp["pd"].to_numpy()
    out["business_score"] = sp["business_score"].to_numpy()
    out["score_band"] = sp["score_band"].to_numpy()  # for segments/UI, not a model feature

    for c in LI_FEATURE_COLUMNS:
        if c in LI_CATEGORICAL:
            out[c] = out[c].astype("category")
        else:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    leaked = [c for c in LI_FEATURE_COLUMNS if c in LEAKAGE_COLUMNS]
    if leaked:
        raise ValueError(f"Leakage columns in feature set: {leaked}")
    return out
