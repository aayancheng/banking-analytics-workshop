"""Train the Loan Adjudication LightGBM default model, calibrate PD-zone thresholds,
run the policy layer over the test split, persist artifacts + validation report, and
enforce the metric gate (AUC >= 0.78, top-20% lift >= 2.0x)."""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from shared.config import RAW, SEED, ADJ_POLICY, LEAKAGE_COLUMNS
from adjudication.src.feature_engineering import (
    ADJ_FEATURE_COLUMNS, ADJ_CATEGORICAL, compute_adjudication_features,
)
from adjudication.src.policy import PolicyConfig, decide
from adjudication.src.reason_codes import top_adverse_shap

MODELS = Path("adjudication/models")
DOCS = Path("adjudication/docs")

AUC_GATE = 0.78
LIFT_GATE = 2.0


def top_ventile_lift(y_true, pd_hat):
    y = np.asarray(y_true); p = np.asarray(pd_hat)
    cut = np.quantile(p, 0.80)
    top = y[p >= cut]
    base = y.mean()
    return float(top.mean() / base) if base > 0 else 0.0


def main():
    MODELS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    biz = pd.read_parquet(RAW / "businesses.parquet")
    X_all = compute_adjudication_features(biz)
    X = X_all[ADJ_FEATURE_COLUMNS]
    y = biz["default"].to_numpy()

    assert set(ADJ_FEATURE_COLUMNS).isdisjoint(set(LEAKAGE_COLUMNS)), "leakage in features"

    X_tr, X_te, y_tr, y_te, idx_tr, idx_te = train_test_split(
        X, y, np.arange(len(X)), test_size=0.2, random_state=SEED, stratify=y)

    model = LGBMClassifier(
        n_estimators=400, learning_rate=0.03, num_leaves=31,
        subsample=0.8, colsample_bytree=0.8, random_state=SEED, n_jobs=-1, verbose=-1,
    )
    model.fit(X_tr, y_tr, categorical_feature=ADJ_CATEGORICAL)

    pd_te = model.predict_proba(X_te)[:, 1]
    auc = float(roc_auc_score(y_te, pd_te))
    lift = top_ventile_lift(y_te, pd_te)

    # --- calibrate PD zones from the model PD distribution (seed values in ADJ_POLICY) ---
    policy_d = dict(ADJ_POLICY)
    pd_full = model.predict_proba(X)[:, 1]
    policy_d["t_low"] = float(round(np.quantile(pd_full, 0.55), 4))
    policy_d["t_high"] = float(round(np.quantile(pd_full, 0.90), 4))
    config = PolicyConfig.from_dict(policy_d)

    # decision mix on the test split (feature frame carries score_band etc.)
    dec = decide(X_all.iloc[idx_te], pd_te, config)
    mix = dec["decision"].value_counts(normalize=True).round(3).to_dict()
    knockouts = int(dec["decision_reasons"].apply(lambda r: len(r) > 0).sum())

    # SHAP sanity (background sample for speed)
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X_te.iloc[:50])
    sv = sv[1] if isinstance(sv, list) else sv
    _ = top_adverse_shap(sv, ADJ_FEATURE_COLUMNS, k=3)

    # --- persist ---
    joblib.dump(model, MODELS / "adjudication_model.pkl")
    (MODELS / "policy_config.json").write_text(json.dumps(config.to_dict(), indent=2))
    metadata = {
        "ADJ_FEATURE_COLUMNS": ADJ_FEATURE_COLUMNS,
        "categorical": ADJ_CATEGORICAL,
        "train_rows": int(len(X_tr)), "test_rows": int(len(X_te)),
        "metrics": {"auc": round(auc, 4), "top20_lift": round(lift, 4)},
        "gate": {"auc_min": AUC_GATE, "lift_min": LIFT_GATE},
        "decision_mix_test": mix,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (MODELS / "metadata.json").write_text(json.dumps(metadata, indent=2))

    report = (
        "# Loan Adjudication — Validation Report\n\n"
        f"- Train rows: {len(X_tr):,}  Test rows: {len(X_te):,}\n"
        f"- **AUC:** {auc:.4f}  (gate >= {AUC_GATE})\n"
        f"- **Top-20% lift:** {lift:.2f}x  (gate >= {LIFT_GATE})\n\n"
        "## PD-zone thresholds (calibrated)\n\n"
        f"- t_low (Approve <=): {config.t_low}\n- t_high (Decline >=): {config.t_high}\n\n"
        "## Decision mix (test split)\n\n"
        + "\n".join(f"- {k}: {v:.1%}" for k, v in sorted(mix.items()))
        + f"\n\n- Files with >=1 policy rule hit: {knockouts:,}\n"
    )
    (DOCS / "validation_report.md").write_text(report)

    print(f"AUC={auc:.4f} lift={lift:.2f}x | t_low={config.t_low} t_high={config.t_high} | mix={mix}")

    assert auc >= AUC_GATE, f"GATE FAIL: AUC {auc:.4f} < {AUC_GATE}"
    assert lift >= LIFT_GATE, f"GATE FAIL: lift {lift:.2f} < {LIFT_GATE}"
    print("GATE PASS")


if __name__ == "__main__":
    main()
