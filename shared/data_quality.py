"""Data-quality report for the synthetic SME data. Session 1 lab artifact.

Writes reports/data_quality.md: row counts, target rates, null audit,
key-feature distributions, and the leakage deny-list. Run after the generator:

    python -m shared.data_generator && python -m shared.data_quality
"""
import pandas as pd

from shared.config import LEAKAGE_COLUMNS, RAW, ROOT

REPORT = ROOT / "reports" / "data_quality.md"

KEY_FEATURES = ["years_in_business", "annual_revenue", "dscr", "current_ratio",
                "leverage", "utilization", "requested_amount"]


def main():
    biz = pd.read_parquet(RAW / "businesses.parquet")
    portfolio = pd.read_parquet(RAW / "portfolio.parquet")
    panel = pd.read_parquet(RAW / "panel.parquet")

    lines = ["# Data-Quality Report — synthetic SME portfolio", ""]
    lines += ["## Row counts", "",
              f"| file | rows | columns |", "|---|---|---|",
              f"| businesses.parquet | {len(biz):,} | {biz.shape[1]} |",
              f"| portfolio.parquet | {len(portfolio):,} | {portfolio.shape[1]} |",
              f"| panel.parquet | {len(panel):,} | {panel.shape[1]} |", ""]

    lines += ["## Target rates", "",
              f"- default rate (applicants): **{biz['default'].mean():.3f}**",
              f"- booked rate: **{biz['booked'].mean():.3f}**",
              f"- deterioration rate (on-book): **{portfolio['deterioration_next_6_12mo'].mean():.3f}**",
              f"- line_increase_good rate (on-book): **{portfolio['line_increase_good'].mean():.3f}**",
              ""]

    nulls = int(biz.isna().sum().sum() + portfolio.isna().sum().sum()
                + panel.isna().sum().sum())
    lines += ["## Null audit", "",
              f"Total nulls across all three files: **{nulls}** "
              f"(synthetic data is complete by construction — a nonzero count here is a bug).",
              ""]

    lines += ["## Key feature distributions (applicants)", "",
              "| feature | min | p25 | median | p75 | max |", "|---|---|---|---|---|---|"]
    for col in KEY_FEATURES:
        q = biz[col].quantile([0, 0.25, 0.5, 0.75, 1.0])
        lines.append("| " + col + " | " + " | ".join(f"{v:,.2f}" for v in q) + " |")
    lines.append("")

    lines += ["## Leakage deny-list", "",
              "These columns exist in the data but must never enter a model's feature",
              "matrix (`shared/config.py::LEAKAGE_COLUMNS`, enforced from stage-2 on):", ""]
    lines += [f"- `{c}`" for c in LEAKAGE_COLUMNS]
    lines.append("")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines))
    print(f"wrote {REPORT.relative_to(ROOT)} ({nulls} nulls, "
          f"{len(biz):,}/{len(portfolio):,}/{len(panel):,} rows)")


if __name__ == "__main__":
    main()
