# Prompt Card AC-4b — Line Increases: Growth Inside Appetite (Session 4)

**Review focus:** the four-gate offer logic. An agent that reports "95 offers" without being able to say *which gate binds* has produced a number, not an analysis.

---

## The brief (copy, fill blank, send)

> You are in the `banking-analytics-workshop` repo at `stage-4` (venv at `.venv`). Reviewer: **[YOUR NAME]**.
>
> **Task:** train the line-increase model and explain the offer funnel.
>
> 1. Run `make train-line-increase`. Report AUC, lift, and the full cohort block (n offered, cohort vs book PD, cohort vs book utilization, aggregate incremental ROE).
> 2. Build me the funnel: of 8,336 accounts, how many survive each gate applied in sequence — probability ≥ threshold → PD ≤ appetite ceiling → recommended amount > 0 → incremental ROE ≥ hurdle? Use `line_increase/src/` code paths; do not invent your own rules.
> 3. Name the binding gate (the one that eliminates the most candidates among those who passed the previous gates) and explain in 2 sentences why the bank WANTS it to bind.
> 4. Touch no config, no gates, no source files.

---

## Your review checklist

- [ ] Funnel arithmetic: do the stage counts actually sum/telescope correctly?
- [ ] Cross-check "95 offers" against `line_increase/models/metadata.json` (`cohort.n_offered`).
- [ ] Ask it: *"Why is offering to only ~1% of the book a success rather than a failure?"* — the answer should mention risk appetite and incremental economics, not model shyness.
- [ ] `python verify.py` yourself.
