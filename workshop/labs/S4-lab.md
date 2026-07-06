# Lab 4 — Early Warning & Line Management (S4, 40 + 40 min)

**Checkpoint:** `stage-4` · Tonight contains the program's most important lesson. Don't read ahead past Part A, step 3 — seriously.

> First command: `make stop`. Lost? `git stash && git checkout stage-4 && python verify.py`.
> Weak laptop + big panel? Codespaces. (The lab reads a pre-aggregated feature cache; the full 200,064-row groupby is optional.)

## Part A — the Early Warning System (40 min)

### Step 1 — write down your expectation

Before training anything, write one number in your notes: *the AUC that would make you proud tonight.* No revising later.

### Step 2 — train

**Agent track (card AC-4a):** brief the agent per the card; its evaluation report is the review object tonight.
**Manual track:**
```bash
make train-ews
```

Read the output: AUC **0.662** · PR-AUC **0.308** · top-decile capture **21.6% = 2.16×**.
Compare with your Step-1 number. Sit with the feeling. **Do not tune anything.**

### Step 3 — measure the ceiling

```bash
python workshop/labs/oracle_ceiling.py
```

It prints three numbers: the noise-free latent's AUC (perfect knowledge of the true drivers), a strong oracle model on observables, and your model. Answer in your notes:

1. Where is your model relative to the ceiling?
2. Was your Step-1 expectation *achievable on this data at all*?
3. Re-grade your model against the **honest gate** (capture ≥ 2×, PR-AUC > 18.0% base). Verdict?

### Step 4 — the watchlist is the product

Open the portal (`make run` → http://localhost:8100). Look at the top-10 watchlist: every account has **named triggers** (HIGH_UTILIZATION, DEPOSIT_DECLINE…), not just a probability. Why do named rules ride alongside the model score in a bank? Two reasons — write them down. (Hint: one is about the relationship manager's phone call, one is about the validator.)

## Part B — line management + your whole platform (40 min)

```bash
make train-line-increase && python verify.py && make run
```

1. **The four simultaneous gates:** find in the summary how many of 8,336 accounts get an offer (**95**). Walk one candidate: probability ≥ threshold, PD ≤ appetite ceiling, amount > 0, incremental ROE ≥ 15%. Which gate kills most candidates? (The app's summary segments help.)
2. **Cohort quality check** — the numbers a validator would demand: cohort PD **0.036** vs book **0.117**; cohort utilization **0.837** vs book **0.471**; aggregate incremental ROE **0.215**. Say in one sentence why *each* comparison matters.
3. **The lifecycle walkthrough (pairs, 3 min each):** one business, five modules, partner asks one "why?" per module. This is your capstone rehearsal.

## Converge

```bash
python verify.py     # ✅ Stage 4 verified — you are here, and it works.
```

**Homework:** skim the instructor doc pack (`docs/model_doc_pack/MODEL_DOCUMENTATION.md`). Mark the two sections you could not yet write for YOUR platform. Bring all four memos next week — they become your documentation pack, and you defend it.
