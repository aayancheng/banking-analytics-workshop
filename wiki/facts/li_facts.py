"""Facts about the committed Proactive Line Increase model (D8), recomputed through the
module's own functions exactly as the platform scores the booked book (app/main.py ->
candidates.score_population): the saved line_increase_model.pkl on
compute_line_increase_features, the offer threshold and PD ceiling from metadata.json,
amount_rules.recommended_amount and amount_rules.incremental_roe per account, and
candidates() / segments() over the result. The held-out split is train.py's own, re-drawn
and asserted against an independent call and the sizes training recorded.

score_population is not called here: it also runs SHAP over all 8,336 accounts, which none
of these facts needs. scored_frame() calls its ingredients (predict_proba,
recommended_amount, incremental_roe) the way it calls them, and
tests/test_wiki_li_facts.py asserts row for row that the result equals score_population's.

metadata.json is read for the offer threshold and the PD ceiling, exactly as
score_population reads them (and both are asserted to equal train.py's recomputed
quantiles); no other number is read from it. tests/test_wiki_li_facts.py pins that the
recomputed headline prints what training recorded.

An offer is `eligible` (candidates() is the authority), never `recommended_amount > 0`.

The whole-book figures are in-sample for the candidate model: 80% of the booked book are
its own training rows. The offered cohort is drawn from the whole book, so most of its
members are training rows (counted below, as D7 counts the watchlist's)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from line_increase.src import candidates as cand
from line_increase.src.amount_rules import (incremental_exposure, incremental_roe,
                                            recommended_amount)
from line_increase.src.feature_engineering import (LI_CATEGORICAL, LI_FEATURE_COLUMNS,
                                                   compute_line_increase_features)
from line_increase.src.train import AUC_GATE, LIFT_GATE, TARGET, top_ventile_lift
from pricing.src.engine import MarketAssumptions, price_loan, profit_waterfall
from shared.config import LINE_INCREASE, MARKET, RAW, ROOT, SEED
from wiki.facts.core import Fact
from wiki.facts.ews_facts import (_auc_with_ties, _status, resample_counts, weighted_auc)
from wiki.facts.score_facts import BOOTSTRAP_N

BOOK = "booked book, all 8,336 accounts (as the portal scores it)"
HOLDOUT = ("held-out 20% of the booked book (line-increase split, seed 42, stratified on "
           "line_increase_good: 1,668 accounts)")
TRAIN_IN = ("training 80% of the booked book (line-increase split, seed 42), in-sample: the "
            "model was fitted on these rows")
WHOLE_IN = ("whole booked book, 8,336 accounts, in-sample: 80% are the model's own training "
            "rows, so this is not a performance measure -- quote the held-out figure")
OFFERS = ("the 95 offered (eligible) accounts, whole booked book: most are the model's own "
          "training rows (see li.offers.n_train)")
OFFERS_HO = HOLDOUT + " -- offered (eligible) accounts only"
AMOUNT_POS = "booked accounts with recommended_amount > 0 (eligible or not)"
MODULE_POP = "module constant"
POLICY_POP = "policy constant"
GATE_POP = "policy constant (gate, measured on the held-out 20% of the booked book)"
COHORT_GATE_POP = "policy constant (cohort gate, measured on the offered cohort vs the book)"

MODEL = "line_increase/models/line_increase_model.pkl"
META = "line_increase/models/metadata.json"
SRC_PROB = ("line_increase_model.pkl predict_proba on compute_line_increase_features "
            "(as candidates.score_population)")
SRC_SPLIT = "line_increase.src.train split (train_test_split, test_size 0.2, seed 42, stratified)"
SRC_LIFT = "line_increase.src.train.top_ventile_lift (top 20% by probability)"
SRC_LABEL = "portfolio.line_increase_good"
SRC_DET = "portfolio.deterioration_next_6_12mo (the EWS label, an observed outcome)"
SRC_DEF = "portfolio.default (an observed outcome)"
SRC_ELIG = ("candidates.score_population's eligible (prob >= offer_threshold, pd <= "
            "offer_max_pd, recommended_amount > 0, incremental_roe clears_hurdle)")
SRC_AMT = "line_increase.src.amount_rules.recommended_amount"
SRC_ROE = "line_increase.src.amount_rules.incremental_roe"
SRC_CAL = ("line_increase.src.train offer calibration (np.quantile of the whole-book "
           "probability / score PD, rounded 4dp)")
SRC_RUN = ("wiki.facts.li_facts.offer_run (train.py's cohort loop: recommended_amount and "
           "incremental_roe with the stressed setting)")
SRC_IMP = "line_increase_model.pkl booster feature_importance"
SRC_CAPS = "app.v2.li_amounts.caps (the binding cap: the lowest of the three, first on a tie)"
TOP_FEATURES = 5
PAGE_N = 10               # app/static/index.html: fetch("/api/line-increase/candidates?n=10")
SENS_STEP = 0.10          # each setting moved by +-10% (relative)
SENS_FIELDS = ["offer_quantile", "max_pd_quantile", "target_util", "pct_cap",
               "revenue_mult_cap"]
CFG_FMT = {"target_util": ".2f", "pct_cap": ".2f", "revenue_mult_cap": ".2f",
           "round_to": ",d", "offer_quantile": ".2f", "max_pd_quantile": ".2f",
           "roe_hurdle": ".2f"}
CAPS = ["headroom_to_target_util", "pct_cap", "revenue_ceiling"]
BANDS = ["D", "C", "B", "A", "AAA"]
TIERS = ["High", "Medium", "Low"]


@dataclass(frozen=True)
class LiSplit:
    port: pd.DataFrame
    feats: pd.DataFrame
    y: np.ndarray
    prob: np.ndarray        # unrounded, as score_population compares it to the threshold
    idx_tr: np.ndarray
    idx_te: np.ndarray


@lru_cache(maxsize=1)
def li_split() -> LiSplit:
    """train.py's split, re-drawn exactly (same X, y, seed, stratification), with the
    committed model's probabilities over the whole booked book."""
    port = pd.read_parquet(RAW / "portfolio.parquet")
    feats = compute_line_increase_features(port)
    X = feats[LI_FEATURE_COLUMNS]
    y = port[TARGET].to_numpy()
    _, _, _, _, tr, te = train_test_split(X, y, np.arange(len(X)), test_size=0.2,
                                          random_state=SEED, stratify=y)
    # train.py splits (X, y) alone. An independent call with exactly its arguments must put
    # the same rows on each side (X carries a RangeIndex, so its index is the row position).
    X_tr, X_te, _, _ = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    assert (np.array_equal(X_tr.index.to_numpy(), tr)
            and np.array_equal(X_te.index.to_numpy(), te)), \
        "the line-increase split no longer reproduces train.py's train_test_split(X, y, ...)"
    prob = joblib.load(ROOT / MODEL).predict_proba(X)[:, 1]
    return LiSplit(port, feats, y, prob, tr, te)


