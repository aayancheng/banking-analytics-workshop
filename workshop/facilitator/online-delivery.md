# Online delivery — platform, recording, dry runs

**Facilitator notes. Not student-facing.**

Five 90-minute sessions, online, all recorded. Toronto + Hong Kong, so the recording is
part of the offer, not a bonus — it's what removes the time-zone objection.

---

## Platform: Google Meet (free) + local recording

**No free platform will record for you.** Meet needs a paid Workspace tier, Zoom free
records locally but caps group calls at 40 minutes, and Jitsi's public instance has no time
limit but needs Jibri (self-hosted) or paid JaaS to record. That's the whole decision in one
line: the meeting is cheap, the recording is what costs.

So stop asking the platform to record. **Record locally on the Mac instead** — which is
better for the YouTube/course goal anyway, because it captures full-resolution screen rather
than a re-encoded conference stream.

| Option | 90 min? | Records? | Verdict |
|---|---|---|---|
| Zoom, free | ✗ 40-min cap → **two** rejoins | ✓ local | Cuts land badly (below) |
| Jitsi (meet.jit.si) | ✓ no cap | ✗ needs Jibri/JaaS | Unfamiliar + unpredictable bridge |
| **Google Meet, free** | ✗ 60-min cap → **one** rejoin | ✗ record locally | **Use this for the pilot** |
| Zoom Pro (~$17/mo) | ✓ 30 h | ✓ per-speaker audio | The upgrade, if the dry run says so |

### Why Meet free beats Zoom free: where the cut lands

Zoom's 40-minute cap forces two rejoins, and in this run of show they land on the two blocks
you cannot afford to interrupt — **0:40 is inside the live demo**, and **1:20 is inside the
guided lab**, the emotional peak of the night. Restructuring around it gives only one viable
split (0:32 / 0:55), which breaks momentum immediately *before* the demo and leaves a
39-minute block with one minute of margin.

Meet's 60-minute cap forces **one** rejoin, and it can be placed where you want it:

> **Take the break at 0:42, right after the live demo's hard cap.**
> Meeting 1 = 0:00–0:42 (18 min of margin). Meeting 2 = 0:42–1:30 (12 min of margin).
> Both comfortably under 60, and the margin sits on the block most likely to overrun.

A 90-minute evening session at 8pm Toronto / 8am Hong Kong **should** have a break anyway.
The cap is forcing good pedagogy. Announce it as a break, not as a platform limit.

**Budget 3–5 minutes for it and take that time out of *How a bank decides* (0:16–0:32)** —
already flagged in the run of show as the recoverable block. Don't let it come out of the lab.

### Why not Jitsi
No cap and no accounts, which is genuinely attractive. But your audience is bank risk
practitioners joining on corporate-ish laptops from two continents, and the public bridge is
the one variable you can neither test in advance nor fix on the night. Small terminal text
over a degraded free bridge is exactly the failure you can't recover from mid-demo. Meet is
the boring, known quantity — and boring is what session 1 needs.

### When to spend the $34
**Zoom Pro, billed monthly (~$16.99), two cycles for Sep 10 → Oct 8 = ~$34.** What that buys
isn't features, it's the removal of a whole class of failure on a night you can't re-run —
no rejoin, no local-recording rig, and per-participant audio tracks that make highlight
editing hours faster.

**Let the dry run decide, because the dry run is free either way.** If the free stack records
cleanly and you can read the terminal on your phone, go free and keep the money. If the
recording rig is shaky at T–7 days, $34 is the cheapest insurance in this entire project.

---

## Recording locally — two tiers

**Tier 1 — QuickTime, zero setup.** New Screen Recording, mic as input. Captures your screen
and your voice. It does *not* capture the participants — macOS won't let an app record system
audio natively.

That's a smaller loss than it sounds, and there's a fix that improves the recording anyway:
**repeat every question before answering it.** Standard practice for recorded teaching, and
it helps the Hong Kong attendees who are listening at 8am regardless.

Use this tier for the dry run. It may be enough for S1.

**Tier 2 — OBS + BlackHole, ~1 hour of setup.** Adds participant audio.
```bash
brew install --cask blackhole-2ch obs
```
Then Audio MIDI Setup → create a **Multi-Output Device** (built-in output + BlackHole) so you
still hear the call while it routes to the recorder; in OBS add a Display Capture, your mic,
and BlackHole as an audio source. Record at 1920×1080.

