"""The data's own AUC ceiling. The ONE place the wiki touches DGP truth: it grades the
data, not a model (same rule as workshop/labs/oracle_ceiling.py). Method: the appendix of
workshop/reading/S1-data-generation.pdf — rebuild the generator's logit without its noise."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score

from wiki.facts.core import Fact

SRC = "wiki.facts.ceiling (DGP logit without noise; S1 reading note appendix)"


def _z(x) -> np.ndarray:
    x = np.asarray(x, float)
    return (x - x.mean()) / x.std()


def signal(b) -> np.ndarray:
    pm = np.clip(b["net_income"] / np.maximum(b["annual_revenue"], 1), -1, 1)
    return (-2.2
            - 0.60 * _z(np.log(b["years_in_business"])) - 0.50 * _z(np.log(b["annual_revenue"]))
            - 0.70 * _z(b["dscr"]) - 0.40 * _z(b["current_ratio"])
            + 0.60 * _z(b["leverage"]) + 0.55 * _z(b["utilization"])
            + 0.50 * _z(b["prior_delinquencies"].astype(float)) + 0.70 * b["public_records"]
            - 0.40 * _z(np.log(b["credit_history_months"])) - 1.50 * pm).to_numpy()


def compute(split) -> dict[str, Fact]:
    b, y, te = split.biz, split.y, split.idx_te
    s = signal(b)
    held = float(roc_auc_score(y[te], s[te]))
    from score.src.predict import predict_score_pd
    model = float(roc_auc_score(y[te], predict_score_pd(b.iloc[te])["pd"].to_numpy()))
    return {
        "ceiling.signal_all": Fact(float(roc_auc_score(y, s)), ".4f", SRC, "all 12,000 applicants"),
        "ceiling.truepd_all": Fact(float(roc_auc_score(y, b["pd_default_origination"])), ".4f",
                                   SRC, "all 12,000 applicants"),
        "ceiling.signal_holdout": Fact(held, ".4f", SRC, "held-out 20% (score split)"),
        "ceiling.gap_holdout": Fact(held - model, ".3f", SRC, "held-out 20% (score split)"),
    }