def report_sizes() -> tuple[int, int]:
    """The train / test sizes line_increase/docs/validation_report.md recorded."""
    m = re.search(r"Train ([\d,]+) / Test ([\d,]+)",
                  (ROOT / "line_increase/docs/validation_report.md").read_text())
    assert m, "line_increase/docs/validation_report.md no longer records the split sizes"
    return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))


def portal_n_default() -> int:
    m = re.search(r"def li_candidates_endpoint\(n: int = (\d+)\)",
                  (ROOT / "app/main.py").read_text())
    assert m, "app/main.py no longer defines li_candidates_endpoint(n: int = ...)"
    return int(m.group(1))


# --- the scored book, built the way score_population builds it (minus SHAP) ---------------
@dataclass(frozen=True)
class Scored:
    amount: np.ndarray
    ead: np.ndarray          # unrounded incremental_ead
    roe: np.ndarray          # unrounded incremental ROE
    net_income: np.ndarray   # unrounded incremental net income
    clears: np.ndarray
    eligible: np.ndarray
    frame: pd.DataFrame      # score_population's columns (rounded as it rounds them)


def score_book(ls: LiSplit, threshold: float, max_pd: float) -> Scored:
    port, feats, prob = ls.port, ls.feats, ls.prob
    pd_s = feats["pd_score"].to_numpy(dtype=float)
    rate = port["risk_based_rate"].to_numpy(dtype=float)
    bal = port["current_balance"].to_numpy(dtype=float)
    lim = port["credit_limit"].to_numpy(dtype=float)
    rev = port["annual_revenue"].to_numpy(dtype=float)
    util = port["utilization_onbook"].to_numpy(dtype=float)
    n = len(port)
    amt, ead, roe, ni = (np.zeros(n) for _ in range(4))
    clears, elig = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(n):
        amt[i] = recommended_amount(float(bal[i]), float(lim[i]), float(rev[i]))
        r = incremental_roe(float(pd_s[i]), amt[i], float(util[i]), float(rate[i]))
        ead[i], roe[i], ni[i], clears[i] = (r["incremental_ead"], r["roe"],
                                            r["incremental_net_income"], r["clears_hurdle"])
        elig[i] = bool(prob[i] >= threshold and pd_s[i] <= max_pd and amt[i] > 0
                       and r["clears_hurdle"])
    frame = pd.DataFrame({
        "business_id": port["business_id"].astype(str).to_numpy(),
        "industry": port["industry"].astype(str).to_numpy(),
        "score_band": feats["score_band"].astype(str).to_numpy(),
        "pd": np.round(pd_s, 4), "rate": rate, "prob": np.round(prob, 4),
        "credit_limit": lim, "current_balance": bal, "utilization_onbook": util,
        "recommended_amount": amt, "incremental_ead": np.round(ead, 2),
        "incremental_roe": np.round(roe, 4), "incremental_net_income": np.round(ni, 2),
        "clears_hurdle": clears, "eligible": elig})
    frame.index = frame["business_id"]
    return Scored(amt, ead, roe, ni, clears, elig, frame)


def offer_run(ls: LiSplit, cfg: dict = LINE_INCREASE, offer_q: float | None = None,
              max_pd_q: float | None = None,
              market: MarketAssumptions = MarketAssumptions.from_market(MARKET)) -> dict:
    """train.py's offered-cohort loop with a (possibly stressed) setting: the threshold and
    PD ceiling are the rounded quantiles train.py takes, the amount comes from
    recommended_amount(cfg=...), the economics from incremental_roe."""
    offer_q = cfg["offer_quantile"] if offer_q is None else offer_q
    max_pd_q = cfg["max_pd_quantile"] if max_pd_q is None else max_pd_q
    port, prob = ls.port, ls.prob
    pd_s = ls.feats["pd_score"].to_numpy(dtype=float)
    util = port["utilization_onbook"].to_numpy(dtype=float)
    thr = float(round(np.quantile(prob, offer_q), 4))
    max_pd = float(round(np.quantile(pd_s, max_pd_q), 4))
    bal = port["current_balance"].to_numpy(dtype=float)
    lim = port["credit_limit"].to_numpy(dtype=float)
    rev = port["annual_revenue"].to_numpy(dtype=float)
    rate = port["risk_based_rate"].to_numpy(dtype=float)
    offered = np.zeros(len(port), bool)
    net = eq = exposure = 0.0
    for i in np.nonzero((prob >= thr) & (pd_s <= max_pd))[0]:
        amt = recommended_amount(bal[i], lim[i], rev[i], cfg)
        if amt <= 0:
            continue
        r = incremental_roe(pd_s[i], amt, util[i], rate[i], market)
        if r["clears_hurdle"]:
            offered[i] = True
            net += r["incremental_net_income"]
            eq += MARKET["capital_ratio"] * r["incremental_ead"]
            exposure += r["incremental_ead"]
    n = int(offered.sum())
    return {"threshold": thr, "max_pd": max_pd, "offered": offered, "n": n,
            "agg_roe": net / eq if eq > 0 else 0.0, "exposure": exposure,
            "cohort_pd": float(pd_s[offered].mean()) if n else float("nan"),
            "cohort_util": float(util[offered].mean()) if n else float("nan")}