Do **not** set this up for the first time in the week of the session, and don't run it live
until a dry run has proved it. A compositor plus Codespaces plus the portal plus slides on
one machine is how you get dropped frames during the demo.

## Recording consent — do this before Sep 10

You intend to publish highlights to YouTube. Attendees are in Ontario and Hong Kong, and
they're identifiable bank practitioners. Get this right the boring way:

1. **In the confirmation email**, plainly: the session is recorded; the recording is shared
   with the cohort; *clips may be published publicly*. Cameras and mics are optional.
2. **At the top of the recording**, say it out loud before anything else. That verbal
   moment is the record that matters if it's ever questioned.
3. **Default to publishing only your screen and your voice.** If a clip contains a
   participant's face, name, voice or employer, ask that person first — one message, in
   writing. Their employers' comms policies are not your problem until you publish them.

Assume anything said about a named employer is unpublishable unless cleared.

---

## Dry run A — technical rehearsal (~20 min, do this first)

Solo. The goal is not to practise teaching; it's to find out whether your screen is legible
and your voice is audible. Nothing else here matters if those fail.

1. **Set the display to 1920×1080 before joining** (System Settings → Displays → Scaled).
   Sharing a Retina desktop makes the conference stream downsample everything, and your
   terminal is the first casualty. Share a **full screen**, not a window.
2. **Scale the fonts.** VS Code editor ≥ 16pt, integrated terminal ≥ 16pt. The default is
   unreadable when re-encoded to 720p.
3. Start a QuickTime screen recording (mic on), share your screen in Meet to nobody, and do
   5 real minutes: the stage-5 dashboard, `make data`, `python verify.py`. No participants
   needed — you're testing legibility and audio, not teaching.
4. **Watch the recording back on your phone.** Not your laptop — your phone. That's the
   worst screen anyone will use, and it's what YouTube viewers get.
   - Can you read the terminal without squinting? If not, fonts up, repeat.
   - Can you hear the laptop fan, the room, the keyboard?
5. **Measure the audio** rather than guessing:
   ```bash
   ffmpeg -hide_banner -i <recording>.m4a -af ebur128 -f null - 2>&1 | grep -A2 "Integrated"
   ```
   Speech wants roughly **−16 to −20 LUFS**. Much quieter and every viewer reaches for the
   volume; much louder and it clips. Fix it with mic position, not by shouting.
6. Confirm the file is actually on disk and plays. A recording you assumed was running is
   the single most common way a session is lost.

## Dry run B — full 90-minute run (week of Sep 3)

Solo, recorded, against a clock, following [S1-run-of-show.md](S1-run-of-show.md) exactly.
Do not skip blocks you "know" — the blocks you know are the ones that overrun.

Checkpoints to write down as you pass them:

| Should be at | Block |
|---|---|
| **0:13** | Containers done, room green |
| **0:32** | Starting the live demo |
| **0:42** | Demo **finished** — this is the 10-min hard cap |
| **0:55** | Starting Anatomy of a DGP |
| **1:12** | Starting the guided lab |

If you're 5+ minutes behind at **0:32**, you will not finish the lab — and the lab is the
emotional peak of the night. The recoverable time is in *How a bank decides* (0:16–0:32),
not in the lab. Decide now what you cut, so you're not deciding it live.

**Rehearse the break.** At 0:42, actually stop, actually rejoin the second meeting link,
actually restart the recording. Time it. If the rejoin costs more than 3 minutes — finding
the link, restarting the capture, re-sharing the screen — fix that now, not on the night.
This is the one thing the free path costs you, and it is entirely rehearsable.

**Failure drills — run each once:**
- Codespace won't start → fall back to `workshop/demo/frames/frame_01.png` / `frame_06.png`
  (already in the run-of-show pre-flight)
- Home internet drops → phone hotspot, *pre-tested*, rejoin as host
- Recording didn't start → check the file exists at the **0:42 break**, not at 1:30. The
  break is your checkpoint; use it.

---

## Session-day pre-flight

Everything in the S1 run-of-show's T–30 list, plus:

- [ ] Display already at 1920×1080, fonts already scaled
- [ ] Notifications off (macOS Focus), Slack/Mail/Messages quit
- [ ] Browser/Meet updated **the day before**, never the hour before
- [ ] **Both meeting links** to hand, and already in the invite
- [ ] Local recording folder has space
- [ ] Phone on silent, hotspot ready
- [ ] Water. It's 90 minutes of talking at 8pm.
