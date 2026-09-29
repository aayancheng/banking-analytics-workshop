import json

import pytest

from wiki.homework import check


@pytest.fixture
def answers(tmp_path, monkeypatch):
    d = tmp_path / "_answers"
    d.mkdir()
    monkeypatch.setattr(check, "ANSWERS", d)
    return d


def _fact(key):
    return json.loads(check.FACTS_JSON.read_text())[key]["text"]


def test_h2_1_passes_with_the_number_and_the_gate(answers):
    (answers / "H2.1.md").write_text(
        f"Without bureau data the held-out AUC is {_fact('score.stress.no_bureau.auc')}, "
        "below the gate, so the model does not ship.")
    ok, lines = check.run("H2.1")
    assert ok, lines


def test_h2_1_fails_without_an_answer_file(answers):
    ok, lines = check.run("H2.1")
    assert not ok and "wiki/homework/_answers/H2.1.md" in lines[0]


def test_h2_2_fails_on_an_auc_without_a_population(answers):
    (answers / "H2.2.md").write_text("The AUC is 0.8176.")
    ok, _ = check.run("H2.2")
    assert not ok


def test_h2_2_passes_when_every_auc_names_its_population(answers):
    (answers / "H2.2.md").write_text(
        f"On booked applicants the held-out AUC is {_fact('score.pop.booked.auc')}; "
        "on all held-out applicants it is 0.8176.")
    ok, lines = check.run("H2.2")
    assert ok, lines


def test_h4_1_part_checks_one_file(tmp_path, monkeypatch):
    monkeypatch.setattr(check, "MDD", tmp_path)
    (tmp_path / "adjudication").mkdir()
    ok, lines = check.run("H4.1", part="performance")
    assert not ok and "performance.qmd" in lines[0]
    (tmp_path / "adjudication" / "performance.qmd").write_text(
        "---\ntitle: \"5.5 Performance\"\norder: 5\n---\n\n"
        + "The held-out AUC is {{< var adj.auc >}} on held-out applicants. " * 30)
    ok, lines = check.run("H4.1", part="performance")
    assert ok, lines


def test_gates_are_checked_against_the_committed_promise():
    assert check.gates_intact() == (True, "the gate is 0.78 in score/src/train.py and verify.py")
