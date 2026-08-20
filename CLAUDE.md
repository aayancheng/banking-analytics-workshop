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

## Conventions

- Commit messages: what changed and *why*, plus what was verified. Co-author trailer.
- **Do not push or tag without being asked.** The repo is public.
- Student-facing wording matters more than usual here: these people are choosing whether to
  trust the material.
