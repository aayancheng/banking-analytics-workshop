import json
import shutil

import verify


def test_wiki_check_passes_on_committed_state():
    ok, detail, fix = verify.check_wiki()
    assert ok, detail


def test_wiki_check_names_a_stale_fact(monkeypatch, tmp_path):
    from wiki.facts import build_facts
    real = json.loads(build_facts.FACTS_JSON.read_text())
    real["score.auc_holdout"]["text"] = "0.9999"
    fake = tmp_path / "facts.json"
    fake.write_text(json.dumps(real))
    monkeypatch.setattr(build_facts, "FACTS_JSON", fake)
    ok, detail, fix = verify.check_wiki()
    assert not ok and "score.auc_holdout" in detail and "make wiki-facts" in fix


def test_wiki_check_rejects_a_fact_no_module_computes(monkeypatch, tmp_path):
    from wiki.facts import build_facts
    real = json.loads(build_facts.FACTS_JSON.read_text())
    real["adj.approve_rate_booked"] = {"value": 0.61, "text": "61.0%", "fmt": ".1%",
                                       "source": "hand", "population": "booked"}
    fake = tmp_path / "facts.json"
    fake.write_text(json.dumps(real))
    monkeypatch.setattr(build_facts, "FACTS_JSON", fake)
    ok, detail, fix = verify.check_wiki()
    assert not ok and "adj.approve_rate_booked" in detail and "not computed" in detail


def test_wiki_check_rejects_a_hand_edited_population(monkeypatch, tmp_path):
    from wiki.facts import build_facts
    real = json.loads(build_facts.FACTS_JSON.read_text())
    real["score.auc_holdout"]["population"] = "everyone"
    fake = tmp_path / "facts.json"
    fake.write_text(json.dumps(real))
    monkeypatch.setattr(build_facts, "FACTS_JSON", fake)
    ok, detail, fix = verify.check_wiki()
    assert not ok and "score.auc_holdout" in detail and "population" in detail


def test_wiki_check_rejects_a_hand_edited_variables_file(monkeypatch, tmp_path):
    from wiki.facts import build_facts
    wiki = tmp_path / "wiki"
    shutil.copytree(build_facts.WIKI, wiki,
                    ignore=shutil.ignore_patterns("_site", "_book", "_validation", ".quarto"))
    yml = wiki / "_variables.yml"
    yml.write_text(yml.read_text().replace('"0.8176"', '"0.8200"', 1))
    monkeypatch.setattr(build_facts, "WIKI", wiki)
    ok, detail, fix = verify.check_wiki()
    assert not ok and "_variables.yml" in detail


def test_wiki_check_is_only_scheduled_on_main_at_stage_5():
    names = [c.name for c in verify.checks_for(5)]
    assert "Docs: model wiki" in names
    assert "Docs: model wiki" not in [c.name for c in verify.checks_for(4)]
