"""D4.8's monitoring thresholds are policy constants registered as facts, so every page
prints them by name. Pin the documented values and that build_facts ships them."""
import pytest

from wiki.facts import policy


@pytest.mark.parametrize("key,text", [
    ("monitoring.psi_watch", "0.10"), ("monitoring.psi_act", "0.25"),
    ("monitoring.ratio_lo", "0.75"), ("monitoring.ratio_hi", "1.25"),
    ("monitoring.iv_useless", "0.02"), ("monitoring.min_band_defaults", "20"),
])
def test_documented_policy_values(key, text):
    f = policy.compute()[key]
    assert f.text() == text
    assert f.population == "policy constant"


def test_build_facts_computes_the_policy():
    from wiki.facts import build_facts
    fresh, _ = build_facts.compute(full=False)
    for k, f in policy.compute().items():
        assert fresh[k].text() == f.text(), k


def test_committed_facts_carry_the_policy():
    from wiki.facts import build_facts
    from wiki.facts.core import load_facts
    committed = load_facts(build_facts.FACTS_JSON)
    for k, f in policy.compute().items():
        assert committed[k]["text"] == f.text(), k
