import os

import pytest

from shared.config import ROOT


@pytest.mark.slow
def test_stress_refits_reproduce_the_s2_numbers():
    os.chdir(ROOT)
    from wiki.facts import score_stress
    from wiki.facts.data import score_split
    f = {k: v.text() for k, v in score_stress.compute(score_split()).items()}
    assert f["score.stress.no_bureau.auc"] == "0.7704"
    assert f["score.stress.no_bureau.ks"] == "0.4334"
    assert f["score.stress.five_raw.auc"] == "0.7804"
    assert f["score.stress.structural_five.auc"] == "0.50"
    assert f["score.stress.proxy_five.auc"] == "0.62"
