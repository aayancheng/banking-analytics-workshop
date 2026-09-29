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


# --- H2.1: the number in any faithful format, and the gate's direction -------------------

@pytest.mark.parametrize("shown", ["0.770", "0.7704", "77.04%", "77.0 %"])
def test_h2_1_accepts_the_number_in_any_faithful_format(answers, shown):
    (answers / "H2.1.md").write_text(
        f"Without bureau data the held-out AUC is {shown}. The refit fails the gate.")
    ok, lines = check.run("H2.1")
    assert ok, lines


def test_h2_1_fails_a_wrong_number_and_names_the_nearest(answers):
    (answers / "H2.1.md").write_text(
        "Without bureau data the held-out AUC is 0.7643 (KS 0.4185). The refit fails the gate.")
    ok, lines = check.run("H2.1")
    assert not ok
    assert "nearest number in your answer is 0.7643" in lines[0]


def test_h2_1_fails_when_the_answer_says_the_gate_passes(answers):
    (answers / "H2.1.md").write_text(
        f"Without bureau data the held-out AUC is {_fact('score.stress.no_bureau.auc')}. "
        "The gate passes, ship it.")
    ok, lines = check.run("H2.1")
    assert not ok and lines[1].startswith("❌")


def test_h2_1_fails_when_the_gate_is_named_without_its_outcome(answers):
    (answers / "H2.1.md").write_text(
        f"Held-out AUC {_fact('score.stress.no_bureau.auc')}. I looked at the gate.")
    ok, _ = check.run("H2.1")
    assert not ok


# --- H2.2: only AUC facts count, sentence or table-row scope ------------------------------

def test_h2_2_ignores_a_bare_ks(answers):
    (answers / "H2.2.md").write_text(
        f"On held-out booked applicants the AUC is {_fact('score.pop.booked.auc')}. "
        f"The KS is {_fact('score.ks_holdout')}.")
    ok, lines = check.run("H2.2")
    assert ok, lines


def test_h2_2_population_must_be_in_the_same_sentence(answers):
    (answers / "H2.2.md").write_text(
        f"On held-out booked applicants the AUC is {_fact('score.pop.booked.auc')}. "
        f"Overall it is {_fact('score.auc_holdout')}.")
    ok, lines = check.run("H2.2")
    assert not ok and _fact("score.auc_holdout") in lines[1]


def test_h2_2_a_table_row_or_its_header_names_the_population(answers):
    (answers / "H2.2.md").write_text(
        "| Population | AUC |\n|---|---|\n"
        f"| all held-out | {_fact('score.pop.everyone.auc')} |\n"
        f"| booked | {_fact('score.pop.booked.auc')} |\n")
    ok, lines = check.run("H2.2")
    assert ok, lines


def test_h2_2_a_table_without_populations_fails(answers):
    (answers / "H2.2.md").write_text(
        "| Model | AUC |\n|---|---|\n"
        f"| scorecard | {_fact('score.auc_holdout')} |\n\n"
        f"On held-out booked applicants it is {_fact('score.pop.booked.auc')}.")
    ok, _ = check.run("H2.2")
    assert not ok


# --- H4.2: every finding needs real evidence -----------------------------------------------

GOOD_H4_2 = (
    "**F1:** The gate is not met on the booked.\n"
    "**Evidence:** `score.pop.booked.auc`.\n\n"
    "F2: Missing inputs are scored as zero.\n"
    "Evidence: score/src/feature_engineering.py\n\n"
    "F3: Band AAA under-predicts on the booked.\n"
    "Evidence: {{< var score.band_booked.AAA.ratio >}}\n"
)


def test_h4_2_passes_three_findings_with_real_evidence(answers):
    (answers / "H4.2.md").write_text(GOOD_H4_2)
    ok, lines = check.run("H4.2")
    assert ok, lines


@pytest.mark.parametrize("bad, why", [
    ("F3: Band AAA under-predicts.\n", "no 'Evidence:' line"),
    ("F3: Band AAA under-predicts.\nEvidence:\n", "no evidence after"),
    ("F3: Band AAA under-predicts.\nEvidence: wiki/mdd/score/limitations.qmd\n",
     "documentation is not evidence"),
    ("F3: Band AAA under-predicts.\nEvidence: score/src\n", "neither a fact key nor a file"),
    ("F3: Band AAA under-predicts.\nEvidence: score.band.AAA.miscalibration\n",
     "neither a fact key nor a file"),
])
def test_h4_2_fails_a_finding_without_real_evidence(answers, bad, why):
    good_two = GOOD_H4_2.split("F3:")[0]
    (answers / "H4.2.md").write_text(good_two + bad)
    ok, lines = check.run("H4.2")
    assert not ok
    assert why in lines[-1], lines


def test_h4_2_fails_fewer_than_three_findings(answers):
    (answers / "H4.2.md").write_text(GOOD_H4_2.split("F3:")[0])
    ok, lines = check.run("H4.2")
    assert not ok and "found 2" in lines[0]


def test_h4_2_accepts_evidence_at_the_end_of_the_finding_line(answers):
    (answers / "H4.2.md").write_text(
        "F1: Gate population. Evidence: `score.pop.booked.auc`\n\n"
        "F2: Missing inputs scored as zero. Evidence: `score/src/feature_engineering.py`\n\n"
        "F3: No out-of-time sample. **Evidence:** `score.psi_score`\n")
    ok, lines = check.run("H4.2")
    assert ok, lines