# --- bootstrap of the lift: top_ventile_lift on each resample, vectorised -----------------
def weighted_lift(y: np.ndarray, p: np.ndarray, W: np.ndarray) -> np.ndarray:
    """top_ventile_lift on each resample: the cut is np.quantile(p, 0.80) of the resampled
    scores (linear interpolation between the order statistics), the rows with p >= cut are
    selected, and their label rate is divided by the resample's base rate."""
    o = np.argsort(p, kind="stable")
    ps, yy, Wo = p[o], y[o].astype(float), W[:, o]
    n = int(W[0].sum())
    h = (n - 1) * 0.80
    j0, j1 = int(np.floor(h)), int(np.ceil(h))
    cw = np.cumsum(Wo, axis=1)
    v0 = ps[(cw <= j0).sum(1)]           # the j0-th (0-based) order statistic of each resample
    v1 = ps[(cw <= j1).sum(1)]
    cut = v0 + (h - j0) * (v1 - v0)
    sel = ps[None, :] >= cut[:, None]
    top = (Wo * yy * sel).sum(1) / (Wo * sel).sum(1)
    return top / ((Wo * yy).sum(1) / n)


def _caps_binding(port: pd.DataFrame) -> np.ndarray:
    from app.v2.li_amounts import caps
    out = []
    for b, l, r in port[["current_balance", "credit_limit", "annual_revenue"]].itertuples(
            index=False):
        rows = caps(float(b), float(l), float(r))
        out.append(next(c["name"] for c in rows if c["binding"]) if rows else "none")
    return np.array(out)


