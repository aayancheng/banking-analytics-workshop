"""Server-chosen display precision for a value shown beside its threshold.

Follows ledgers.py's display_triple precedent: the server picks how many decimals
make a comparison honest, never the browser. A fixed precision chosen client-side is
tuned to today's data and silently breaks on a retrain -- Task 15's first draft
hardcoded 6dp for one clause because that happened to separate BIZ101719's PD from
its cap, but measuring every screen found the real problem wasn't precision, it was
that NO fixed precision is safe: EWS's RISING_UTILIZATION fires on BIZ106189 at
util_drift 0.15000000000000013 against a config 0.15 -- a difference of 1.3e-16, pure
float noise, at which the screen printed "0.15 > 0.15 -- FIRED": a comparison that
reads false next to a status that says true.

display_precision finds the fewest decimals at which a value and its threshold render
DIFFERENTLY, so a strict comparator is never shown printing two equal numbers.
`tied` is True when nothing up to max_dp separates them -- genuinely equal, or apart
only by float noise -- and the caller should then say the value is AT the threshold
rather than draw a comparison that looks false. Whether the rule fired/passed is
always the module's own verdict; this function never decides it and is never used to
recompute one.
"""
from __future__ import annotations


def display_precision(value: float, threshold: float,
                       base_dp: int = 4, max_dp: int = 8) -> dict:
    """The fewest decimals at which `value` and `threshold` render differently.

    Returns {"dp": int, "tied": bool}. `tied` is True when no precision up to
    max_dp separates them -- the screen then says the value is AT the threshold
    instead of printing a comparison that reads as false. Whether the rule
    met/fired/passed is still the module's own verdict, never recomputed here or
    from this function's output.
    """
    if value == threshold:
        return {"dp": base_dp, "tied": True}
    for dp in range(base_dp, max_dp + 1):
        if round(value, dp) != round(threshold, dp):
            return {"dp": dp, "tied": False}
    return {"dp": base_dp, "tied": True}
