# Recutting a session recording

Turns a raw Zoom recording into the compact video that goes to students — polls, clock
checks and hiccups cut out; a title/agenda card; a chapter break (freeze + rising banner)
at each chapter; callout cards at the teaching moments; a small `teamyan.substack.com`
watermark; chapter marks embedded in the MP4 and a YouTube description block. The same
pipeline with a different cut list makes the ~3-minute LinkedIn promo.

**Session 1 is done** (76:53 → 58:53; promo 3:04 cut from the footage) as one stitched video.
**Session 2 is done** (84:37 → six standalone chapter videos of 5–12 min *and* the stitched
53:04, plus a 55 s promo made of the six hooks over a music bed) and is the worked example for
the per-chapter shape below. `S2.cuts.json` is the template for a master cut list,
`S2-promo.cuts.json` for a hooks-only promo with music, `S1-promo.cuts.json` for a promo cut
from footage; the `S2-ch*-hook` compositions are the animated cold opens.

## Where things live

```
workshop/facilitator/recut/            TRACKED — this tooling
  align.py      Zoom transcript -> video time: offset search, anonymised dump, pause windows
  snap.py       moves rough keep boundaries onto audio pauses
  split.py      master cut list -> one cuts file per chapter (S2-ch1.cuts.json ...)
  build.py      graphics -> pieces -> concat; chapters, YouTube block, output-time map
  S1.cuts.json, S1-promo.cuts.json, S2.cuts.json, S2-ch*.cuts.json, S2-promo.cuts.json   the cut lists
  hf/           HyperFrames project: compositions/{S*-intro,S*-outro,chapter,watermark}.html,
                compositions/S2-ch*-hook.html (+ hook.css, hook.js), compositions/callouts/S*-*.html,
                shared.css (deck palette), shared.js

workshop/LectureSummaryandRecordings/  GITIGNORED — recordings, transcripts, every output
  <recording>.mp4, <transcript>.txt, *.pauses*.json (caches), <transcript>.videotime.txt
  music/          the promo's bed (YouTube Audio Library) and music/sfx/ (media-use's bundled SFX)
  out/graphics/   rendered cards, banners, callouts, hooks, watermark.png
  out/frames-<stem>/  out/segments-<stem>/  out/<stem>-compact.mp4  out/<stem>-chapters.txt
  blog/           the Substack post, its screenshots, the LinkedIn copy (S1 examples)
```

