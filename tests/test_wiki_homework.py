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


# --- fix round 2 ---------------------------------------------------------------------------

@pytest.mark.parametrize("ref", ["./wiki/mdd/score/data.qmd",
                                 "wiki/../wiki/mdd/score/data.qmd",
                                 "wiki/mdd/score/data.qmd"])
def test_h4_2_rejects_the_documentation_however_the_path_is_spelled(answers, ref):
    (answers / "H4.2.md").write_text(
        GOOD_H4_2.split("F3:")[0] + f"F3: Band AAA under-predicts.\nEvidence: {ref}\n")
    ok, lines = check.run("H4.2")
    assert not ok and "documentation is not evidence" in lines[-1], lines


def test_h4_2_accepts_a_code_path_spelled_with_dot_slash(answers):
    (answers / "H4.2.md").write_text(
        GOOD_H4_2.split("F3:")[0] + "F3: Scoring.\nEvidence: ./score/src/predict.py\n")
    ok, lines = check.run("H4.2")
    assert ok, lines


@pytest.mark.parametrize("verdict", ["The refit does not pass the gate.",
                                     "The refit does not clear the gate; it fails.",
                                     "It doesn't meet the gate."])
def test_h2_1_accepts_negated_pass_phrasings(answers, verdict):
    (answers / "H2.1.md").write_text(
        f"Without bureau data the held-out AUC is {_fact('score.stress.no_bureau.auc')}. {verdict}")
    ok, lines = check.run("H2.1")
    assert ok, lines


# --- Session 1 and Session 3 (H1.1-H1.3, H3.1-H3.3) ----------------------------------------
# Answers are built from the recomputed facts, never typed, so a pin moves with the model.

@pytest.fixture
def clean_git(monkeypatch):
    """A working tree with nothing changed and nothing left behind, whatever the real one has."""
    monkeypatch.setattr(check, "_git", lambda *a: "")
    return monkeypatch


GOOD_H1_1 = (
    "- **LEAK:** `pd_default_origination` — the generator's true PD, which no bank observes.\n"
    "- LEAK: default — the outcome itself, known only after the loan has run.\n"
    "LEAK: `booked`: decided after the credit decision, from the true PD.\n"
    "LEAK: risk_based_rate — priced from the true PD plus a small noise term.\n\n"
    "net_income predicts but is on the application: not a leak.\n")


def test_h1_1_passes_the_four_deny_listed_columns_with_reasons(answers):
    (answers / "H1.1.md").write_text(GOOD_H1_1)
    ok, lines = check.run("H1.1")
    assert ok, lines


@pytest.mark.parametrize("edit, why", [
    (lambda s: s.replace("LEAK: risk_based_rate", "SAFE: risk_based_rate"),
     "missing from your LEAK lines: risk_based_rate"),
    (lambda s: s + "LEAK: net_income — it is built from revenue and predicts default.\n",
     "not on the deny-list: net_income"),
    (lambda s: s + "LEAK: line_increase_good — a later outcome on booked accounts.\n",
     "lives in portfolio.parquet only"),
    (lambda s: s + "LEAK: pd_true — the true PD under another name.\n",
     "`pd_true` is not a column of businesses.parquet"),
    (lambda s: s.replace("the outcome itself, known only after the loan has run", "label"),
     "say why in a few words: default"),
])
def test_h1_1_fails_a_wrong_or_thin_list(answers, edit, why):
    (answers / "H1.1.md").write_text(edit(GOOD_H1_1))
    ok, lines = check.run("H1.1")
    assert not ok and any(why in l for l in lines), lines


def test_h1_1_fails_when_the_deny_list_was_edited(answers, monkeypatch):
    import shared.config
    monkeypatch.setattr(shared.config, "LEAKAGE_COLUMNS", ["default", "booked"])
    (answers / "H1.1.md").write_text(GOOD_H1_1)
    ok, lines = check.run("H1.1")
    assert not ok and "LEAKAGE_COLUMNS in shared/config.py was changed" in lines[-1]


def _h1_2(truepd, honest=None):
    honest = honest or _fact("leakage.honest.auc")
    return (f"Honest model, held-out applicants: {honest}. With the true PD added: {truepd}. "
            "The true PD does not exist at decision time, so it cannot ship.")


@pytest.mark.parametrize("shown", ["0.8326", "0.833", "83.26%", "83.3 %"])
def test_h1_2_accepts_the_middle_rung_in_any_faithful_format(answers, clean_git, shown):
    (answers / "H1.2.md").write_text(_h1_2(shown))
    ok, lines = check.run("H1.2")
    assert ok, lines


