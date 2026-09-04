# S1 — Run of Show (90 minutes)

**Facilitator notes. Not student-facing.**

Session 1 of 5 · **Thursday, September 10, 2026 · 8:00–9:30 pm EDT** (Toronto)
= **Friday, September 11 · 8:00–9:30 am HKT** (Hong Kong) — see *Scheduling* below
Format: online · **free pilot** · checkpoint: `stage-1`

> **This is the 90-minute cut.** The `S1.md` deck was authored for a ~3-hour in-room session.
> What moved is recorded in *What changed from the 3-hour design* at the bottom — read that
> before you rehearse, because two blocks are no longer in this session.

---

## Pre-flight (T–30 min)

- [ ] Instructor Codespace on `stage-5`, `make run` **already warmed** — a cold container during the demo is the worst 90 seconds of the night
- [ ] Second window: clean repo at `stage-1`, mirroring what students see
- [ ] `verify.py` run **twice** (first run is slow on cold imports — your own slides say so)
- [ ] Slides rendered: `npx @marp-team/marp-cli workshop/slides/S1.md --html`
- [ ] Demo fallback open in tabs: `workshop/demo/frames/frame_01.png`, `frame_06.png`
- [ ] `workshop/prompt-cards/AC-1.md` and `workshop/labs/S1-lab.md` open
- [ ] Screen-share tested; terminal font scaled up for the smallest screen in the room

**Pre-work email (send ~3 days ahead).** At 90 minutes the room sweep cannot absorb a broken
laptop. Ask everyone to open the repo in Codespaces *before* the session and confirm it goes
green. Say plainly: **red at the start = join from Codespaces, we do not debug your laptop live.**

⚠️ **They will land on `main`, which is `stage-5`, and see "✅ Stage 5 verified" with nine
checks — not stage-0.** That is correct and it is the stronger check: nine passing checks prove
the whole dependency set, every model and the doc pack, where `stage-0` proves two. Tell them
the expected string in the email, or you will spend the first ten minutes answering "mine says
Stage 5, is that wrong?" It also seeds the 0:32 demo: they have already seen the finished
platform on their own machine.

---

## Run of show

