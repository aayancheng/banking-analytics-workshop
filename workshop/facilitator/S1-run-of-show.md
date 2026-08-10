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
laptop. Ask everyone to open the repo in Codespaces and run `verify.py` *before* the session —
`stage-0` is exactly this pre-work checkpoint. Say plainly: **red at the start = join from
Codespaces, we do not debug your laptop live.**

---

## Run of show

| Time | Block | Beats to hit |
|---|---|---|
| **0:00–0:08** | Welcome + room sweep | Everyone runs `verify.py` **first, before anything else**. Red → Codespaces. State the rule for all five weeks: *no debugging at your seat.* Origin story, **3 minutes hard**: ~30 years bank credit risk → rebuilt this platform solo with AI agents in **4 days, ~$150 in tokens**. That artifact is real; they're inside it in 20 minutes. |
| **0:08–0:12** | Promise of five sessions | By S5 they **defend**, not demo. The checkpoint contract: one command always says *"you are here, and it works."* Missing a session costs nothing. |
| **0:12–0:30** | How a bank decides | Lifecycle: Originate → Adjudicate → Price → Monitor → Manage. PD as the one shared number — *score the business, not the loan*; 300–850 is PD in a friendlier suit. **Signature idea #1:** the leverage is in the **application**, not the model. |
| **0:30–0:40** | The destination — live demo · **10 min hard cap** | stage-5 dashboard: 12,000 scored, approval mix, **$1.28B** mispriced exposure. Walk one Approve and one Decline through Customer 360. Resist rabbit holes — every module reappears in a later session. |
| **0:40–0:55** | Why synthetic data | Privacy · control · teachability. Seed 42 → their numbers match your slides exactly. **Discussion, 3 min:** *why would identical numbers alarm you in production?* (stale data, broken pipeline, copied artifacts). Don't answer it for them — count to ten in silence. |
| **0:55–1:05** | Anatomy of a DGP | attributes → latent logit → **+ noise** → Bernoulli draw → label. The three rules they'll defend: noise is deliberate · the label is a **draw, not a formula** · truth columns are written down and denied. |
| **1:05–1:12** | Leakage: the six forbidden columns | `shared/config.py::LEAKAGE_COLUMNS`, named and reviewable. The line to land: *a deny-list in someone's head is not a control; a deny-list in `config.py` is.* |
| **1:12–1:25** | Guided lab — do it together | `make data` live (it's fast). Confirm **12,000 / 8,336 / 200,064**, default 16.7%, booked 69.5%. Ask: *why is 8,336 not a round number?* Then the **leakage probe together** — train on a denied column, watch AUC ≈ 1.0, feel the poison, delete the file. This is the emotional peak of the night; protect the time. |
| **1:25–1:30** | Checkpoint + homework | `python verify.py` → ✅ *Stage 1 verified*. **Nobody leaves un-green.** Homework below. |

**Homework to assign (30–45 min):**
1. Finish the full audit checklist on the lab sheet (agent track: run prompt card **AC-1** and *review* the agent's audit — you are the reviewer, not the typist)
2. Read the [4-day build journal](https://teamyan.substack.com/p/claude-code-credit-app-suite)
3. Five lines: *which of the four decision apps would you trust least, and what would you check first?* — collected at the top of S2

---

## Rehearse these three specifically

1. **The origin story.** You will run long — it's your own history. Time it. Three minutes.
2. **The 10-minute demo.** Rehearse twice: once normally, once assuming the container is cold or the portal 500s. Know which screenshot you'd switch to mid-sentence.
3. **The discussion prompt.** Ten seconds of silence feels like a minute on a video call. Have your prompt-again line ready: *"Give me the worst-case reason — you open Monday's dashboard and the numbers are identical to Friday's."*

**Timing checkpoints while you rehearse** — if you're past these, cut, don't speed up:
- Demo must **start** by 0:30 and **end** by 0:40
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