def test_h1_2_fails_the_population_ceiling_in_place_of_the_rung(answers, clean_git):
    # the true PD's AUC over all 12,000 applicants is a different experiment
    (answers / "H1.2.md").write_text(_h1_2(_fact("ceiling.truepd_all")))
    ok, lines = check.run("H1.2")
    assert not ok and f"nearest number in your answer is {_fact('ceiling.truepd_all')}" in lines[0]


def test_h1_2_fails_without_the_decision_time_sentence(answers, clean_git):
    (answers / "H1.2.md").write_text(
        f"Honest {_fact('leakage.honest.auc')}; with the true PD {_fact('leakage.truepd.auc')}.")
    ok, lines = check.run("H1.2")
    assert not ok and lines[2].startswith("❌")


def test_h1_2_fails_while_the_probe_is_still_in_the_repo(answers, monkeypatch):
    monkeypatch.setattr(check, "_probes_left", lambda: ["leakage_probe.py"])
    (answers / "H1.2.md").write_text(_h1_2(_fact("leakage.truepd.auc")))
    ok, lines = check.run("H1.2")
    assert not ok and "delete the probe" in lines[3] and "leakage_probe.py" in lines[3]


def test_a_probe_is_a_script_that_fits_on_the_true_pd():
    assert check._is_probe('X.assign(c=b["pd_default_origination"]); m.fit(X, y)')
    assert not check._is_probe('assert "pd_default_origination" in LEAKAGE_COLUMNS')


GOOD_H1_3 = (
    "| Leaked column | AUC |\n|---|---|\n"
    "| none (honest) | {honest} |\n"
    "| `pd_default_origination`, the true PD | {truepd} |\n"
    "| `default`, the label | {label} |\n\n"
    "Each default is a Bernoulli draw on the true PD, so even the truth ranks imperfectly.\n")


def _h1_3(**kw):
    vals = {"honest": _fact("leakage.honest.auc"), "truepd": _fact("leakage.truepd.auc"),
            "label": _fact("leakage.label.auc")} | kw
    return GOOD_H1_3.format(**vals)


@pytest.mark.parametrize("label", ["1.0000", "1.00", "1.0", "100%"])
def test_h1_3_passes_with_each_rung_on_its_own_row(answers, label):
    (answers / "H1.3.md").write_text(_h1_3(label=label))
    ok, lines = check.run("H1.3")
    assert ok, lines


def test_h1_3_fails_the_transcripts_swap(answers):
    # the claim being caught: the 1.0 pinned on the true PD
    (answers / "H1.3.md").write_text(_h1_3(truepd=_fact("leakage.label.auc"),
                                           label=_fact("leakage.truepd.auc")))
    ok, lines = check.run("H1.3")
    assert not ok and lines[0].startswith("❌") and lines[1].startswith("❌")


def test_h1_3_fails_without_the_reason(answers):
    (answers / "H1.3.md").write_text(_h1_3().split("\n\n")[0] + "\n\nThe transcript was wrong.\n")
    ok, lines = check.run("H1.3")
    assert not ok and "cannot reach 1.0" in lines[-1]


def _h3_1(**kw):
    f = {k: _fact(f"adj.dscr_whatif.{k}") for k in
         ("flipped", "Approve.n", "Refer.n", "Decline.n")} | kw
    return ("Over all 12,000 applicants, as the portal decides them, "
            f"{f['flipped']} decisions change, all Refer to Decline. After: Approve "
            f"{f['Approve.n']}, Refer {f['Refer.n']}, Decline {f['Decline.n']}. Approve does "
            "not move: the thin-margin override already sent those files to Refer.")


def test_h3_1_passes_with_the_mix_the_count_and_the_override(answers, clean_git):
    (answers / "H3.1.md").write_text(_h3_1())
    ok, lines = check.run("H3.1")
    assert ok, lines


def test_h3_1_accepts_shares_and_unseparated_counts(answers, clean_git):
    (answers / "H3.1.md").write_text(_h3_1(
        flipped=_fact("adj.dscr_whatif.flipped").replace(",", ""),
        **{k: _fact(f"adj.dscr_whatif.{k[:-2]}.share") for k in ("Refer.n", "Decline.n")}))
    ok, lines = check.run("H3.1")
    assert ok, lines


