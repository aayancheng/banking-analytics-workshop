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

from shared.config import EWS_TRIGGERS
from app.v2.explain import _booked_row

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
