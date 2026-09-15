# Session 2 polls — four launches

**Facilitator notes. Not student-facing.** Same rules as [session-polls.md](session-polls.md)
(the Session 1 set): create them in the Zoom **web portal** on the scheduled meeting, **every
poll anonymous**, find the launch button before 8:00pm, and **share the results out loud** —
a poll you collect silently is a survey.

Session 1's three polls were the highest-engagement minutes of the night. Session 2 gets four,
and two of them are load-bearing: A sets up a reveal at 0:32, and C sets up the reveal at 0:44.
Neither slide works if its poll was skipped.

---

## Poll A — "The number you sealed" · launch 0:04

**Why:** Session 1's homework item 4 asked them to write down the held-out AUC they expected
from their five chosen features *before* tonight, and promised it would be "collected at the
top of S2." This is the collection. Launch it while `verify.py` is running on their screens.

One question, anonymous.

**The AUC you sealed before tonight — which bucket?**
- Below 0.70
- 0.70 – 0.75
- 0.75 – 0.80
- 0.80 – 0.85
- Above 0.85
- I didn't seal one

**Share the results, but do not reveal 0.8176 yet.** Say only: *"hold that thought — you'll
find out at half past."* The reveal is at 0:32, right after the gate demo, where 0.7643 (the
model without bureau data) and 0.8176 (the full card) land back to back. Whoever sealed
0.70–0.75 was closer than they think, and you get to say why.

---

## Poll B — "How many bins?" · launch 0:20

**Why:** it turns the binning slide from exposition into a decision they have just made, and it
is decision #1 in the lab. Everybody has an opinion about this one; nobody is wrong.

One question, anonymous, 30 seconds.

**You are binning DSCR for a scorecard. How many bins?**
- 3 — coarse and stable
- 4 – 5
- 6 – 8
- Let the optimizer decide
- Depends — I'd want to see the data first

**What you do with it:** two slides on, the worked example shows 6 hand-picked bins at IV 0.209
and optbinning's 8 at 0.247. Read the poll back against that: *"most of you said 4–5; the
machine wanted 8 and bought 0.04 of IV for it. Would you take that trade? A validator will ask
you the same question."* The "depends" option is the right answer and you should say so.

---

## Poll C — "Where does the gate hold?" · launch 0:42

**Why:** this is the beat of the night. The poll is what makes the reveal land — a number
shown cold is information; a number shown after they have committed to a guess is a lesson.

One question, anonymous, 45 seconds. Launch it **from the "12,000 scored. 8,336 booked." slide**,
after you have said out loud that a bank never observes outcomes on the loans it declined.

**This scorecard scores 0.8176 held out on all 12,000 applicants. On just the 8,336 the bank
would actually book, its AUC is…**
- Higher
- About the same
- Lower
- No idea — how would I know?

**Share the results, then advance.** The next slide is the table: 0.8176 on everyone,
**0.7447 on booked-only — below the 0.78 gate.** If most of the room said "lower," say
*"you're right, but by how much — and did you expect it to fail its own gate?"* If most
said "about the same," better still: that is exactly the assumption that ships.

**Then count to ten in silence.** Do not resolve the reject-inference question; it is homework.

---

## Poll D — "One question before you go" · launch 1:29

Session 1's Poll C, verbatim. Anonymous. Twenty seconds. **Do not share these results on screen.**

**Tonight was:**
- Too slow — I wanted more
- About right
- Too fast — I lost the thread
- I got stuck on setup and missed most of it

Read it afterwards, next to Session 1's. The fourth option is the one you are running the
pilot to find, and the delta between the two weeks is the first real signal you have on
whether the 90-minute cut is working.

---

## Before the day

- [ ] All four created in the web portal on the **scheduled** meeting, anonymous
- [ ] A and C are load-bearing — if you must cut one, cut B
- [ ] Co-host can launch them if you are mid-demo (C lands while you are driving a terminal)
- [ ] Download the poll report afterwards; A tells you how calibrated the room's intuition is,
      and that number belongs in the S5 doc-pack discussion
