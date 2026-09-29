"""Fast facts about the committed Business Credit Score, computed through the module's
own functions (predict_score_pd, feature_contributions, the saved scorecard)."""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

from shared.config import ROOT, SEED
from score.src.feature_engineering import CATEGORICAL, FEATURE_COLUMNS, compute_features
from score.src.predict import _load, predict_score_pd
from score.src.reason_codes import feature_contributions
from score.src.train import AUC_GATE, ks_statistic
from wiki.facts.core import Fact

HOLDOUT = "held-out 20% of applicants (score split, seed 42)"
TRAIN = "training 80% of applicants (score split, seed 42)"
ALL = "all 12,000 applicants"
BANDS = ["D", "C", "B", "A", "AAA"]
STRUCTURAL_ZEROS_IN_MODEL = ["industry", "entity_type", "trade_lines"]
BOOTSTRAP_N = 1000
SRC_PRED = "score.src.predict.predict_score_pd"


def _psi(expected: pd.Series, actual: pd.Series) -> float:
    cats = sorted(set(expected.unique()) | set(actual.unique()), key=str)
    e = expected.value_counts(normalize=True).reindex(cats, fill_value=0).clip(lower=1e-6)
    a = actual.value_counts(normalize=True).reindex(cats, fill_value=0).clip(lower=1e-6)
    return float(((a - e) * np.log(a / e)).sum())


def _vif(M: np.ndarray) -> np.ndarray:
    out = []
    for j in range(M.shape[1]):
        A = np.column_stack([np.ones(len(M)), np.delete(M, j, axis=1)])
        coef, *_ = np.linalg.lstsq(A, M[:, j], rcond=None)
        r2 = 1 - (M[:, j] - A @ coef).var() / M[:, j].var()
        out.append(1 / max(1 - r2, 1e-12))
    return np.array(out)


