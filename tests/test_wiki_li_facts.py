"""D8's facts are recomputed through the line-increase module's own functions (the saved model
on compute_line_increase_features, recommended_amount, incremental_roe, candidates, segments)
on train.py's own split. They must print exactly what training recorded in
line_increase/models/metadata.json. If a pin fails, investigate the computation -- never edit
the pinned value."""
import json
import os

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from shared.config import LINE_INCREASE, ROOT

META = json.loads((ROOT / "line_increase/models/metadata.json").read_text())
REPORT = (ROOT / "line_increase/docs/validation_report.md").read_text()
FUNNEL = ("book", "prob", "pd", "amount", "roe")
CAPS = ("headroom_to_target_util", "pct_cap", "revenue_ceiling")
SENS = [(fd, n) for fd in ("offer_quantile", "max_pd_quantile", "target_util", "pct_cap",
                           "revenue_mult_cap") for n in ("down", "up")]


@pytest.fixture(scope="module")
def ls():
    os.chdir(ROOT)
    from wiki.facts.li_facts import li_split
    return li_split()


@pytest.fixture(scope="module")
def es():
    os.chdir(ROOT)
    from wiki.facts.ews_facts import ews_split
    return ews_split()


@pytest.fixture(scope="module")
def lf(ls, es):
    from wiki.facts import ceiling, li_facts
    return {**li_facts.compute(ls, es), **ceiling.compute_li(ls)}


@pytest.fixture(scope="module")
def t(lf):
    return {k: v.text() for k, v in lf.items()}


def _n(s: str) -> int:
    return int(s.replace(",", ""))


def test_headline_prints_what_metadata_recorded(t):
    m, c = META["metrics"], META["cohort"]
    assert t["li.auc"] == f"{m['auc']:.4f}" == "0.8128"
    assert t["li.lift"] == f"{m['top20_lift']:.2f}" == "2.66"       # .2f, as the report prints it
    assert t["li.base_rate"] == f"{META['base_rate']:.1%}" == "22.2%"
    assert t["li.offer_threshold"] == f"{META['offer_threshold']:.4f}" == "0.3121"
    assert t["li.offer_max_pd"] == f"{META['offer_max_pd']:.4f}" == "0.0741"
    assert t["li.n_offered"] == f"{c['n_offered']:,d}" == "95"
    assert t["li.cohort_pd"] == f"{c['cohort_pd']:.4f}" == "0.0363"
    assert t["li.book_pd"] == f"{c['book_pd']:.4f}" == "0.1171"
    assert t["li.cohort_util"] == f"{c['cohort_util']:.4f}" == "0.8371"
    assert t["li.book_util"] == f"{c['book_util']:.4f}" == "0.4714"
    assert t["li.agg_roe"] == f"{c['agg_incremental_roe']:.4f}" == "0.2153"
    assert t["li.gate.roe_hurdle"] == f"{c['roe_hurdle']:.2f}" == "0.15"
    for k in ("li.auc", "li.lift", "li.base_rate", "li.offer_threshold", "li.offer_max_pd",
              "li.n_offered", "li.cohort_pd", "li.book_pd", "li.cohort_util", "li.book_util",
              "li.agg_roe", "li.gate.roe_hurdle", "li.gate.auc_min", "li.gate.lift_min"):
        assert t[k] in REPORT, k


def test_gates_print_what_train_py_asserts(t, lf):
    g = META["gate"]
    assert lf["li.gate.auc_min"].value == g["auc_min"] and t["li.gate.auc_min"] == "0.78"
    assert lf["li.gate.lift_min"].value == g["lift_min"] and t["li.gate.lift_min"] == "2.0"
    assert lf["li.auc"].value >= g["auc_min"] and lf["li.lift"].value >= g["lift_min"]


def test_split_reproduces_train_py_sizes(t):
    assert (t["li.n_train"], t["li.n_test"], t["li.n_book"]) == ("6,668", "1,668", "8,336")
    assert (META["train_rows"], META["test_rows"]) == (6668, 1668)


def test_only_the_offer_settings_are_read_from_metadata(lf):
    """metadata.json supplies the threshold and PD ceiling (asserted equal to the recomputed
    quantiles); every metric and cohort number is recomputed."""
    srcs = {f.source for f in lf.values() if "metadata.json" in f.source}
    # the only metadata.json read: EWS's tier cutoffs, to tier the offers as the EWS screen does
    assert srcs and all(x.startswith("ews.src.watchlist.risk_tier with ews metadata.json tiers")
                        for x in srcs), srcs


