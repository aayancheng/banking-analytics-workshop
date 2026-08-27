# Demo narration — reference script + recording notes

**This is a reference, not a teleprompter.** Say it your way. The words below exist so you
don't have to invent a structure at the mic, and so the numbers come out right — those are
the only part that has to be exact, because they're checkable and the audience will check.

One clip per frame. The build reads each clip's real duration and times the frame to it, so
there is no stopwatch to hit and no take to redo because you ran two seconds long.

## How long should each frame be?

You don't decide — your voice does. The storyboard seconds in `build_frames()` are now a
**floor**: the minimum time that frame stays up so a viewer can actually read what's on it.
Speak longer and the frame stretches to fit you. Speak shorter and the floor holds.

| Clip | Frame | Floor | Free at ~145 wpm |
|---|---|---:|---:|
| `vo_00` | Title | 3.5s | ~6 words |
| `vo_01` | The four moves | 7.0s | ~14 words |
| `vo_02` | Setup / Codespaces | 4.5s | ~8 words |
| `vo_03` | S1 · Portfolio (table) | 8.5s | ~18 words |
| `vo_04` | S2 · Credit score (chart) | 8.5s | ~18 words |
| `vo_05` | S3 · Decisions (portal) | 5.5s | ~11 words |
| `vo_06` | S4 · Watchlist (portal) | 9.0s | ~19 words |
| `vo_07` | S5 · Governance (terminal) | 5.0s | ~9 words |
| `vo_08` | Close | 4.0s | ~7 words |

"Free" = words that fit inside the floor for free. Going over is fine and costs nothing but
runtime — 15–25 words a frame lands the video around 65–75s, which is still a good length.
The floors exist because three frames carry something to read: the S1 table, the S2
distribution, and the S4 watchlist. Don't rush those even if you have nothing left to say.

## Record

QuickTime Player → File → New Audio Recording (or Voice Memos). Save into
`workshop/demo/audio/` as `vo_00.m4a` … `vo_08.m4a` — `.m4a`, `.wav`, `.mp3`, `.aiff` all work.

- Wired earbuds with a mic beat the built-in mic — the laptop mic picks up room echo.
- Quiet room, no fan, nothing that can knock the desk.
- Leave ~1 second of silence at the start and end of each take.
- One frame per take. A bad Session 4 is a 9-second retake, not a re-record.
- Don't push your voice to compensate for a quiet mic. The build high-passes at 80 Hz and
  normalises every clip to −16 LUFS, so takes from different days still match.
- Record `vo_03` first, not `vo_00`. It's the most ordinary one; by the time you reach the
  title card you'll have found the voice.

---

## The frames

### `vo_00` — Title card
**The idea:** what this is, and that it costs nothing to try.
**Something like:** "Credit analytics with AI agents. Five sessions, and you run all of it
in your browser."

### `vo_01` — The big picture: four moves
**The idea:** the four moves are the transferable part — this is lending, but it's the same
shape in investing, marketing, fraud.
**Keep the order:** build the portfolio → score the risk → decide and price → monitor.
**Something like:** "Every analytics decision comes down to four moves. Build the portfolio.
Score the risk. Decide and price it. Then monitor what you booked."

### `vo_02` — Setup
**The idea:** the setup objection is dead. No install, no environment, no "it works on my
machine."
**Something like:** "You start in Codespaces. Nothing to install — the container builds
itself, and then it proves it worked."

### `vo_03` — Session 1 · Your portfolio
**The idea:** synthetic, so it's publishable — but built to behave like a real book, so
modelling it teaches you something.
**Exact:** 12,000 borrowers · 8,336 booked · 10 industries · 16.7% default.
**Something like:** "Session one builds twelve thousand small-business borrowers across ten
industries. Synthetic, so it's safe to publish — and realistic enough to actually model."

### `vo_04` — Session 2 · Your credit score
**The idea:** the strongest nine seconds in the video. Not "we built a model" — *the gate is
committed in the code, and missing it fails the build.* Nobody else's demo says that.
**Exact:** 300–850, banded D→AAA · realised default 28.9% → 1.0% · held-out AUC 0.8176 ·
gate ≥ 0.78.
**Something like:** "Session two is the scorecard. Held-out A-U-C of point eight two,
against a gate that's committed in the code. Miss the gate and the build fails."

### `vo_05` — Session 3 · Decisions
**The idea:** a score is not a decision. This is where it becomes approve/refer/decline and
a price.
**Exact:** $1.28B mispriced. Say it however sits best — "one-point-two-eight billion" is
accurate; "nearly one-point-three billion" is easier in the mouth and still true.
**Something like:** "Session three turns that score into a decision and a price — and finds
one-point-two-eight billion dollars mispriced."

### `vo_06` — Session 4 · Your watchlist
**The idea:** ranked *and* explained. The named trigger is the difference between a list
someone works and a list someone ignores.
**Something like:** "Session four watches the book you just built. A ranked watchlist that
names the trigger behind every borrower — so you get why, not just who."

### `vo_07` — Session 5 · Governance
**The idea:** the part most courses skip. You leave with the documentation pack, not just a
model.
**Exact:** nine checks, all green.
**Something like:** "Session five assembles the model documentation pack. Nine checks, all
green."

### `vo_08` — Close
**The idea:** the promise of the whole repo — at every checkpoint you can prove where you
are and that it works.
**Something like:** "Five sessions, six checkpoints. At every one of them, you can prove it
works."

---

## Then rebuild

```bash
python workshop/demo/make_demo.py
```

Audio is detected automatically. The console prints which frames got a clip and the new
total runtime. Frames without a clip stay silent at their floor, so you can record a few at
a time and rebuild as you go.
