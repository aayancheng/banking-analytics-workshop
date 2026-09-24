# Lab S3_4 — From Adjudication to Pricing to Portfolio Action (80 min)

**Checkpoint:** the completed lifecycle artifacts on `main` · one score spine, four decisions.

This lab replaces the separate S3 and S4 lab flows. You will use the combined notebook
[`notebooks/03_04_adjudication_pricing_monitoring.ipynb`](../../notebooks/03_04_adjudication_pricing_monitoring.ipynb)
as your study guide, then use the existing Python commands and apps to produce evidence.

> First command: `make stop`. Then run `python verify.py` so you know which checkpoint you
> have. The notebook and workshop materials live on `main`; if a stage jump made them
> disappear, restore them with `git checkout main -- notebooks workshop` without changing
> your current stage.

## The lifecycle you are about to trace

```text
application data + score spine
            |
            v
   adjudicate: approve / refer / decline
            |
            v
   price: quoted rate -> hurdle -> recommended rate
            |
            v
   monitor: deterioration probability + named triggers
            |
            v
   manage: line increase only when risk and economics clear together
```

The central question is not “is the model accurate?” It is:

> What decision does this analysis support, what rule constrains it, and what evidence
> would make the decision defensible?

### Two ways to complete the lab

**Manual track:** run the commands in each section, inspect the outputs, and answer the
questions in your notes.

**Agent track:** use the applicable prompt cards from the original labs (`AC-3a` for
adjudication and `AC-4a`/`AC-4b` for monitoring and line management). The review standard
is the same: verify the agent’s reported numbers against the generated artifacts and check
that it did not silently retune a policy threshold.

## Before you start — 5 min

1. Open the combined notebook and skim its flowchart and section headings.
2. Run:

   ```bash
   make stop
   python verify.py
   ```

3. Keep one page of notes with four columns: **decision**, **model signal**, **business
   rule**, and **evidence**. Add one row for the account you follow through the lab.

## Adjudication — 15 min

Open the notebook’s **Section 1 — Adjudication** before running the app. The notebook
separates a score from a decision: hard knockouts are applied first, PD zones determine
the model outcome next, and refer overrides can make an otherwise acceptable case go to
manual review.

### Run the existing adjudication code

```bash
make train-adjudication
make run                 # http://localhost:8100
```

### What to notice

1. Read three decision trails: one **Approve**, one **Refer**, and one **Decline**. For
   each, write whether the final result came from the model or a rule.
2. Count hard-rule knockouts among Declines. Estimate what share of decisions the model
   actually made after policy rules were applied.
3. Find one applicant where the challenger and the scorecard disagree materially. Which
   decision would you defend, and what would be the cost of being wrong?

Reference mix: **Approve 30.8% / Refer 36.8% / Decline 32.4%**.

Do not treat the mix as the answer by itself. A bank also needs reason codes, policy
traceability, and a clear answer to “why did this applicant receive this outcome?”

## Pricing — 15 min

Read the notebook’s **Section 2 — Pricing**. Pricing converts the same risk estimate into
loan economics:

- **ROE** asks how much return the loan generates relative to the capital assigned to it.
- **RAROC** asks whether the return compensates for the risk-adjusted capital consumed.
- The **hurdle rate** is the minimum acceptable return. The **recommended rate** adds the
  business’s pricing buffer or target margin. A quoted rate can therefore be acceptable,
  borderline, or economically unattractive even when the borrower is approved.

### Run the existing pricing code

```bash
make price
python verify.py
```

Use the notebook’s parallel examples to compare:

1. a loan below the hurdle;
2. a loan above the hurdle but below the recommended rate; and
3. a loan above the recommended rate.

Record the business action for each case: decline or reprice, approve with an exception,
or proceed at the recommended economics.

### What to notice

| Pricing evidence | Reference result | Your interpretation |
|---|---:|---|
| Share clearing the 15% hurdle | **30.4%** | How much of the book earns its capital? |
| Median ROE at quoted rate | **10.9%** | Is the typical quoted loan attractive? |
| Mispriced exposure | **$1.28B** | How much balance-sheet value is at risk? |

