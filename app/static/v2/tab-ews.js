"use strict";
/* Task 14 -- Early Warning tab: orchestration only. Rendering (smallMultiples/
   triggerTable/tierBar) lives in ews-charts.js, loaded before this file. Uses
   api/fmt/el/postJSON (util.js) and divergingBars (svg.js). Formats and draws
   only -- every number on screen, including the model's own reported limits,
   comes straight off a server response; nothing here recomputes a probability,
   a tier, or a threshold. */

const EWS_WHATIF = id => `/api/v2/loan/${id}/ews/whatif`;
const TIER_GLYPH = {Low: "✓", Medium: "!", High: "✗"};

// Colour is never the sole carrier of a tier state -- every chip and tile below
// carries TIER_GLYPH alongside the colour class.
function tierChip(tier) {
  return el("span", {class: "chip " + tier}, `${TIER_GLYPH[tier] ?? ""} ${tier}`);
}

// book_tiers can omit a tier with zero accounts (pandas value_counts drops it --
// the same trap tab-decision.js's bookMixTiles guards for decisions) -- never
// leave a tile blank.
function bookTierTiles(counts) {
  const wrap = el("div", {class: "book-mix"});
  for (const k of ["Low", "Medium", "High"]) {
    wrap.append(el("div", {class: "tile chip " + k},
      el("div", {class: "n"}, String(counts[k] ?? 0)),
      el("div", {class: "k"}, `${TIER_GLYPH[k]} ${k}`)));
  }
  return wrap;
}

// The model's limits as visible body text next to its own output, quoted
// verbatim from model_caveat -- never recomputed. Numbers stay in the metadata's
// own units (a bare decimal, not a percent) so the figures on screen match
// metadata.json exactly.
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
// only), so divergingBars (svg.js) always renders them pushing one direction --
// reused as-is rather than inventing a new bar renderer. It has no feature
// "value" here (unlike the decision tab's ledgers), so fmt.feature(undefined)
// prints blank in that slot: display-only, nothing computed.
function driverBars(drivers) {
  if (!drivers.length) return el("p", {class: "muted"}, "No adverse SHAP drivers.");
  return divergingBars(drivers.map(d => ({feature: d.feature, contribution: d.impact})));
}

TABS.ews = async (panel, id) => {
  const e = await api(`/api/v2/loan/${id}/ews`);
  panel.innerHTML = "";
  if (e === null) {
    panel.append(el("p", {class: "muted"},
      "This applicant was never funded, so there is no behaviour to monitor."));
    return;
  }
  // ews_whatif's response is what actually carries book_tiers/book_trigger_counts
  // (the batch aggregates) -- the same reason tab-decision.js and tab-pricing.js
  // both seed from an empty-body POST rather than the GET alone.
  const seed = await postJSON(EWS_WHATIF(id), {});

  const topBox = el("div"), err = el("p", {class: "ews-error hidden"});
  const barBox = el("div", {class: "ews-ruler"});
  const trigBox = el("div");
  panel.append(
    topBox, err, barBox,
    el("h3", {}, "24-month behaviour"), smallMultiples(e.panel, e.triggers),
    el("h3", {}, "Behavioural triggers"), trigBox,
    el("h3", {}, "SHAP drivers"), driverBars(e.drivers),
    el("h3", {}, "Model limits"), caveatBlock(e.model_caveat));

  // Only topBox and trigBox are ever rebuilt after the initial draw -- the tier
  // bar SVG (and the pointer capture a live drag holds on it) is never touched,
  // which is what keeps a drag-triggered re-render from detaching the node
  // mid-drag (axisWithHandles calls getScreenCTM() on pointermove; a detached
  // node returns null there and throws).
  const paint = w => {
    topBox.innerHTML = "";
    topBox.append(tierChip(w.risk_tier),
      el("p", {class: "ews-prob"}, `p(deterioration) ${fmt.num(w.prob, 4)}`),
      bookTierTiles(w.book_tiers));
    trigBox.innerHTML = "";
    trigBox.append(triggerTable(w.triggers));
  };
  paint(seed);

  barBox.append(tierBar(seed.prob, seed.tiers, async vals => {
    try {
      const w = await postJSON(EWS_WHATIF(id), vals);
      err.classList.add("hidden");
      paint(w);
    } catch (ex) {
      err.textContent = ex.message;
      err.classList.remove("hidden");
    }
  }));
};
