# Prompt Card HW-H1.2 — The Ladder's Middle Rung (Session 1 homework)

**Kind: Build.** You are the reviewer. The agent builds the leak that ships — a model that
quietly uses the generator's true PD — measures it, and then removes it.

**Goal.** Two held-out AUCs from the same recipe — honest, and honest plus the true PD — and
one sentence on why the second model cannot ship.

---

## The brief (copy, fill the blank, send to your agent)

> You are in the `banking-analytics-workshop` repo on `main`, at the repo root. Run Python
> with `.venv/bin/python`. Reviewer: **[YOUR NAME]**.
>
> **Task:** measure what leaking the true PD buys a model.
>
> 1. Use the leakage probe's recipe from `workshop/labs/S1-lab.md`, exactly: the four honest
>    features `dscr`, `leverage`, `utilization`, `prior_delinquencies` from
>    `shared/data/raw/businesses.parquet`; target `default`; `LGBMClassifier(verbose=-1)`;
>    `train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)`.
> 2. Fit two models: the honest one, and the same four features plus
>    `pd_default_origination`. Report each held-out AUC to four decimals, and the population
>    it was measured on.
> 3. Write a short report to `wiki/homework/_answers/H1.2.md`: both AUCs, the gain, and one
>    sentence on why the second model cannot ship.
> 4. Put the script outside the repository, or delete it once you have the numbers. Change
>    nothing under `shared/`.

---

## What "done" looks like

- Two AUCs, four decimals, on the held-out applicants, from one recipe.
- A sentence that says the true PD does not exist when the decision is made.
- `git status` shows no probe script and no change under `shared/`.

## Check it

```bash
python -m wiki.homework.check H1.2
```

The check refits both rungs itself and compares them with your answer (three or four
decimals, or a percentage). It wants the decision-time sentence, fails if a script that fits
a model on the true PD is left untracked in the repository, and fails if `LEAKAGE_COLUMNS`
has moved.

## The trap

- **The number looks fine.** The middle rung is not near 1.0. It is the kind of AUC a good
  scorecard reaches, so a review that only reads the metric passes it. The exercise is to say
  why it is still wrong.
- **A different recipe, a different number.** More trees, another seed or another split give
  another AUC. Same recipe, or the comparison with the honest rung means nothing.
- **Leaving it behind.** The lab says: run it, read the numbers, delete the file. A probe left
  in the repository is a leak waiting for someone to import it.
