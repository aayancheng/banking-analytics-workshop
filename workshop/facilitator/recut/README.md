# Recutting a session recording

Turns a raw Zoom recording into the compact video that goes to students — polls, clock
checks and hiccups cut out; a title/agenda card; a chapter break (freeze + rising banner)
at each chapter; callout cards at the teaching moments; a small `teamyan.substack.com`
watermark; chapter marks embedded in the MP4 and a YouTube description block. The same
pipeline with a different cut list makes the ~3-minute LinkedIn promo.

**Session 1 is done** (76:53 → 58:53; promo 3:04) and is the worked example everything
below refers to. `S1.cuts.json` and `S1-promo.cuts.json` are the templates; the
`S1-*` compositions are the cards to copy.

## Where things live

```
workshop/facilitator/recut/            TRACKED — this tooling
  align.py      Zoom transcript -> video time: offset search, anonymised dump, pause windows
  snap.py       moves rough keep boundaries onto audio pauses
  build.py      graphics -> pieces -> concat; chapters, YouTube block, output-time map
  S1.cuts.json, S1-promo.cuts.json     the cut lists (source seconds)
  hf/           HyperFrames project: compositions/{S1-intro,S1-outro,chapter,watermark}.html,
                compositions/callouts/S1-*.html, shared.css (deck palette), shared.js

workshop/LectureSummaryandRecordings/  GITIGNORED — recordings, transcripts, every output
  <recording>.mp4, <transcript>.txt, *.pauses*.json (caches), <transcript>.videotime.txt
  out/graphics/   rendered cards, banners, callouts, watermark.png
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
| `npx hyperframes` | pinned `0.8.36` in `hf/package.json`; Node ≥ 22 + Chrome; `npx hyperframes doctor` |
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

## Doing Session 2

```bash
cd workshop/facilitator/recut
```

**0. Drop the files in** `workshop/LectureSummaryandRecordings/` — the Zoom MP4 and the
transcript `.txt`. Name them by session (`S2-recording.mp4`, `S2-transcript.txt`); the S1
files have generic names because they arrived first. Check the capture is the shared
screen only: sample five frames at moments you reacted to chat/polls and look for Zoom UI.

**1. Start the cut list** from the template and point it at the new files:

```bash
cp S1.cuts.json S2.cuts.json          # then edit: stem, session, source, transcript,
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

**3. Author the keeps** from the dump — one per block of teaching content. Cut: polls
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
moved for a name and three chapter points moved onto pauses.

**5. Cards and callouts.** Copy `S1-intro.html` → `S2-intro.html` (title, subtitle, and the
agenda — S1 used the four sections of Yan's own session summary), `S1-outro.html` →
`S2-outro.html` (what's next, repo, Substack). Callouts: one file each under `callouts/`,
`S2-c1-….html`, in the shape of the S1 files — a kicker, a body (code in `<code>`), an
optional note. Every number on a card must trace to the repo or to what is on screen. Set
`session: "2"` in the cuts file; the chapter banner reads it. Lint before rendering — and
note **`lint` on a missing path reports 0 findings**, so check the file exists.

**6. Build.**

```bash
python build.py S2.cuts.json graphics          # ~10 s per composition
python build.py S2.cuts.json draft             # 960 px, ~2 min: scrub every seam and freeze
python build.py S2.cuts.json final             # full quality, ~6 min with 5 workers
python build.py S2.cuts.json final --only K5 --keep-segments   # one piece after a fix
```

`build.py` prints the output-time map, checks concatenated length == sum of pieces, embeds
chapter atoms in the MP4, and writes `out/S2-chapters.txt` for the YouTube description
(YouTube reads chapters from the description, never from the file; first line `00:00`,
each ≥ 10 s).

**7. Verify before sharing.** Frame pairs on both sides of every seam (`-ss t±0.12`);
each callout composited over the source frame it annotates; A/V sync by cross-correlating
6 s of output audio against the source at a few mapped points (S1: a constant −26 ms,
below the ~45 ms detection threshold); no Zoom UI; `grep '@'` on the diff.

**8. The promo** is the same again: `cp S1-promo.cuts.json S2-promo.cuts.json`, seven
excerpts of ~20 s (the strongest moment of each chapter, not its first 20 s), each
chapter's freeze on *its excerpt's* first frame, `S2-promo-intro/outro` cards. A jump cut
inside a chapter is invisible on a static screen. `stem` keys every output, so the two cut
lists never clobber each other.

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

## Not done yet

- **Words at the seams are checked by timing, not by ear.** `brew install whisper-cpp` plus
  the `ggml-base.en.bin` model (~150 MB) would let a script transcribe 6 s around each
  boundary and print the words. Ask before downloading.
- **Burned-in captions** for the promo (LinkedIn autoplays muted) — same dependency.
- The constant −26 ms audio lead could be zeroed with one `adelay` in `build.py`.
