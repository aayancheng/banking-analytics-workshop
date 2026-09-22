"""The policy layer as a per-loan ledger: every rule, its threshold, this loan's
value, and whether it fired.

policy.decide() returns only the reasons that fired. A screen that is trying to
explain a decision needs the rules that did NOT fire just as much -- that is the
difference between "declined for leverage" and "passed everything except leverage".
The thresholds and comparators here are read from the same PolicyConfig the batch
pipeline uses; only the presentation is new.
"""
from __future__ import annotations

KNOCKOUTS = [
    ("dscr_floor", "DSCR below floor", "dscr", "<", "dscr_floor"),
    ("public_records_cap", "Public records present", "public_records", ">", "public_records_cap"),
    ("prior_delinq_cap", "Prior delinquencies at cap", "prior_delinquencies", ">=", "prior_delinq_cap"),
    ("leverage_cap", "Leverage above cap", "leverage", ">", "leverage_cap"),
]

REFER_OVERRIDES = [
    ("dscr_refer_hi", "Thin affordability margin", "dscr", "<", "dscr_refer_hi"),
    ("score_floor", "Weak credit score", "business_score", "<", "score_floor"),
    ("req_to_rev_cap", "Large request vs revenue", "req_to_rev", ">", "req_to_rev_cap"),
]

_OPS = {"<": lambda a, b: a < b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}


def loan_values(profile_row, score_row) -> dict:
    """The seven numbers the policy layer looks at, for one loan."""
    rev = max(float(profile_row["annual_revenue"]), 1.0)
    return {
        "dscr": float(profile_row["dscr"]),
        "leverage": float(profile_row["leverage"]),
        "public_records": float(profile_row["public_records"]),
        "prior_delinquencies": float(profile_row["prior_delinquencies"]),
        "business_score": float(score_row["business_score"]),
        "req_to_rev": float(profile_row["requested_amount"]) / rev,
    }


def _rows(specs, values, config, applicable) -> list[dict]:
    out = []
    for rule, label, value_key, comparator, config_key in specs:
        threshold = float(getattr(config, config_key))
        value = values[value_key]
        out.append({
            "rule": rule, "label": label, "value_key": value_key,
            "comparator": comparator, "threshold": threshold,
            "value": round(value, 4),
            "fired": bool(_OPS[comparator](value, threshold)),
            "applicable": applicable,
        })
    return out


def ledger(profile_row, score_row, config, decision_zone: str) -> dict:
    """decision_zone is the PD-zone verdict BEFORE overrides, because a refer
    override only applies to a loan the PD zones would have approved."""
    values = loan_values(profile_row, score_row)
    # dscr_refer_hi only bites above the floor -- below it the knockout already fired.
    refer = _rows(REFER_OVERRIDES, values, config, applicable=decision_zone == "Approve")
    for r in refer:
        if r["rule"] == "dscr_refer_hi":
            r["fired"] = bool(r["fired"] and values["dscr"] >= float(config.dscr_floor))
            r["label"] = (f"Thin affordability margin "
                          f"({config.dscr_floor} <= DSCR < {config.dscr_refer_hi})")
    return {
        "knockouts": _rows(KNOCKOUTS, values, config, applicable=True),
        "refer_overrides": refer,
    }


def nearest_flip(led: dict, pd_value: float, config) -> dict:
    """Which single lever is closest to changing this decision, in relative terms.

    Relative distance so thresholds on different scales compare: a DSCR 0.05 from
    its floor and a score 30 points from its floor are both ~5%.
    """
    candidates = []
    for r in led["knockouts"] + led["refer_overrides"]:
        if not r["applicable"] or r["threshold"] == 0:
            continue
        gap = abs(r["value"] - r["threshold"]) / max(abs(r["threshold"]), 1e-9)
        candidates.append({"lever": r["rule"], "label": r["label"],
                           "value": r["value"], "threshold": r["threshold"],
                           "relative_gap": round(gap, 4),
                           "currently_firing": r["fired"]})
    for name, t in (("t_low", float(config.t_low)), ("t_high", float(config.t_high))):
        gap = abs(pd_value - t) / max(t, 1e-9)
        candidates.append({"lever": name, "label": f"PD zone cutoff {name}",
                           "value": round(pd_value, 4), "threshold": t,
                           "relative_gap": round(gap, 4), "currently_firing": None})
    return min(candidates, key=lambda c: c["relative_gap"]) if candidates else {}
