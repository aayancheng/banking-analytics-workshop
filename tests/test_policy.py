"""Policy layer — knockouts dominate, zones split, refers only downgrade."""
import pandas as pd

from shared.config import ADJ_POLICY
from adjudication.src.policy import PolicyConfig, decide

CFG = PolicyConfig.from_dict(ADJ_POLICY)


def _frame(**cols):
    base = {"dscr": 2.0, "leverage": 1.0, "public_records": 0, "prior_delinquencies": 0,
            "business_score": 700, "requested_amount": 100_000, "annual_revenue": 1_000_000}
    base.update(cols)
    return pd.DataFrame([base])


def test_knockout_beats_low_pd():
    dec = decide(_frame(dscr=0.5), [0.01], CFG)
    assert dec["decision"].iloc[0] == "Decline"
    assert any("dscr" in r for r in dec["decision_reasons"].iloc[0])


def test_pd_zones():
    assert decide(_frame(), [CFG.t_low], CFG)["decision"].iloc[0] == "Approve"
    assert decide(_frame(), [CFG.t_high], CFG)["decision"].iloc[0] == "Decline"
    mid = (CFG.t_low + CFG.t_high) / 2
    assert decide(_frame(), [mid], CFG)["decision"].iloc[0] == "Refer"


def test_refer_override_downgrades_approve_only():
    # thin dscr downgrades an approve-zone applicant…
    thin = decide(_frame(dscr=(CFG.dscr_floor + CFG.dscr_refer_hi) / 2), [0.01], CFG)
    assert thin["decision"].iloc[0] == "Refer"
    # …but never upgrades a decline-zone one
    still_decline = decide(_frame(dscr=(CFG.dscr_floor + CFG.dscr_refer_hi) / 2),
                           [CFG.t_high + 0.1], CFG)
    assert still_decline["decision"].iloc[0] == "Decline"


def test_weak_score_refers():
    dec = decide(_frame(business_score=CFG.score_floor - 50), [0.01], CFG)
    assert dec["decision"].iloc[0] == "Refer"
    assert "weak credit score" in dec["decision_reasons"].iloc[0]
