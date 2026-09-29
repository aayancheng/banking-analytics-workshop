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
               skip_prefixes: tuple[str, ...] = ()) -> list[str]:
    """Compare what a reader would see — the printed text — plus the population, source
    and format that travel with it. skip_prefixes (the fast path passes the slow stress
    refits' prefixes) excuses committed facts that were deliberately not recomputed; any
    other committed fact that no module computed is a problem."""
    problems = []
    for k in sorted(set(fresh) | set(committed)):
        if k not in committed:
            problems.append(f"{k}: new, not in facts.json")
        elif k not in fresh:
            if k.startswith(skip_prefixes):
                continue
            problems.append(f"{k}: in facts.json but not computed by any module")
        else:
            c, f = committed[k], fresh[k]
            if f.text() != c.get("text"):
                problems.append(f"{k}: facts.json says {c.get('text')}, recomputed {f.text()}")
            for field in ("population", "source", "fmt"):
                if getattr(f, field) != c.get(field):
                    problems.append(f"{k}: facts.json {field} is {c.get(field)!r}, "
                                    f"recomputed {getattr(f, field)!r}")
    return problems
