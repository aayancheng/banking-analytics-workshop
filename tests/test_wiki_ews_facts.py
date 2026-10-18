"""D7's facts are recomputed through the EWS module's own functions (the saved model on
compute_ews_features, risk_tier, flag_triggers, watchlist) on train.py's own split. They must
print exactly what training recorded in ews/models/metadata.json. If a pin fails, investigate
the computation -- never edit the pinned value."""
import json
import os

import numpy as np
import pytest
from sklearn.metrics import average_precision_score, roc_auc_score

from shared.config import EWS_TRIGGERS, ROOT

META = json.loads((ROOT / "ews/models/metadata.json").read_text())
TIERS = ("High", "Medium", "Low")
TRIGGERS = ("high_utilization", "rising_utilization", "delinquency", "deposit_decline",
            "frequent_overdrafts")


@pytest.fixture(scope="module")
def es():
    os.chdir(ROOT)
    from wiki.facts.ews_facts import ews_split
    return ews_split()


@pytest.fixture(scope="module")
def ef(es):
    from wiki.facts import ceiling, ews_facts
    return {**ews_facts.compute(es), **ceiling.compute_ews(es)}


@pytest.fixture(scope="module")
def t(ef):
    return {k: v.text() for k, v in ef.items()}


def _n(s: str) -> int:
    return int(s.replace(",", ""))


def _pct(s: str) -> float:
    return float(s.rstrip("%")) / 100


def test_headline_prints_what_metadata_recorded(t):
    m = META["metrics"]
    assert t["ews.auc"] == f"{m['auc']:.4f}" == "0.6622"
    assert t["ews.pr_auc"] == f"{m['pr_auc']:.4f}" == "0.3080"      # fmt .4f, as the report
    assert t["ews.capture"] == f"{m['top_decile_capture']:.1%}" == "21.6%"
    assert t["ews.lift"] == f"{m['top_decile_lift']:.2f}" == "2.16"
    assert t["ews.base_rate"] == f"{META['base_rate']:.1%}" == "18.0%"
    assert t["ews.t_high"] == f"{META['tiers']['t_high']:.4f}" == "0.5073"
    assert t["ews.t_med"] == f"{META['tiers']['t_med']:.4f}" == "0.1649"
    report = (ROOT / "ews/docs/validation_report.md").read_text()
    for k in ("ews.auc", "ews.pr_auc", "ews.capture", "ews.lift", "ews.t_high", "ews.t_med"):
        assert t[k] in report, k


def test_gates_print_what_train_py_asserts(t, ef):
    g = META["gate"]
    assert ef["ews.gate.capture_min"].value == g["capture_min"] and t["ews.gate.capture_min"] == "20%"
    assert t["ews.gate.lift_min"] == "2.0"
    assert g["pr_auc_min"] == "base_rate" and t["ews.gate.pr_auc_min"] == "the base rate"
    assert ef["ews.gate.auc_floor"].value == g["auc_report_floor"] and t["ews.gate.auc_floor"] == "0.60"
    # and they pass, by the stated margins
    assert _n(t["ews.capture_events"]) - _n(t["ews.gate.capture_events_needed"]) == \
        _n(t["ews.gate.capture_events_margin"]) >= 0
    assert ef["ews.pr_auc"].value > ef["ews.base_rate"].value


def test_split_reproduces_train_py_sizes(t):
    assert (t["ews.n_train"], t["ews.n_test"], t["ews.n_book"]) == ("6,668", "1,668", "8,336")


def test_held_out_is_the_headline_and_the_whole_book_is_in_sample(ef):
    """CLAUDE.md: capture is 21.6% held out but ~54% over the whole book. Quote the first."""
    assert ef["ews.capture"].value == pytest.approx(META["metrics"]["top_decile_capture"], abs=5e-5)
    assert ef["ews.whole.capture"].value > ef["ews.capture"].value
    assert ef["ews.whole.auc"].value > ef["ews.auc"].value
    assert ef["ews.whole.capture"].text() == "54.4%"
    for k in ("ews.whole.auc", "ews.whole.capture", "ews.train.auc"):
        assert "in-sample" in ef[k].population, k
    for k in ("ews.auc", "ews.pr_auc", "ews.capture"):
        assert ef[k].population.startswith("held-out 20%"), k


