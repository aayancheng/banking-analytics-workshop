# Prompt Card HW-H2.1 — Bureau Feed Down: Document a Gate Failure (Session 2 homework)

**Kind: Build.** You are the reviewer. The agent refits the scorecard without the credit
bureau; you make sure it reports the failure instead of engineering it away.

**Goal.** A refit without the four bureau columns, its held-out AUC, and one plain sentence on
what that does to the gate — with the committed scorecard and the gate exactly as they were.

---

## The brief (copy, fill the blank, send to your agent)

> You are in the `banking-analytics-workshop` repo on `main`, at the repo root. Run Python
> with `.venv/bin/python`. Reviewer: **[YOUR NAME]**.
>
> **Task:** measure what happens to the Business Credit Score if the credit bureau feed goes
> down.
>
> 1. Read `score/src/train.py` and reuse its recipe exactly: same `FEATURE_COLUMNS` minus the
>    dropped ones, same `BinningProcess` and `LogisticRegression`, same `train_test_split`
>    (`test_size=0.2`, `random_state=SEED`, `stratify=y`).
> 2. Drop exactly these four bureau columns: `utilization`, `credit_history_months`,
>    `prior_delinquencies`, `trade_lines`.
> 3. Do the refit in a scratch script outside the repo's tracked files. Do **not** run
>    `make train-score`, do not write anything under `score/models/`, and do not edit
>    `AUC_GATE` or `verify.py`.
> 4. Report the held-out AUC and KS to four decimals, the population they were measured on,
>    and whether the refit passes the committed gate. If it fails, say so and stop — do not
>    tune it until it passes.
> 5. Write your report, in three or four sentences, to `wiki/homework/_answers/H2.1.md`.

---

## What "done" looks like

- One AUC and one KS, four decimals, on the held-out applicants.
- A sentence that says what happened to the gate, in the word *gate*.
- `git status` shows nothing changed under `score/` or in `verify.py`.

## Check it

```bash
python -m wiki.homework.check H2.1
```

The check recomputes the no-bureau AUC itself and compares it with your answer, and it
fails if the gate in `score/src/train.py` or `verify.py` has moved.

## The trap

- **Relaxing the gate.** The exercise is to *document* a failure. An agent that lowers
  `AUC_GATE`, or keeps adding bins until it passes, has solved the wrong problem. The check
  fails you for the first; your review has to catch the second.
- **Overwriting the committed model.** `make train-score` rewrites `score/models/`. If that
  happened: `git checkout -- score/`.
- **The wrong fourth column.** The S2 lab sheet drops `public_records` instead of
  `trade_lines`. Both refits are correct for their own column set; they give different
  AUCs, and this exercise (and D4.6) uses `trade_lines`.
