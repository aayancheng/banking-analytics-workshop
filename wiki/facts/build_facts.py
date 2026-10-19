"""Compute every number the wiki prints, through the modules' own functions.

    python -m wiki.facts.build_facts          # fast facts; keeps the cached slow refits
    python -m wiki.facts.build_facts --full   # also re-runs the stress refits and the EWS oracle refit

Writes wiki/facts/facts.json (committed), wiki/_variables.yml (for {{< var key >}}, via
tables.render_all so verify.py checks it too),
the generated tables in wiki/_generated/, reference/facts.qmd, the D4 figures, the D6 figure, the D7 figure and the D8 figure.
verify.py recomputes the fast facts (the slow refits only under --full), checks every
generated file, and fails on any difference.
"""
from __future__ import annotations

import argparse
import os
import re

from shared.config import ROOT
from wiki.facts import (adj_facts, ceiling, ews_facts, figures, leakage, li_facts, policy,
                        pricing_facts, score_facts, score_stress, tables)
from wiki.facts.core import Fact, dump_facts, load_facts
from wiki.facts.data import score_split

WIKI = ROOT / "wiki"
FACTS_JSON = WIKI / "facts" / "facts.json"
GENERATED = WIKI / "_generated"
FIG_DIR = WIKI / "mdd" / "score" / "fig"
PRICING_FIG_DIR = WIKI / "mdd" / "pricing" / "fig"
EWS_FIG_DIR = WIKI / "mdd" / "ews" / "fig"
LI_FIG_DIR = WIKI / "mdd" / "line_increase" / "fig"
FACT_INDEX = WIKI / "reference" / "facts.qmd"
KEY_SEGMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")   # also enforced by wiki/tools/lint.py
SLOW_PREFIXES = ("score.stress.", "ceiling.ews.oracle_model.")


def compute(full: bool) -> tuple[dict[str, Fact], dict]:
    os.chdir(ROOT)
    split = score_split()
    facts, exhibits = score_facts.compute(split)
    facts.update(adj_facts.compute(split))
    facts.update(pricing_facts.compute())
    facts.update(ceiling.compute(split))
    lk = leakage.compute(split)
    facts.update(lk)
    facts.update(ceiling.compute_leakage(split, lk["leakage.honest.auc"].value))
    es = ews_facts.ews_split()
    facts.update(ews_facts.compute(es))
    facts.update(ceiling.compute_ews(es))
    ls = li_facts.li_split()
    facts.update(li_facts.compute(ls, es))
    facts.update(ceiling.compute_li(ls))
    facts.update(policy.compute())
    if full:
        facts.update(score_stress.compute(split))
        facts.update(ceiling.compute_ews_oracle(es))
    return facts, exhibits


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--full", action="store_true", help="re-run the slow refits (score stress, EWS oracle)")
    args = ap.parse_args(argv)
    facts, exhibits = compute(args.full)
    if not args.full and FACTS_JSON.exists():
        for k, d in load_facts(FACTS_JSON).items():
            if k.startswith(SLOW_PREFIXES):
                facts[k] = Fact(d["value"], d["fmt"], d["source"], d["population"])
    missing = [p for p in SLOW_PREFIXES if not any(k.startswith(p) for k in facts)]
    if missing:
        raise SystemExit(f"No cached slow refits for {missing} yet. Run once: make wiki-facts-full")
    bad = [k for k in facts if not all(KEY_SEGMENT.match(seg) for seg in k.split("."))]
    if bad:   # Quarto's {{< var >}} cannot address a segment like "1" (a YAML integer key)
        raise SystemExit(f"Fact keys Quarto cannot print, rename them: {bad}")
    dump_facts(facts, FACTS_JSON)
    text = {k: f.text() for k, f in facts.items()}
    tables.write_all(text, load_facts(FACTS_JSON), WIKI)
    figures.write_all(exhibits, FIG_DIR)
    figures.write_pricing(text, PRICING_FIG_DIR)
    figures.write_ews(text, EWS_FIG_DIR)
    figures.write_li(text, LI_FIG_DIR)
    print(f"{len(facts)} facts → {FACTS_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
