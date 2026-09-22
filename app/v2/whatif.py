"""The write path: overrides in, recomputed numbers out.

Every function here does the same three things -- take the committed configuration,
apply the caller's overrides, and hand the result to the module function the batch
pipeline calls. It never re-implements the calculation. That is what makes the
guarantee testable: an empty override body must reproduce the batch numbers exactly.

Step 4's probe confirmed `app_state.profiles.assign(business_score=...)` reproduces
v1's decisions and reasons exactly against every one of the 12,000 applicants (v1
calls decide() on compute_adjudication_features(biz), but every column decide() reads
-- dscr, leverage, public_records, prior_delinquencies, business_score,
requested_amount, annual_revenue -- passes through that function unmodified). The
cheaper frame is used deliberately, not by default.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from adjudication.src.policy import PolicyConfig, decide


class DecisionOverrides(BaseModel):
    t_low: float | None = Field(default=None, ge=0.0, le=1.0)
    t_high: float | None = Field(default=None, ge=0.0, le=1.0)
    dscr_floor: float | None = Field(default=None, ge=0.0, le=10.0)
    dscr_refer_hi: float | None = Field(default=None, ge=0.0, le=10.0)
    public_records_cap: int | None = Field(default=None, ge=0, le=20)
    prior_delinq_cap: int | None = Field(default=None, ge=0, le=20)
    leverage_cap: float | None = Field(default=None, ge=0.0, le=50.0)
    req_to_rev_cap: float | None = Field(default=None, ge=0.0, le=10.0)
    score_floor: float | None = Field(default=None, ge=300, le=850)

    def apply_to(self, config: PolicyConfig) -> PolicyConfig:
        d = config.to_dict()
        d.update({k: v for k, v in self.model_dump().items() if v is not None})
        return PolicyConfig.from_dict(d)


def decision_whatif(app_state, business_id: str, overrides: DecisionOverrides) -> dict:
    from app.v2 import explain, rules

    p = explain._row(app_state, business_id)  # UnknownLoan before any computation
    s = app_state.scores.loc[business_id]

    base_config = app_state.policy_config
    config = overrides.apply_to(base_config)

    pd_model = app_state.decisions["pd"].to_numpy()
    redecided = decide(app_state.profiles.assign(
        business_score=app_state.scores["business_score"]), pd_model, config)

    row = redecided.loc[business_id]
    pd_value = float(pd_model[app_state.profiles.index.get_loc(business_id)])
    zone = explain._zone(pd_value, config)
    led = rules.ledger(p, s, config, zone)
    flipped = int((redecided["decision"].to_numpy()
                   != app_state.decisions["decision"].to_numpy()).sum())
    return {
        "business_id": business_id,
        "decision": str(row["decision"]),
        "zone": zone,
        "rule_hits": list(row["decision_reasons"]),
        "rules": led,
        "nearest_flip": rules.nearest_flip(led, pd_value, config),
        "book_mix": {k: int(v) for k, v in
                     redecided["decision"].value_counts().items()},
        "flipped_count": flipped,
        "config": config.to_dict(),
    }
