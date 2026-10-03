"""Wiki lint — the rule that keeps every number traceable.

Fails on: a hand-typed metric (a decimal with 3+ places, or a percentage) in page prose;
an unknown {{< var key >}}; an unknown {{< yt ID >}}; a same-page @fig-/@tbl-/@sec- reference
without its anchor; a relative link to a .qmd that does not exist; a ```{mermaid} cell (it
needs a browser to render for the PDF -- use _assets/<name>.mmd and `make wiki-diagrams`); a
diagram PNG whose recorded source hash no longer matches its .mmd.
Code blocks, inline code, shortcodes, HTML comments and {attribute} blocks are not prose.
Stdlib only: CI runs this without the project's virtualenv.

    python -m wiki.tools.lint [--strict] [files…]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WIKI = Path(__file__).resolve().parents[1]
FACTS_JSON = WIKI / "facts" / "facts.json"
VIDEOS_JSON = WIKI / "_data" / "videos.json"
ALLOW = WIKI / "tools" / "lint_allow.txt"

_BLANK = lambda m: re.sub(r"[^\n]", " ", m.group(0))   # keep line numbers stable
FENCE = re.compile(r"^(```|~~~)[^\n]*\n.*?^\1[ \t]*$", re.M | re.S)
FRONT = re.compile(r"\A---\n.*?\n---\n", re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
SHORTCODE = re.compile(r"\{\{<.*?>\}\}", re.S)
INLINE = re.compile(r"`[^`\n]+`")
ATTRS = re.compile(r"\{(?:[#.][^{}\n]*|[^{}\n]*=[^{}\n]*)\}")
METRIC = re.compile(r"(?<![\w.])(\d+\.\d{3,}|\d+(?:\.\d+)?\s?%)")
VAR = re.compile(r"\{\{<\s*var\s+([\w.]+)\s*>\}\}")
YT = re.compile(r"\{\{<\s*yt\s+([\w-]+)\s*>\}\}")
XREF = re.compile(r"(?<![\w])@((?:fig|tbl|sec)-[\w-]+)")
ANCHOR = re.compile(r"\{#((?:fig|tbl|sec)-[\w-]+)")
LINK = re.compile(r"\]\((?!https?:|mailto:|#)([^)#\s]+\.qmd)(?:#[^)]*)?\)")


def _allow() -> tuple[set[str], set[tuple[str, str]]]:
    glob, per = set(), set()
    if ALLOW.exists():
        for line in ALLOW.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            if "::" in line:
                path, lit = line.split("::", 1)
                per.add((path.strip(), lit.strip()))
            else:
                glob.add(line)
    return glob, per


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def lint_text(rel: str, text: str, keys: set[str], videos: dict,
              page_path: Path | None = None) -> list[str]:
    problems = []
    live = text                          # what renders: no front matter, code or comments
    for rx in (FRONT, FENCE, COMMENT, INLINE):
        live = rx.sub(_BLANK, live)
    for m in VAR.finditer(live):
        if m.group(1) not in keys:
            problems.append(f"{rel}:{_line(live, m.start())}: unknown fact '{m.group(1)}'")
    for m in YT.finditer(live):
        if m.group(1) not in videos:
            problems.append(f"{rel}:{_line(live, m.start())}: unknown video '{m.group(1)}'")
    anchors = set(ANCHOR.findall(live))
    prose = live
    for rx in (SHORTCODE, ATTRS):
        prose = rx.sub(_BLANK, prose)
    for m in XREF.finditer(prose):
        if m.group(1) not in anchors:
            problems.append(f"{rel}:{_line(prose, m.start())}: cross-reference "
                            f"@{m.group(1)} has no anchor on this page")
    if page_path is not None:
        for m in LINK.finditer(prose):
            if not (page_path.parent / m.group(1)).resolve().exists():
                problems.append(f"{rel}:{_line(prose, m.start())}: broken link {m.group(1)}")
    glob, per = _allow()
    for m in METRIC.finditer(prose):
        lit = m.group(1).replace(" ", "")
        if lit in glob or (rel, lit) in per:
            continue
        problems.append(f"{rel}:{_line(prose, m.start())}: hand-typed number '{lit}' "
                        "— use {{< var … >}}")
    return problems


MERMAID = re.compile(r"^```\{mermaid\}", re.M)


def lint_diagrams(wiki: Path = WIKI) -> list[str]:
    """Each _assets/*.mmd has a PNG rendered from exactly this source (see wiki/tools/diagrams.py)."""
    import hashlib
    out = []
    for mmd in sorted((wiki / "_assets").glob("*.mmd")):
        png, sha = mmd.with_suffix(".png"), mmd.with_suffix(".png.sha")
        want = hashlib.sha256(mmd.read_bytes()).hexdigest()[:16]
        if not png.exists() or not sha.exists() or sha.read_text().strip() != want:
            out.append(f"_assets/{mmd.name}: the PNG is missing or older than its source -- run `make wiki-diagrams`")
    return out


def lint_all(wiki: Path = WIKI, files: list[Path] | None = None,
             strict: bool = False) -> list[str]:
    keys = set(json.loads(FACTS_JSON.read_text())) if FACTS_JSON.exists() else set()
    videos = json.loads(VIDEOS_JSON.read_text()) if VIDEOS_JSON.exists() else {}
    pages = files or sorted(p for p in wiki.rglob("*.qmd")
                            if not any(part.startswith("_") for part in p.relative_to(wiki).parts)
                            or p.parent.name == "_template")
    problems = []
    for p in pages:
        rel = str(p.relative_to(wiki))
        if rel == "reference/facts.qmd":
            continue                     # generated from facts.json; checked by tables.stale
        text = p.read_text()
        problems += lint_text(rel, text, keys, videos, page_path=p)
        for m in MERMAID.finditer(text):
            problems.append(f"{rel}:{_line(text, m.start())}: a {{mermaid}} cell needs a browser to render "
                            "for the PDF -- move it to _assets/<name>.mmd and run `make wiki-diagrams`")
    problems += lint_diagrams(wiki)
    if strict:
        problems += [f"_data/videos.json: '{k}' has no YouTube id yet"
                     for k, v in videos.items() if not v.get("youtube")]
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    strict = "--strict" in args
    files = [Path(a).resolve() for a in args if a != "--strict"] or None
    problems = lint_all(files=files, strict=strict)
    for p in problems:
        print(p)
    print(f"wiki lint: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