| Time | Block | Beats to hit |
|---|---|---|
| **0:00–0:03** | Welcome | Origin story, **3 minutes hard**: ~30 years bank credit risk → rebuilt this platform solo with AI agents in **4 days, ~$150 in tokens**. That artifact is real; they are inside it within ten minutes. |
| **0:03–0:13** | **Containers** — full script in *Containers, in ten minutes* below | They click the Codespaces badge in minute one; you teach into the 2–4 minute build. Ends with the room green and the rule for all five weeks stated: *no debugging at your seat.* |
| **0:13–0:16** | Promise of five sessions | By S5 they **defend**, not demo. The checkpoint contract: one command always says *"you are here, and it works."* Missing a session costs nothing. |
| **0:16–0:32** | How a bank decides | Lifecycle: Originate → Adjudicate → Price → Monitor → Manage. PD as the one shared number — *score the business, not the loan*; 300–850 is PD in a friendlier suit. **Signature idea #1:** the leverage is in the **application**, not the model. |
| **0:32–0:42** | The destination — live demo · **10 min hard cap** | stage-5 dashboard: 12,000 scored, approval mix, **$1.28B** mispriced exposure. Walk one Approve and one Decline through Customer 360. Resist rabbit holes — every module reappears in a later session. |
| **0:42–0:55** | Why synthetic data | Privacy · control · teachability. Seed 42 → their numbers match your slides exactly. **Discussion, 3 min:** *why would identical numbers alarm you in production?* (stale data, broken pipeline, copied artifacts). Don't answer it for them — count to ten in silence. |
| **0:55–1:05** | Anatomy of a DGP | attributes → latent logit → **+ noise** → Bernoulli draw → label. The three rules they'll defend: noise is deliberate · the label is a **draw, not a formula** · truth columns are written down and denied. |
| **1:05–1:12** | Leakage: the six forbidden columns | **First: `git checkout stage-1` — the room is still on `stage-0` and cannot see this file.** See *Stage-1 handoff* below. Then `shared/config.py::LEAKAGE_COLUMNS`, named and reviewable. The line to land: *a deny-list in someone's head is not a control; a deny-list in `config.py` is.* |
| **1:12–1:25** | Guided lab — do it together | *(Requires `stage-1` — done at 1:05.)* `make data` live (it's fast). Confirm **12,000 / 8,336 / 200,064**, default 16.7%, booked 69.5%. Ask: *why is 8,336 not a round number?* Then the **leakage probe together** — train on a denied column, watch AUC ≈ 1.0, feel the poison, delete the file. This is the emotional peak of the night; protect the time. |
| **1:25–1:30** | Checkpoint + homework | `python verify.py` → ✅ *Stage 1 verified*. **Nobody leaves un-green.** Then, before anyone closes the tab: **`make notebooks`** — the room is on `stage-1` and `notebooks/` lives on `main` only, so tonight's homework opens a file they do not currently have. Homework below. |

**Homework to assign (30–45 min):**

> **Say this first:** `make notebooks`, then open `notebooks/01_stage1_portfolio.ipynb` and run it.
> Items 2–4 come straight off the end of that notebook. It is also the only way they see the
> portfolio profile, the booking funnel and the IV scan — none of which fit in the 90-minute cut.

1. Finish the full audit checklist on the lab sheet (agent track: run prompt card **AC-1** and *review* the agent's audit — you are the reviewer, not the typist)
2. **Bin one feature by hand and compute WoE** — `dscr`, `utilization` or `prior_delinquencies`, five bins. **Lab 2 Part A opens with exactly this**, so this is the item that buys back time next week. Bring the table.
3. **Five in, five out** — from the 20 safe columns, five they would put in a scorecard and five they would refuse, one line each
4. **Seal a number** — the held-out AUC they expect from their five features, written down before S2. The gate is 0.78; the gap is the lesson — collected at the top of S2
5. Read the [4-day build journal](https://teamyan.substack.com/p/claude-code-credit-app-suite). Five lines: *which of the four decision apps would you trust least, and what would you check first?* — collected at the top of S2

⚠️ **Items 2–4 are new and they change how S2 opens.** Lab 2 gives 45 minutes to binning on the
assumption the room arrives cold. If they do the homework they will not — open Part A by asking
who brought a WoE table, and spend the recovered time on the *decisions* rather than the mechanics.

---

## Containers, in ten minutes (0:03–0:13)

**The pacing trick:** a Codespace takes 2–4 minutes to build. Don't wait for it in silence and
don't teach after it lands. **Have them click first, then teach into the gap** — the lesson is
happening on their screen while you explain it.

### Minute by minute

**0:03–0:04 · "Click this before I say anything else"**

On screen: the repo README and its green **Open in GitHub Codespaces** badge.

> "Click it now. It takes two to four minutes. While it builds I'll tell you what it's doing —
> you don't need to watch it."

Everyone now builds in parallel, and your dead time has become teaching time.

**0:04–0:09 · What the container actually is (while theirs builds)**

Put `.devcontainer/devcontainer.json` on screen. The entire environment is twelve lines:

```json
{
  "name": "banking-analytics-workshop",
  "image": "mcr.microsoft.com/devcontainers/python:3.13",
  "postCreateCommand": "make setup && make verify",
  "forwardPorts": [8100, 5180],
  "customizations": { "vscode": { "extensions": ["ms-python.python"] } }
}
```

Four beats, one per line:

1. **`image`** — "This is the machine. Not your laptop, not mine: a stated, identical Linux box
   with Python 3.13. Nobody in this room is on a different machine tonight."
2. **`postCreateCommand`** — "It installs the pinned dependencies *and runs `verify.py`* before
   you ever touch the keyboard. The environment proves itself green before it hands itself to you."
3. **`forwardPorts`** — "In Session 3 you'll run a web app *inside* this container. Port 8100 is
   tunnelled out to your browser. That's how you'll click around your own portal without
   installing anything."
4. **The file itself** — "Twelve lines, in git, reviewable in a pull request like any other code."

**The point that lands for this room:**

> "Every one of you has shipped a model that worked on your machine and broke on someone else's.
> That is not an inconvenience, it is a model risk finding. *Reproducible* has to cover the
> environment, not just the seed. This file is what turns 'reproducible' from something a
> modeller promises into something a validator can check."

Then the teaching promise: identical machine + pinned versions means **their numbers match your
slides exactly**. When Session 2 gives them AUC 0.8176 and your deck says 0.8176, that is not
luck — and *why identical numbers would alarm you in production* is this session's other lesson.

**0:09–0:11 · It lands — first look.** Walk them through the four commands below.

**0:11–0:13 · Read the output, set the rule.** The last line is the whole contract:

```
✅ Stage 5 verified — you are here, and it works.
```

> "That line is the promise of the next five weeks. Whenever you are lost, one command tells you
> where you are and whether it works."

Then state the rule once, and enforce it all term:

> **Red at the start means you join from Codespaces. We do not debug your laptop live.**

---

### What students run, and what they should see

All of this is in their own Codespace terminal.

**1 — The build log (automatic, nothing to type)**

`postCreateCommand` runs `make setup && make verify` and ends with:

```
[9/9] Apps: decision platform smoke .......... OK
✅ Stage 5 verified — you are here, and it works.
```

> "You did not just open a repo. You opened the *finished* platform, and it proved itself before
> you arrived."

**2 — Confirm it themselves**

```bash
make verify
```

The same nine green checks. Their first act is re-running someone else's claim — the habit the
whole workshop is built on.

**3 — Rewind to the beginning**

```bash
git checkout stage-0
make verify
```

```
[1/2] Python 3.11+ ........................... OK
[2/2] Dependencies (pinned) .................. OK
✅ Stage 0 verified — you are here, and it works.
```

Two checks now, because at `stage-0` there is nothing else yet to check. (`.venv` is gitignored,
so it survives the checkout and the environment stays green.)

**4 — See how empty it is**

```bash
git ls-files
```

```
.devcontainer/devcontainer.json
.gitignore
LICENSE
Makefile
README.md
requirements.txt
stage.txt
verify.py
```

> "Eight files. That is the entire repository tonight. The data, the scorecard, the decision
> apps, the portal, the documentation — you are going to build all of it."

⚠️ **Use `git ls-files`, not `ls`.** By this point the container has already run `verify.py` on
`main`, which leaves `__pycache__` folders behind. Those are gitignored, so `git checkout
stage-0` does not remove them, and a plain `ls` shows **thirteen** entries including `score/`
and `app/` — which flatly contradicts the point you are making. `git ls-files` shows what git
actually tracks at this commit. (Verified: `ls` → 13 entries, `git ls-files` → 8.)

That contrast is the emotional beat of the block: they have just watched the finished platform
prove itself, and now they are standing at zero holding six files.

**5 — Your room tally (optional, facilitator)**

```bash
.venv/bin/python verify.py --json
```

```json
{"stage": 0, "ok": true, "checks": [{"name": "Python 3.11+", "ok": true, "detail": "Python 3.13.5", ...
```

Machine-readable, so an assistant can sweep the room fast.

---

### ✅ FIXED in v1.2 — kept for the explanation (was: bare `python` missed `.venv`)

`make setup` installs into `.venv`, but the Codespace terminal's bare `python` is the **system**
3.13. So a student who types the workshop's own signature line —

```bash
python verify.py
```

— gets `Missing: pandas, numpy, ...` instead of green, because those packages live in `.venv`.
The failure message is self-explaining (it prints *"Run: make setup"*), but it lands at minute
nine of session one, which is the worst possible moment for avoidable friction.

Two ways out:

- **Say `make verify` everywhere** — it routes through `.venv/bin/python`. No code change, but
  the README, the slides and the demo video all say `python verify.py`.
- **Make the signature line true** — add one key to `.devcontainer/devcontainer.json`:
  ```json
  "remoteEnv": { "PATH": "${containerWorkspaceFolder}/.venv/bin:${containerEnv:PATH}" }
  ```
  Bare `python` then *is* the venv's python, and every instruction in the repo works verbatim.

**The second was taken** (commit `d0c5769`, shipped in v1.2): `remoteEnv` is in
`.devcontainer/devcontainer.json` on `main` today, so bare `python verify.py` works verbatim
in a Codespace. Nothing to do before Sept 10 — the block above is retained because the
*explanation* is still worth giving if a student asks why a venv lives inside a container.

---

### Questions this block reliably produces

- **"A virtualenv inside a container? Isn't that belt and braces?"** Yes, deliberately. The
  container guarantees the machine; the venv guarantees the packages and keeps the laptop path
  identical to the Codespaces path. One `verify.py` has to be true on both.
- **"Does this cost me anything?"** GitHub's free tier includes monthly Codespaces core-hours;
  this workshop fits comfortably inside it. Stop the codespace when you're done.
- **"Can I just use my laptop?"** Yes, if `make verify` is green. The container is the guarantee,
  not the requirement.
- **"Where is my work saved?"** In the codespace, and it persists between sessions. Push to your
  own fork if you want it to outlive the workshop.
- **"Why 3.13 when the README says 3.11+?"** 3.11 is the floor the code needs; the container pins
  one exact version so nobody is debugging a version difference at 9pm.

### Failure modes

| What you see | What you do |
|---|---|
| Build still spinning past 5 minutes | Keep teaching. It will land, and nobody needs to watch it |
| Codespaces disabled on their account or org | Personal GitHub account, or pair them with a neighbour tonight |
| `Missing: pandas, ...` | `make setup` — or ship the `remoteEnv` fix above |
| Port 8100 won't open in S3 | Ports panel → set 8100 to Public |
| Locked-down corporate laptop | Codespaces *is* the escape hatch. Do not debug it live |

---

## Stage-1 handoff (1:05) — do not skip this

At 0:13 the room checked out `stage-0` and counted eight files. **They are still there.**
Everything from 1:05 onward needs code that does not exist at `stage-0`:

| Needs | Exists at stage-0? |
|---|---|
| `shared/config.py::LEAKAGE_COLUMNS` (1:05 block) | ✗ |
| `make data` → `python -m shared.data_generator` (lab) | ✗ — `ModuleNotFoundError` |
| `from shared.config import RAW` (leakage probe) | ✗ |

`stage-0` has **0** files under `shared/`; `stage-1` has **7**. Run the lab from `stage-0` and it
fails on the first command, in front of everyone, at the emotional peak of the night.

**Open the 1:05 block with this:**

```bash
git checkout stage-1
python verify.py
```

```
[3/3] Data: synthetic SME portfolio .......... OK
✅ Stage 1 verified — you are here, and it works.
```

> "You've just watched where we finish and stood at zero. Now here's tonight: one command, and
> you're holding the code we're about to run. This is the contract — every week you can jump
> straight to where the group is, so missing a session costs you nothing."

**Why `stage-1` and not building from empty:** `stage-1` ships the generator *and* its output.
That is deliberate — the lab's job is to regenerate and prove determinism (seed 42, identical
numbers to the slide), not to type a data generator from scratch in thirteen minutes. The lab
sheet already says so: *"the repo ships it pre-baked; regeneration proves determinism."*

**Detached HEAD is fine and expected.** `CHECKPOINTS.md` already teaches `git checkout stage-N`
as the normal way to move. If anyone worries, the answer is: nothing is lost, and
`git checkout main` returns them to the finished platform.

⚠️ **Watch for:** anyone who ran `verify.py` on `main` has `__pycache__` left behind, so plain
`ls` still shows later-stage folders after the checkout. Use `git ls-files` if you show the tree.

---

## Rehearse these three specifically

1. **The origin story.** You will run long — it's your own history. Time it. Three minutes.
2. **The 10-minute demo.** Rehearse twice: once normally, once assuming the container is cold or the portal 500s. Know which screenshot you'd switch to mid-sentence.
3. **The discussion prompt.** Ten seconds of silence feels like a minute on a video call. Have your prompt-again line ready: *"Give me the worst-case reason — you open Monday's dashboard and the numbers are identical to Friday's."*

**Timing checkpoints while you rehearse** — if you're past these, cut, don't speed up:
- Containers done by **0:13** — if builds are slow keep talking, never stall
- Demo must **start** by 0:32 and **end** by 0:42
- Leakage probe must **start** by 1:18, or you'll finish un-green

## Have answers ready

- *Why isn't 8,336 a round number?*
- *Why would identical numbers alarm you in production?*
- *Do I need a paid AI subscription?* → **No.** The manual track reaches the identical checkpoint; `verify.py` cannot tell which track you took.
- *Will sessions be recorded?*
- *Can I use my own data?*
- *I missed a session — am I lost?* → `git checkout stage-N && python verify.py`. That's the whole recovery.

---

## What changed from the 3-hour design

| 3-hour design | 90-minute cut | Why |
|---|---|---|
| 15-min room sweep | 8 min | Environment moved to **pre-work** (`stage-0`) and stated as a rule |
| 60-min Lab 1 in-room | 13-min guided lab + **homework** | The full audit is self-paced work; the *leakage probe* is the part that must be felt together |
| 20-min **oracle ceiling** block | **Moved to S2** | Its natural home is the session that sets the hard gate — the ceiling is what justifies the gate |
| 10-min break | none | 90 minutes is one sitting |

⚠️ **Knock-on to plan for:** S2 now opens with the oracle-ceiling block *and* still has to collect
homework five-liners, teach WoE, and run its own lab. If every session is 90 minutes, S2 needs its
own re-cut before Sep 17 — S1 is the pilot for that re-timing.

---

## Scheduling — CONFIRMED

**Thursday, September 10, 2026 · 8:00–9:30 pm EDT** (Toronto, UTC−4)
**= Friday, September 11 · 8:00–9:30 am HKT** (Hong Kong, UTC+8)

Hong Kong is **12 hours ahead**, so HK participants join on the **following calendar day**.
That is the one thing most likely to make someone miss session one, so handle it mechanically:

- [ ] Write **both dates and both zones** on every invite, email, and slide — never "8pm" alone
- [ ] Send a **calendar invite** (`.ics`) to HK participants — clients convert automatically; humans don't
- [ ] Say "EDT", not "EST" — in September Toronto is UTC−4, and the wrong label lands people an hour off
- [ ] Reminder to HK participants **the morning of their Sep 11**, not the evening of Sep 10
- [ ] Open the room 10 minutes early — 8:00 am is a hard start for HK

**Facilitator note:** you're presenting at 8 pm your time and they're at 8 am theirs. Their energy
curve is the opposite of yours. The demo at 0:30 is your best tool for waking a morning room.
