"""Facts about the committed Early Warning model (D7), recomputed through the module's own
functions exactly as the platform scores the booked book (app/main.py ->
watchlist.score_population): the saved ews_model.pkl on compute_ews_features, tiered by
risk_tier with the cutoffs in metadata.json, flagged by flag_triggers, ranked by
watchlist.watchlist. The held-out split is train.py's own, re-drawn and asserted.

score_population is not called here: it also runs SHAP over all 8,336 accounts (~1.6 s), which
none of these facts needs. Instead its three ingredients (predict_proba, risk_tier,
flag_triggers) are called directly, and tests/test_wiki_ews_facts.py asserts row for row that
the result equals score_population's own tiers, triggers, probabilities and watchlist.

metadata.json is read for the tier cutoffs, exactly as score_population reads them (and they
are asserted to equal train.py's recomputed quantiles); no other number is read from it.
tests/test_wiki_ews_facts.py pins that the recomputed headline prints what training recorded.

The whole-book figures are in-sample: 80% of the booked book are the model's own training
rows. They are facts because the portal shows the whole book, never as a performance claim
(CLAUDE.md: always quote the held-out number)."""
from __future__ import annotations

import inspect
import json
import math
from dataclasses import dataclass
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

from ews.src import watchlist as wl
from ews.src.feature_engineering import EWS_FEATURE_COLUMNS, compute_ews_features
from ews.src.train import AUC_REPORT_FLOOR, CAPTURE_GATE, TARGET, top_decile_capture
from ews.src.triggers import flag_triggers
from shared.config import EWS_TRIGGERS, RAW, ROOT, SEED
from wiki.facts.core import Fact
from wiki.facts.policy import MIN_BAND_DEFAULTS, RATIO_HI, RATIO_LO
from wiki.facts.score_facts import BOOTSTRAP_N

BOOK = "booked book, all 8,336 accounts (as the portal scores it)"
HOLDOUT = "held-out 20% of the booked book (EWS split, seed 42, stratified: 1,668 accounts)"
TRAIN_IN = ("training 80% of the booked book (EWS split, seed 42), in-sample: the model was "
            "fitted on these rows")
WHOLE_IN = ("whole booked book, 8,336 accounts, in-sample: 80% are the model's own training "
            "rows, so this is not a performance measure -- quote the held-out figure")
MODULE_POP = "module constant"
POLICY_POP = "policy constant"
GATE_POP = "policy constant (gate, measured on the held-out 20% of the booked book)"

MODEL = "ews/models/ews_model.pkl"
META = "ews/models/metadata.json"
SRC_PROB = "ews_model.pkl predict_proba on compute_ews_features (as watchlist.score_population)"
SRC_SPLIT = "ews.src.train split (train_test_split, test_size 0.2, seed 42, stratified)"
SRC_CAP = "ews.src.train.top_decile_capture"
SRC_TIER = "ews.src.watchlist.risk_tier with metadata.json tiers"
SRC_CAL = "ews.src.train tier calibration (np.quantile of whole-book prob, rounded 4dp)"
SRC_TRIG = "ews.src.triggers.flag_triggers with shared.config.EWS_TRIGGERS"
SRC_WL = "ews.src.watchlist.watchlist (default top_n) over the scored book"
SRC_LABEL = "portfolio.deterioration_next_6_12mo"
SRC_IMP = "ews_model.pkl booster feature_importance"
TIERS = ["High", "Medium", "Low"]
Q_HIGH, Q_MED = 0.90, 0.70        # the quantiles train.py calibrates t_high / t_med at
TOP_FEATURES = 5

# (trigger name flag_triggers writes, fact slug, clauses: (feature, config key or None,
# what the rule compares)). DELINQUENCY's second clause is hard-coded in triggers.py: > 0.
TRIGGERS = [
    ("HIGH_UTILIZATION", "high_utilization", [("util_recent", "high_utilization", ">")]),
    ("RISING_UTILIZATION", "rising_utilization", [("util_drift", "rising_utilization", ">")]),
    ("DELINQUENCY", "delinquency", [("dpd_max", "dpd_severe", ">="), ("dpd_recent", None, ">")]),
    ("DEPOSIT_DECLINE", "deposit_decline", [("deposit_decline_pct", "deposit_decline", ">")]),
    ("FREQUENT_OVERDRAFTS", "frequent_overdrafts", [("overdraft_recent", "overdraft_recent",
                                                     ">=")]),
]
TRIGGER_FEATURES = ["util_recent", "util_drift", "dpd_max", "dpd_recent", "deposit_decline_pct",
                    "overdraft_recent"]
