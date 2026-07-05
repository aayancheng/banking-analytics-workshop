"""Synthetic SME population generator. Deterministic given seed.

This is Session 1 material, ported from the BusinessBankingApp reference build.
Study the shape: observable features first, then a *latent* default logit built
from a subset of them plus noise, then downstream targets. The truth columns it
writes (`pd_default_origination`, `default`, ...) are on the LEAKAGE_COLUMNS
deny-list in shared/config.py — models must rediscover the signal, never read it.
"""
import numpy as np
import pandas as pd

from shared.config import N_BUSINESSES, PANEL_MONTHS, SEED, MARKET, RAW

INDUSTRIES = ["Retail", "Construction", "Professional Services", "Manufacturing",
              "Hospitality", "Healthcare", "Transport", "Wholesale", "Technology",
              "Agriculture"]
REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
ENTITY_TYPES = ["LLC", "Sole Proprietor", "Corporation", "Partnership"]
PURPOSES = ["Working Capital", "Equipment", "Expansion", "Refinance",
            "Inventory", "Real Estate"]


def _z(x: np.ndarray) -> np.ndarray:
    """Standardize to mean 0 / std 1 (guard against zero std)."""
    s = x.std()
    return (x - x.mean()) / (s if s > 0 else 1.0)


def generate_businesses(n: int = N_BUSINESSES, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    business_id = np.array([f"BIZ{100000 + i}" for i in range(n)])
    industry = rng.choice(INDUSTRIES, n)
    region = rng.choice(REGIONS, n)
    entity_type = rng.choice(ENTITY_TYPES, n, p=[0.45, 0.20, 0.25, 0.10])

    years_in_business = np.clip(rng.gamma(3.0, 3.0, n), 0.5, 40.0).round(1)
    employees = np.clip(rng.lognormal(2.0, 1.0, n).round(), 1, 500).astype(int)
    annual_revenue = np.clip(rng.lognormal(13.0, 1.0, n), 5e4, 5e7).round(-3)
    profit_margin = np.clip(rng.normal(0.08, 0.06, n), -0.20, 0.40)
    net_income = (annual_revenue * profit_margin).round(-2)
    total_debt = np.clip(annual_revenue * rng.uniform(0.05, 0.80, n), 0, None).round(-3)
    current_ratio = np.clip(rng.normal(1.5, 0.6, n), 0.2, 5.0).round(2)
    dscr = np.clip(rng.normal(1.4, 0.5, n), 0.1, 5.0).round(2)
    leverage = np.clip(total_debt / np.maximum(annual_revenue, 1.0), 0, 5).round(2)
    credit_history_months = np.clip(rng.gamma(4.0, 12.0, n), 3, 360).round().astype(int)
    prior_delinquencies = rng.poisson(0.6, n).astype(int)
    trade_lines = np.clip(rng.poisson(6, n), 0, 40).astype(int)
    utilization = np.clip(rng.beta(2.0, 3.0, n), 0.0, 1.0).round(3)
    public_records = rng.binomial(1, 0.08, n).astype(int)

    requested_amount = np.clip(annual_revenue * rng.uniform(0.05, 0.50, n), 1e4, 5e6).round(-3)
    term_months = rng.choice([12, 24, 36, 48, 60, 84], n,
                             p=[0.10, 0.20, 0.30, 0.20, 0.15, 0.05])
    loan_purpose = rng.choice(PURPOSES, n)
    collateral_flag = rng.binomial(1, 0.5, n).astype(int)

    logit = (
        -2.2
        - 0.60 * _z(np.log(years_in_business))
        - 0.50 * _z(np.log(annual_revenue))
        - 0.70 * _z(dscr)
        - 0.40 * _z(current_ratio)
        + 0.60 * _z(leverage)
        + 0.55 * _z(utilization)
        + 0.50 * _z(prior_delinquencies.astype(float))
        + 0.70 * public_records
        - 0.40 * _z(np.log(credit_history_months))
        - 1.50 * profit_margin
        + rng.normal(0.0, 0.5, n)
    )
    pd_true = 1.0 / (1.0 + np.exp(-logit))
    default = rng.binomial(1, pd_true).astype(int)

    risk_based_rate = (
        MARKET["cost_of_funds"]
        + pd_true * MARKET["lgd"]
        + MARKET["opex_rate"]
        + MARKET["base_margin"]
        + rng.normal(0.0, 0.003, n)
    ).round(4)

    approve_logit = 2.0 - 6.0 * pd_true + rng.normal(0.0, 0.5, n)
    booked = rng.binomial(1, 1.0 / (1.0 + np.exp(-approve_logit))).astype(int)

    return pd.DataFrame({
        "business_id": business_id,
        "industry": industry, "region": region, "entity_type": entity_type,
        "years_in_business": years_in_business, "employees": employees,
        "annual_revenue": annual_revenue, "net_income": net_income,
        "total_debt": total_debt, "current_ratio": current_ratio, "dscr": dscr,
        "leverage": leverage, "credit_history_months": credit_history_months,
        "prior_delinquencies": prior_delinquencies, "trade_lines": trade_lines,
        "utilization": utilization, "public_records": public_records,
        "requested_amount": requested_amount, "term_months": term_months,
        "loan_purpose": loan_purpose, "collateral_flag": collateral_flag,
        "pd_default_origination": pd_true.round(4), "default": default,
        "risk_based_rate": risk_based_rate, "booked": booked,
    })


def generate_portfolio_and_panel(businesses: pd.DataFrame,
                                 panel_months: int = PANEL_MONTHS,
                                 seed: int = SEED):
    """Build on-book portfolio (account-level) and a long monthly behavioral panel
    for the BOOKED subset. Returns (portfolio_df, panel_df)."""
    rng = np.random.default_rng(seed + 1)
    book = businesses[businesses["booked"] == 1].reset_index(drop=True).copy()
    m = len(book)

    credit_limit = book["requested_amount"].to_numpy().astype(float)
    tenure_months = np.minimum(book["credit_history_months"].to_numpy(),
                               rng.integers(6, 60, m)).astype(int)
    start_util = np.clip(book["utilization"].to_numpy() + rng.normal(0, 0.05, m), 0.02, 0.98)
    pd_true = book["pd_default_origination"].to_numpy()

    months = np.arange(panel_months)
    drift = (pd_true - pd_true.mean()) * 0.015
    rows = []
    util_path = np.zeros((m, panel_months))
    for t in months:
        step = rng.normal(0, 0.03, m) + drift
        cur = np.clip(start_util + step * t, 0.0, 1.2)
        util_path[:, t] = cur
        balance = (cur * credit_limit).round(-1)
        dpd_lambda = np.clip(pd_true * 30 * (1 + 0.5 * (cur > 0.9)), 0, None)
        days_past_due = rng.poisson(dpd_lambda * 0.1).astype(int)
        deposit_inflow = np.clip(book["annual_revenue"].to_numpy() / 12.0
                                 * rng.uniform(0.6, 1.2, m)
                                 * (1 - 0.3 * (cur > 0.95)), 0, None).round(-1)
        overdraft_count = rng.poisson(np.clip(cur - 0.8, 0, None) * 3).astype(int)
        rows.append(pd.DataFrame({
            "business_id": book["business_id"].to_numpy(),
            "month_index": t,
            "balance": balance,
            "utilization": cur.round(3),
            "days_past_due": days_past_due,
            "deposit_inflow": deposit_inflow,
            "overdraft_count": overdraft_count,
        }))
    panel = pd.concat(rows, ignore_index=True)

    util_last3 = util_path[:, -3:].mean(axis=1)
    util_trend = util_path[:, -1] - util_path[:, 0]
    det_logit = (
        -2.4
        + 3.0 * pd_true
        + 2.0 * np.clip(util_last3 - 0.85, 0, None)
        + 1.5 * np.clip(util_trend, 0, None)
        + 0.4 * _z(book["leverage"].to_numpy())
        + rng.normal(0, 0.4, m)
    )
    deterioration = rng.binomial(1, 1.0 / (1.0 + np.exp(-det_logit))).astype(int)

    # line_increase_good leans on OBSERVABLE drivers (on-book utilization, revenue)
    # with modest Bernoulli noise, so a leakage-safe model can genuinely learn it.
    # The reference build's first version of this label was noise-capped below its
    # metric gate — the fix (and when such a fix is safe at all) is a Session 4 story.
    li_logit = (
        -2.1
        - 3.0 * pd_true
        + 7.0 * np.clip(util_last3 - 0.5, 0, None)
        + 1.2 * _z(np.log(book["annual_revenue"].to_numpy()))
        - 0.4 * deterioration
        + rng.normal(0, 0.18, m)
    )
    line_increase_good = rng.binomial(1, 1.0 / (1.0 + np.exp(-li_logit))).astype(int)

    portfolio = book.copy()
    portfolio["credit_limit"] = credit_limit.round(-3)
    portfolio["current_balance"] = (util_last3 * credit_limit).round(-1)
    portfolio["utilization_onbook"] = util_last3.round(3)
    portfolio["tenure_months"] = tenure_months
    portfolio["deterioration_next_6_12mo"] = deterioration
    portfolio["line_increase_good"] = line_increase_good

    return portfolio, panel


def main():
    biz = generate_businesses()
    portfolio, panel = generate_portfolio_and_panel(biz)
    biz.to_parquet(RAW / "businesses.parquet", index=False)
    portfolio.to_parquet(RAW / "portfolio.parquet", index=False)
    panel.to_parquet(RAW / "panel.parquet", index=False)
    print(f"businesses: {len(biz):,} rows, default rate {biz['default'].mean():.3f}, "
          f"booked {biz['booked'].mean():.3f}")
    print(f"portfolio:  {len(portfolio):,} accounts, "
          f"deterioration {portfolio['deterioration_next_6_12mo'].mean():.3f}, "
          f"line_increase_good {portfolio['line_increase_good'].mean():.3f}")
    print(f"panel:      {len(panel):,} rows ({panel['month_index'].nunique()} months)")


if __name__ == "__main__":
    main()
