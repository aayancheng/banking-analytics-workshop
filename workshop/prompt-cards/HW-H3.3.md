# Prompt Card HW-H3.3 — Audit an Early-Warning What-If (Session 3 homework)

**Kind: Audit.** You are the validator. Below is a what-if function for the early-warning
tiers. It looks reasonable and its simplest test passes. The defect in it is a real one: the
loan workbench shipped with it, and its fix is in this repository's history.

**Goal.** A finding: which accounts the what-if gets wrong with the committed cutoffs, why,
whether its docstring is true, and the fix.

---

## The code under review

Save it as `whatif_tiers.py` in a scratch folder **outside** the repository:

```python
# whatif_tiers.py -- a what-if for the early-warning tiers (planted for H3.3)
import json
from ews.src import watchlist as wl

BOOK = wl.score_population()
TIERS = json.loads(open("ews/models/metadata.json").read())["tiers"]


def retier(t_high=None, t_med=None):
    """Every booked account's tier under these cutoffs. With no cutoffs given, reuse the
    batch tiers. Otherwise re-tier from the persisted prob: score_population stores only
    that column, so it is the best probability available."""
    if t_high is None and t_med is None:
        return BOOK["risk_tier"].tolist()
    cut = dict(TIERS)
    if t_high is not None:
        cut["t_high"] = t_high
    if t_med is not None:
        cut["t_med"] = t_med
    return [wl.risk_tier(p, cut) for p in BOOK["prob"]]
```

## The brief (copy, fill the blank, send)

> You are in the `banking-analytics-workshop` repo on `main`, at the repo root. Run Python
> with `.venv/bin/python` from the repo root, with `PYTHONPATH=.:<the scratch folder>` so
> both the repo's packages and `whatif_tiers.py` import. Reviewer: **[YOUR NAME]**.
>
> **Task:** audit `whatif_tiers.py`. The requirement: with the committed cutoffs, the what-if
> reproduces the batch tier of every booked account, whatever the caller sends.
>
> 1. Call `retier()` with no arguments, and `retier(**TIERS)` — the committed cutoffs sent
>    explicitly, which is what a screen with sliders sends on every change. Compare each with
>    `BOOK["risk_tier"]`, account by account.
> 2. List every account whose tier differs, with its stored `prob` and the cutoff involved.
> 3. Find the cause in `ews/src/watchlist.py`. Is the docstring's claim true? Check it.
> 4. Propose the fix, and the test that would have caught it.
> 5. Change no file under `ews/` or `app/`. Write the finding to
>    `wiki/homework/_answers/H3.3.md`.

---

## What "done" looks like

- Every account that changes tier, by ID, with its batch and what-if tier.
- The cause in one sentence, and a verdict on the docstring.
- A fix that leaves one path for every call, and a test that sends the committed values
  explicitly.

## Check it

```bash
python -m wiki.homework.check H3.3
```

The check re-runs the defect itself. It wants every account the defect re-tiers named by ID,
the cause (what was done to the stored `prob`), the fix (which probability to re-tier from),
and nothing changed under `ews/` or `app/`.

## The trap

- **The easy test.** `retier()` with no arguments returns the batch tiers, so it passes. The
  bug is on the path a real caller takes.
- **"Two accounts out of 8,336 — immaterial."** A what-if that moves a loan to another tier
  with nothing changed is lying, and a reviewer who sees it once stops trusting every screen.
  The rule in this repository is that the what-if equals the batch, exactly.
- **Believing the docstring.** It states a fact about the code. Check it.
