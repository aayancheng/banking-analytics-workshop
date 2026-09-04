# Lab 5 — The Documentation Pack & The Defense (S5, 40 min + capstone)

**Checkpoint:** `stage-5` · Today's artifact is a document; today's skill is a defense.

> `python verify.py` first, as always. Lost? `git stash && git checkout stage-5 && python verify.py`.
> Notebooks vanish after a stage jump? They live on `main` only — `make notebooks` brings them back.

## Part A — assemble YOUR documentation pack (40 min)

**Inputs:** your four memos (S1 data audit · S2 scorecard · S3 cutoff · S4 watchlist) + `workshop/labs/doc-pack-template.md`.
**Output:** `my_model_doc.md` — a mini model-doc a validator could read without you in the room.

### Agent track (card AC-5)

The agent drafts sections *from your memos*; you edit for accuracy. Every number in the final doc must trace to an artifact you can open (`score/docs/validation_report.md`, `pricing/docs/summary.json`, …). An unedited agent draft is detectable in the defense round — and graded accordingly.

### Manual track

Work through the template section by section. Copy nothing from the instructor pack — its structure is your map (`docs/model_doc_pack/MODEL_DOCUMENTATION.md`), your memos are the content.

### Both tracks — write these two sections yourself, unassisted

1. **Limitations & appropriate use.** At minimum: synthetic data (what that does and doesn't prove), the EWS oracle ceiling (cite the number), one limitation nobody has said out loud in class yet.
2. **Monitoring plan.** What metric drifts first if the world changes? At what threshold does who get called? What would make you *pull* a model?

### Quality bar (self-check before the defense)

- [ ] Every metric has its gate next to it — including the honest gate, presented as integrity, not apology
- [ ] A named human owns each decision layer (cutoffs, pricing hurdle, offer rules)
- [ ] The two unassisted sections say something a template couldn't

## Part B — the defense round (10 min each, hard timer)

**5 min demo** (portal, one business, all five modules) + **5 min panel Q&A** (peer panelist draws from `workshop/labs/challenge-questions.md` — all 20 are fair game).

Rubric (each 1–5): lifecycle completeness · decision reasoning with numbers · honesty under challenge · documentation quality · agent direction.

**Strategy advice, free of charge:** when you don't know, say what you'd check and where. "I'd verify that against the validation report before answering" *scores*. Bluffing doesn't — the panel has the artifacts open.

## Converge — the last one

```bash
python verify.py     # ✅ Stage 5 verified — you are here, and it ALL works.
```

Keep the repo. It's yours — public, portfolio-grade, and you can defend every number in it. That's rarer than you think.
