# Lab S3_4 — From Adjudication to Pricing to Portfolio Action (80 min)

**Checkpoint:** the completed lifecycle artifacts on `main` · one score spine, four decisions.

This lab replaces the separate S3 and S4 lab flows. You will use the combined notebook
[`notebooks/03_04_adjudication_pricing_monitoring.ipynb`](../../notebooks/03_04_adjudication_pricing_monitoring.ipynb)
as your study guide, then use the existing Python commands and apps to produce evidence.

> First, fetch tonight's material. The combined notebook and the v2 portal were added
> after you cloned:
>
> ```bash
> git stash -u && git checkout main && git pull
> ```
>
> Then `make stop`, then `python verify.py` so you know which checkpoint you have. If you
> would rather stay on a stage tag, it must be `stage-4` or later:
> `git checkout stage-4 && git checkout main -- app notebooks workshop`. Do not do this at
> `stage-3`, because its models cannot load `main`'s portal.

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
4. Start the portal and open **both** versions:

   ```bash
   make run    # v1: http://localhost:8100    v2: http://localhost:8100/v2
   ```

   **v1** is the original portfolio page. **v2** is the loan-level workbench: filter the
   book (decision, score band, industry, region, booked, EWS tier, mispriced, line-increase
   offer) or type an ID such as `BIZ100000` into the ID box, then read the loan in four
   tabs: **Decision**, **Pricing & Profitability**, **Early Warning** and **Line
   Increase**. Sliders and draggable cutoffs run a *what-if* on the server using the same
   module function as the batch pipeline. Nothing is saved; click a tab's name to return
   to the committed values.

### v1 and v2 — what an AI agent changed

v2 was built by an AI agent from one prompt, under review, beside the untouched v1. It
adds **no new analytics**: every number comes from the module that owns it, and with the
sliders untouched a what-if reproduces the batch result exactly. Keep both tabs open as you
work. For each section below, note one question v2 answers that v1 cannot, and one thing
you would still want to check in the code rather than trust on screen.

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

Reference mix: **Approve 30.8% / Refer 36.8% / Decline 32.4%**. That is the model's
**held-out 2,400** applicants. v2's book mix covers **all 12,000** (Approve 3,760 · Refer
4,229 · Decline 4,011, i.e. 31.3 / 35.2 / 33.4%). Both numbers are right; always name the
population behind a percentage.

**In v2 (Decision tab).** Each rule is listed whether it fired or not, with its value
against its threshold, next to the PD zone and both model rationales (scorecard points and
SHAP). Try `BIZ100000` (Approve: the model decided), `BIZ100003` (Refer: PD in the Approve
zone, a refer override fired) and `BIZ100008` (Decline: PD in the Approve zone, a DSCR
knockout fired). Then **drag `t_low` to zero** and read the book mix. Why do all 3,760
Approves become Refers while the Decline count does not move?

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

**In v2 (Pricing & Profitability tab).** Filter **Mispriced = yes** and a score band, then
read one loan's waterfall in dollars and bps: interest income, cost of funds, expected
loss, operating cost, tax, allocated equity. Two things to try:

- `BIZ103012` earns an ROE of **14.997%** against a **15%** hurdle. How far below the
  hurdle-clearing rate is its quoted rate, and should a committee care?
- **Drag LGD from 0.45 to 0.90.** The share of the book clearing the hurdle falls from
  **30.4% to 4.7%**. Whose assumption is LGD, and who should sign it off?

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

**In v2 (Early Warning tab).** Filter **EWS tier = High**, open one account, and read its
24-month history, its probability against the tier cutoffs, and each trigger broken into
the clauses that fired it. Then open `BIZ106189`: its `RISING_UTILIZATION` trigger fires
because utilization drift is **0.15000000000000013**, just over **0.15**. What would you
ask the model owner to change, and would you have caught it from the watchlist alone?

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
3. In v2 (Line Increase tab), compare `BIZ100132` (an offer: all four gates pass, $71,000)
   with `BIZ100024` (a **$2,000** recommended amount that is **not** an offer). Which gates
   fail? **1,243** accounts have a positive amount, but only **95** are offers. A
   recommended amount is not an offer.
4. Open `BIZ100375`. Its binding cap is exactly **$54,500** and its amount is **$54,000**,
   because Python's `round()` sends an exact half to the *even* thousand. Is that a policy
   choice or an accident of the language? Where would you document it?
5. Compare the offered cohort with the book: cohort PD **0.036** vs book **0.117**,
   cohort utilization **0.837** vs book **0.471**, and aggregate incremental ROE
   **0.215**. Explain why each comparison matters to a validator and a business owner.

## Integrated lifecycle decision — 10 min

Choose one business and walk it through the notebook and **v2**, whose four tabs are these
four questions for one account:

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
