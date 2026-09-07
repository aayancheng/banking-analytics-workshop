# T−1 reminder — send Sep 9

**Facilitator notes. Not student-facing.** Template only: no names, no live list.

**Send to the live list**, not everyone: `python workshop/facilitator/cohort.py --live --unknown`
→ 65 addresses as of the Sep 5 export. The `--unknown` bucket is the seven people who left the
attendance question blank when the form was edited mid-flight; a blank answer should not cost
someone the join link. Recording-only sign-ups get the video afterwards and do not need this.

**Re-export from Tally on the morning of Sep 9** and regenerate — the list is only as current as
the file on disk, and the script prints the newest sign-up it contains so a stale export says so.

**Use Gmail's Schedule send** (the arrow beside Send) rather than trusting yourself to remember
on the day. Everyone in **Bcc**, you in To.

**Hong Kong:** the subject already says "Friday 8am in Hong Kong". Send a short personal note to
the HK attendees on the morning of *their* Sep 11 as well — they attend on a different calendar
day and a Thursday-evening reminder lands while they are asleep.

---

## Subject

> Tomorrow, 8pm EDT — your join link (Friday 8am in Hong Kong)

## Body

Hi everyone,

Session 1 is tomorrow. Everything you need is in this email.

**JOIN**
`[[MEETING_LINK]]`

**WHEN**
Toronto: Thursday 10 September, 8:00–9:30pm EDT
Hong Kong: Friday 11 September, 8:00–9:30am HKT — the next calendar day

**IF YOU HAVEN'T DONE THE 10-MINUTE SETUP, DO IT TODAY**

1. github.com/aayancheng/banking-analytics-workshop
2. Code > Codespaces > Create codespace on main
3. Wait for it to build, then run: `python verify.py`
4. You want a green line ending: **you are here, and it works.**

It will say **"Stage 5 verified"** with nine checks passing. That's correct — Stage 5 is the
finished platform, and tomorrow we rewind to the start and build it.

**Please don't leave this until tomorrow evening.** We have 90 minutes and I can't debug laptops
live — if you arrive red, the answer will be "join from Codespaces", so it's worth finding that
out today. If it doesn't go green, reply now and I'll sort it with you before we start.

**TWO SMALL THINGS**

- Questions go in the **chat**, not on mic. There are a lot of us, and I'd rather answer them as
  we go than lose them.
- The session is **recorded** and goes out to everyone afterwards. If something breaks on your
  end, or you can't make it after all, nothing is lost.

See you tomorrow.

Yan

---

## Why it's this short

The confirmation email did the explaining. This one has a single job: get people into the room
with a working environment. Every line either carries the link, the time, or the pre-work.

- **The link is first**, before any prose. On the night, people scroll to the top and click.
- **"Do it today" is the real payload.** At ~40 live the pre-work rule is the only thing standing
  between the session and an evening spent on one person's corporate proxy. Stating the
  consequence plainly — *you arrive red, you join from Codespaces* — is kinder than discovering
  it together at 8:05.
- **The expected string is repeated.** "Stage 5 verified" surprised people the first time; saying
  it again costs one line and prevents a round of "mine says Stage 5, is that wrong?".
- **Chat-not-mic is set here, not on the night.** An expectation set in advance is a norm; the
  same thing said at 8:02 is a correction.
- **Nothing new is introduced.** No reading, no links to explore, no homework. Anything added
  here competes with the one action that matters.
