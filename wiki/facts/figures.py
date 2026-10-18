"""Deterministic SVG exhibits for D4 (no timestamps, fixed hash salt)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"svg.hashsalt": "wiki", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False})
INK, ACCENT, MUTED = "#1a2332", "#245bb2", "#9fb4d4"


def _save(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)


def write_all(ex: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot(ex["roc"]["fpr"], ex["roc"]["tpr"], color=ACCENT, lw=2)
    ax.plot([0, 1], [0, 1], color=MUTED, ls="--", lw=1)
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    _save(fig, out / "roc.svg")

    b = ex["bands"]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = range(len(b))
    ax.bar([i - 0.2 for i in x], b["predicted"] * 100, width=0.4, color=MUTED, label="predicted")
    ax.bar([i + 0.2 for i in x], b["observed"] * 100, width=0.4, color=ACCENT, label="observed")
    ax.set_xticks(list(x), b["band"]); ax.set_ylabel("default rate (%)"); ax.legend(frameon=False)
    _save(fig, out / "calibration.svg")

    for name, series, xlabel in [("psi", ex["psi"], "PSI, train → held-out"),
                                 ("iv", ex["iv"], "information value (training split)")]:
        fig, ax = plt.subplots(figsize=(6, 4.2))
        ax.barh(series.index[::-1], series.values[::-1], color=ACCENT)
        ax.set_xlabel(xlabel)
        _save(fig, out / f"{name}.svg")


def write_pricing(t: dict[str, str], out: Path) -> None:
    """D6: share of each score band's booked loans quoted below the hurdle-clearing rate,
    drawn from the printed facts so the figure and the tables cannot disagree."""
    out.mkdir(parents=True, exist_ok=True)
    bands = ["D", "C", "B", "A", "AAA"]
    rates = [float(t[f"pricing.band.{b}.mispriced_rate"].rstrip("%")) for b in bands]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.bar(bands, rates, color=ACCENT)
    ax.axhline(float(t["pricing.share_mispriced"].rstrip("%")), color=INK, ls="--", lw=1,
               label="whole booked book")
    ax.set_ylim(0, 100); ax.set_xlabel("score band"); ax.set_ylabel("quoted below hurdle (%)")
    ax.legend(frameon=False, loc="lower right")
    _save(fig, out / "mispriced-by-band.svg")


def write_ews(t: dict[str, str], out: Path) -> None:
    """D7: observed deterioration rate against mean model probability by risk tier, on the
    held-out rows, drawn from the printed facts so the figure and the tables cannot disagree."""
    out.mkdir(parents=True, exist_ok=True)
    tiers = ["Low", "Medium", "High"]
    obs = [float(t[f"ews.tier_ho.{k}.observed"].rstrip("%")) for k in tiers]
    pred = [float(t[f"ews.tier_ho.{k}.predicted"].rstrip("%")) for k in tiers]
    labels = [f"{k}\n(n={t[f'ews.tier_ho.{k}.n']})" for k in tiers]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = range(len(tiers))
    ax.bar([i - 0.2 for i in x], pred, width=0.4, color=MUTED, label="mean probability")
    ax.bar([i + 0.2 for i in x], obs, width=0.4, color=ACCENT, label="observed")
    ax.axhline(float(t["ews.base_rate"].rstrip("%")), color=INK, ls="--", lw=1,
               label="book base rate")
    ax.set_xticks(list(x), labels); ax.set_ylabel("deterioration rate (%)")
    ax.legend(frameon=False, loc="upper left")
    _save(fig, out / "tier-calibration.svg")
