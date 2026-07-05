# Data-Quality Report — synthetic SME portfolio

## Row counts

| file | rows | columns |
|---|---|---|
| businesses.parquet | 12,000 | 25 |
| portfolio.parquet | 8,336 | 31 |
| panel.parquet | 200,064 | 7 |

## Target rates

- default rate (applicants): **0.167**
- booked rate: **0.695**
- deterioration rate (on-book): **0.180**
- line_increase_good rate (on-book): **0.222**

## Null audit

Total nulls across all three files: **0** (synthetic data is complete by construction — a nonzero count here is a bug).

## Key feature distributions (applicants)

| feature | min | p25 | median | p75 | max |
|---|---|---|---|---|---|
| years_in_business | 0.50 | 5.10 | 8.00 | 11.80 | 40.00 |
| annual_revenue | 50,000.00 | 224,000.00 | 437,000.00 | 870,000.00 | 24,849,000.00 |
| dscr | 0.10 | 1.06 | 1.40 | 1.74 | 3.30 |
| current_ratio | 0.20 | 1.09 | 1.49 | 1.90 | 3.93 |
| leverage | 0.05 | 0.23 | 0.42 | 0.61 | 0.80 |
| utilization | 0.01 | 0.24 | 0.39 | 0.55 | 0.98 |
| requested_amount | 10,000.00 | 49,000.00 | 108,000.00 | 233,000.00 | 5,000,000.00 |

## Leakage deny-list

These columns exist in the data but must never enter a model's feature
matrix (`shared/config.py::LEAKAGE_COLUMNS`, enforced from stage-2 on):

- `pd_default_origination`
- `default`
- `risk_based_rate`
- `booked`
- `deterioration_next_6_12mo`
- `line_increase_good`
