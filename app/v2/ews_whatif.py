"""Early-warning what-if: tier cutoffs and trigger thresholds in, a re-tiered and
re-flagged book out.

Lives beside app/v2/whatif.py rather than in it -- whatif.py was already at 145 of
~150 lines after Task 7 pricing/decision overrides, with no room left. Re-tiering
calls risk_tier and re-flagging calls flag_triggers, the same functions
score_population uses, so an empty override body reproduces the watchlist exactly.
`fired` always comes from flag_triggers' own output, never from a clause's `met`
flag -- `met` explains a verdict, it never decides one.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from shared.config import EWS_TRIGGERS
from app.v2.explain import _booked_row
from app.v2.ews import trigger_rows
from app.v2.whatif import InvalidOverride
from ews.src.triggers import flag_triggers
from ews.src.watchlist import risk_tier


class EwsOverrides(BaseModel):
    t_high: float | None = Field(default=None, ge=0.0, le=1.0)
    t_med: float | None = Field(default=None, ge=0.0, le=1.0)
    high_utilization: float | None = Field(default=None, ge=0.0, le=2.0)
    rising_utilization: float | None = Field(default=None, ge=-1.0, le=2.0)
    dpd_severe: int | None = Field(default=None, ge=0, le=180)
    deposit_decline: float | None = Field(default=None, ge=0.0, le=1.0)
    overdraft_recent: int | None = Field(default=None, ge=0, le=50)

    def tiers(self, base: dict) -> dict:
        """Merge onto the committed cutoffs and reject an inverted band: t_med=0.9
        is in range alone but empties the Medium tier once merged with a committed
        t_high -- the same trap DecisionOverrides guards for t_low/t_high."""
        d = dict(base)
        for k in ("t_high", "t_med"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        if d["t_med"] > d["t_high"]:
            raise InvalidOverride(
                f"t_med ({d['t_med']:.4f}) must not exceed t_high ({d['t_high']:.4f}): "
                "an inverted tier band empties the Medium tier")
        return d

    def trigger_cfg(self) -> dict:
        d = dict(EWS_TRIGGERS)
        d.update({k: v for k, v in self.model_dump(
            exclude={"t_high", "t_med"}).items() if v is not None})
        return d


def ews_whatif(app_state, business_id: str, overrides: EwsOverrides):
    """Re-tier with risk_tier and re-flag with flag_triggers, the functions
    score_population uses, so an empty override body reproduces the watchlist
    exactly.

    score_population computes risk_tier from the model's unrounded probability but
    only persists prob rounded to 4dp, so two of 8,336 accounts sit exactly on a
    cutoff after rounding and re-deriving their tier from the rounded prob flips
    both. An unmodified tier config sidesteps this by reusing the batch's own
    risk_tier column rather than reconstructing it from that lossy value.

    A moved cutoff has no such column to fall back on: it re-tiers every account
    from the same rounded prob, so a dragged threshold that happens to land exactly
    on a rounded value carries the identical imprecision, with no batch figure to
    compare against. That is not fixed here and cannot be from v2 state alone -- no
    unrounded probability is cached anywhere; only the retrained model has it.
    """
    _, booked = _booked_row(app_state, business_id)  # UnknownLoan before computation
    if not booked:
        return None

    ews = app_state.ews
    feats = app_state.v2.ews_feats
    tiers = overrides.tiers(app_state.ews_meta["tiers"])
    cfg = overrides.trigger_cfg()

    if overrides.t_high is None and overrides.t_med is None:
        retiered = list(ews["risk_tier"])
    else:
        retiered = [risk_tier(p, tiers) for p in ews["prob"].to_numpy(dtype=float)]
    refired = flag_triggers(feats, cfg)
    pos = feats.index.get_loc(business_id)
    fired = set(refired[pos])

    counts: dict[str, int] = {}
    for lst in refired:
        for t in lst:
            counts[t] = counts.get(t, 0) + 1
    book_tiers: dict[str, int] = {}
    for t in retiered:
        book_tiers[t] = book_tiers.get(t, 0) + 1

    return {
        "business_id": business_id,
        "prob": float(ews.loc[business_id, "prob"]),
        "risk_tier": retiered[pos],
        "tiers": tiers,
        "triggers": trigger_rows(feats.loc[business_id], cfg, fired),
        "trigger_config": cfg,
        "book_tiers": book_tiers,
        "book_trigger_counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
    }
