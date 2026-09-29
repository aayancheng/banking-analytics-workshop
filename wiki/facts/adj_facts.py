"""Adjudication headline facts, read from the module's committed artifacts. Enough for the
S4 lab to draft D5 against; the full D5 facts arrive with the D5 chapter."""
from __future__ import annotations

import json

from shared.config import MARKET, ROOT
from wiki.facts.core import Fact

HOLDOUT = "held-out 20% of applicants (adjudication split, seed 42, same 12,000 rows as score)"
META = "adjudication/models/metadata.json"
POLICY = "adjudication/models/policy_config.json"


def compute() -> dict[str, Fact]:
    m = json.loads((ROOT / META).read_text())
    p = json.loads((ROOT / POLICY).read_text())
    f = {
        "adj.auc": Fact(float(m["metrics"]["auc"]), ".4f", META, HOLDOUT),
        "adj.lift": Fact(float(m["metrics"]["top20_lift"]), ".2f", META, HOLDOUT),
        "adj.gate_auc": Fact(float(m["gate"]["auc_min"]), ".2f", META, HOLDOUT),
        "adj.gate_lift": Fact(float(m["gate"]["lift_min"]), ".1f", META, HOLDOUT),
        "adj.t_low": Fact(float(p["t_low"]), ".4f", POLICY, "calibrated at train time"),
        "adj.t_high": Fact(float(p["t_high"]), ".4f", POLICY, "calibrated at train time"),
        "adj.n_train": Fact(int(m["train_rows"]), ",d", META, "training 80% of applicants"),
        "adj.n_test": Fact(int(m["test_rows"]), ",d", META, HOLDOUT),
        "adj.n_features": Fact(len(m["ADJ_FEATURE_COLUMNS"]), "d", META, HOLDOUT),
        "market.roe_hurdle": Fact(float(MARKET["roe_hurdle"]), ".0%",
                                  "shared.config.MARKET", "platform assumption"),
    }
    for k, v in m["decision_mix_test"].items():
        f[f"adj.mix.{k}"] = Fact(float(v), ".1%", META, HOLDOUT)
    return f
