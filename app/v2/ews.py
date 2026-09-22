"""Per-loan early-warning read path: the account's actual 24-month behavioural
series, the fired triggers with their clauses' thresholds and this account's value
against each, the SHAP drivers, and the model's own limits displayed beside its
output.

score_population (ews/src/watchlist.py) already aggregates the behavioural features
per account and evaluates flag_triggers over them -- this module only surfaces what
it already computed. `fired` is always the module's verdict, taken from
flag_triggers' own output and never recomputed here.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from shared.config import EWS_TRIGGERS
from app.v2.explain import _booked_row
from app.v2.whatif import InvalidOverride
from ews.src.triggers import flag_triggers
from ews.src.watchlist import risk_tier

# Each trigger is a LIST of clauses joined by OR, because flag_triggers' DELINQUENCY
# rule is compound: (dpd_max >= dpd_severe) | (dpd_recent > 0). Representing it as the
# single dpd_max clause made the screen contradict itself on every account where it
# fires -- all 4,225 of them (50.7% of the book) trip the recent clause with dpd_max
# below 30, so the row read "value 2, threshold 30, FIRED". A clause's threshold
# source is a config key, or a literal number where the rule has one (dpd_recent > 0).
_TRIGGER_SPECS = [
    ("HIGH_UTILIZATION",    [("util_recent", ">", "high_utilization")]),
    ("RISING_UTILIZATION",  [("util_drift", ">", "rising_utilization")]),
    ("DELINQUENCY",         [("dpd_max", ">=", "dpd_severe"),
                             ("dpd_recent", ">", 0)]),
    ("DEPOSIT_DECLINE",     [("deposit_decline_pct", ">", "deposit_decline")]),
    ("FREQUENT_OVERDRAFTS", [("overdraft_recent", ">=", "overdraft_recent")]),
]

_CLAUSE_OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b}

_PANEL_SERIES = ["utilization", "balance", "deposit_inflow",
                 "days_past_due", "overdraft_count"]


def _trigger_rows(feat_row, cfg: dict, fired_names: set[str]) -> list[dict]:
    """Every trigger's clauses with their thresholds and this account's values, and
    `fired` taken from flag_triggers -- never recomputed here.

    `fired` is the module's verdict. `met` on each clause is display metadata that
    EXPLAINS that verdict. They must always agree (a fired trigger has at least one
    met clause); a test asserts it across the whole book, because a screen showing
    "value 2, threshold 30, FIRED" destroys trust in every other number on it.

    feat_row comes from the EWS FEATURE frame, not the scored watchlist row: the
    watchlist carries only KEY_METRICS, which excludes dpd_recent, so reading clause
    values off it would silently show 0.0 for the clause that actually fired.
    """
    rows = []
    for name, clauses in _TRIGGER_SPECS:
        spelled = []
        for metric, comparator, source in clauses:
            threshold = float(cfg[source]) if isinstance(source, str) else float(source)
            value = float(feat_row.get(metric, 0.0))
            spelled.append({
                "metric": metric, "comparator": comparator, "threshold": threshold,
                "value": round(value, 4),
                "met": bool(_CLAUSE_OPS[comparator](value, threshold)),
            })
        rows.append({"name": name, "join": "OR", "clauses": spelled,
                     "fired": name in fired_names})
    return rows


def ews_detail(app_state, business_id: str):
    _, booked = _booked_row(app_state, business_id)
    if not booked:
        return None
    e = app_state.ews.loc[business_id]
    meta = app_state.ews_meta
    panel = app_state.v2.panel.loc[[business_id]].sort_values("month_index")
    return {
        "business_id": business_id,
        "prob": float(e["prob"]),
        "risk_tier": str(e["risk_tier"]),
        "tiers": meta["tiers"],
        "triggers": _trigger_rows(app_state.v2.ews_feats.loc[business_id],
                                  EWS_TRIGGERS, set(e["triggers"])),
        "panel": {
            "months": [int(m) for m in panel["month_index"]],
            "series": {c: [float(v) for v in panel[c]] for c in _PANEL_SERIES},
        },
        "drivers": [{"feature": r["feature"], "impact": r["impact"]}
                    for r in e["top_shap_reasons"]],
        "model_caveat": {
            "top_decile_capture": meta["metrics"]["top_decile_capture"],
            "top_decile_lift": meta["metrics"]["top_decile_lift"],
            "auc": meta["metrics"]["auc"],
            "auc_is_gated": False,
            "base_rate": meta["base_rate"],
            "note": ("Gated on top-decile capture, not AUC: the data-generating "
                     "process puts a real ceiling on separability. Held-out numbers."),
        },
    }


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
    exactly. `fired` always comes from flag_triggers' own output, never from a
    clause's `met` flag.

    score_population computes risk_tier from the model's unrounded probability but
    only persists prob rounded to 4dp, so two of 8,336 accounts sit exactly on a
    cutoff after rounding and recomputing from the rounded prob would flip their
    tier. An unmodified tier config reuses the batch's own risk_tier column rather
    than re-deriving it from a lossy value -- the empty-override guarantee needs
    the module's actual output, not a reconstruction of it.
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
        "triggers": _trigger_rows(feats.loc[business_id], cfg, fired),
        "trigger_config": cfg,
        "book_tiers": book_tiers,
        "book_trigger_counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
    }
