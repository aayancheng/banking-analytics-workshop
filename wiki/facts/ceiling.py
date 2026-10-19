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


# --- S1: the leakage ladder's middle rung (the true PD leaked into a model) ----------------
SRC_LEAK = ("wiki.facts.ceiling.compute_leakage (notebook 01 leakage cell / S1 lab "
            "leakage_probe.py: LGBMClassifier(verbose=-1) on four honest features plus the "
            "true PD, fitted by wiki.facts.leakage.probe_auc)")


def compute_leakage(split, honest_auc: float) -> dict[str, Fact]:
    """The probe's middle rung: the four honest features plus the generator's true PD. Also
    the true PD's own AUC on the same held-out rows, which bounds what any model leaking it
    can reach: the outcome is a Bernoulli draw on the PD, so even the truth ranks it
    imperfectly. honest_auc is wiki.facts.leakage's honest rung, for the gain."""
    from wiki.facts.leakage import HONEST, POP, probe_auc
    b, te = split.biz, split.idx_te
    pd_true = b["pd_default_origination"]                     # DGP truth: allowed HERE only
    rung = probe_auc(b[HONEST].assign(cheat=pd_true), b["default"], split)
    alone = float(roc_auc_score(split.y[te], pd_true.to_numpy()[te]))
    return {
        "leakage.truepd.auc": Fact(rung, ".4f", SRC_LEAK, POP),
        "leakage.truepd.gain": Fact(rung - honest_auc, ".2f",
                                    SRC_LEAK + " minus wiki.facts.leakage's honest rung", POP),
        "leakage.truepd.alone_auc": Fact(alone, ".4f",
                                         SRC + ": the true PD itself, ranked", POP),
    }


# --- D7: the deterioration label's ceiling (mirrors workshop/labs/oracle_ceiling.py) ---------
SRC_EWS = ("wiki.facts.ceiling.ews_latent (the DGP's deterioration logit without its noise "
           "term; mirrors workshop/labs/oracle_ceiling.py)")
SRC_ORACLE = ("wiki.facts.ceiling.compute_ews_oracle (LightGBM on every observable column, "
              "train.py's hyper-parameters and split; mirrors workshop/labs/oracle_ceiling.py)")
EWS_BOOK = "booked book, all 8,336 accounts"
EWS_HOLDOUT = "held-out 20% of the booked book (EWS split, seed 42, stratified: 1,668 accounts)"


def ews_latent(port) -> np.ndarray:
    """The deterioration logit of shared/data_generator.py without its N(0, 0.4) noise and
    without its intercept (AUC is rank-only), built exactly as oracle_ceiling.py builds it:
    the true PD, on-book utilisation (last three months), the first-to-last utilisation trend
    from the panel, and leverage."""
    import pandas as pd
    from shared.config import RAW
    panel = pd.read_parquet(RAW / "panel.parquet")
    last_m = panel["month_index"].max()
    u = panel.pivot_table(index="business_id", columns="month_index",
                          values="utilization", aggfunc="first")
    util_trend = (u[last_m] - u[0]).loc[port["business_id"]].to_numpy()
    pd_true = port["pd_default_origination"].to_numpy()       # DGP truth: allowed HERE only
    util_last3 = port["utilization_onbook"].to_numpy()
    lev = np.asarray(port["leverage"], float)
    return (3.0 * pd_true + 2.0 * np.clip(util_last3 - 0.85, 0, None)
            + 1.5 * np.clip(util_trend, 0, None) + 0.4 * _z(lev))


def compute_ews(es) -> dict[str, Fact]:
    """es: wiki.facts.ews_facts.EwsSplit (train.py's split and the committed model's prob)."""
    from ews.src.train import top_decile_capture
    from sklearn.metrics import average_precision_score
    y, te = es.y, es.idx_te
    lat = ews_latent(es.port)
    held = float(roc_auc_score(y[te], lat[te]))
    model = float(roc_auc_score(y[te], es.prob[te]))
    return {
        "ceiling.ews.latent_book": Fact(float(roc_auc_score(y, lat)), ".4f", SRC_EWS, EWS_BOOK),
        "ceiling.ews.latent_holdout": Fact(held, ".4f", SRC_EWS, EWS_HOLDOUT),
        "ceiling.ews.latent_pr_auc_holdout": Fact(
            float(average_precision_score(y[te], lat[te])), ".4f", SRC_EWS, EWS_HOLDOUT),
        "ceiling.ews.latent_capture_holdout": Fact(
            top_decile_capture(y[te], lat[te]), ".1%",
            SRC_EWS + " ranked by ews.src.train.top_decile_capture", EWS_HOLDOUT),
        "ceiling.ews.gap_holdout": Fact(held - model, ".3f",
                                        SRC_EWS + " minus the committed EWS model's AUC",
                                        EWS_HOLDOUT),
        "ceiling.ews.share_of_reach": Fact((model - 0.5) / (held - 0.5), ".0%",
                                           "(EWS AUC - 0.5) / (noise-free AUC - 0.5)",
                                           EWS_HOLDOUT),
    }