The transcript carries attendee names. It never leaves the gitignored folder, the cut
list's `note` fields never name anyone, and the diff is grepped for `@` before a commit
(invariant 6 in the repo's CLAUDE.md).

## Tools

| | |
|---|---|
| `ffmpeg` / `ffprobe` | Homebrew build; **no `drawtext`** — every pixel of text comes from HyperFrames |
| `npx hyperframes` | pinned in `hf/package.json` (`0.8.49` since S2); `build.py` reads the pin from there. Bump with `npx hyperframes@latest upgrade --project hf`, then re-render one banner and look at it — `check`/`lint` want an `index.html` this graphics-only project does not have, so a render *is* the check. Node ≥ 22 + Chrome; `npx hyperframes doctor` |
| Python 3.11+ | stdlib only for the scripts here |

HyperFrames' agent skills are installed per user (`~/.claude/skills/hyperframes*`), not in
the repo. `hyperframes-core` is the composition contract; the rest is optional.

## Division of labour

**HyperFrames renders the graphics; ffmpeg cuts and composites.** HyperFrames renders one
headless-Chrome screenshot per frame — right for a nine-second card, wrong for an hour of
footage (its own docs route "multi-minute" videos to cloud rendering). It never touches
the lecture.

- Cards (`*-intro`, `*-outro`) render to MP4; the chapter banner and callouts to
  **ProRes 4444 MOV with alpha**; the watermark to one PNG.
- `build.py` models the timeline as **pieces**: `card` | `keep` (a source range, watermark
  and timed overlays baked in via `-itsoffset` + `overlay … enable=between`) | `freeze`
  (a chapter break). Pieces encode in parallel to MPEG-TS, then concatenate with stream
  copy — the footage is encoded exactly once. Audio: fixed gain to ≈ −16 LUFS, a −1 dB
  limiter, 50 ms fades, `apad` to the exact video length.
- **A chapter is a freeze.** The keep splits at the chapter point; the chapter's first frame
  holds 2.6 s in silence while the banner rises from below the frame to mid-left and holds;
  the resumed footage carries the banner's drop-out. So a chapter point **must sit on a
  pause** — a two-second silence mid-sentence is worse than no chapter.

## Two output shapes

- **Stitched** (S1): intro card → keeps with a chapter *freeze* at each chapter → outro.
- **One video per chapter** (S2, for YouTube): the master `S2.cuts.json` gives every keep a
  `chapter` number and a `mark` (a YouTube chapter inside the standalone video, no freeze), and
  every chapter a `hook` — the 6–7 s animated cold open that replaces the intro card.
  `python split.py S2.cuts.json` derives `S2-ch1.cuts.json … S2-ch6.cuts.json`; each builds
  exactly like a stitched file (`stem` keys the outputs). The master still builds the stitched
  version with freezes, and there the keep marks are ignored — a mark two seconds after a freeze
  breaks YouTube's 10-second rule. Edit the master, never the derived files.

  The hooks are standalone compositions in the S1-intro shape (root + one `.clip`, one paused
  timeline, `hook.css` + `hook.js` for the title/closer choreography). Every number on a hook
  traces to the repo or to the screen: S2's terminal hook quotes the `AUC=0.7704` frame at
  49:15, not the deck's stale 0.7643. The registry (`npx hyperframes catalog --query …`) was
  searched first; its carousel takes twelve *image* cards, so the five-card ring in
  `S2-ch1-hook.html` is hand-built in that look (gap reported with `hyperframes feedback`).

- **Hooks-only promo with music** (S2): `S2-promo.cuts.json` has no keeps at all — a
  `sequence` of cards (open card, the six hooks, a CTA card) and a `music` block. Each hook is
  rendered again under its own name (`"as": "S2-ch1-promo"`) at a duration that is a whole
  number of bars of the bed (`"vars": {"dur": 7.28}`); the extra time is the closer's hold.
  `music` names the bed, the fades, a loudness target (−14 LUFS, YouTube's normalisation
  point, so the platform does not turn it down), and timed SFX — each `at` is the output
  second where the sound's *peak* lands and `peak` is where that peak sits in the file.
  `mix_music()` renders the mix once to measure it, applies one global gain, limits, and
  stream-copies the video. No voice, so no carve.

  Getting the seams onto the beat cost three things worth knowing. (1) **A composition's
  `data-duration` is read before any script runs**, so a variable cannot change it; the hooks
  therefore carry *no* static duration and the render infers the length from the timeline
  (`hookDuration()` in `hook.js`, `discoveredDuration` in the render log). (2) **The concat
  demuxer offsets each piece by its *container* length**, which is the video plus one padded
  AAC frame (~21 ms), so seams drift a frame every piece; a music build writes a `duration`
  line per file from the *video* stream and concatenates with `-an`. The chapter videos keep
  the old behaviour — a 21 ms hold at a seam is invisible there, and changing it would
  re-cut published files. (3) The beat grid came from onset autocorrelation on the bed
  (`Taking Flight`: 132 BPM, first hit at 4.56 s — the open card's length), then each hook's
  bars were rounded to 25 fps frames so the accumulated error stays under a frame; the
  `hyperframes beats` command wants a project with an `index.html`, which this one is not.

## Doing a session (S2 is the worked example)

```bash
cd workshop/facilitator/recut
```

**0. Drop the files in** `workshop/LectureSummaryandRecordings/` — the Zoom MP4 and the
transcript `.txt`. Name them by session (`S2-recording.mp4`, `S2-transcript.txt`); the S1
files have generic names because they arrived first. Check the capture is the shared
screen only: sample five frames at moments you reacted to chat/polls and look for Zoom UI.

**1. Start the cut list** from the template and point it at the new files:

```bash
cp S2.cuts.json S3.cuts.json          # then edit: stem, session, source, transcript,
                                      # cards, and empty keeps/chapters/callouts
```

**2. Align the transcript** — it is wall-clock; the recording started when you pressed
Record (S1: 13 min after the first cue; offset 20:03:49.25).

```bash
python align.py S2.cuts.json offset   # scans every feasible offset; writes transcript_offset
python align.py S2.cuts.json dump     # <transcript>.videotime.txt — read this end to end
```

If `offset` warns that the peak is not clear-cut, read the macOS menu-bar clock off a frame
(`ffmpeg -ss T -i S2-recording.mp4 -frames:v 1 -vf crop=520:26:1400:0 clock.png`) and
compare; a minute flip pins it to ±5 s.

**3. Author the keeps** from the dump — one per block of teaching content, each with its
`chapter` and a `mark`. For the per-chapter shape, write the chapter theses first (S2: six, one
per video) and let each keep serve exactly one of them; a keep can be moved out of source order
(S2's chapter 6 opens with the 10× odds passage from 34:47 — `build.py` concatenates keeps in
list order). Cut: polls
(launch, wait, read-out), clock checks, live-cohort logistics, plugs the watermark already
carries, the hiccup *and* the later apology for it, start/stop-recording fumbling. Keep
every explanation, every demo, both lab tracks. Where a hiccup contradicted the curriculum,
plan a **correction card** at that moment instead of cutting the lesson.

**4. Snap and read.** `snap.py` moves each boundary onto a pause; it does not know which
sentence the pause follows, so **read every move** against the dump:

```bash
python snap.py S2.cuts.json
python align.py S2.cuts.json window 42:30 +20     # pauses ≥0.3 s + cue text around a point
```

Any boundary next to something you must exclude — an attendee's first name, the sentence
that starts the hiccup — pick the pause by hand from `window`. Chapter points that fall
mid-keep get the same treatment (`snap.py` handles keeps only). S1 needed two boundaries
moved for a name and three chapter points moved onto pauses; S2 moved **eight of 28** —
`snap.py` happily lands on a pause *inside* a sentence ("But it's a good, um…"), so read the
cue text, not just the pause list, and use `--min 0.2 --noise -28` where the phrasing is fast.
Zoom also drops speech: S2's 37:11–37:20 has nine seconds of Yan reading a slide with no cue
at all — check the frame (was the slide up?) and the RMS (speech-level?) before cutting it.

**5. Cards and callouts.** Copy `S1-intro.html` → `S2-intro.html` (title, subtitle, and the
agenda — S1 used the four sections of Yan's own session summary), `S1-outro.html` →
`S2-outro.html` (what's next, repo, Substack). Callouts: one file each under `callouts/`,
`S2-c1-….html`, in the shape of the S1 files — a kicker, a body (code in `<code>`), an
optional note. Every number on a card must trace to the repo or to what is on screen. Set
`session: "2"` in the cuts file; the chapter banner reads it. Lint before rendering — and
note **`lint` on a missing path reports 0 findings**, so check the file exists.

**5b. Hooks** (per-chapter shape): one `S2-ch<n>-hook.html` per chapter, 6–7 s, named in
`chapters[].hook`. Render each with `npx hyperframes render -c compositions/<hook>.html
--format mp4 --fps 25 -o /tmp/x.mp4` and look at three frames before wiring it in — every S2
hook needed one layout pass (a label under a bar, a gate line behind the bars, `white-space:
pre` turning markup newlines into blank terminal lines).

**6. Build.**

```bash
python split.py S2.cuts.json                   # -> S2-ch1..6.cuts.json (per-chapter shape)
python build.py S2.cuts.json graphics          # ~10 s per composition
python build.py S2-ch1.cuts.json graphics      # renders that chapter's hook
python build.py S2-ch3.cuts.json draft         # 960 px: scrub every seam
python build.py S2-ch3.cuts.json final         # full quality
python build.py S2.cuts.json final             # the stitched version, freezes and all
python build.py S2.cuts.json final --only K5 --keep-segments   # one piece after a fix
python build.py S2.cuts.json final --keep-segments             # re-concat only (chapter marks)
```

`build.py` prints the output-time map, checks concatenated length == sum of pieces, embeds
chapter atoms in the MP4, and writes `out/S2-chapters.txt` for the YouTube description
(YouTube reads chapters from the description, never from the file; first line `00:00`,
each ≥ 10 s).

**7. Verify before sharing.** Frame pairs on both sides of every seam (`-ss t±0.12`);
each callout composited over the source frame it annotates; A/V sync by cross-correlating
6 s of output audio against the source at a few mapped points (S1: a constant −26 ms,
below the ~45 ms detection threshold); no Zoom UI; `grep '@'` on the diff.

**8. The promo.** Two shapes exist. S1's is cut from the footage: seven excerpts of ~20 s
(the strongest moment of each chapter, not its first 20 s), each chapter's freeze on *its
excerpt's* first frame, intro/outro cards. S2's is the six hooks over a music bed, no footage
(see *Two output shapes*): drop the bed in `music/`, `cp S2-promo.cuts.json S3-promo.cuts.json`,
find the bed's tempo and first hit, set the open card's length to the hit and each hook's
`dur` to whole bars, then `graphics` → `final`. Verify with frame pairs at every seam, an
SFX-only render to check the peaks land on their `at` times (the bed's own transients drown
them in the mix), and `ebur128` on the result. `stem` keys every output, so the cut lists
never clobber each other.

## Things that bit once

- **HyperFrames root-level clips are pinned to `top:0; left:0`** by the runtime's auto
  layout. Anything positioned elsewhere needs a full-frame `.clip` wrapper with the element
  inside (the watermark rendered top-left until it got one).
- **`overlay=…:format=auto` dropped the alpha** on a ProRes 4444 input; the default format
  composites correctly.
- **MPEG-TS `duration` under-reports audio** by up to an AAC frame; the per-piece "v/a
  diff" is a measurement artefact. Judge sync by cross-correlation on the final, not by
  those numbers.
- **`-ss` before `-i` is frame-accurate** when re-encoding; `-t`, not `-to`, for the length.
- **Zoom's transcript is ±1 s** and rounds cue times; a 3 s plateau of equal alignment
  scores is normal — `align.py` takes its middle.
- **The camera never records the Zoom UI** on a screen share, but the *audio* records you
  reacting to chat by name. That is what moves boundaries, not the picture.
- **`build.py` once hardcoded its own `hyperframes@0.8.36`** beside the pin in `package.json`;
  an `upgrade` bumped one and not the other. It now reads the pin from `package.json`.
- **The deck can be stale where the recording is not.** S2's slides, lab, run of show and
  CLAUDE.md all said the four-bureau-column drop gives 0.7643; the screen — and `main` HEAD,
  re-run — say **0.7704**. Cards quote the screen; the repo fix is a separate task.

## Not done yet

- **Words at the seams are checked by timing, not by ear.** `brew install whisper-cpp` plus
  the `ggml-base.en.bin` model (~150 MB) would let a script transcribe 6 s around each
  boundary and print the words. Ask before downloading. S2's `snapped` note lists the four
  boundaries a by-ear check would settle (K5 in, K6 out, K9b in, K11 out).
- **Pickups** (S3): a keep may carry its own `"source"` — a short recording made after the
  session to close a gap the live run left (S3's P1–P3). Its times are seconds into that file;
  a callout that belongs to it names the same `source`. A solo take usually sits a couple of LU
  hot against the room recording: `"gain_db": -1.5` on the keep, then measure 30 s either side of each seam. The scripts and screen flow live beside
  the recordings (`S3-pickups.md`), every number recomputed through the modules first.
- **Zoom's cloud VTT is on recording time** (S3): `align.py offset` still runs and lands on ≈ 0
  with every gap hit. The Zoom `.txt` from local recording is wall-clock (S1, S2).
- **Shorts.** The hooks keep their content centred so a 9:16 render is a `data-width/height`
  swap plus a layout pass; the footage needs a crop/punch-in pass that does not exist yet.
- **The chapter videos' hooks predate the stage fade-in.** `hookIn()` now fades the whole
  stage in with the title (added for the promo's seams, where the carousel's back card popped);
  the six `S2-chN-compact.mp4` on disk were rendered before it and were being uploaded, so they
  were left alone. The next `build.py S2-chN.cuts.json graphics && … final` picks it up.
- **Burned-in captions** for the promo (LinkedIn autoplays muted) — same dependency.
- The constant −26 ms audio lead could be zeroed with one `adelay` in `build.py`.
