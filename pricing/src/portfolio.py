"""Pricing over the booked population (PD from the Module 0 scorecard) +
portfolio summary + a validation report writer."""
from __future__ import annotations
from pathlib import Path

import pandas as pd

from shared.config import RAW, MARKET
from score.src.predict import predict_score_pd
from pricing.src.engine import MarketAssumptions, price_loan

DOCS = Path(__file__).resolve().parent.parent / "docs"
_MARKET = MarketAssumptions.from_market(MARKET)


def price_population(market: MarketAssumptions | None = None) -> pd.DataFrame:
    market = market or _MARKET
    biz = pd.read_parquet(RAW / "businesses.parquet")
    booked = biz[biz["booked"] == True].copy()  # noqa: E712
    sp = predict_score_pd(booked)
    booked = booked.reset_index(drop=True)
    sp = sp.reset_index(drop=True)
    records = []
    for i in range(len(booked)):
        r = price_loan(
            pd_=float(sp["pd"].iloc[i]),
            ead=float(booked["requested_amount"].iloc[i]),
            quoted_rate=float(booked["risk_based_rate"].iloc[i]),
            market=market,
        )
        records.append({
            "business_id": str(booked["business_id"].iloc[i]),
            "industry": str(booked["industry"].iloc[i]),
            "score_band": str(sp["score_band"].iloc[i]),
            "ead": r["ead"],
            "pd": r["pd"],
            "quoted_rate": r["quoted_rate"],
            "recommended_rate": r["recommended_rate"],
            "roe_at_quoted": r["roe_at_quoted"],
            "raroc_at_quoted": r["raroc_at_quoted"],
            "clears_hurdle": r["clears_hurdle"],
            "mispriced": r["mispriced"],
            "rate_shortfall": r["rate_shortfall"],
        })
    return pd.DataFrame(records)


def _segment(df: pd.DataFrame, col: str) -> list[dict]:
    rows = []
    for key, g in df.groupby(col):
        rows.append({
            "key": str(key),
            "mispriced_rate": round(float(g["mispriced"].mean()), 4),
            "count": int(len(g)),
        })
    return sorted(rows, key=lambda r: r["key"])


def portfolio_summary(df: pd.DataFrame) -> dict:
    n = int(len(df))
    n_clears = int(df["clears_hurdle"].sum())
    return {
        "n": n,
        "n_clears": n_clears,
        "share_clears": round(n_clears / n, 4) if n else 0.0,
        "median_roe": round(float(df["roe_at_quoted"].median()), 4),
        "mispriced_ead": round(float(df.loc[df["mispriced"], "ead"].sum()), 2),
        "by_band": _segment(df, "score_band"),
        "by_industry": _segment(df, "industry"),
    }


def write_report() -> dict:
    DOCS.mkdir(parents=True, exist_ok=True)
    df = price_population()
    s = portfolio_summary(df)
    # machine-readable copy — verify.py checks pricing totals against this
    import json
    (DOCS / "summary.json").write_text(json.dumps(s, indent=2))
    lines = [
        "# Pricing & Profitability — Validation Report\n",
        f"- Booked loans priced: {s['n']:,}",
        f"- Clear ROE hurdle at quoted rate: {s['n_clears']:,} ({s['share_clears']:.1%})",
        f"- Median ROE (at quoted): {s['median_roe']:.1%}",
        f"- Mispriced EAD: ${s['mispriced_ead']:,.0f}\n",
        "## Mispriced rate by score band\n",
        *[f"- {r['key']}: {r['mispriced_rate']:.1%}  (n={r['count']:,})" for r in s["by_band"]],
    ]
    (DOCS / "validation_report.md").write_text("\n".join(lines) + "\n")
    return s


if __name__ == "__main__":
    print(write_report())
