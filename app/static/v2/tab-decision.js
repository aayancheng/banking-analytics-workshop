"use strict";
/* Task 12 -- Decision tab: orchestration only. Rendering (rulesTable/ledgerBars/
   pdRuler/bookMixTiles/nearestFlipLine) lives in decision-charts.js, loaded
   before this file. Uses api/fmt/el/postJSON/latest (util.js). Every fired/clear
   state, every book-mix count, and the additive-footer numbers come straight from
   a server response -- nothing here compares a value to a threshold. */

TABS.decision = async (panel, id, fresh) => {
  const d = await api(`/api/v2/loan/${id}/decision`);
  // empty overrides == the batch pipeline. postJSON (util.js) is the shared
  // what-if POST every tab uses -- it always reads the body so a 422 surfaces
  // the server's own message instead of a bare status code.
  const seed = await postJSON(`/api/v2/loan/${id}/decision/whatif`, {});
  if (!fresh()) return;   // another loan or tab was chosen while this loaded

  panel.innerHTML = "";
  const topBox = el("div", {id: "dec-top"});
  const err = el("p", {class: "dec-error hidden"});
  const rulerBox = el("div", {class: "dec-ruler"});
  const tables = el("div", {id: "dec-tables"});
  const flipBox = el("div");
  panel.append(topBox, err, rulerBox, tables,
    ledgerBars(d.score_ledger, "Scorecard rationale (WoE × β)"),
    ledgerBars(d.shap, "Adjudication model rationale (SHAP)", "base value"),
    flipBox);

  // The ruler SVG (and the pointer capture a live drag holds on it) is never
  // rebuilt after the initial draw -- only re-labelled -- which is what keeps a
  // drag-triggered re-render from detaching the node mid-drag.
  let ruler = null;
  const paint = w => {
    topBox.innerHTML = "";
    // The header chip is the BATCH decision; this one is the what-if's, and says so.
    const chip = el("div", {class: "whatif-decision"});
    chip.append(el("span", {class: "lbl"}, "what-if decision "),
                el("span", {class: "chip " + w.decision}, w.decision));
    topBox.append(chip, bookMixTiles(w.book_mix, w.flipped_count));
    tables.innerHTML = "";
    tables.append(rulesTable(w.rules.knockouts, "Knockout rules"),
                  rulesTable(w.rules.refer_overrides, "Refer overrides"));
    flipBox.innerHTML = "";
    flipBox.append(nearestFlipLine(w.nearest_flip));
    if (ruler) ruler.setFormat(v => v.toFixed(w.pd_zones.dp));
  };
  paint(seed);

  const ticket = latest();
  ruler = pdRuler(d.pd_zones, async vals => {
    const ok = ticket();
    try {
      const w = await postJSON(`/api/v2/loan/${id}/decision/whatif`, vals);
      if (!ok() || !fresh()) return;   // a newer drag already answered
      err.classList.add("hidden");
      paint(w);
    } catch (e) {
      if (!ok() || !fresh()) return;
      console.error(e);
      err.textContent = e.message;
      err.classList.remove("hidden");
    }
  });
  rulerBox.append(ruler);
};
