"use strict";
/* Page-agnostic helpers shared by the shell and every tab (Tasks 12-15): a fetch
   wrapper, number formatting, a tiny DOM builder, debounce, and guarded
   localStorage access. Nothing here decides anything or touches a number the
   server didn't already compute. */

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
  /* A feature's raw value for a ledger label. Categoricals pass through; integers
     print bare; floats get 4dp. Without this a computed feature renders at full
     float width -- `pd_score 0.2219917066245684` on a projected screen. Formatting
     is the browser's job; calculating is not. */
  feature: v => {
    if (typeof v !== "number") return String(v ?? "");
    return Number.isInteger(v) ? String(v) : v.toFixed(4);
  },
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

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
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
