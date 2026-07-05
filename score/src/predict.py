"""Reusable Business Credit Score inference: load the saved scorecard and produce
business_score (300-850), pd, and score_band for any applicant DataFrame.

Used by downstream modules (e.g. Adjudication) so they consume the *modeled* score/PD,
never the DGP ground truth (pd_default_origination).
"""
import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from score.src.feature_engineering import FEATURE_COLUMNS, compute_features
from score.src.train import score_to_fico

MODELS = Path("score/models")
_BANDS_BINS = [300, 580, 640, 700, 750, 850]
_BANDS_LABELS = ["D", "C", "B", "A", "AAA"]


@lru_cache(maxsize=1)
def _load():
    scorecard = joblib.load(MODELS / "scorecard.pkl")
    scaling = json.loads((MODELS / "score_scaling.json").read_text())
    return scorecard, scaling["lo"], scaling["hi"]


def predict_score_pd(df: pd.DataFrame) -> pd.DataFrame:
    """Return DataFrame[business_score, pd, score_band] aligned to df.index."""
    scorecard, lo, hi = _load()
    X = compute_features(df)[FEATURE_COLUMNS]
    # The optbinning WoE matmul can emit cosmetic over/divide/invalid warnings on
    # extreme feature values; correctness is unaffected, so guard the scoring calls.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        pd_hat = scorecard.predict_proba(X)[:, 1]
        fico = score_to_fico(scorecard.score(X), lo, hi)
    band = pd.cut(fico, bins=_BANDS_BINS, labels=_BANDS_LABELS, include_lowest=True)
    return pd.DataFrame(
        {
            "business_score": np.asarray(fico, dtype=int),
            "pd": np.clip(pd_hat, 0.0, 1.0),
            "score_band": band.astype(str),
        },
        index=df.index,
    )
