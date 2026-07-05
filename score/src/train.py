"""Train the Business Credit Score scorecard (WoE + Logistic), scale to 300-850,
compute metrics, persist artifacts + validation report, and enforce the gate.

THE GATE IS A PROMISE. AUC >= 0.78 on the held-out split, hard assert — a model
that misses it fails the build. The gate value was set BELOW the measured
ceilings of this synthetic target (noise-free latent AUC 0.818, LightGBM oracle
on observables 0.807), so it is demanding but reachable: see Session 2.
verify.py recomputes this metric independently — relaxing the assert here
does not move the checkpoint.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from optbinning import BinningProcess, Scorecard
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from shared.config import RAW, SCORE_MIN, SCORE_MAX, SEED
from score.src.feature_engineering import FEATURE_COLUMNS, CATEGORICAL, compute_features

MODELS = Path("score/models")
DOCS = Path("score/docs")

AUC_GATE = 0.78   # workshop gate — the committed promise (KS reported, not gated)


def score_to_fico(raw_scores, lo, hi):
    """Linearly map raw scorecard points (in [lo, hi]) to [SCORE_MIN, SCORE_MAX], clamped."""
    raw = np.asarray(raw_scores, dtype=float)
    if hi <= lo:
        return np.full_like(raw, (SCORE_MIN + SCORE_MAX) / 2.0)
    scaled = SCORE_MIN + (raw - lo) / (hi - lo) * (SCORE_MAX - SCORE_MIN)
    return np.clip(scaled, SCORE_MIN, SCORE_MAX).round().astype(int)


def ks_statistic(y_true, y_score):
    order = np.argsort(y_score)
    y = np.asarray(y_true)[order]
    cum_bad = np.cumsum(y) / max(y.sum(), 1)
    cum_good = np.cumsum(1 - y) / max((1 - y).sum(), 1)
    return float(np.max(np.abs(cum_bad - cum_good)))


def main():
    MODELS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    biz = pd.read_parquet(RAW / "businesses.parquet")
    X_all = compute_features(biz)
    X = X_all[FEATURE_COLUMNS]
    y = biz["default"].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y)

    binning_process = BinningProcess(
        variable_names=FEATURE_COLUMNS,
        categorical_variables=CATEGORICAL,
    )
    estimator = LogisticRegression(solver="lbfgs", max_iter=1000)
    scorecard = Scorecard(
        binning_process=binning_process,
        estimator=estimator,
        scaling_method="pdo_odds",
        scaling_method_params={"pdo": 50, "odds": 20, "scorecard_points": 600},
        reverse_scorecard=False,  # False gives FICO-like direction: high score = low default risk
    )
    scorecard.fit(X_train, y_train)

    raw_train = scorecard.score(X_train)
    lo, hi = np.percentile(raw_train, 1), np.percentile(raw_train, 99)

    pd_test = scorecard.predict_proba(X_test)[:, 1]
    auc = float(roc_auc_score(y_test, pd_test))
    ks = ks_statistic(y_test, pd_test)

    fico_test = score_to_fico(scorecard.score(X_test), lo, hi)
    bands = pd.cut(fico_test, bins=[300, 580, 640, 700, 750, 850],
                   labels=["D", "C", "B", "A", "AAA"], include_lowest=True)
    band_tbl = (pd.DataFrame({"band": bands, "default": y_test})
                .groupby("band", observed=True)["default"]
                .agg(["count", "mean"]).round(4))

    joblib.dump(scorecard, MODELS / "scorecard.pkl")
    (MODELS / "score_scaling.json").write_text(json.dumps({"lo": float(lo), "hi": float(hi)}))
    metadata = {
        "FEATURE_COLUMNS": FEATURE_COLUMNS,
        "categorical": CATEGORICAL,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "metrics": {"auc": round(auc, 4), "ks": round(ks, 4)},
        "gate": {"auc_min": AUC_GATE},
        "score_range": [SCORE_MIN, SCORE_MAX],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (MODELS / "metadata.json").write_text(json.dumps(metadata, indent=2))

    band_md = band_tbl.to_markdown()
    report = (
        "# Business Credit Score — Validation Report\n\n"
        f"- Train rows: {len(X_train):,}  Test rows: {len(X_test):,}\n"
        f"- **AUC:** {auc:.4f}  (gate >= {AUC_GATE})  |  **KS:** {ks:.4f}\n\n"
        "## Default rate by score band (test)\n\n"
        f"{band_md}\n"
    )
    (DOCS / "validation_report.md").write_text(report)

    print(f"AUC={auc:.4f} KS={ks:.4f} | scaling lo={lo:.2f} hi={hi:.2f}")
    print(band_tbl)

    assert auc >= AUC_GATE, f"GATE FAIL: AUC {auc:.4f} < {AUC_GATE}"
    print("GATE PASS")


if __name__ == "__main__":
    main()
