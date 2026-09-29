# Prompt Card HW-H2.2 — Catch an AUC Without Its Population (Session 2 homework)

**Kind: Catch.** You are the reviewer. First let the agent answer the question the way
anyone would; then catch what is missing and send it back.

**Goal.** An answer in which every AUC names the population it was measured on, and which
includes the scorecard's AUC on the held-out applicants the bank actually books.

---

## Round 1 — the question as a manager would ask it (send as is)

> In the `banking-analytics-workshop` repo on `main`, how good is the committed Business
> Credit Score at ranking risk? One paragraph.

Read the reply before you go on. Mark every AUC in it that does not say *on whom*.

## Round 2 — the brief (copy, fill the blank, send)

> Reviewer: **[YOUR NAME]**. Run Python with `.venv/bin/python` from the repo root.
>
> 1. For every AUC in your last answer, name the population it was measured on.
> 2. Score all applicants with `score.src.predict.predict_score_pd`. Recreate the scorecard's
>    held-out split exactly as `score/src/train.py` does (`test_size=0.2`,
>    `random_state=SEED`, `stratify=y`, on `shared/data/raw/businesses.parquet`).
> 3. On that held-out split, report the AUC for: all applicants; booked applicants only
>    (`booked == 1`); rejected applicants only. Give the row count of each.
> 4. Say which of these the committed gate is measured on, and which one matters for the
>    loans the bank holds.
> 5. Write the answer to `wiki/homework/_answers/H2.2.md`. Every AUC in it names its
>    population in the same sentence.

---

## What "done" looks like

- Three AUCs, each with a population and a row count, all on the held-out split.
- A sentence saying the gate is measured on all applicants, not on the booked.

## Check it

```bash
python -m wiki.homework.check H2.2
```

The check recomputes the booked-only AUC and fails any AUC in your answer whose sentence
(or, in a table, whose row or header row) names no population. It counts as an AUC any
number that matches one of the recomputed AUCs to four decimals; a KS is not checked.

## The trap

- **The in-sample booked AUC.** Filtering the whole book to `booked == 1` and computing
  the AUC gives a higher number than the held-out booked AUC, because most of those loans
  were in the training data. It looks like the right answer and it names a population — the
  wrong one. Same split, then filter.
- **"The AUC is …"** An AUC without a population is not wrong, it is incomplete — and an
  incomplete number is how a gate that holds on applicants gets quoted as holding on the book.
