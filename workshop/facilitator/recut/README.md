# Recutting a session recording

Turns a raw Zoom recording of a session into the compact video that goes to
students: the polls, clock checks and hiccups cut out, a title and agenda card,
chapter lower-thirds, a handful of callout cards at the teaching moments, and a
small `teamyan.substack.com` watermark. First used on Session 1 (76:53 → 58:53).

The recording, the Zoom transcript (it carries attendee names) and every output
live in `workshop/LectureSummaryandRecordings/`, which is **gitignored**. Only
this folder is tracked. Invariant 6 applies: nothing keyed to a real person goes
in a tracked file, and that includes the cut list's notes.

## Tools

| | |
|---|---|
| `ffmpeg` / `ffprobe` | Homebrew build. Note it has **no `drawtext`** — all on-screen text comes from HyperFrames. |
| `npx hyperframes` | pinned `0.8.36` in `hf/package.json`; needs Node ≥ 22 and Chrome. `npx hyperframes doctor` checks. |
| Python 3.11+ | stdlib only for the scripts here. |

## Division of labour

**HyperFrames renders the graphics; ffmpeg cuts and composites.** HyperFrames
renders through headless Chrome one screenshot per frame — the right tool for a
nine-second card, the wrong one for an hour of footage (its own docs route
"multi-minute" videos to cloud rendering). So:

- `hf/compositions/` — one HTML file per graphic. `intro.html`, `outro.html`
  (opaque MP4); `chapter.html` (one composition, rendered once per chapter with
  `--variables`); `callouts/*.html` (one per card); `watermark.html` (a single
  PNG). Lower-thirds and callouts render to **ProRes 4444 MOV with alpha**.
  `shared.css` is the slide deck's palette; `shared.js` the in/out timeline.
- `build.py` extracts each kept range **once**, with the watermark and that
  range's timed overlays baked in (`-itsoffset` + `overlay … enable=between`),
  in parallel, to MPEG-TS intermediates; then concatenates with stream copy.
  The footage is encoded exactly once. Audio: fixed gain to ≈ −16 LUFS (Zoom's
  AGC already flattens it — measure with `ebur128` first), a −1 dB limiter,
  50 ms fades and `apad` so every piece's audio is exactly as long as its video.
- **A chapter is a freeze.** The keep is split at the chapter point; between the
  halves goes a silent piece that holds the chapter's first frame for `freeze`
  seconds (2.6) while the banner rises from below the frame to mid-left and
  holds; the resumed footage carries the banner's drop-out (the MOV's last
  0.5 s, via `-ss` into the file). So a chapter point **must sit on a pause** —
  a two-second silence mid-sentence is worse than no chapter. Chapter marks are
  embedded in the MP4 (VLC, IINA, mpv, QuickTime) and written to
  `<stem>-chapters.txt` for the YouTube description — YouTube reads chapters
  from the description, never from the file; first line `00:00`, each ≥ 10 s.

## Workflow

```bash
cd workshop/facilitator/recut

# 1. Author the cut list from the transcript (see "Aligning the transcript").
#    Times are SOURCE seconds; chapters/callouts are source times too.
$EDITOR S2.cuts.json

# 2. Move every keep boundary onto a pause between sentences, then READ the
#    moves against the transcript — snap.py finds pauses, it does not know
#    which sentence they follow. Widen with --window, or fix by hand.
python snap.py S2.cuts.json

# 3. Graphics, then a 960-px draft in ~2 minutes. Scrub every seam.
python build.py S2.cuts.json graphics
python build.py S2.cuts.json draft

# 4. Full quality (~6 min with 5 workers). Rebuild one piece after a fix:
python build.py S2.cuts.json final
python build.py S2.cuts.json final --only K5 --keep-segments
```

`build.py` prints an output-time map (where every chapter and callout lands
in the finished file) and checks that the concatenated length equals the sum
of the pieces.

## Aligning the transcript to the video

Zoom's transcript is wall-clock; the recording is not, and it need not start
when the meeting did (S1's recording began 13 min after the first transcript
cue). Two anchors that worked:

1. **The macOS menu-bar clock is in every frame of a screen share.** Crop it
   (`crop=520:26:1400:0`) at a few points and read it; a minute flip pins the
   offset to ±5 s.
2. **Cross-correlate transcript gaps with audio pauses**: cue gaps ≥ 1.5 s
   should coincide with `silencedetect` pauses; scan candidate offsets in
   0.25 s steps and take the peak. S1: `video_t = wall − 20:03:49.25`.

Then `snap.py` moves each boundary onto a real pause. Cue times are only good
to ~1 s, so for any boundary next to something you must exclude (an attendee's
name, the sentence that starts the hiccup) look at the pause structure at
`silencedetect=noise=-30dB:d=0.3` and pick the pause by hand. Chapter points
that fall mid-keep need the same treatment (`snap.py` only handles keeps).

## What to cut, from S1

Polls (launch, wait, read-out); time checks ("I'm at 45 minutes, really
good"); logistics for the live cohort; plugs the watermark already carries;
the hiccup itself *and* the later apology for it; the start/stop-recording
fumbling. Keep every explanation, the demo, both lab tracks, the notebook.
Where a hiccup contradicted the curriculum (S1's failed stage checkout ended
with "don't do stages"), a **correction card** at that moment fixes the record
without re-recording.

## Privacy checks before sharing

- No Zoom UI in the capture (chat, polls, participants). Sample frames at the
  moments you reacted to chat.
- No attendee name in the audio at a kept boundary (S1 needed two boundaries
  moved for this).
- The transcript never leaves the gitignored folder; `git status` before
  committing, and grep the diff for `@`.
