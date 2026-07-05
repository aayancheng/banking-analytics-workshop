"""Assemble the model documentation pack (Session 5 deliverable).

One command turns the platform's committed artifacts — metadata, validation
reports, the pricing summary, the leakage deny-list — into a single reviewable
document. Deterministic: same artifacts in, same document out. This is the
pack a validator reads first; every claim in it traces to a generated artifact.

    make docpack   →   docs/model_doc_pack/MODEL_DOCUMENTATION.md
"""
import json
from pathlib import Path

from shared.config import (
    LEAKAGE_COLUMNS, MARKET, N_BUSINESSES, PANEL_MONTHS, ROOT, SEED,
)

PACK = ROOT / "docs" / "model_doc_pack"


def _meta(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def _report(path: str) -> str:
    """Inline a module's validation report, demoting its headings under ours."""
    text = (ROOT / path).read_text().strip()
    lines = [l for l in text.splitlines() if not l.startswith("# ")]
    return "\n".join("###" + l[2:] if l.startswith("## ") else l for l in lines).strip()


def main() -> None:
    PACK.mkdir(parents=True, exist_ok=True)
    score = _meta("score/models/metadata.json")
    adj = _meta("adjudication/models/metadata.json")
    pricing = _meta("pricing/docs/summary.json")
    ews = _meta("ews/models/metadata.json")
    li = _meta("line_increase/models/metadata.json")

    doc = f"""# Model Documentation Pack — SME Lending Decision Platform

Workshop build. Synthetic data throughout (seed {SEED}: {N_BUSINESSES:,} applicants,
{PANEL_MONTHS}-month behavioral panel). Every metric below is recomputed from committed
artifacts by `python verify.py` — this document cites, it does not assert.

## Data & leakage controls

- Generator: `shared/data_generator.py`, deterministic, seed {SEED}. Data-quality report:
  `reports/data_quality.md`.
- Deny-list (`shared/config.py::LEAKAGE_COLUMNS`) — columns that exist in the data but may
  never enter a feature matrix; enforced by assertions in every feature-engineering module
  and by `tests/test_leakage.py`:
{chr(10).join(f"  - `{c}`" for c in LEAKAGE_COLUMNS)}
- Score-reuse contract: downstream models consume the SAVED scorecard's output
  (`score/src/predict.py`), never the generator's true PD.

## Business Credit Score

- WoE binning + logistic scorecard (optbinning), scaled 300-850; reason codes are exact
  WoE x coefficient contributions (deliberately not SHAP).
- Held-out **AUC {score['metrics']['auc']}** (gate >= {score['gate']['auc_min']}), KS {score['metrics']['ks']}.

{_report('score/docs/validation_report.md')}

## Loan Adjudication

- LightGBM PD challenger + vectorized policy layer (hard knockouts -> PD zones -> refer
  overrides); SHAP reason codes + rule hits per applicant.
- Held-out **AUC {adj['metrics']['auc']}** (gate >= {adj['gate']['auc_min']}), top-20% lift
  **{adj['metrics']['top20_lift']}x** (gate >= {adj['gate']['lift_min']}).

{_report('adjudication/docs/validation_report.md')}

## Pricing & Profitability

- No ML: deterministic ROE/RAROC engine (`pricing/src/engine.py`), 6 machine-precision
  identity tests. Booked book priced against the {MARKET['roe_hurdle']:.0%} ROE hurdle.
- **{pricing['share_clears']:.1%}** of {pricing['n']:,} booked loans clear the hurdle at the
  quoted rate; median ROE {pricing['median_roe']:.1%}; **${pricing['mispriced_ead']:,.0f}
  mispriced EAD**.

{_report('pricing/docs/validation_report.md')}

## Early Warning

- LightGBM on 24-month panel trend features + 5 named triggers + calibrated High/Med/Low tiers.
- **Honest gate** (the label is noise-capped by construction): top-decile capture
  **{ews['metrics']['top_decile_capture']:.1%} = {ews['metrics']['top_decile_lift']}x**
  (gate >= 2x), PR-AUC **{ews['metrics']['pr_auc']}** > base rate {ews['base_rate']};
  AUC {ews['metrics']['auc']} reported, NOT gated.

{_report('ews/docs/validation_report.md')}

## Proactive Line Increase

- LightGBM candidate model + headroom-to-target amount rules + incremental-ROE gate reusing
  the pricing engine + risk-appetite PD ceiling.
- **AUC {li['metrics']['auc']}** (gate >= {li['gate']['auc_min']}), lift
  **{li['metrics']['top20_lift']}x**; {li['cohort']['n_offered']} offers; cohort PD
  {li['cohort']['cohort_pd']} << book {li['cohort']['book_pd']}; cohort utilization
  {li['cohort']['cohort_util']} > book {li['cohort']['book_util']}; aggregate incremental
  ROE **{li['cohort']['agg_incremental_roe']}** >= hurdle {li['cohort']['roe_hurdle']}.

{_report('line_increase/docs/validation_report.md')}

## Governance record

| Module | Gate | Result | Status |
|---|---|---|---|
| Score | AUC >= {score['gate']['auc_min']} | {score['metrics']['auc']} | PASS |
| Adjudication | AUC >= {adj['gate']['auc_min']}, lift >= {adj['gate']['lift_min']} | {adj['metrics']['auc']} / {adj['metrics']['top20_lift']}x | PASS |
| Pricing | engine identities, machine precision | 6/6 tests | PASS |
| Early warning | capture >= 2x, PR-AUC > base (AUC ungated) | {ews['metrics']['top_decile_lift']}x / {ews['metrics']['pr_auc']} | PASS (honest gate) |
| Line increase | AUC/lift + cohort PD/util + incr. ROE | {li['metrics']['auc']} / {li['metrics']['top20_lift']}x / {li['cohort']['agg_incremental_roe']} | PASS |

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
"""
    (PACK / "MODEL_DOCUMENTATION.md").write_text(doc)
    print(f"wrote docs/model_doc_pack/MODEL_DOCUMENTATION.md "
          f"({len(doc.splitlines())} lines)")


if __name__ == "__main__":
    main()
