"""The oracle-ceiling calculator (Session 4).

Answers one question: was your expectation achievable on this data at all?

Three numbers, in descending order of privilege:
  1. noise-free latent  — scores the DGP's own clean logit against the drawn label.
                          Perfect knowledge of the true drivers. NOTHING can beat
                          this except luck.
  2. oracle model       — the strongest model we can train on OBSERVABLE features.
                          The best any honest model can do.
  3. your model         — the committed EWS model, same held-out split as training.

Run from the repo root:  python workshop/labs/oracle_ceiling.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from shared.config import LEAKAGE_COLUMNS, RAW, SEED, ROOT
from ews.src.feature_engineering import (
    EWS_FEATURE_COLUMNS, _cached_panel_features, compute_ews_features,
)

TARGET = "deterioration_next_6_12mo"

port = pd.read_parquet(RAW / "portfolio.parquet")
y = port[TARGET].to_numpy()

# ---- 1. the noise-free latent (rebuild the DGP logit WITHOUT its noise term) ----
# This mirrors shared/data_generator.py exactly — go read it, it's short.
pf = _cached_panel_features().set_index("business_id")
pd_true = port["pd_default_origination"].to_numpy()          # allowed HERE only:
util_last3 = port["utilization_onbook"].to_numpy()           # we are grading the
lev = port["leverage"].to_numpy()                            # DATA, not a model.
# util_trend exactly as the DGP defines it: last month minus first month
panel = pd.read_parquet(RAW / "panel.parquet")
last_m = panel["month_index"].max()
u = panel.pivot_table(index="business_id", columns="month_index",
                      values="utilization", aggfunc="first")
util_trend = (u[last_m] - u[0]).loc[port["business_id"]].to_numpy()


def _z(x):
    s = x.std()
    return (x - x.mean()) / (s if s > 0 else 1.0)


latent = (3.0 * pd_true
          + 2.0 * np.clip(util_last3 - 0.85, 0, None)
          + 1.5 * np.clip(util_trend, 0, None)
          + 0.4 * _z(lev))
auc_latent = roc_auc_score(y, latent)

# ---- 2. the oracle model on observables only ----
X = port.merge(pf.reset_index(), on="business_id")
X = X.drop(columns=[c for c in LEAKAGE_COLUMNS + ["business_id", "net_income"]
                    if c in X.columns])
for c in ["industry", "region", "entity_type", "loan_purpose"]:
    X[c] = X[c].astype("category")
cats = ["industry", "region", "entity_type", "loan_purpose"]
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                          random_state=SEED, stratify=y)
oracle = LGBMClassifier(n_estimators=500, learning_rate=0.03, num_leaves=31,
                        subsample=0.8, colsample_bytree=0.8, random_state=SEED,
                        n_jobs=-1, verbose=-1)
oracle.fit(X_tr, y_tr, categorical_feature=cats)
auc_oracle = roc_auc_score(y_te, oracle.predict_proba(X_te)[:, 1])

# ---- 3. your committed model, same held-out split as training ----
model = joblib.load(ROOT / "ews" / "models" / "ews_model.pkl")
feats = compute_ews_features(port)[EWS_FEATURE_COLUMNS]
_, Xm_te, _, ym_te = train_test_split(feats, y, test_size=0.2,
                                      random_state=SEED, stratify=y)
auc_yours = roc_auc_score(ym_te, model.predict_proba(Xm_te)[:, 1])

print()
print(f"  1. noise-free latent (perfect knowledge) : AUC {auc_latent:.3f}")
print(f"  2. oracle model (observables only)       : AUC {auc_oracle:.3f}")
print(f"  3. your EWS model                        : AUC {auc_yours:.3f}")
print()
print("  If (3) is close to (2), your model is not weak — your expectation was")
print("  impossible. Now re-grade it against the honest gate: capture >= 2x,")
print("  PR-AUC > the 18.0% base rate. (Spoiler: python verify.py already did.)")
