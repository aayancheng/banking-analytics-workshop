# CLAUDE.md — working notes for this repo

Teaching repo for a 5-session workshop that rebuilds a small-business lending analytics
platform. Public, MIT. The audience is bank risk/analytics practitioners, many not fluent
in git or containers.

## The one promise

`python verify.py` tells you where you are and that it works. Everything else serves that.
`verify.py` reads `stage.txt`, runs the checks for that stage, and recomputes every claim from
scratch — it never trusts a stored result.

## Layout

```
shared/        data generator, config (LEAKAGE_COLUMNS, MARKET), data-quality report
score/         WoE scorecard — the score spine every other module consumes
adjudication/  model + policy layer -> Approve / Refer / Decline + reasons
pricing/       deterministic ROE engine (NO ML) -> rate, mispricing
ews/           behavioural early warning -> tiered watchlist + named triggers
line_increase/ candidate model + amount rules + incremental economics
app/           FastAPI portal (port 8100) — orchestrates modules, never re-implements them
tools/         doc-pack builder
notebooks/     one per stage: a visual read-out of that stage's key results
workshop/      slides, labs, prompt cards, CHECKPOINTS.md (students), facilitator/
workshop/reading/  optional post-session notes: .html is source, .pdf committed beside it
```

## Invariants — do not break these

1. **Never move a stage tag.** `stage-0..stage-5` are the curriculum's fixed checkpoints;
   students are promised that jumping to one always works. Fix forward on `main` and cut a new
   `v1.x` instead. (This is why the devcontainer fix in v1.2 lives only on `main`.)
2. **Gates are committed promises.** Each module asserts its gate at train time. If one fails,
   investigate the model — never relax the gate. `ews` is deliberately gated on *top-decile
   capture*, with AUC **reported, not gated**, because the DGP's noise puts a real ceiling on it.
3. **Leakage deny-list lives in `shared/config.py::LEAKAGE_COLUMNS`** and is asserted by every
   feature module. Downstream code consumes the *saved model's* output, never DGP truth.
4. **Data and model artifacts are committed on purpose** so every stage is self-sufficient.
   That is not an accident; `.gitignore` says so.
5. **One service per module.** The portal and the notebooks call the module's own functions
   (`predict_score_pd`, `policy.decide`, `price_population`, `watchlist.score_population`,
   `candidates.score_population`). If a caller and the platform disagree, that is a bug.
6. **No attendee data in tracked files. This repo is public.** `.gitignore` keeps the Tally
   exports out (`*Submissions*.csv` anywhere in the tree), but that rule is only as good as the
   code beside it: a hardcoded email map in `cohort.py` once routed straight around it. Anything
   keyed by a real person's address lives in a gitignored file the script loads if present
   (`workshop/facilitator/email_fixes.json`), never in source. Grep the diff for `@` before any
   push.

## Verifying a change

Docs-only changes still deserve `python verify.py`. Anything touching code, deps or artifacts
gets the full sweep in a **clean clone with a fresh venv** (a warm `.venv` hides missing deps):

```bash
git clone <repo> /tmp/sweep && cd /tmp/sweep
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
for t in stage-0 stage-1 stage-2 stage-3 stage-4 stage-5; do
  git checkout -q $t && .venv/bin/python verify.py | tail -1
done
git checkout -q main && .venv/bin/python verify.py | tail -1
```

Also execute every notebook from that same clean clone (`pip install nbconvert` there — it is a
test-only tool, deliberately not a dep), and **test any stage-jump behaviour at the tag itself,
in the clean clone.** A worktree is not good enough: it carries `main`'s files, which is exactly
how `make notebooks` shipped as advice that does not work at any stage tag.

Then cut/annotate a `v1.x` tag recording what was verified.

## Gotchas discovered the hard way

- **Module metrics are nested**: `metadata.json` has `["metrics"]["auc"]` and `["gate"]["auc_min"]`,
  not top-level keys. Reading `d.get("auc")` silently yields `None`/`nan`.
- **Held-out vs in-sample**: `ews` capture is 21.6% held out but ~54% recomputed over the whole
  book (the model trained on most of it). Always quote the metadata number.
- **A line-increase "offer" is `eligible`** (95), not `recommended_amount > 0` (1,243).
  `candidates()` is the authority.
- **`ls` lies after a stage jump**: gitignored `__pycache__` keeps later-stage folders alive.
  Use `git ls-files` to show what a stage really contains.
- **Demo video is generated, not recorded.** `workshop/demo/capture_assets.py` renders the three
  data-derived assets (gitignored), then `make_demo.py` composes frames + MP4. Timing lives in
  `build_frames()`. Never hand-trim the MP4.
- **`nbconvert` is intentionally not a dependency** — students run notebooks in VS Code, which
  needs `ipykernel` (pinned). `nbconvert` is a test-only tool for executing notebooks headlessly.
- **Notebooks chdir to the repo root** because modules use root-relative paths like
  `Path("score/models")`.
