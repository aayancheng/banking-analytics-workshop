"""Render a Marp deck to a standalone HTML file you can open in a browser.

No npm, no marp-cli, no network, no dependencies outside the standard library —
the same reasoning as `make reading` using headless Chrome rather than a toolchain.

    python workshop/slides/render_html.py                       # every S*.md
    python workshop/slides/render_html.py workshop/slides/S1.md # just one

Writes S1.html beside S1.md (gitignored — it is derived from the .md).

What it is for: checking the deck reads correctly and **that no slide overflows**.
Each slide is drawn on a real 16:9 card at the deck's own font sizes, and any card
whose content spills is flagged in red with its overflow in pixels — the check that
otherwise only happens when you are standing in front of the room.

Speaker notes (`<!-- ... -->`) are collected per slide and hidden behind a toggle, so
the same file works for rehearsing and for sending to someone.

It covers the subset these decks actually use: h1-h3, tables, fenced code,
blockquotes, ordered and unordered lists, bold, italic and inline code. It is not a
general Markdown implementation and does not try to be.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def inline(t: str) -> str:
    """Escape, then apply inline markup. Code spans are protected from the rest."""
    spans: list[str] = []

    def stash(m):
        spans.append(html.escape(m.group(1)))
        return f"\x00{len(spans) - 1}\x00"

    t = re.sub(r"`([^`]+)`", stash, t)
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{spans[int(m.group(1))]}</code>", t)


def starts_block(ln: str) -> bool:
    """True if this line opens a non-paragraph block. `-`/`*` need a following space:
    without that check a paragraph opening with **bold** is mistaken for a bullet."""
    return (ln.startswith(("#", ">", "|", "```"))
            or re.match(r"^[-*]\s", ln) is not None
            or re.match(r"^\d+\.\s", ln) is not None)


def render_slide(md: str) -> tuple[str, list[str]]:
    """One slide's markdown -> (html, speaker notes)."""
    notes, body, i = [], [], 0
    lines = md.splitlines()

    # lift HTML comments out first; they are speaker notes, not content
    text, buf, inside = [], [], False
    for ln in lines:
        if "<!--" in ln:
            inside = True
            buf.append(ln[ln.index("<!--") + 4:])
            if "-->" in ln:
                inside = False
                notes.append(" ".join(buf).replace("-->", "").strip())
                buf = []
            continue
        if inside:
            if "-->" in ln:
                inside = False
                buf.append(ln[:ln.index("-->")])
                notes.append(" ".join(buf).strip())
                buf = []
            else:
                buf.append(ln)
            continue
        text.append(ln)
    lines = text

    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
        elif ln.startswith("```"):                                    # fenced code
            lang, i, code = ln[3:].strip(), i + 1, []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i]); i += 1
            i += 1
            cls = f' class="lang-{lang}"' if lang else ""
            body.append(f"<pre{cls}><code>{html.escape(chr(10).join(code))}</code></pre>")
        elif ln.lstrip().startswith("|"):                             # table
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].strip()); i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            sep = 1 if len(cells) > 1 and all(set(c) <= set("-: ") for c in cells[1]) else 0
            out = ["<table>"]
            if sep:
                out.append("<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells[0]) + "</tr></thead>")
            out.append("<tbody>")
            for row in cells[1 + sep:] if sep else cells:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
            out.append("</tbody></table>")
            body.append("".join(out))
        elif ln.startswith(">"):                                      # blockquote
            q = []
            while i < len(lines) and (lines[i].startswith(">") or
                                      (q and lines[i].strip() and not lines[i].startswith(("#", "-", "|", "```")))):
                q.append(lines[i].lstrip("> ").rstrip()); i += 1
            body.append(f"<blockquote>{inline(' '.join(q))}</blockquote>")
        elif re.match(r"^\d+\.\s", ln) or re.match(r"^[-*]\s", ln):   # lists
            ordered = bool(re.match(r"^\d+\.\s", ln))
            items = []
            while i < len(lines):
                m = re.match(r"^(\d+\.|[-*])\s+(.*)", lines[i])
                if m:
                    items.append(m.group(2)); i += 1
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip(); i += 1      # continuation
                else:
                    break
            tag = "ol" if ordered else "ul"
            body.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
        elif ln.startswith("#"):                                      # heading
            lvl = len(ln) - len(ln.lstrip("#"))
            body.append(f"<h{lvl}>{inline(ln[lvl:].strip())}</h{lvl}>")
            i += 1
        else:                                                         # paragraph
            para = [lines[i].strip()]; i += 1     # always consume at least this line,
            while i < len(lines) and lines[i].strip() and not starts_block(lines[i]):
                para.append(lines[i].strip()); i += 1
            body.append(f"<p>{inline(' '.join(para))}</p>")
    return "".join(body), notes


CSS = """
:root{--ink:#1a2332;--accent:#245bb2;--muted:#5b6b80;--line:#d6dee9;--paper:#fff}
*{box-sizing:border-box}
body{margin:0;background:#eef1f5;font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:var(--ink)}
header{position:sticky;top:0;z-index:9;background:var(--ink);color:#fff;padding:10px 20px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
header b{font-size:15px}header label{font-size:13px;color:#b9c7dc;cursor:pointer;user-select:none}
header .warn{margin-left:auto;font-size:13px;color:#ffb4ad}
main{padding:24px;display:flex;flex-direction:column;align-items:center;gap:24px}
.wrap{width:1280px;max-width:100%}
.num{font-size:12px;color:var(--muted);margin-bottom:6px;display:flex;justify-content:space-between}
.slide{width:1280px;height:720px;background:var(--paper);border:1px solid var(--line);border-radius:8px;
  padding:56px 64px;overflow:hidden;position:relative;font-size:26px;line-height:1.45}
.slide.over{border-color:#c0392b;box-shadow:0 0 0 3px rgba(192,57,43,.18)}
.badge{position:absolute;right:10px;bottom:8px;font-size:12px;color:#c0392b;font-weight:600}
.slide h1{font-size:52px;color:var(--ink);margin:0 0 .5em}
.slide h2{font-size:34px;margin:.2em 0 .4em}
.slide h3{font-size:28px;color:var(--muted);margin:.2em 0 .4em;font-weight:600}
.slide strong{color:var(--accent)}
.slide code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.86em;background:#f2f5f9;padding:.08em .3em;border-radius:3px}
.slide pre{background:#0d1421;color:#dee4ec;padding:14px 18px;border-radius:6px;overflow:auto;font-size:20px;line-height:1.4}
.slide pre code{background:none;color:inherit;font-size:1em;padding:0}
.slide blockquote{border-left:4px solid var(--accent);margin:.6em 0;padding:.1em 0 .1em 18px;font-style:normal;color:#2c3e55}
.slide table{border-collapse:collapse;font-size:22px;margin:.4em 0}
.slide th,.slide td{border:1px solid var(--line);padding:6px 12px;text-align:left}
.slide th{background:#f4f7fb}
.slide ul,.slide ol{margin:.3em 0;padding-left:1.3em}.slide li{margin:.18em 0}
.notes{background:#fffbe8;border:1px solid #e6d9a8;border-radius:6px;padding:10px 14px;margin-top:8px;font-size:14px;color:#5a4b1c}
body:not(.shownotes) .notes{display:none}
@media print{body{background:#fff}header,.num,.notes{display:none}
  main{padding:0;gap:0}.slide{border:0;border-radius:0;page-break-after:always;box-shadow:none!important}}
"""

JS = """
document.getElementById('sn').addEventListener('change',e=>document.body.classList.toggle('shownotes',e.target.checked));
let over=0;
document.querySelectorAll('.slide').forEach(s=>{
  const px=s.scrollHeight-s.clientHeight;
  if(px>2){over++;s.classList.add('over');
    const b=document.createElement('div');b.className='badge';b.textContent='OVERFLOWS by '+px+'px';s.appendChild(b);}
});
document.querySelector('.warn').textContent = over
  ? over+' slide'+(over>1?'s':'')+' overflow the 16:9 frame — fix before presenting'
  : 'No slide overflows the 16:9 frame';
"""


def render_file(md_path: Path) -> Path:
    raw = md_path.read_text()
    body = raw.split("\n---\n", 1)[1] if raw.startswith("---") else raw
    slides = [s for s in body.split("\n---\n") if s.strip()]

    parts = []
    for n, sl in enumerate(slides, 1):
        inner, notes = render_slide(sl)
        title = re.search(r"^# (.+)", sl, re.M)
        parts.append(
            f'<div class="wrap"><div class="num"><span>{n} / {len(slides)}</span>'
            f'<span>{html.escape(title.group(1)) if title else ""}</span></div>'
            f'<section class="slide">{inner}</section>'
            + (f'<div class="notes"><b>Speaker:</b> '
               f'{html.escape(re.sub(r"^Speaker:\s*", "", " ".join(notes)))}</div>' if notes else "")
            + "</div>")

    out = md_path.with_suffix(".html")
    out.write_text(
        f"<!doctype html><html><head><meta charset=utf-8>"
        f"<title>{html.escape(md_path.stem)} — slide preview</title><style>{CSS}</style></head><body>"
        f"<header><b>{html.escape(md_path.stem)}</b><span>{len(slides)} slides</span>"
        f"<label><input type=checkbox id=sn> speaker notes</label>"
        f"<span class=warn></span></header><main>{''.join(parts)}</main>"
        f"<script>{JS}</script></body></html>")
    return out


if __name__ == "__main__":
    targets = [Path(a).resolve() for a in sys.argv[1:]] or sorted((ROOT / "workshop/slides").glob("S*.md"))
    for t in targets:
        out = render_file(t)
        try:
            shown = out.relative_to(ROOT)
        except ValueError:
            shown = out
        print(f"wrote {shown}")
