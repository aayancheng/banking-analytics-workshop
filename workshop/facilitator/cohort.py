"""Turn the latest Tally export into a clean Bcc list — and nothing else.

The export is PII and gitignored; this script is not. Sign-ups arrive continuously,
so the recurring question is never "who signed up" but "who signed up since I last
emailed anyone".

    python workshop/facilitator/cohort.py                      # everyone, deduped
    python workshop/facilitator/cohort.py --since 2026-08-31   # on/after that date
    python workshop/facilitator/cohort.py --not-in OLD.csv     # exact set difference
    python workshop/facilitator/cohort.py --live               # the room on the night
    python workshop/facilitator/cohort.py --live --unknown     # everyone who gets the join link
    python workshop/facilitator/cohort.py --recording --later  # everyone else

Attendance buckets (--live / --recording / --later) union when combined. Note that
"Recording then join later" means live *eventually* — they belong on the recording list
for Session 1 but still want the join link for sessions 2-5.

Prefer --not-in over --since when you have the export you last mailed from: it is an
exact set difference and cannot be off by a day. --since is date-only and INCLUSIVE,
so it can re-include someone who signed up earlier that same day — harmless (a second
confirmation costs nothing) but not exact.

Paths are resolved against the repo root, so it behaves the same from any directory.
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OWN = {"teamyan2025@gmail.com", "aayancheng@gmail.com"}   # your own test submissions
PATTERNS = ("workshop/facilitator/*Submissions*.csv", "*Submissions*.csv")
# Columns are resolved BY HEADER NAME, never by position. Tally exports reorder and
# rename as the form is edited — "Your background" and "Can you make Session 1 live"
# swapped places between the Sep-4 and Sep-5 exports, and reading attendance out of the
# background column fails silently rather than loudly.
COLUMNS = {
    "submitted":  ("submitted at",),
    "name":       ("your name", "name"),
    "email":      ("email",),
    "region":     ("home base", "join from", "where"),
    "attend":     ("session 1 live", "make session", "live"),
    "background": ("your background", "background"),
}


def resolve(header: list[str]) -> dict[str, int]:
    """Map each logical field to a column index by matching header text."""
    lowered = [h.strip().strip('"').lower() for h in header]
    found: dict[str, int] = {}
    for key, needles in COLUMNS.items():
        for needle in needles:                      # first needle wins: most specific first
            hits = [i for i, h in enumerate(lowered)
                    if needle in h and i not in found.values()]
            if hits:
                found[key] = hits[0]
                break
    missing = [k for k in COLUMNS if k not in found]
    if missing:
        raise SystemExit(
            f"Could not find these columns in the export: {missing}\n"
            f"Header was: {header}\n"
            "Tally's form was probably edited. Add the new wording to COLUMNS in this file."
        )
    return found


def candidates() -> list[Path]:
    seen, out = set(), []
    for pat in PATTERNS:
        for f in glob.glob(str(ROOT / pat)):
            rp = Path(f).resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(rp)
    return out


def read(path: Path) -> tuple[dict[str, int], list[list[str]]]:
    rows = [r for r in csv.reader(open(path, encoding="utf-8-sig")) if any(r)]
    return resolve(rows[0]), rows[1:]


def latest_submission(path: Path) -> str:
    try:
        col, rows = read(path)
    except SystemExit:
        return ""
    i = col["submitted"]
    stamps = [r[i].strip() for r in rows if len(r) > i]
    return max(stamps) if stamps else ""


def dedupe(rows: list[list[str]], col: dict[str, int]) -> list[list[str]]:
    """Keep the FIRST submission per email — the original sign-up time is what the
    date filter has to reason about."""
    need = max(col.values())
    seen, out, short = set(), [], 0
    for r in rows:
        if len(r) <= need:
            short += 1
            continue
        email = r[col["email"]].strip().lower()
        if not email or email in OWN or email in seen:
            continue
        seen.add(email)
        out.append(r)
    if short:
        print(f"⚠️  skipped {short} malformed row(s) with too few fields")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-MM-DD — sign-ups on or after this date")
    ap.add_argument("--not-in", dest="not_in", help="a previous export; show only emails absent from it")
    ap.add_argument("--live", action="store_true", help='bucket: "Yes live"')
    ap.add_argument("--recording", action="store_true", help='bucket: "Recording only"')
    ap.add_argument("--later", action="store_true", help='bucket: "Recording then join later"')
    ap.add_argument("--unknown", action="store_true",
                    help="bucket: attendance left blank (the form was edited mid-flight)")
    a = ap.parse_args()

    files = candidates()
    if not files:
        raise SystemExit(f"No *Submissions*.csv under {ROOT}. Export from Tally first.")

    chosen = max(files, key=lambda p: latest_submission(p) or "")
    newest_mtime = max(files, key=os.path.getmtime)

    print(f"export:   {chosen.name}")
    print(f"latest sign-up in it: {latest_submission(chosen) or '(none)'}   <- if this looks old, re-export")
    if chosen != newest_mtime:
        print(f"note:     {newest_mtime.name} was copied more recently but contains older "
              f"sign-ups; using the one with the newest data.")
    if len(files) > 1:
        print(f"          ({len(files)} exports on disk; delete stale ones to keep this simple)")

    col, raw = read(chosen)
    SUBMITTED, EMAIL, REGION, ATTEND, BACKGROUND = (
        col["submitted"], col["email"], col["region"], col["attend"], col["background"])
    people = dedupe(raw, col)
    total = len(people)
    print(f"rows:     {len(raw)} submissions -> {total} distinct people")

    if a.not_in:
        prev = Path(a.not_in)
        if not prev.exists():
            prev = ROOT / a.not_in
        if not prev.exists():
            raise SystemExit(f"--not-in file not found: {a.not_in}")
        pcol, prows = read(prev)
        pe = pcol["email"]
        already = {r[pe].strip().lower() for r in prows if len(r) > pe}
        people = [r for r in people if r[EMAIL].strip().lower() not in already]
        print(f"filter:   not in {prev.name} ({len(already)} addresses)")
    if a.since:
        people = [r for r in people if r[SUBMITTED].strip()[:10] >= a.since]
        print(f"filter:   signed up on or after {a.since} (inclusive)")
    # Attendance buckets. Passing several unions them; passing none keeps everyone.
    wanted = set()
    if a.live:
        wanted.add("yes live")
    if a.recording:
        wanted.add("recording only")
    if a.later:
        wanted.add("recording then join later")
    if a.unknown:
        wanted.add("")
    if wanted:
        people = [r for r in people if r[ATTEND].strip().lower() in wanted]
        print(f"filter:   attendance in {sorted(wanted)}")

    print(f"selected: {len(people)}")
    for label, idx in (("attendance", ATTEND), ("region", REGION), ("background", BACKGROUND)):
        counts = Counter(r[idx].strip() for r in people).most_common()
        print(f"{label:11}" + " · ".join(f"{v} {k}" for k, v in counts))

    if not people:
        print("\nNobody selected. Nothing to send.")
        return

    print(f"\n--- BCC ({len(people)}) — paste into Gmail's Bcc field ---")
    print(", ".join(r[EMAIL].strip() for r in people))
    if len(people) > 90:
        print("\n⚠️  Over ~90 recipients: split into two sends. Gmail throttles large Bcc "
              "lists and a personal account is likelier to be spam-filtered.")


if __name__ == "__main__":
    main()
