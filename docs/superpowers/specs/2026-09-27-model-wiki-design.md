# Model Documentation Wiki — design

**Date:** 2026-09-27
**Status:** approved in brainstorming, awaiting spec review
**Context:** Sessions 1–3 have run and are recut. Session 4 (the finale, Thu 1 Oct 2026,
8pm EDT) is model governance. The existing documentation pack
(`docs/model_doc_pack/MODEL_DOCUMENTATION.md`, 147 lines, built by
`tools/build_doc_pack.py`) is an accurate results summary but not a model development
document: it has almost nothing on intended use, conceptual soundness, alternatives,
assumptions, limitations, sensitivity, calibration, stability, monitoring or inventory.
A validator would return it.

## Why

One body of writing, three readers:

- the **self-learner** working through the course in a GitHub Codespace, with the videos;
- the **validator** who wants a static, versioned document to review;
- the **practitioner** who wants a short book on credit analytics that stands without the
  repo (a reproducible alternative to Siddiqi's *Credit Risk Scorecards*).

## Decisions taken

| Decision | Choice |
|---|---|
| Primary reader | Both learner and validator, as equals: two navigation spines over shared pages |
| Outputs | Site (GitHub Pages), validation PDF, e-book (EPUB + 6×9 print PDF for KDP) |
| Book vs site | Same text, free online. Standard KDP, **not** KDP Select (Select needs exclusivity) |
| Licence | Prose in `wiki/` under **CC BY-NC-ND 4.0** (`LICENSE-CONTENT`); code stays MIT |
| Regulatory frame | **SR 11-7 / OCC 2011-12** spine, with a crosswalk appendix to **OSFI E-23** and **PRA SS1/23** |
| Toolchain | **Quarto**, PDF through **Typst** (no LaTeX); profiles select pages per output |
| Thursday scope | Framework + the Score chapter (D4) in full; students start D5 in the S4 lab |

Structure follows **Diátaxis**: the book is the *explanation* pages, the validation PDF is
the *reference* pages, and the site adds the *tutorials* (course, labs, videos, Codespaces).

## Non-goals

- Replacing or changing `tools/build_doc_pack.py` or `docs/model_doc_pack/`.
  `verify.py::check_doc_pack` expects that file at `stage-5`, and tags never move.
- Any new model, gate or artifact. New *measurements* of the existing scorecard only.
- Numbers typed by hand anywhere in `wiki/`.
- A course platform, accounts, progress tracking or a grader service.
- For Thursday: D5–D8 in full, E1–E10, converting S1–S3 into Course chapters, book
  packaging, and the homework set beyond S2 and S4.

## Public references

Content bar: SR 11-7 / OCC 2011-12; OCC Comptroller's Handbook, *Model Risk Management*
(2021); OSFI E-23; PRA SS1/23; ValidMind's open-source documentation templates and
credit-scorecard demos; Model Cards (Mitchell et al., 2019); Datasheets for Datasets
(Gebru et al.); Siddiqi, *Credit Risk Scorecards* (chapter order).

Course shape: Microsoft's "…for Beginners" repos (repo-as-course with Codespaces);
the Hugging Face LLM course (chapters, video per section, notebook buttons); GitHub Skills
(course inside the learner's repo, automated checks); QuantEcon and d2l.ai (books whose
numbers come from executed code); Molnar, *Interpretable Machine Learning* (tone for the
reason-code chapter); MIT *Missing Semester* (video plus notes per page); Diátaxis.

## 1. Layout and build

```
wiki/                          # main-only, like notebooks/ and workshop/ — in no stage tag
  _quarto.yml                  # shared config: theme, nav, var shortcodes
  _quarto-site.yml             # profile: every page, two sidebars
  _quarto-validation.yml       # profile: Model Documentation spine → validation PDF
  _quarto-book.yml             # profile: explanation chapters → EPUB + 6×9 print PDF
  _variables.yml               # GENERATED from facts.json — never edited by hand
  facts/
    build_facts.py             # computes every number through the module functions
    facts.json                 # committed cache; verify.py recomputes and compares
  course/                      # Course spine: 0 Start here, S1 … S4
  mdd/                         # Model Documentation spine, SR 11-7 order
  explain/                     # explanation pages shared by site and book
  reference/                   # glossary, crosswalk, fact index, video index, changelog
  homework/
    check.py                   # python -m wiki.homework.check <id>
  _includes/                   # video (embed on site ↔ QR + short link in print),
                               # codespace button, gate box
```

### Where the numbers come from

`metadata.json` holds only AUC, KS and the gate for the scorecard. `build_facts.py`
computes everything else **through the modules' own functions** (`predict_score_pd`,
`feature_contributions`, `policy.decide`, `price_population`, `score_population` …),
never from DGP truth or rounded persisted columns. It writes `facts.json` (nested keys,
e.g. `score.auc_holdout`, `score.auc_booked`) and renders `_variables.yml`. Pages write
`{{< var score.auc_booked >}}`. Each fact records its source function and population, so
the reference fact index can print both — no AUC without its population.

