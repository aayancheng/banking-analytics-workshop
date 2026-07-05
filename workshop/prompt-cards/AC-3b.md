# Prompt Card AC-3b — Price the Book, Find the Money (Session 3)

**This one is an analysis brief, not a build brief.** The engine already exists and has machine-precision tests; the agent's job is to run it and help you find the story.

---

## The brief (copy, fill blanks, send)

> You are in the `banking-analytics-workshop` repo at `stage-3` (venv at `.venv`). Reviewer: **[YOUR NAME]**.
>
> **Task:** price the booked portfolio and prepare the mispricing analysis for my one-slide "so what."
>
> 1. Run `make price`. Report: share clearing the 15% ROE hurdle, median ROE at quoted, total mispriced EAD, and the mispricing rate by score band.
> 2. The AAA band's mispricing rate will look wrong for a "safe" band. Using ONLY the closed-form waterfall in `pricing/src/engine.py`, decompose the hurdle-clearing rate for a PD = 0.01 loan into its components and show which components a low quoted rate fails to cover.
> 3. Segment mispriced EAD by score band × industry. Give me the top 5 segments by dollar amount, with count and average rate shortfall.
> 4. Recommend ONE segment to reprice first and give the argument in ≤ 3 sentences: **[TELL IT YOUR PRIORITIZATION CRITERION — e.g. dollars at stake, or fewest clients to call, or lowest relationship risk]**
> 5. Touch no source files. Engine outputs only.

---

## Your review checklist

- [ ] Do its headline numbers match `pricing/docs/summary.json` exactly? (If not, it recomputed something itself — find out what.)
- [ ] Is the AAA decomposition arithmetic you can re-add on paper? Do it once.
- [ ] Does its recommended segment actually follow YOUR criterion, or its own?
- [ ] `python verify.py` — pricing totals are tolerance-checked against the committed summary.
