# S2 — Run of Show (90 minutes)

**Facilitator notes. Not student-facing.**

Session 2 of 5 · **Thursday, September 17, 2026 · 8:00–9:30 pm EDT** (Toronto)
Format: online · **free pilot** · checkpoint: `stage-2`

> **This is the 90-minute cut.** The `S2.md` deck and `S2-lab.md` were authored for a ~160-minute
> in-room session with a break and 75 minutes of lab. What moved is recorded in *What changed
> from the 160-minute design* at the bottom — read that before you rehearse, because the lab is
> now 28 minutes, guided, and the two live demos that replaced it are the point of the evening.

---

## Pre-flight (T–30 min)

- [ ] Instructor Codespace on **`stage-2`** with `score/` **clean** (`git status` shows nothing
      under `score/`) — the gate demo at 0:32 edits two files there and restores them with
      `git checkout -- score/`. A dirty `score/` before you start means you cannot restore.
- [ ] `python verify.py` run **twice** in that window (cold imports are slow); leave it showing
      `✅ Stage 2 verified` with `[4/4]` — that is the "before" state the room will see.
- [ ] Second window on **`main`** with `notebooks/02_stage2_score_spine.ipynb` **already
      executed** end to end. You drive §6 live at 0:50; §7's table is the 0:44 reveal. Scroll it
      to §6 before you share.
- [ ] Slides rendered: `make slides` → `workshop/slides/S2.html`. It flags any slide that
      overflows the 16:9 frame. Fifteen slides; no slide should be flagged.
- [ ] `workshop/labs/S2-lab.md` and `workshop/prompt-cards/AC-2.md` open in tabs.
- [ ] **Tell the room to read the lab sheet from GitHub in a browser**, not from their
      checkout. They arrive on `stage-1` (where `workshop/` exists only if they restored it)
      and jump to `stage-2` at 0:50 — the jump deletes it again until they restore.
- [ ] **Four polls created in the Zoom web portal, anonymous** — see
      [S2-polls.md](S2-polls.md). A and C are load-bearing. Find the launch button before 8:00pm.
- [ ] Session 1's Poll C report downloaded and read — if "got stuck on setup" was high, open with
      the recovery line and slow the 0:50 handoff.
- [ ] Screen-share tested; terminal font scaled up.

**Pre-work email (send ~3 days ahead).** Remind them of the three Session 1 homework items that
S2 opens on: *bring your WoE table* (item 2), *seal your AUC* (item 4 — Poll A collects it), and
the five-liner (item 5). Ask them to open the Codespace before the session and confirm
`python verify.py` is green at `stage-1`. **Red at the start = join from Codespaces.**

---

## Run of show

> No live timer app for this session — the `run-of-show-app.html` on the second screen mirrors
> Session 1's table and has not been re-cut. Use a phone timer set to the block boundaries
> below. The RECOVERABLE block is *Reason codes* (1:18); the PROTECT blocks are the two live
> demos (0:32–0:50) and Part B of the lab.

