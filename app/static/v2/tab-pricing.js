"use strict";
/* Task 13 -- Pricing & Profitability tab: orchestration only. Rendering
   (waterfallTable/rateLadder/verdictTiles/bookStrip) lives in pricing-charts.js,
   loaded before this file. Uses api/fmt/el/debounce/postJSON (util.js) and
   sliderPanel (sliders.js, fix round 1 -- generalised out of this file's own
   sliders() so tab-ews.js's trigger sliders don't re-type the same widget).
   Formats and draws only -- every number is straight from a server response. */

// [key, label, min, max, step] -- covers each PricingOverrides field's legal
// range, including the edges the brief tests deliberately (capital_ratio's 0 and
// tax_rate's 1 are both invalid -- gt 0 / lt 1 -- and must round-trip a 422).
const SLIDER_DEFS = [
  ["quoted_rate", "Quoted rate", 0, 1, 0.001], ["cost_of_funds", "Cost of funds", 0, 1, 0.001],
  ["lgd", "LGD", 0, 1, 0.01], ["opex_rate", "Opex rate", 0, 1, 0.001],
  ["capital_ratio", "Capital ratio", 0, 1, 0.001], ["tax_rate", "Tax rate", 0, 1, 0.001],
  ["base_margin", "Base margin", 0, 1, 0.001], ["roe_hurdle", "ROE hurdle", 0, 2, 0.01],
  ["fee_rate", "Fee rate", 0, 1, 0.001],
];

const PRICING_WHATIF = id => `/api/v2/loan/${id}/pricing/whatif`;

TABS.pricing = async (panel, id) => {
  // pricing_whatif already returns null for an unbooked id, so the empty-body
  // POST alone answers both "is this booked" and "what are the batch numbers" --
  // no separate GET whose response would be thrown away.
  const seed = await postJSON(PRICING_WHATIF(id), {});
  panel.innerHTML = "";
  if (seed === null) {
    panel.append(el("p", {class: "muted"},
      "This applicant was never funded, so there is nothing to price."));
    return;
  }

  const topBox = el("div"), err = el("p", {class: "pr-error hidden"});
  const ladderBox = el("div"), wfBox = el("div"), sliderBox = el("div"), bookBox = el("div");
  const resetBtn = el("button", {type: "button"}, "Reset to book assumptions");
  panel.append(topBox, err, ladderBox, wfBox, el("h3", {}, "Market sliders"), sliderBox,
    bookBox, resetBtn);

  const paint = w => {
    topBox.innerHTML = ""; topBox.append(verdictTiles(w.verdict));
    ladderBox.innerHTML = ""; ladderBox.append(rateLadder(w.rates, w.verdict));
    wfBox.innerHTML = ""; wfBox.append(waterfallTable(w.waterfall, w.ead));
    bookBox.innerHTML = ""; bookBox.append(bookStrip(w.book));
  };
  paint(seed);

  const runWhatif = async body => {
    try {
      const w = await postJSON(PRICING_WHATIF(id), body);
      err.classList.add("hidden");
      paint(w);
    } catch (e) {
      err.textContent = e.message;
      err.classList.remove("hidden");
    }
  };

  // sliderPanel (sliders.js) reads defaults[key] for each SLIDER_DEFS entry --
  // {quoted_rate, ...market} is the same defaults object sliders() built inline.
  const sl = sliderPanel(SLIDER_DEFS, {quoted_rate: seed.rates.quoted, ...seed.market}, runWhatif);
  sliderBox.append(sl.node);
  resetBtn.onclick = () => { sl.reset(); runWhatif({}); };
};