CFG_FMT = {"high_utilization": ".2f", "rising_utilization": ".2f", "dpd_severe": "d",
           "deposit_decline": ".2f", "overdraft_recent": "d"}
FEAT_FMT = {"util_recent": ".2f", "util_drift": ".2f", "dpd_max": ".0f", "dpd_recent": ".0f",
            "deposit_decline_pct": ".2f", "overdraft_recent": ".0f"}


@dataclass(frozen=True)
class EwsSplit:
    port: pd.DataFrame
    feats: pd.DataFrame
    y: np.ndarray
    prob: np.ndarray        # unrounded, as score_population passes it to risk_tier
    idx_tr: np.ndarray
    idx_te: np.ndarray


@lru_cache(maxsize=1)
def ews_split() -> EwsSplit:
    """train.py's split, re-drawn exactly (same X, y, seed, stratification), with the
    committed model's probabilities over the whole booked book."""
    port = pd.read_parquet(RAW / "portfolio.parquet")
    feats = compute_ews_features(port)
    X = feats[EWS_FEATURE_COLUMNS]
    y = port[TARGET].to_numpy()
    X_tr, X_te, _, _, tr, te = train_test_split(X, y, np.arange(len(X)), test_size=0.2,
                                                random_state=SEED, stratify=y)
    assert np.array_equal(X_tr.index.to_numpy(), tr) and np.array_equal(X_te.index.to_numpy(), te)
    prob = joblib.load(ROOT / MODEL).predict_proba(X)[:, 1]
    return EwsSplit(port, feats, y, prob, tr, te)


def report_sizes() -> tuple[int, int]:
    """The train / test sizes ews/docs/validation_report.md recorded at train time."""
    import re
    m = re.search(r"Train ([\d,]+) / Test ([\d,]+)",
                  (ROOT / "ews/docs/validation_report.md").read_text())
    assert m, "ews/docs/validation_report.md no longer records the split sizes"
    return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))


# --- vectorised bootstrap: a resample is a row of counts over the held-out rows ------------
def resample_counts(n: int, b: int, seed: int) -> np.ndarray:
    """(b, n) counts. One rng.integers(0, n, (b, n)) draw: the same stream as b successive
    rng.integers(0, n, n) calls, so row i is the i-th resample a loop would draw."""
    idx = np.random.default_rng(seed).integers(0, n, (b, n))
    return np.bincount((idx + np.arange(b)[:, None] * n).ravel(),
                       minlength=b * n).reshape(b, n).astype(float)


def weighted_auc(y: np.ndarray, p: np.ndarray, W: np.ndarray) -> np.ndarray:
    """roc_auc_score on each resample. Exact when no two distinct rows share a score
    (compute() asserts it), since then ties occur only between copies of one row."""
    o = np.argsort(p, kind="stable")
    yy, Wo = y[o].astype(bool), W[:, o]
    neg_below = np.cumsum(Wo * ~yy, axis=1) - Wo * ~yy
    wp, wn = (Wo * yy).sum(1), (Wo * ~yy).sum(1)
    return (Wo * yy * neg_below).sum(1) / (wp * wn)


def weighted_ap(y: np.ndarray, p: np.ndarray, W: np.ndarray) -> np.ndarray:
    """average_precision_score on each resample (same no-ties condition)."""
    o = np.argsort(-p, kind="stable")
    yy, Wo = y[o].astype(float), W[:, o]
    tp = np.cumsum(Wo * yy, axis=1)
    fp = np.cumsum(Wo * (1 - yy), axis=1)
    prec = np.divide(tp, tp + fp, out=np.zeros_like(tp), where=(tp + fp) > 0)
    return (Wo * yy * prec).sum(1) / (Wo * yy).sum(1)


def weighted_capture(y: np.ndarray, p: np.ndarray, W: np.ndarray) -> np.ndarray:
    """top_decile_capture on each resample (same no-ties condition)."""
    n = int(W[0].sum())
    k = max(1, int(round(0.10 * n)))          # as top_decile_capture sizes the decile
    o = np.argsort(-p, kind="stable")
    yy, Wo = y[o].astype(float), W[:, o]
    cw = np.cumsum(Wo, axis=1)
    take = np.clip(k - (cw - Wo), 0, Wo)
    return (take * yy).sum(1) / (Wo * yy).sum(1)


