# Proactive Line Increase — Validation Report

- Train 6,668 / Test 1,668  | base rate 22.2%
- **AUC:** 0.8128  (gate >= 0.78)
- **Top-20% lift:** 2.66x  (gate >= 2.0)
- Offer threshold (prob quantile 0.75): 0.3121
- Risk-appetite PD ceiling (quantile 0.5): 0.0741

## Offered cohort vs book

- Offered accounts: 95
- Mean modeled PD: cohort 0.0363 vs book 0.1171  (gate cohort < book)
- Mean utilization: cohort 0.8371 vs book 0.4714  (gate cohort > book)
- Exposure-weighted incremental ROE: 0.2153  (gate >= 0.15)

> Incremental ROE is EAD-invariant (depends only on PD & the rate charged on the incremental balance); the drawdown assumption (Δlimit × utilization) scales the reported incremental exposure and net income, not the ROE ratio.
