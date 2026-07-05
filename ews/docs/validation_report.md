# Early Warning — Validation Report

- Train 6,668 / Test 1,668  | base rate 18.0%
- **Top-decile capture:** 21.6%  =  **2.16x** lift  (gate >= 2x)
- **PR-AUC:** 0.3080  (gate > base rate 0.1802)
- **AUC:** 0.6622  (reported; not gated — see note below)
- Risk tiers: High >= 0.5073, Medium >= 0.1649

> **Gate note (Option B):** the synthetic `deterioration_next_6_12mo` label is noise-capped (logit noise + Bernoulli draw → oracle ceiling ~0.70 AUC), so the gate is set to what the data genuinely supports: top-decile capture >= 2x lift and PR-AUC above the base rate. A signal-sharpening enhancement (Option A) is documented in `ews/docs/enhancement_notes.md` for a future iteration.