def test_every_fact_names_its_population_and_no_metric_is_read_from_metadata(ef):
    assert all(f.population for f in ef.values())
    # metadata.json supplies the tier cutoffs to risk_tier, as score_population reads them;
    # every metric is recomputed
    from wiki.facts.ews_facts import SRC_TIER
    assert {f.source for f in ef.values() if "metadata.json" in f.source} == {SRC_TIER}


def test_score_population_agrees_row_for_row(es, ef):
    """The facts skip score_population's SHAP pass; its tiers, triggers, prob and watchlist
    must equal what the facts compute from the same three functions."""
    from ews.src import watchlist as wl
    from ews.src.triggers import flag_triggers
    from wiki.facts.ews_facts import scored_frame
    sp = wl.score_population()
    meta = json.loads((ROOT / "ews/models/metadata.json").read_text())
    tier = np.array([wl.risk_tier(p, meta["tiers"]) for p in es.prob])
    trig = flag_triggers(es.feats)
    ids = list(es.port["business_id"].astype(str))
    assert list(sp["business_id"]) == ids and list(sp.index) == ids
    assert np.array_equal(sp["prob"].to_numpy(), np.round(es.prob, 4))
    assert list(sp["risk_tier"]) == list(tier)
    assert [list(x) for x in sp["triggers"]] == trig
    for T in TIERS:
        assert int((sp["risk_tier"] == T).sum()) == ef[f"ews.tier.{T}.n"].value
    assert wl.watchlist(sp) == wl.watchlist(scored_frame(es.port, es.prob, tier, trig))


def test_bootstrap_vectorised_equals_a_loop(es):
    from ews.src.train import top_decile_capture
    from wiki.facts.ews_facts import (_auc_with_ties, resample_counts, weighted_ap,
                                      weighted_auc, weighted_capture)
    y, p = es.y[es.idx_te], es.prob[es.idx_te]
    s = es.feats["pd_score"].to_numpy()[es.idx_te]
    B = 40
    W = resample_counts(len(y), B, 42)
    rng = np.random.default_rng(42)
    loop = [rng.integers(0, len(y), len(y)) for _ in range(B)]
    want = np.array([[roc_auc_score(y[i], p[i]), average_precision_score(y[i], p[i]),
                      top_decile_capture(y[i], p[i]), roc_auc_score(y[i], s[i])] for i in loop])
    got = np.column_stack([weighted_auc(y, p, W), weighted_ap(y, p, W),
                           weighted_capture(y, p, W), _auc_with_ties(y, s, W)])
    assert np.abs(got - want).max() < 1e-12


def test_intervals_contain_the_point_estimates(ef):
    for k in ("auc", "pr_auc", "capture"):
        point = ef["ews." + k].value
        assert ef[f"ews.boot.{k}.lo"].value < point < ef[f"ews.boot.{k}.hi"].value, k


def test_tiers(t, ef):
    assert sum(_n(t[f"ews.tier.{T}.n"]) for T in TIERS) == _n(t["ews.n_book"])
    assert sum(_n(t[f"ews.tier_ho.{T}.n"]) for T in TIERS) == _n(t["ews.n_test"])
    assert sum(_n(t[f"ews.tier_ho.{T}.events"]) for T in TIERS) == _n(t["ews.n_events_holdout"])
    # cutoffs are the 90% / 70% quantiles of the whole-book probability: 10% / 20% / 70%
    assert [t[f"ews.tier.{T}.share"] for T in TIERS] == ["10.0%", "20.0%", "70.0%"]
    # observed deterioration rate falls with the tier on held-out rows
    rates = [ef[f"ews.tier_ho.{T}.observed"].value for T in TIERS]
    assert rates == sorted(rates, reverse=True), rates


def test_tier_calibration_status_follows_the_floor_rule(ef):
    from wiki.facts.policy import MIN_BAND_DEFAULTS, RATIO_HI, RATIO_LO
    for T in TIERS:
        g = f"ews.tier_ho.{T}"
        r = float(ef[f"{g}.ratio"].text())
        ev = ef[f"{g}.events"].value
        want = ("within tolerance" if RATIO_LO <= r <= RATIO_HI else
                "finding" if ev >= MIN_BAND_DEFAULTS else "observation (below the floor)")
        assert ef[f"{g}.status"].value == want, T


