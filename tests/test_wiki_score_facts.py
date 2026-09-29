"""The facts layer must reproduce every number the workshop has already published.
If one of these fails, investigate the computation — never edit the pinned value."""
import os

import pytest

from shared.config import ROOT


@pytest.fixture(scope="module")
def facts():
    os.chdir(ROOT)
    from wiki.facts import adj_facts, ceiling, score_facts
    from wiki.facts.data import score_split
    split = score_split()
    f, _ = score_facts.compute(split)
    f.update(adj_facts.compute())
    f.update(ceiling.compute(split))
    return {k: v.text() for k, v in f.items()}


@pytest.mark.parametrize("key,text", [
    ("score.auc_holdout", "0.8176"), ("score.ks_holdout", "0.4946"),
    ("score.pop.booked.auc", "0.7447"), ("score.pop.rejected.auc", "0.8440"),
    ("score.pop.everyone.auc", "0.8176"), ("score.band.D.n", "1,222"),
    ("score.n_booked", "8,336"), ("score.n_test", "2,400"), ("score.n_train", "9,600"),
    ("score.gate", "0.78"), ("score.benchmark_adj_auc", "0.8096"),
    ("adj.auc", "0.8096"), ("adj.t_low", "0.0955"), ("adj.t_high", "0.4943"),
    ("ceiling.signal_all", "0.8177"), ("ceiling.truepd_all", "0.8311"),
    ("ceiling.signal_holdout", "0.8353"), ("market.roe_hurdle", "15%"),
])
def test_published_numbers_reproduce(facts, key, text):
    assert facts[key] == text


def test_bootstrap_interval_brackets_the_point_estimate(facts):
    assert float(facts["score.auc_ci_lo"]) < 0.8176 < float(facts["score.auc_ci_hi"])


def test_every_band_is_present_and_shares_sum_to_one(facts):
    shares = [float(facts[f"score.band.{b}.share"].rstrip("%")) for b in
              ("D", "C", "B", "A", "AAA")]
    assert abs(sum(shares) - 100) < 0.3


def test_structural_zero_share_is_measured(facts):
    assert facts["score.var_share_structural"].endswith("%")


def test_band_defaults_add_up_to_the_held_out_default_rate(facts):
    n = sum(int(facts[f"score.band.{b}.defaults"].replace(",", "")) for b in
            ("D", "C", "B", "A", "AAA"))
    assert abs(n / 2400 * 100 - float(facts["score.pop.everyone.dr"].rstrip("%"))) < 0.05


def test_woe_monotonicity_is_measured_on_the_committed_card(facts):
    # D4.4 reports this as an assumption not fully met; a change here changes that text.
    assert facts["score.woe_nonmonotonic"] == "leverage, trade_lines"
    assert facts["score.n_woe_nonmonotonic"] == "2"
