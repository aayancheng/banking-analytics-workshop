# Notebooks — see what you just built

One notebook per stage. Each is a **visual read-out of that stage's key results**: run it after
`verify.py` goes green and you can see the thing you just built, rather than trusting a console
line that says it worked.

| Notebook | Run it after | Shows you |
|---|---|---|
| `01_stage1_portfolio.ipynb` | Session 1 | who is in the book (segments, size, skew), the applicant→booked funnel and what it selected on, row counts, null audit, rank-ordering plus an Information Value scan of all 20 candidate features, the panel over 24 months, the deny-list and the leakage probe — ending in a computed checkpoint card and homework for Session 2 |
| `02_stage2_score_spine.ipynb` | Session 2 | the AUC gate with its margin, the banded score distribution, default rate by band, ROC + KS, and one borrower's reason codes |
| `03_stage3_decisions_and_price.ipynb` | Session 3 | the approve/refer/decline mix, why people were referred, price as a function of risk, the ROE distribution, and where the $1.28B of mispricing sits |
| `04_stage4_portfolio_watch.ipynb` | Session 4 | watchlist tiers, how often each named trigger fires, the capture curve (work 10% of the book, catch how much?), and the line-increase cohort |
| `05_stage5_governance.ipynb` | Session 5 | every gate in the platform on one page, one borrower traced through all five modules, and the doc-pack contents |

## Running them

From the repo root:

```bash
make verify          # make sure the stage is green first
```

Then open the notebook in VS Code (or Codespaces) and pick the **`.venv`** kernel. If VS Code
offers to install a kernel, you should not need it — `ipykernel` is in `requirements.txt`, so
`make setup` already installed one.

Prefer the browser?

```bash
.venv/bin/python -m jupyter lab      # if you have jupyterlab installed
```

## Two things worth knowing

**They chdir to the repo root.** The first cell walks up from wherever you launched to find
`verify.py`, then changes directory there — because the modules use paths relative to the repo
root (e.g. `Path("score/models")`). So it does not matter where you start Jupyter.

**They stop early and tell you why.** Each notebook checks for the artifacts its stage needs. Run
the Session 4 notebook while you are still at `stage-2` and it will say so, and tell you the two
ways to fix it — rather than dying twelve cells later on a missing file.

**They reuse the real modules.** Nothing here re-implements the pipeline: the score comes from
`score.src.predict`, the decisions from `adjudication.src.policy`, the prices from
`pricing.src.portfolio`, and so on. If a notebook and the platform ever disagree, that is a bug
worth reporting — they are running the same code.

## If you jumped to an older stage

These notebooks live on `main` — **no stage tag contains them**, on purpose. They are a view onto
whatever stage you are at, so there is one copy that stays current instead of five frozen ones.
After `git checkout stage-N` they will seem to vanish. Bring them along:

```bash
git checkout main -- notebooks
```

That works from **any** stage, because it needs nothing but git.

There is also `make notebooks`, which does the same thing and refuses rather than overwriting if
you have unsaved notebook edits — but it only exists **on `main`**. Each stage tag ships the
Makefile it had at the time and the tags never move, so the target is not there after a jump.
Use it while you are on `main`; use the git command everywhere else.
