"""Central configuration: paths, seed, population sizes, market assumptions.

Module-specific policy blocks (adjudication knockouts, EWS triggers, line-increase
rules) arrive with their stages — this file grows with the workshop.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "shared" / "data" / "raw"
PROCESSED = ROOT / "shared" / "data" / "processed"

SEED = 42

# Population
N_BUSINESSES = 12_000        # applicants
PANEL_MONTHS = 24            # months of on-book behavioral history

# Market assumptions (used by Pricing from stage-3; stored here as the single source)
MARKET = {
    "cost_of_funds": 0.035,  # COF / FTP rate
    "lgd": 0.45,             # loss given default
    "opex_rate": 0.010,      # operating cost as a rate on EAD
    "tax_rate": 0.25,
    "capital_ratio": 0.12,   # allocated equity = capital_ratio * EAD (simplified RWA=EAD)
    "base_margin": 0.020,    # target margin baked into reference pricing
    "roe_hurdle": 0.15,
}

# Score scaling (FICO-like target band)
SCORE_MIN = 300
SCORE_MAX = 850

# Workshop-reserved ports (documented in the failure playbook; `make stop` frees them)
PORTS = {"fastapi": 8100, "vite": 5180}

RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

# Adjudication policy-layer defaults (PD zones, hard knockouts, refer overrides).
# t_low / t_high are re-calibrated from the model PD distribution at train time and
# written to adjudication/models/policy_config.json; these are the seed values.
ADJ_POLICY = {
    "t_low": 0.10,          # pd <= t_low  -> Approve zone
    "t_high": 0.35,         # pd >= t_high -> Decline zone
    "dscr_floor": 1.0,      # dscr < floor -> hard Decline
    "dscr_refer_hi": 1.2,   # approve-zone pd but dscr in [floor, refer_hi) -> Refer
    "public_records_cap": 0,   # public_records > cap -> hard Decline
    "prior_delinq_cap": 3,     # prior_delinquencies >= cap -> hard Decline
    "leverage_cap": 6.0,    # leverage > cap -> hard Decline
    "req_to_rev_cap": 0.75, # requested_amount / annual_revenue > cap -> Refer
    "score_floor": 600,     # approve-zone pd but business_score < floor -> Refer
}

# Columns that must never enter any model's feature matrix (target / post-decision /
# downstream-module leakage). Single source of truth for all stages.
LEAKAGE_COLUMNS = [
    "pd_default_origination",     # DGP ground-truth PD
    "default",                    # scorecard/adjudication target
    "risk_based_rate",            # priced from the true PD
    "booked",                     # funding decision (post-adjudication)
    "deterioration_next_6_12mo",  # downstream early-warning target
    "line_increase_good",         # downstream line-increase target
]