def compute_ews_oracle(es) -> dict[str, Fact]:
    """Slow (a 500-tree refit): the strongest model on OBSERVABLE columns, as
    oracle_ceiling.py trains it. Run under --full only; cached in facts.json otherwise."""
    import pandas as pd
    from lightgbm import LGBMClassifier
    from sklearn.model_selection import train_test_split
    from ews.src.feature_engineering import _cached_panel_features
    from shared.config import LEAKAGE_COLUMNS, SEED
    port, y = es.port, es.y
    X = port.merge(_cached_panel_features(), on="business_id")
    assert np.array_equal(X["business_id"].to_numpy(), port["business_id"].to_numpy())
    X = X.drop(columns=[c for c in LEAKAGE_COLUMNS + ["business_id", "net_income"]
                        if c in X.columns])
    cats = ["industry", "region", "entity_type", "loan_purpose"]
    for c in cats:
        X[c] = X[c].astype("category")
    X_tr, X_te, y_tr, y_te, _, te = train_test_split(X, y, np.arange(len(X)), test_size=0.2,
                                                     random_state=SEED, stratify=y)
    assert np.array_equal(te, es.idx_te), "oracle split no longer matches the EWS split"
    oracle = LGBMClassifier(n_estimators=500, learning_rate=0.03, num_leaves=31,
                            subsample=0.8, colsample_bytree=0.8, random_state=SEED,
                            n_jobs=-1, verbose=-1)
    oracle.fit(X_tr, y_tr, categorical_feature=cats)
    auc = float(roc_auc_score(y_te, oracle.predict_proba(X_te)[:, 1]))
    return {
        "ceiling.ews.oracle_model.auc": Fact(auc, ".4f", SRC_ORACLE, EWS_HOLDOUT),
        "ceiling.ews.oracle_model.n_columns": Fact(int(X.shape[1]), "d", SRC_ORACLE,
                                                   "module constant"),
    }


# --- D8: the line-increase label's ceiling (the DGP's li_logit without its noise term) -------
SRC_LI = ("wiki.facts.ceiling.li_latent (the DGP's line-increase logit without its N(0, 0.18) "
          "noise term and intercept)")
LI_HOLDOUT = ("held-out 20% of the booked book (line-increase split, seed 42, stratified on "
              "line_increase_good: 1,668 accounts)")


def li_latent(port, with_deterioration: bool = True) -> np.ndarray:
    """shared/data_generator.py's line_increase_good logit, noise and intercept removed (AUC is
    rank-only): the true PD, on-book utilisation above 0.5, standardised log revenue over the
    booked book, and -- an outcome realised after the decision -- deterioration.

    One input differs from the generator's: it uses portfolio.utilization_onbook, which is
    the generator's util_last3 rounded to 3 dp, because util_last3 itself is not stored. The
    rounding moves the latent by at most 7.0 x 0.0005 and only ties accounts whose
    utilisation agrees to 3 dp; its effect on a rank measure is negligible."""
    pd_true = port["pd_default_origination"].to_numpy()       # DGP truth: allowed HERE only
    util_last3 = port["utilization_onbook"].to_numpy()
    out = (-3.0 * pd_true + 7.0 * np.clip(util_last3 - 0.5, 0, None)
           + 1.2 * _z(np.log(port["annual_revenue"].to_numpy())))
    if with_deterioration:
        out = out - 0.4 * port["deterioration_next_6_12mo"].to_numpy()
    return out


def compute_li(ls) -> dict[str, Fact]:
    """ls: wiki.facts.li_facts.LiSplit (train.py's split and the committed model's prob)."""
    from line_increase.src.train import top_ventile_lift
    y, te = ls.y, ls.idx_te
    lat = li_latent(ls.port)
    lat_nd = li_latent(ls.port, with_deterioration=False)
    held = float(roc_auc_score(y[te], lat[te]))
    model = float(roc_auc_score(y[te], ls.prob[te]))
    src_nd = SRC_LI + ", without the deterioration term (what exists at decision time)"
    return {
        "ceiling.li.latent_book": Fact(float(roc_auc_score(y, lat)), ".4f", SRC_LI, EWS_BOOK),
        "ceiling.li.latent_holdout": Fact(held, ".4f", SRC_LI, LI_HOLDOUT),
        "ceiling.li.latent_lift_holdout": Fact(top_ventile_lift(y[te], lat[te]), ".2f",
                                               SRC_LI + " ranked by line_increase.src.train."
                                               "top_ventile_lift", LI_HOLDOUT),
        "ceiling.li.latent_no_det_holdout": Fact(float(roc_auc_score(y[te], lat_nd[te])), ".4f",
                                                 src_nd, LI_HOLDOUT),
        "ceiling.li.gap_holdout": Fact(held - model, ".3f",
                                       SRC_LI + " minus the committed line-increase model's AUC",
                                       LI_HOLDOUT),
        "ceiling.li.share_of_reach": Fact((model - 0.5) / (held - 0.5), ".0%",
                                          "(LI AUC - 0.5) / (noise-free AUC - 0.5)", LI_HOLDOUT),
    }
