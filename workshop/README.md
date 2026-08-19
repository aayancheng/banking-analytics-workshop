# Workshop Materials

Student-facing materials for the live sessions. Everything here assumes the repo root as working directory.

| Folder | Contents |
|---|---|
| **[CHECKPOINTS.md](CHECKPOINTS.md)** | **Start here** — how the stage tags work, and how to jump between them |
| `slides/` | Session decks S1–S5, Markdown source ([Marp](https://marp.app) format) |
| `labs/` | Dual-track lab sheets S1–S5, the oracle-ceiling calculator, the doc-pack template, and the S5 challenge-question bank |
| `prompt-cards/` | Agent-track briefs AC-1, AC-2, AC-3a, AC-3b, AC-4a, AC-4b, AC-5 |

## Reading the slides

The decks are plain Markdown — readable as-is on GitHub. To render them as slides
(instructor machine only; students never need this):

```bash
npx @marp-team/marp-cli workshop/slides/S1.md --pdf   # or --html
```

## A note on the two tracks

Pick whichever track you like, per session. The **agent track** practices directing an
AI coding agent under quality gates — the review checklists on the prompt cards are the
actual skill. The **manual track** runs the same steps yourself. `verify.py` is
track-blind: same checkpoint, same credit, no paid AI subscription ever required.

## If you checked out an old stage tag

These materials live on `main`. After `git checkout stage-N`, bring them back with:

```bash
git checkout main -- workshop
```