| Time | Block | Beats to hit |
|---|---|---|
| **0:00–0:06** | Re-verify + homework in · **Poll A** (0:04) | `python verify.py` on their screens while Poll A runs — the AUC they sealed, in buckets. Share it; **do not reveal 0.8176 yet.** Hands up for a WoE table — that is who you cold-call in the lab. The notebook's *"Session 1 homework, worked"* section has both answers (utilization WoE, IV 0.1756; a five-in card at **0.7804**, the five decoys at 0.50) — show it in the lab, not here; the five-in bar sits just above the gate and it spoils 0:32 if it goes up now. Two five-liners on *which app would you trust least*, 60s each; note them for S5 panels. |
| **0:06–0:18** | Why a scorecard | Adverse action · SR 11-7 · stability. The alternatives table: **0.8176 vs LightGBM's 0.8096**, and the boosted model had *more* inputs. Land: *flexibility only pays when the relationship needs it; this one doesn't.* |
| **0:18–0:32** | Bin → WoE → points, on one variable · **Poll B** (0:20) | WoE definition, then the arc: six hand bins on DSCR (IV 0.209) → the fitted model (β₀ = the book log-odds, β₁ ≈ −1) → two applicants scored (33.0% / 435 vs 4.7% / 601) → one variable vs fifteen (0.6383 vs 0.8176). Read Poll B back against the 6-vs-8-bin IV. **Rank features by IV, never by coefficient** — say it once, they will hear it again from a validator. |
| **0:32–0:40** | **LIVE — the gate you cannot negotiate** · PROTECT | Your window, `stage-2`. Drop the four bureau columns → `make train-score` fails at **0.7643**. Set `AUC_GATE = 0.75` → `GATE PASS`. `python verify.py` → **FAIL, 0.7643 below the committed 0.78.** Restore, verify green. **Then reveal Poll A** — the room's sealed numbers against 0.8176 and 0.7643. Minute-by-minute below. |
| **0:40–0:50** | **LIVE — the population you evaluated on** · **Poll C** (0:42) · PROTECT | Session 1's funnel: 12,000 → 8,336 booked. *A bank never sees an outcome on a loan it declined.* Launch Poll C from that slide. Share. Advance: **0.8176 on everyone, 0.7447 on booked-only — below the gate.** Count to ten. Two questions, in order; resolve neither. This is the emotional peak of the night. |
| **0:50–1:18** | **Guided lab, 28 min** — Part B is PROTECT | **0:50 handoff first** (below). Part A 12 min: you drive §6 for four minutes with `VAR="utilization"`, then they change `VAR` themselves. **1:02 call time on A regardless.** Part B 10 min: apply their drop, `make train-score`, `verify.py`. Part C only if the room is ahead. Anyone red at 1:15: `git checkout stage-2 -- score/models`. |
| **1:18–1:26** | Reason codes · defend round · RECOVERABLE | `WoE × coefficient` is the adverse-action letter, exactly. Three students, one question each: *why is your top variable in, and what would make you remove it?* Pick people whose Part-A drops differed. If behind, cut the defend round to one student. |
| **1:26–1:30** | Checkpoint · homework · **Poll D** (1:29) | **1:26** `python verify.py` sweep — nobody leaves un-green. **1:28** homework: finish the notebook (§7 is the booked-only table) and the memo, which now has a fourth clause: *which population my gate is measured on.* **1:29** Poll D; do **not** share its results. |

---

## The gate demo (0:32–0:40) — minute by minute

Rehearsed in a clean clone at `stage-2`; every string below is real output. Do it in **your**
window, at `stage-2`, with `score/` clean.

**0:32 · The scenario.** *"The bureau feed is down for this segment. We don't have utilization,
credit history, delinquencies or public records. Ship without them?"* Open
`score/src/feature_engineering.py`, delete those four names from `FEATURE_COLUMNS`.

**0:33 · Train.**
```bash
make train-score
```
```
AUC=0.7643 KS=0.4185 | scaling lo=341.48 hi=706.25
...
AssertionError: GATE FAIL: AUC 0.7643 < 0.78
```
*"Sixteen thousandths short. Every one of you has been in the meeting where someone says: it's
basically there."*

**0:34 · The tempting fix.** Open `score/src/train.py`, change `AUC_GATE = 0.78` to `0.75`.
Say what you are doing as you do it. Run it again:
```
AUC=0.7643 KS=0.4185 | scaling lo=341.48 hi=706.25
GATE PASS
```
Pause. *"Green. Ship it?"* Let someone object. If nobody does, that is its own lesson — say so.

**0:36 · The auditor.**
```bash
python verify.py
```
```
[4/4] Model: scorecard + AUC gate ............ FAIL
      ❌ held-out AUC 0.7643 is below the committed gate 0.78
      Fix: The gate does not move — the model does. ...
❌ Stage 2 not verified yet
```
*"`verify.py` has its own copy of 0.78, and it recomputes the AUC from the saved model. Nothing
you edit in `train.py` reaches it. That is what a gate is: a number that lives somewhere you
can't edit on the way to a deadline."*

**0:37 · Restore, and prove it.**
```bash
git checkout -- score/
python verify.py            # ✅ Stage 2 verified
```
Do not skip this — the room needs to see that the clean state is one command away, because
they will be doing it themselves in Part C.

