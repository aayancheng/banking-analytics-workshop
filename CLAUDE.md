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
workshop/slides/render_html.py  `make slides` -> browsable S*.html, stdlib only, flags overflow
workshop/facilitator/  run-of-show + the live timer app, polls, cohort.py, email templates
workshop/facilitator/recut/  session-recording recut pipeline (align/snap/build + HyperFrames graphics)
workshop/LectureSummaryandRecordings/  GITIGNORED: recordings, Zoom transcripts, recut outputs, blog drafts
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
- **`workshop/` and `notebooks/` both live on `main` and are in NO tag** — not stage-1, not even
  stage-5. A stage jump therefore deletes the lab sheet, the prompt cards and `CHECKPOINTS.md`
  along with the notebooks. The S1 handoff at 1:05 is `git checkout stage-1` **followed by**
  `git checkout main -- workshop notebooks`. ⚠️ Never restore before the `stage-0` "eight files"
  beat at 0:13: restored files are staged and survive a later checkout, so `git ls-files` then
  reports 80 instead of 8 (verified in a clean clone at the tag). Same reasoning below.
- **`notebooks/` lives on `main` and is in no tag** — on purpose: one copy that stays current
  beats five frozen ones. A stage jump deletes it. The command to give a student is
  `git checkout main -- workshop notebooks`, which needs nothing but git. **Not `make notebooks`** — that
  target exists only on `main`, because a tag ships the Makefile it had at the time and tags
  never move. Same trap applies to any future `make` target you are tempted to put in
  stage-jump advice.
- **Notebook 01 must run at `stage-1`, where `score/` does not exist.** It imports
  `FEATURE_COLUMNS` from `score.src.feature_engineering` inside a `try`, with a hard-coded
  fallback. Anything else it reaches for from a later stage needs the same treatment.
- **The leakage probe's headline number was wrong for a month.** Every artifact said "watch AUC
  hit ~1.0" while the shipped code leaked `pd_default_origination` — the generator's *true PD*,
  not the label — which measures **0.8326**. Only leaking `default` reaches 1.0000. It is now a
  three-rung ladder (**0.7299 / 0.8326 / 1.0000**) and the teaching point is the *middle* rung:
  +0.10 AUC, plausible-looking, passes review, ships, then performs at 0.73 because at decision
  time the true PD does not exist. If you change one artifact's numbers, change all five —
  notebook cell 35, `S1-lab.md`, `S1.md` (twice), `S1-run-of-show.md`, `run-of-show-app.html`.
- **`localStorage` throws, it does not return null.** Chrome disables it on `data:` URLs and
  restricts some `file://` contexts. An unguarded `save()` in `run-of-show-app.html` killed a
  change handler silently, and once it was also called from `render()` it would have killed the
  render loop every second. Wrap every access; treat persistence as a convenience, never a
  dependency. Same rule for any future local HTML tool here.
- **The gate passes on a population the bank never lends to.** The scorecard trains and gates on all
  12,000 applicants; on the 8,336 *booked* it scores held-out AUC **0.7447** (rejected-only 0.8440,
  everyone 0.8176). Not a defect — the DGP gives every applicant an outcome — but it is S2's set-piece
  reveal (notebook 02 §7) and the memo's fourth clause. Any "AUC" quoted without its population is
  incomplete. Dropping the four bureau columns gives **0.7643** — the rehearsed live gate-fail.
- **`requested_amount` crashes optbinning's default CP solver** (`TypeError: __radd__` inside
  `optbinning/binning/cp.py`) on the training rows with the pinned `ortools==9.14.6206`; row
  subsets (booked-only) can trip it on other variables too. `solver="mip"` binds every safe column
  identically (net_income gets 8 bins instead of 7). The committed 15 `FEATURE_COLUMNS` are fine
  under CP on the full training split, so `train.py` is unaffected — but any cell that lets a
  student pick raw columns must pass `binning_fit_params={c: {"solver": "mip"}}` (notebook 02
  does). Five raw columns (`dscr, utilization, prior_delinquencies, leverage, years_in_business`)
  score **0.7804** held out; the five structural zeros score 0.50; the five `annual_revenue`
  proxies 0.62.
- **Reading notes render with headless Chrome** (`make reading`) — no npm, LaTeX or pandoc. The
  `.html` is source and the `.pdf` is committed beside it so students need no toolchain.
