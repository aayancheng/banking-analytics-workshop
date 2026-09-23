"use strict";
/* Fix round 1 -- generalised out of tab-pricing.js's sliders(), which was
   hardcoded to its own SLIDER_DEFS and to fmt.pct display. Task 14's trigger
   thresholds need the same range-input-group pattern but are not all
   percentages (dpd_severe/overdraft_recent are integer counts), so this
   version takes each def's own format function instead of assuming one. A
   stateful input widget (drives onChange as the user drags), so it sits
   beside axis-handles.js rather than among the pure renderers -- both
   tab-pricing.js and tab-ews.js load it and call it, so the group is defined
   once. It reports values; every repaint still comes from a server what-if
   response, never from arithmetic on what the sliders read.

   defs: [[key, label, min, max, step, format?], ...]. format(v) defaults to
   fmt.pct(v, 2), matching the pricing tab's original behaviour exactly.
   defaults: the starting (and reset) value for every key in defs.
   onChange(fullValuesObject): fires debounced 120ms on every input, carrying
   the CURRENT value of every key this panel manages (not just the one that
   moved), the same shape the original sliders() sent. */
function sliderPanel(defs, defaults, onChange) {
  // Only the keys this panel owns. Seeding from the whole defaults object meant a
  // panel sharing an override body with another widget (the EWS tier bar) carried
  // that widget's values frozen at mount time and re-sent them on every change,
  // silently reverting the other widget's latest drag.
  const values = Object.fromEntries(defs.map(([key]) => [key, defaults[key]]));
  const inputs = {};
  const wrap = el("div", {class: "sliders"});
  const fire = debounce(() => onChange({...values}), 120);
  for (const [key, label, min, max, step, format] of defs) {
    const fmtFn = format || (v => fmt.pct(v, 2));
    const input = el("input", {type: "range", id: "sl_" + key, min: String(min),
      max: String(max), step: String(step), value: String(defaults[key])});
    const out = el("span", {class: "sliderval"}, fmtFn(defaults[key]));
    input.oninput = () => {
      values[key] = Number(input.value);
      out.textContent = fmtFn(values[key]);
      fire();
    };
    inputs[key] = {input, out, fmtFn};
    wrap.append(el("div", {class: "sliderrow"}, el("label", {for: input.id}, label), input, out));
  }
  return {
    node: wrap,
    reset() {
      for (const [key] of defs) {
        values[key] = defaults[key];
        inputs[key].input.value = String(defaults[key]);
        inputs[key].out.textContent = inputs[key].fmtFn(defaults[key]);
      }
    },
  };
}
