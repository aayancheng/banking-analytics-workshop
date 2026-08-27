"""Build the cohort calendar file.

Generated, not hand-written — the dates move, and a hand-edited .ics is where
timezone bugs live. UTC-anchored so every attendee's calendar renders it in their
own zone; Hong Kong attends the *following calendar day*, which is exactly the kind
of arithmetic nobody should be doing by hand.

    python workshop/facilitator/make_ics.py 1     # only Session 1 (dates not yet locked)
    python workshop/facilitator/make_ics.py       # all five

Fill in the join links after generating — they are placeholders on purpose so this
file stays safe in a public repo.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent / "credit-analytics-workshop.ics"

# Session 1 is locked. Later sessions are weekly at the same time, but the dates are
# confirmed with the cohort at S1 — regenerate with no argument once they are.
S1_START = datetime(2026, 9, 10, 20, 0, tzinfo=timezone(timedelta(hours=-4)))  # EDT
DTSTAMP = "20260820T120000Z"
HKT = timezone(timedelta(hours=8))

SESSIONS = [
    ("S1", "How a Bank Decides",
     "Build 12,000 synthetic SME borrowers you can trust — and meet the six forbidden columns.",
     "stage-1"),
    ("S2", "The Score Spine",
     "A WoE scorecard that passes a hard gate, or doesn't ship. Held-out AUC, committed in code.",
     "stage-2"),
    ("S3", "Decisions I — Adjudication & Pricing",
     "Your score starts making money decisions: approve / refer / decline, and the right price.",
     "stage-3"),
    ("S4", "Decisions II — The Portfolio Wakes Up",
     "Behavioural early warning: a ranked watchlist that names the trigger. Plus honest gates.",
     "stage-4"),
    ("S5", "Governance & the Human-Agent Team",
     "You don't demo today. You defend. Assemble the model documentation pack.",
     "stage-5"),
]


def fold(line: str) -> str:
    """RFC 5545 §3.1: no content line over 75 octets; continuations start with a space."""
    out, cur = [], ""
    for ch in line:
        if len((cur + ch).encode()) > 73:
            out.append(cur)
            cur = " " + ch
        else:
            cur += ch
    out.append(cur)
    return "\r\n".join(out)


def build(n: int) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//TeamYan//Credit Analytics with AI Agents//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             "X-WR-CALNAME:Credit Analytics with AI Agents"]
    for i, (code, title, blurb, tag) in enumerate(SESSIONS[:n]):
        s = S1_START + timedelta(weeks=i)
        e = s + timedelta(minutes=90)
        hk = s.astimezone(HKT)
        desc = (
            f"{blurb}\\n\\n"
            f"Toronto: {s:%a %-d %b} {s:%-I:%M}pm-{e:%-I:%M}pm EDT\\n"
            f"Hong Kong: {hk:%a %-d %b} 8:00am-9:30am HKT (the NEXT calendar day)\\n\\n"
            "JOIN: [[MEETING_LINK]]\\n\\n"
            f"Checkpoint: {tag}. Repo: "
            "https://github.com/aayancheng/banking-analytics-workshop\\n"
            "Recorded — the link goes out to the cohort afterwards.\\n"
            "Before session 1: open the repo in Codespaces and run  python verify.py"
        )
        lines += [
            "BEGIN:VEVENT",
            f"UID:{code.lower()}-credit-analytics-agents-2026@teamyan.dev",
            f"DTSTAMP:{DTSTAMP}",
            f"DTSTART:{s.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}",
            f"DTEND:{e.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}",
            fold(f"SUMMARY:{code} — {title} · Credit Analytics with AI Agents"),
            fold(f"DESCRIPTION:{desc}"),
            "LOCATION:Online — see the join link in the description",
            "STATUS:CONFIRMED", "TRANSP:OPAQUE",
            # 12h alarm lands the evening before for Hong Kong, who attend the next day
            "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-PT12H",
            fold(f"DESCRIPTION:Tomorrow morning (HK): {code} — {title}"), "END:VALARM",
            "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-PT30M",
            fold(f"DESCRIPTION:Starting in 30 minutes: {code} — {title}"), "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(SESSIONS)
    OUT.write_bytes(build(n).encode())
    print(f"wrote {OUT.name} — {n} session(s)")
