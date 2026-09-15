# Lab 2 — Bin, Weigh, Train, GATE (S2, 28 min, guided)

**Checkpoint:** `stage-2` · The gate is **AUC ≥ 0.78 on the held-out split, hard assert** — and `verify.py` recomputes it from the tag's committed constant, so it cannot be negotiated locally.

> Lost? `git stash -u && git checkout stage-2 && git checkout main -- workshop notebooks && python verify.py` puts you at a working scorecard with this sheet and the notebooks back.
> This sheet or the notebooks vanish after a stage jump? `workshop/` and `notebooks/` live on `main` and are in no tag — `git checkout main -- workshop notebooks` brings them all back from any stage, without moving you off it.
> Ports busy? `make stop`.

**This lab is done together, on screen, in 28 minutes.** The facilitator drives the first four
minutes of Part A; you take over from there. Everything below Part B is homework if the clock
runs out — Part B is the part that must happen tonight.

## Before you start (everyone, 1 minute)

```bash
git stash -u && git checkout stage-2 && git checkout main -- workshop notebooks
python verify.py          # [4/4] Model: scorecard + AUC gate ... OK
```

You are now at the finished checkpoint with the notebooks restored. Open
`notebooks/02_stage2_score_spine.ipynb` in VS Code and **Run All** once — it needs the
stage-2 artifacts you just checked out, and takes under a minute on a cold kernel.

## Part A — bin and weigh, in the notebook (12 min)

**Both tracks do Part A by hand.** You cannot review binning you've never done. Everything
happens in **§6 "Build one by hand"** — the WoE table, the fit and the points are already
wired up; you change two lines and re-run.

1. Find the cell that starts with `VAR = "dscr"`. Run it as is. Read the WoE column
   top to bottom — is it monotonic? (It should be. Say why.)
2. Change `VAR` to `"utilization"` with
   `EDGES = [-np.inf, .25, .40, .55, .70, .85, np.inf]` and re-run the three cells.
   The WoE column runs the *other* way. **Should** it?
3. Then `"prior_delinquencies"` with `EDGES = [-np.inf, 0, 1, 2, np.inf]`. Four bins is
   all it has to give — why?
4. Go back to `dscr` and try `EDGES = [-np.inf, 1.0, 1.25, 1.5, np.inf]`. IV drops from
   0.209 to 0.184. **That is decision 1 — granularity — with a price on it.**
5. Run the **"Your turn"** IV scan at the end of §6. The bottom of that chart is where
   decision 2 lives.

Brought a WoE table from the Session 1 homework? The section **"Session 1 homework, worked"**
at the top of the notebook finishes the lab snippet exactly — `utilization`, five quantile bins,
all 12,000 rows, IV 0.1756. If you used those settings your numbers match to the fourth
decimal; if you cut differently the numbers move but the *shape* should not. Its second cell
scores your **five in / five out** against the AUC you sealed — put your number in `SEALED`
before you run it.

**Write down, for your memo:**
- **Decision 1 — granularity:** what changed when you went from 4 bins to 6?
- **Decision 2 — the drop:** which of the 15 features would you *exclude*, and what evidence says so?
- **Decision 3 — the smell test:** what WoE pattern would make you suspect leakage rather than signal?

## Part B — train, evaluate, GATE (10 min)

Apply decision 2. Edit `FEATURE_COLUMNS` in `score/src/feature_engineering.py` and remove the
one feature you chose — nothing else. Then:

### Manual track

```bash
make train-score      # trains, evaluates, and asserts the gate
python verify.py      # recomputes AUC independently — the only number that counts
```
Read the whole console output: AUC/KS, the band table, and `GATE PASS` or the assertion.
Then open `score/docs/validation_report.md` — is the band table **monotonic** (D worst → AAA best)?

### Agent track (prompt card AC-2)

Brief your agent with `workshop/prompt-cards/AC-2.md`, filling in your three Part-A decisions —
the agent must *respect them*, not re-decide them. **Review before you run the gate.** The
review checklist on the card is your deliverable.

### Converge (both tracks)

```bash
python verify.py     # [4/4] Model: scorecard + AUC gate .... OK
```

**Nobody leaves un-green.** If you are red at 1:15, restore the checkpoint model and keep your
notes: `git checkout stage-2 -- score/models`.

## Part C — if there is time (5 min): try to cheat

You watched this live at 0:32. Now do it yourself. Drop the four bureau columns
(`utilization`, `credit_history_months`, `prior_delinquencies`, `public_records`) and run
`make train-score` — AUC 0.7643, the gate fails. Now set `AUC_GATE = 0.75` in
`score/src/train.py` and run it again: `GATE PASS`. Then:

```bash
python verify.py
#   [4/4] Model: scorecard + AUC gate ............ FAIL
#         ❌ held-out AUC 0.7643 is below the committed gate 0.78
git checkout -- score/      # put it all back; verify.py goes green again
```

`verify.py` carries its own copy of the gate and recomputes the AUC from the saved model.
Nothing you edit locally reaches it. **This is the point of the entire evening.**

## If your gate FAILS

**Good.** Some configurations fail by design. The protocol — in this order:

1. Read the number. How far off is it? 0.001 or 0.05 are different diseases.
2. Check the band table — non-monotonic bands point at binning, not at the logistic.
3. Revisit your Part-A decisions (usually decision 2 — you dropped something that carried signal).
4. **What you may not do:** edit `AUC_GATE` in `train.py` and declare victory. Part C shows you why.

## Homework (due S3)

1. Finish the notebook. **§7 "Does the gate hold where you lend?"** re-measures the committed
   model on booked-only loans — 0.8176 becomes 0.7447. Write three lines: which population
   *your* gate is measured on, and what you would do about it.
2. **Decision memo (1 page):** *My scorecard: what's in it, what I excluded and why, which
   population my gate is measured on, and the one question I'd fear from a validator.*
   Keep it — every memo becomes part of your S5 documentation pack.
