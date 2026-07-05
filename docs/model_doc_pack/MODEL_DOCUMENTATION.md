# Model Documentation Pack — SME Lending Decision Platform

Workshop build. Synthetic data throughout (seed 42: 12,000 applicants,
24-month behavioral panel). Every metric below is recomputed from committed
artifacts by `python verify.py` — this document cites, it does not assert.

## Data & leakage controls

- Generator: `shared/data_generator.py`, deterministic, seed 42. Data-quality report:
  `reports/data_quality.md`.
- Deny-list (`shared/config.py::LEAKAGE_COLUMNS`) — columns that exist in the data but may
  never enter a feature matrix; enforced by assertions in every feature-engineering module
  and by `tests/test_leakage.py`:
  - `pd_default_origination`
  - `default`
  - `risk_based_rate`
  - `booked`
  - `deterioration_next_6_12mo`
  - `line_increase_good`
- Score-reuse contract: downstream models consume the SAVED scorecard's output
  (`score/src/predict.py`), never the generator's true PD.

## Business Credit Score

- WoE binning + logistic scorecard (optbinning), scaled 300-850; reason codes are exact
  WoE x coefficient contributions (deliberately not SHAP).
- Held-out **AUC 0.8176** (gate >= 0.78), KS 0.4946.

- Train rows: 9,600  Test rows: 2,400
- **AUC:** 0.8176  (gate >= 0.78)  |  **KS:** 0.4946

### Default rate by score band (test)

| band   |   count |   mean |
|:-------|--------:|-------:|
| D      |    1222 | 0.2823 |
| C      |     438 | 0.0708 |
| B      |     366 | 0.0437 |
| A      |     182 | 0.0275 |
| AAA    |     192 | 0.0208 |

## Loan Adjudication

- LightGBM PD challenger + vectorized policy layer (hard knockouts -> PD zones -> refer
  overrides); SHAP reason codes + rule hits per applicant.
- Held-out **AUC 0.8096** (gate >= 0.78), top-20% lift
  **2.8554x** (gate >= 2.0).

- Train rows: 9,600  Test rows: 2,400
- **AUC:** 0.8096  (gate >= 0.78)
- **Top-20% lift:** 2.86x  (gate >= 2.0)

### PD-zone thresholds (calibrated)

- t_low (Approve <=): 0.0955
- t_high (Decline >=): 0.4943

### Decision mix (test split)

- Approve: 30.8%
- Decline: 32.4%
- Refer: 36.8%

- Files with >=1 policy rule hit: 994

## Pricing & Profitability

- No ML: deterministic ROE/RAROC engine (`pricing/src/engine.py`), 6 machine-precision
  identity tests. Booked book priced against the 15% ROE hurdle.
- **30.4%** of 8,336 booked loans clear the hurdle at the
  quoted rate; median ROE 10.9%; **$1,276,148,000
  mispriced EAD**.

- Booked loans priced: 8,336
- Clear ROE hurdle at quoted rate: 2,534 (30.4%)
- Median ROE (at quoted): 10.9%
- Mispriced EAD: $1,276,148,000

### Mispriced rate by score band

- A: 73.1%  (n=845)
- AAA: 80.4%  (n=822)
- B: 70.9%  (n=1,497)
- C: 65.9%  (n=1,851)
- D: 67.5%  (n=3,321)

## Early Warning

- LightGBM on 24-month panel trend features + 5 named triggers + calibrated High/Med/Low tiers.
- **Honest gate** (the label is noise-capped by construction): top-decile capture
  **21.6% = 2.1595x**
  (gate >= 2x), PR-AUC **0.308** > base rate 0.1802;
  AUC 0.6622 reported, NOT gated.

- Train 6,668 / Test 1,668  | base rate 18.0%
- **Top-decile capture:** 21.6%  =  **2.16x** lift  (gate >= 2x)
- **PR-AUC:** 0.3080  (gate > base rate 0.1802)
- **AUC:** 0.6622  (reported; not gated — see note below)
- Risk tiers: High >= 0.5073, Medium >= 0.1649

> **Gate note (Option B):** the synthetic `deterioration_next_6_12mo` label is noise-capped (logit noise + Bernoulli draw → oracle ceiling ~0.70 AUC), so the gate is set to what the data genuinely supports: top-decile capture >= 2x lift and PR-AUC above the base rate. A signal-sharpening enhancement (Option A) is documented in `ews/docs/enhancement_notes.md` for a future iteration.

## Proactive Line Increase

- LightGBM candidate model + headroom-to-target amount rules + incremental-ROE gate reusing
  the pricing engine + risk-appetite PD ceiling.
- **AUC 0.8128** (gate >= 0.78), lift
  **2.659x**; 95 offers; cohort PD
  0.0363 << book 0.1171; cohort utilization
  0.8371 > book 0.4714; aggregate incremental
  ROE **0.2153** >= hurdle 0.15.

- Train 6,668 / Test 1,668  | base rate 22.2%
- **AUC:** 0.8128  (gate >= 0.78)
- **Top-20% lift:** 2.66x  (gate >= 2.0)
- Offer threshold (prob quantile 0.75): 0.3121
- Risk-appetite PD ceiling (quantile 0.5): 0.0741

### Offered cohort vs book

- Offered accounts: 95
- Mean modeled PD: cohort 0.0363 vs book 0.1171  (gate cohort < book)
- Mean utilization: cohort 0.8371 vs book 0.4714  (gate cohort > book)
- Exposure-weighted incremental ROE: 0.2153  (gate >= 0.15)

> Incremental ROE is EAD-invariant (depends only on PD & the rate charged on the incremental balance); the drawdown assumption (Δlimit × utilization) scales the reported incremental exposure and net income, not the ROE ratio.

## Governance record

| Module | Gate | Result | Status |
|---|---|---|---|
| Score | AUC >= 0.78 | 0.8176 | PASS |
| Adjudication | AUC >= 0.78, lift >= 2.0 | 0.8096 / 2.8554x | PASS |
| Pricing | engine identities, machine precision | 6/6 tests | PASS |
| Early warning | capture >= 2x, PR-AUC > base (AUC ungated) | 2.1595x / 0.308 | PASS (honest gate) |
| Line increase | AUC/lift + cohort PD/util + incr. ROE | 0.8128 / 2.659x / 0.2153 | PASS |

- Gates are hard asserts in each `train.py` AND independently recomputed by `verify.py`
  from constants committed in the tag — a gate cannot be silently relaxed.
- The early-warning gate is the platform's governance exhibit: when a target's measured
  oracle ceiling sits below the aspirational gate, the honest resolution is to gate on
  what the data supports and report the rest — never to quietly tune the number, and
  never to regenerate data a downstream model already consumes. (The reference build
  escalated exactly this decision to a human, twice, with opposite resolutions — see
  `ews/docs/enhancement_notes.md` for the deferred Option A.)
- Reproducibility: pinned interpreter floor (3.11+) and `requirements.txt`; deterministic
  seeds; `git checkout stage-N && python verify.py` reproduces any checkpoint.
