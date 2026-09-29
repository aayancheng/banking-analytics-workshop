"""Documented monitoring policy (D4.8). These are policy constants, not measurements: they
are registered as facts so that every page prints them by name and a change to the policy
is a change in one place, reviewed like any other."""
from __future__ import annotations

from wiki.facts.core import Fact

SRC = "wiki.facts.policy (documented monitoring policy)"
POP = "policy constant"

PSI_WATCH = 0.10    # population stability: below this, stable
PSI_ACT = 0.25      # above this, a shift that needs action
RATIO_LO = 0.75     # observed / predicted default rate by band: tolerance, lower edge
RATIO_HI = 1.25     # ... upper edge
IV_USELESS = 0.02   # information value below this: conventionally unpredictive


def compute() -> dict[str, Fact]:
    return {f"monitoring.{k}": Fact(v, ".2f", SRC, POP) for k, v in [
        ("psi_watch", PSI_WATCH), ("psi_act", PSI_ACT),
        ("ratio_lo", RATIO_LO), ("ratio_hi", RATIO_HI), ("iv_useless", IV_USELESS)]}
