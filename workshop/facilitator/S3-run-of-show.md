# S3 — Run of Show: Decisions through the Lifecycle (90 minutes)

**Facilitator notes. Not student-facing.**

Session 3 delivery using the combined S3–4 material · **Thursday, September 24, 2026 ·
8:00–9:30 pm EDT** (Toronto) · **Friday, September 25 · 8:00–9:30 am HKT** (Hong Kong)

Primary materials:

- slides: [`workshop/slides/S3_4.html`](../slides/S3_4.html);
- notebook: [`notebooks/03_04_adjudication_pricing_monitoring.ipynb`](../../notebooks/03_04_adjudication_pricing_monitoring.ipynb);
- lab reference: [`workshop/labs/S3_4-lab.md`](../labs/S3_4-lab.md);
- polls: [`workshop/facilitator/S3-polls.md`](S3-polls.md).

> **This is the 90-minute cut.** The combined deck uses the first 50 minutes. The lab sheet
> contains four exercises and cannot be completed in the remaining time. Poll C measures
> which applications interest this cohort most; the **top two** become guided lab demos,
> **15 minutes each**. The other two remain optional follow-up work.

---

## Session promise

By 9:30, participants should be able to explain how one score spine supports four different
business decisions:

```text
adjudication → pricing → monitoring → line increases
```

They do not need to finish four models. They need to see that each stage asks a different
question, applies a different policy or economic constraint, and requires different evidence.

## Pre-flight (T–30 min)

- [ ] Use **`main` with the completed lifecycle artifacts**, not the historical `stage-3`
      tag. The combined session needs monitoring and line-increase outputs that do not exist
      at the old S3 checkpoint.
- [ ] Run `make stop && python verify.py`; leave the green result available in a terminal tab.
- [ ] Run `make run` and confirm the portal opens at `http://localhost:8100`.
- [ ] Open `workshop/slides/S3_4.html` in a browser and confirm no overflow warning appears.
- [ ] Open the combined notebook in a second window, already executed end to end.
- [ ] In the notebook, bookmark or note the locations of `## 1. Adjudication`,
      `## 2. Pricing`, `## 3. Monitoring`, `## 4. Line increases`, and
      `## One account, four decisions`.
- [ ] Keep the notebook positioned at **The flow of decisions** before participants arrive.
- [ ] Open the lab sheet in a third tab. It is a reference menu, not tonight’s linear script.
- [ ] Create all four anonymous polls from `S3-polls.md`. Poll C must allow participants to
      **select up to two** responses.
- [ ] Rehearse the four slide-to-notebook switches below. Share one application window rather
      than the entire desktop so the change of context is obvious.
- [ ] Pre-run all four training commands. During the lab, rerun only the commands needed for
      the two winning demos; if a command is slow, use the executed notebook output.

## Window discipline

Use slides to frame the business question and the notebook to prove how the analytics works.
Say the switch out loud before changing windows:

> “The slide gives us the decision. Now I’m switching to the notebook to show the evidence.”

When returning:

> “We have the evidence. Back to the slides for the next business question.”

Do not scroll while the wrong window is shared. Pause for one beat after every switch so
participants can reorient.

## Run of show