**0:38 · Reveal Poll A.** Put the poll results back up next to two numbers: **0.8176** (the full
card) and **0.7643** (without bureau). *"Whoever sealed 0.70–0.75: that's what this segment
scores if the bureau is down. You weren't wrong, you were modelling a different bank."*

**If it goes wrong:** the only realistic failure is a dirty `score/` before you start, which
makes `git checkout -- score/` restore *your* uncommitted state instead of the tag's. Check
`git status` at T–30. If `make train-score` itself errors, `git checkout stage-2 -- score/`
and move to 0:40 — the lab's Part C covers the same ground.

---

## The booked reveal (0:40–0:50)

Two slides, one poll, one table. The mechanics are simple; the discipline is **not explaining
it before they have guessed.**

**0:40 · Set it up.** The slide has the funnel — 12,000, 8,336, 69.5% — and the sentence *a
real bank never sees a default outcome for a loan it did not make.* Say it twice. Then: *"the
gate you just watched — 0.8176 — is measured on all 12,000. Including the 3,664 the bank
declined."*

**0:42 · Poll C.** 45 seconds. Share it. Do not comment on the split.

**0:44 · The table.** Same model, same 2,400 held-out rows, split by `booked`:

| | n | default | AUC |
|---|---|---|---|
| everyone | 2,400 | 16.7% | 0.8176 |
| **booked only** | 1,644 | 11.1% | **0.7447** |
| rejected only | 756 | 28.8% | 0.8440 |

Read the middle row. Then: *"below the gate, on the only population the bank will ever lend
to."* **Count to ten.**

**0:46 · Why.** The declined applicants are the easy ones — the credit policy already sorted
them. Any model that sees their outcomes gets rank-ordering credit for calls the policy made.
In production, on the booked book, that credit is gone. *"Session 1's leakage lesson, different
coat: an honest number, computed correctly, on the wrong population."*

**0:47 · Two questions, in order. Resolve neither.**
1. *Which population is your gate measured on?* (Most rooms have never asked.)
2. *Real banks call the fix reject inference — you invent outcomes for loans you never made.
   Why is that contested?* Homework. The good arguments come back next week.

**0:49 · Bridge.** *"§7 of the notebook builds that table in ten lines. You'll run it in the lab.
First, everyone to stage-2."*

**A note on the numbers.** They are recomputed, not stored — `predict_score_pd` on the held-out
rows, split by `businesses["booked"]`. The synthetic DGP assigns an outcome to every applicant,
which is how we *can* measure the rejected population; that is a property of the teaching data,
not a defect, and it is worth one sentence if someone asks.

---

## Stage-2 handoff (0:50) — one line, everyone, before Part A

The room arrives on `stage-1`. `stage-2` adds the trained scorecard the notebook needs and the
lab retrains. The jump also deletes `workshop/` and `notebooks/` (they live only on `main`),
so the restore is part of the same line:

```bash
git stash -u && git checkout stage-2 && git checkout main -- workshop notebooks
python verify.py            # [4/4] Model: scorecard + AUC gate ... OK
```

- `git stash -u` first, because anyone who ran notebook 01 for homework has a modified file
  that would block the checkout. Nothing is lost; nothing needs to be popped tonight.
- Have the line on the slide **and** in chat. Give it ninety seconds. Ask for green hands.
- Anyone still red at 0:53 joins from a fresh Codespace and runs the same line there.

---

## The lab, guided (0:50–1:18)

This is Session 1's *guided lab* pattern, not the independent 75-minute lab the sheet used to
describe. You drive; they follow; the sheet is the reference, not the script.

**0:52–0:56 · You drive §6.** Share the notebook window. On the way down, thirty seconds on
*"Session 1 homework, worked"* at the top: the utilization table they were asked to bring, and
the five-in / five-out cell — five decent columns clear the gate by 0.0004, five decoys are a
coin flip. Tell them to put their sealed number in `SEALED` and run it themselves at home. Set `VAR = "utilization"` and the
suggested `EDGES`, run the three cells, and narrate the WoE column *running the other way*.
Ask: *should it?* Then the IV scan — point at the bottom of the chart. That is decision 2.

**0:56–1:02 · They drive.** *"Your turn — change `VAR`, change `EDGES`, break it."* Cold-call
whoever raised a hand for a WoE table at 0:05. Walk the chat, not the room.