def test_score_population_agrees_row_for_row(ls, lf):
    """The facts skip score_population's SHAP pass; every other column must be identical."""
    from line_increase.src import candidates as cand
    from wiki.facts.li_facts import score_book
    sp = cand.score_population()
    mine = score_book(ls, META["offer_threshold"], META["offer_max_pd"]).frame
    cols = [c for c in sp.columns if c != "top_shap_reasons"]
    assert list(mine.columns) == cols
    assert sp[cols].equals(mine[cols])
    assert int(sp["eligible"].sum()) == lf["li.n_offered"].value
    assert int((sp["recommended_amount"] > 0).sum()) == lf["li.n_amount_positive"].value
    assert cand.candidates(sp) == cand.candidates(mine)
    assert cand.segments(sp) == cand.segments(mine)


def test_eligible_not_amount_is_the_offer(t):
    """CLAUDE.md: an offer is eligible (95), not recommended_amount > 0 (1,243)."""
    assert t["li.n_offered"] == "95" and t["li.n_amount_positive"] == "1,243"
    assert _n(t["li.n_amount_positive"]) - _n(t["li.n_offered"]) == _n(t["li.n_amount_not_offered"])
    assert t["li.funnel.roe.n"] == t["li.n_offered"]


def test_funnel_adds_up(t):
    prev = None
    for s in FUNNEL:
        n = _n(t[f"li.funnel.{s}.n"])
        if prev is not None:
            assert prev - n == _n(t[f"li.funnel.{s}.dropped"]), s
            assert n <= prev
        prev = n
    assert _n(t["li.funnel.prob.n"]) == _n(t["li.clause.prob.n"])
    assert _n(t["li.clause.amount.n"]) == _n(t["li.n_amount_positive"])
    assert _n(t["li.clause.clears.n"]) == _n(t["li.econ.n_clear_amount"])


def test_threshold_is_set_on_in_sample_probabilities(t, lf):
    assert t["li.thr.share_book"] == "25.0%"         # the 0.75 quantile of the whole book
    assert lf["li.thr.share_train"].value > lf["li.thr.share_holdout"].value
    for k in ("li.whole.auc", "li.train.auc", "li.offer_threshold", "li.thr.share_train"):
        assert "in-sample" in lf[k].population, k
    for k in ("li.auc", "li.lift", "li.thr.share_holdout", "li.offers_ho.observed"):
        assert lf[k].population.startswith("held-out 20%"), k
    assert lf["li.train.auc"].value > lf["li.whole.auc"].value > lf["li.auc"].value


def test_offered_cohort_is_mostly_training_rows(t, lf):
    assert _n(t["li.offers.n_train"]) + _n(t["li.offers.n_holdout"]) == _n(t["li.n_offered"])
    assert lf["li.offers.n_train"].value > lf["li.offers.n_holdout"].value
    assert _n(t["li.served.portal.n"]) == _n(t["li.portal_n"]) == 25
    assert _n(t["li.served.page.n"]) == _n(t["li.page_n"]) == 10


def test_holdout_offer_calibration_follows_the_floor_rule(lf):
    from wiki.facts.policy import MIN_BAND_DEFAULTS, RATIO_HI, RATIO_LO
    for g in ("li.offers_ho", "li.thr_ho"):
        r = float(lf[f"{g}.ratio"].text())
        ev = lf[f"{g}.events"].value
        want = ("within tolerance" if RATIO_LO <= r <= RATIO_HI else
                "finding" if ev >= MIN_BAND_DEFAULTS else "observation (below the floor)")
        assert lf[f"{g}.status"].value == want, g


