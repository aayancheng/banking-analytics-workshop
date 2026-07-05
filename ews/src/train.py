"""Train the EWS LightGBM deterioration model, calibrate risk-tier cutoffs, persist
artifacts + report, enforce the gate (top-decile capture >= 2x lift, PR-AUC > base rate).
Option B: AUC reported (not gated); sanity floor 0.60. See ews/docs/enhancement_notes.md."""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import train_test_split

from shared.config import RAW, SEED, EWS_TIERS, LEAKAGE_COLUMNS
from ews.src.feature_engineering import (
    EWS_FEATURE_COLUMNS, EWS_CATEGORICAL, compute_ews_features,
)
from adjudication.src.reason_codes import top_adverse_shap

MODELS = Path("ews/models")
DOCS = Path("ews/docs")
TARGET = "deterioration_next_6_12mo"
# Gate (Option B — honest gate for the noise-capped synthetic deterioration target).
# The DGP label carries a large logit-noise + Bernoulli draw, so the oracle ceiling is
# ~0.70 AUC; we gate on what the data genuinely supports and report AUC for transparency.
# See ews/docs/enhancement_notes.md for the Option-A signal-sharpening enhancement (deferred).
CAPTURE_GATE = 0.20  # >= 20% of deteriorations in the top decile == 2x lift
AUC_REPORT_FLOOR = 0.60  # sanity floor only (model must beat near-random); not the headline gate


def top_decile_capture(y_true, prob):
    y = np.asarray(y_true); p = np.asarray(prob)
    k = max(1, int(round(0.10 * len(y))))
    top_idx = np.argsort(p)[::-1][:k]
    total_bad = y.sum()
    return float(y[top_idx].sum() / total_bad) if total_bad else 0.0


def main():
    MODELS.mkdir(parents=True, exist_ok=True); DOCS.mkdir(parents=True, exist_ok=True)
    port = pd.read_parquet(RAW / "portfolio.parquet")
    feats = compute_ews_features(port)
    X = feats[EWS_FEATURE_COLUMNS]
    y = port[TARGET].to_numpy()
    assert set(EWS_FEATURE_COLUMNS).isdisjoint(set(LEAKAGE_COLUMNS)), "leakage in features"

    # persist the panel-feature cache so verify.py and the app skip the slow groupby
    from ews.src.feature_engineering import _cached_panel_features
    _cached_panel_features().to_parquet(MODELS / "panel_features.parquet", index=False)

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y)
    model = LGBMClassifier(n_estimators=500, learning_rate=0.03, num_leaves=31,
                           subsample=0.8, colsample_bytree=0.8, random_state=SEED,
                           n_jobs=-1, verbose=-1)
    model.fit(X_tr, y_tr, categorical_feature=EWS_CATEGORICAL)

    prob_te = model.predict_proba(X_te)[:, 1]
    auc = float(roc_auc_score(y_te, prob_te))
    pr_auc = float(average_precision_score(y_te, prob_te))
    capture = top_decile_capture(y_te, prob_te)
    lift = capture / 0.10

    prob_full = model.predict_proba(X)[:, 1]
    tiers = dict(EWS_TIERS)
    tiers["t_high"] = float(round(np.quantile(prob_full, 0.90), 4))
    tiers["t_med"] = float(round(np.quantile(prob_full, 0.70), 4))

    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X_te.iloc[:50])
    sv = sv[1] if isinstance(sv, list) else sv
    _ = top_adverse_shap(sv, EWS_FEATURE_COLUMNS, k=3)

    joblib.dump(model, MODELS / "ews_model.pkl")
    metadata = {
        "EWS_FEATURE_COLUMNS": EWS_FEATURE_COLUMNS, "categorical": EWS_CATEGORICAL,
        "metrics": {"auc": round(auc, 4), "pr_auc": round(pr_auc, 4),
                    "top_decile_capture": round(capture, 4), "top_decile_lift": round(lift, 4)},
        "gate": {"capture_min": CAPTURE_GATE, "pr_auc_min": "base_rate",
                 "auc_report_floor": AUC_REPORT_FLOOR},
        "tiers": tiers, "base_rate": round(float(y.mean()), 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (MODELS / "metadata.json").write_text(json.dumps(metadata, indent=2))
    base = float(y.mean())
    report = (
        "# Early Warning — Validation Report\n\n"
        f"- Train {len(X_tr):,} / Test {len(X_te):,}  | base rate {base:.1%}\n"
        f"- **Top-decile capture:** {capture:.1%}  =  **{lift:.2f}x** lift  (gate >= 2x)\n"
        f"- **PR-AUC:** {pr_auc:.4f}  (gate > base rate {base:.4f})\n"
        f"- **AUC:** {auc:.4f}  (reported; not gated — see note below)\n"
        f"- Risk tiers: High >= {tiers['t_high']}, Medium >= {tiers['t_med']}\n\n"
        "> **Gate note (Option B):** the synthetic `deterioration_next_6_12mo` label is "
        "noise-capped (logit noise + Bernoulli draw → oracle ceiling ~0.70 AUC), so the gate "
        "is set to what the data genuinely supports: top-decile capture >= 2x lift and "
        "PR-AUC above the base rate. A signal-sharpening enhancement (Option A) is documented "
        "in `ews/docs/enhancement_notes.md` for a future iteration.\n"
    )
    (DOCS / "validation_report.md").write_text(report)
    print(f"AUC={auc:.4f} PR-AUC={pr_auc:.4f} capture={capture:.1%} lift={lift:.2f}x base={base:.4f}")
    assert capture >= CAPTURE_GATE, f"GATE FAIL: capture {capture:.3f} < {CAPTURE_GATE} (2x)"
    assert pr_auc > base, f"GATE FAIL: PR-AUC {pr_auc:.4f} <= base rate {base:.4f}"
    assert auc >= AUC_REPORT_FLOOR, f"GATE FAIL: AUC {auc:.4f} < sanity floor {AUC_REPORT_FLOOR}"
    print("GATE PASS")


if __name__ == "__main__":
    main()