def _status(ratio: float, events: int) -> str:
    """D4's rule: a calibration miss outside the tolerance is a finding only on at least
    monitoring.min_band_defaults events (here: deteriorations); below it, an observation."""
    if RATIO_LO <= ratio <= RATIO_HI:
        return "within tolerance"
    return "finding" if events >= MIN_BAND_DEFAULTS else "observation (below the floor)"


def isolated_counts(feats: pd.DataFrame) -> dict[str, int]:
    """How many accounts each trigger clause fires on by itself: flag_triggers on a frame that
    keeps one feature and zeroes the other five (zero fires no rule)."""
    out = {}
    for name, _, clauses in TRIGGERS:
        for feat, _, _ in clauses:
            iso = pd.DataFrame(0.0, index=feats.index, columns=TRIGGER_FEATURES)
            iso[feat] = pd.to_numeric(feats[feat], errors="coerce").fillna(0.0).to_numpy()
            out[feat] = sum(name in t for t in flag_triggers(iso))
    return out


def compute(es: EwsSplit | None = None) -> dict[str, Fact]:
    es = es or ews_split()
    port, feats, y, prob, tr, te = es.port, es.feats, es.y, es.prob, es.idx_tr, es.idx_te
    meta = json.loads((ROOT / META).read_text())
    model = joblib.load(ROOT / MODEL)
    y_te, p_te = y[te], prob[te]
    assert (len(tr), len(te)) == report_sizes(), "EWS split no longer reproduces train.py's sizes"
    assert len(np.unique(p_te)) == len(p_te), "tied held-out probabilities: bootstrap not exact"
    f: dict[str, Fact] = {}

    def put(key, value, fmt, source, population):
        f[key] = Fact(value, fmt, source, population)

    base = float(y.mean())
    # --- split and headline (held out: the number to quote) ---
    put("ews.n_book", int(len(y)), ",d", SRC_SPLIT, BOOK)
    put("ews.n_train", int(len(tr)), ",d", SRC_SPLIT, TRAIN_IN)
    put("ews.n_test", int(len(te)), ",d", SRC_SPLIT, HOLDOUT)
    put("ews.n_features", len(EWS_FEATURE_COLUMNS), "d",
        "ews.src.feature_engineering.EWS_FEATURE_COLUMNS", MODULE_POP)
    put("ews.target", TARGET, "", "ews.src.train.TARGET", MODULE_POP)
    put("ews.base_rate", base, ".1%", SRC_LABEL, BOOK)
    put("ews.n_events", int(y.sum()), ",d", SRC_LABEL, BOOK)
    put("ews.base_rate_holdout", float(y_te.mean()), ".1%", SRC_LABEL, HOLDOUT)
    put("ews.n_events_holdout", int(y_te.sum()), ",d", SRC_LABEL, HOLDOUT)
    auc, pr = float(roc_auc_score(y_te, p_te)), float(average_precision_score(y_te, p_te))
    cap = top_decile_capture(y_te, p_te)
    put("ews.auc", auc, ".4f", SRC_PROB, HOLDOUT)
    put("ews.pr_auc", pr, ".4f", SRC_PROB, HOLDOUT)
    put("ews.pr_auc_over_base", pr / base, ".2f", SRC_PROB + " / base rate", HOLDOUT)
    put("ews.capture", cap, ".1%", SRC_CAP, HOLDOUT)
    put("ews.lift", cap / 0.10, ".2f", SRC_CAP + " / 0.10 (as train.py)", HOLDOUT)
    k = max(1, int(round(0.10 * len(te))))
    top = np.argsort(p_te)[::-1][:k]
    put("ews.top_k", k, ",d", SRC_CAP + " (rows in the top decile)", HOLDOUT)
    put("ews.capture_events", int(y_te[top].sum()), ",d", SRC_CAP, HOLDOUT)
    put("ews.top_decile_rate", float(y_te[top].mean()), ".1%", SRC_CAP, HOLDOUT)

    # --- gates ---
    put("ews.gate.capture_min", float(CAPTURE_GATE), ".0%", "ews.src.train.CAPTURE_GATE", GATE_POP)
    put("ews.gate.lift_min", float(CAPTURE_GATE) / 0.10, ".1f",
        "ews.src.train.CAPTURE_GATE / 0.10", GATE_POP)
    put("ews.gate.pr_auc_min", "the base rate", "", "ews.src.train (assert pr_auc > base)",
        GATE_POP)
    put("ews.gate.auc_floor", float(AUC_REPORT_FLOOR), ".2f",
        "ews.src.train.AUC_REPORT_FLOOR (sanity floor; AUC reported, not gated)", GATE_POP)
    need = math.ceil(CAPTURE_GATE * int(y_te.sum()) - 1e-9)
    put("ews.gate.capture_events_needed", need, ",d",
        "ceil(CAPTURE_GATE x held-out deteriorations)", HOLDOUT)
    put("ews.gate.capture_events_margin", int(y_te[top].sum()) - need, ",d",
        "captured minus needed deteriorations in the top decile", HOLDOUT)
    put("ews.gate.capture_margin_pp", (cap - CAPTURE_GATE) * 100, ".1f",
        "top-decile capture minus CAPTURE_GATE, percentage points", HOLDOUT)

    # --- tier cutoffs: recomputed as train.py calibrates them, checked against metadata ---
    t_high, t_med = (round(float(np.quantile(prob, q)), 4) for q in (Q_HIGH, Q_MED))
    tiers = meta["tiers"]
    assert (t_high, t_med) == (tiers["t_high"], tiers["t_med"]), \
        f"metadata.json tiers {tiers} != recomputed {t_high}/{t_med}"
    cal_pop = ("whole booked book, 8,336 accounts, in-sample probabilities (80% are training "
               "rows) -- the distribution train.py sets the cutoffs on")
    put("ews.t_high", t_high, ".4f", SRC_CAL, cal_pop)
    put("ews.t_med", t_med, ".4f", SRC_CAL, cal_pop)
    put("ews.q_high", Q_HIGH, ".0%", "ews.src.train (quantile for t_high)", POLICY_POP)
    put("ews.q_med", Q_MED, ".0%", "ews.src.train (quantile for t_med)", POLICY_POP)

    # --- bootstrap intervals, held out (vectorised; equal to a loop, tests pin it) ---
    W = resample_counts(len(te), BOOTSTRAP_N, SEED)
    src_boot = f"bootstrap, {BOOTSTRAP_N} resamples, seed {SEED}"
    boots = {"auc": weighted_auc(y_te, p_te, W), "pr_auc": weighted_ap(y_te, p_te, W),
             "capture": weighted_capture(y_te, p_te, W)}
    for name, v in boots.items():
        lo, hi = np.percentile(v, [2.5, 97.5])
        fmt = ".1%" if name == "capture" else ".4f"
        put(f"ews.boot.{name}.lo", float(lo), fmt, src_boot, HOLDOUT)
        put(f"ews.boot.{name}.hi", float(hi), fmt, src_boot, HOLDOUT)
    put("ews.boot.n", BOOTSTRAP_N, ",d", src_boot, HOLDOUT)
    below = float((boots["capture"] < CAPTURE_GATE).mean())
    put("ews.boot.capture_below_gate", below, ".1%",
        src_boot + ": share of resamples whose capture is below CAPTURE_GATE", HOLDOUT)
    put("ews.boot.pr_auc_at_or_below_base", float((boots["pr_auc"] <= base).mean()), ".1%",
        src_boot + ": share of resamples whose PR-AUC is at or below the base rate", HOLDOUT)

    # --- held out vs in-sample (the whole-book figure is not a performance measure) ---
    put("ews.whole.auc", float(roc_auc_score(y, prob)), ".4f", SRC_PROB, WHOLE_IN)
    put("ews.whole.pr_auc", float(average_precision_score(y, prob)), ".4f", SRC_PROB, WHOLE_IN)
    wcap = top_decile_capture(y, prob)
    put("ews.whole.capture", wcap, ".1%", SRC_CAP, WHOLE_IN)
    put("ews.whole.lift", wcap / 0.10, ".2f", SRC_CAP + " / 0.10", WHOLE_IN)
    put("ews.train.auc", float(roc_auc_score(y[tr], prob[tr])), ".4f", SRC_PROB, TRAIN_IN)
    put("ews.train.capture", top_decile_capture(y[tr], prob[tr]), ".1%", SRC_CAP, TRAIN_IN)

    # --- tiers over the book (what the portal shows) ---
    tier = np.array([wl.risk_tier(p, tiers) for p in prob])
    for T in TIERS:
        m = tier == T
        put(f"ews.tier.{T}.n", int(m.sum()), ",d", SRC_TIER, BOOK)
        put(f"ews.tier.{T}.share", float(m.mean()), ".1%", SRC_TIER, BOOK)
    # --- tiers on held-out rows: observed rate, calibration, lift, the floor rule ---
    t_te = tier[te]
    for T in TIERS:
        m = t_te == T
        ev = int(y_te[m].sum())
        obs, pred = float(y_te[m].mean()), float(p_te[m].mean())
        g = f"ews.tier_ho.{T}"
        put(f"{g}.n", int(m.sum()), ",d", SRC_TIER, HOLDOUT)
        put(f"{g}.share", float(m.mean()), ".1%", SRC_TIER, HOLDOUT)
        put(f"{g}.events", ev, ",d", SRC_LABEL, HOLDOUT)
        put(f"{g}.observed", obs, ".1%", SRC_LABEL, HOLDOUT)
        put(f"{g}.predicted", pred, ".1%", SRC_PROB, HOLDOUT)
        put(f"{g}.ratio", obs / pred, ".2f", SRC_PROB, HOLDOUT)
        put(f"{g}.lift", obs / base, ".2f", SRC_LABEL + " / book base rate", HOLDOUT)
        put(f"{g}.status", _status(obs / pred, ev), "",
            "wiki.facts.policy ratio tolerance and MIN_BAND_DEFAULTS (events = deteriorations)",
            HOLDOUT)
        put(f"{g}.recall", float(y_te[m].sum() / y_te.sum()), ".1%", SRC_LABEL, HOLDOUT)

    # --- triggers ---
    trig = flag_triggers(feats)
    known = {name for name, _, _ in TRIGGERS}
    unknown = {s for t in trig for s in t} - known
    assert not unknown, f"flag_triggers wrote names the facts do not know: {unknown}"
    assert set(EWS_TRIGGERS) == {c for _, _, cl in TRIGGERS for _, c, _ in cl if c}, \
        "shared.config.EWS_TRIGGERS gained or lost a threshold"
    iso = isolated_counts(feats)
    y_ev = y_te.sum()
    n_dead = n_dead_clauses = 0
    for name, slug, clauses in TRIGGERS:
        m = np.array([name in t for t in trig])
        mt = m[te]
        g = f"ews.trigger.{slug}"
        put(f"{g}.name", name, "", SRC_TRIG, MODULE_POP)
        put(f"{g}.n", int(m.sum()), ",d", SRC_TRIG, BOOK)
        put(f"{g}.share", float(m.mean()), ".1%", SRC_TRIG, BOOK)
        put(f"{g}.n_ho", int(mt.sum()), ",d", SRC_TRIG, HOLDOUT)
        prec = float(y_te[mt].mean()) if mt.any() else 0.0
        put(f"{g}.precision", prec, ".1%", SRC_TRIG + " (deterioration rate among flagged)",
            HOLDOUT)
        put(f"{g}.recall", float(y_te[mt].sum() / y_ev), ".1%",
            SRC_TRIG + " (share of deteriorations flagged)", HOLDOUT)
        put(f"{g}.lift", prec / base, ".2f", SRC_TRIG + " precision / book base rate", HOLDOUT)
        n_dead += int(m.sum() == 0)
        for feat, ck, op in clauses:
            c = f"{g}.clause.{feat}"
            put(f"{c}.feature", feat, "", "ews.src.triggers.flag_triggers", MODULE_POP)
            put(f"{c}.op", op, "", "ews.src.triggers.flag_triggers", MODULE_POP)
            if ck:
                put(f"{c}.threshold", EWS_TRIGGERS[ck], CFG_FMT[ck],
                    f"shared.config.EWS_TRIGGERS['{ck}']", POLICY_POP)
                put(f"{c}.config_key", ck, "", "shared.config.EWS_TRIGGERS", POLICY_POP)
            else:
                put(f"{c}.threshold", 0, "d", "ews.src.triggers (hard-coded, not in EWS_TRIGGERS)",
                    MODULE_POP)
                put(f"{c}.config_key", "none (hard-coded)", "", "ews.src.triggers", MODULE_POP)
            put(f"{c}.feature_max", float(feats[feat].max()), FEAT_FMT[feat],
                "compute_ews_features", BOOK)
            put(f"{c}.n_alone", int(iso[feat]), ",d",
                SRC_TRIG + " on this feature alone (the others zeroed)", BOOK)
            n_dead_clauses += int(iso[feat] == 0)
    put("ews.trigger.n_triggers", len(TRIGGERS), "d", "ews.src.triggers.flag_triggers",
        MODULE_POP)
    put("ews.trigger.n_dead", n_dead, "d", SRC_TRIG + " (triggers that fire on no account)", BOOK)
    put("ews.trigger.n_dead_clauses", n_dead_clauses, "d",
        SRC_TRIG + " (clauses that fire on no account by themselves)", BOOK)
    any_t = np.array([len(t) > 0 for t in trig])
    put("ews.trigger.any.n", int(any_t.sum()), ",d", SRC_TRIG, BOOK)
    put("ews.trigger.any.share", float(any_t.mean()), ".1%", SRC_TRIG, BOOK)
    a_te = any_t[te]
    put("ews.trigger.any.precision", float(y_te[a_te].mean()), ".1%", SRC_TRIG, HOLDOUT)
    put("ews.trigger.any.recall", float(y_te[a_te].sum() / y_ev), ".1%", SRC_TRIG, HOLDOUT)
    put("ews.trigger.none.rate", float(y_te[~a_te].mean()), ".1%",
        SRC_TRIG + " (deterioration rate with no trigger)", HOLDOUT)
    n_trig = np.array([len(t) for t in trig])
    put("ews.trigger.multi.share", float((n_trig >= 2).mean()), ".1%",
        SRC_TRIG + " (two or more triggers)", BOOK)

    # --- triggers vs the High tier (book, as the portal shows both side by side) ---
    high = tier == "High"
    put("ews.overlap.high_with_trigger.n", int((high & any_t).sum()), ",d", SRC_TRIG, BOOK)
    put("ews.overlap.high_with_trigger.share", float(any_t[high].mean()), ".1%", SRC_TRIG,
        BOOK + " -- share of High-tier accounts")
    put("ews.overlap.high_no_trigger.n", int((high & ~any_t).sum()), ",d", SRC_TRIG, BOOK)
    put("ews.overlap.triggered_not_high.n", int((~high & any_t).sum()), ",d", SRC_TRIG, BOOK)
    put("ews.overlap.triggered_not_high.share", float((~high[any_t]).mean()), ".1%", SRC_TRIG,
        BOOK + " -- share of accounts with at least one trigger")
    put("ews.overlap.low_with_trigger.n", int(((tier == "Low") & any_t).sum()), ",d", SRC_TRIG,
        BOOK)
    hn = high[te] & ~a_te
    put("ews.overlap.high_no_trigger_ho.n", int(hn.sum()), ",d", SRC_TRIG, HOLDOUT)
    put("ews.overlap.high_no_trigger_ho.events", int(y_te[hn].sum()), ",d", SRC_LABEL, HOLDOUT)

    # --- the watchlist: watchlist(df) with its default top_n, over the scored book ---
    top_n = inspect.signature(wl.watchlist).parameters["top_n"].default
    scored = scored_frame(port, prob, tier, trig)
    items = wl.watchlist(scored)
    assert len(items) == top_n
    ids = [r["business_id"] for r in items]
    pos = pd.Series(np.arange(len(port)), index=port["business_id"].astype(str)).loc[ids].to_numpy()
    in_te = np.isin(pos, te)
    put("ews.watchlist.n", len(items), ",d", SRC_WL, BOOK)
    put("ews.watchlist.top_n_default", int(top_n), ",d", "ews.src.watchlist.watchlist signature",
        MODULE_POP)
    put("ews.watchlist.high_n", sum(r["risk_tier"] == "High" for r in items), ",d", SRC_WL, BOOK)
    put("ews.watchlist.no_trigger_n", sum(not r["triggers"] for r in items), ",d", SRC_WL, BOOK)
    put("ews.watchlist.events", int(y[pos].sum()), ",d", SRC_LABEL,
        WHOLE_IN.replace("whole booked book, 8,336 accounts", "the 100 watchlist accounts"))
    put("ews.watchlist.rate", float(y[pos].mean()), ".1%", SRC_LABEL,
        WHOLE_IN.replace("whole booked book, 8,336 accounts", "the 100 watchlist accounts"))
    put("ews.watchlist.n_train", int((~in_te).sum()), ",d", SRC_SPLIT, BOOK)
    put("ews.watchlist.n_holdout", int(in_te.sum()), ",d", SRC_SPLIT, HOLDOUT)
    put("ews.watchlist.holdout_events", int(y[pos[in_te]].sum()), ",d", SRC_LABEL, HOLDOUT)
    put("ews.watchlist.holdout_rate", float(y[pos[in_te]].mean()), ".1%", SRC_LABEL,
        HOLDOUT + " -- watchlist members only")

    # --- dependence on the score ---
    pd_te = feats["pd_score"].to_numpy()[te]
    s_auc = float(roc_auc_score(y_te, pd_te))
    put("ews.pd_score.auc", s_auc, ".4f", "predict_score_pd's pd (the pd_score feature) alone",
        HOLDOUT)
    put("ews.pd_score.capture", top_decile_capture(y_te, pd_te), ".1%",
        SRC_CAP + " on pd_score alone", HOLDOUT)
    put("ews.pd_score.diff", auc - s_auc, ".4f", "EWS AUC minus pd_score AUC", HOLDOUT)
    src_pair = (f"paired bootstrap, {BOOTSTRAP_N} resamples, seed {SEED}: EWS AUC minus "
                "pd_score AUC on the same resampled rows")
    diffs = boots["auc"] - _auc_with_ties(y_te, pd_te, W)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    put("ews.pd_score.diff_lo", float(lo), ".4f", src_pair, HOLDOUT)
    put("ews.pd_score.diff_hi", float(hi), ".4f", src_pair, HOLDOUT)

    # --- feature importance (gain: what the trees' splits bought; split: how often used) ---
    gain = pd.Series(model.booster_.feature_importance("gain"), EWS_FEATURE_COLUMNS)
    split = pd.Series(model.feature_importances_, EWS_FEATURE_COLUMNS)
    for kind, s in (("gain", gain), ("split", split)):
        s = s.sort_values(ascending=False, kind="stable")
        for i, (feat, v) in enumerate(s.head(TOP_FEATURES).items(), 1):
            put(f"ews.importance.{kind}.{i}.feature", feat, "", SRC_IMP + f" ({kind})", MODULE_POP)
            put(f"ews.importance.{kind}.{i}.share", float(v / s.sum()), ".1%",
                SRC_IMP + f" ({kind}), share of total", MODULE_POP)
        put(f"ews.importance.{kind}.pd_score_rank", int(list(s.index).index("pd_score")) + 1, "d",
            SRC_IMP + f" ({kind})", MODULE_POP)
    put("ews.importance.score_gain_share",
        float((gain["pd_score"] + gain["business_score"]) / gain.sum()), ".1%",
        SRC_IMP + " (gain), pd_score + business_score", MODULE_POP)
    put("ews.importance.top_n", TOP_FEATURES, "d", "wiki.facts.ews_facts.TOP_FEATURES", MODULE_POP)
    put("ews.model.n_estimators", int(model.n_estimators), ",d", MODEL, MODULE_POP)
    put("ews.model.num_leaves", int(model.num_leaves), ",d", MODEL, MODULE_POP)
    return f


