"""Feature engineering for Loan Adjudication.

Application fields + affordability ratios + the *modeled* business_score / pd reused
from Module 0 (decision-time signals, not leakage). Categorical features use pandas
'category' dtype for LightGBM. Guaranteed leakage-free against shared LEAKAGE_COLUMNS.
"""
import numpy as np
import pandas as pd

from shared.config import LEAKAGE_COLUMNS
from score.src.predict import predict_score_pd

ADJ_CATEGORICAL = ["industry", "entity_type", "loan_purpose"]

ADJ_FEATURE_COLUMNS = [
    # application / firmographic
    "years_in_business", "employees", "annual_revenue", "requested_amount",
    "term_months", "collateral_flag",
    # affordability / financial ratios
    "dscr", "leverage", "current_ratio", "debt_to_income", "utilization", "profit_margin",
    # bureau-like
    "credit_history_months", "prior_delinquencies", "trade_lines", "public_records",
    # reused modeled signals from Module 0
    "business_score", "pd_score",
    # categorical (kept last)
    "industry", "entity_type", "loan_purpose",
]


def compute_adjudication_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # derived ratios (same formulas as the scorecard's feature engineering)
    out["debt_to_income"] = (
        out["total_debt"] / np.maximum(out["net_income"].abs(), 1.0)
    ).clip(0, 50).round(3)
    out["profit_margin"] = (
        out["net_income"] / np.maximum(out["annual_revenue"], 1.0)
    ).clip(-1, 1).round(4)

    # reuse modeled score/PD from Module 0
    sp = predict_score_pd(df)
    out["business_score"] = sp["business_score"].to_numpy()
    out["pd_score"] = sp["pd"].to_numpy()
    out["score_band"] = sp["score_band"].to_numpy()  # kept for the policy layer (not a model feature)

    # dtypes
    for c in ADJ_FEATURE_COLUMNS:
        if c in ADJ_CATEGORICAL:
            out[c] = out[c].astype("category")
        else:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    leaked = [c for c in ADJ_FEATURE_COLUMNS if c in LEAKAGE_COLUMNS]
    if leaked:
        raise ValueError(f"Leakage columns in feature set: {leaked}")
    return out
