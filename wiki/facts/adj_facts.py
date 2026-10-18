"""Facts about the committed Loan Adjudication model and policy, recomputed through the
module's own functions exactly as the platform scores it (app/main.py): load the saved
LightGBM, build features with compute_adjudication_features, predict PD, and decide with
policy.decide + PolicyConfig.from_dict(policy_config.json).

metadata.json is not read for any number. tests/test_wiki_adj_facts.py pins that the
recomputed values print identically to what training recorded there."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from adjudication.src.feature_engineering import (
    ADJ_FEATURE_COLUMNS, compute_adjudication_features,
)
from adjudication.src.policy import PolicyConfig, decide
from adjudication.src.reason_codes import top_adverse_shap
from adjudication.src.train import AUC_GATE, LIFT_GATE, top_ventile_lift
from shared.config import MARKET, ROOT, SEED
from wiki.facts.core import Fact
from wiki.facts.score_facts import BOOTSTRAP_N

HOLDOUT = "held-out 20% of applicants (adjudication split, seed 42, same 12,000 rows as score)"
BOOKED = "held-out booked applicants (adjudication split, seed 42)"
REJECTED = "held-out rejected applicants (adjudication split, seed 42)"
DECLINES = "held-out Declines (adjudication split, seed 42)"
TRAIN = "training 80% of applicants (adjudication split, seed 42)"
ALL = "all 12,000 applicants"
POLICY_POP = "policy constant"
MODULE_POP = "module constant"
TRAIN_INSAMPLE = ("training 80% of applicants, in-sample model PDs (the model was fitted on "
                  "these rows, so their PDs spread wider than out-of-sample ones: the 55% "
                  "quantile is biased low); not an out-of-sample recalibration")
HIT = " -- rule hits: a file is counted when the rule fires, whatever decide() finally returns"
OV_HIT = (" -- rule hits: an override fires only on a PD-zone Approve, and a knockout on the "
          "same file still makes it a Decline")

MODEL = "adjudication/models/adjudication_model.pkl"
POLICY = "adjudication/models/policy_config.json"
SRC_PD = "adjudication_model.pkl predict_proba on compute_adjudication_features"
SRC_DECIDE = "adjudication.src.policy.decide"
SRC_SPLIT = "adjudication.src.train split (train_test_split, seed 42, stratified)"
SRC_LIFT = "adjudication.src.train.top_ventile_lift"
SRC_CAL = "adjudication.src.train calibration (np.quantile of model PD, rounded 4dp)"
SRC_HITS = "adjudication.src.policy.decide (rule hits read from decision_reasons)"
SRC_SHAP = "shap.TreeExplainer + adjudication.src.reason_codes.top_adverse_shap"
DECISIONS = ["Approve", "Refer", "Decline"]
Q_LOW, Q_HIGH = 0.55, 0.90        # the quantiles train.py calibrates t_low / t_high at
SENS_STEP = 0.10                  # cutoff sensitivity: each threshold moved by +-10%

# Each policy rule, keyed for facts, with the decision_reasons string decide() writes.
def _rules(c: PolicyConfig) -> dict[str, tuple[str, str]]:
    return {
        "dscr_floor": ("knockout", f"dscr<{c.dscr_floor}"),
        "public_records": ("knockout", "public_records present"),
        "prior_delinquencies": ("knockout", f"prior_delinquencies>={c.prior_delinq_cap}"),
        "leverage": ("knockout", f"leverage>{c.leverage_cap}"),
        "thin_dscr": ("override", "thin affordability margin (dscr)"),
        "weak_score": ("override", "weak credit score"),
        "large_request": ("override", "large request vs revenue"),
    }


def _zone(p: np.ndarray, c: PolicyConfig) -> np.ndarray:
    """The PD-zone rule alone (decide() step 2), without knockouts or overrides."""
    return np.where(p <= c.t_low, "Approve", np.where(p >= c.t_high, "Decline", "Refer"))


def lift_top_share() -> float:
    """The share of files top_ventile_lift actually ranks as its top group, measured on
    the function rather than read from its name: one default on the riskiest of n rows
    gives lift n/k, so the share k/n is 1/lift."""
    n = 10_000
    y = np.zeros(n); y[-1] = 1
    return 1 / top_ventile_lift(y, np.arange(n, dtype=float))


def compute(split) -> dict[str, Fact]:
    biz, y = split.biz, split.y
    X_all = compute_adjudication_features(biz)
    X = X_all[ADJ_FEATURE_COLUMNS]
    _, _, _, _, tr, te = train_test_split(X, y, np.arange(len(X)), test_size=0.2,
                                          random_state=SEED, stratify=y)
    assert np.array_equal(tr, split.idx_tr) and np.array_equal(te, split.idx_te), \
        "adjudication's split no longer matches the score split"

    model = joblib.load(ROOT / MODEL)
    cfg = PolicyConfig.from_dict(json.loads((ROOT / POLICY).read_text()))
    p_all = model.predict_proba(X)[:, 1]
    p_te, y_te = p_all[te], y[te]
    booked = biz["booked"].to_numpy().astype(bool)[te]
    dec = decide(X_all.iloc[te], p_te, cfg)
    d = dec["decision"].to_numpy()
    reasons = dec["decision_reasons"].tolist()
    f: dict[str, Fact] = {}

    def put(key, value, fmt, source, population):
        f[key] = Fact(value, fmt, source, population)

    # --- split, gates, headline ---
    put("adj.n_train", int(len(tr)), ",d", SRC_SPLIT, TRAIN)
    put("adj.n_test", int(len(te)), ",d", SRC_SPLIT, HOLDOUT)
    put("adj.n_applicants", int(len(biz)), ",d", SRC_SPLIT, ALL)
    put("adj.test_share", len(te) / len(biz), ".0%", SRC_SPLIT, ALL)
    put("adj.n_features", len(ADJ_FEATURE_COLUMNS), "d",
        "adjudication.src.feature_engineering.ADJ_FEATURE_COLUMNS", MODULE_POP)
    put("adj.gate_auc", float(AUC_GATE), ".2f", "adjudication.src.train.AUC_GATE",
        POLICY_POP + " (gate, measured on the held-out 20% of applicants)")
    put("adj.gate_lift", float(LIFT_GATE), ".1f", "adjudication.src.train.LIFT_GATE",
        POLICY_POP + " (gate, measured on the held-out 20% of applicants)")
    put("adj.auc", float(roc_auc_score(y_te, p_te)), ".4f", SRC_PD, HOLDOUT)
    put("adj.lift", top_ventile_lift(y_te, p_te), ".2f", SRC_LIFT, HOLDOUT)
    put("adj.lift_top_share", lift_top_share(), ".0%", SRC_LIFT,
        "measured on the function (one default among 10,000 ranked rows)")
    put("adj.lift_function", "top_ventile_lift", "", SRC_LIFT, "function name")
    put("market.roe_hurdle", float(MARKET["roe_hurdle"]), ".0%", "shared.config.MARKET",
        "platform assumption")

    # --- thresholds: recomputed as train.py calibrates them, checked against the config ---
    t_low, t_high = (round(float(np.quantile(p_all, q)), 4) for q in (Q_LOW, Q_HIGH))
    assert (t_low, t_high) == (cfg.t_low, cfg.t_high), \
        f"policy_config.json thresholds {cfg.t_low}/{cfg.t_high} != recomputed {t_low}/{t_high}"
    put("adj.t_low", t_low, ".4f", SRC_CAL, ALL)
    put("adj.t_high", t_high, ".4f", SRC_CAL, ALL)
    put("adj.q_low", Q_LOW, ".0%", "adjudication.src.train (quantile for t_low)", POLICY_POP)
    put("adj.q_high", Q_HIGH, ".0%", "adjudication.src.train (quantile for t_high)", POLICY_POP)
    for k, fmt in [("dscr_floor", ".1f"), ("dscr_refer_hi", ".1f"),
                   ("public_records_cap", "d"), ("prior_delinq_cap", "d"),
                   ("leverage_cap", ".1f"), ("req_to_rev_cap", ".2f"), ("score_floor", "d")]:
        v = getattr(cfg, k)
        put(f"adj.policy.{k}", int(v) if fmt == "d" else float(v), fmt, POLICY, POLICY_POP)

    for k in DECISIONS:
        put(f"adj.mix.{k}", float((d == k).mean()), ".1%", SRC_DECIDE, HOLDOUT)

    # --- discrimination: interval, populations ---
    rng = np.random.default_rng(SEED)
    boot = [roc_auc_score(y_te[s], p_te[s])
            for s in (rng.integers(0, len(te), len(te)) for _ in range(BOOTSTRAP_N))]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    src_boot = f"bootstrap, {BOOTSTRAP_N} resamples, seed {SEED}"
    put("adj.auc_ci_lo", float(lo), ".4f", src_boot, HOLDOUT)
    put("adj.auc_ci_hi", float(hi), ".4f", src_boot, HOLDOUT)
    put("adj.auc_ci_half", float((hi - lo) / 2), ".2f", src_boot, HOLDOUT)

    pops = [("everyone", np.ones(len(te), bool), HOLDOUT), ("booked", booked, BOOKED),
            ("rejected", ~booked, REJECTED)]
    for name, m, pop in pops:
        put(f"adj.pop.{name}.n", int(m.sum()), ",d", "businesses.booked", pop)
        put(f"adj.pop.{name}.dr", float(y_te[m].mean()), ".1%", "businesses.default", pop)
        put(f"adj.pop.{name}.auc", float(roc_auc_score(y_te[m], p_te[m])), ".4f", SRC_PD, pop)
        put(f"adj.pop.{name}.lift", top_ventile_lift(y_te[m], p_te[m]), ".2f", SRC_LIFT, pop)

    # --- decisions by population: mix, observed default rate, mean PD (items 2, 3) ---
    for name, m, pop in pops:
        for k in DECISIONS:
            mk = m & (d == k)
            put(f"adj.dec.{name}.{k}.n", int(mk.sum()), ",d", SRC_DECIDE, pop)
            put(f"adj.dec.{name}.{k}.share", float(mk.sum() / m.sum()), ".1%", SRC_DECIDE, pop)
            put(f"adj.dec.{name}.{k}.defaults", int(y_te[mk].sum()), ",d",
                "businesses.default", pop)
            put(f"adj.dec.{name}.{k}.dr", float(y_te[mk].mean()), ".1%",
                "businesses.default", pop)
            put(f"adj.dec.{name}.{k}.pd", float(p_te[mk].mean()), ".1%", SRC_PD, pop)

    # --- calibration by PD zone alone (item 8) ---
    z = _zone(p_te, cfg)
    # the zone shares the calibration aims at, by construction, over the rows it ran on
    for k, v in [("Approve", Q_LOW), ("Refer", Q_HIGH - Q_LOW), ("Decline", 1 - Q_HIGH)]:
        put(f"adj.zone_target.{k}", v, ".0%",
            "adjudication.src.train calibration quantiles (55% / 90%)",
            "policy constant (share of all 12,000 applicants' PDs in each zone, by construction)")
    for name, m, pop in pops[:2]:
        for k in DECISIONS:
            mk = m & (z == k)
            obs, pred = float(y_te[mk].mean()), float(p_te[mk].mean())
            put(f"adj.zone.{name}.{k}.n", int(mk.sum()), ",d", SRC_PD, pop)
            put(f"adj.zone.{name}.{k}.share", float(mk.sum() / m.sum()), ".1%", SRC_PD, pop)
            put(f"adj.zone.{name}.{k}.defaults", int(y_te[mk].sum()), ",d",
                "businesses.default", pop)
            put(f"adj.zone.{name}.{k}.observed", obs, ".1%", "businesses.default", pop)
            put(f"adj.zone.{name}.{k}.predicted", pred, ".1%", SRC_PD, pop)
            put(f"adj.zone.{name}.{k}.ratio", obs / pred, ".2f", SRC_PD, pop)

    # --- rule hits from decide()'s reason strings (item 2) ---
    rules = _rules(cfg)
    for key, (kind, text) in rules.items():
        hit = np.array([text in r for r in reasons])
        pop_hit = HOLDOUT + (OV_HIT if kind == "override" else HIT)
        put(f"adj.rule.{key}.n", int(hit.sum()), ",d", SRC_HITS, pop_hit)
        put(f"adj.rule.{key}.share", float(hit.mean()), ".1%", SRC_HITS, pop_hit)
        put(f"adj.rule.{key}.text", text, "", SRC_DECIDE, POLICY_POP)
        put(f"adj.rule.{key}.kind", kind, "", "adjudication.src.policy (decision order)",
            POLICY_POP)
    # the same rules over every applicant: a rule that never fires anywhere is inert
    reasons_all = decide(X_all, p_all, cfg)["decision_reasons"].tolist()
    for key, (kind, text) in rules.items():
        put(f"adj.rule.{key}.n_all", sum(text in r for r in reasons_all), ",d", SRC_HITS,
            ALL + (OV_HIT if kind == "override" else HIT))
    rev = np.maximum(X_all["annual_revenue"].to_numpy(dtype=float), 1.0)
    put("adj.max_req_to_rev", float((X_all["requested_amount"].to_numpy(dtype=float) / rev).max()),
        ".2f", "requested_amount / annual_revenue, as decide() computes it", ALL)
    put("adj.max_leverage", float(X_all["leverage"].max()), ".2f", "businesses.leverage", ALL)
    known = {t for _, t in rules.values()}
    unknown = {s for r in reasons for s in r} - known
    assert not unknown, f"decide() wrote reason strings the facts do not know: {unknown}"
    ko_texts = {t for kind, t in rules.values() if kind == "knockout"}
    ov_texts = known - ko_texts
    any_ko = np.array([bool(ko_texts & set(r)) for r in reasons])
    any_ov = np.array([bool(ov_texts & set(r)) for r in reasons])
    put("adj.rule.any_knockout.n", int(any_ko.sum()), ",d", SRC_HITS, HOLDOUT + HIT)
    put("adj.rule.any_knockout.share", float(any_ko.mean()), ".1%", SRC_HITS, HOLDOUT + HIT)
    put("adj.rule.any_override.n", int(any_ov.sum()), ",d", SRC_HITS, HOLDOUT + OV_HIT)
    put("adj.rule.any_override.share", float(any_ov.mean()), ".1%", SRC_HITS, HOLDOUT + OV_HIT)
    any_hit = np.array([len(r) > 0 for r in reasons])
    put("adj.rule.any.n", int(any_hit.sum()), ",d", SRC_HITS, HOLDOUT + HIT)
    # a knockout that overturned the PD zone: zone said Approve or Refer, decide() said Decline
    put("adj.rule.knockout_overturns.n", int((any_ko & (z != "Decline")).sum()), ",d",
        SRC_DECIDE, HOLDOUT)

    # --- cutoff sensitivity (item 4) ---
    for name, field, factor in [("t_low_down", "t_low", 1 - SENS_STEP),
                                ("t_low_up", "t_low", 1 + SENS_STEP),
                                ("t_high_down", "t_high", 1 - SENS_STEP),
                                ("t_high_up", "t_high", 1 + SENS_STEP)]:
        c2 = replace(cfg, **{field: getattr(cfg, field) * factor})
        d2 = decide(X_all.iloc[te], p_te, c2)["decision"].to_numpy()
        src = f"{SRC_DECIDE} with {field} x {factor:.2f}"
        put(f"adj.sens.{name}.t", float(getattr(c2, field)), ".4f", src, POLICY_POP)
        for k in DECISIONS:
            put(f"adj.sens.{name}.{k}", float((d2 == k).mean()), ".1%", src, HOLDOUT)
        put(f"adj.sens.{name}.changed", int((d2 != d).sum()), ",d", src, HOLDOUT)
    put("adj.sens.step", SENS_STEP, ".0%", "wiki.facts.adj_facts.SENS_STEP", POLICY_POP)

    # --- business_score and pd_score carry one signal: the score never rises with the PD ---
    o = np.argsort(X_all["pd_score"].to_numpy(), kind="stable")
    put("adj.score_pd.order_breaks", int((np.diff(X_all["business_score"].to_numpy()[o]) > 0).sum()),
        ",d", "predict_score_pd: business_score in ascending pd order, rises counted", ALL)

    # --- agreement with the scorecard's PD, zone rule alone (item 5) ---
    z_score = _zone(X_all["pd_score"].to_numpy()[te], cfg)
    src_agree = "PD-zone rule on predict_score_pd's pd vs the LightGBM PD"
    put("adj.score_zone.differ.n", int((z_score != z).sum()), ",d", src_agree, HOLDOUT)
    put("adj.score_zone.differ.share", float((z_score != z).mean()), ".1%", src_agree, HOLDOUT)
    opposite = ((z_score == "Approve") & (z == "Decline")) | \
               ((z_score == "Decline") & (z == "Approve"))
    put("adj.score_zone.opposite.n", int(opposite.sum()), ",d", src_agree, HOLDOUT)

    # --- reasons on the held-out Declines (item 6) ---
    dm = d == "Decline"
    n_dec = int(dm.sum())
    put("adj.decline.n", n_dec, ",d", SRC_DECIDE, DECLINES)
    put("adj.decline.rule_share", float(any_hit[dm].mean()), ".1%", SRC_HITS, DECLINES + HIT)
    put("adj.decline.knockout_share", float(any_ko[dm].mean()), ".1%", SRC_HITS,
        DECLINES + HIT)
    by_text = {t: k for k, (_, t) in rules.items()}
    rule_counts = Counter(s for r, m in zip(reasons, dm) if m for s in r)
    top_rules = sorted(rule_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    for i, (text, n) in enumerate(top_rules, 1):
        pop_d = DECLINES + (OV_HIT if text in ov_texts else HIT)
        put(f"adj.decline.rule{i}.reason", text, "", SRC_HITS, pop_d)
        put(f"adj.decline.rule{i}.key", by_text[text], "", SRC_HITS, pop_d)
        put(f"adj.decline.rule{i}.n", int(n), ",d", SRC_HITS, pop_d)
        put(f"adj.decline.rule{i}.share", n / n_dec, ".1%", SRC_HITS, pop_d)

    sv = shap.TreeExplainer(model).shap_values(X.iloc[te][dm])
    sv = sv[1] if isinstance(sv, list) else sv          # as train.py handles it
    top = top_adverse_shap(sv, ADJ_FEATURE_COLUMNS, k=3)
    feat_counts = Counter(r["feature"] for row in top for r in row)
    for i, (feat, n) in enumerate(sorted(feat_counts.items(),
                                         key=lambda kv: (-kv[1], kv[0]))[:3], 1):
        put(f"adj.decline.shap{i}.feature", feat, "", SRC_SHAP, DECLINES)
        put(f"adj.decline.shap{i}.n", int(n), ",d", SRC_SHAP, DECLINES)
        put(f"adj.decline.shap{i}.share", n / n_dec, ".1%", SRC_SHAP, DECLINES)

    # --- candidate finding: thresholds calibrated on rows that include the held-out (7a) ---
    tr_low, tr_high = (round(float(np.quantile(p_all[tr], q)), 4) for q in (Q_LOW, Q_HIGH))
    src_tr = SRC_CAL + " applied to the in-sample PDs of the training rows only"
    put("adj.trainonly.t_low", tr_low, ".4f", src_tr, TRAIN_INSAMPLE)
    put("adj.trainonly.t_high", tr_high, ".4f", src_tr, TRAIN_INSAMPLE)
    c3 = replace(cfg, t_low=tr_low, t_high=tr_high)
    d3 = decide(X_all.iloc[te], p_te, c3)["decision"].to_numpy()
    src3 = (f"{SRC_DECIDE} with thresholds from in-sample training-row PDs only "
            "(not an out-of-sample recalibration)")
    for k in DECISIONS:
        put(f"adj.trainonly.mix.{k}", float((d3 == k).mean()), ".1%", src3, HOLDOUT)
    put("adj.trainonly.changed", int((d3 != d).sum()), ",d", src3, HOLDOUT)
    return f
