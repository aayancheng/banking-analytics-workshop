import json

import pytest

from wiki.facts.core import Fact, diff_facts, dump_facts, load_facts, nest, to_yaml


def test_fact_text_uses_its_format():
    assert Fact(0.81761, ".4f", "s", "p").text() == "0.8176"
    assert Fact(1222, ",d", "s", "p").text() == "1,222"
    assert Fact(0.509, ".1%", "s", "p").text() == "50.9%"
    assert Fact("none", "", "s", "p").text() == "none"


def test_dump_is_sorted_and_round_trips(tmp_path):
    p = tmp_path / "facts.json"
    dump_facts({"b.x": Fact(0.123456789, ".4f", "s", "p"), "a.y": Fact(3, "d", "s", "p")}, p)
    data = load_facts(p)
    assert list(data) == ["a.y", "b.x"]
    assert data["b.x"] == {"value": 0.123457, "text": "0.1235", "fmt": ".4f",
                           "source": "s", "population": "p"}
    assert p.read_text().endswith("\n")


def test_nest_and_yaml():
    tree = nest({"score.auc": "0.8176", "score.band.D.count": "1,222"})
    assert tree == {"score": {"auc": "0.8176", "band": {"D": {"count": "1,222"}}}}
    assert to_yaml(tree) == ('score:\n  auc: "0.8176"\n  band:\n    D:\n'
                             '      count: "1,222"')


def test_nest_rejects_a_key_that_is_both_leaf_and_branch():
    with pytest.raises(ValueError):
        nest({"score.auc": "1", "score.auc.booked": "2"})


def test_diff_names_the_stale_key():
    fresh = {"score.auc": Fact(0.8176, ".4f", "s", "p")}
    committed = {"score.auc": {"text": "0.8100"}, "score.stress.x": {"text": "0.7"}}
    assert diff_facts(fresh, committed) == [
        "score.auc: facts.json says 0.8100, recomputed 0.8176",
        "score.stress.x: in facts.json but no longer computed",
    ]
    assert diff_facts(fresh, committed, partial=True) == [
        "score.auc: facts.json says 0.8100, recomputed 0.8176"]


def test_diff_reports_new_facts():
    assert diff_facts({"a": Fact(1, "d", "s", "p")}, {}) == ["a: new, not in facts.json"]


from wiki.facts import tables


def _meta(t):
    return {k: {"text": v, "source": "src", "population": "pop"} for k, v in t.items()}


def test_band_table_is_generated_from_fact_text():
    t = {}
    for b in ("D", "C", "B", "A", "AAA"):
        t.update({f"score.band.{b}.n": "1", f"score.band.{b}.share": "2%",
                  f"score.band.{b}.observed": "3%", f"score.band.{b}.predicted": "4%",
                  f"score.band.{b}.ratio": "0.75"})
    md = tables.band_table(t)
    assert md.splitlines()[0] == "| Band | n | Share | Observed default rate | Mean predicted PD | Observed / predicted |"
    assert "| AAA | 1 | 2% | 3% | 4% | 0.75 |" in md


def test_stale_reports_an_outdated_generated_file(tmp_path):
    t = {"a.b": "1"}
    (tmp_path / "facts.qmd").write_text("old")
    assert any("facts.qmd" in p for p in tables.stale_files({"facts.qmd": "new"}, tmp_path))


def test_fact_index_escapes_the_var_shortcode_it_names():
    meta = _meta({"score.auc": "0.8176"})
    text = tables.fact_index(meta)
    assert "{{</* var key */>}}" in text
    assert "{{< var key >}}" not in text
