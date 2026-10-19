# Prompt Card HW-H3.2 — Catch: "Mispricing Is Worst in Band D" (Session 3 homework)

**Kind: Catch.** You are the reviewer. Below is an agent's answer to a pricing-desk question.
It sounds like risk management. Find what is missing, have it measured, and correct it.

**Goal.** An answer in which every "worst" says by what measure, with the band that is worst
by share of loans and the band that is worst by money, both recomputed.

---

## The transcript (read it before you go on)

> Q: Where in the booked book is mispricing worst?
>
> A: Mispricing is worst in band D. That is where the riskiest loans are, and band D holds
> about $354M of loans priced below the hurdle, so it is where the pricing desk should start.

Mark the claim you can check, and the word that hides a choice.

## The brief (copy, fill the blank, send)

> You are in the `banking-analytics-workshop` repo on `main`, at the repo root. Run Python
> with `.venv/bin/python`. Reviewer: **[YOUR NAME]**.
>
> 1. Price the booked book with `pricing.src.portfolio.price_population()` and summarise it
>    with `portfolio_summary`.
> 2. For each score band, report the number of loans, the share mispriced, and the mispriced
>    EAD (the sum of `ead` over loans with `mispriced` true).
> 3. Which band is worst by share of loans mispriced? Which by mispriced EAD? Are they the
>    same band? Why not?
> 4. Write the corrected answer to `wiki/homework/_answers/H3.2.md`. Every "worst" in it says
>    by which measure.

---

## What "done" looks like

- A table by band: loans, share mispriced, mispriced EAD.
- The worst band by share, with its share; the worst band by EAD, with its amount.
- One sentence on which measure answers which business question.

## Check it

```bash
python -m wiki.homework.check H3.2
```

The check prices the book itself. It wants the band with the highest mispriced share named
beside its share and a sentence of your own (not only a table) saying it is worst by share;
the band with the most mispriced EAD named beside its amount (in millions, in billions or as
the full figure); and no sentence calling that band worst by share, "by every measure", or
without a money measure. Quoting the transcript's claim is fine.

## The trap

- **"Worst" without a measure.** By share and by money, different bands lead. A sentence that
  says "worst" and names no measure is how a session ends up on the wrong band — Session 3's
  recording carries a correction card at exactly this point.
- **The story fits the wrong answer.** "Riskiest band, most mispricing" sounds right. Measure
  first.
- **What the share means here.** The quotes are generated without a capital charge, so the
  level of mispricing is a property of the data, not of a pricing desk — see D6.7, finding 1.
