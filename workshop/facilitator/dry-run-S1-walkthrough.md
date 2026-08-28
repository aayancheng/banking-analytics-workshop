# Dry run — 8-minute S1 walkthrough

**Facilitator notes. Not student-facing.** Companion to
[online-delivery.md](online-delivery.md) → *Dry run A*.

Two jobs at once. It rehearses the **four signature ideas** of Session 1, and it deliberately
exercises **every capture surface** you'll use on the night — face, terminal, slides, browser,
code editor — including the share transitions between them, which is where recordings actually
break. By minute eight you'll know whether the setup holds.

Zoom free is fine here: the 40-minute cap is irrelevant for an 8-minute test. It just can't
tell you anything about a continuous 90-minute recording, which is what you're buying Pro for.

---

## Pre-flight — before you press record

- [ ] Display set to **1920×1080 scaled** (System Settings → Displays)
- [ ] VS Code editor **≥16pt**, integrated terminal **≥16pt**
- [ ] `make run` already warmed — portal answering at **localhost:8100**
- [ ] Notifications off (Focus), Slack / Mail / Messages quit
- [ ] Zoom **desktop app** → Settings → Recording → tick **"Record a separate audio file for
      each participant"** and *Optimize for 3rd party video editor*. Free plan includes this.
      Two things silently defeat it: it only works when you **Record on this Computer** (never
      cloud), and it must be on **before** you hit record — enabling it afterwards does nothing.
      Without it you get one mixed track, and mixed voices can never be separated again. That
      matters because the course is to be built from your screen and your voice only: in a
      mixed track any moment a participant spoke carries their voice permanently and needs
      their written permission, whereas split tracks let you render a your-voice-only version
- [ ] Open and arranged: terminal · portal tab · `shared/config.py` · slides
- [ ] **Optional but worth it:** join from your phone as a second participant and say one
      sentence during the run — solo you get one file, which proves the setting is on but not
      that the split works. Two files appearing is the actual proof. **Turn the phone's volume
      fully down first**, or the two devices in one room will howl; unmute its mic, speak, mute

---

## The run

| Time | Do / say | What it's testing |
|---|---|---|
| **0:00–0:15** | **Slate.** Camera on, no share. "Dry run, Aug 26, Zoom local recording test." Then **five seconds of complete silence** — still, not talking. | Marks the file. The silence gives you a noise-floor sample to measure. |
| **0:15–1:00** | **Cold open, camera only.** ~30 years in bank credit risk; rebuilt a full small-business lending platform solo with AI agents in **4 days, ~$150 in tokens**. "That artifact is real, and you'll be inside it in ten minutes." | Face + voice with no share — your clean audio baseline. |
| **1:00–2:15** | **The contract. First screen share → terminal.** Run `python verify.py`. **Talk into the run**, don't wait in silence. End on the green line: *"you are here, and it works."* | ⚠️ The share transition — the riskiest moment. Small terminal text legibility. Holding the room over dead air. |
| **2:15–3:30** | **How a bank decides.** Switch share → slides. Originate → Adjudicate → Price → Monitor → Manage. PD as the one shared number; *score the business, not the loan*; 300–850 is PD in a friendlier suit. Land **signature idea #1: the leverage is in the application, not the model.** | Second share switch. Slide legibility at 720p. |
| **3:30–5:30** | **The destination.** Switch share → portal at `localhost:8100`. 12,000 scored, the approval mix, **$1.28B mispriced exposure**. Walk **one Approve and one Decline** through Customer 360. Resist rabbit holes — that's the live discipline too. | Browser capture, colour and chart legibility, mouse tracking, scrolling. |
| **5:30–7:00** | **Leakage.** Switch share → `shared/config.py`, show `LEAKAGE_COLUMNS` — all six, named and reviewable. The line: *a deny-list in someone's head is not a control; a deny-list in `config.py` is.* | Code-editor rendering, which behaves differently from the terminal. Scrolling code. |
| **7:00–8:00** | **Close.** Back to the terminal, `python verify.py`, green again. Restate the five-session contract: six checkpoints, and **missing a week costs nothing**. | Final share switch, and ending cleanly rather than trailing off. |
| **8:00** | **Stop recording, then stay put ten seconds.** Don't cut instantly. | Gives you tail to trim against. |

**Four signature ideas, in order:** the checkpoint contract · leverage is in the application ·
the destination is real · leakage is a control problem. If those four land in eight minutes,
the 90-minute version has a spine.

---

## Then check it — this is the actual point

Recording it proves nothing. Watching it does.

1. **Watch it back on your phone.** Not the laptop. Worst screen anyone will use.
   - Can you read the terminal without squinting? If not: fonts up, run it again.
   - Do the share transitions drop frames or go black?
   - Can you hear the fan, the room, the keyboard?
