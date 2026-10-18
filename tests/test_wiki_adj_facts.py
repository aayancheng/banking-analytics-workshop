"""D5's facts are recomputed through the adjudication module's own functions (saved model,
compute_adjudication_features, policy.decide). They must print exactly what training
recorded in metadata.json and policy_config.json. If a pin fails, investigate the
computation — never edit the pinned value."""
import json
import os

import pytest

from shared.config import ROOT

META = json.loads((ROOT / "adjudication/models/metadata.json").read_text())
POLICY = json.loads((ROOT / "adjudication/models/policy_config.json").read_text())
DECISIONS = ("Approve", "Refer", "Decline")


@pytest.fixture(scope="module")
def adj():
    os.chdir(ROOT)
    from wiki.facts import adj_facts
    from wiki.facts.data import score_split
    return adj_facts.compute(score_split())


@pytest.fixture(scope="module")
def t(adj):
    return {k: v.text() for k, v in adj.items()}


def _n(s: str) -> int:
    return int(s.replace(",", ""))


def _pct(s: str) -> float:
    return float(s.rstrip("%"))


def test_recomputed_headline_prints_what_metadata_recorded(t):
    assert t["adj.auc"] == f"{META['metrics']['auc']:.4f}" == "0.8096"
    assert t["adj.lift"] == f"{META['metrics']['top20_lift']:.2f}" == "2.86"
    assert t["adj.gate_auc"] == f"{META['gate']['auc_min']:.2f}"
    assert t["adj.gate_lift"] == f"{META['gate']['lift_min']:.1f}"
    assert t["adj.n_train"] == f"{META['train_rows']:,d}"
    assert t["adj.n_test"] == f"{META['test_rows']:,d}"
    assert t["adj.n_features"] == str(len(META["ADJ_FEATURE_COLUMNS"]))
    assert t["adj.n_applicants"] == "12,000" and t["adj.test_share"] == "20%"


def test_recomputed_thresholds_are_the_committed_policy(t):
    assert t["adj.t_low"] == f"{POLICY['t_low']:.4f}" == "0.0955"
    assert t["adj.t_high"] == f"{POLICY['t_high']:.4f}" == "0.4943"


@pytest.mark.parametrize("k", DECISIONS)
def test_recomputed_mix_prints_what_metadata_recorded(t, k):
    assert t[f"adj.mix.{k}"] == f"{META['decision_mix_test'][k]:.1%}"
    assert t[f"adj.mix.{k}"] == t[f"adj.dec.everyone.{k}.share"]


def test_no_adj_fact_reads_metadata(adj):
    assert not any("metadata.json" in f.source for k, f in adj.items() if k.startswith("adj."))


def test_every_fact_names_its_population(adj):
    assert all(f.population for f in adj.values())


def test_booked_and_rejected_partition_the_held_out(t):
    assert _n(t["adj.pop.booked.n"]) + _n(t["adj.pop.rejected.n"]) == _n(t["adj.n_test"])
    for k in DECISIONS:
        assert _n(t[f"adj.dec.booked.{k}.n"]) + _n(t[f"adj.dec.rejected.{k}.n"]) == \
            _n(t[f"adj.dec.everyone.{k}.n"])
        assert _n(t[f"adj.dec.booked.{k}.defaults"]) + _n(t[f"adj.dec.rejected.{k}.defaults"]) \
            == _n(t[f"adj.dec.everyone.{k}.defaults"])
    for p in ("everyone", "booked", "rejected"):
        n = sum(_n(t[f"adj.dec.{p}.{k}.n"]) for k in DECISIONS)
        assert n == _n(t[f"adj.pop.{p}.n"])
        d = sum(_n(t[f"adj.dec.{p}.{k}.defaults"]) for k in DECISIONS)
        assert abs(d / n * 100 - _pct(t[f"adj.pop.{p}.dr"])) < 0.05


