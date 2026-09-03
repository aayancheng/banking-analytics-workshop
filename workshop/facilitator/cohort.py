"""Turn the latest Tally export into a clean BCC list — and nothing else.

The export is PII and gitignored; this script is not. Run it, paste the output,
delete nothing. Sign-ups arrive continuously, so the recurring question is never
"who signed up" but "who signed up since I last emailed anyone".

    python workshop/facilitator/cohort.py                 # everyone, deduped
    python workshop/facilitator/cohort.py --since 2026-08-31
    python workshop/facilitator/cohort.py --live          # only "yes live"

--since takes the date of your last send and prints only the people who arrived
after it, which is the list you actually want most of the time.
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
from collections import Counter

# Your own test submissions — never mail yourself.
OWN = {"teamyan2025@gmail.com", "aayancheng@gmail.com"}
SEARCH = ("workshop/facilitator/*Submissions*.csv", "*Submissions*.csv")
SUBMITTED, NAME, EMAIL, REGION, ATTEND, BACKGROUND = 2, 3, 4, 5, 6, 7


def newest_export() -> str:
    found = [f for pat in SEARCH for f in glob.glob(pat)]
    if not found:
        raise SystemExit("No *Submissions*.csv found. Export from Tally first.")
    return max(found, key=os.path.getmtime)


def load(path: str) -> list[list[str]]:
    """Deduplicate on email, keeping the FIRST submission — the original sign-up
    timestamp is what --since needs to be correct."""
    rows = [r for r in csv.reader(open(path)) if any(r)][1:]
    seen, out = set(), []
    for r in rows:
        email = r[EMAIL].strip().lower()
        if not email or email in OWN or email in seen:
            continue
        seen.add(email)
        out.append(r)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-MM-DD — only sign-ups after this date")
    ap.add_argument("--live", action="store_true", help="only those attending live")
    a = ap.parse_args()

    path = newest_export()
    people = load(path)
    total = len(people)

    if a.since:
        people = [r for r in people if r[SUBMITTED].strip()[:10] > a.since]
    if a.live:
        people = [r for r in people if r[ATTEND].strip().startswith("Yes")]

    print(f"export:   {os.path.basename(path)}")
    print(f"distinct: {total}   selected: {len(people)}")
    for label, idx in (("attendance", ATTEND), ("region", REGION), ("background", BACKGROUND)):
        counts = Counter(r[idx].strip() for r in people).most_common()
        print(f"{label:11}" + " · ".join(f"{v} {k}" for k, v in counts))

    if not people:
        print("\nNobody new. Nothing to send.")
        return

    print(f"\n--- BCC ({len(people)}) — paste into Gmail's Bcc field ---")
    print(", ".join(r[EMAIL].strip() for r in people))
    if len(people) > 90:
        print("\n⚠️  Over ~90 recipients: split into two sends. Gmail throttles large "
              "Bcc lists and a personal account is more likely to be spam-filtered.")


if __name__ == "__main__":
    main()
