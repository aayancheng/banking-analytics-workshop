"""Pre-render the wiki's mermaid diagrams to committed PNGs.

A ```{mermaid} cell is executed by Quarto in every profile -- even inside content hidden for
that profile -- and rendering it for Typst (the validation PDF, the book) needs a browser.
GitHub Codespaces has none, so `make wiki-pdf` failed there. So no page carries a mermaid cell:
the source lives in `_assets/<name>.mmd`, this script renders it to `_assets/<name>.png` with
Quarto's own mermaid renderer (needs Chrome -- an author-side step), and writes
`_assets/<name>.png.sha` with the source's hash. `wiki/tools/lint.py` fails when the hash no
longer matches the .mmd, so the picture cannot drift from its source.

    python -m wiki.tools.diagrams          # every _assets/*.mmd, or: make wiki-diagrams
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "_assets"


def source_sha(mmd: Path) -> str:
    return hashlib.sha256(mmd.read_bytes()).hexdigest()[:16]


def render(mmd: Path) -> Path:
    png = mmd.with_suffix(".png")
    with tempfile.TemporaryDirectory() as tmp:
        qmd = Path(tmp) / "diagram.qmd"
        qmd.write_text("---\nformat: typst\nmermaid-format: png\n---\n\n```{mermaid}\n" + mmd.read_text() + "```\n")
        r = subprocess.run(["quarto", "render", str(qmd), "--to", "typst"], capture_output=True, text=True)
        figs = sorted(Path(tmp).rglob("mermaid-figure-*.png"))
        if r.returncode or not figs:
            sys.exit(f"{mmd.name}: quarto could not render it (it needs Chrome)\n{r.stderr[-1500:]}")
        shutil.copy(figs[0], png)
    png.with_name(png.name + ".sha").write_text(source_sha(mmd) + "\n")
    return png


def main() -> int:
    for mmd in sorted(ASSETS.glob("*.mmd")):
        print(f"rendered {render(mmd).relative_to(ASSETS.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
