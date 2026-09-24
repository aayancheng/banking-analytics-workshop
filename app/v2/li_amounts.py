"""The line-increase AMOUNT, explained: the three caps recommended_amount() takes the
min of, and the steps from the lowest of them to the amount it returns.

recommended_amount() (line_increase/src/amount_rules.py -- a committed module v2 must
not change) takes min(caps), returns 0 if that is <= 0, and otherwise rounds to the
nearest LINE_INCREASE["round_to"]. Showing the caps alone made the screen contradict
the amount it was explaining (final review I4): on 7,069 of 8,336 accounts the
binding cap is NEGATIVE (caption "at $-12,345" over a zero-width bar labelled
"binds"); on 579 the recommended amount is ABOVE the binding cap (BIZ100084: cap
$14,554, recommended $15,000) because the rounding comes after the min; on 23 more a
positive cap under $500 rounds to $0. amount_steps names each move so the words
never state an amount the chart contradicts. `recommended` is always the batch's own
recommended_amount, never re-derived here; a whole-book test checks the steps lead to
it.
"""
from __future__ import annotations

from shared.config import LINE_INCREASE


def caps(current_balance: float, credit_limit: float, annual_revenue: float,
          cfg: dict = LINE_INCREASE) -> list[dict]:
    """The three ceilings recommended_amount() takes the min of, each shown so the
    binding one is visible instead of inferred."""
    if credit_limit <= 0:
        return []
    values = {
        "headroom_to_target_util": current_balance / cfg["target_util"] - credit_limit,
        "pct_cap": cfg["pct_cap"] * credit_limit,
        "revenue_ceiling": cfg["revenue_mult_cap"] * annual_revenue - credit_limit,
    }
    # min() over the KEYS, not a value comparison: two caps can tie exactly.
    # BIZ111364 (balance 10,180 · limit 10,000 · revenue 50,000) gives pct_cap
    # 0.50*10,000 = 5,000.00 and revenue_ceiling 0.30*50,000-10,000 = 5,000.00 --
    # an exact float tie, not a rounding artifact. Comparing `v == lowest` marks both
    # binding, and the tab's whole claim is that ONE cap binds. First key wins, which
    # is deterministic because `values` is built in a fixed order.
    binding_key = min(values, key=values.get)
    return [{"name": k, "amount": round(float(v), 2), "binding": k == binding_key}
            for k, v in values.items()]


def amount_steps(cap_rows: list[dict], recommended: float,
                 cfg: dict = LINE_INCREASE) -> dict | None:
    """lowest cap -> floored at $0 -> rounded to the nearest round_to -> recommended.
    `min_cap` is the binding cap exactly as the chart prints it. None when there are
    no caps (credit_limit <= 0: recommended_amount returns 0 before any cap)."""
    if not cap_rows:
        return None
    binding = next(c for c in cap_rows if c["binding"])
    min_cap = float(binding["amount"])
    floored, rnd = max(0.0, min_cap), float(cfg["round_to"])
    return {
        "binding": binding["name"],
        "min_cap": min_cap,
        "no_headroom": min_cap <= 0,
        "floored_at_zero": floored,
        "round_to": rnd,
        # recommended_amount() rounds with Python's round(), which sends an exact
        # half to the EVEN multiple: 54,500 -> 54,000 but 53,500 -> 54,000. On the
        # 82 accounts whose floored cap is an exact half of round_to, "rounded to the
        # nearest $1,000" alone reads as an arithmetic slip on the ones that go down
        # (BIZ100375: $54,500 -> $54,000), so the caption names the rule.
        "half_to_even": (floored / rnd) % 1 == 0.5,
        "recommended": float(recommended),
    }