- **Recutting a recording** (`workshop/facilitator/recut/README.md` is the runbook; S1 is the
  worked example). The things that cost time once: **HyperFrames renders the graphics only**
  (one Chrome screenshot per frame — never the footage; ffmpeg cuts and composites). **This
  ffmpeg has no `drawtext`** — all text is a HyperFrames render. **Zoom's transcript is
  wall-clock and the recording starts later** (S1: 13 min later) — `align.py offset` finds the
  offset by matching transcript gaps to audio pauses; never author a cut from raw cue times.
  **Every cut and every chapter point must sit on a pause**, and a boundary next to an attendee's
  spoken first name gets moved by hand (`align.py window`). **Chapter breaks are freezes**, so a
  mid-sentence chapter point is worse than none. **HyperFrames root-level clips are pinned to
  top-left** — wrap anything positioned elsewhere. **`npx hyperframes lint` on a missing path
  reports 0 findings.** The recordings folder is gitignored because the transcript names people;
  the cut lists' `note` fields must not.

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

## Where things stand — updated 2026-09-19

**v1.4** is the public release. **Session 1 ran Thu 10 Sep** (recording recut to 58:53 and a
3:04 LinkedIn promo — see *Session recordings* below). **Session 2 ran Thu 17 Sep** at the
90-minute re-cut; **its recording is recut** (2026-09-18) into six standalone chapter videos plus
a 53:04 stitched version, and a **55 s promo** (2026-09-20: the six hooks over a music bed, no
footage) — the S2 post is next. YouTube channel **TeamYan, @teamyan2026**; chapter 1 is up.
Sessions 3–5 are Thursdays 8pm EDT.
Local `main` may be ahead of `origin/main` — check `git status -sb`; nothing is pushed without
being asked.

### Session recordings — S1 and S2 done, S3 next

`workshop/facilitator/recut/` (tracked) turns a Zoom recording + transcript into the student
video(s) and the promo; `workshop/LectureSummaryandRecordings/` (gitignored) holds the inputs and
outputs. **The README there is the step-by-step** — S2 is the worked example: a master
`S2.cuts.json` (keeps carry `chapter` + `mark`, chapters carry `hook`), `split.py` derives one
cuts file per chapter, each chapter video = a 6–7 s HyperFrames hook → footage → outro; the
master builds the stitched version with freezes. S2's six theses: WoE+logistic vs the flexible
challengers (0.8176 vs 0.8096) · DSCR by hand 3→6 bins then optimizer 8 (one feature 0.64) ·
coin→one→fifteen and the 0.78 gate · the live drop of four bureau columns → **0.7704**, gate
fails · everyone 0.8176 / booked 0.7447 / rejected 0.8440 · reason codes = WoE × β. Outputs
`out/S2-ch{1..6}-compact.mp4` (4:55–11:33) and `out/S2-compact.mp4`, with `*-chapters.txt`
YouTube blocks. Cut everywhere: all polls, the agent-track lab (the agent did not drop the
features), the public-records Q&A, the client hunt; two spoken first names trimmed on pauses.
**The deck's 0.7643 for that drop is stale — the screen and `main` say 0.7704** (separate fix).

