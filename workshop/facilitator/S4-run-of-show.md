# S4 — Run of Show: Model documentation a validator accepts (90 minutes)

**Facilitator notes. Not student-facing.**

Session 4 of 4, the finale · **Thursday, October 1, 2026 · 8:00–9:30 pm EDT** (Toronto) ·
**Friday, October 2 · 8:00–9:30 am HKT** (Hong Kong)
Format: online · **free pilot** · checkpoint: **`main`** — no stage jump tonight

Primary materials:

- slides: [`workshop/slides/S4.html`](../slides/S4.html) (fifteen slides, `make slides`);
- lab sheet: [`workshop/labs/S4-lab.md`](../labs/S4-lab.md);
- prompt cards: [`HW-H4.1.md`](../prompt-cards/HW-H4.1.md) (the lab),
  [`HW-H4.2.md`](../prompt-cards/HW-H4.2.md) (the validator review);
- polls: [`S4-polls.md`](S4-polls.md);
- the wiki: `wiki/` — D4 is `wiki/mdd/score/`, D5's stub is `wiki/mdd/adjudication/`.

> **Where the room is.** On `main`, seeing "Stage 5 verified", as after S2 and S3. The
> reminder email asked for `git stash -u && git checkout main && git pull`, then *Codespaces: Rebuild Container*, then
> `python verify.py`. Some will have skipped the rebuild; that costs them the rendered preview
> and nothing else — the lint and `wiki.homework.check` are plain Python. Say so once, at 0:00,
> and do not troubleshoot a rebuild in the room.

---

## Pre-flight (T–30 min)

- [ ] **The wiki is on `origin/main`.** Tonight's pull is what brings `wiki/`, the
      prompt cards and the devcontainer change to the room. If it is not merged and pushed
      before the reminder goes out, nothing below works for them.
- [ ] Instructor Codespace on **`main`**, `git status` **clean** — the 0:12 demo edits
      `wiki/facts/facts.json` and restores it with `git checkout --`. A dirty tree before you
      start means the restore puts back *your* state, not the commit's.
- [ ] `python verify.py` run **twice** (cold imports are slow); leave it showing
      `[9/10] Docs: model wiki ...................... OK` and
      `✅ Stage 5 verified — you are here, and it works.`
- [ ] The site running for the tour: `make wiki` (Quarto preview) in a second terminal, the
      forwarded port open in a browser tab on **D4 at a glance** (`mdd/score/index.html`).
      Backup: `make wiki-site` beforehand and open `wiki/_site/index.html`.
- [ ] The validation PDF built: `make wiki-pdf`. Open it on the title page (it shows the
      version, date and artifact hashes) for ten seconds at 0:09.
- [ ] `docs/model_doc_pack/MODEL_DOCUMENTATION.md` open in a tab — it is the 0:02 slide's
      exhibit.
- [ ] Slides rendered: `make slides` → `workshop/slides/S4.html`. The page header reads
      **No slide overflows the 16:9 frame**. Fifteen slides.
- [ ] **H4.2 pre-run.** Run `HW-H4.2.md` through your agent once before the session and keep
      the answer (`wiki/homework/_answers/H4.2.md`, gitignored). At 1:08 you re-run it live;
      if the agent is slow, you show the pre-run. Rename the pre-run file first
      (`H4.2-prerun.md`) so the live run cannot read it.
- [ ] The part assignment ready to paste in chat (below, *0:38*).
- [ ] Both polls created, anonymous — see [S4-polls.md](S4-polls.md).
- [ ] Screen-share tested; terminal font scaled up; VS Code with `wiki/facts/facts.json`
      open, cursor on `"score.auc_holdout"`.

---

## Run of show

> No live timer app for this session — `run-of-show-app.html` still mirrors Session 1. Use a
> phone timer set to the block boundaries below. The RECOVERABLE block is the **D4
> walkthrough (0:20)**; the PROTECT block is the **lab (0:38)**, thirty minutes that do not
> shrink.