Slow facts (the stress refits) are cached in `facts.json`; `verify.py` recomputes the fast
facts every run and the refits only under `--full`.

### Checks added to `verify.py`

Active only where `wiki/` exists (the same guard as the v2 smoke), so every stage tag
reports exactly as before.

1. **Facts are current:** recompute and compare with committed `facts.json`; a mismatch
   fails naming the stale key.
2. **No hand-typed metrics:** lint every `.qmd` and fail on a decimal with ≥3 places or a
   percentage outside a `var` shortcode, with a small explicit allow-list (e.g. the gate
   constants quoted as code, seeds, dates).
3. **Everything resolves:** every `var` key, cross-reference and video ID.

The lint and check script are pure Python and need no Quarto.

### Make targets

`wiki-facts`, `wiki` (preview site), `wiki-pdf`, `wiki-book`. `docpack` unchanged.

### Codespaces

Add the Quarto devcontainer feature. Existing Codespaces need **Rebuild Container**
(same trap as the mermaid extension); the pre-session email says so.

## 2. Navigation spines and chapter tree

Legend: S = site, V = validation PDF, B = book.

**Course tab** (session order; each chapter: video, short read, notebook, lab,
`verify.py` check, agent homework). Site only.

| | Chapter | Draws on |
|---|---|---|
| 0 | Start here: Codespaces, `verify.py`, stage tags, working with an agent | README, CHECKPOINTS |
| 1 | Data and leakage (S1) | 7 chapter videos, notebook 01, S1 lab |
| 2 | The score spine (S2) | 6 chapter videos, notebook 02 |
| 3 | Decisions, price and watch (S3) | 7 chapter videos, notebook 03_04, v2 workbench |
| 4 | Governance: documenting a model with agents (S4) | D4 as worked example; lab drafts D5 |

**Model Documentation tab** (SR 11-7 order).

| § | Chapter | S | V | B |
|---|---|---|---|---|
| D0 | Executive summary, model inventory, risk tiering (pricing listed as a deterministic tool, not a model, with the reason) | ✓ | ✓ | |
| D1 | Platform purpose, intended use, prohibited uses | ✓ | ✓ | |
| D2 | Data: generating process, quality, leakage controls, booked vs applicant populations | ✓ | ✓ | |
| D3 | Model dependencies: the score spine and what breaks if it moves | ✓ | ✓ | |
| D4–D8 | Module chapters: Score · Adjudication · Pricing · Early warning · Line increase | ✓ | ✓ | |
| D9 | Implementation, reproducibility, change control (`verify.py`, tags, gates) | ✓ | ✓ | |
| D10 | Use of AI agents in development: what was delegated, how it was checked | ✓ | ✓ | ✓ |
| D11 | Validation sign-off table, open findings, version | | ✓ | |

**Module chapter template** (every D4–D8):
`.1` Purpose and use · `.2` Data and sample · `.3` Methodology and alternatives ·
`.4` Assumptions · `.5` Performance (discrimination, calibration, stability, benchmark) ·
`.6` Sensitivity and stress · `.7` Limitations and compensating controls ·
`.8` Monitoring plan and triggers · `.9` Gate record

**Explain pages** (S and B; working titles):
E1 Synthetic data you can reason about (from `workshop/reading/S1-data-generation`) ·
E2 The leakage ladder · E3 WoE scorecards and exact reason codes ·
E4 An AUC without its population is incomplete · E5 Ceilings, noise and honest gates ·
E6 From score to decision: the policy layer · E7 Pricing without ML ·
E8 Early warning when the label is noisy · E9 Line increases: incremental economics ·
E10 Documentation a validator accepts.

