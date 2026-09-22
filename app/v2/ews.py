"""Per-loan early-warning read path: the account's actual 24-month behavioural
series, the fired triggers with their thresholds and this account's value against
each, the SHAP drivers, and the model's own limits displayed beside its output.

score_population (ews/src/watchlist.py) already aggregates util_recent, util_drift,
dpd_max, deposit_decline_pct and overdraft_recent per account and evaluates
flag_triggers over them -- this module only surfaces what it already computed. It
never re-evaluates a trigger comparator itself, so this screen cannot disagree with
the batch watchlist.
"""
from __future__ import annotations

from shared.config import EWS_TRIGGERS
from app.v2.explain import _booked_row

_TRIGGER_SPECS = [
    ("HIGH_UTILIZATION", "util_recent", ">", "high_utilization"),
    ("RISING_UTILIZATION", "util_drift", ">", "rising_utilization"),
    ("DELINQUENCY", "dpd_max", ">=", "dpd_severe"),
    ("DEPOSIT_DECLINE", "deposit_decline_pct", ">", "deposit_decline"),
    ("FREQUENT_OVERDRAFTS", "overdraft_recent", ">=", "overdraft_recent"),
]

_PANEL_SERIES = ["utilization", "balance", "deposit_inflow",
                 "days_past_due", "overdraft_count"]


def _trigger_rows(ews_row, cfg: dict, fired_names: set[str]) -> list[dict]:
    """Threshold and value for every trigger, with fired taken from flag_triggers --
    never recomputed here, so this screen cannot disagree with the module."""
    rows = []
    for name, value_key, comparator, cfg_key in _TRIGGER_SPECS:
        rows.append({
            "name": name, "value_key": value_key, "comparator": comparator,
            "threshold": float(cfg[cfg_key]),
            "value": round(float(ews_row.get(value_key, 0.0)), 4),
            "fired": name in fired_names,
        })
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
        "triggers": _trigger_rows(e, EWS_TRIGGERS, set(e["triggers"])),
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
