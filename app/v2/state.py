"""v2 workbench state: the extra objects loan-level explanation needs, built once.

v1's app.state already holds the scored populations, and v2 reuses them rather than
re-scoring. v2 adds only what per-loan explanation needs: the scorecard object (for
the WoE x beta ledger), a SHAP explainer over the adjudication model, the feature
matrices to index into, and the 24-month behavioural panel.

Nothing is precomputed across the population — a per-loan explanation is 2-3ms, so
precomputing 12,000 of them would cost seconds of boot to save nothing. Measured
cost of this build: ~0.15s on top of v1's 7.4s.

adj_X is recomputed here rather than shared out of v1's lifespan. It costs 0.05s and
it keeps app/main.py at four added statements, which is the point of v2 being a
side-by-side demo rather than a rewrite.
"""
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
import shap

from shared.config import RAW
from score.src.feature_engineering import FEATURE_COLUMNS, compute_features
from adjudication.src.feature_engineering import (
    ADJ_FEATURE_COLUMNS, compute_adjudication_features,
)
from app.v2 import loans

ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class V2State:
    scorecard: object
    score_X: pd.DataFrame
    adj_X: pd.DataFrame
    adj_explainer: object
    panel: pd.DataFrame
    index: pd.DataFrame


def build_state(app_state) -> V2State:
    """app_state is the FastAPI app.state, after v1's lifespan has populated it."""
    profiles = app_state.profiles
    scorecard = joblib.load(ROOT / "score" / "models" / "scorecard.pkl")
    score_X = compute_features(profiles)[FEATURE_COLUMNS]
    adj_X = compute_adjudication_features(profiles)[ADJ_FEATURE_COLUMNS]
    adj_model = joblib.load(ROOT / "adjudication" / "models" / "adjudication_model.pkl")
    adj_explainer = shap.TreeExplainer(adj_model)
    panel = pd.read_parquet(RAW / "panel.parquet").set_index("business_id")
    index = loans.build_index(app_state)
    return V2State(scorecard, score_X, adj_X, adj_explainer, panel, index)