def test_three_cohort_gates_cannot_fail_one_by_construction(t, lf):
    """ROE cannot fail for any book; utilization and PD cannot fail on THIS book only."""
    cg = "li.cohort_gate"
    # utilization: an amount needs utilization above target_util (structural), and target_util
    # is above this book's mean (empirical)
    assert lf[f"{cg}.util.min_amount"].value > LINE_INCREASE["target_util"] > \
        lf["li.book_util"].value
    assert lf[f"{cg}.util.min_amount"].value <= lf[f"{cg}.util.median_amount"].value
    # PD: the ceiling is the book median (structural), below the book mean (empirical)
    assert t[f"{cg}.pd.book_median"] == t["li.offer_max_pd"]
    assert lf["li.offer_max_pd"].value < lf["li.book_pd"].value
    assert lf[f"{cg}.pd.max_offers"].value <= lf["li.offer_max_pd"].value
    # ROE: every offer clears alone, so the equity-weighted mean does
    assert lf[f"{cg}.roe.min_offers"].value >= lf["li.gate.roe_hurdle"].value
    assert (t[f"{cg}.n_cannot_fail"], t[f"{cg}.n_by_construction"], t[f"{cg}.n_on_this_book"],
            t["li.gate.n_gates"]) == ("3", "1", "2", "6")
    assert "by construction" not in lf[f"{cg}.n_on_this_book"].source


def test_offers_on_the_ews_screen_have_book_baselines(t):
    """The book columns are computed as D7's ews.tier.* / ews.trigger.* facts are."""
    committed = json.loads((ROOT / "wiki/facts/facts.json").read_text())
    for T in ("High", "Medium", "Low"):
        assert t[f"li.book.ews.{T}.share"] == committed[f"ews.tier.{T}.share"]["text"], T
    assert t["li.book.ews.any_trigger.share"] == committed["ews.trigger.any.share"]["text"]
    for k in ("high_utilization", "rising_utilization", "delinquency", "deposit_decline",
              "frequent_overdrafts"):
        assert t[f"li.book.ews.trigger.{k}.share"] == \
            committed[f"ews.trigger.{k}.share"]["text"], k
    pct = lambda k: float(t[k].rstrip("%"))
    # by tier the offers are LESS flagged than the book
    assert pct("li.offers.ews.High.share") < pct("li.book.ews.High.share")
    assert pct("li.offers.ews.high_or_medium.share") < pct("li.book.ews.high_or_medium.share")
    # the trigger excess is mostly the two utilization rules
    excess_any = pct("li.offers.ews.any_trigger.share") - pct("li.book.ews.any_trigger.share")
    excess_non = (pct("li.offers.ews.non_util_trigger.share")
                  - pct("li.book.ews.non_util_trigger.share"))
    assert excess_non < excess_any / 2
    assert pct("li.offers.ews.trigger.delinquency.share") < \
        pct("li.book.ews.trigger.delinquency.share")


def test_offer_deterioration_not_distinguishable_from_the_book(lf):
    for g in ("li.offers", "li.offers_ho"):
        assert lf[f"{g}.det.p_value"].value > 0.05, g
        book = lf["li.book.det.rate" if g == "li.offers" else "li.book_ho.det.rate"].value
        assert lf[f"{g}.det.ci_lo"].value < book < lf[f"{g}.det.ci_hi"].value, g


def test_bootstrap_vectorised_equals_a_loop(ls):
    from line_increase.src.train import top_ventile_lift
    from wiki.facts.ews_facts import _auc_with_ties, resample_counts, weighted_auc
    from wiki.facts.li_facts import weighted_lift
    y, p = ls.y[ls.idx_te], ls.prob[ls.idx_te]
    u = ls.feats["utilization_onbook"].to_numpy(dtype=float)[ls.idx_te]
    B = 40
    W = resample_counts(len(y), B, 42)
    rng = np.random.default_rng(42)
    loop = [rng.integers(0, len(y), len(y)) for _ in range(B)]
    want = np.array([[roc_auc_score(y[i], p[i]), top_ventile_lift(y[i], p[i]),
                      roc_auc_score(y[i], u[i])] for i in loop])
    got = np.column_stack([weighted_auc(y, p, W), weighted_lift(y, p, W),
                           _auc_with_ties(y, u, W)])
    assert np.abs(got - want).max() < 1e-12


def test_intervals_contain_the_point_estimates(lf):
    for k in ("auc", "lift"):
        assert lf[f"li.boot.{k}.lo"].value < lf["li." + k].value < lf[f"li.boot.{k}.hi"].value, k
    for b in ("utilization", "revenue", "pd_score", "ews"):
        assert lf[f"li.baseline.{b}.diff_lo"].value < lf[f"li.baseline.{b}.diff"].value < \
            lf[f"li.baseline.{b}.diff_hi"].value, b
        assert lf[f"li.baseline.{b}.diff_lo"].value > 0, b     # the model beats every baseline


