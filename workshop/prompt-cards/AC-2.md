# Prompt Card AC-2 — Train the Scorecard Under a Gate (Session 2)

**Your Part-A decisions go in the brief. The agent executes your judgment; it doesn't replace it.**

---

## The brief (copy, fill blanks, send)

> You are in the `banking-analytics-workshop` repo at `stage-2` (venv at `.venv`). Reviewer: **[YOUR NAME]**.
>
> **Task:** train and evaluate the Business Credit Score scorecard, respecting MY modeling decisions:
>
> - Binning granularity: **[YOUR DECISION 1 — e.g. "keep optbinning defaults" or "max 5 bins per numeric"]**
> - Feature exclusion: **[YOUR DECISION 2 — the feature you drop, or "keep all 15"]** — if you exclude, edit `FEATURE_COLUMNS` in `score/src/feature_engineering.py` and nothing else.
> - Report to me anything that looks "too good to be true" per: **[YOUR DECISION 3]**
>
> 1. Run `make train-score`. Report AUC, KS, and the score-band default table verbatim.
> 2. The gate is AUC ≥ 0.78, hard-asserted. If the gate FAILS: do not tune hyperparameters blindly, do not touch the gate. Diagnose (band monotonicity first), propose ONE change, and wait for my approval.
> 3. Confirm the leakage assertion ran (quote the line of code that enforces it).
> 4. List every file you changed. Changing `AUC_GATE`, anything in `verify.py`, or any file under `shared/data/` is out of bounds.

---

## Your review checklist

- [ ] Band table monotonic D → AAA? Quote it back from *the report file*, not the agent's summary.
- [ ] Did it change ONLY the files your decisions authorize? (`git status` — anything else is a finding.)
- [ ] Ask it: *"What is the weakest variable in this scorecard and what evidence says so?"* A good answer cites IV or coefficient, not vibes.
- [ ] `python verify.py` yourself — the recomputed AUC is the only number that counts.