def test_zone_calibration_adds_up(t):
    for p in ("everyone", "booked"):
        assert sum(_n(t[f"adj.zone.{p}.{k}.n"]) for k in DECISIONS) == _n(t[f"adj.pop.{p}.n"])
    for k in DECISIONS:
        assert _n(t[f"adj.zone.booked.{k}.defaults"]) <= _n(t[f"adj.zone.everyone.{k}.defaults"])


def test_raising_a_cutoff_moves_the_mix_the_right_way(adj):
    v = lambda k: adj[k].value
    assert v("adj.sens.t_low_up.Approve") >= v("adj.mix.Approve") >= v("adj.sens.t_low_down.Approve")
    assert v("adj.sens.t_high_up.Decline") <= v("adj.mix.Decline") <= v("adj.sens.t_high_down.Decline")
    assert v("adj.sens.t_low_up.Decline") == v("adj.mix.Decline")   # t_low cannot touch Decline
    assert v("adj.sens.t_high_up.Approve") == v("adj.mix.Approve")  # t_high cannot touch Approve


def test_rule_counts_are_consistent(t):
    ko = ("dscr_floor", "public_records", "prior_delinquencies", "leverage")
    assert _n(t["adj.rule.any_knockout.n"]) <= sum(_n(t[f"adj.rule.{r}.n"]) for r in ko)
    assert _n(t["adj.rule.any.n"]) <= _n(t["adj.rule.any_knockout.n"]) + _n(t["adj.rule.any_override.n"])
    # every knocked-out file is a Decline
    assert _n(t["adj.rule.any_knockout.n"]) <= _n(t["adj.decline.n"])
    assert _n(t["adj.decline.n"]) == _n(t["adj.dec.everyone.Decline.n"])
    for r in ("dscr_floor", "public_records", "weak_score"):
        assert _n(t[f"adj.rule.{r}.n"]) <= _n(t[f"adj.rule.{r}.n_all"])


def test_lift_function_ranks_the_top_fifth_not_a_ventile(t):
    assert t["adj.lift_function"] == "top_ventile_lift"
    assert t["adj.lift_top_share"] == "20%"


def test_decline_reasons_are_ranked(adj):
    for kind in ("rule", "shap"):
        ns = [adj[f"adj.decline.{kind}{i}.n"].value for i in (1, 2, 3)]
        assert ns == sorted(ns, reverse=True)
        assert ns[0] <= adj["adj.decline.n"].value


def test_tables_render_from_the_facts(t):
    from wiki.facts import build_facts, tables
    from wiki.facts.core import load_facts
    committed = load_facts(build_facts.FACTS_JSON)
    files = tables.render_all({**{k: d["text"] for k, d in committed.items()}, **t}, committed)
    for name in ("adj-populations", "adj-decisions", "adj-cutoffs", "adj-rules",
                 "adj-calibration"):
        body = files[f"_generated/{name}.md"]
        assert body.startswith(tables.HEADER) and "| " in body
    assert t["adj.pop.booked.auc"] in files["_generated/adj-populations.md"]
    assert t["adj.trainonly.t_high"] in files["_generated/adj-cutoffs.md"]


def test_labels_say_what_was_measured(adj):
    """Constants are not held-out measurements; rule counts are hits, not decisions; the
    training-only thresholds are in-sample quantiles, not an out-of-sample recalibration."""
    from wiki.facts.adj_facts import HOLDOUT
    for k in ("adj.n_features", "adj.gate_auc", "adj.gate_lift"):
        assert adj[k].population != HOLDOUT and "constant" in adj[k].population, k
    for k in ("adj.trainonly.t_low", "adj.trainonly.t_high"):
        assert "in-sample" in adj[k].population and "not an out-of-sample" in adj[k].population
    for k in ("thin_dscr", "weak_score", "large_request"):
        for f in ("n", "share", "n_all"):
            pop = adj[f"adj.rule.{k}.{f}"].population
            assert "hit" in pop and "knockout" in pop, (k, f)
    for k in ("dscr_floor", "public_records", "prior_delinquencies", "leverage"):
        assert "hit" in adj[f"adj.rule.{k}.n"].population, k
