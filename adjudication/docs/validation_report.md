# Loan Adjudication — Validation Report

- Train rows: 9,600  Test rows: 2,400
- **AUC:** 0.8096  (gate >= 0.78)
- **Top-20% lift:** 2.86x  (gate >= 2.0)

## PD-zone thresholds (calibrated)

- t_low (Approve <=): 0.0955
- t_high (Decline >=): 0.4943

## Decision mix (test split)

- Approve: 30.8%
- Decline: 32.4%
- Refer: 36.8%

- Files with >=1 policy rule hit: 994
