"""The leakage ladder (Session 1): the probe in notebook 01 (the leakage cell) and in
workshop/labs/S1-lab.md, recomputed. Four honest features, then the same four plus one
leaked column, each fitted with an untuned LightGBM on the same stratified 80/20 split.

Two rungs live here: the honest model and the label leak (`default`, the outcome itself).
The middle rung leaks the generator's true PD -- DGP truth -- so
it is computed in wiki/facts/ceiling.py, the one place the facts may read DGP truth; it
calls probe_auc below so all three rungs are fitted identically.

The probe's split is train_test_split(X, y, test_size=0.2, random_state=42, stratify=y) on
the 12,000 applicants, which puts exactly the score split's rows on each side; compute()
asserts it, so the population is the scorecard's held-out 20%."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from wiki.facts.core import Fact

HONEST = ["dscr", "leverage", "utilization", "prior_delinquencies"]   # notebook 01, S1 lab
PROBE_SEED = 42                     # the probe's own literal random_state (= shared SEED)
SRC = ("wiki.facts.leakage.probe_auc (notebook 01 leakage cell / S1 lab leakage_probe.py: "
       "LGBMClassifier(verbose=-1) on four honest features{})")
POP = "held-out 20% of applicants (score split, seed 42)"


def probe_auc(X: pd.DataFrame, y: pd.Series, split=None) -> float:
    """One rung, exactly as the probe fits it. With `split`, assert the probe's own split
    puts the score split's held-out rows on the test side."""
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=PROBE_SEED,
                                          stratify=y)
    if split is not None:
        assert np.array_equal(Xte.index.to_numpy(), split.idx_te), \
            "the leakage probe's split no longer matches the score split"
    from lightgbm import LGBMClassifier
    model = LGBMClassifier(verbose=-1).fit(Xtr, ytr)
    return float(roc_auc_score(yte, model.predict_proba(Xte)[:, 1]))


def compute(split) -> dict[str, Fact]:
    b = split.biz
    X_ok, y = b[HONEST], b["default"]
    honest = probe_auc(X_ok, y, split)
    label = probe_auc(X_ok.assign(cheat=b["default"]), y, split)
    return {
        "leakage.n_honest": Fact(len(HONEST), "d", "wiki.facts.leakage.HONEST",
                                 "module constant"),
        "leakage.honest.auc": Fact(honest, ".4f", SRC.format(""), POP),
        "leakage.label.auc": Fact(label, ".4f",
                                  SRC.format(" plus the label `default` itself"), POP),
    }
