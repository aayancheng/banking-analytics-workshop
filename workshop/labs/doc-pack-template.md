# Model Documentation — [YOUR NAME]'s SME Lending Platform

*Template: replace every bracket. Every number needs an artifact path next to it.
Your four memos are the raw material; the instructor pack shows the shape, not the words.*

## 1. Purpose & scope
[What business decisions does this platform make? For whom? What is explicitly OUT of scope?]

## 2. Data
[Source and generation process · row counts · seed/determinism · the leakage deny-list and HOW it is enforced (name the mechanism, not the intention) · data-quality evidence — from your S1 memo]

## 3. Business Credit Score
[Method and why this method (the regulatory argument) · features in, features excluded and WHY (your S2 memo) · held-out metrics WITH the gate · band table and what monotonicity proves · how reason codes work]

## 4. Adjudication
[The three decision layers in order · your cutoff and its defense (S3 memo: approval rate, expected loss, swap-set) · challenger comparison and why better AUC ≠ switch · decision mix]

## 5. Pricing
[Engine logic (no ML — say why that still needs governance) · the hurdle · headline findings with artifact citations · your repricing recommendation]

## 6. Portfolio monitoring (EWS)
[Panel features · the honest gate: what is gated, what is reported, and the oracle-ceiling number that justifies the split · tiers and named triggers · your S4 watchlist reading]

## 7. Line management
[The four offer gates in sequence · cohort quality vs book (all three comparisons) · why offering to ~1% of the book is the design working]

## 8. Limitations & appropriate use  ← write this yourself
[Synthetic data: what tonight's results do and do not prove · the ceiling: which targets are noise-capped and what that means for expectations · at least one limitation not said out loud in class]

## 9. Monitoring plan  ← write this yourself
[Which metric drifts first, and why that one · thresholds and who gets called · what evidence would make you PULL a model from production]

## 10. Governance record
[Every gate: value, result, PASS/FAIL · any gate that was renegotiated, by whom, with what evidence · who owns each decision layer — names, not roles]
