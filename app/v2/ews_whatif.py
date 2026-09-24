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
from app.v2.ews import prob_display, trigger_rows
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


def retier_book(app_state, overrides: EwsOverrides) -> list[str]:
    """Every booked account's tier under these cutoffs, in app_state.ews order,
    ALWAYS from the unrounded probability (app_state.v2.ews_prob_raw) -- the number
    score_population itself passes to risk_tier.

    There is deliberately no "cutoffs untouched" shortcut. The first version reused
    the batch risk_tier column for an empty body and re-tiered from the persisted
    4dp prob otherwise; the tab re-sends t_med/t_high on EVERY drag, so moving an
    unrelated trigger slider took the rounded path and moved BIZ108170 Medium ->
    High and BIZ103657 Low -> Medium (book 5835/1668/833 -> 5834/1668/834). One
    path, the right input, for every body.
    """
    tiers = overrides.tiers(app_state.ews_meta["tiers"])
    return [risk_tier(p, tiers) for p in app_state.v2.ews_prob_raw.to_numpy(dtype=float)]


def ews_whatif(app_state, business_id: str, overrides: EwsOverrides):
    """Re-tier with risk_tier and re-flag with flag_triggers, the functions
    score_population uses, on the same inputs it uses: the unrounded probability
    (retier_book, above) and the EWS feature frame. So any body carrying the
    committed values -- empty, or explicit as the tab sends them -- reproduces the
    watchlist exactly, and a moved cutoff re-tiers from the true probability rather
    than from a 4dp display copy of it.
    """
    _, booked = _booked_row(app_state, business_id)  # UnknownLoan before computation
    if not booked:
        return None

    ews = app_state.ews
    feats = app_state.v2.ews_feats
    tiers = overrides.tiers(app_state.ews_meta["tiers"])
    cfg = overrides.trigger_cfg()

    retiered = retier_book(app_state, overrides)
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
        **prob_display(app_state, business_id, tiers),
        "risk_tier": retiered[pos],
        "tiers": tiers,
        "triggers": trigger_rows(feats.loc[business_id], cfg, fired),
        "trigger_config": cfg,
        "book_tiers": book_tiers,
        "book_trigger_counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
    }