What S1 settled, so S2 does not re-decide it: cut the polls entirely, cut time checks and
cohort logistics and plugs, cut a hiccup *and* its later apology; where a hiccup contradicted
the curriculum (S1's failed stage checkout ended in "don't do stages"), a **correction card**
at that moment quoting the lab's own command; chapter breaks are a 2.6 s freeze with the banner
rising to mid-left; watermark bottom-right; chapter marks embedded in the MP4 *and* written as
a YouTube description block (YouTube ignores embedded chapters); the promo is the strongest
~20 s of each chapter, not its first 20 s, entered through the chapter freeze. Both S1 videos
were checked by frame pairs at every seam and by audio cross-correlation (constant −26 ms,
no drift) — **not by ear**: a words-at-the-seam check needs `whisper-cpp` and a ~150 MB model,
which was not installed without asking.

S1's Substack post (four milestone screenshots), LinkedIn copy, and the S2 T−1 reminder are in
`workshop/LectureSummaryandRecordings/blog/` and `workshop/facilitator/emails/`. The S1 post's
shape — thesis, the "right question" reframe, four milestones, the leakage ladder as the core
insight, a governance section, homework — is the template for the S2 post.

### The cohort (no names or addresses here — this repo is public)

**109 distinct sign-ups; live seats closed 2026-09-05.** 58 on the live list, 51 on the
recording track. Expect **35–45 in the room**. Zoom Pro (100-participant cap) is being bought
2026-09-09 — one month covers all five sessions if bought that day; auto-renew off immediately.

`workshop/facilitator/cohort.py` turns a Tally export into a Bcc list. Buckets are
`--live / --recording / --later / --unknown`, they union, and **sign-ups on or after
`LIVE_CLOSED_FROM` (2026-09-05) are recording-only whatever they ticked** — the form kept
accepting "yes live" after the seats were gone. Columns resolve **by header name**, because
Tally reordered them mid-flight. Exports and `email_fixes.json` are gitignored; never inline an
address (invariant 6).

### Facilitator tooling added since v1.3

- **`workshop/facilitator/run-of-show-app.html`** — open in a browser on a second screen. Counts
  the 90 minutes, fires every timed cue (polls, the stage-1 handoff command with a copy button,
  the two-minute demo warning), and shows drift if you click the block you are actually on.
  Marks *How a bank decides* RECOVERABLE and the lab PROTECT. **It mirrors the run-of-show table
  — change one, change the other.**
- **`workshop/facilitator/session-polls.md`** — three anonymous Zoom polls: A at 0:04 in the
  container-build gap, B at 0:14, C at 1:29 (a pulse whose results are **not** shared on screen).
- **`workshop/facilitator/course-from-recordings.md`** — Zoom recording settings that must be on
  *before* the session (record shared screen **separately**, participant names **off**, consent
  prompt **on**), the Udemy bar, and the platform comparison. **Decision: buy no course platform
  yet**; Substack + the public repo + YouTube is the stack while the goal is list growth.
- **`make slides`** → `render_html.py`, stdlib-only deck preview that **flags any slide
  overflowing the 16:9 frame**. The rendered `S*.html` **are committed** beside their `.md`
  (since 2026-09-09: a Codespace has no `open` and no `file://`, so an uncommitted deck meant a
  render plus a forwarded port before you could read a slide). Re-run `make slides` when you
  edit an `.md`; in a Codespace, `python -m http.server 5180 --directory workshop/slides`.
- **`make run` now depends on `stop`** — a leftover uvicorn on 8100 killed the dry run.

### Open threads, none started

- A *"how these ten were chosen"* subsection for the reading note, between §3 and §4: the
  sentence test, unarguable signs, routing levels through ratios, excluding what a bank must not
  price on, designing the decoys deliberately, weights by target variance share.
- Nothing equivalent to the S1 reading note exists for Sessions 2–5.
- **S2 post** — the recut and the promo are done (above); the post follows the S1 post's shape
  with the six chapter videos embedded (playlist links, not bare video links). Titles,
  descriptions and the promo/LinkedIn copy are in `blog/S2-youtube-descriptions.md`.
  `run-of-show-app.html` still mirrors S1 (S2 used a phone timer).
- **Notebooks 01 and 02 carry executed outputs in the working tree** (local paths baked in) from
  running them in VS Code — clear outputs before committing anything in `notebooks/`.
- **S2's run of show assumed students arrive on `stage-1`**; after S1's failed handoff the room
  stayed on `main` ("Stage 5 verified"). The S2 T−1 reminder says that state is correct and the
  move to `stage-2` is a group step at the lab (`git stash -u && git checkout stage-2`). Carry
  that assumption into S3–S5 material: students are wherever the last group step left them.
- **S2 re-cut to 90 minutes on 2026-09-14** — `workshop/facilitator/S2-run-of-show.md` + `S2-polls.md`,
  deck retimed, lab cut to 28 min guided and driven from notebook 02 §6 (`VAR`/`EDGES`). Not done:
  `run-of-show-app.html` still mirrors S1 — use a phone timer for S2.
- The dry run ran **22% long** (9m48s against 8m). Applied to 90 minutes that is ~110. The
  recoverable block is named in the run of show; the lab is not it.

Housekeeping: local-only branches `backup/pre-pii-rewrite` and `archive/yanexercise` (the
deleted remote branch, SHA `bcb055b`) — delete when no longer wanted.

## v2 loan workbench (added 2026-09-23, task 16 of the v2-loan-workbench plan)

`app/v2/` adds a loan-level "Loan Workbench" at `/v2`, running side by side with the
existing v1 portfolio portal at `/`. `make run` serves both on port 8100 — no second
server, no second target. v2 never re-implements a module: every number on screen
comes from calling the existing module functions (`price_loan`, `policy.decide`,
`flag_triggers`, `risk_tier`, `recommended_amount`, `incremental_roe`,
`feature_contributions`) the same way the batch pipeline does. `app/main.py` carries
the whole integration in four statements (import, one lifespan line, `include_router`,
the `/static/v2` mount) — invariant 5 (one service per module) applies to v2 exactly
as it does to v1.

- **`app/v2/` is main-only, like `notebooks/` and `workshop/`.** No stage tag
  contains it, and tags never move. `verify.py`'s v2 smoke (inside `check_apps`) is
  guarded on `(ROOT / "app" / "v2").exists()`, so it is silent at every stage tag and
  only runs where `app/v2` exists. Verified in a clean clone: `stage-0`..`stage-5`
  untouched all report exactly as they did before v2 existed, and running `verify.py`
  where `app/v2` is present (`main`, merged 2026-09-23) exercises the v2 smoke, which asserts a what-if with an empty override body
  agrees with the batch `/api/adjudicate` decision.
- **The stage-3 handoff is unsafe — do not give it, and the reason is not v2's
  imports.** `main`'s `app/main.py` is the stage-4+ version of v1: line 26 already
  reads `from ews.src import watchlist as ews_watchlist`, at module import time,
  *before* the v2 import on line 28 is ever reached. Stage-3's own `app/main.py` has
  no such line (`git show stage-3:app/main.py` — it imports only score, adjudication
  and pricing; no `ews` reference at all). So **restoring `main`'s `app/` into
  stage-3 was never safe, with or without v2** — `app/v2/state.py` (which separately
  imports `ews.src.feature_engineering` and `line_increase`) never even gets a
  chance to fail, because `app/main.py`'s own pre-existing v1 import fails two lines
  earlier. Do not "fix" this by making v2's imports lazy — that cannot repair a
  v1-only failure that happens before v2 is reached.

  DO NOT RUN the block below as advice — it is kept only as the clean-clone proof of
  the failure, on a fresh venv:
  ```
  git checkout -f stage-3
  git checkout main -- app notebooks workshop
  python verify.py
  ```
  fails at the apps check with exactly:
  `cannot import name 'watchlist' from 'ews.src' (unknown location)`

  **The safe handoff is stage-4 or later — give this, literally, as a
  ready-to-run command:**
  ```
  git checkout stage-4
  git checkout main -- app notebooks workshop
  ```
  Verified 2026-09-23 on the merged `main`, in a clean clone with a fresh venv, at
  stage-4 and at stage-5: `verify.py` passes
  (`✅ Stage 4/5 verified`), the server then boots cleanly — no `V2State`
  alignment-assert failure, which is real evidence, since those asserts fire at boot
  if a tag's committed artifacts differ from `main`'s — `/api/v2/health` answers, and
  every tab's endpoint (`/api/v2/loan/BIZ100002{,/decision,/pricing,/ews,
  /line-increase}`), `/` (v1) and `/v2` return 200.
- **v2's what-if must equal the batch pipeline — for the bodies the UI SENDS,
  not only `{}`.** Every slider calls the same module function the batch run calls.
  After the first interaction the browser always posts explicit values (the EWS tab
  sends both cutoffs and all five trigger thresholds on every drag), and that path
  hid the final review's Critical: explicit committed cutoffs re-tiered the book from
  the 4dp-rounded prob (BIZ108170 Medium -> High). `tests/test_app_v2.py` pins the
  empty body against `/api/adjudicate`, `/api/pricing/<id>` and `/api/ews/<id>`;
  `tests/test_app_v2_ui_bodies.py` pins the explicit committed bodies — every one of
  the 8,336 EWS tiers, `flipped_count == 0` over 12,000 decisions, the full pricing
  payload. `verify.py`'s v2 smoke re-asserts the adjudication case on every run. If
  any fails, the demo is lying — fix the drift, never the test or the smoke check.
  Never re-derive a verdict from a rounded persisted column (`prob`, `pd`): v2 caches
  the unrounded values (`V2State.ews_prob_raw`, `li_prob_raw`) with alignment asserts.
- **Every number printed beside a threshold carries a server-chosen `dp`**
  (`app/v2/display.py`); `tests/test_app_v2_display.py` formats as the browser does
  and demands distinct strings over the whole book.
- **The JS display layer has no automated regression coverage, by design** — there
  is no JS test runner (no new dependency). The rendered-string checks behind each
  UI fix were one-off browser scripts; re-run them by hand in a browser after any
  change to `app/static/v2/`.
- **No financial arithmetic in the v2 JavaScript.** Every number on screen came from
  a server response; the browser only formats and draws. A threshold comparison done
  in JS is a bug even on the loans where it currently agrees with the server.

Sessions 3 and 4 are merging into one new Session 3 (adjudication + pricing + early
warning, line increase optional); v2 is the demo artifact for it. Curriculum work that
follows from v2 — stubbing the EWS tab as the S3 lab exercise, preserving the prompt
that produced v2 in `workshop/prompt-cards/`, and updating every printed stage-jump
command to the stage-4-or-later form above — is deferred to that session rewrite, not
this build.
