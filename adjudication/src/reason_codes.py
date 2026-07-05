"""Adjudication reason codes: top adverse SHAP contributions (features pushing PD up)
combined with policy rule hits into one explanation object per applicant."""
import numpy as np
import pandas as pd


def top_adverse_shap(shap_values, feature_names, k: int = 3):
    """Per-row list of the top-k features with the largest positive SHAP value
    (largest push toward default). Non-positive contributions are dropped."""
    arr = np.asarray(shap_values, dtype=float)
    names = np.asarray(feature_names, dtype=object)
    out = []
    for i in range(arr.shape[0]):
        order = np.argsort(arr[i])[::-1][:k]
        out.append([
            {"feature": str(names[j]), "impact": round(float(arr[i, j]), 4)}
            for j in order if arr[i, j] > 0
        ])
    return out


def explain(decision_df: pd.DataFrame, shap_reasons: list) -> list:
    """Combine the policy decision frame with SHAP reasons into per-applicant dicts."""
    records = []
    for pos, (_, row) in enumerate(decision_df.iterrows()):
        records.append({
            "decision": row["decision"],
            "pd": round(float(row["pd"]), 4),
            "rule_hits": list(row["decision_reasons"]),
            "top_shap_reasons": shap_reasons[pos] if pos < len(shap_reasons) else [],
        })
    return records
