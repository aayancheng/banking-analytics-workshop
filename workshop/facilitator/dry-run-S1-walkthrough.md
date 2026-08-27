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
- [ ] Zoom → Recording: **local**, *Optimize for 3rd party video editor*, *Record separate
      audio file for each participant*
- [ ] Open and arranged: terminal · portal tab · `shared/config.py` · slides
- [ ] **Optional but worth it:** join from your phone as a second participant and say one
      sentence during the run — it's the only way to prove the per-speaker audio split works
      before you rely on it for editing

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
