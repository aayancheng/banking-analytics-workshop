"""Capture the data-derived demo assets from the REAL repo artifacts.

The demo video shows outcomes, not just terminal output. Three of those outcomes
are figures rather than screenshots, so they are rendered here from the actual
committed data + trained scorecard and written into assets/ for make_demo.py:

  s1_portfolio.png          - a sample of the synthetic SME portfolio (Session 1)
  s2_score_distribution.png - the 300-850 score distribution by band (Session 2)
  s4_watchlist.png          - the early-warning watchlist, cropped from the portal

Run after stage-2 artifacts exist (the scorecard must be trained):

    .venv/bin/python workshop/demo/capture_assets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# run as `python workshop/demo/capture_assets.py` from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image

from score.src.predict import _BANDS_BINS, _BANDS_LABELS, predict_score_pd

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
RAW = Path("shared/data/raw")

INK = "#1a2332"
ACCENT = "#245bb2"
MUTED = "#5f6880"
PAPER = "#ffffff"
# D -> AAA, risky to safe
BAND_COLORS = ["#b3372e", "#c9782a", "#c9a227", "#4f9e56", "#2f7d4f"]


def portfolio_card():
    """A readable slice of the synthetic portfolio + the headline totals."""
    biz = pd.read_parquet(RAW / "businesses.parquet")
    cols = ["business_id", "industry", "region", "years_in_business",
            "annual_revenue", "dscr", "utilization", "requested_amount"]
    sample = biz.loc[:, cols].head(11).copy()

    head = ["Client", "Industry", "Region", "Yrs", "Revenue", "DSCR", "Util", "Requested"]
    rows = [
        [r.business_id, r.industry, r.region, f"{int(r.years_in_business)}",
         f"${r.annual_revenue/1e6:.1f}M", f"{r.dscr:.2f}",
         f"{r.utilization:.0%}", f"${r.requested_amount/1e3:.0f}k"]
        for r in sample.itertuples()
    ]

    fig = plt.figure(figsize=(15.2, 6.6), dpi=130)
    ax = fig.add_axes((0.02, 0.155, 0.96, 0.815))
    ax.axis("off")

    tbl = ax.table(cellText=rows, colLabels=head, cellLoc="left",
                   colWidths=[.14, .20, .14, .06, .12, .08, .07, .19],
                   bbox=(0, 0, 1, 1))
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(16)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#e2e7ef")
        cell.set_linewidth(1)
        if r == 0:
            cell.set_facecolor(INK)
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#ffffff" if r % 2 else "#f6f8fb")
            cell.set_text_props(color=INK)

    n, booked = len(biz), int(biz["booked"].sum())
    rate = biz["default"].mean()
    fig.text(.5, .082,
             f"{n:,} businesses   ·   {booked:,} booked   ·   "
             f"{biz['industry'].nunique()} industries   ·   default rate {rate:.1%}",
             ha="center", fontsize=20, color=ACCENT, weight="bold")
    fig.text(.5, .028,
             "100% synthetic · seeded and reproducible · no real customer data anywhere",
             ha="center", fontsize=15, color=MUTED)

    out = ASSETS / "s1_portfolio.png"
    fig.savefig(out, facecolor=PAPER)
    plt.close(fig)
    print(f"wrote {out.name}  ({n:,} rows sampled)")


def score_distribution_card():
    """The 300-850 distribution, banded, with each band's realised default rate."""
    biz = pd.read_parquet(RAW / "businesses.parquet")
    scored = predict_score_pd(biz)
    df = pd.concat([biz[["default"]].reset_index(drop=True),
                    scored.reset_index(drop=True)], axis=1)

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(15.2, 6.6), dpi=130, gridspec_kw={"width_ratios": [2.45, 1]})

    ax.hist(df["business_score"], bins=54, color="#9fb4d4", edgecolor="white", linewidth=.6)
    for lo, hi, lab, col in zip(_BANDS_BINS[:-1], _BANDS_BINS[1:], _BANDS_LABELS, BAND_COLORS):
        ax.axvspan(lo, hi, color=col, alpha=.10)
        ax.text((lo + hi) / 2, ax.get_ylim()[1] * .94, lab,
                ha="center", fontsize=16, weight="bold", color=col)
    ax.set_xlabel("Business credit score  (300–850)", fontsize=15, color=INK)
    ax.set_ylabel("Borrowers", fontsize=15, color=INK)
    ax.set_xlim(_BANDS_BINS[0], _BANDS_BINS[-1])
    ax.tick_params(labelsize=13, colors=MUTED)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#d8dce6")

    by = (df.groupby("score_band", observed=True)["default"]
            .agg(["size", "mean"]).reindex(_BANDS_LABELS).dropna())
    ax2.barh(range(len(by)), by["mean"] * 100,
             color=[BAND_COLORS[_BANDS_LABELS.index(b)] for b in by.index], height=.62)
    ax2.set_yticks(range(len(by)), by.index, fontsize=15, color=INK)
    ax2.invert_yaxis()
    ax2.set_xlabel("Default rate  (%)", fontsize=15, color=INK)
    ax2.tick_params(labelsize=13, colors=MUTED)
    for s in ("top", "right", "left"):
        ax2.spines[s].set_visible(False)
    ax2.spines["bottom"].set_color("#d8dce6")
    for i, (_, r) in enumerate(by.iterrows()):
        ax2.text(r["mean"] * 100 + .45, i, f"{r['mean']:.1%}",
                 va="center", fontsize=14, color=INK, weight="bold")
    ax2.set_title("Riskier band → higher default.\nThe score rank-orders.",
                  fontsize=15, color=ACCENT, weight="bold", pad=14)

    fig.tight_layout(rect=(0, .045, 1, 1))
    fig.text(.5, .012,
             "Every borrower scored by the WoE scorecard  ·  held-out AUC 0.8176  ·  gate ≥ 0.78 PASS",
             ha="center", fontsize=15, color=MUTED)

    out = ASSETS / "s2_score_distribution.png"
    fig.savefig(out, facecolor=PAPER)
    plt.close(fig)
    print(f"wrote {out.name}  (bands: {', '.join(by.index)})")


def watchlist_crop():
    """Crop the early-warning watchlist out of the full S4 portal screenshot."""
    src = Image.open(ASSETS / "s4_portal.png")
    w, h = src.size
    crop = src.crop((0, 0, w, int(h * 0.545)))   # the watchlist card, above line-increase
    out = ASSETS / "s4_watchlist.png"
    crop.save(out)
    print(f"wrote {out.name}  ({crop.size[0]}x{crop.size[1]} from {w}x{h})")


if __name__ == "__main__":
    portfolio_card()
    score_distribution_card()
    watchlist_crop()
