# Workshop Demo — screenshot series + walkthrough video

A step-by-step tour of the repo in GitHub Codespaces, setup → Session 1 → Session 5.

| File | What it is |
|---|---|
| `demo.mp4` | 42-second captioned walkthrough (1920×1080) — title → setup → S1–S5 → close |
| `frames/frame_*.png` | The same 8 steps as standalone captioned screenshots (for slides or a blog post) |
| `assets/` | The **real** captured material the frames are built from — command output (`*.txt`) and portal screenshots (`*.png`) |
| `make_demo.py` | The generator: composes captioned frames from the assets and stitches the MP4 |

## The steps

0. **Title** — what this is
1. **Setup** — open in Codespaces; the devcontainer runs `make setup && make verify` for you
2. **Session 1 — Data** — `make data`: 12,000 businesses / 8,336 booked / 200,064 panel rows, seeded and leakage-safe
3. **Session 2 — The Score** — `make train-score`: AUC 0.8176, **GATE PASS**
4. **Session 3 — Decisions** — the portal: adjudication decisions + pricing's $1.28B mispricing finding
5. **Session 4 — The Portfolio** — early-warning watchlist (honest gate) + proactive line increases
6. **Session 5 — Governance** — `make docpack`: nine checks green, demo-ready
7. **Close** — you are here, and it all works

## Regenerate

The video is not a screen recording — it is composed from committed assets, so it
rebuilds deterministically (the reference build's `make_video.py` pattern):

```bash
python workshop/demo/make_demo.py     # → frames/*.png + demo.mp4
```

To refresh the assets from a live run (e.g. after a UI change), retrain the models,
serve the app (`make run`), re-capture the portal screenshots and command output into
`assets/`, then regenerate. Fonts used: Menlo + Helvetica (macOS); swap the paths at the
top of `make_demo.py` on other platforms.
