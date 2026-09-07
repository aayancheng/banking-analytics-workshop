# Lab 3 — Adjudicate, then Price the Book (S3, 45 + 40 min)

**Checkpoint:** `stage-3` · Two apps running against **your** stage-2 scorecard.

> First command of the night, always: `make stop` (S2 leftovers hold the ports).
> Lost? `git stash && git checkout stage-3 && python verify.py`.
> This sheet or the notebooks vanish after a stage jump? `workshop/` and `notebooks/` live on `main` and are in no tag — `git checkout main -- workshop notebooks` brings them all back from any stage, without moving you off it.

## Part A — the adjudication app (45 min)

### Agent track (prompt card AC-3a)

Brief the agent to train the adjudication model and wire it to *your* scorecard. **Review focus for tonight:** did the agent respect the committed policy config, or did it quietly re-tune the cutoffs? Check `adjudication/models/policy_config.json` against what it reports.

### Manual track

```bash
make train-adjudication      # LightGBM + policy calibration; ends in GATE PASS
make run                     # → http://localhost:8100
```

### Everyone — the three measurements

1. **Read three decision trails** (one Approve, one Refer, one Decline — use the example chips on the page). For each: did the *model* or a *rule* decide?
2. **Count the knockouts.** Of all Declines, how many had at least one hard-rule hit? Estimate: *what share of tonight's decisions did the model actually make?* Write the number down **before** the debrief.
3. **Swap-set vs your scorecard.** The app shows model PD and business score side by side. Find one applicant where challenger and scorecard disagree materially. Which do you believe, and what would it cost to be wrong?

Reference decision mix (yours should match): **Approve 30.8% / Refer 36.8% / Decline 32.4%**

## Part B — the pricing engine (40 min)

```bash
make price
python verify.py             # pricing totals must match the committed summary
```

Open the dashboard (`make run` → http://localhost:8100). Confirm your three headline numbers:

| Yours tonight | Expected |
|---|---|
| Share clearing the 15% hurdle | **30.4%** |
| Median ROE at quoted | **10.9%** |
| Mispriced exposure | **$1.28B** |

### The "so what" (this is the actual lab)

1. Which **score band** has the worst mispricing rate? (You expect the risky bands. Check AAA.)
2. Explain the AAA result in two sentences using the waterfall: what floor can a low quoted rate not cover, even at tiny PD?
3. Pick the **one client segment** (band × industry) you'd call first about repricing, and say why: exposure? win-back odds? relationship risk?
4. One slide, 60 seconds, per team at 2:40.

## Converge

```bash
python verify.py     # ✅ Stage 3 verified — you are here, and it works.
python verify.py --json
```

## Decision memo (due S4, 1 page): "Defend your cutoff"

Approval rate you chose · expected loss at that cutoff · swap-set winners/losers vs the challenger · the repricing call you'd make first. This memo is graded on *reasoning under trade-offs*, not on matching the reference numbers.
