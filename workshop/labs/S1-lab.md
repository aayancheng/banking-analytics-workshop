# Lab 1 — Generate & Audit the Portfolio (S1, 60 min)

**Checkpoint:** `stage-1` · **Both tracks end at the same place.** `verify.py` cannot tell which track you took, and neither can your grade.

> **If anything breaks for more than 5 minutes:** open this repo in GitHub Codespaces and keep moving. Fix your laptop later.
> **If you edited something and are lost:** `git stash && git checkout stage-1 && python verify.py`
> Notebooks vanish after a stage jump? They live on `main` only — `git checkout main -- notebooks` brings them back from any stage.

## Before you start (both tracks)

```bash
git checkout main -- workshop notebooks   # if this sheet vanished when you jumped to stage-1
make stop && python verify.py             # stage-1 green (this lab needs shared/)
```

**Why the first line.** `workshop/` and `notebooks/` live on `main` and are in **no stage tag**,
so jumping to `stage-1` removes this sheet, the AC-1 card and `CHECKPOINTS.md` from your
checkout. That one command brings them back **without moving you off `stage-1`**. You can also
just read them on GitHub in a browser — that always shows `main`.

The first `verify.py` after a fresh install is slow (cold imports). Run it twice; the second run is the real speed. That's normal.

---

## Agent track (prompt card AC-1)

You are the **reviewer**, not the typist. The agent generates and audits; you grade its audit.

1. Open prompt card `workshop/prompt-cards/AC-1.md`. Fill in the two blanks (your name, your one extra audit question).
2. Give the brief to your agent (Claude Code, Copilot CLI — anything that can run shell + Python).
3. While it works, write down: *what would a lazy agent skip?*
4. When it reports, review its audit output against the checklist below. **Find at least one thing it did not check** and make it check that.
5. Run the convergence commands (bottom of this sheet) yourself. Never outsource the checkpoint.

## Manual track

1. Regenerate the data yourself (the repo ships it pre-baked; regeneration proves determinism):
   ```bash
   make data
   ```
   Expected console output — yours must match **exactly** (seed 42):
   ```
   businesses: 12,000 rows, default rate 0.167, booked 0.695
   portfolio:  8,336 accounts, deterioration 0.180, line_increase_good 0.222
   panel:      200,064 rows (24 months)
   ```
2. Open `reports/data_quality.md` (just regenerated). Work through the audit checklist below, ticking each item against the report + your own spot checks in Python.

## The audit checklist (both tracks)

- [ ] Row counts: 12,000 / 8,336 / 200,064 — and *why is 8,336 not a round number?*
- [ ] Zero nulls (synthetic data is complete by construction — a null is a bug)
- [ ] Default rate 16.7% overall. Check it **by industry**: does any industry look implausible?
- [ ] Rank-ordering sanity: split `dscr` into quartiles — does default rate fall as DSCR rises? Do the same for `utilization` (should rise).
- [ ] The deny-list: open `shared/config.py::LEAKAGE_COLUMNS`. For each of the 6 columns, say *in one sentence* why it's forbidden.

## The leakage probe (everyone, together — last 10 minutes)

Feel the poison once, on purpose:

```python
# leakage_probe.py — run it, read the two numbers, then delete this file
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from shared.config import RAW

biz = pd.read_parquet(RAW / "businesses.parquet")
X_ok  = biz[["dscr", "leverage", "utilization", "prior_delinquencies"]]
X_bad = X_ok.assign(cheat=biz["pd_default_origination"])   # <- deny-listed column
y = biz["default"]
for name, X in [("honest", X_ok), ("LEAKED", X_bad)]:
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    m = LGBMClassifier(verbose=-1).fit(Xtr, ytr)
    print(f"{name}: AUC = {roc_auc_score(yte, m.predict_proba(Xte)[:, 1]):.4f}")
```

Write down both numbers. In production, the second number is what a **silent join mistake** looks like. It will not announce itself with a `cheat` column name.

## Converge (both tracks)

```bash
python verify.py            # ✅ Stage 1 verified — you are here, and it works.
python verify.py --json     # show the facilitator on the way out
```

## Homework — 30 minutes, and Session 2 gets twice as useful

Open `notebooks/01_stage1_portfolio.ipynb` and run it — you already restored it with the command
at the top of this sheet. (If it is missing: `git checkout main -- workshop notebooks`.) The
notebook ends with a checkpoint card and the full brief for items 1–3.

1. **Bin one feature by hand and compute WoE.** `dscr`, `utilization` or `prior_delinquencies`,
   five bins, count + bad rate + WoE per bin. Lab 2 Part A opens with exactly this. Bring the table.
2. **Five in, five out.** From the 20 safe columns, name five you would put in a scorecard and
   five you would refuse — one line each. The notebook's IV scan is evidence, not a verdict.
   You saw one case in the session: default rate by industry looks like a finding and has an IV
   of 0.006. There are nineteen more columns and the scan puts a number on every one of them —
   including two that carry real signal without having any causal role at all.
3. **Seal a number.** Write down the held-out AUC you expect from your five features. The S2 gate
   is 0.78. You only learn anything from the gap if you commit before you see the answer.
4. **Read the reference build journal**
   (teamyan.substack.com/p/claude-code-credit-app-suite). Five lines: *which of the four decision
   apps would you trust least, and what would you check first?*

**Optional, if you want the longer version:** `workshop/reading/S1-data-generation.pdf` — the
data-generating process in full. Every weight in the default logit, the eleven columns with no
causal role (and the two of them that predict anyway), and how the 0.78 gate was set against a
ceiling that was measured first. Not assigned, not assessed.
