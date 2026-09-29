"""Sensitivity refits for D4.6 — train.py's exact recipe on reduced column sets. Slow
(minutes), so build_facts runs them only with --full and caches them in facts.json."""
from __future__ import annotations

from optbinning import BinningProcess, Scorecard
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from score.src.feature_engineering import CATEGORICAL, FEATURE_COLUMNS, compute_features
from score.src.train import ks_statistic
from wiki.facts.core import Fact

BUREAU = ["utilization", "credit_history_months", "prior_delinquencies", "trade_lines"]
FIVE_RAW = ["dscr", "utilization", "prior_delinquencies", "leverage", "years_in_business"]
STRUCTURAL_FIVE = ["industry", "entity_type", "trade_lines", "term_months", "collateral_flag"]
PROXY_FIVE = ["requested_amount", "net_income", "total_debt", "annual_revenue", "employees"]
RAW_CATS = {"industry", "region", "entity_type", "loan_purpose"}
HOLDOUT = "held-out 20% of applicants (score split, seed 42)"


def _refit(X, cols, cats, y, tr, te, mip: bool) -> tuple[float, float]:
    X = X[cols].copy()
    for c in cats:
        X[c] = X[c].astype(str)
    extra = {"binning_fit_params": {c: {"solver": "mip"} for c in cols}} if mip else {}
    card = Scorecard(
        binning_process=BinningProcess(variable_names=cols, categorical_variables=cats, **extra),
        estimator=LogisticRegression(solver="lbfgs", max_iter=1000),
        scaling_method="pdo_odds",
        scaling_method_params={"pdo": 50, "odds": 20, "scorecard_points": 600},
        reverse_scorecard=False,
    ).fit(X.iloc[tr], y[tr])
    p = card.predict_proba(X.iloc[te])[:, 1]
    return float(roc_auc_score(y[te], p)), float(ks_statistic(y[te], p))


def compute(split) -> dict[str, Fact]:
    biz, y, tr, te = split.biz, split.y, split.idx_tr, split.idx_te
    feats = compute_features(biz)
    kept = [c for c in FEATURE_COLUMNS if c not in BUREAU]
    nb_auc, nb_ks = _refit(feats, kept, [c for c in kept if c in CATEGORICAL],
                           y, tr, te, mip=False)       # train.py's recipe: default CP solver
    src = "wiki.facts.score_stress (train.py recipe, reduced columns)"
    src_mip = src + ", solver=mip"
    f = {
        "score.stress.no_bureau.auc": Fact(nb_auc, ".4f", src, HOLDOUT),
        "score.stress.no_bureau.ks": Fact(nb_ks, ".4f", src, HOLDOUT),
        "score.stress.bureau_columns": Fact(", ".join(BUREAU), "", src, HOLDOUT),
    }
    for key, cols, fmt in [("five_raw", FIVE_RAW, ".4f"),
                           ("structural_five", STRUCTURAL_FIVE, ".2f"),
                           ("proxy_five", PROXY_FIVE, ".2f")]:
        auc, _ = _refit(biz, cols, [c for c in cols if c in RAW_CATS], y, tr, te, mip=True)
        f[f"score.stress.{key}.auc"] = Fact(auc, fmt, src_mip, HOLDOUT)
        f[f"score.stress.{key}_columns"] = Fact(", ".join(cols), "", src_mip, HOLDOUT)
    return f
