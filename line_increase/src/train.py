"""Train the Proactive Line-Increase LightGBM candidate model (target line_increase_good),
calibrate the offer threshold, build the offered cohort with the amount rules + incremental
ROE, persist artifacts + validation report, and enforce the gate:
  AUC >= 0.78, top-20% lift >= 2.0, offered cohort lower mean PD + higher mean utilization
  than the book, and exposure-weighted incremental ROE >= the hurdle."""
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

from shared.config import RAW, SEED, LEAKAGE_COLUMNS, LINE_INCREASE, MARKET
from line_increase.src.feature_engineering import (
    LI_FEATURE_COLUMNS, LI_CATEGORICAL, compute_line_increase_features,
)
from line_increase.src.amount_rules import recommended_amount, incremental_roe
from pricing.src.engine import MarketAssumptions
from adjudication.src.reason_codes import top_adverse_shap

MODELS = Path("line_increase/models")
DOCS = Path("line_increase/docs")
TARGET = "line_increase_good"

AUC_GATE = 0.78
LIFT_GATE = 2.0
_MARKET = MarketAssumptions.from_market(MARKET)


def top_ventile_lift(y_true, prob):
    y = np.asarray(y_true); p = np.asarray(prob)
    cut = np.quantile(p, 0.80)
    base = y.mean()
    return float(y[p >= cut].mean() / base) if base > 0 else 0.0


