# Prompt Card HW-H4.1 — Draft One Part of D5 (Session 4 lab and homework)

**Kind: Build.** You are the author of record. The agent drafts one part of D5, Loan
Adjudication; you decide whether a validator would accept it.

**Goal.** One sub-chapter of D5 — say `performance` — that follows the template, cites every
number as a fact and passes the lint. Pairs can take different parts and work in parallel.

---

## The brief (copy, fill the blanks, send to your agent)

> You are in the `banking-analytics-workshop` repo on `main`, at the repo root. Run Python
> with `.venv/bin/python`. Author: **[YOUR NAME]**. Part: **[ONE OF: purpose, data,
> methodology, assumptions, performance, sensitivity, limitations, monitoring, gate]**.
>
> **Task:** draft that part of D5, the Loan Adjudication chapter of the model documentation.
>
> 1. Copy `wiki/mdd/_template/<part>.qmd` to `wiki/mdd/adjudication/<part>.qmd`. Read the
>    comment in it: it says what the part must cover.
> 2. Read D4's version of the same part (`wiki/mdd/score/<part>.qmd`) as the worked example,
>    and `wiki/mdd/adjudication/index.qmd` for what D5 covers.
> 3. Every number is a fact: `{{< var key >}}`, with keys taken from
>    `wiki/facts/facts.json`. Never type a number into the prose — not a metric, not a
>    percentage. If a fact you need does not exist, write "not yet measured" and list the
>    missing fact at the end of your reply; do not invent a value.
> 4. Name the population beside every metric.
> 5. Run `.venv/bin/python -m wiki.tools.lint wiki/mdd/adjudication/<part>.qmd` and fix
>    everything it reports. Do not edit `wiki/tools/lint_allow.txt` to make it pass.
> 6. Change no other file.

---

## What "done" looks like

- At least 150 words of your own, beyond the template's comment.
- Every metric a `{{< var … >}}`; every one names its population.
- The lint reports 0 problems. What the page claims is true of the code — read two of its
  claims against `adjudication/src/` yourself.

## Check it

```bash
python -m wiki.homework.check H4.1 --part <part>
```

Without `--part` it checks all nine parts, which is the homework's full chapter.

## The trap

- **Numbers that look like words.** "The top 20% of applicants" is a hand-typed number; the
  lint rejects it. Rephrase, or add the fact.
- **Borrowed facts.** A `score.*` key renders the scorecard's number, not the adjudication
  model's. A draft can lint clean and still quote the wrong model.
- **Invented facts.** An agent short of a fact will describe it as if it had one. Anything
  the facts do not contain is "not yet measured".
- **Allow-listing.** Adding a literal to `lint_allow.txt` makes the lint quiet and the page
  untraceable.
