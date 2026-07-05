"""Named early-warning trigger flags: a pure, vectorized rule layer surfaced alongside the
model probability. Thresholds come from shared.config.EWS_TRIGGERS."""
import numpy as np
import pandas as pd

from shared.config import EWS_TRIGGERS


def flag_triggers(features: pd.DataFrame, cfg: dict | None = None) -> list[list[str]]:
    cfg = cfg or EWS_TRIGGERS
    n = len(features)

    def col(name):
        return (pd.to_numeric(features[name], errors="coerce").fillna(0.0).to_numpy()
                if name in features.columns else np.zeros(n))

    util_recent = col("util_recent"); util_drift = col("util_drift")
    dpd_max = col("dpd_max"); dpd_recent = col("dpd_recent")
    deposit_decline = col("deposit_decline_pct"); overdraft_recent = col("overdraft_recent")

    rules = [
        ("HIGH_UTILIZATION", util_recent > cfg["high_utilization"]),
        ("RISING_UTILIZATION", util_drift > cfg["rising_utilization"]),
        ("DELINQUENCY", (dpd_max >= cfg["dpd_severe"]) | (dpd_recent > 0)),
        ("DEPOSIT_DECLINE", deposit_decline > cfg["deposit_decline"]),
        ("FREQUENT_OVERDRAFTS", overdraft_recent >= cfg["overdraft_recent"]),
    ]
    out = [[] for _ in range(n)]
    for name, mask in rules:
        for i in np.nonzero(mask)[0]:
            out[i].append(name)
    return out