**Reference:** SR 11-7 → E-23 / SS1/23 crosswalk (appendix to V and B), glossary (V, B),
fact index with source function and population (V), video index, changelog.

Book = E1–E10 + D10 + crosswalk + glossary, ≈150–180 pages at 6×9, with exercises at the
end of each chapter. It must read without the repo; the Course tab links to explanations
rather than repeating them.

## 3. D4 — Business Credit Score (Thursday's deliverable and the template)

| § | Contents | Facts |
|---|---|---|
| 4.1 | Rank-orders the 12,000 applicants on 300–850; the input downstream modules consume (saved model output, never DGP truth); prohibited uses | link to D3 diagram |
| 4.2 | 9,600 / 2,400 split, seed 42; deny-list and enforcement; trains and gates on applicants while the bank lends to the 8,336 booked | row counts, population table |
| 4.3 | WoE binning (optbinning) + logistic, scaled; why not the LightGBM challenger (exact reason codes); CP-vs-MIP solver note | IV per feature, bin tables, **coefficient sign vs expected sign** |
| 4.4 | Monotonic WoE, feature independence, stable population, DGP as ground truth | **max pairwise correlation, VIF** |
| 4.5 | Discrimination: AUC 0.8176, KS 0.4946, **bootstrap 95% interval**; rank-ordering by band; **calibration by band**; **PSI train→test per feature and score**; benchmark vs adjudication LightGBM on the same split; the ceiling table, compared only within a sample | ROC, band table, calibration plot, ceiling table |
| 4.6 | Drop bureau columns → 0.7704 (gate fail); five raw columns → 0.7804; structural zeros → 0.50; revenue proxies → 0.62 | stress table |
| 4.7 | The open findings below, each with a compensating control | |
| 4.8 | PSI thresholds (0.10 watch, 0.25 act), band default-rate tolerance, booked-population AUC tracked beside the gate, redevelopment triggers | monitoring table |
| 4.9 | AUC ≥ 0.78 hard assert in `train.py`, recomputed by `verify.py`; gate history | gate box |

(Figures in this table are the current values; in the chapter every one is a `var`.)

**Open findings, raised by the document itself:**

1. **No out-of-time sample.** Origination is a single cross-section; temporal stability is
   untested. Control: 4.8.
2. **Gate population ≠ lending population.** Booked-only held-out AUC 0.7447, below the
   0.78 gate. Control: report both; future gate on the booked.
3. **Features with no causal role are in the model.** `industry`, `entity_type`,
   `trade_lines` are structural zeros in the DGP yet among the 15 `FEATURE_COLUMNS`.
   Their fitted contribution is **measured by `build_facts.py` before the chapter states
   anything** about it.
4. **Concentrated score distribution.** 1,222 of 2,400 held-out rows (51%) fall in band D,
   limiting discrimination inside it.

**New computations** (fixed seeds, methods written into `build_facts.py` and D4.5):
bootstrap (1,000 resamples, seed 42), PSI (training-split bins), calibration by band, VIF,
the four stress refits (`solver="mip"`), attribution for finding 3.

On the site each sub-chapter is a page, with S2 chapter videos embedded where they fit
(the population reveal, the gate fail). In the PDF it is one chapter with numbered exhibits.

## 4. Homework with AI agents

Each Course chapter ends with 3–4 agent exercises; each Explain chapter a shorter set in
the book. The skill practised: direct an agent, then check it against the repo.

| Kind | The learner… | The trap |
|---|---|---|
| Ask | has the agent explain code or a result, then checks it against `facts.json` | confident paraphrased numbers |
| Build | has the agent write code or documentation that must pass `verify.py` / the lint | relaxing a gate fails the exercise |
| Audit | has the agent review a branch or page with a planted defect | defects are real ones from this repo's history |
| Catch the agent | finds the wrong claim in a supplied transcript | trains scepticism |

Starter set:

- **S1** — H1.1 Ask: which columns leak (check vs `LEAKAGE_COLUMNS`). H1.2 Build: the
  ladder's middle rung, must measure 0.8326. H1.3 Catch: "leaking true PD gives ≈1.0".
- **S2** — H2.1 Build: refit without bureau columns; the gate fails at 0.7704 and is
  documented, not tuned. H2.2 Catch: "AUC 0.82" — on which population? H2.3 Ask: why
  `profit_margin` has the largest coefficient and 0.3% of variance.