| Time | Block | Notes |
|---|---|---|
| **0:00–0:08** | Would this pass validation? Current pack vs SR 11-7 checklist · **Poll A** (0:00) | Slides 1–2. Paste `git stash -u && git checkout main && git pull && python verify.py` in chat; launch Poll A while it runs. Share it. Open the 147-line pack, scroll it once. The slide's three columns: present / thin / absent. Land: *correct numbers are not documentation.* Do not explain the **0.7447** (held-out booked) yet — it is finding 2. |
| **0:08–0:20** | Wiki tour: two tabs, one source, three outputs, the facts layer | Slides 3–5. Site in the browser (Course tab, then Model Documentation tab), the PDF's title page for ten seconds. **0:12 LIVE: change a fact, `verify.py` fails** — minute by minute below. Then the two spines, sixty seconds. |
| **0:20–0:38** | D4 walkthrough: the template, then the five open findings · **RECOVERABLE** | Slides 6–11. The nine-part template (D4's column), then one slide per finding, three minutes each. Every number is on the slide and in `wiki/mdd/score/limitations.qmd`. **If behind at 0:26:** show the template, finding 2 and finding 5 only, and say the other three are on the page. |
| **0:38–1:08** | **Lab H4.1** — pairs draft one D5 part each with an agent; `check H4.1` passes · **PROTECT, 30 min** | Slide 12. Paste the part assignment and the three commands in chat. **1:00** start your own H4.2 agent run (it is ready by 1:08). **1:05** call time: *"whatever your check says now, that is what we look at."* |
| **1:08–1:20** | Validator review live (H4.2); the room judges which findings are real | Slide 13. Your agent's findings, one at a time; the room votes **F / O / N** (finding, observation, noise) in chat. Then `limitations.qmd` side by side: which of the five did it miss? Two or three pairs report a claim they checked against the code. |
| **1:20–1:27** | Publishing and continuing self-paced · **Poll C** (1:20, not shown) | Slide 14. The site, the PDF, the homework page, the videos. No dates promised. |
| **1:27–1:30** | Close | Slide 15. `python verify.py` on screen, one last time, green. Thank the room — this is the last session. |

---

## Would this pass validation? (0:00–0:08)

**0:00 · Open.** Paste in chat:

```bash
git stash -u && git checkout main && git pull && python verify.py
```

The stash and checkout rescue anyone still on a stage tag from S3, where a bare `git pull`
fails. "Stage 5 verified" is the right answer.

Launch Poll A while it runs (45 s). *"If you didn't rebuild the container, you lose the
preview and nothing else."* Share Poll A and read it back (see [S4-polls.md](S4-polls.md)).

**0:02 · The pack.** Open `docs/model_doc_pack/MODEL_DOCUMENTATION.md` and scroll it top to
bottom — it is short, and that is the point. Every metric in it is read from a committed
artifact; none of it is wrong. Then the slide: for the scorecard alone, what a validator would find
**present** (data and leakage controls, performance, the gate), **thin** (purpose and use,
methodology, implementation) and **absent** (sensitivity, limitations, a monitoring plan,
dependencies, the risk tier).

*"Your validator starts from the right-hand column."*

**0:06 · The population.** The pack quotes a held-out AUC of **0.8176** (it means all held-out applicants). It does not
say so. Point at the **0.7447** (held-out booked applicants) at the bottom of the slide and leave it: *"we'll come back to that
number at 0:26 — it's a finding."*

---

## The wiki tour (0:08–0:20) — minute by minute

**0:08 · One source, three outputs.** The browser tab with the site. Click **Course**, then
**Model Documentation**: same pages, two orders. Show the validation PDF's title page — version,
date, the hash of every artifact it cites. *"The validator gets a PDF they can file. It is
rendered from the same pages you're looking at."*

**0:10 · Where the numbers come from.** Slide 4. In VS Code, open `wiki/mdd/score/index.qmd`
and point at a line with `{{< var score.auc_holdout >}}`. Then `wiki/facts/facts.json` at that
key:

```json
"score.auc_holdout": {
  "fmt": ".4f",
  "population": "held-out 20% of applicants (score split, seed 42)",
  "source": "score.src.predict.predict_score_pd",
  "text": "0.8176",
  "value": 0.817562
},
```

*"The page never types the number. The fact names where it came from and on whom it was
measured. And `verify.py` doesn't trust this file either."*

**0:12 · LIVE — change a fact.** Rehearsed on the `model-wiki` branch 2026-09-29; every string
below is real output. Safety copy first, then edit the text by hand:

```bash
cp wiki/facts/facts.json /tmp/f.json
```

In VS Code change `"text": "0.8176"` to `"text": "0.8276"` under `score.auc_holdout`. Save.
*"Someone's tidying the document before the committee. It's only the fourth decimal."*

```bash
python verify.py
```

```
[9/10] Docs: model wiki ...................... FAIL
      ❌ score.auc_holdout: facts.json says 0.8276, recomputed 0.8176 (+4 more)
      Fix: A number changed: make wiki-facts (make wiki-facts-full for the stress refits). A hand-typed number: replace it with {{< var key >}}. Full list: python -m wiki.tools.lint
[10/10] Apps: decision platform smoke ........ OK
❌ Stage 5 not verified yet — fix the line(s) above and rerun. Stuck for 5 minutes? Switch to Codespaces and keep moving.
```

Read the ❌ line aloud. *"It names the key, the number you typed and the number the model
actually produces."* The **+4 more** are the four generated files built from the facts
(`_generated/score-ceiling.md`, `_generated/score-stress.md`, `reference/facts.qmd` and
`_variables.yml`, which every page prints from) — each now disagrees with the edited
`facts.json`. If asked: that is the same edit caught four more times, not four more problems.

**0:14 · Restore, and prove it.**

```bash
git checkout -- wiki/facts/facts.json
python verify.py            # [9/10] Docs: model wiki ... OK · ✅ Stage 5 verified
```

Do not skip the second run: the room needs to see the clean state is one command away,
because their own lab ends with `verify.py`.

**0:15 · Optional, if on time — a hand-typed number.** Append a sentence to a D4 page and lint
just that page:

```bash
printf '\nThe held-out AUC is 0.8176.\n' >> wiki/mdd/score/performance.qmd
python -m wiki.tools.lint wiki/mdd/score/performance.qmd
```

```
mdd/score/performance.qmd:160: hand-typed number '0.8176' — use {{< var … >}}
wiki lint: 1 problem(s)
```

```bash
git checkout -- wiki/mdd/score/performance.qmd
```

*"The right number, typed by hand, is still a failure. It's right today."*

**0:16 · The two spines.** Slide 5, sixty seconds. A learner and a validator read the same
facts; nothing is written twice, so nothing drifts. The crosswalk maps each SR 11-7 element to
OSFI E-23 and PRA SS1/23 — it is a reading aid, not a compliance opinion; say so if asked.

**If it goes wrong:** the only realistic failure is a dirty tree before you start. `git status`
at T–30. If the restore leaves `facts.json` modified, `cp /tmp/f.json wiki/facts/facts.json`
and run `verify.py` again.

---

## The D4 walkthrough (0:20–0:38) · RECOVERABLE

**0:20 · The template (slide 6).** Nine parts, the same in every model chapter, so a validator
finds the same thing in the same place. Read D4's column down, fast. Stop on two rows:

- **Row 6, sensitivity.** The bureau feed is `utilization, credit_history_months,
  prior_delinquencies, trade_lines`. With all four removed and the card refitted, held-out AUC
  is **0.7704** on the held-out applicants — below the **0.78** gate. *"The document records a gate failure. It doesn't
  hide it; it says what the bank does when the feed is down."*
- **Row 7, limitations.** Five open findings, each with evidence, a compensating control and
  an owner. *"A validator trusts a document that raises its own findings."*

**0:24–0:38 · Five findings, one slide each** (all numbers from `facts.json`; the page is
`wiki/mdd/score/limitations.qmd`):

| Slide | Finding | The line to land |
|---|---|---|
| 7 · 0:24 | No out-of-time sample (PSI **0.0018**; **0** features over the **0.10** watch level) | *"A stable PSI between two random splits isn't good news. It's no news."* |
| 8 · 0:27 | The gate population is not the lending population (held-out AUC **0.8176** all applicants, **0.7447** booked, gate **0.78**) | *"S2's reveal, written down, with an owner."* |
| 9 · 0:30 | Features with no causal role (`industry`, `entity_type`, `trade_lines`: **0.4%** of the logit's variance) | *"We measured before we wrote the finding. 'Inert' is what the number says."* |
| 10 · 0:33 | Concentrated in band D (**1,222** of **2,400**, **51%**, default rate **28.2%**) | *"The band can't tell these applicants apart. The PD can."* |
| 11 · 0:35 | `leverage`'s WoE not monotonic (**2** of **13** numeric features; `leverage` carries **11.4%** of the logit's variance) | *"Not a discrimination problem. A reason-code problem: you can't explain it to the applicant."* |

**Recovery.** If you reach 0:26 still on the template, go to finding 2, then finding 5, and
say the other three are on the page. The lab starts at 0:38 whatever happens here.

**Bridge (0:37).** *"Five findings, each with evidence, a control and an owner. Now you write
D5. Nobody finds five in thirty minutes — one well-documented part is the whole job."*

---

## The lab (0:38–1:08) · PROTECT

**0:38 · Handoff — paste in chat, all at once:**

```text
Part by pair (breakout room) number:
1 purpose · 2 data · 3 methodology · 4 assumptions · 5 performance
6 sensitivity · 7 limitations · 8 monitoring · 9 gate · 10 → start again at purpose

cp wiki/mdd/_template/<part>.qmd wiki/mdd/adjudication/
# brief your agent with workshop/prompt-cards/HW-H4.1.md
python -m wiki.homework.check H4.1 --part <part>
```

Pairs are breakout rooms of two if the co-host can open them by 0:39; otherwise work solo with
the same numbering by the order hands go up. Either works: the check is per file. **Tell them
to read the lab sheet on GitHub**, not in their checkout, so it survives whatever the agent
does.

**0:40–1:00 · Walk the chat.** The three questions you will get, in order of frequency:

1. *"Which facts exist?"* — `grep -A5 '"adj\.' wiki/facts/facts.json`. Twelve adjudication
   keys: AUC, lift, both gates, the two cutoffs, the three-way mix, rows and features.
   Anything else is "not yet measured".
2. *"The lint says hand-typed number but it's just 20%."* — That's the trap. Rephrase ("the
   highest fifth") or leave it as not yet measured. The lab sheet's table has every ❌ line.
3. *"Can I use a `score.*` fact?"* — Only for the scorecard's number, named as the scorecard's.

**1:00 · Start your own H4.2 run** in your window (the pre-run renamed out of the way). It
works while the room finishes.

**1:05 · Call time.** *"Whatever your check says now is what we look at."*

**Rehearsal (2026-09-29, clean clone of `model-wiki` with a fresh venv).** Part A done as the
agent would, for `performance`: copy the template, read the prompt card, D4's
`performance.qmd`, `adjudication/src/train.py` and the adjudication facts; write the draft;
check. It passed first time, all four lines ✅, and `verify.py` stayed green with the draft in
place. The agent's own work took **under two minutes of machine time** — that is not a human
pace. For a pair, budget: part assigned and template copied **3 min**, brief filled in and sent
**4 min**, agent run **3–8 min**, check and one fix **5 min**, two claims read against the code
**3 min** — about **20 minutes**, inside the 25-minute ceiling, leaving 5–10 minutes slack. The
check output on the passing draft:

```text
✅ performance.qmd has at least 150 words of your own
✅ performance.qmd cites at least one fact
✅ performance.qmd lints clean
✅ the gate is 0.78 in score/src/train.py and verify.py
```

With "the highest fifth" rewritten as "the top 20%", the third line became:

```text
❌ mdd/adjudication/performance.qmd:25: hand-typed number '20%' — use {{< var … >}}
```

Not rehearsed: a live Copilot agent in a Codespace. If the first pairs report agents taking
over ten minutes, say at 0:50 that one ✅ on the lint is a good result and the full check is
homework.

**Failure modes.** An agent edits `lint_allow.txt` or a D4 page — `git status` shows it,
`git checkout -- <path>` restores it; best discussion of the night if it happens. An agent
changes a gate — the check fails with *"a gate was changed"*; `git checkout --
score/src/train.py verify.py`. `verify.py` red after the lab because a draft does not lint —
correct behaviour; finish it or move it aside (lab sheet).

---

## The validator review (1:08–1:20)

**1:08 · Your window.** The agent's `wiki/homework/_answers/H4.2.md`, then:

```bash
python -m wiki.homework.check H4.2
```

A passing review from the worked solution (rehearsed 2026-09-29):

```text
✅ at least three findings (found 4)
✅ finding 1 cites a fact (score.pop.booked.auc)
✅ finding 2 cites a file that exists (score/src/feature_engineering.py)
✅ finding 3 cites a fact (score.band_booked.AAA.ratio)
✅ finding 4 cites a fact (score.psi_score)
Now compare your findings with D4.7 — which did the agent miss, and why?
```

If your agent cited a documentation page, the check says so — show it, it is the lesson:

```text
❌ finding 3 cites the documentation (wiki/mdd/score/performance.qmd); the documentation is not evidence — cite a fact or the code
```

**1:10 · The room judges.** One finding at a time. The room types **F** (a finding: the
developer must fix or control it), **O** (an observation: record it, do not raise it) or **N**
(noise). Anyone who answered *I'm the validator* in Poll A goes first. Then open
`wiki/mdd/score/limitations.qmd` beside it: which of D4's five did the agent miss, and could it
have seen them? In the worked solution it missed band D and `leverage` — both on pages it had
been given; it never opened the band table or the binning tables. *"An agent audits what it
looks at. Ask it what it read."*

**1:16 · Two or three pairs report** one claim from their draft they checked against the code.
If nobody found a wrong one, offer the rehearsal's: the PD-zone cutoffs are quantiles of the
model's PD over **all** applicants, training rows included (`adjudication/src/train.py`) — so
they are not a held-out measurement, and a draft that calls them "validated on held-out data"
is wrong while linting clean.

---

## Publishing and self-paced (1:20–1:27)

Launch **Poll C** as slide 14 goes up; do not share it.

- The site goes on GitHub Pages and the validation PDF on a release **when Yan publishes
  them** — the link comes in the follow-up email. Promise no date.
- The homework page (*Course* → *Session 4 homework*) has H4.1 (the full chapter: the check
  without `--part`), H4.2 and H4.3, each with a worked solution written by running it with an
  agent.
- The Session 1–3 chapter videos: YouTube, TeamYan (@teamyan2026).

## Close (1:27–1:30)

`python verify.py` on screen, one last time. *"It tells you where you are and that it works.
Tonight it also tells you the document's numbers are current."* Thank the room; this is the last session.

---

## Rehearse these three specifically

1. **The 0:12 fact demo, twice, with a stopwatch.** Four minutes including the restore and the
   second green run. Have `facts.json` open at the key before you share.
2. **The part assignment paste at 0:38.** Once, read aloud, then in chat.
3. **The 1:08 review with your pre-run file.** Know which findings you will call F, O and N
   before the room votes.

## Have answers ready

- *"Is this compliant with SR 11-7 / E-23?"* — It follows SR 11-7's order and the crosswalk
  maps to E-23 and SS1/23, but a crosswalk is a reading aid, not a compliance opinion, and no
  regulator has reviewed it.
- *"Why not just write it in Word?"* — A number typed into Word is right the day it is typed.
  Here, `verify.py` fails the day it stops being right. The validator still gets a PDF.
- *"Does the lint catch every hand-typed number?"* — No. It catches decimals with three or more
  places and percentages. A two-decimal number like a gate value passes the lint; the check's
  "cites at least one fact" and your own read catch the rest. Say it plainly.
- *"Can the agent add the facts too?"* — Yes: a new number is added in
  `wiki/facts/adj_facts.py` through the module's own functions, then `make wiki-facts`. That
  is code, reviewed like code — homework, not tonight.
- *"Why five findings and not zero?"* — A document with no findings has not looked. Every one
  of these has a measured number behind it and an owner.

---

## What this replaces

The previous `S4.md` and `S4-lab.md` were written for the five-session plan (Decisions II:
early warning and line management). That material was taught in the combined Session 3
(`S3_4.md`, `S3_4-lab.md`), so the finale's slot now carries model documentation. The spec is
`docs/superpowers/specs/2026-09-27-model-wiki-design.md` §5.