def test_triggers(t, ef):
    for k in TRIGGERS:
        for s in ("share", "precision", "recall"):
            assert 0 <= ef[f"ews.trigger.{k}.{s}"].value <= 1, (k, s)
    assert 0 <= ef["ews.trigger.any.share"].value <= 1
    assert ef["ews.trigger.n_triggers"].value == len(TRIGGERS)
    # every config threshold is printed, with its value
    for ck, v in EWS_TRIGGERS.items():
        assert any(ef[k].value == ck and ef[k.replace(".config_key", ".threshold")].value == v
                   for k in ef if k.endswith(".config_key")), ck


def test_the_dead_delinquency_clause(t):
    """dpd_max never reaches dpd_severe on this book, so DELINQUENCY is dpd_recent > 0 alone."""
    c = "ews.trigger.delinquency.clause"
    assert float(t[f"{c}.dpd_max.feature_max"]) < float(t[f"{c}.dpd_max.threshold"])
    assert t[f"{c}.dpd_max.n_alone"] == "0"
    assert t[f"{c}.dpd_recent.n_alone"] == t["ews.trigger.delinquency.n"]
    assert t["ews.trigger.n_dead"] == "0" and t["ews.trigger.n_dead_clauses"] == "1"


def test_overlap_and_watchlist_add_up(t):
    assert _n(t["ews.overlap.high_with_trigger.n"]) + _n(t["ews.overlap.high_no_trigger.n"]) == \
        _n(t["ews.tier.High.n"])
    assert _n(t["ews.overlap.high_with_trigger.n"]) + _n(t["ews.overlap.triggered_not_high.n"]) == \
        _n(t["ews.trigger.any.n"])
    assert _n(t["ews.watchlist.n"]) == _n(t["ews.watchlist.top_n_default"]) == 100
    assert _n(t["ews.watchlist.n_train"]) + _n(t["ews.watchlist.n_holdout"]) == 100


def test_ceiling_is_above_the_model_on_the_same_rows(ef):
    assert ef["ceiling.ews.latent_holdout"].value > ef["ews.auc"].value
    assert ef["ceiling.ews.latent_holdout"].population == ef["ews.auc"].population
    assert ef["ceiling.ews.gap_holdout"].value == pytest.approx(
        ef["ceiling.ews.latent_holdout"].value - ef["ews.auc"].value)
    assert ef["ceiling.ews.latent_capture_holdout"].value > ef["ews.capture"].value
    # the lab script's printed population ceiling
    assert ef["ceiling.ews.latent_book"].text() == "0.7038"


def test_dgp_truth_only_in_ceiling():
    src = (ROOT / "wiki/facts/ews_facts.py").read_text()
    assert "pd_default_origination" not in src
    assert "pd_default_origination" in (ROOT / "wiki/facts/ceiling.py").read_text()


def test_cached_oracle_model_fact():
    """The oracle refit runs under --full only; its cached value is the lab script's."""
    facts = json.loads((ROOT / "wiki/facts/facts.json").read_text())
    assert facts["ceiling.ews.oracle_model.auc"]["text"] == "0.6647"
    assert facts["ceiling.ews.oracle_model.auc"]["population"] == facts["ews.auc"]["population"]


def test_score_dependency(ef):
    assert ef["ews.pd_score.auc"].population == ef["ews.auc"].population
    assert ef["ews.pd_score.diff_lo"].value < ef["ews.pd_score.diff"].value < \
        ef["ews.pd_score.diff_hi"].value
    names = {ef[f"ews.importance.gain.top{i}.feature"].value for i in range(1, 6)}
    from ews.src.feature_engineering import EWS_FEATURE_COLUMNS
    assert names <= set(EWS_FEATURE_COLUMNS)


def test_no_fact_prints_float_noise(ef):
    for k, f in ef.items():
        if isinstance(f.value, float):
            assert f.fmt, k
            assert "e-" not in f.text(), k