def main():
    MODELS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    port = pd.read_parquet(RAW / "portfolio.parquet")
    feats = compute_line_increase_features(port)
    X = feats[LI_FEATURE_COLUMNS]
    y = port[TARGET].to_numpy()
    assert set(LI_FEATURE_COLUMNS).isdisjoint(set(LEAKAGE_COLUMNS)), "leakage in features"

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y)
    model = LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=31,
                           subsample=0.8, colsample_bytree=0.8, random_state=SEED,
                           n_jobs=-1, verbose=-1)
    model.fit(X_tr, y_tr, categorical_feature=LI_CATEGORICAL)

    prob_te = model.predict_proba(X_te)[:, 1]
    auc = float(roc_auc_score(y_te, prob_te))
    lift = top_ventile_lift(y_te, prob_te)

    # offer threshold calibrated to the population prob quantile
    prob_full = model.predict_proba(X)[:, 1]
    threshold = float(round(np.quantile(prob_full, LINE_INCREASE["offer_quantile"]), 4))

    # build the offered cohort (prob >= threshold AND within risk appetite AND amount > 0
    # AND incremental ROE clears). The risk-appetite ceiling offers only to the lower-risk
    # half of the book — proactive increases go to low-PD accounts that are using their line.
    bal = port["current_balance"].to_numpy(dtype=float)
    lim = port["credit_limit"].to_numpy(dtype=float)
    rev = port["annual_revenue"].to_numpy(dtype=float)
    util = port["utilization_onbook"].to_numpy(dtype=float)
    rate = port["risk_based_rate"].to_numpy(dtype=float)
    pd_score = feats["pd_score"].to_numpy(dtype=float)
    max_pd = float(round(np.quantile(pd_score, LINE_INCREASE["max_pd_quantile"]), 4))

    offered = np.zeros(len(port), dtype=bool)
    sum_net_income = 0.0
    sum_equity = 0.0
    for i in range(len(port)):
        if prob_full[i] < threshold or pd_score[i] > max_pd:
            continue
        amt = recommended_amount(bal[i], lim[i], rev[i])
        if amt <= 0:
            continue
        r = incremental_roe(pd_score[i], amt, util[i], rate[i], _MARKET)
        if r["clears_hurdle"]:
            offered[i] = True
            sum_net_income += r["incremental_net_income"]
            sum_equity += MARKET["capital_ratio"] * r["incremental_ead"]

    book_pd = float(pd_score.mean())
    book_util = float(util.mean())
    cohort_pd = float(pd_score[offered].mean()) if offered.any() else float("nan")
    cohort_util = float(util[offered].mean()) if offered.any() else float("nan")
    agg_incr_roe = float(sum_net_income / sum_equity) if sum_equity > 0 else 0.0
    n_offered = int(offered.sum())

    # SHAP sanity (small background sample for speed)
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X_te.iloc[:50])
    sv = sv[1] if isinstance(sv, list) else sv
    _ = top_adverse_shap(sv, LI_FEATURE_COLUMNS, k=3)

    joblib.dump(model, MODELS / "line_increase_model.pkl")
    metadata = {
        "LI_FEATURE_COLUMNS": LI_FEATURE_COLUMNS, "categorical": LI_CATEGORICAL,
        "train_rows": int(len(X_tr)), "test_rows": int(len(X_te)),
        "metrics": {"auc": round(auc, 4), "top20_lift": round(lift, 4)},
        "gate": {"auc_min": AUC_GATE, "lift_min": LIFT_GATE},
        "offer_threshold": threshold,
        "offer_max_pd": max_pd,
        "base_rate": round(float(y.mean()), 4),
        "cohort": {
            "n_offered": n_offered,
            "book_pd": round(book_pd, 4), "cohort_pd": round(cohort_pd, 4),
            "book_util": round(book_util, 4), "cohort_util": round(cohort_util, 4),
            "agg_incremental_roe": round(agg_incr_roe, 4),
            "roe_hurdle": MARKET["roe_hurdle"],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (MODELS / "metadata.json").write_text(json.dumps(metadata, indent=2))

    report = (
        "# Proactive Line Increase — Validation Report\n\n"
        f"- Train {len(X_tr):,} / Test {len(X_te):,}  | base rate {y.mean():.1%}\n"
        f"- **AUC:** {auc:.4f}  (gate >= {AUC_GATE})\n"
        f"- **Top-20% lift:** {lift:.2f}x  (gate >= {LIFT_GATE})\n"
        f"- Offer threshold (prob quantile {LINE_INCREASE['offer_quantile']}): {threshold}\n"
        f"- Risk-appetite PD ceiling (quantile {LINE_INCREASE['max_pd_quantile']}): {max_pd}\n\n"
        "## Offered cohort vs book\n\n"
        f"- Offered accounts: {n_offered:,}\n"
        f"- Mean modeled PD: cohort {cohort_pd:.4f} vs book {book_pd:.4f}  (gate cohort < book)\n"
        f"- Mean utilization: cohort {cohort_util:.4f} vs book {book_util:.4f}  (gate cohort > book)\n"
        f"- Exposure-weighted incremental ROE: {agg_incr_roe:.4f}  "
        f"(gate >= {MARKET['roe_hurdle']})\n\n"
        "> Incremental ROE is EAD-invariant (depends only on PD & the rate charged on the "
        "incremental balance); the drawdown assumption (Δlimit × utilization) scales the "
        "reported incremental exposure and net income, not the ROE ratio.\n"
    )
    (DOCS / "validation_report.md").write_text(report)

    print(f"AUC={auc:.4f} lift={lift:.2f}x thr={threshold} offered={n_offered} "
          f"cohort_pd={cohort_pd:.4f}<book_pd={book_pd:.4f} "
          f"cohort_util={cohort_util:.4f}>book_util={book_util:.4f} "
          f"agg_incr_roe={agg_incr_roe:.4f}")

    assert auc >= AUC_GATE, f"GATE FAIL: AUC {auc:.4f} < {AUC_GATE}"
    assert lift >= LIFT_GATE, f"GATE FAIL: lift {lift:.2f} < {LIFT_GATE}"
    assert n_offered > 0, "GATE FAIL: no accounts offered"
    assert cohort_pd < book_pd, f"GATE FAIL: cohort PD {cohort_pd:.4f} !< book {book_pd:.4f}"
    assert cohort_util > book_util, f"GATE FAIL: cohort util {cohort_util:.4f} !> book {book_util:.4f}"
    assert agg_incr_roe >= MARKET["roe_hurdle"], (
        f"GATE FAIL: agg incremental ROE {agg_incr_roe:.4f} < {MARKET['roe_hurdle']}")
    print("GATE PASS")


if __name__ == "__main__":
    main()
