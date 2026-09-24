"use strict";
/* Plain-DOM tile builders for the Early Warning tab -- split from ews-charts.js
   (final fix wave) on the seam it already named: SVG renderers there, tiles here,
   the split pricing-charts.js uses for verdictTiles/bookStrip. Data in, DOM out,
   no network, no state. Uses el/fmt (util.js) and divergingBars (svg.js). Every
   number shown came straight off a server response. */

const TIER_GLYPH = {Low: "✓", Medium: "!", High: "✗"};
// Same order ews.py's _TRIGGER_SPECS uses.
const TRIGGER_NAMES = ["HIGH_UTILIZATION", "RISING_UTILIZATION", "DELINQUENCY",
                       "DEPOSIT_DECLINE", "FREQUENT_OVERDRAFTS"];

// Colour is never the sole carrier of a tier state -- every chip/tile below
// carries TIER_GLYPH alongside the colour class.
function tierChip(tier) {
  return el("span", {class: "chip " + tier}, `${TIER_GLYPH[tier] ?? ""} ${tier}`);
}

// book_tiers can omit a tier with zero accounts (pandas value_counts drops it --
// the same trap tab-decision.js's bookMixTiles guards for decisions).
function bookTierTiles(counts) {
  const wrap = el("div", {class: "book-mix"});
  for (const k of ["Low", "Medium", "High"]) {
    wrap.append(el("div", {class: "tile chip " + k},
      el("div", {class: "n"}, String(counts[k] ?? 0)),
      el("div", {class: "k"}, `${TIER_GLYPH[k]} ${k}`)));
  }
  return wrap;
}

// The whole book's fired count per trigger -- the visible payoff of dragging a
// trigger threshold (high_utilization 0.90 -> 0.10 takes this from 628 to
// ~7,538), the same role bookTierTiles plays for the tier bar.
function bookTriggerCounts(counts) {
  const wrap = el("div", {class: "trigger-counts"});
  for (const name of TRIGGER_NAMES) {
    wrap.append(el("span", {class: "trigger-count"},
      `${name.replace(/_/g, " ")} ${counts[name] ?? 0}`));
  }
  return wrap;
}

// The model's limits as visible body text next to its own output, quoted
// verbatim from model_caveat -- never recomputed, and left in the metadata's
// own decimal units (not a percent) so the figures match metadata.json exactly.
function caveatBlock(c) {
  const wrap = el("div", {class: "ews-caveat"});
  wrap.append(
    el("p", {},
      `Top-decile capture ${fmt.num(c.top_decile_capture, 4)} held out ` +
      `(lift ${fmt.num(c.top_decile_lift, 4)}×). AUC ${fmt.num(c.auc, 4)} — ` +
      `reported, not gated. Base rate ${fmt.num(c.base_rate, 4)}.`),
    el("p", {}, c.note));
  return wrap;
}

// SHAP drivers are adverse-only (top_adverse_shap keeps positive contributions
// only), so divergingBars always renders them pushing one direction -- reused
// as-is. No feature "value" here (unlike the decision tab's ledgers), so
// fmt.feature(undefined) prints blank in that slot: display-only.
function driverBars(drivers) {
  if (!drivers.length) return el("p", {class: "muted"}, "No adverse SHAP drivers.");
  return divergingBars(drivers.map(d => ({feature: d.feature, contribution: d.impact})));
}