def compute(ls: LiSplit | None = None, es=None) -> dict[str, Fact]:
    ls = ls or li_split()
    port, feats, y, prob, tr, te = ls.port, ls.feats, ls.y, ls.prob, ls.idx_tr, ls.idx_te
    meta = json.loads((ROOT / META).read_text())
    model = joblib.load(ROOT / MODEL)
    market = MarketAssumptions.from_market(MARKET)
    y_te, p_te = y[te], prob[te]
    assert (len(tr), len(te)) == report_sizes(), \
        "line-increase split no longer reproduces train.py's sizes"
    assert len(np.unique(p_te)) == len(p_te), "tied held-out probabilities: bootstrap not exact"
    pd_s = feats["pd_score"].to_numpy(dtype=float)
    util = port["utilization_onbook"].to_numpy(dtype=float)
    f: dict[str, Fact] = {}

    def put(key, value, fmt, source, population):
        f[key] = Fact(value, fmt, source, population)

    base = float(y.mean())
    # --- split and headline (held out: the number to quote) ---
    put("li.n_book", int(len(y)), ",d", SRC_SPLIT, BOOK)
    put("li.n_train", int(len(tr)), ",d", SRC_SPLIT, TRAIN_IN)
    put("li.n_test", int(len(te)), ",d", SRC_SPLIT, HOLDOUT)
    put("li.test_share", len(te) / len(y), ".0%", SRC_SPLIT + " (test_size)", HOLDOUT)
    put("li.n_features", len(LI_FEATURE_COLUMNS), "d",
        "line_increase.src.feature_engineering.LI_FEATURE_COLUMNS", MODULE_POP)
    put("li.n_categorical", len(LI_CATEGORICAL), "d",
        "line_increase.src.feature_engineering.LI_CATEGORICAL", MODULE_POP)
    put("li.target", TARGET, "", "line_increase.src.train.TARGET", MODULE_POP)
    put("li.base_rate", base, ".1%", SRC_LABEL, BOOK)
    put("li.n_events", int(y.sum()), ",d", SRC_LABEL, BOOK)
    put("li.base_rate_holdout", float(y_te.mean()), ".1%", SRC_LABEL, HOLDOUT)
    put("li.n_events_holdout", int(y_te.sum()), ",d", SRC_LABEL, HOLDOUT)
    auc, lift = float(roc_auc_score(y_te, p_te)), top_ventile_lift(y_te, p_te)
    put("li.auc", auc, ".4f", SRC_PROB, HOLDOUT)
    put("li.lift", lift, ".2f", SRC_LIFT, HOLDOUT)
    cut = np.quantile(p_te, 0.80)
    top = p_te >= cut
    put("li.top20.n", int(top.sum()), ",d", SRC_LIFT + " (rows selected)", HOLDOUT)
    put("li.top20.events", int(y_te[top].sum()), ",d", SRC_LIFT, HOLDOUT)
    put("li.top20.rate", float(y_te[top].mean()), ".1%", SRC_LIFT, HOLDOUT)
    put("li.top20.capture", float(y_te[top].sum() / y_te.sum()), ".1%",
        SRC_LIFT + " (share of all held-out positives in the top 20%)", HOLDOUT)

    # --- gates (train.py asserts all six) ---
    put("li.gate.auc_min", float(AUC_GATE), ".2f", "line_increase.src.train.AUC_GATE", GATE_POP)
    put("li.gate.lift_min", float(LIFT_GATE), ".1f", "line_increase.src.train.LIFT_GATE",
        GATE_POP)
    put("li.gate.roe_hurdle", float(market.roe_hurdle), ".2f",
        "shared.config.MARKET['roe_hurdle'] (train.py's agg incremental ROE gate and "
        "incremental_roe's clears_hurdle)", COHORT_GATE_POP)
    put("li.gate.auc_margin", auc - AUC_GATE, ".4f", "held-out AUC minus AUC_GATE", HOLDOUT)
    put("li.gate.lift_margin", lift - LIFT_GATE, ".2f", "held-out lift minus LIFT_GATE", HOLDOUT)
    put("li.gate.n_gates", 6, "d", "line_increase.src.train.main (six GATE FAIL asserts)",
        MODULE_POP)

    # --- offer threshold and PD ceiling: recomputed as train.py calibrates them ---
    thr = float(round(np.quantile(prob, LINE_INCREASE["offer_quantile"]), 4))
    max_pd = float(round(np.quantile(pd_s, LINE_INCREASE["max_pd_quantile"]), 4))
    assert (thr, max_pd) == (meta["offer_threshold"], meta["offer_max_pd"]), \
        f"metadata.json threshold / PD ceiling != recomputed {thr} / {max_pd}"
    put("li.offer_threshold", thr, ".4f", SRC_CAL,
        "whole booked book, 8,336 accounts, in-sample probabilities (80% are training rows) "
        "-- the distribution train.py sets the threshold on")
    put("li.offer_max_pd", max_pd, ".4f", SRC_CAL,
        "whole booked book, 8,336 accounts: the scorecard's PD (predict_score_pd), the "
        "distribution train.py sets the ceiling on")
    for k in ("offer_quantile", "max_pd_quantile", "target_util", "pct_cap",
              "revenue_mult_cap", "round_to", "roe_hurdle"):
        put(f"li.config.{k}", LINE_INCREASE[k], CFG_FMT[k],
            f"shared.config.LINE_INCREASE['{k}']", POLICY_POP)
    # LINE_INCREASE['roe_hurdle'] is never read: the hurdle is incremental_roe's market's
    import line_increase.src as li_pkg
    from pathlib import Path
    srcs = "".join(p.read_text() for p in Path(li_pkg.__file__).parent.glob("*.py"))
    reads = re.findall(r"""(?:CFG|cfg|LINE_INCREASE)\[["'](\w+)["']\]""", srcs)
    unread = sorted(set(LINE_INCREASE) - set(reads))
    put("li.config.unread", ", ".join(unread) if unread else "none", "",
        "keys of shared.config.LINE_INCREASE that no file in line_increase/src reads "
        "(regex over the source)", MODULE_POP)
    put("li.config.n_unread", len(unread), "d",
        "keys of shared.config.LINE_INCREASE that no file in line_increase/src reads",
        MODULE_POP)

    # held out vs in-sample: where the threshold sits on each side of the split
    put("li.thr.share_book", float((prob >= thr).mean()), ".1%", SRC_PROB, WHOLE_IN)
    put("li.thr.share_train", float((prob[tr] >= thr).mean()), ".1%", SRC_PROB, TRAIN_IN)
    put("li.thr.share_holdout", float((p_te >= thr).mean()), ".1%", SRC_PROB, HOLDOUT)
    thr_tr = float(round(np.quantile(prob[tr], LINE_INCREASE["offer_quantile"]), 4))
    thr_te = float(round(np.quantile(p_te, LINE_INCREASE["offer_quantile"]), 4))
    put("li.thr.train_only", thr_tr, ".4f", SRC_CAL + " over the training rows only", TRAIN_IN)
    put("li.thr.holdout_only", thr_te, ".4f", SRC_CAL + " over the held-out rows only", HOLDOUT)

    # --- the scored book (score_population's columns) and the funnel ---
    sc = score_book(ls, thr, max_pd)
    run = offer_run(ls)
    assert np.array_equal(run["offered"], sc.eligible), \
        "train.py's cohort loop and score_population's eligible no longer agree"
    off = sc.eligible
    n_off = int(off.sum())
    a = prob >= thr
    b = pd_s <= max_pd
    c = sc.amount > 0
    steps = [("book", np.ones(len(y), bool), "the booked book"),
             ("prob", a, "probability >= offer_threshold"),
             ("pd", a & b, "and score PD <= offer_max_pd"),
             ("amount", a & b & c, "and recommended_amount > 0"),
             ("roe", a & b & c & sc.clears, "and the incremental ROE clears the hurdle")]
    prev = len(y)
    for slug, m, label in steps:
        put(f"li.funnel.{slug}.n", int(m.sum()), ",d", SRC_ELIG + f" -- {label}", BOOK)
        put(f"li.funnel.{slug}.share", float(m.mean()), ".1%", SRC_ELIG + f" -- {label}", BOOK)
        put(f"li.funnel.{slug}.dropped", prev - int(m.sum()), ",d",
            SRC_ELIG + f" -- removed at this step ({label})", BOOK)
        put(f"li.funnel.{slug}.label", label, "", "wiki.facts.li_facts (funnel step)", MODULE_POP)
        prev = int(m.sum())
    assert int((a & b & c & sc.clears).sum()) == n_off
    # each clause by itself, over the book
    for slug, m, src in (("prob", a, SRC_PROB), ("pd", b, "predict_score_pd's pd"),
                         ("amount", c, SRC_AMT), ("clears", sc.clears, SRC_ROE)):
        put(f"li.clause.{slug}.n", int(m.sum()), ",d", src + " (this clause alone)", BOOK)
    # the documented distinction: eligible (95) vs recommended_amount > 0 (1,243)
    offers = cand.candidates(sc.frame)
    assert len(offers) == n_off and all(o["clears_hurdle"] for o in offers)
    put("li.n_offered", n_off, ",d", "line_increase.src.candidates.candidates (len)", BOOK)
    put("li.offer_share", n_off / len(y), ".1%", "line_increase.src.candidates.candidates",
        BOOK)
    put("li.n_amount_positive", int(c.sum()), ",d", SRC_AMT + " (> 0)", BOOK)
    put("li.n_amount_not_offered", int((c & ~off).sum()), ",d",
        SRC_AMT + " (> 0) and not eligible", BOOK)
    put("li.amount_offer_ratio", c.sum() / n_off, ".1f",
        "accounts with recommended_amount > 0 per eligible account", BOOK)
    put("li.portal_n", portal_n_default(), "d",
        "app/main.py li_candidates_endpoint (default n)", MODULE_POP)
    put("li.page_n", PAGE_N, "d",
        "app/static/index.html (fetch /api/line-increase/candidates?n=10)", MODULE_POP)

    # --- the cohort (train.py's cohort gates) ---
    book_pd, book_util = float(pd_s.mean()), float(util.mean())
    put("li.book_pd", book_pd, ".4f", "predict_score_pd's pd, mean", BOOK)
    put("li.book_util", book_util, ".4f", "portfolio.utilization_onbook, mean", BOOK)
    put("li.cohort_pd", run["cohort_pd"], ".4f", "predict_score_pd's pd, mean", OFFERS)
    put("li.cohort_util", run["cohort_util"], ".4f", "portfolio.utilization_onbook, mean",
        OFFERS)
    put("li.agg_roe", run["agg_roe"], ".4f",
        "sum incremental net income / sum (capital_ratio x incremental EAD), as train.py",
        OFFERS)
    # three of the six gates hold by construction
    util_pos_min = float(util[c].min())
    put("li.construct.min_util_amount", util_pos_min, ".3f",
        "portfolio.utilization_onbook, minimum where recommended_amount > 0", AMOUNT_POS)
    put("li.construct.min_util_offers", float(util[off].min()), ".3f",
        "portfolio.utilization_onbook, minimum", OFFERS)
    put("li.construct.pd_margin", book_pd - max_pd, ".4f",
        "book mean score PD minus offer_max_pd (a cohort capped at the ceiling has a mean "
        "below it)", BOOK)
    roe_min = float(sc.roe[off].min())
    put("li.construct.min_roe_offers", roe_min, ".4f", SRC_ROE + " (minimum)", OFFERS)
    util_bc = util_pos_min > book_util            # any cohort with an amount beats the book
    pd_bc = max_pd < book_pd                      # any cohort under the ceiling beats the book
    roe_bc = bool(roe_min >= market.roe_hurdle)   # a weighted mean of clearing ROEs clears
    put("li.gate.n_by_construction", int(util_bc) + int(pd_bc) + int(roe_bc), "d",
        "cohort gates that cannot fail given the offer rules: utilization (every account with "
        "an amount is above the book mean), PD (the ceiling is below the book mean), "
        "aggregate ROE (an EAD-weighted mean of ROEs that each clear the hurdle)", BOOK)

    # --- the offered cohort: train vs held out, outcomes, the floor rule ---
    off_te = off[te]
    put("li.offers.n_train", int(off[tr].sum()), ",d", SRC_SPLIT, OFFERS)
    put("li.offers.n_holdout", int(off_te.sum()), ",d", SRC_SPLIT, OFFERS_HO)
    put("li.offers.train_share", float(off[tr].sum() / n_off), ".0%", SRC_SPLIT, OFFERS)
    put("li.offers.events", int(y[off].sum()), ",d", SRC_LABEL, OFFERS)
    put("li.offers.rate", float(y[off].mean()), ".1%", SRC_LABEL, OFFERS)
    ev = int(y_te[off_te].sum())
    obs, pred = float(y_te[off_te].mean()), float(p_te[off_te].mean())
    put("li.offers_ho.events", ev, ",d", SRC_LABEL, OFFERS_HO)
    put("li.offers_ho.observed", obs, ".1%", SRC_LABEL, OFFERS_HO)
    put("li.offers_ho.predicted", pred, ".1%", SRC_PROB, OFFERS_HO)
    put("li.offers_ho.ratio", obs / pred, ".2f", SRC_PROB, OFFERS_HO)
    put("li.offers_ho.lift", obs / base, ".2f", SRC_LABEL + " / book base rate", OFFERS_HO)
    put("li.offers_ho.status", _status(obs / pred, ev), "",
        "wiki.facts.policy ratio tolerance and MIN_BAND_DEFAULTS (events = line_increase_good "
        "outcomes)", OFFERS_HO)
    g = p_te >= thr
    ev_g = int(y_te[g].sum())
    obs_g, pred_g = float(y_te[g].mean()), float(p_te[g].mean())
    pop_g = HOLDOUT + " -- probability >= offer_threshold"
    put("li.thr_ho.n", int(g.sum()), ",d", SRC_PROB, pop_g)
    put("li.thr_ho.events", ev_g, ",d", SRC_LABEL, pop_g)
    put("li.thr_ho.observed", obs_g, ".1%", SRC_LABEL, pop_g)
    put("li.thr_ho.predicted", pred_g, ".1%", SRC_PROB, pop_g)
    put("li.thr_ho.ratio", obs_g / pred_g, ".2f", SRC_PROB, pop_g)
    put("li.thr_ho.status", _status(obs_g / pred_g, ev_g), "",
        "wiki.facts.policy ratio tolerance and MIN_BAND_DEFAULTS (events = line_increase_good "
        "outcomes)", pop_g)
    # observed outcomes the label does not measure: deterioration (the EWS label) and default
    det = port["deterioration_next_6_12mo"].to_numpy()
    dflt = port["default"].to_numpy()
    for slug, v, src in (("det", det, SRC_DET), ("default", dflt, SRC_DEF)):
        put(f"li.offers.{slug}.events", int(v[off].sum()), ",d", src, OFFERS)
        put(f"li.offers.{slug}.rate", float(v[off].mean()), ".1%", src, OFFERS)
        put(f"li.book.{slug}.rate", float(v.mean()), ".1%", src, BOOK)
        put(f"li.offers_ho.{slug}.events", int(v[te][off_te].sum()), ",d", src, OFFERS_HO)
        put(f"li.offers_ho.{slug}.rate", float(v[te][off_te].mean()), ".1%", src, OFFERS_HO)
        put(f"li.book_ho.{slug}.rate", float(v[te].mean()), ".1%", src, HOLDOUT)

    # --- the offered accounts on the EWS screen (what the portal shows beside them) ---
    if es is not None:
        from ews.src import watchlist as wl
        from ews.src.triggers import flag_triggers
        assert np.array_equal(es.port["business_id"].to_numpy(), port["business_id"].to_numpy())
        etiers = json.loads((ROOT / "ews/models/metadata.json").read_text())["tiers"]
        tier = np.array([wl.risk_tier(p, etiers) for p in es.prob])
        trig = flag_triggers(es.feats)
        pop_e = ("the 95 offered accounts, as the EWS screen tiers and flags them "
                 "(ews.src.watchlist.risk_tier, ews.src.triggers.flag_triggers)")
        for T in TIERS:
            put(f"li.offers.ews.{T}.n", int((tier[off] == T).sum()), ",d",
                "ews.src.watchlist.risk_tier with ews metadata.json tiers", pop_e)
        idx = np.nonzero(off)[0]
        put("li.offers.ews.any_trigger.n", int(sum(len(trig[i]) > 0 for i in idx)), ",d",
            "ews.src.triggers.flag_triggers (at least one)", pop_e)
        for name in ("HIGH_UTILIZATION", "RISING_UTILIZATION", "DELINQUENCY",
                     "DEPOSIT_DECLINE", "FREQUENT_OVERDRAFTS"):
            put(f"li.offers.ews.trigger.{name.lower()}.n", int(sum(name in trig[i] for i in idx)),
                ",d", f"ews.src.triggers.flag_triggers ({name})", pop_e)
        put("li.offers.ews.watchlist_n", int(sum(
            r["business_id"] in set(port["business_id"].astype(str)[off])
            for r in wl.watchlist(_ews_scored(es, tier, trig)))), ",d",
            "ews.src.watchlist.watchlist (default top_n) members that are also offered", pop_e)
        # the EWS probability as a baseline ranking for this label (lower = better candidate)
        e_te = es.prob[te]
        put("li.baseline.ews.auc", float(roc_auc_score(y_te, -e_te)), ".4f",
            "EWS model probability alone, negated (lower deterioration risk ranks higher)",
            HOLDOUT + "; the EWS model was fitted on its own split, which puts about 80% of "
            "these rows in its training data (for a different label)")
        put("li.baseline.ews.in_ews_train", float(np.isin(te, es.idx_tr).mean()), ".0%",
            "share of the line-increase held-out rows that are EWS training rows", HOLDOUT)

    # --- discrimination with uncertainty, and single-feature baselines (held out) ---
    W = resample_counts(len(te), BOOTSTRAP_N, SEED)
    src_boot = f"bootstrap, {BOOTSTRAP_N} resamples, seed {SEED}"
    boots = {"auc": weighted_auc(y_te, p_te, W), "lift": weighted_lift(y_te, p_te, W)}
    for name, v in boots.items():
        lo, hi = np.percentile(v, [2.5, 97.5])
        fmt = ".4f" if name == "auc" else ".2f"
        put(f"li.boot.{name}.lo", float(lo), fmt, src_boot, HOLDOUT)
        put(f"li.boot.{name}.hi", float(hi), fmt, src_boot, HOLDOUT)
    put("li.boot.n", BOOTSTRAP_N, ",d", src_boot, HOLDOUT)
    put("li.boot.auc_below_gate", float((boots["auc"] < AUC_GATE).mean()), ".1%",
        src_boot + ": share of resamples whose AUC is below AUC_GATE", HOLDOUT)
    put("li.boot.lift_below_gate", float((boots["lift"] < LIFT_GATE).mean()), ".1%",
        src_boot + ": share of resamples whose lift is below LIFT_GATE", HOLDOUT)

    baselines = {
        "utilization": (feats["utilization_onbook"].to_numpy(dtype=float),
                        "utilization_onbook alone (higher ranks higher)"),
        "revenue": (port["annual_revenue"].to_numpy(dtype=float),
                    "annual_revenue alone (higher ranks higher)"),
        "pd_score": (-pd_s, "predict_score_pd's pd alone, negated (lower PD ranks higher)"),
    }
    if es is not None:
        baselines["ews"] = (-es.prob, "EWS model probability alone, negated")
    for name, (x, label) in baselines.items():
        x_te = x[te]
        if name != "ews":
            put(f"li.baseline.{name}.auc", float(roc_auc_score(y_te, x_te)), ".4f", label,
                HOLDOUT)
        put(f"li.baseline.{name}.lift", top_ventile_lift(y_te, x_te), ".2f",
            SRC_LIFT + f" on {label}", HOLDOUT)
        d = boots["auc"] - _auc_with_ties(y_te, x_te, W)
        lo, hi = np.percentile(d, [2.5, 97.5])
        src_pair = (f"paired bootstrap, {BOOTSTRAP_N} resamples, seed {SEED}: model AUC minus "
                    f"{label} AUC on the same resampled rows")
        pt = auc - float(roc_auc_score(y_te, x_te))
        put(f"li.baseline.{name}.diff", pt, ".4f", "model AUC minus " + label + " AUC", HOLDOUT)
        put(f"li.baseline.{name}.diff_lo", float(lo), ".4f", src_pair, HOLDOUT)
        put(f"li.baseline.{name}.diff_hi", float(hi), ".4f", src_pair, HOLDOUT)
    # the best single numeric input, oriented (an AUC below 0.5 read the other way)
    best, best_auc = None, -1.0
    n_lift = n_num = 0
    for col in LI_FEATURE_COLUMNS:
        if col in LI_CATEGORICAL:
            continue
        x_te = feats[col].to_numpy(dtype=float)[te]
        a_ = float(roc_auc_score(y_te, x_te))
        if max(a_, 1 - a_) > best_auc + 1e-12:
            best, best_auc = col, max(a_, 1 - a_)
        n_num += 1
        n_lift += int(top_ventile_lift(y_te, x_te if a_ >= 0.5 else -x_te) >= LIFT_GATE)
    put("li.baseline.n_numeric", n_num, "d", "numeric columns of LI_FEATURE_COLUMNS", MODULE_POP)
    put("li.baseline.n_pass_lift", n_lift, "d",
        "numeric LI features that, sorted alone (oriented by their AUC), reach LIFT_GATE "
        "under top_ventile_lift", HOLDOUT)
    put("li.baseline.best.feature", best, "",
        "the numeric LI feature with the highest oriented held-out AUC (max(AUC, 1 - AUC))",
        HOLDOUT)
    put("li.baseline.best.auc", best_auc, ".4f",
        "roc_auc_score of that feature alone, oriented", HOLDOUT)

    # --- in-sample vs held out ---
    put("li.whole.auc", float(roc_auc_score(y, prob)), ".4f", SRC_PROB, WHOLE_IN)
    put("li.whole.lift", top_ventile_lift(y, prob), ".2f", SRC_LIFT, WHOLE_IN)
    put("li.train.auc", float(roc_auc_score(y[tr], prob[tr])), ".4f", SRC_PROB, TRAIN_IN)
    put("li.train.lift", top_ventile_lift(y[tr], prob[tr]), ".2f", SRC_LIFT, TRAIN_IN)

    # --- the candidates the portal serves (top of the same ranking, in-sample) ---
    pos = pd.Series(np.arange(len(port)), index=port["business_id"].astype(str))
    for slug, k in (("portal", portal_n_default()), ("page", PAGE_N)):
        sub = cand.candidates(sc.frame, top_n=k)
        sp = pos.loc[[r["business_id"] for r in sub]].to_numpy()
        popk = (f"the top {k} of candidates() (eligible accounts ranked by probability), "
                "in-sample: training rows are scored by the model fitted on them")
        src = f"line_increase.src.candidates.candidates(top_n={k})"
        put(f"li.served.{slug}.n", len(sub), ",d", src, popk)
        put(f"li.served.{slug}.n_train", int((~np.isin(sp, te)).sum()), ",d", src, popk)
        put(f"li.served.{slug}.rate", float(y[sp].mean()), ".1%", SRC_LABEL, popk)

    # --- segments(): offers by score band (the portal's summary) ---
    seg = {r["key"]: r for r in cand.segments(sc.frame)["by_band"]}
    assert set(seg) == set(BANDS), f"unexpected score bands {sorted(seg)}"
    for bnd in BANDS:
        m = (sc.frame["score_band"] == bnd).to_numpy()
        popb = f"booked book, score band {bnd}"
        put(f"li.band.{bnd}.n", seg[bnd]["count"], ",d", "line_increase.src.candidates.segments",
            popb)
        put(f"li.band.{bnd}.offers", int(off[m].sum()), ",d", SRC_ELIG, popb)
        put(f"li.band.{bnd}.offer_rate", float(off[m].mean()), ".1%",
            "line_increase.src.candidates.segments (offer_rate, unrounded)", popb)
        put(f"li.band.{bnd}.amount_positive", int(c[m].sum()), ",d", SRC_AMT + " (> 0)", popb)
        put(f"li.band.{bnd}.exposure", seg[bnd]["expected_incremental_exposure"], ",.0f",
            "line_increase.src.candidates.segments (expected_incremental_exposure)", popb)

    # --- economics among the offers ---
    put("li.econ.amount_total", float(sc.amount[off].sum()), ",.0f", SRC_AMT, OFFERS)
    put("li.econ.amount_median", float(np.median(sc.amount[off])), ",.0f", SRC_AMT, OFFERS)
    put("li.econ.exposure_total", float(sc.ead[off].sum()), ",.0f",
        "line_increase.src.amount_rules.incremental_exposure (delta x utilization)", OFFERS)
    put("li.econ.exposure_median", float(np.median(sc.ead[off])), ",.0f",
        "line_increase.src.amount_rules.incremental_exposure", OFFERS)
    put("li.econ.net_income_total", float(sc.net_income[off].sum()), ",.0f", SRC_ROE, OFFERS)
    put("li.econ.roe_min", roe_min, ".1%", SRC_ROE, OFFERS)
    put("li.econ.roe_median", float(np.median(sc.roe[off])), ".1%", SRC_ROE, OFFERS)
    put("li.econ.roe_max", float(sc.roe[off].max()), ".1%", SRC_ROE, OFFERS)
    put("li.econ.roe_mean", float(sc.roe[off].mean()), ".1%",
        SRC_ROE + " (unweighted mean)", OFFERS)
    put("li.econ.n_near_hurdle", int((sc.roe[off] < market.roe_hurdle + 0.01).sum()), ",d",
        SRC_ROE + " (offers within 1 point of the hurdle)", OFFERS)
    # EAD invariance: per loan exact (every waterfall line is linear in EAD)
    rate = port["risk_based_rate"].to_numpy(dtype=float)
    tol = 1e-12
    worst = 0.0
    for i in np.nonzero(off)[0]:
        worst = max(worst, abs(profit_waterfall(pd_s[i], sc.ead[i], rate[i], market)["roe"]
                               - profit_waterfall(pd_s[i], 1.0, rate[i], market)["roe"]))
    if not worst < tol:
        raise AssertionError(f"incremental ROE is not EAD-invariant: {worst:.3e}")
    src_bound = (" -- asserted below 1e-12 (tests/test_engine.py's tolerance) in "
                 "wiki.facts.li_facts.compute")
    put("li.econ.ead_invariance", f"< {tol:.0e}", "",
        "max over the offers of |ROE at the incremental EAD - ROE at EAD 1|" + src_bound, OFFERS)
    # the aggregate is an EAD-weighted mean: invariant to a uniform drawdown, not to its shape
    k_cap = MARKET["capital_ratio"]
    agg = run["agg_roe"]
    scaled = (sc.net_income[off] * 0.5).sum() / (k_cap * sc.ead[off] * 0.5).sum()
    if not abs(scaled - agg) < tol:
        raise AssertionError("aggregate ROE moved under a uniform drawdown scaling")
    put("li.econ.agg_uniform_invariance", f"< {tol:.0e}", "",
        "|aggregate ROE with every incremental EAD halved - aggregate ROE|" + src_bound, OFFERS)
    full_ni = full_eq = 0.0
    full_n = 0
    for i in np.nonzero(sc.amount > 0)[0]:
        ead_f = incremental_exposure(sc.amount[i], 1.0)
        w = profit_waterfall(pd_s[i], ead_f, rate[i], market)
        if (prob[i] >= thr and pd_s[i] <= max_pd and w["roe"] >= market.roe_hurdle):
            full_n += 1
            full_ni += w["net_income"]
            full_eq += k_cap * ead_f
    put("li.econ.full_draw.n_offered", full_n, ",d",
        "train.py's cohort rule with the increment fully drawn (EAD = delta)", BOOK)
    put("li.econ.full_draw.agg_roe", full_ni / full_eq, ".4f",
        "aggregate incremental ROE with the increment fully drawn (EAD = delta)", OFFERS)
    # the ROE test is the pricing test: clears_hurdle equals D6's verdict on the loan itself
    agree = 0
    for i in np.nonzero(c)[0]:
        r = price_loan(pd_s[i], float(port["requested_amount"].iloc[i]), rate[i], market)
        agree += bool(r["clears_hurdle"]) == bool(sc.clears[i])
    put("li.econ.pricing_agree", agree, ",d",
        "accounts whose incremental clears_hurdle equals pricing.src.engine.price_loan's "
        "clears_hurdle on the loan itself (requested_amount, quoted risk_based_rate)",
        AMOUNT_POS)
    put("li.econ.n_clear_amount", int((c & sc.clears).sum()), ",d", SRC_ROE, AMOUNT_POS)

    # --- sensitivity: each setting +-10% (relative), through train.py's cohort loop ---
    put("li.sens.step", SENS_STEP, ".0%", "wiki.facts.li_facts.SENS_STEP", MODULE_POP)
    for field in SENS_FIELDS:
        for name, factor in (("down", 1 - SENS_STEP), ("up", 1 + SENS_STEP)):
            v = LINE_INCREASE[field] * factor
            if field in ("offer_quantile", "max_pd_quantile"):
                r = offer_run(ls, **{"offer_q" if field == "offer_quantile" else "max_pd_q": v})
            else:
                r = offer_run(ls, cfg={**LINE_INCREASE, field: v})
            key = f"li.sens.{field}.{name}"
            src = SRC_RUN + f" with LINE_INCREASE's {field} x {factor:.2f}"
            pop = BOOK + f" -- {field} x {factor:.2f}"
            put(f"{key}.value", v, ".3f", src, POLICY_POP)
            put(f"{key}.n_offered", r["n"], ",d", src, pop)
            put(f"{key}.agg_roe", r["agg_roe"], ".4f", src, pop)
            put(f"{key}.cohort_pd", r["cohort_pd"], ".4f", src, pop)
            put(f"{key}.cohort_util", r["cohort_util"], ".4f", src, pop)
            put(f"{key}.exposure", r["exposure"], ",.0f", src, pop)
            ok = (r["n"] > 0 and r["cohort_pd"] < book_pd and r["cohort_util"] > book_util
                  and r["agg_roe"] >= market.roe_hurdle)
            put(f"{key}.gates", "pass" if ok else "fail", "", src + " (the four cohort gates)",
                pop)
    assert abs(run["exposure"] - float(sc.ead[off].sum())) < 1e-6

    # --- the amount caps: which one binds ---
    bind = _caps_binding(port)
    n_dead = 0
    for cap in CAPS:
        put(f"li.caps.{cap}.book", int((bind == cap).sum()), ",d", SRC_CAPS, BOOK)
        put(f"li.caps.{cap}.amount", int((bind[c] == cap).sum()), ",d", SRC_CAPS, AMOUNT_POS)
        put(f"li.caps.{cap}.offers", int((bind[off] == cap).sum()), ",d", SRC_CAPS, OFFERS)
        n_dead += int((bind[c] == cap).sum() == 0)
    put("li.caps.n_dead", n_dead, "d", SRC_CAPS + " (caps that bind on no account with an amount)",
        AMOUNT_POS)
    bal = port["current_balance"].to_numpy(dtype=float)
    lim = port["credit_limit"].to_numpy(dtype=float)
    rev = port["annual_revenue"].to_numpy(dtype=float)
    min_cap = np.minimum.reduce([bal / LINE_INCREASE["target_util"] - lim,
                                 LINE_INCREASE["pct_cap"] * lim,
                                 LINE_INCREASE["revenue_mult_cap"] * rev - lim])
    put("li.caps.no_headroom", int((min_cap <= 0).sum()), ",d",
        SRC_AMT + " (the lowest cap is <= 0: amount 0)", BOOK)
    put("li.caps.rounds_to_zero", int(((min_cap > 0) & ~c).sum()), ",d",
        SRC_AMT + " (a positive lowest cap that rounds to 0)", BOOK)
    put("li.caps.revenue_negative", int((LINE_INCREASE["revenue_mult_cap"] * rev - lim <= 0).sum()),
        ",d", SRC_AMT + " (revenue ceiling <= 0: the limit already exceeds revenue_mult_cap x "
        "revenue)", BOOK)

    # --- inputs and importance ---
    from ews.src.feature_engineering import EWS_FEATURE_COLUMNS
    shared_ews = [x for x in LI_FEATURE_COLUMNS if x in EWS_FEATURE_COLUMNS]
    put("li.inputs.n_shared_ews", len(shared_ews), "d",
        "LI_FEATURE_COLUMNS also in EWS_FEATURE_COLUMNS", MODULE_POP)
    put("li.inputs.shared_ews", ", ".join(shared_ews), "",
        "LI_FEATURE_COLUMNS also in EWS_FEATURE_COLUMNS", MODULE_POP)
    put("li.inputs.from_score", "pd_score", "",
        "line_increase.src.feature_engineering (predict_score_pd's pd)", MODULE_POP)
    put("li.inputs.uses_ews_output", "no", "",
        "line_increase.src.feature_engineering (no EWS probability, tier or trigger)",
        MODULE_POP)
    hr = feats["util_headroom"].to_numpy(dtype=float)
    put("li.inputs.headroom_identity", int(np.isclose(hr, 1 - util, atol=5e-5).sum()), ",d",
        "rows where util_headroom == 1 - utilization_onbook (it is clipped at 0 elsewhere)", BOOK)
    put("li.inputs.util_above_one", int((util > 1).sum()), ",d",
        "portfolio.utilization_onbook > 1 (util_headroom clipped to 0)", BOOK)
    lr = feats["log_revenue"].to_numpy(dtype=float)
    order_same = bool(np.all(np.diff(lr[np.argsort(rev, kind="stable")]) >= 0))
    put("li.inputs.log_revenue_monotone", "yes" if order_same else "no", "",
        "log_revenue never decreases as annual_revenue increases (trees split both alike)",
        BOOK)
    gain = pd.Series(model.booster_.feature_importance("gain"), LI_FEATURE_COLUMNS)
    split = pd.Series(model.feature_importances_, LI_FEATURE_COLUMNS)
    for kind, s in (("gain", gain), ("split", split)):
        s = s.sort_values(ascending=False, kind="stable")
        for i, (feat, v) in enumerate(s.head(TOP_FEATURES).items(), 1):
            put(f"li.importance.{kind}.top{i}.feature", feat, "", SRC_IMP + f" ({kind})",
                MODULE_POP)
            put(f"li.importance.{kind}.top{i}.share", float(v / s.sum()), ".1%",
                SRC_IMP + f" ({kind}), share of total", MODULE_POP)
        put(f"li.importance.{kind}.pd_score_rank", int(list(s.index).index("pd_score")) + 1, "d",
            SRC_IMP + f" ({kind})", MODULE_POP)
    put("li.importance.pair_gain_share",
        float((gain["utilization_onbook"] + gain["util_headroom"]) / gain.sum()), ".1%",
        SRC_IMP + " (gain), utilization_onbook + util_headroom", MODULE_POP)
    put("li.importance.revenue_gain_share",
        float((gain["annual_revenue"] + gain["log_revenue"]) / gain.sum()), ".1%",
        SRC_IMP + " (gain), annual_revenue + log_revenue", MODULE_POP)
    put("li.importance.top_n", TOP_FEATURES, "d", "wiki.facts.li_facts.TOP_FEATURES", MODULE_POP)
    put("li.model.n_estimators", int(model.n_estimators), ",d", MODEL, MODULE_POP)
    put("li.model.num_leaves", int(model.num_leaves), ",d", MODEL, MODULE_POP)
    return f


def _ews_scored(es, tier, trig) -> pd.DataFrame:
    from wiki.facts.ews_facts import scored_frame
    return scored_frame(es.port, es.prob, tier, trig)
