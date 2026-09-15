# T−1 reminder — send Sep 16

**Facilitator notes. Not student-facing.** Template only: no names, no live list.

**Send to the join-link audience**, not everyone:
`python workshop/facilitator/cohort.py --live --unknown`
The recording track gets the video afterwards and does not need a join link. **Re-export
from Tally on the morning of Sep 16** and regenerate — the script prints the newest sign-up it
contains, so a stale export says so. Everyone in **Bcc**, you in To. **Use Gmail's Schedule
send.** Over ~90 addresses, split into two sends.

**Hong Kong:** their session is *Friday Sep 18, 8:00am HKT*. Send the short personal note on the
morning of *their* Friday as well — a Wednesday-evening Toronto reminder lands while they sleep.

**What state are they in?** Not `stage-1`. Session 1's stage handoff failed live and the room
was told "don't do stages", so every student who ran `verify.py` is on `main` and sees
**"Stage 5 verified"**. This email says that is fine and that we move to `stage-2` together at
the lab. Do **not** ask them to jump stages by email the night before: an unsupervised
`git checkout stage-1` on a tree with `make data` output in it is the S1 failure, forty times,
with nobody watching. The 0:50 handoff in the run of show must therefore be
`git stash && git checkout stage-2 && python verify.py` **from `main`**, and the pre-flight line
"they arrive on `stage-1`" is out of date — fix it in the S2 re-cut.

**The homework is the pre-work.** Session 2 opens on it: Poll A at 0:04 collects the sealed
AUC, the WoE table is who you cold-call in Part A, the five-liners are read at 0:02. Asking for
them here is not "introducing something new" — it is the one action that makes the 0:32 reveal
land for each person individually.

---

## Subject

> Tomorrow, 8pm EDT — Session 2: score the portfolio (Friday 8am in Hong Kong)

## Body

Hi everyone,

Session 2 is tomorrow: we score the portfolio. Everything you need is in this email.

**JOIN**
`[[MEETING_LINK]]` — same link as Session 1.

**WHEN**
Toronto: Thursday 17 September, 8:00–9:30pm EDT
Hong Kong: Friday 18 September, 8:00–9:30am HKT — the next calendar day

**BEFORE YOU JOIN — 10 MINUTES, TODAY**

1. Open your Codespace (github.com/aayancheng/banking-analytics-workshop → Code → Codespaces)
   and run `python verify.py`. You want the green line ending: **you are here, and it works.**
   "Stage 5 verified" is the right answer — that is where Session 1 left everyone. We move to
   `stage-2` together during the lab; please don't jump ahead on your own.
2. Open the Session 2 lab sheet **on GitHub in your browser**, not inside the Codespace:
   `workshop/labs/S2-lab.md`. The stage jump during the lab hides the `workshop/` folder until
   you restore it; the browser copy never disappears.
3. If `verify.py` is red, reply today and I'll sort it with you before we start. If you're on
   a local install and it's red, the answer is: join from Codespaces.

**BRING THREE THINGS** — the Session 1 homework. Tomorrow opens on them.

- Your **WoE table**: one feature, five bins, count / bad rate / WoE per bin. The lab starts
  from it, and I'll ask who has one.
- Your **sealed number**: the held-out AUC you expect from your five chosen features. The first
  poll, at 8:04, collects it anonymously — *before* you see the answer. No number, nothing to
  learn from the gap.
- Your **five lines**: which of the four decision apps you would trust least, and what you'd
  check first. Two people read theirs out.

Didn't get to the homework? Come anyway — but write a number down before you join. Thirty
seconds, and it makes the reveal at 8:32 yours instead of mine.

**MISSED SESSION 1, OR WANT TO REWATCH?** The edited recording (59 minutes, with chapters)
and the write-up: `[[RECORDING_LINK]]` · `[[SUBSTACK_LINK]]`

Same two rules as last time: questions in the **chat**, not on mic; and the session is
**recorded**, so if something breaks on your end, nothing is lost.

See you tomorrow.

Yan

---

## Why it's shaped like this

Same single job as the S1 reminder — get people into the room with a working environment — plus
the one thing S2 needs that S1 didn't: **a number in their hand before they arrive.**

- **The link is first**, before any prose. On the night, people scroll to the top and click.
- **"Stage 5 verified is the right answer" is said in so many words.** Half the room will
  remember "Stage 1" from the slides and wonder whether they broke something. One sentence
  prevents forty chat messages at 8:01.
- **"Don't jump ahead" is stated, not implied.** Anyone who tries `git checkout stage-2` alone
  the night before hits the dirty-tree error from Session 1 and arrives rattled. The handoff is
  a group move with you on screen, for exactly that reason.
- **The lab sheet goes in the browser** because the 0:50 jump deletes `workshop/` until it is
  restored, and "where did the lab go?" cost minutes in S1.
- **The homework is asked for as three concrete objects** — a table, a number, five lines —
  not "please do the homework". Each maps to a specific minute of the session (Part A, Poll A,
  0:02), so the ask is honest about why it matters.
- **The fallback is a thirty-second action.** "Write a number down before you join" costs
  nothing and rescues the reveal for the people who did nothing else.
- **The recording link is one line.** It is not the point of this email; the S1 summary mail
  and the Substack post carry it properly.
