"""The policy layer as a per-loan ledger: every rule, its threshold, this loan's
value, and whether it fired.

policy.decide() returns only the reasons that fired. A screen that is trying to
explain a decision needs the rules that did NOT fire just as much -- that is the
difference between "declined for leverage" and "passed everything except leverage".
The thresholds and comparators here are read from the same PolicyConfig the batch
pipeline uses; only the presentation is new.
"""
from __future__ import annotations

from app.v2.display import display_precision

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
    """Three distinct facts per rule, because conflating them makes the screen lie.

      condition_met -- the comparator is true for this loan
      applicable    -- this rule can bite this loan at all
      fired         -- it actually contributed to the decision (both of the above)

    A refer override only downgrades a loan the PD zones would have APPROVED. On a
    loan already in the Refer zone its comparator can be true while it changed
    nothing. Reporting that as `fired` disagreed with policy.decide's own rule_hits
    on 43.4% of applicants -- BIZ100052 is the case: v1 says "rule hits: none" while
    the ledger claimed two fired. `fired` means "this rule contributed" everywhere
    else in this codebase (Task 8 fixed the identical confusion for EWS triggers), so
    it has to mean that here too.
    """
    out = []
    for rule, label, value_key, comparator, config_key in specs:
        threshold = float(getattr(config, config_key))
        value = values[value_key]
        condition_met = bool(_OPS[comparator](value, threshold))
        # value is rounded at the server-chosen dp (>= 4, never fewer than before),
        # so a value a hair across its threshold cannot print equal to it.
        prec = display_precision(value, threshold)
        out.append({
            "rule": rule, "label": label, "value_key": value_key,
            "comparator": comparator, "threshold": threshold,
            "value": round(value, prec["dp"]), "dp": prec["dp"], "tied": prec["tied"],
            "condition_met": condition_met,
            "applicable": applicable,
            "fired": bool(condition_met and applicable),
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
            # the band is two-sided: below the floor the knockout already fired
            r["condition_met"] = bool(r["condition_met"]
                                      and values["dscr"] >= float(config.dscr_floor))
            r["fired"] = bool(r["condition_met"] and r["applicable"])
            r["label"] = (f"Thin affordability margin "
                          f"({config.dscr_floor} <= DSCR < {config.dscr_refer_hi})")
    return {
        "knockouts": _rows(KNOCKOUTS, values, config, applicable=True),
        "refer_overrides": refer,
    }


def nearest_flip(led: dict, pd_value: float, config) -> dict:
    """Which single lever is closest to changing this decision.

    Ranked by distance-to-cross divided by the rule's own scale, so thresholds on
    different scales compare. Distance-to-cross is how far this loan's value must move
    to trip the rule -- for an integer count rule with a `>` comparator sitting exactly
    on its cap, that is one whole record, not zero.

    A threshold of exactly 0 has no meaningful relative scale, so it falls back to unit
    scale. It is NEVER dropped. An earlier version skipped every zero threshold, which
    silently made `public_records_cap` unrankable on 11,041 of the 12,000 applicants --
    every loan sitting exactly on the cap, which is the tightest margin a rule can have.
    """
    INTEGER_COUNT_RULES = {"public_records_cap"}
    candidates = []
    for r in led["knockouts"] + led["refer_overrides"]:
        if not r["applicable"]:
            continue
        distance = abs(r["value"] - r["threshold"])
        if r["rule"] in INTEGER_COUNT_RULES and r["comparator"] == ">" and not r["fired"]:
            distance = max(distance, 1.0)   # only trips at the next whole record
        scale = abs(r["threshold"]) or 1.0
        candidates.append({
            "lever": r["rule"], "label": r["label"], "value": r["value"],
            "threshold": r["threshold"], "distance_to_cross": round(distance, 4),
            "gap": round(distance / scale, 4), "at_threshold": r["value"] == r["threshold"],
            "currently_firing": r["fired"],
        })
    for name, t in (("t_low", float(config.t_low)), ("t_high", float(config.t_high))):
        candidates.append({
            "lever": name, "label": f"PD zone cutoff {name}", "value": pd_value,
            "threshold": t, "distance_to_cross": round(abs(pd_value - t), 6),
            "gap": round(abs(pd_value - t) / (abs(t) or 1.0), 4),
            "at_threshold": False, "currently_firing": None,
        })
    for c in candidates:
        # I6: the PD levers carry the unrounded pd_value, which the tab printed
        # via String() at 16 digits; dp is the server's choice, like every clause.
        c.update(display_precision(c["value"], c["threshold"]))
    if not candidates:
        return {}
    ranked = sorted(candidates, key=lambda c: c["gap"])
    return {**ranked[0], "candidates": ranked}
