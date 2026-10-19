"""Facts the Course tab's Session 1 and Session 3 chapters and their homework print: the
leakage ladder, the adjudication mix over the whole book and the H3.1 what-if, and the
rounded-prob re-tier behind H3.3. Each is recomputed through the module's own functions; the
pins are the numbers the sessions showed on screen. If a pin fails, investigate the
computation -- never edit the pinned value."""
import json
import os

import numpy as np
import pytest

from shared.config import ROOT


@pytest.fixture(scope="module")
def split():
    os.chdir(ROOT)
    from wiki.facts.data import score_split
    return score_split()


@pytest.fixture(scope="module")
def ladder(split):
    from wiki.facts import ceiling, leakage
    lk = leakage.compute(split)
    return {**lk, **ceiling.compute_leakage(split, lk["leakage.honest.auc"].value)}


# --- the leakage ladder (S1): the three numbers notebook 01 and the S1-c7 video print -----

def test_the_ladder_prints_the_three_rungs_the_session_showed(ladder):
    assert ladder["leakage.honest.auc"].text() == "0.7299"
    assert ladder["leakage.truepd.auc"].text() == "0.8326"
    assert ladder["leakage.label.auc"].text() == "1.0000"
    assert ladder["leakage.truepd.gain"].text() == "0.10"


def test_the_ladder_is_measured_on_the_score_splits_held_out_rows(ladder):
    pops = {ladder[k].population for k in ("leakage.honest.auc", "leakage.truepd.auc",
                                           "leakage.label.auc", "leakage.truepd.alone_auc")}
    assert pops == {"held-out 20% of applicants (score split, seed 42)"}


def test_no_model_leaking_the_true_pd_beats_the_true_pd_itself(ladder):
    # the point of H1.3: the outcome is a draw on the PD, so the truth ranks below 1.0
    assert ladder["leakage.truepd.auc"].value < ladder["leakage.truepd.alone_auc"].value < 0.9


def test_dgp_truth_only_in_ceiling():
    assert "pd_default_origination" not in (ROOT / "wiki/facts/leakage.py").read_text()
    assert "pd_default_origination" in (ROOT / "wiki/facts/ceiling.py").read_text()


def test_the_probe_matches_the_s1_lab_sheet():
    """The facts fit the rungs the way the lab sheet's leakage_probe.py does."""
    from wiki.facts.leakage import HONEST, PROBE_SEED
    lab = (ROOT / "workshop/labs/S1-lab.md").read_text()
    assert str(HONEST).replace("'", '"') in lab
    assert f"random_state={PROBE_SEED}" in lab and "LGBMClassifier(verbose=-1)" in lab


# --- adjudication over the whole book (S3-c2) and the H3.1 what-if -----------------------

@pytest.fixture(scope="module")
def adj(split):
    from wiki.facts import adj_facts
    return adj_facts.compute(split)


def test_the_book_mix_is_the_one_session_3_showed(adj):
    assert [adj[f"adj.book.{k}.n"].text() for k in ("Approve", "Refer", "Decline")] == \
        ["3,760", "4,229", "4,011"]


def test_the_book_mix_equals_the_portal(adj):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        decisions = app.state.decisions["decision"]
    for k in ("Approve", "Refer", "Decline"):
        assert int((decisions == k).sum()) == adj[f"adj.book.{k}.n"].value


def test_the_dscr_whatif_only_moves_refers_to_decline(adj):
    assert adj["adj.dscr_whatif.floor"].value == json.loads(
        (ROOT / "adjudication/models/policy_config.json").read_text())["dscr_refer_hi"]
    assert adj["adj.dscr_whatif.Approve.n"].value == adj["adj.book.Approve.n"].value
    assert adj["adj.dscr_whatif.approve_below_floor"].value == 0
    assert adj["adj.dscr_whatif.flipped"].value == adj["adj.dscr_whatif.refer_to_decline"].value
    assert adj["adj.dscr_whatif.flipped"].text() == "1,282"


# --- the rounded-prob re-tier (H3.3, the v2 what-if defect) -------------------------------

@pytest.fixture(scope="module")
def ews():
    os.chdir(ROOT)
    from wiki.facts import ews_facts
    return ews_facts.compute()


def test_rounded_retier_matches_score_populations_own_columns(ews):
    """Independent of the facts' path: re-tier score_population's persisted prob column and
    compare with its own risk_tier column."""
    from ews.src import watchlist as wl
    book = wl.score_population()
    tiers = json.loads((ROOT / "ews/models/metadata.json").read_text())["tiers"]
    rounded = np.array([wl.risk_tier(p, tiers) for p in book["prob"]])
    flipped = sorted(book["business_id"][rounded != book["risk_tier"].to_numpy()])
    n = ews["ews.rounded_retier.n_flipped"].value
    assert flipped == [ews[f"ews.rounded_retier.flip{j}.business_id"].value
                       for j in range(1, n + 1)]
    assert np.array_equal(np.round(book["prob"].to_numpy(), ews["ews.rounded_retier.dp"].value),
                          book["prob"].to_numpy())


def test_rounded_retier_is_the_defect_claude_md_records(ews):
    assert ews["ews.rounded_retier.n_flipped"].text() == "2"
    flips = {ews[f"ews.rounded_retier.flip{j}.business_id"].value:
             (ews[f"ews.rounded_retier.flip{j}.batch"].value,
              ews[f"ews.rounded_retier.flip{j}.rounded"].value) for j in (1, 2)}
    assert flips == {"BIZ108170": ("Medium", "High"), "BIZ103657": ("Low", "Medium")}
    for j in (1, 2):   # each unrounded prob sits just below the cutoff it rounds onto
        p = ews[f"ews.rounded_retier.flip{j}.prob"].value
        cut = ews[f"ews.rounded_retier.flip{j}.cutoff"].value
        assert p < cut == round(p, 4)
