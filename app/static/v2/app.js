"use strict";
/* Loan Workbench v2.
   This file formats and draws. It never calculates a financial number: every value
   on screen came from a server response, because the server calls the same module
   function the batch pipeline calls. */

const FACETS = ["decision", "score_band", "industry", "region",
    "booked", "ews_tier", "mispriced", "li_eligible"];
const TABS = {};   // tab name -> render function, filled by later files/tasks

const state = { loanId: null, tab: "decision", filters: {} };

async function api(path, body) {
  const opts = body === undefined
    ? {} : {method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)};
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(path + " -> " + r.status);
  return r.json();
}

const fmt = {
  money: v => "$" + Math.round(v).toLocaleString(),
  pct: (v, d = 1) => (v * 100).toFixed(d) + "%",
  bps: v => Math.round(v).toLocaleString() + " bps",
  num: (v, d = 2) => Number(v).toFixed(d),
};

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else n.setAttribute(k, v);
  }
  for (const kid of kids) n.append(kid?.nodeType ? kid : document.createTextNode(kid));
  return n;
}

/* localStorage throws rather than returning null in restricted contexts, so every
   access is guarded. Remembered filters are a convenience, never a dependency. */
function remember(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* fine */ }
}
function recall(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch (e) { return fallback; }
}

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
    wrap.append(el("label", {}, f.replace(/_/g, " ")), sel);
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

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
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
  await TABS[name](panel, state.loanId);
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
