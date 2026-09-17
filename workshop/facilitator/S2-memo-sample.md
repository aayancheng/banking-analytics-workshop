# Lab 2, Part A — a sample memo (facilitator's answer key)

**Facilitator notes. Not student-facing until after the lab.** This is what a good one-page
answer to the three Part A decisions looks like, with every number recomputed from the
`stage-2` data on the notebook's own split (`SEED`, 80/20, stratified). Use it to grade the
homework memos, to cold-call against, or hand it out after S2 as a worked example. The
leakage table in decision 3 is the part students most often get vague about — it is the
reason this file exists.

Numbers below: `dscr` WoE with the lab's six edges; the leak columns cut into six quantile
bins; the IV scan is the notebook's `iv_quick` (ten quantile bins, training split). Book
default rate on the training split: **16.7%**.

---

## Memo — Lab 2, Part A · scorecard binning decisions

**Reviewer:** *(student)* · **Checkpoint:** `stage-2` · **Card under review:** the committed
15-feature scorecard, held-out AUC 0.8176 against a gate of 0.78.

### Decision 1 — granularity: six bins on DSCR, not four

With the lab's six edges (0.9 / 1.1 / 1.3 / 1.6 / 2.0) DSCR has **IV 0.209**; with four
(1.0 / 1.25 / 1.5) it drops to **0.184**, a 12% loss of information for two fewer rows in the
card. What the coarser cut destroys is the cleanest bin: above 2.0× coverage the default rate
is **6.6%** (WoE +1.04); merged into "above 1.5×" it becomes **11.0%** (WoE +0.49). The
optimiser found the covenant on its own — cuts near 0.7, 1.0 and 1.23 — so the shape is
economics, not noise.

The check that makes six defensible: the smallest cell is 1,111 borrowers and 245 defaults.
Every bin is monotonic in the direction coverage should run, and no bin is thin enough to be
one quarter's bad luck. I would go to seven only if a bin above 2.0 still had 50+ defaults in
it; it does not (74 in total).

### Decision 2 — the drop: `trade_lines`

Bottom of the IV scan, training split, ten quantile bins:

| feature | IV |
|---|---|
| public_records | 0.013 |
| profit_margin | 0.012 |
| industry | 0.009 |
| entity_type | 0.003 |
| **trade_lines** | **0.003** |

`trade_lines` is the lowest of the fifteen, an order of magnitude under the 0.02 "useless"
line, and it has no story: no covenant references it, no underwriter would defend a decline
on it, and Session 1's data-generation note lists it among the columns the generator gives
**no causal role at all**. Removing it costs the card nothing — Part B will show the gate
still passes — and buys one fewer line to explain in an adverse-action letter.

Two things I am *not* dropping, and why. `industry` (0.009) looks the same on this chart but
is the Session 1 teaching case — a tidy 3.3-point spread across sectors with an IV of 0.006;
it goes next, once I have shown someone the chart and the number side by side. And
`profit_margin` (0.012) is a trap in the other direction: low IV because its spread is tiny,
not because it is noise — the generator uses it. Low IV says "little to gain here", not "no
mechanism here". I keep it and put the question to the validator.

### Decision 3 — the smell test: what leakage looks like in a WoE table

Session 1 gave the hint: a model that "peeked" at the true PD went from AUC 0.72 to **0.83**
and looked like a breakthrough. Here is that same column in the tool we are using tonight,
next to an honest feature and next to a proxy that *isn't* a leak:

| | `dscr` (honest) | `requested_amount` (proxy, not a leak) | `pd_default_origination` (leak) |
|---|---|---|---|
| IV | 0.21 | 0.10 | **1.58** |
| WoE span, best to worst bin | −0.64 … +1.04 | −0.46 … +0.55 | **−1.69 … +2.67** |
| default rate, best → worst bin | 6.6% → 27.5% (4×) | 10.4% → 24.1% (2×) | **1.4% → 52.0% (37×)** |
| worst bin against the 16.7% book rate | 1.6× | 1.4× | **3.1×** |
| single-variable held-out AUC | 0.64 | 0.60 | **0.84** — beats the whole 15-feature card (0.82) |
| mechanism | coverage → repayment | borrowed from revenue (rank-corr 0.85) | *it is the label's own driver* |

Five patterns, in the order I would check them:

1. **IV off the scale.** The best honest feature in this book is 0.22. Anything above ~0.5 is
   not "strong", it is a question. 1.58 is seven times the best honest feature.
2. **A bin with almost no defaults and a bin with more than half.** Honest features spread the
   book from 7% to 28%. A leak spreads it from 1% to 52% — the worst bin alone holds 832 of
   the 1,605 training defaults.
3. **Too clean.** Monotonic *and* steep across every quantile bin, no plateau, no wobble.
   Real risk drivers are monotonic but shallow: DSCR's WoE moves 1.7 log-odds end to end;
   the leak moves 4.4.
4. **One column outperforms the whole card.** DSCR alone is 0.64; fifteen honest features are
   0.82; this one column alone is 0.84. A single feature that beats the model is not a
   discovery — it is the answer key.
5. **No economic mechanism, or the wrong timing.** Ask of every candidate: *would this value
   exist, unchanged, at the moment the score is computed?* `risk_based_rate` (IV 1.60, AUC
   0.84, a near-copy of the PD column) is set at pricing, after adjudication. `booked` is the
   decision itself. `deterioration_next_6_12mo` is the future. None of them exist at scoring
   time, whatever their IV says.

And the pattern that is **not** leakage, because students over-call this one:
`requested_amount` has real, stable, monotonic signal (IV 0.10) and no causal role — it
inherits everything from `annual_revenue`. That is redundancy, not leakage. The test that
separates them: a proxy's contribution collapses once its parent is in the card; a leak's
contribution collapses for nothing. Drop a proxy for parsimony; drop a leak because the
number it produces is fiction.

Two columns telling the same story is the last tell. `pd_default_origination` and
`risk_based_rate` have the same shape, the same IV and the same AUC, and no shared economics
except that one was computed from the other. When two features agree that closely, one of
them was derived from the label's driver.

### The one question I would fear from a validator

*"Your fifteen features were chosen on the same 12,000 applicants the AUC is measured on.
What does the gate read on the 8,336 the bank actually booked?"* Section 7 of the notebook
answers it — 0.8176 becomes 0.7447 — and that is the fourth clause of the homework memo.

---

## Grading notes

- **Decision 1** earns full marks for a *number* (IV before and after) plus a *cell-size
  argument*; "six looks smoother" is not a decision.
- **Decision 2** needs the drop *and* the evidence *and* one feature they chose not to drop
  with a reason. The `profit_margin` point separates students who read the S1 note from
  students who read the chart.
- **Decision 3** is the one to push on. A memo that says "IV too high" has one of five
  patterns. The timing question (*does it exist at scoring time?*) and the proxy-vs-leak
  distinction are what a validator will actually ask; a memo that names them is ready for S5.
- Every number here is reproducible in under a minute in §6 of the notebook: set `VAR` to any
  column in `businesses` — including the deny-listed ones, which is the whole point of
  letting students see them once.
