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


def test_wiki_check_is_only_scheduled_on_main_at_stage_5():
    names = [c.name for c in verify.checks_for(5)]
    assert "Docs: model wiki" in names
    assert "Docs: model wiki" not in [c.name for c in verify.checks_for(4)]