def compute(split) -> tuple[dict[str, Fact], dict]:
    biz, y, tr, te = split.biz, split.y, split.idx_tr, split.idx_te
    scorecard, _, _ = _load()
    bp = scorecard.binning_process_
    scored = predict_score_pd(biz)
    pd_all, band_all = scored["pd"].to_numpy(), scored["score_band"].to_numpy()
    y_te, pd_te = y[te], pd_all[te]
    X = compute_features(biz)[FEATURE_COLUMNS]
    booked = biz["booked"].to_numpy().astype(bool)
    f: dict[str, Fact] = {}

    def put(key, value, fmt, source, population):
        f[key] = Fact(value, fmt, source, population)

    put("score.n_train", int(len(tr)), ",d", "wiki.facts.data.score_split", TRAIN)
    put("score.n_test", int(len(te)), ",d", "wiki.facts.data.score_split", HOLDOUT)
    put("score.test_share", len(te) / len(biz), ".0%", "wiki.facts.data.score_split", ALL)
    put("score.n_applicants", int(len(biz)), ",d", "shared/data/raw/businesses.parquet", ALL)
    put("score.n_booked", int(booked.sum()), ",d", "businesses.booked", ALL)
    put("score.gate", float(AUC_GATE), ".2f", "score.src.train.AUC_GATE", HOLDOUT)
    put("score.auc_holdout", float(roc_auc_score(y_te, pd_te)), ".4f", SRC_PRED, HOLDOUT)
    put("score.ks_holdout", float(ks_statistic(y_te, pd_te)), ".4f",
        "score.src.train.ks_statistic", HOLDOUT)

    rng = np.random.default_rng(SEED)
    boot = [roc_auc_score(y_te[s], pd_te[s])
            for s in (rng.integers(0, len(te), len(te)) for _ in range(BOOTSTRAP_N))]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    src_boot = f"bootstrap, {BOOTSTRAP_N} resamples, seed {SEED}"
    put("score.auc_ci_lo", float(lo), ".4f", src_boot, HOLDOUT)
    put("score.auc_ci_hi", float(hi), ".4f", src_boot, HOLDOUT)
    put("score.auc_ci_half", float((hi - lo) / 2), ".2f", src_boot, HOLDOUT)
    put("score.bootstrap_n", BOOTSTRAP_N, ",d", src_boot, HOLDOUT)

    for name, mask, pop in [("everyone", np.ones(len(te), bool), HOLDOUT),
                            ("booked", booked[te], "held-out booked applicants"),
                            ("rejected", ~booked[te], "held-out rejected applicants")]:
        put(f"score.pop.{name}.auc", float(roc_auc_score(y_te[mask], pd_te[mask])), ".4f",
            SRC_PRED, pop)
        put(f"score.pop.{name}.n", int(mask.sum()), ",d", "businesses.booked", pop)
        put(f"score.pop.{name}.dr", float(y_te[mask].mean()), ".1%", "businesses.default", pop)

    rows = []
    for b in BANDS:
        m = band_all[te] == b
        n, obs, pred = int(m.sum()), float(y_te[m].mean()), float(pd_te[m].mean())
        rows.append({"band": b, "n": n, "share": n / len(te), "observed": obs, "predicted": pred})
        put(f"score.band.{b}.n", n, ",d", SRC_PRED, HOLDOUT)
        put(f"score.band.{b}.share", n / len(te), ".1%", SRC_PRED, HOLDOUT)
        put(f"score.band.{b}.observed", obs, ".1%", "businesses.default", HOLDOUT)
        put(f"score.band.{b}.predicted", pred, ".1%", SRC_PRED, HOLDOUT)
        put(f"score.band.{b}.ratio", obs / pred, ".2f", SRC_PRED, HOLDOUT)
        put(f"score.band.{b}.defaults", int(y_te[m].sum()), ",d", "businesses.default", HOLDOUT)
    put("score.band_d_share", f["score.band.D.share"].value, ".0%", SRC_PRED, HOLDOUT)

    BOOKED_HOLDOUT = "held-out booked applicants"    # the population 4.8 monitors
    bk = booked[te]
    for b in BANDS:
        m = (band_all[te] == b) & bk
        n, obs, pred = int(m.sum()), float(y_te[m].mean()), float(pd_te[m].mean())
        put(f"score.band_booked.{b}.n", n, ",d", SRC_PRED, BOOKED_HOLDOUT)
        put(f"score.band_booked.{b}.defaults", int(y_te[m].sum()), ",d", "businesses.default",
            BOOKED_HOLDOUT)
        put(f"score.band_booked.{b}.observed", obs, ".1%", "businesses.default", BOOKED_HOLDOUT)
        put(f"score.band_booked.{b}.predicted", pred, ".1%", SRC_PRED, BOOKED_HOLDOUT)
        put(f"score.band_booked.{b}.ratio", obs / pred, ".2f", SRC_PRED, BOOKED_HOLDOUT)

    idx = bp.transform(X, metric="indices")
    psi = pd.Series({c: _psi(idx[c].iloc[tr], idx[c].iloc[te]) for c in idx.columns})
    src_psi = "PSI over the scorecard's own bins, train -> test"
    put("score.psi_score", _psi(pd.Series(band_all[tr]), pd.Series(band_all[te])), ".4f",
        "PSI over score bands, train -> test", "train vs held-out applicants")
    put("score.psi_max", float(psi.max()), ".4f", src_psi, "train vs held-out applicants")
    put("score.psi_max_feature", str(psi.idxmax()), "", src_psi, "train vs held-out applicants")
    put("score.psi_n_over_010", int((psi > 0.10).sum()), "d", src_psi,
        "train vs held-out applicants")

    summary = bp.summary().set_index("name")   # optbinning 0.20.0 (pinned): summary() has
    iv = summary.loc[FEATURE_COLUMNS, "iv"].astype(float)   # a "name"/"iv" column directly
    for c, v in iv.items():
        put(f"score.iv.{c}", float(v), ".3f", "BinningProcess.summary()", TRAIN)
    put("score.n_features", len(FEATURE_COLUMNS), "d",
        "score.src.feature_engineering.FEATURE_COLUMNS", TRAIN)
    put("score.n_iv_below_002", int((iv < 0.02).sum()), "d", "BinningProcess.summary()", TRAIN)

    nonmono = []                        # WoE read in bin order, Special/Missing rows dropped
    for c in FEATURE_COLUMNS:
        if c in CATEGORICAL:            # categories have no order to be monotonic in
            continue
        with warnings.catch_warnings():   # optbinning calls a renamed sklearn argument
            warnings.simplefilter("ignore", FutureWarning)
            table = bp.get_binned_variable(c).binning_table.build()
        woe = table["WoE"].iloc[:-3].astype(float)
        d = np.diff(woe.to_numpy())
        if not ((d >= 0).all() or (d <= 0).all()):
            nonmono.append(c)
    src_mono = "BinningProcess binning tables (WoE in bin order; monotonic_trend='auto')"
    put("score.woe_nonmonotonic", ", ".join(nonmono) if nonmono else "none", "", src_mono, TRAIN)
    put("score.n_woe_nonmonotonic", len(nonmono), "d", src_mono, TRAIN)
    put("score.n_numeric", len(FEATURE_COLUMNS) - len(CATEGORICAL), "d",
        "score.src.feature_engineering.FEATURE_COLUMNS", TRAIN)

    woe_tr = bp.transform(X.iloc[tr], metric="woe")
    coef = pd.Series(scorecard.estimator_.coef_[0], index=woe_tr.columns)
    dominant = np.sign(coef).mode().iloc[0]
    opposite = [c for c, v in coef.items() if np.sign(v) != dominant]
    put("score.coef_sign", "negative" if dominant < 0 else "positive", "",
        "scorecard.estimator_.coef_", TRAIN)
    put("score.coef_opposite", ", ".join(opposite) if opposite else "none", "",
        "scorecard.estimator_.coef_", TRAIN)

    M = woe_tr.to_numpy(dtype=float)
    corr = np.abs(np.corrcoef(M, rowvar=False))
    np.fill_diagonal(corr, 0)
    i, j = np.unravel_index(np.argmax(corr), corr.shape)
    vif = _vif(M)
    put("score.corr_max", float(corr[i, j]), ".2f", "WoE correlation matrix", TRAIN)
    put("score.corr_max_pair", f"{woe_tr.columns[i]} / {woe_tr.columns[j]}", "",
        "WoE correlation matrix", TRAIN)
    put("score.vif_max", float(vif.max()), ".2f", "VIF on WoE features", TRAIN)
    put("score.vif_max_feature", str(woe_tr.columns[int(vif.argmax())]), "",
        "VIF on WoE features", TRAIN)

    contrib = feature_contributions(scorecard, X.iloc[te])
    var = contrib.var()
    share = var / var.sum()
    src_var = "score.src.reason_codes.feature_contributions (variance share)"
    for c, v in share.items():
        put(f"score.var_share.{c}", float(v), ".1%", src_var, HOLDOUT)
    put("score.var_share_structural", float(share[STRUCTURAL_ZEROS_IN_MODEL].sum()), ".1%",
        src_var, HOLDOUT)

    adj = json.loads((ROOT / "adjudication/models/metadata.json").read_text())
    put("score.benchmark_adj_auc", float(adj["metrics"]["auc"]), ".4f",
        "adjudication/models/metadata.json",
        "held-out 20% of applicants (adjudication split, seed 42, same 12,000 rows as score)")

    fpr, tpr, _ = roc_curve(y_te, pd_te)
    exhibits = {"roc": {"fpr": fpr, "tpr": tpr}, "bands": pd.DataFrame(rows),
                "psi": psi.sort_values(ascending=False), "iv": iv.sort_values(ascending=False)}
    return f, exhibits
