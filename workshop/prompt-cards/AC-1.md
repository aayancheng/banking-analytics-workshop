# Prompt Card AC-1 — Generate & Audit (Session 1)

**You are the reviewer.** The card below is a *brief*, not a script — read it before you send it, and fill the two blanks.

---

## The brief (copy, fill blanks, send to your agent)

> You are working in the `banking-analytics-workshop` repo (you are at repo root; a `.venv` exists; run Python via `.venv/bin/python`). Reviewer: **[YOUR NAME]**.
>
> **Task:** regenerate the synthetic SME portfolio and produce a data-audit report I will review.
>
> 1. Run `make data`. Confirm the console reports exactly 12,000 businesses / 8,336 booked / 200,064 panel rows, default rate 0.167, booked 0.695. If ANY number differs, STOP and report — do not continue, do not "fix" anything.
> 2. Read `shared/config.py` and list the LEAKAGE_COLUMNS with a one-line reason each for why it must never be a model feature.
> 3. Audit `shared/data/raw/*.parquet` and write `reports/audit_AC1.md` containing: null counts (must be 0); default rate by industry and by region; default-rate rank-ordering across quartiles of `dscr` and of `utilization` (state the expected direction and whether the data obeys it); the 5 largest `requested_amount` values with their PD band.
> 4. Also answer: **[YOUR ONE EXTRA AUDIT QUESTION]**
> 5. Do NOT modify any file under `shared/` — you are auditing, not fixing. End by printing the audit file path and a 5-line summary.

---

## Your review checklist (do this when it reports back)

- [ ] Did it actually run the generator, or just read the pre-baked files? (Check timestamps.)
- [ ] Are the rank-ordering directions *stated and checked*, or just tabulated?
- [ ] Did it answer your extra question, or paraphrase it away?
- [ ] Find **one thing it did not check** and send it back to check that.
- [ ] **Mark it against the notebook.** `git checkout main -- workshop notebooks`, run
      `notebooks/01_stage1_portfolio.ipynb`, and compare its IV scan to what the agent reported.
      Where the agent found a story in a column the scan gives an IV near zero, that is the
      finding — the agent did what you nearly did with the industry chart in the session. An
      audit you can mark against independent evidence is the only kind worth having.
- [ ] Run `python verify.py` yourself. The checkpoint is never delegated.
