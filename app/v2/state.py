"""v2 workbench state: the extra objects loan-level explanation needs, built once.

v1's app.state already holds the scored populations, and v2 reuses them rather than
re-scoring. v2 adds only what per-loan explanation needs: the scorecard object (for
the WoE x beta ledger), a SHAP explainer over the adjudication model, the feature
matrices to index into, the 24-month behavioural panel, and the EWS feature frame
(ews_feats) -- the watchlist row only carries KEY_METRICS, which excludes columns
like dpd_recent that a compound trigger rule reads, so explaining a fired trigger
needs the full feature row, not the scored one.

Nothing is precomputed across the population — a per-loan explanation is 2-3ms, so
precomputing 12,000 of them would cost seconds of boot to save nothing. Measured
cost of this build: ~0.15s on top of v1's 7.4s.

adj_X is recomputed here rather than shared out of v1's lifespan. It costs 0.05s and
it keeps app/main.py at four added statements, which is the point of v2 being a
side-by-side demo rather than a rewrite.
"""
import json
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
from adjudication.src.policy import PolicyConfig
from ews.src.feature_engineering import compute_ews_features
from line_increase.src.feature_engineering import (
    LI_FEATURE_COLUMNS, compute_line_increase_features,
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
    ews_feats: pd.DataFrame
    li_prob_raw: pd.Series


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
    app_state.policy_config = PolicyConfig.from_dict(
        json.loads((ROOT / "adjudication" / "models" / "policy_config.json").read_text()))
    portfolio = pd.read_parquet(RAW / "portfolio.parquet")
    ews_feats = compute_ews_features(portfolio)
    ews_feats = ews_feats.set_index(ews_feats["business_id"].astype(str))
    # ews_whatif re-tiers positionally against app_state.ews, so the two frames must
    # stay in the same ORDER, not merely hold the same ids. They do today because both
    # derive from this one call, but nothing else enforces it and a silent reorder
    # would return another loan's tier under the right business_id.
    assert ews_feats.index.equals(app_state.ews.index), (
        "ews_feats and app.state.ews are misaligned; v2 would report the wrong "
        "loan's risk tier")

    # Fix round 1 (display-precision review): candidates.score_population decides
    # `eligible` on the model's UNROUNDED probability but persists `prob` rounded to
    # 4dp; app/v2/line_increase.py's prob_above_threshold clause was reading that
    # rounded column, so a screen could show PASS/FAIL that disagreed with the
    # verdict it was explaining. Recomputed here the same way candidates.py does --
    # same model, same feature function, same portfolio row order -- rather than
    # exposing an internal of that module. `portfolio` is the exact frame
    # compute_line_increase_features expects (candidates.py reads it fresh too), so
    # this reuses the read already done for ews_feats instead of a second I/O pass.
    li_model = joblib.load(ROOT / "line_increase" / "models" / "line_increase_model.pkl")
    li_X = compute_line_increase_features(portfolio)
    li_prob_raw = pd.Series(
        li_model.predict_proba(li_X[LI_FEATURE_COLUMNS])[:, 1],
        index=li_X["business_id"].astype(str), name="prob_raw")
    # Same order-alignment risk as ews_feats above: nothing but this assert stops a
    # future reorder from silently attaching one loan's raw probability to another's
    # eligibility clause.
    assert li_prob_raw.index.equals(app_state.li.index), (
        "li_prob_raw and app_state.li are misaligned; v2 would report the wrong "
        "loan's raw probability")

    return V2State(scorecard, score_X, adj_X, adj_explainer, panel, index, ews_feats,
                   li_prob_raw)
