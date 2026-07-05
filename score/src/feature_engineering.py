"""Feature engineering for the Business Credit Score scorecard.

Mix of raw and derived ratios. Categorical features are kept as strings;
optbinning's BinningProcess handles WoE encoding for both numeric and categorical.
"""
import numpy as np
import pandas as pd

# Shared with the trainer and the API in later phases.
FEATURE_COLUMNS = [
    # numeric
    "years_in_business", "annual_revenue", "dscr", "current_ratio", "leverage",
    "utilization", "credit_history_months", "prior_delinquencies", "trade_lines",
    "public_records", "debt_to_income", "revenue_per_employee", "profit_margin",
    # categorical
    "industry", "entity_type",
]

CATEGORICAL = ["industry", "entity_type"]


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["debt_to_income"] = (out["total_debt"] / np.maximum(out["net_income"].abs(), 1.0)).clip(0, 50).round(3)
    out["revenue_per_employee"] = (out["annual_revenue"] / np.maximum(out["employees"], 1)).round(0)
    out["profit_margin"] = (out["net_income"] / np.maximum(out["annual_revenue"], 1.0)).clip(-1, 1).round(4)
    for c in FEATURE_COLUMNS:
        if c not in CATEGORICAL:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)
        else:
            out[c] = out[c].astype(str)
    return out
