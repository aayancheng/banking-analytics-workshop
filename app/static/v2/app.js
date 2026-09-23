"use strict";
/* Loan Workbench v2 -- the shell (selector, persistent header, tab chrome).
   This file formats and draws. It never calculates a financial number: every value
   on screen came from a server response, because the server calls the same module
   function the batch pipeline calls. api/fmt/el/remember/recall/debounce come from
   util.js; svgEl/svgRoot/sparkline/divergingBars/hbars from svg.js;
   axisWithHandles from axis-handles.js -- load order in index.html puts all three
   ahead of this file. */

const FACETS = ["decision", "score_band", "industry", "region",
    "booked", "ews_tier", "mispriced", "li_eligible"];
const TABS = {};   // tab name -> render function, filled by later files/tasks

const state = { loanId: null, tab: "decision", filters: {} };

async function renderSelector() {
  const facets = await api("/api/v2/filters");
  const box = document.getElementById("filters");
  box.innerHTML = "";
  for (const f of FACETS) {
    const sel = el("select", {id: "f_" + f});
    sel.append(el("option", {value: ""}, "any"));
    for (const o of facets[f]) {
      sel.append(el("option", {value: String(o.value)},
                    `${o.value} (${o.count.toLocaleString()})`));
    }
    sel.value = state.filters[f] || "";
    sel.onchange = () => {
      state.filters[f] = sel.value;
      remember("v2.filters", state.filters);
      refreshMatches();
    };
    const wrap = el("div");
    // Programmatic label, not proximity-only: this screen is projected and may
    // be read by assistive tech.
    wrap.append(el("label", {for: sel.id}, f.replace(/_/g, " ")), sel);
    box.append(wrap);
  }
  document.getElementById("q").oninput = debounce(refreshMatches, 250);
  document.getElementById("clearfilters").onclick = () => {
    state.filters = {};
    remember("v2.filters", {});
    document.getElementById("q").value = "";
    renderSelector().then(refreshMatches);
  };
  await refreshMatches();
}

async function refreshMatches() {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(state.filters)) if (v) params.set(k, v);
  const q = document.getElementById("q").value.trim();
  if (q) params.set("q", q);
  const r = await api("/api/v2/loans?" + params.toString());
  const pick = document.getElementById("loanpick");
  pick.innerHTML = "";
  for (const l of r.loans) {
    pick.append(el("option", {value: l.business_id},
      `${l.business_id} · ${l.decision} · band ${l.score_band} · ${l.industry} · ${fmt.money(l.requested_amount)}`));
  }
  document.getElementById("matchcount").textContent =
    r.total === r.shown ? `${r.total.toLocaleString()} matches`
                        : `${r.shown} of ${r.total.toLocaleString()} shown`;
  pick.onchange = () => loadLoan(pick.value);
  if (r.loans.length) await loadLoan(r.loans[0].business_id);
}

async function loadLoan(id) {
  state.loanId = id;
  const h = await api("/api/v2/loan/" + id);
  renderHeader(h);
  for (const n of ["loanheader", "tabs", "panel"])
    document.getElementById(n).classList.remove("hidden");
  document.getElementById("empty").classList.add("hidden");
  await selectTab(state.tab);
}

function renderHeader(h) {
  const box = document.getElementById("loanheader");
  box.innerHTML = "";
  const cells = [
    ["business", h.business_id],
    ["industry / region", `${h.identity.industry} · ${h.identity.region}`],
    ["entity / age", `${h.identity.entity_type} · ${fmt.num(h.identity.years_in_business, 1)} yrs`],
    ["requested", `${fmt.money(h.terms.requested_amount)} · ${h.terms.term_months}mo`],
    ["purpose", `${h.terms.loan_purpose}${h.terms.collateral_flag ? " · secured" : ""}`],
    ["score", `${h.score.business_score} (band ${h.score.score_band})`],
    ["model PD", fmt.pct(h.score.pd, 2)],
    ["booked", h.booked ? "yes" : "no — never funded"],
  ];
  const grid = el("div", {class: "hdr-grid"});
  for (const [lbl, val] of cells) {
    const d = el("div");
    d.append(el("div", {class: "lbl"}, lbl), el("div", {class: "val"}, val));
    grid.append(d);
  }
  const dec = el("div");
  dec.append(el("div", {class: "lbl"}, "decision"),
             el("span", {class: "chip " + h.decision}, h.decision));
  grid.append(dec);
  box.append(grid);
  state.header = h;
}

async function selectTab(name) {
  state.tab = name;
  remember("v2.tab", name);
  for (const b of document.querySelectorAll("#tabs button"))
    b.classList.toggle("active", b.dataset.tab === name);
  const panel = document.getElementById("panel");
  if (!TABS[name]) { panel.innerHTML = "<p class='muted'>Not built yet.</p>"; return; }
  panel.innerHTML = "<p class='muted'>Loading…</p>";
  // Guarded: an unhandled rejection here (a server hiccup, a 404) used to leave
  // the panel reading "Loading…" forever -- indistinguishable on stage from a
  // slow render. A failed render now says so, with the actual error text.
  try {
    await TABS[name](panel, state.loanId);
  } catch (e) {
    panel.innerHTML = "";
    panel.append(el("p", {class: "tab-error"}, "Failed to load this tab: " + e.message));
  }
}

function start() {
  state.filters = recall("v2.filters", {});
  state.tab = recall("v2.tab", "decision");
  for (const b of document.querySelectorAll("#tabs button"))
    b.onclick = () => selectTab(b.dataset.tab);
  renderSelector().catch(e => {
    document.getElementById("empty").textContent = "Failed to load: " + e.message;
  });
}
document.addEventListener("DOMContentLoaded", start);
