"""Compute every number the wiki prints, through the modules' own functions.

    python -m wiki.facts.build_facts          # fast facts; keeps the cached slow refits
    python -m wiki.facts.build_facts --full   # also re-runs the stress refits (a few seconds)

Writes wiki/facts/facts.json (committed), wiki/_variables.yml (for {{< var key >}}, via
tables.render_all so verify.py checks it too),
the generated tables in wiki/_generated/, reference/facts.qmd and the D4 figures.
verify.py recomputes the fast facts (the stress refits only under --full), checks every
generated file, and fails on any difference.
"""
from __future__ import annotations

import argparse
import os

from shared.config import ROOT
from wiki.facts import adj_facts, ceiling, figures, policy, score_facts, score_stress, tables
from wiki.facts.core import Fact, dump_facts, load_facts
from wiki.facts.data import score_split

WIKI = ROOT / "wiki"
FACTS_JSON = WIKI / "facts" / "facts.json"
GENERATED = WIKI / "_generated"
FIG_DIR = WIKI / "mdd" / "score" / "fig"
FACT_INDEX = WIKI / "reference" / "facts.qmd"
SLOW_PREFIXES = ("score.stress.",)


def compute(full: bool) -> tuple[dict[str, Fact], dict]:
    os.chdir(ROOT)
    split = score_split()
    facts, exhibits = score_facts.compute(split)
    facts.update(adj_facts.compute())
    facts.update(ceiling.compute(split))
    facts.update(policy.compute())
    if full:
        facts.update(score_stress.compute(split))
    return facts, exhibits


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--full", action="store_true", help="re-run the slow stress refits")
    args = ap.parse_args(argv)
    facts, exhibits = compute(args.full)
    if not args.full and FACTS_JSON.exists():
        for k, d in load_facts(FACTS_JSON).items():
            if k.startswith(SLOW_PREFIXES):
                facts[k] = Fact(d["value"], d["fmt"], d["source"], d["population"])
    if not any(k.startswith(SLOW_PREFIXES) for k in facts):
        raise SystemExit("No cached stress refits yet. Run once: make wiki-facts-full")
    dump_facts(facts, FACTS_JSON)
    text = {k: f.text() for k, f in facts.items()}
    tables.write_all(text, load_facts(FACTS_JSON), WIKI)
    figures.write_all(exhibits, FIG_DIR)
    print(f"{len(facts)} facts → {FACTS_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
