"""Adverse reason codes for the WoE+Logistic scorecard.

For a linear-in-WoE model, each feature's contribution to the log-odds of default
is exactly WoE(feature) * coefficient(feature). The features with the largest
positive contribution (pushing PD up) are the adverse reason codes.
"""
import numpy as np
import pandas as pd


def feature_contributions(scorecard, X: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame (rows aligned to X) of per-feature logit contributions."""
    bp = scorecard.binning_process_
    woe = bp.transform(X, metric="woe")           # DataFrame of WoE values
    coef = scorecard.estimator_.coef_[0]          # one coef per binned feature
    names = list(woe.columns)
    contrib = woe.to_numpy() * coef
    return pd.DataFrame(contrib, columns=names, index=X.index)


def top_reason_codes(scorecard, X: pd.DataFrame, k: int = 3):
    """List (per row) of the top-k features increasing default risk."""
    contrib = feature_contributions(scorecard, X)
    reasons = []
    cols = np.array(contrib.columns)
    arr = contrib.to_numpy()
    for i in range(arr.shape[0]):
        order = np.argsort(arr[i])[::-1][:k]      # largest positive contributions
        reasons.append([{"feature": str(cols[j]), "impact": round(float(arr[i, j]), 4)}
                        for j in order if arr[i, j] > 0])
    return reasons