@pytest.mark.parametrize("edit, why", [
    (lambda s: s.replace(_fact("adj.dscr_whatif.Decline.n"), _fact("adj.book.Decline.n")),
     "the new Decline count or share is missing"),
    (lambda s: s.replace("the thin-margin override already sent those files to Refer",
                         "the best files are safe"), "explain the Approve count"),
    (lambda s: s.replace("Over all 12,000 applicants, as the portal decides them, ", ""),
     "does not say on whom"),
])
def test_h3_1_fails_a_wrong_or_unexplained_shift(answers, clean_git, edit, why):
    (answers / "H3.1.md").write_text(edit(_h3_1()))
    ok, lines = check.run("H3.1")
    assert not ok and any(why in l for l in lines), lines


def test_h3_1_fails_when_the_policy_file_was_edited(answers, monkeypatch):
    monkeypatch.setattr(check, "_git",
                        lambda *a: " M adjudication/models/policy_config.json\n")
    (answers / "H3.1.md").write_text(_h3_1())
    ok, lines = check.run("H3.1")
    assert not ok and "adjudication/models/policy_config.json" in lines[-1]


def _h3_2(d_amount=None):
    worst, d = _fact("pricing.worst_band"), _fact("pricing.band.D.mispriced_ead")
    return (f'The claim "mispricing is worst in band D" needs a measure. By share, band '
            f'{worst} is worst at {_fact("pricing.worst_band_rate")} mispriced. By mispriced '
            f"EAD, band D is worst, with ${d_amount or d}.")


@pytest.mark.parametrize("amount", [None, "353.8M", "353.8 million", "354M", "0.35bn"])
def test_h3_2_passes_both_measures_in_any_money_format(answers, amount):
    (answers / "H3.2.md").write_text(_h3_2(amount))
    ok, lines = check.run("H3.2")
    assert ok, lines


def test_h3_2_fails_the_claim_unqualified(answers):
    (answers / "H3.2.md").write_text(_h3_2() + " Overall, band D is the worst band.")
    ok, lines = check.run("H3.2")
    assert not ok and "without its measure" in lines[-1]


def test_h3_2_fails_without_the_share_reading(answers):
    (answers / "H3.2.md").write_text(
        f"By mispriced EAD, band D is worst, with ${_fact('pricing.band.D.mispriced_ead')}.")
    ok, lines = check.run("H3.2")
    assert not ok and lines[0].startswith("❌") and lines[1].startswith("✅")


def test_h3_2_fails_a_wrong_amount_for_band_d(answers):
    (answers / "H3.2.md").write_text(_h3_2(_fact("pricing.band.D.ead")))
    ok, lines = check.run("H3.2")
    assert not ok and lines[1].startswith("❌")


def _h3_3(ids=None):
    ids = ids or [_fact("ews.rounded_retier.flip1.business_id"),
                  _fact("ews.rounded_retier.flip2.business_id")]
    return (f"With the committed cutoffs sent explicitly, {' and '.join(ids)} change tier. "
            "score_population stores prob rounded to 4 dp; the what-if re-tiers from it. "
            "Fix: re-tier from the unrounded probability on every path.")


def test_h3_3_passes_with_both_accounts_the_cause_and_the_fix(answers, clean_git):
    (answers / "H3.3.md").write_text(_h3_3())
    ok, lines = check.run("H3.3")
    assert ok, lines


@pytest.mark.parametrize("edit, why", [
    (lambda s: s.replace(_fact("ews.rounded_retier.flip1.business_id"), "one account"),
     "your answer does not name"),
    (lambda s: s.replace("stores prob rounded to 4 dp", "stores prob"), "name the cause"),
    (lambda s: s.replace("from the unrounded probability", "carefully"), "name the fix"),
])
def test_h3_3_fails_an_incomplete_finding(answers, clean_git, edit, why):
    (answers / "H3.3.md").write_text(edit(_h3_3()))
    ok, lines = check.run("H3.3")
    assert not ok and any(why in l for l in lines), lines


def test_h3_3_fails_when_the_app_was_patched(answers, monkeypatch):
    monkeypatch.setattr(check, "_git", lambda *a: " M app/v2/ews_whatif.py\n")
    (answers / "H3.3.md").write_text(_h3_3())
    ok, lines = check.run("H3.3")
    assert not ok and "app/v2/ews_whatif.py" in lines[-1]


def test_every_checked_exercise_has_a_prompt_card_and_a_page_section():
    root = check.ROOT
    pages = "".join((root / "wiki/course" / f"homework-s{n}.qmd").read_text() for n in (1, 2, 3, 4))
    for hid in check.CHECKS:
        assert f"python -m wiki.homework.check {hid}" in pages, hid
        if hid not in ("H4.3",):
            assert (root / "workshop/prompt-cards" / f"HW-{hid}.md").exists(), hid