- **`notebooks/` lives on `main` and is in no tag** — on purpose: one copy that stays current
  beats five frozen ones. A stage jump deletes it. The command to give a student is
  `git checkout main -- notebooks`, which needs nothing but git. **Not `make notebooks`** — that
  target exists only on `main`, because a tag ships the Makefile it had at the time and tags
  never move. Same trap applies to any future `make` target you are tempted to put in
  stage-jump advice.
- **Notebook 01 must run at `stage-1`, where `score/` does not exist.** It imports
  `FEATURE_COLUMNS` from `score.src.feature_engineering` inside a `try`, with a hard-coded
  fallback. Anything else it reaches for from a later stage needs the same treatment.
- **Reading notes render with headless Chrome** (`make reading`) — no npm, LaTeX or pandoc. The
  `.html` is source and the `.pdf` is committed beside it so students need no toolchain.

## The DGP, in numbers

Facts a session needs before touching Session 1 or 2 material. All recomputable — the appendix of
`workshop/reading/S1-data-generation.pdf` has the code, and the note itself is the long version.

- **9 of the 20 safe columns are in the default logit**, plus `profit_margin` (a generator
  primitive; `net_income = annual_revenue * profit_margin`). The other 11 have **no causal role**
  and split into two groups that fail differently:
  - *structural zeros* (`industry`, `region`, `entity_type`, `loan_purpose`, `term_months`,
    `collateral_flag`, `trade_lines`, `employees`) — IV 0.0005–0.006, effect exactly zero.
    `industry`'s tidy 3.3pp spread is the teaching case: an honest chart, an invented story.
  - *inherited proxies* (`requested_amount` IV 0.103, `net_income` 0.100, `total_debt` 0.014) —
    real, stable, monotonic signal borrowed from `annual_revenue` via the three derived-column
    lines. `requested_amount = annual_revenue * uniform(0.05, 0.50)`, rank-corr 0.85.
- **A weight is not an effect size.** `profit_margin` carries the largest coefficient (−1.50) and
  0.3% of the logit's variance, because it is one of two unstandardised terms and its spread is
  ~0.06. Rank by variance share, not by coefficient.
- **Noise enters twice.** `normal(0, 0.5)` inside the logit (unobserved heterogeneity, 9.5% of
  variance, std recovered at 0.499 against signal std 1.545) *and* the Bernoulli draw on
  `pd_true`. Different jobs; both cap AUC.
- **The intercept is not the base rate.** `sigmoid(-2.2) = 0.0998`; mean PD is 0.1696.

**The ceiling, and the trap in comparing to it:**

| | measured over | AUC |
|---|---|---|
| noise-free signal | all 12,000 | **0.8177** |
| true PD (incl. noise) | all 12,000 | 0.8311 |
| noise-free signal | the scorecard's held-out 20% | **0.8353** |
| committed scorecard | the same held-out 20% | 0.8176 |
| the gate in `score/src/train.py` | | 0.7800 |

Compare only within a row's sample. Comparing the population ceiling (0.8177) to the scorecard's
held-out 0.8176 makes it look 0.0001 from perfect; that is two different samples. On its **own**
split the gap is 0.018, against a bootstrapped 95% interval of ±0.02 on 2,400 rows — so the
honest claim is *indistinguishable from the maximum*, and a third decimal place anywhere in this
repo is decoration.

## Conventions

- Commit messages: what changed and *why*, plus what was verified. Co-author trailer.
- **Do not push or tag without being asked.** The repo is public.
- Student-facing wording matters more than usual here: these people are choosing whether to
  trust the material.

## Where things stand — updated 2026-09-06

Released **v1.3** (annotated tag on `main`, pushed). Pilot cohort starts **Thu 10 Sep 2026,
8:00–9:30pm EDT**; Session 1 ends at `stage-1`.

Session 1 material as it now stands:

- `notebooks/01_stage1_portfolio.ipynb` — 40 cells. Portfolio profile, the applicant→booked
  funnel (16.7% / 10.9% / 29.9%), IV + monotonicity scan over all 20 candidates, the two
  no-causal-role cases above, a computed checkpoint card, and homework that feeds Lab 2 Part A
  (hand-bin + WoE, five-in/five-out, a sealed AUC prediction against the 0.78 gate).
- `workshop/reading/S1-data-generation.pdf` — 10pp, optional and unassessed, the DGP in full.
- `workshop/facilitator/S1-run-of-show.md` — the room moves `main` → `stage-0` (0:13) →
  `stage-1` (1:05) and **ends the night on `stage-1`**, which is why the homework pointer is
  `git checkout main -- notebooks`.

Open threads, none started:

- A *"how these ten were chosen"* subsection for the reading note, between §3 and §4. It explains
  *what* is in the logit but never *why those nine*: the sentence test, unarguable signs, routing
  levels through ratios, excluding what a bank must not price on, designing the decoys
  deliberately, and setting weights by target variance share.
- Nothing equivalent to the S1 reading note exists for Sessions 2–5.

Housekeeping: a local `backup/pre-pii-rewrite` branch holds the pre-rewrite `cohort.py` history
and was never pushed — delete it when it is no longer wanted.