Answer these questions:

1. Which score band has the worst mispricing rate? Check whether the AAA result surprises
   you.
2. Explain the AAA result using the pricing waterfall: what cost floor can a low quoted
   rate fail to cover even when PD is tiny?
3. Choose one client segment (band × industry) to call first about repricing. Defend the
   choice using exposure, win-back odds, and relationship risk.

## Monitoring — 20 min

Read **Section 3 — Monitoring** before training. The deterioration model is trained on
behavior after origination, not just the original application. Its features include
utilization drift, deposit decline, delinquency or days-past-due behavior, overdrafts,
business score, and other account-level trends. The target is whether the account
deteriorates in the next 6–12 months.

### Run the existing monitoring code

Before training, write down an AUC that would make you proud. Do not change it later.

```bash
make train-ews
python workshop/labs/oracle_ceiling.py
```

Reference monitoring output:

- AUC: **0.662**
- PR-AUC: **0.308**
- top-decile capture: **21.6% = 2.16×** the base-rate benchmark

### What to notice

1. Compare the model with the oracle ceiling. Was your original AUC expectation achievable
   on this data?
2. Explain why the held-out top-decile capture is about **21%**, while the in-sample value
   can be about **54%**. The training sample lets the model exploit patterns that do not
   repeat for unseen accounts; this is a warning about overfit and sample noise, not
   evidence that the held-out result is broken.
3. Re-grade the model against the honest gate: capture at least **2×** and PR-AUC above
   the **18.0% base rate**. Is the watchlist useful even though AUC is not spectacular?
4. Inspect the top-10 watchlist. Every account should have **named triggers**, such as
   `HIGH_UTILIZATION` or `DEPOSIT_DECLINE`, alongside a probability. Explain why a bank
   needs both a ranked signal for prioritization and named reasons for a relationship
   manager’s call and for model validation.

## Line increases — 15 min

Read **Section 4 — Line increases**. Growth is offered only when risk appetite, a real
dollar amount, and incremental economics all clear together.

### Run the existing line-management code

```bash
make train-line-increase
python verify.py
make run
```

The **four simultaneous gates** are:

```text
deterioration probability >= 0.3121
AND origination PD <= 0.0741
AND recommended amount > $0
AND incremental ROE >= 15%
```

The recommended amount is capped by all three limits:

```text
min(
    amount needed to reach 65% utilization,
    50% of current credit limit,
    30% of annual revenue - current credit limit
)
```

### What to notice

1. Trace one accepted offer. Point to evidence for all four gates.
2. Trace one rejected candidate. Identify the first gate that fails and explain why the
   other three gates cannot rescue the offer.
3. Compare the offered cohort with the book: cohort PD **0.036** vs book **0.117**,
   cohort utilization **0.837** vs book **0.471**, and aggregate incremental ROE
   **0.215**. Explain why each comparison matters to a validator and a business owner.

## Integrated lifecycle decision — 10 min

Choose one business and walk it through the portal and notebook:

1. What score and policy rules produced the adjudication outcome?
2. At what quoted rate would the loan clear the hurdle? Is the recommended rate higher?
3. What is the deterioration probability, risk tier, and named trigger set?
4. Is a line increase offered? Which of the four gates controls the result?

### Decision memo

Write a short memo titled **“Defend this lifecycle decision.”** Include:

- the adjudication outcome and whether a model or rule determined it;
- the pricing result, including quoted rate, hurdle, and ROE/RAROC interpretation;
- the monitoring signal and why the held-out metric is the evidence you trust;
- the line-increase verdict and the gate that mattered most; and
- one business trade-off and one control you would require before deployment.

The goal is not to produce the highest metric. The goal is to connect a number to a
decision, a rule, and an accountable next action.

## Converge — 5 min

```bash
python verify.py
python verify.py --json
```

Bring your memo and four-column notes to the debrief. Be ready to explain one place where
the model helped, one place where policy overruled it, and one place where economics
changed the business answer.
