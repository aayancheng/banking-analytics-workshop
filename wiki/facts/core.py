"""The facts layer's plumbing: one record per number, a JSON cache, the YAML Quarto reads.

A fact carries its value, how it is printed, the function that produced it and the
population it was measured on — so no page can print an AUC without its population.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Fact:
    value: float | int | str
    fmt: str          # a Python format spec: ".4f", ",d", ".1%"; "" for strings
    source: str       # the function or file that produced it
    population: str   # what it was measured on

    def text(self) -> str:
        return format(self.value, self.fmt) if self.fmt else str(self.value)

    def to_json(self) -> dict:
        value = round(self.value, 6) if isinstance(self.value, float) else self.value
        return {"value": value, "text": self.text(), "fmt": self.fmt,
                "source": self.source, "population": self.population}


def dump_facts(facts: dict[str, Fact], path: Path) -> None:
    data = {k: facts[k].to_json() for k in sorted(facts)}
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def load_facts(path: Path) -> dict[str, dict]:
    return json.loads(path.read_text())


def nest(flat: dict[str, str]) -> dict:
    """{"a.b": v} -> {"a": {"b": v}} — the shape Quarto's var shortcode walks."""
    out: dict = {}
    for key in sorted(flat):
        *parents, leaf = key.split(".")
        node = out
        for p in parents:
            node = node.setdefault(p, {})
            if not isinstance(node, dict):
                raise ValueError(f"fact key {key!r} collides with a leaf")
        if leaf in node:
            raise ValueError(f"fact key {key!r} collides with a branch")
        node[leaf] = flat[key]
    return out


def to_yaml(tree: dict, indent: int = 0) -> str:
    """Nested dict of strings -> YAML. JSON-quoted scalars are valid YAML (no PyYAML here)."""
    lines = []
    for k in sorted(tree):
        v = tree[k]
        if isinstance(v, dict):
            lines.append(" " * indent + f"{k}:")
            lines.append(to_yaml(v, indent + 2))
        else:
            lines.append(" " * indent + f"{k}: {json.dumps(v)}")
    return "\n".join(lines)


def diff_facts(fresh: dict[str, Fact], committed: dict[str, dict],
               partial: bool = False) -> list[str]:
    """Compare printed text, not floats: what matters is what a reader would see.
    partial=True (the fast path) ignores committed facts that were not recomputed."""
    problems = []
    for k in sorted(set(fresh) | set(committed)):
        if k not in committed:
            problems.append(f"{k}: new, not in facts.json")
        elif k not in fresh:
            if not partial:
                problems.append(f"{k}: in facts.json but no longer computed")
        elif fresh[k].text() != committed[k]["text"]:
            problems.append(f"{k}: facts.json says {committed[k]['text']}, "
                            f"recomputed {fresh[k].text()}")
    return problems