def _auc_with_ties(y: np.ndarray, p: np.ndarray, W: np.ndarray) -> np.ndarray:
    """roc_auc_score per resample for a score that may tie across rows (pd_score is
    rounded): a tied positive/negative pair counts one half, as roc_auc_score does."""
    vals, inv = np.unique(p, return_inverse=True)
    yy = y.astype(bool)
    G = len(vals)
    pos = np.zeros((W.shape[0], G)); neg = np.zeros((W.shape[0], G))
    for g_arr, mask in ((pos, yy), (neg, ~yy)):
        cols = inv[mask]
        np.add.at(g_arr.T, cols, W[:, mask].T)
    neg_below = np.cumsum(neg, axis=1) - neg
    num = (pos * (neg_below + 0.5 * neg)).sum(1)
    return num / (pos.sum(1) * neg.sum(1))


def scored_frame(port: pd.DataFrame, prob: np.ndarray, tier: np.ndarray,
                 trig: list[list[str]]) -> pd.DataFrame:
    """The columns of score_population that watchlist() reads, built the way it builds them
    (prob rounded to 4dp, index = business_id). Tests assert equality with score_population."""
    out = pd.DataFrame({"business_id": port["business_id"].astype(str).to_numpy(),
                        "industry": port["industry"].to_numpy(),
                        "prob": np.round(prob, 4), "risk_tier": list(tier), "triggers": trig})
    out.index = out["business_id"]
    return out
