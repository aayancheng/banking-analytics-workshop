"use strict";
/* Task 13 -- Pricing & Profitability tab: waterfall in dollars and bps, a rate
   ladder, market sliders, and a book strip. Formats and draws only -- every
   number is straight from a server response. postPricingWhatif is named to
   avoid colliding with tab-decision.js's global postWhatif (classic <script>
   tags share one scope; the later tag would silently misroute the other's calls). */

const COST_LINES = new Set(["cost_of_funds", "expected_loss", "operating_cost", "tax"]);
const RULE_BEFORE = new Set(["pre_tax_profit", "net_income"]);
const LABELS = {interest_income: "Interest income", cost_of_funds: "Cost of funds",
  expected_loss: "Expected loss", operating_cost: "Operating cost",
  pre_tax_profit: "Pre-tax profit", tax: "Tax", net_income: "Net income",
  allocated_equity: "Allocated equity"};

// One row per line, dollars and bps both from the response. A cost line stores a
// positive amount that is SUBTRACTED in the waterfall, so its display sign is the
// negation of the stored value (usually "-", but tax flips to a plain positive
// when pre_tax_profit itself is negative -- a rebate, not a further cost). An
// income/subtotal line displays its stored value as-is. Either way the sign
// choice and Math.abs() below are display polarity on a server-given number, the
// same pattern divergingBars (svg.js) already uses for its bar direction -- not
// a new financial figure. A rule marks the two subtotals.
function waterfallTable(lines, ead) {
  const body = el("tbody");
  for (const w of lines) {
    const cost = COST_LINES.has(w.line);
    const dEffect = cost ? -w.dollars : w.dollars, bEffect = cost ? -w.bps : w.bps;
    const sign = dEffect < 0 ? "− " : "";
    body.append(el("tr", {class: RULE_BEFORE.has(w.line) ? "wf-rule" : ""},
      el("td", {}, LABELS[w.line] || w.line),
      el("td", {}, sign + fmt.money(Math.abs(dEffect))),
      el("td", {}, sign + fmt.bps(Math.abs(bEffect)))));
  }
  const t = el("table", {class: "waterfall"});
  t.append(el("caption", {}, `Profit waterfall — EAD ${fmt.money(ead)}`),
    el("thead", {}, el("tr", {}, el("th", {}, "line"), el("th", {}, "dollars"),
      el("th", {}, "bps on EAD"))), body);
  return t;
}

// A static axis (no dragging -- this reports) with break-even/hurdle-clearing/
// recommended as plain ticks and the quoted rate as a pin coloured by
// verdict.clears_hurdle. A glyph rides with the colour for greyscale/screen readers.
function rateLadder(rates, verdict) {
  const width = 640, height = 78, pad = {l: 24, r: 24, t: 34};
  const vals = [rates.break_even, rates.hurdle_clearing, rates.recommended, rates.quoted];
  const lo = Math.min(...vals), hi = Math.max(...vals), span = (hi - lo) || 0.01;
  const min = lo - span * 0.15, max = hi + span * 0.15;
  const toX = v => pad.l + (v - min) / (max - min) * (width - pad.l - pad.r);
  const s = svgRoot(width, height);
  const tick = (x, half, w, color) => s.append(svgEl("line",
    {x1: x, x2: x, y1: pad.t - half, y2: pad.t + half, stroke: color, "stroke-width": w}));
  s.append(svgEl("line", {x1: pad.l, x2: width - pad.r, y1: pad.t, y2: pad.t,
    stroke: "var(--ink)", "stroke-width": 2}));
  for (const [key, label] of [["break_even", "break-even"],
      ["hurdle_clearing", "hurdle-clearing"], ["recommended", "recommended"]]) {
    const x = toX(rates[key]);
    tick(x, 8, 2, "var(--muted)");
    const lab = svgEl("text", {x, y: pad.t + 24, "font-size": 11, "text-anchor": "middle"});
    lab.textContent = `${label} ${fmt.pct(rates[key], 2)}`;
    s.append(lab);
  }
  const qx = toX(rates.quoted), color = verdict.clears_hurdle ? "var(--ok)" : "var(--bad)";
  const glyph = verdict.clears_hurdle ? "✓" : "✗";
  tick(qx, 16, 3, color);
  const pin = svgEl("text", {x: qx, y: pad.t - 20, "font-size": 12, "text-anchor": "middle",
    "font-weight": "700", fill: color});
  pin.textContent = `${glyph} quoted ${fmt.pct(rates.quoted, 2)}`;
  s.append(pin);
  const wrap = el("div", {class: "pr-ladder"});
  wrap.append(s, el("p", {class: "shortfall"},
    `${glyph} ${verdict.clears_hurdle ? "clears the hurdle" : "short of the hurdle"} ` +
    `by ${fmt.bps(verdict.rate_shortfall_bps)}`));
  return wrap;
}

