# Lab 2 — Bin, Weigh, Train, GATE (S2, 45 + 30 min)

**Checkpoint:** `stage-2` · The gate is **AUC ≥ 0.78 on the held-out split, hard assert** — and `verify.py` recomputes it from the tag's committed constant, so it cannot be negotiated locally.

> Lost? `git stash && git checkout stage-2 && python verify.py` puts you at a working scorecard.
> This sheet or the notebooks vanish after a stage jump? `workshop/` and `notebooks/` live on `main` and are in no tag — `git checkout main -- workshop notebooks` brings them all back from any stage, without moving you off it.
> Ports busy? `make stop`.

## Part A — bin and weigh by hand-ish (45 min, before the break)

**Both tracks do Part A manually.** You cannot review binning you've never done.

1. In a Python session (or notebook), take `dscr`, `utilization`, `prior_delinquencies` from `businesses.parquet`.
2. For each: cut into 4–6 bins (your choice — this is decision point #1), compute per-bin default rate and WoE:
   ```python
   import numpy as np, pandas as pd
   from shared.config import RAW
   biz = pd.read_parquet(RAW / "businesses.parquet")
   b = pd.qcut(biz["dscr"], 5)
   tab = biz.groupby(b, observed=True)["default"].agg(["count", "mean"])
   good = (1 - biz.groupby(b, observed=True)["default"].mean())
   # WoE per bin: ln(%goods in bin / %bads in bin) — write this yourself; it's 4 lines
   ```
3. Answer in your notes (these three feed your memo):
   - **Decision 1 — granularity:** what changed when you went from 4 bins to 6?
   - **Decision 2 — the drop:** which of the 15 features would you *exclude*, and why?
   - **Decision 3 — the smell test:** what WoE pattern would make you suspect leakage?

## Part B — train, evaluate, GATE (30 min, after the break)

### Agent track (prompt card AC-2)

1. Brief your agent with `workshop/prompt-cards/AC-2.md`, filling in your three Part-A decisions — the agent must *respect them*, not re-decide them.
2. **Review before you run the gate.** The review checklist on the card is your deliverable; the facilitator has a copy of what a good review catches tonight.
3. Converge below.

### Manual track

```bash
make train-score
```
Read the whole console output. You should see AUC/KS, the band table, and `GATE PASS`.
Then open `score/docs/validation_report.md` — check the band table is **monotonic** (D worst → AAA best).

### Converge (both tracks)

```bash
python verify.py     # [4/4] Model: scorecard + AUC gate .... OK
```

## If your gate FAILS

**Good.** Some configurations fail by design. The protocol — in this order:

1. Read the number. How far off is it? 0.001 or 0.05 are different diseases.
2. Check the band table — non-monotonic bands point at binning, not at the logistic.
3. Revisit your Part-A decisions (usually decision #2).
4. **What you may not do:** edit `AUC_GATE` in `train.py` and declare victory. Try it if you like — then run `python verify.py` and read what happens. The checkpoint reads the *committed* gate. This is the point of the entire evening.

## Decision memo (due S3, 1 page)

*My scorecard: what's in it, what I excluded and why, and the one question I'd fear from a validator.* Keep it — every memo becomes part of your S5 documentation pack.