def test_sensitivity_runs_reproduce_the_committed_cohort(ls):
    from wiki.facts.li_facts import offer_run
    r = offer_run(ls)
    c = META["cohort"]
    assert (r["threshold"], r["max_pd"]) == (META["offer_threshold"], META["offer_max_pd"])
    assert r["n"] == c["n_offered"]
    assert f"{r['agg_roe']:.4f}" == f"{c['agg_incremental_roe']:.4f}"
    # an explicit cfg equal to the committed one changes nothing
    assert offer_run(ls, cfg=dict(LINE_INCREASE))["n"] == c["n_offered"]


@pytest.mark.parametrize("field,name", SENS)
def test_sensitivity_values(t, lf, field, name):
    k = f"li.sens.{field}.{name}"
    factor = 0.9 if name == "down" else 1.1
    assert lf[f"{k}.value"].value == pytest.approx(LINE_INCREASE[field] * factor)
    assert lf[f"{k}.gates"].value in ("pass", "fail")
    assert _n(t[f"{k}.n_offered"]) > 0


def test_caps_add_up(t):
    assert sum(_n(t[f"li.caps.{c}.book"]) for c in CAPS) == _n(t["li.n_book"])
    assert sum(_n(t[f"li.caps.{c}.amount"]) for c in CAPS) == _n(t["li.n_amount_positive"])
    assert sum(_n(t[f"li.caps.{c}.offers"]) for c in CAPS) == _n(t["li.n_offered"])
    assert _n(t["li.caps.no_headroom"]) + _n(t["li.caps.rounds_to_zero"]) + \
        _n(t["li.n_amount_positive"]) == _n(t["li.n_book"])
    assert t["li.caps.n_dead"] == "0"


def test_ead_invariance_is_algebra(ls):
    """Every waterfall line is linear in EAD, so ROE = net income / equity does not move."""
    from pricing.src.engine import MarketAssumptions, profit_waterfall
    from shared.config import MARKET
    m = MarketAssumptions.from_market(MARKET)
    for pd_, rate in ((0.01, 0.08), (0.07, 0.12), (0.3, 0.05)):
        base = profit_waterfall(pd_, 1.0, rate, m)
        for ead in (0.5, 1234.0, 1e6):
            w = profit_waterfall(pd_, ead, rate, m)
            for k in ("net_income", "allocated_equity"):
                assert w[k] == pytest.approx(base[k] * ead, rel=1e-12)
            assert w["roe"] == pytest.approx(base["roe"], abs=1e-12)


def test_roe_test_is_the_pricing_test(t):
    assert t["li.econ.pricing_agree"] == t["li.n_amount_positive"]


def test_unread_config_key(t):
    assert t["li.config.unread"] == "roe_hurdle" and t["li.config.n_unread"] == "1"


def test_ceiling_is_above_the_model_on_the_same_rows(lf):
    assert lf["ceiling.li.latent_holdout"].value > lf["li.auc"].value
    assert lf["ceiling.li.latent_holdout"].population == lf["li.auc"].population
    assert lf["ceiling.li.gap_holdout"].value == pytest.approx(
        lf["ceiling.li.latent_holdout"].value - lf["li.auc"].value)


def test_dgp_truth_only_in_ceiling():
    src = (ROOT / "wiki/facts/li_facts.py").read_text()
    assert "pd_default_origination" not in src
    assert "pd_default_origination" in (ROOT / "wiki/facts/ceiling.py").read_text()


def test_inputs_and_importance(lf):
    from line_increase.src.feature_engineering import LI_FEATURE_COLUMNS
    names = {lf[f"li.importance.gain.top{i}.feature"].value for i in range(1, 6)}
    assert names <= set(LI_FEATURE_COLUMNS)
    assert lf["li.inputs.uses_ews_output"].value == "no"
    assert lf["li.inputs.headroom_identity"].value + lf["li.inputs.util_above_one"].value == \
        lf["li.n_book"].value


def test_keys_are_addressable_and_no_fact_prints_float_noise(lf):
    from wiki.facts.build_facts import KEY_SEGMENT
    for k, f in lf.items():
        assert all(KEY_SEGMENT.match(seg) for seg in k.split(".")), k
        assert f.population, k
        if isinstance(f.value, float):
            assert f.fmt, k
            assert "e-" not in f.text(), k
