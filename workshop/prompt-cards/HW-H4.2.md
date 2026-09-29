# Prompt Card HW-H4.2 — Turn the Agent into a Validator (Session 4 homework)

**Kind: Audit.** The agent reviews D4, the Business Credit Score chapter, as an independent
validator would. You then mark its review against the findings D4 raises about itself.

**Goal.** At least three findings about the model (not about the prose), each with evidence
that exists in the repository.

---

## The brief (copy, fill the blank, send to your agent)

> You are in the `banking-analytics-workshop` repo on `main`, at the repo root. Run Python
> with `.venv/bin/python`. Reviewer: **[YOUR NAME]**.
>
> **Task:** act as an independent model validator reviewing the Business Credit Score.
>
> 1. Read the model: `score/src/` and `score/models/metadata.json`. Read the documentation:
>    `wiki/mdd/score/`, **except `limitations.qmd` — do not open it yet.**
> 2. Raise findings about the model and how it is used: weaknesses in data, method,
>    performance, stability or controls that a validator would require the developer to
>    answer. Not typos, not style.
> 3. Write each finding in this form, one per paragraph, to
>    `wiki/homework/_answers/H4.2.md`:
>
>        F1: <the finding, in one or two sentences>
>        Evidence: <a fact key from wiki/facts/facts.json, or a repo path>
>
>    The evidence is a single fact key (such as `score.pop.booked.auc`) or a file path from
>    the repo root. No page anchors, no line numbers, no prose.
> 4. Do not change any file other than the answer.

---

## What "done" looks like

- Three or more findings, each about the model, each with one piece of evidence that exists.
- At least one finding you did not see coming.

## Check it

```bash
python -m wiki.homework.check H4.2
```

Then open `wiki/mdd/score/limitations.qmd` (D4.7) and compare. Which of its findings did
the agent miss, and why — did it not look, or could it not have seen it? Which of the
agent's findings does D4.7 record only as an observation, or not at all? Would you raise it?

## The trap

- **Grading the documentation as evidence.** "The chapter says so" is not evidence against
  the model. Point at a fact or at code.
- **Findings about the writing.** A validator's finding is something the developer must
  fix or control, not a sentence to rephrase.
- **Reading the answers first.** An agent that has read D4.7 will return D4.7. Keep it closed
  until the review is written.
