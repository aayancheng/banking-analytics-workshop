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
`tied` is True only when the values DIFFER but nothing up to max_dp separates them
(float noise, e.g. 1.3e-16) -- the caller should then say the value is AT the
threshold rather than draw a comparison that looks false. Exactly equal values are
not tied (fix round 2, below): they print identically and the plain comparison
already reads correctly. Whether the rule fired/passed is
always the module's own verdict; this function never decides it and is never used to
recompute one.

Fix round 2: the first draft treated EXACT equality as a tie too, which was wrong in
the other direction -- an exact match's plain comparison already reads correctly
("0 > 0 -> not met", "3 >= 3 -> met"), so marking it tied relabelled 4,858 honest EWS
rows, 4,111 of them healthy zero-days-past-due accounts, as "at the threshold" of
delinquency. `tied` now means only "the values differ, but nothing up to max_dp
separates them" -- exact equality returns `tied: False` at base_dp instead.
"""
from __future__ import annotations


def display_precision(value: float, threshold: float,
                      base_dp: int = 4, max_dp: int = 8) -> dict:
    """The fewest decimals at which a value and the threshold it is compared against
    render DIFFERENTLY, so a clause never prints two equal numbers under a strict
    comparator.

    A fixed precision chosen in the browser is tuned to today's data and silently
    breaks on a retrain. `tied` is True when the values differ but no precision up
    to max_dp separates them (floating-point noise) -- the screen then says the
    value is AT the threshold rather than printing a comparison that reads as
    false. Exactly equal values return tied False: they print identically and the
    plain comparison reads correctly. Whether the rule met is still the module's verdict, never recomputed.
    """
    if value == threshold:
        # EXACTLY equal is not a tie in the sense that matters: the plain comparison
        # already reads correctly ("0 > 0 -> not met", "3 >= 3 -> met"). Marking it
        # tied relabelled 4,858 honest EWS rows -- 4,111 of them healthy accounts with
        # zero days past due, suddenly described as "at the threshold" of delinquency.
        return {"dp": base_dp, "tied": False}
    for dp in range(base_dp, max_dp + 1):
        if round(value, dp) != round(threshold, dp):
            return {"dp": dp, "tied": False}
    return {"dp": base_dp, "tied": True}


def axis_precision(value: float, thresholds) -> dict:
    """display_precision against SEVERAL thresholds drawn on one axis (a PD pin
    between t_low and t_high, a probability between t_med and t_high): the pin and
    every handle are printed with one shared format, so it must separate the value
    from the nearest of them. dp is the max over the pairs, tied if any pair ties."""
    precs = [display_precision(value, t) for t in thresholds]
    return {"dp": max(p["dp"] for p in precs), "tied": any(p["tied"] for p in precs)}