| Time | Shared screen | Block | Beats to hit |
|---|---|---|---|
| **0:00–0:05** | **SCREEN: SLIDES** | Open the lifecycle | Title, route, and one score spine/four decisions. Participants run `python verify.py` while you establish the sequence. Do not open the notebook yet. |
| **0:05–0:12** | **SCREEN: SLIDES** | Adjudication · **Poll A** at 0:07 | “A decision is not a score,” then policy parameters. Poll A makes the room commit on what happens when low PD conflicts with a hard rule. |
| **0:12–0:16** | **SWITCH → NOTEBOOK §1** | Show policy becoming a decision | Show the decision sequence, exact policy parameters, and the Approve/Refer/Decline output. Read one reason trail. Do not train live here. |
| **0:16–0:22** | **RETURN → SLIDES** | Pricing | ROE/RAROC, then quoted vs hurdle vs recommended rate. Land the idea that deterministic arithmetic can change an approval into a reprice decision. |
| **0:22–0:26** | **SWITCH → NOTEBOOK §2** | Show the three pricing cases | Display the parallel three-loan table. Ask for the action on each column before reading the notebook interpretation. |
| **0:26–0:34** | **RETURN → SLIDES** | Monitoring · **Poll B** at 0:29 | “The portfolio wakes up,” then the metric table. Poll B asks which metric fits a 10%-capacity watchlist. Reveal top-decile capture and lift. |
| **0:34–0:39** | **SWITCH → NOTEBOOK §3** | Show the deterioration model | Point out features and training split, then the held-out metrics and 54% vs 21.6% chart. Quote the held-out number. If time permits, show the oracle ceiling output. |
| **0:39–0:44** | **RETURN → SLIDES** | Line increases | Walk the four conjunctive gates and the amount cap. Emphasize that all gates must pass; a strong candidate score cannot rescue weak PD or economics. |
| **0:44–0:47** | **SWITCH → NOTEBOOK §4** | Show an actual offer decision | Display the exact thresholds, then move to “One account, four decisions.” Trace one row from adjudication through the line-increase verdict. |
| **0:47–0:50** | **RETURN → SLIDES** | Lab handoff · **Poll C** | Launch the application-interest poll. Share results. Announce the top two and write their order in chat: highest interest first, second-highest next. |
| **0:50–1:05** | Notebook / portal / terminal | Guided demo 1 | Run the highest-interest exercise using the 15-minute card below. Participants may follow, but the facilitator owns the screen and clock. |
| **1:05–1:20** | Notebook / portal / terminal | Guided demo 2 | Run the second-highest exercise. Stop at 1:20 even if discussion is lively; paste the remaining prompts into chat as follow-up. |
| **1:20–1:27** | Notebook final table | Lifecycle debrief | Compare the two demos: model signal, business rule, evidence, action. Ask two participants which decision they would defend and what they would show first. |
| **1:27–1:30** | Terminal, then poll | Checkpoint + **Poll D** | `python verify.py`; assign the short decision memo; launch the exit pulse at 1:29 and do not share it on screen. |

The PROTECT blocks are the four notebook switches and both guided demos. If the slide portion
runs long, compress explanation on the policy-parameter table and the line-amount formula.
Do not steal time from Poll C or the demos.

---

## Screen-share choreography

### 0:12 · SWITCH → NOTEBOOK §1

Start at **“The decision sequence.”** Show the order: hard knockouts, PD zones, then refer
overrides. Move to the output that reports the decision mix and read one applicant’s trail.

Bridge back:

> “The model supplied a PD. Policy turned it into a customer outcome.”

### 0:22 · SWITCH → NOTEBOOK §2

Go directly to the three pricing examples. Keep the table visible while asking:

1. Which loan fails the hurdle?
2. Which clears the minimum but not the recommendation?
3. Why can a high-PD loan still show strong ROE at a sufficiently high rate?

Bridge back:

> “Approval answered whether we lend. Pricing answers whether the yes earns its capital.”

### 0:34 · SWITCH → NOTEBOOK §3

Show the deterioration feature list and the 80/20 held-out training logic, then jump to the
capture chart. Do not linger on code syntax. The teaching beat is that 54% is partly the
model remembering its training book; 21.6% is the estimate for unseen accounts.

Bridge back:

> “The watchlist is useful because it concentrates risk inside a workable queue—not because
> the AUC looks impressive.”

### 0:44 · SWITCH → NOTEBOOK §4

Show the exact offer rule and one-account table. Read every gate for one offered account and
one failed gate for a non-offered account. End on the integrated account view; this makes the
lab menu feel like four views of one system rather than four unrelated exercises.

Bridge back:

> “We have seen all four applications. Now your interest determines which two we explore.”

---

## Poll C protocol — interest chooses the lab

Poll C is not a quiz and there is no correct answer. It asks which applications participants
are **most interested** in exploring. Each person may select up to two:

1. adjudication;
2. pricing;
3. monitoring; and
4. line increases / line management.

Sort by total votes and run the **top two** as guided demos, highest first. Read all four vote
totals aloud so participants know their preferences changed the session.

If second place is tied, run a ten-second chat runoff between the tied applications. If the
runoff is still tied, use **Adjudication + Monitoring** as the default because they provide
the clearest policy and held-out-evaluation lessons. Do not try to squeeze in a third demo.

Say this explicitly:

> “The full lab has four exercises. In 90 minutes, depth beats checking boxes. We will work
> the top two now; the other two remain in the lab sheet for follow-up.”

---

## The four 15-minute guided-demo cards

Use only the two selected by Poll C. Each card is intentionally complete on its own.

### A — Adjudication: model signal vs policy decision

**0:00–0:03 · orient.** Open notebook §1 and restate the decision order.

**0:03–0:10 · inspect.** In the portal, read one Approve, one Refer, and one Decline trail.
For each, ask: *model or rule?* Point out a hard knockout and a refer override.

**0:10–0:15 · decide.** Show the reference mix—Approve **30.8%**, Refer **36.8%**, Decline
**32.4%**—and ask what would change if a PD cutoff moved versus a hard rule changed.