2. **Measure the voice** — target **−16 to −20 LUFS**:
   ```bash
   ffmpeg -hide_banner -i <recording> -af ebur128 -f null - 2>&1 | grep -A2 "Integrated"
   ```
3. **Measure the noise floor** from that five seconds of silence at the top:
   ```bash
   ffmpeg -hide_banner -i <recording> -t 5 -af astats -f null - 2>&1 | grep -i "RMS level"
   ```
   Below about **−60 dB** is quiet. Nearer −40 dB means the room or the mic is audible under
   everything you say, and it gets worse across 90 minutes.
4. **Confirm the files are on disk** and play. If you joined from your phone, confirm the
   per-participant audio split actually happened.
5. **Time yourself.** If the eight minutes ran to twelve, that's a 50% overrun — apply the
   same factor to the 90-minute plan and see what breaks. Better to learn it here.

---

# Take 1 review — 2026-08-28 (9m48s)

Measured off the recording, not impressions.

## What's already right — don't touch it

| | Measured | Target |
|---|---|---|
| Noise floor (opening silence) | **−87.5 dB RMS** | below −60 dB |
| Loudness range | **4.9 LU** | tight = consistent delivery |
| Opening slate silence | 3.5s present | ✓ |
| Tail after the close | 2.6s | ✓ don't cut instantly |

The room and mic are clean, the delivery is even, and the camera cold-open framing and
lighting are good. **The audio setup is solved — stop tuning it.**

## Must fix before Sep 10

1. **`make run` died: "address already in use" on 8100** — and the portal was never shown in
   the entire ten minutes. The demo is the single highest-value block in S1 and it did not
   happen. **Fixed in the Makefile**: `run` now depends on `stop`, so the port is freed first.
   Verified by occupying 8100, running `make run`, and getting a live `/health` response.
2. **The CVXPY solver error prints in the middle of `make verify`**, between `[3/9]` and
   `[4/9]`. Placement could not be worse: it lands inside the one command whose entire job is
   to say *it works*. Traced to `optbinning → ropwr → cvxpy → highspy`; it's a transitive
   dependency, not your code, and Codespaces-only (linux/py3.13 — it does not reproduce on
   macOS). `verify.py` still returns 9/9 green, so it is cosmetic. Two ways to handle it:
   pin `highspy` in `requirements.txt` and test in a *throwaway Codespace* (the only place it
   reproduces), or, if that can't be settled in time, **name it out loud**: "that's a
   third-party solver we don't use — the nine checks are what matter." Owning it turns a
   credibility risk into a credibility moment. Letting it sit there unmentioned does not.
3. **Your speaker notes were on screen.** You showed `S1.md` *source*, including
   `<!-- Speaker: … ~30 years … $150 in tokens … -->` and the block timing comments. The room
   can read your notes and your clock. Show the **rendered** preview, or the Marp HTML — never
   the markdown source.
4. **Close the Copilot / "Build with Agent" chat panel.** It took ~25% of the width for the
   whole run, squeezing the content that matters.
5. **Terminal font is smaller than the editor font.** It's the least forgiving surface you
   have and currently the least readable. Raise it independently
   (`"terminal.integrated.fontSize": 16`).

## Pacing

**9m48s against an 8m plan — 22% over.** Apply that to the 90-minute session and you finish at
**110 minutes**. Decide what comes out of *How a bank decides* now, not live.

There's also a **5.1-second dead gap at 0:09** — the worst possible position, before anyone has
committed to watching. Total silence over 1.5s came to ~29s across the run.

## Levels — one adjustment

Integrated **−19.4 LUFS** is at the quiet end of the −16..−20 band; aim nearer −17.

But **true peak hit −0.3 dBFS**, which is almost clipping. With the average that far below the
peaks, something transient is spiking ~19 dB above your voice — a desk knock, a plosive, or the
mouse. So you can't simply raise the gain. Find the transient first (move the mic off the desk,
or off-axis from your mouth), then raise the level.

## Coverage — two of four signature ideas didn't happen

Only the checkpoint contract and part of *how a bank decides* landed. **The portal ($1.28B) and
`LEAKAGE_COLUMNS` were never shown** — and those are two of the four ideas S1 is built on. Take
2 should reach the portal by 3:30 and `shared/config.py` by 5:30, per the table above.

## Take 2 pre-flight — the additions

- [ ] `make run` **before** you record, confirm localhost:8100 answers, and leave it running
- [ ] Rendered slides open — **not** the markdown source
- [ ] Copilot chat panel closed; Explorer sidebar is fine, it shows the module layout
- [ ] Terminal font raised
- [ ] Browser tabs audited — only what you intend to show
