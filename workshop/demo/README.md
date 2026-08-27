# Workshop Demo — screenshot series + walkthrough video

A step-by-step tour of the repo in GitHub Codespaces, setup → Session 1 → Session 5.

| File | What it is |
|---|---|
| `demo.mp4` | 60-second captioned walkthrough (1920×1080) — title → overview → setup → S1–S5 → close |
| `frames/frame_*.png` | The same 9 steps as standalone captioned screenshots (for slides or a blog post) |
| `assets/` | The **real** captured material the frames are built from — command output (`*.txt`) and portal screenshots (`*.png`) |
| `capture_assets.py` | Renders the three *derived* assets from the committed data + trained scorecard (gitignored — regenerate them) |
| `make_demo.py` | The generator: composes captioned frames from the assets and stitches the MP4 |
| `NARRATION.md` | The voiceover script + recording notes — read this before recording |
| `audio/vo_*.m4a` | The narration recordings, one per frame. **Source, not derived** — committed, because they cannot be regenerated |

## The steps

0. **Title** — what this is
1. **The big picture** — the four moves behind every analytics decision (build the portfolio · score the risk · decide & price · monitor & step in), and why they transfer to investing, marketing, and fraud. No code — readable by anyone.
2. **Setup** — open in Codespaces; the devcontainer runs `make setup && make verify` for you
3. **Session 1 — Your portfolio** — a real slice of the 12,000 synthetic SME borrowers you generate, with the headline totals (8,336 booked · 10 industries · 16.7% default)
4. **Session 2 — Your credit score** — the 300–850 distribution banded D→AAA, beside each band's realised default rate (28.9% → 1.0%): the score rank-orders. AUC 0.8176, **GATE PASS**
5. **Session 3 — Decisions** — the portal: adjudication decisions + pricing's $1.28B mispricing finding
6. **Session 4 — Your watchlist** — the early-warning watchlist, ranked, with the named triggers behind each borrower
7. **Session 5 — Governance** — `make docpack`: nine checks green, demo-ready
8. **Close** — you are here, and it all works

## Regenerate

The video is not a screen recording — it is composed from assets, so it rebuilds
deterministically (the reference build's `make_video.py` pattern). **Two steps**, because
three assets are derived from the data rather than captured, and are gitignored:

```bash
python workshop/demo/capture_assets.py   # → the S1 table, S2 distribution, S4 watchlist crop
python workshop/demo/make_demo.py        # → frames/*.png + demo.mp4
```

`capture_assets.py` needs the stage-2 scorecard to exist (it scores the whole population to
draw the distribution). If you only changed captions or timings, `make_demo.py` alone is
enough — the derived assets are already on disk.

To refresh the *captured* assets from a live run (e.g. after a UI change), retrain the models,
serve the app (`make run`), and re-capture the portal screenshots and command output into
`assets/`. Fonts used: Menlo + Helvetica (macOS); swap the paths at the top of `make_demo.py`
on other platforms.

Timing lives in `build_frames()` — one `(frame, seconds)` pair per step. The S1/S2/S4 outcome
frames deliberately hold ~8.5–9s so a viewer can actually read them; the total is ~60s.

## Narration

Drop clips into `audio/` as `vo_00`..`vo_08` (`.m4a`, `.wav`, `.mp3`, `.aiff`) and
`make_demo.py` picks them up automatically — see [NARRATION.md](NARRATION.md) for the script.

**With audio present the recordings drive the timings.** Each frame is held for its clip's
measured length plus a beat either side, *or* its storyboard seconds — whichever is longer.
So a retake never means re-tuning a storyboard number, the voice can't be cut off
mid-sentence, and a brisk take can't whip the S1 table or the S4 watchlist off screen before
it can be read: the numbers in `build_frames()` become read-time floors rather than targets.
Frames with no clip play silent at their floor, so the voiceover can be recorded a few
frames at a time. Every clip is high-passed at 80 Hz and normalised to −16 LUFS
individually, so takes recorded on different days match.

Durations are *measured off the rendered audio segments*, not computed — the same
recompute-don't-trust rule the rest of the repo follows. Intermediates land in
`frames/narration/` and are gitignored; the recordings themselves are committed.