**1:02 · Call time on Part A** whether or not they are done. Part B is the part that must happen.

**1:02–1:12 · Part B.** *"Apply your drop. One feature, `FEATURE_COLUMNS`, nothing else. Then
`make train-score`, then `verify.py`."* Most drops clear the gate; a few will not — those are
the best conversations in the room, and the sheet's *If your gate FAILS* protocol handles them.
The agent track briefs AC-2 with the same three decisions.

**1:12–1:17 · Part C if ahead, otherwise converge.** Part C is the gate demo done by their own
hands; it is optional because they watched it at 0:32. **1:15: anyone red restores** with
`git checkout stage-2 -- score/models` and keeps their notes.

**Failure modes.** Someone edits `verify.py` itself: that is tampering with the auditor — best
discussion of the night if it happens, take it. Someone's `make train-score` takes over a
minute: cold `optbinning` import, wait. Someone's notebook stage guard fires: they skipped the
0:50 handoff; run the line.

---

## Homework to assign (30–45 min)

1. **Finish the notebook.** §7 is the booked-only table. Three lines: *which population is
   your gate measured on, and what would you do about it?*
2. **Decision memo, 1 page, due S3:** *My scorecard: what's in it, what I excluded and why,
   which population my gate is measured on, and the one question I'd fear from a validator.*
   The fourth clause is new tonight. Every memo feeds the S5 doc pack.
3. Part C of the lab, if they did not reach it.

---

## Rehearse these three specifically

1. **The gate demo, twice, with a stopwatch.** Eight minutes including the restore and the
   Poll A reveal. The edit-run-edit-run-verify rhythm is what carries it; fumbling a file path
   kills it.
2. **The ten-second silence at 0:44.** It is longer than it feels. Count.
3. **The 0:50 handoff line, read aloud.** Once, slowly, then pasted in chat.

## Have answers ready

- *"Why does the rejected population score higher (0.8440)?"* — Because it is the easy end of
  the distribution: high-PD, low-DSCR, and the model's ranking there is nearly free. Range
  restriction cuts the other way on the booked book.
- *"So is 0.78 the wrong gate?"* — The gate is fine; the *population* is the question. A gate
  measured on the booked book would be a different number, and choosing which book to measure
  on is a modelling decision that belongs in the memo.
- *"Why did the boosted model lose?"* — The DGP is close to linear in its drivers and every
  model is capped by the same noise (Session 1's ceiling table). Flexibility bought nothing.
- *"Can I use optbinning's IV instead of the notebook's quick IV?"* — Yes, and it will differ
  slightly; the ranking is what matters. The scan is for choosing, not for reporting.

---

## What changed from the 160-minute design

The original `S2.md` blocks ran `0:00–2:40` with a break at 1:30 and 75 minutes of lab
(Lab 2a 45 min, Lab 2b 30 min). For 90 minutes online, with a room that is not hands-on:

- **Lab 2a + 2b → one guided 28-minute lab, notebook-driven.** Part A no longer asks anyone
  to write WoE from scratch in a blank Python session; notebook §6 is parameterised on `VAR`
  and `EDGES` and the exercise is *change two lines, re-run, decide*. Part B is unchanged in
  substance and ten minutes long. The Session 1 homework (bring a WoE table) is assumed done.
- **Two live demos added, in the time the lab gave back.** The gate you cannot negotiate
  (0:32) was a lab bullet; it is now the instructor's set piece, rehearsed at the tag. The
  booked-population reveal (0:40) is new material: the committed model re-measured on
  booked-only loans, 0.8176 → 0.7447.
- **Four polls, none in the original.** A collects Session 1's sealed AUC (a promise the
  original deck never kept); B makes binning granularity a committed guess; C sets up the
  reveal; D is Session 1's exit pulse, verbatim, for the week-over-week delta.
- **Five teach slides added** in the 0:18–0:32 block: alternatives to WoE+logistic, the DSCR
  worked example, the fitted coefficients, two scored applicants, one variable vs fifteen.
- **The memo gained a fourth clause** — *which population my gate is measured on.*
- **Not done:** `run-of-show-app.html` still mirrors Session 1. Use a phone timer.
