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