Optional command if artifacts are missing:

```bash
make train-adjudication
```

### B — Pricing: approved does not mean profitable

**0:00–0:03 · orient.** Open notebook §2 and distinguish quoted, hurdle, and recommended rates.

**0:03–0:10 · inspect.** Use the three-loan table. Have participants call the action for each
column before revealing the notebook’s result.

**0:10–0:15 · decide.** Show the reference totals—**30.4%** clearing the 15% hurdle,
**10.9%** median ROE, and **$1.28B** mispriced exposure. Ask which segment should receive the
first repricing call and why.

Optional command:

```bash
make price
```

### C — Monitoring: turn probability into a workable queue

**0:00–0:03 · orient.** Open notebook §3 and identify the target, behavioral features, and
held-out split.

**0:03–0:10 · inspect.** Compare AUC **0.662**, PR-AUC **0.308**, and top-decile capture
**21.6% = 2.16×**. Show why the held-out point—not the 54% in-sample curve—is trusted.

**0:10–0:15 · decide.** Open the top-10 watchlist. Ask why named triggers must accompany the
probability for relationship managers and validators.

Optional commands:

```bash
make train-ews
python workshop/labs/oracle_ceiling.py
```

### D — Line increases: growth inside four gates

**0:00–0:03 · orient.** Open notebook §4 and read the four simultaneous gates aloud.

**0:03–0:10 · inspect.** Walk one accepted offer and one rejected candidate. For the rejection,
name the controlling failed gate; do not average the conditions together.

**0:10–0:15 · decide.** Compare the offered cohort with the book: PD **0.036 vs 0.117**,
utilization **0.837 vs 0.471**, and incremental ROE **0.215**. Ask whether 95 offers from
8,336 accounts is excessive restraint or disciplined growth.

Optional command:

```bash
make train-line-increase
```

---

## Debrief (1:20–1:27)

Return to the notebook’s **One account, four decisions** table. Draw four columns in chat or
on a blank slide:

| Decision | Model signal | Business rule | Evidence shown |
|---|---|---|---|
| Adjudication | PD / score | knockout, PD zone, refer override | reason trail |
| Pricing | PD + quoted rate | ROE hurdle / recommendation | pricing waterfall |
| Monitoring | deterioration probability | review capacity / trigger rules | held-out capture |
| Line increases | candidate probability | PD, amount, and ROE gates | offer audit trail |

Fill the two demonstrated rows first, then ask the room to complete the other two verbally.
The point is continuity: one account can receive a sensible “yes” at one stage and a sensible
“no” at another because the business question changed.

## Homework to assign

1. Complete either of the two lab exercises not demonstrated live.
2. Write the short **“Defend this lifecycle decision”** memo from `S3_4-lab.md` using one
   business from the final notebook table.
3. Bring one sentence to the next session: *where did a policy or economic rule matter more
   than the model score?*

## Rehearse these three specifically

1. **The four window switches.** Each switch should take under ten seconds and land at the
   correct notebook section without visible searching.
2. **Poll C tally and announcement.** Practice turning the result into a demo order in under
   one minute, including the tie procedure.
3. **Both 15-minute hard stops.** Rehearse all four demo cards once so any pair can win.

## Have answers ready

- **“Why not complete all four labs?”** Four 15-minute exercises plus setup, teaching, and
  debrief exceed 90 minutes. The deck gives everyone the full lifecycle; the demos give depth
  on the applications the cohort values most.
- **“Does low PD guarantee approval?”** No. Hard policy rules can decline before the PD zone,
  and refer overrides can downgrade an approval.
- **“Why is recommended rate above the hurdle?”** The hurdle is the minimum required return;
  the recommendation adds the reference margin cushion.
- **“Is 0.662 AUC weak?”** Not by itself. Compare the model with the data ceiling, PR-AUC base
  rate, and operational capture gate. The watchlist clears the workshop’s honest gate.
- **“Why can a good account fail a line-increase offer?”** The offer is conjunctive. Candidate
  appetite, origination PD, a positive amount, and incremental ROE must all pass.

## What changed from the full lab design

- The 80-minute `S3_4-lab.md` remains the complete student reference.
- The live session uses **30 minutes for two Poll-C-selected guided demos**, not 80 minutes for
  four independent exercises.
- Slides and notebook are interleaved at four planned transitions. Slides state the business
  decision; notebook outputs provide the evidence.
- Poll C measures application interest rather than testing knowledge. Its result changes what
  happens live.
- The two exercises not selected become follow-up work, not rushed live content.

