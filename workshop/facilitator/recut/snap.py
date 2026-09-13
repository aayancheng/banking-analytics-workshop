#!/usr/bin/env python3
"""Snap every keep boundary in a cuts file to the nearest pause in the source audio.

Rough boundaries come from a transcript; a transcript's clock is good to a few
seconds, which is enough to cut mid-word. This moves each `in` to just after the
end of the nearest silence and each `out` to just before the start of one, so
every join lands in a gap between sentences.

    python snap.py S1.cuts.json              # prints the moves, rewrites in place
    python snap.py S1.cuts.json --dry-run    # prints only
    python snap.py S1.cuts.json --window 4   # search +-4 s (default 3)

Pauses are found with ffmpeg's silencedetect (>= 0.6 s below -32 dBFS, after a
120 Hz high-pass so room rumble does not hide them) and cached beside the source.
Stdlib + ffmpeg only.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repo root


def find_pauses(source: Path, cache: Path) -> list[tuple[float, float]]:
    if cache.exists():
        return [tuple(p) for p in json.loads(cache.read_text())]
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(source), "-vn",
           "-af", "highpass=f=120,silencedetect=noise=-32dB:d=0.6", "-f", "null", "-"]
    out = subprocess.run(cmd, capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", out)]
    pauses = list(zip(starts, ends))
    cache.write_text(json.dumps(pauses))
    return pauses


def snap(t: float, pauses, window: float, edge: str, margin: float = 0.15):
    """edge='in': land just after a pause ends; edge='out': just before one starts."""
    best = None
    for s, e in pauses:
        cand = e - margin if edge == "in" else s + margin
        if abs(cand - t) <= window and (best is None or abs(cand - t) < abs(best - t)):
            best = cand
    return round(best, 2) if best is not None else None


def fmt(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cuts")
    ap.add_argument("--window", type=float, default=3.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    path = Path(a.cuts)
    doc = json.loads(path.read_text())
    source = ROOT / doc["source"]
    pauses = find_pauses(source, source.with_suffix(".pauses.json"))
    print(f"{len(pauses)} pauses in {source.name}")

    moved = unsnapped = 0
    for k in doc["keeps"]:
        for edge in ("in", "out"):
            old = k[edge]
            new = snap(old, pauses, a.window, edge)
            if new is None:
                unsnapped += 1
                print(f"  {k['id']:<4} {edge:<3} {fmt(old)}  -> no pause within +-{a.window}s, left as is")
                continue
            if abs(new - old) > 0.01:
                moved += 1
                print(f"  {k['id']:<4} {edge:<3} {fmt(old)}  -> {fmt(new)}  ({new - old:+.2f}s)")
            k[edge] = new
        if k["out"] <= k["in"]:
            sys.exit(f"{k['id']}: out <= in after snapping; widen or fix by hand")
    print(f"moved {moved} boundaries, {unsnapped} left unsnapped")
    if not a.dry_run:
        doc["snapped"] = True
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