- **S3** — H3.1 Build: move a threshold through `policy.decide`, explain the mix shift.
  H3.2 Catch: "mispricing is worst in band D" (it is AAA/A). H3.3 Audit: a what-if that
  re-tiers from the rounded `prob` column.
- **S4** — H4.1 Build: draft D5 from the template (lint clean, all `var`s resolve, nine
  sub-chapters). H4.2 Audit: agent as validator on D4, compared with the four findings.
  H4.3 Build: extend the crosswalk for one module.

Thursday needs S2 and S4 fully built; S1 and S3 follow.

**Self-check:** `python -m wiki.homework.check <id>` asserts facts, files, lint and an
unchanged gate in the diff; it recomputes, never trusts a pasted number. Exercises assume
`main`. **Solutions:** collapsed callouts on the site (the prompt that worked, a transcript
excerpt, where the agent first went wrong); the book prints exercises with a QR code to
solutions. **Agents:** prompt cards in `workshop/prompt-cards/` are agent-agnostic; every
exercise is tested with GitHub Copilot (free in Codespaces) and Claude Code (paid).

## 5. S4 session, publishing, verification

### Run of show (90 min; room starts on `main`)

| Time | Block | Notes |
|---|---|---|
| 0:00 | Would this pass validation? Current pack vs SR 11-7 checklist | Poll A |
| 0:08 | Wiki tour: two tabs, one source, three outputs, the facts layer | live: change a fact, the lint fails |
| 0:20 | D4 walkthrough: template, then the four open findings | RECOVERABLE |
| 0:38 | Lab H4.1: pairs draft one D5 sub-chapter each with an agent; `check H4.1` passes | PROTECT, 30 min |
| 1:08 | Validator review live (H4.2); the room judges which findings are real | |
| 1:20 | Publishing and continuing self-paced | Poll C (not shown) |
| 1:27 | Close | |

The lab works without Quarto (lint and check are pure Python); only preview needs it.
Materials: rewrite `S4.md` / `S4-lab.md` (current S4 deck is from the five-session plan),
new `S4-run-of-show.md`, `S4-polls.md`, pre-session email with the rebuild step.

### Publishing (nothing public without Yan's go-ahead)

- **Site:** `quarto-dev/quarto-actions` workflow → GitHub Pages on push to `main` (Yan
  enables Pages). Optional for Thursday.
- **Validation PDF:** `make wiki-pdf`, attached to the `v1.5` release, stamped with tag,
  date and SHA-256 of every artifact it cites.
- **Book:** after the course — cover, ISBN choice, Kindle Previewer + `epubcheck`, 6×9
  interior, `LICENSE-CONTENT`, README licence note.

### Verification before tagging v1.5 (clean clone, fresh venv, per CLAUDE.md)

1. `stage-0`…`stage-5` report exactly as before; `main` passes including the wiki checks.
2. `build_facts.py` reproduces `facts.json` byte for byte; lint clean; all references resolve.
3. All three profiles render; every PDF exhibit read against `facts.json`; site link check
   and a browser check at phone width in both themes.
4. `check H4.1` passes on a worked D5 sub-chapter and fails on a planted hand-typed number
   and on a relaxed gate.
5. Grep the diff for `@`; clear notebook outputs.

### Schedule

| Day | Work |
|---|---|
| Sun 27 | Spec; implementation plan |
| Mon 28 | Install Quarto (with approval); framework skeleton; `build_facts.py` and new computations; measure finding 3; D0–D3 stubs |
| Tue 29 | D4 in full; homework checks (S2, S4); devcontainer feature; **pre-session email with the rebuild step** |
| Wed 30 | S4 deck, lab, run of show, polls; dry run; clean-clone sweep; `v1.5` prepared, not pushed |
| Thu 1 Oct | Session |

## Risks

- **Stress refits are slow or trip optbinning.** Mitigation: `solver="mip"` everywhere,
  cached in `facts.json`, recomputed only under `--full`.
- **Finding 3 turns out negligible or large.** The chapter states what is measured; the
  finding's wording is written after the number exists.
- **Codespaces not rebuilt by the room.** The lab does not depend on Quarto.
- **Writing load on Tue 29.** D0–D3 stay stubs for Thursday; D4 is the only full chapter.
