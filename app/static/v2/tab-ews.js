"use strict";
/* Task 14 -- Early Warning tab: orchestration only. Rendering (smallMultiples/
   triggerTable/tierBar/tierChip/bookTierTiles/bookTriggerCounts/caveatBlock/
   driverBars) lives in ews-charts.js, loaded before this file. Uses api/fmt/el
   /postJSON (util.js) and sliderPanel (sliders.js). Formats and draws only --
   every number on screen, including the model's own reported limits, comes
   straight off a server response; nothing here recomputes a probability, a
   tier, or a threshold.

   Fix round 1: the spec requires the named triggers to carry draggable
   thresholds, not just the tier cutoffs -- EwsOverrides has accepted all five
   (high_utilization, rising_utilization, dpd_severe, deposit_decline,
   overdraft_recent) since Task 9. Tier cutoffs and trigger thresholds now post
   together as one override body from a single `overrides` snapshot kept here,
   so a drag on either widget always sends the OTHER widget's last-known-good
   values alongside its own -- the server never sees a partial picture. */

const EWS_WHATIF = id => `/api/v2/loan/${id}/ews/whatif`;

// [key, label, min, max, step, format] -- EwsOverrides' own bounds
// (app/v2/ews_whatif.py). dpd_severe/overdraft_recent are integer counts, so
// they get integer steps and a plain-count format instead of fmt.pct.
const TRIGGER_SLIDER_DEFS = [
  ["high_utilization", "High utilization", 0, 2, 0.01, v => fmt.pct(v, 0)],
  ["rising_utilization", "Rising utilization", -1, 2, 0.01, v => fmt.pct(v, 0)],
  ["dpd_severe", "Delinquency (days)", 0, 180, 1, v => fmt.num(v, 0)],
  ["deposit_decline", "Deposit decline", 0, 1, 0.01, v => fmt.pct(v, 0)],
  ["overdraft_recent", "Overdraft count", 0, 50, 1, v => fmt.num(v, 0)],
];

TABS.ews = async (panel, id) => {
  const e = await api(`/api/v2/loan/${id}/ews`);
  panel.innerHTML = "";
  if (e === null) {
    panel.append(el("p", {class: "muted"},
      "This applicant was never funded, so there is no behaviour to monitor."));
    return;
  }
  // ews_whatif's response is what actually carries book_tiers/book_trigger_counts
  // and trigger_config (the batch aggregates and the merged threshold config) --
  // the same reason tab-decision.js and tab-pricing.js both seed from an
  // empty-body POST rather than the GET alone.
  const seed = await postJSON(EWS_WHATIF(id), {});

  const topBox = el("div"), err = el("p", {class: "ews-error hidden"});
  const barBox = el("div", {class: "ews-ruler"});
  const sliderBox = el("div");
  const countsBox = el("div");
  const panelBox = el("div");
  const trigBox = el("div");
  panel.append(
    topBox, err, barBox,
    el("h3", {}, "Trigger thresholds"), sliderBox, countsBox,
    el("h3", {}, "24-month behaviour"), panelBox,
    el("h3", {}, "Behavioural triggers"), trigBox,
    el("h3", {}, "SHAP drivers"), driverBars(e.drivers),
    el("h3", {}, "Model limits"), caveatBlock(e.model_caveat));

  // The single source of truth for what was last sent successfully -- every
  // drag (tier bar OR trigger slider) posts {...overrides, ...itsOwnPatch}, so
  // the other widget's last-good values always ride along. Only reassigned on
  // a successful response (the server's own echoed tiers/trigger_config), so a
  // rejected drag never contaminates what the NEXT drag sends -- the same
  // "tiles frozen at last valid values" contract the ruler already had.
  let overrides = {
    t_med: seed.tiers.t_med, t_high: seed.tiers.t_high,
    ...Object.fromEntries(TRIGGER_SLIDER_DEFS.map(([k]) => [k, seed.trigger_config[k]])),
  };

  // Everything but the tier-bar SVG is rebuilt on every paint(); the ruler (and
  // the pointer capture a live drag holds on it) is never touched, which is
  // what keeps a drag-triggered re-render from detaching it mid-drag
  // (axisWithHandles calls getScreenCTM() on pointermove; a detached node
  // returns null there and throws). Rebuilding panelBox is what makes the
  // utilization sparkline's dashed rule follow a dragged high_utilization
  // instead of staying stranded at the value read at first paint.
  const paint = w => {
    topBox.innerHTML = "";
    topBox.append(tierChip(w.risk_tier),
      el("p", {class: "ews-prob"}, `p(deterioration) ${fmt.num(w.prob, 4)}`),
      bookTierTiles(w.book_tiers));
    countsBox.innerHTML = "";
    countsBox.append(bookTriggerCounts(w.book_trigger_counts));
    panelBox.innerHTML = "";
    panelBox.append(smallMultiples(e.panel, w.trigger_config));
    trigBox.innerHTML = "";
    trigBox.append(triggerTable(w.triggers));
  };
  paint(seed);

  const runWhatif = async patch => {
    const body = {...overrides, ...patch};
    try {
      const w = await postJSON(EWS_WHATIF(id), body);
      overrides = {t_med: w.tiers.t_med, t_high: w.tiers.t_high, ...w.trigger_config};
      err.classList.add("hidden");
      paint(w);
    } catch (ex) {
      err.textContent = ex.message;
      err.classList.remove("hidden");
    }
  };

  barBox.append(tierBar(seed.prob, seed.tiers, runWhatif));
  // sliderPanel only reads/writes the five keys in TRIGGER_SLIDER_DEFS, so
  // passing the wider `overrides` object as its defaults is safe -- it simply
  // ignores t_med/t_high.
  const sl = sliderPanel(TRIGGER_SLIDER_DEFS, overrides, runWhatif);
  sliderBox.append(sl.node);
};