function verdictTiles(v) {
  const mk = (label, node) => {
    const d = el("div", {class: "tile"});
    d.append(el("div", {class: "n"}, node), el("div", {class: "k"}, label));
    return d;
  };
  const clears = el("span", {class: "chip " + (v.clears_hurdle ? "Approve" : "Decline")},
    v.clears_hurdle ? "✓ clears" : "✗ short");
  const wrap = el("div", {class: "pr-tiles"});
  wrap.append(mk("ROE at quoted", fmt.pct(v.roe, 2)), mk("ROE hurdle", fmt.pct(v.roe_hurdle, 2)),
    mk("Clears hurdle", clears), mk("Shortfall", fmt.bps(v.rate_shortfall_bps)));
  return wrap;
}

// share_clears and mispriced_ead, sized to watch while a market slider drags --
// this is the session's set-piece (lgd 0.45 -> 0.90 visibly fails the book).
function bookStrip(book) {
  const big = el("div", {class: "book-big"});
  big.append(el("div", {class: "book-share"}, fmt.pct(book.share_clears, 2)),
    el("div", {class: "book-sub"}, `of ${book.n.toLocaleString()} booked loans ` +
      `clear the hurdle (${book.n_clears.toLocaleString()})`));
  const mis = el("div", {class: "book-mispriced"}, el("span", {class: "k"}, "Mispriced EAD"),
    el("span", {class: "n"}, fmt.money(book.mispriced_ead)));
  const wrap = el("div", {class: "pr-book"});
  wrap.append(big, mis);
  return wrap;
}

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

// Nine inputs that always post together as one overrides body (PricingOverrides
// wants a complete picture, not a partial diff). Debounced 120ms -- the book
// recompute itself is ~17ms, so that budget is UI settling, not server latency.
// reset() restores every input without posting; the caller re-POSTs {} itself.
function sliders(market, quotedRate, onChange) {
  const defaults = {quoted_rate: quotedRate, ...market};
  const values = {...defaults};
  const inputs = {};
  const wrap = el("div", {class: "sliders"});
  const fire = debounce(() => onChange({...values}), 120);
  for (const [key, label, min, max, step] of SLIDER_DEFS) {
    const input = el("input", {type: "range", id: "sl_" + key, min: String(min),
      max: String(max), step: String(step), value: String(defaults[key])});
    const out = el("span", {class: "sliderval"}, fmt.pct(defaults[key], 2));
    input.oninput = () => {
      values[key] = Number(input.value);
      out.textContent = fmt.pct(values[key], 2);
      fire();
    };
    inputs[key] = {input, out};
    wrap.append(el("div", {class: "sliderrow"}, el("label", {for: input.id}, label), input, out));
  }
  return {
    node: wrap,
    reset() {
      for (const [key] of SLIDER_DEFS) {
        values[key] = defaults[key];
        inputs[key].input.value = String(defaults[key]);
        inputs[key].out.textContent = fmt.pct(defaults[key], 2);
      }
    },
  };
}

// Local, like tab-decision.js's postWhatif: always reads the body so a 422's
// message reaches the caller verbatim instead of a bare status code.
async function postPricingWhatif(id, body) {
  const r = await fetch(`/api/v2/loan/${id}/pricing/whatif`, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = Array.isArray(data.detail)
      ? data.detail.map(e => e.msg).join("; ") : (data.detail || `request failed (${r.status})`);
    throw new Error(msg);
  }
  return data;
}

TABS.pricing = async (panel, id) => {
  const d = await api(`/api/v2/loan/${id}/pricing`);
  panel.innerHTML = "";
  if (d === null) {
    panel.append(el("p", {class: "muted"},
      "This applicant was never funded, so there is nothing to price."));
    return;
  }
  const seed = await postPricingWhatif(id, {});  // empty overrides == the batch pipeline

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
      const w = await postPricingWhatif(id, body);
      err.classList.add("hidden");
      paint(w);
    } catch (e) {
      err.textContent = e.message;
      err.classList.remove("hidden");
    }
  };

  const sl = sliders(seed.market, seed.rates.quoted, runWhatif);
  sliderBox.append(sl.node);
  resetBtn.onclick = () => { sl.reset(); runWhatif({}); };
};
