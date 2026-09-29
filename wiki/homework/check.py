"""Self-check an agent exercise. Recomputes; never trusts a pasted number.

    python -m wiki.homework.check H2.1
    python -m wiki.homework.check H4.1 --part performance

Answers go in wiki/homework/_answers/<ID>.md (gitignored). Exercises assume `main`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FACTS_JSON = ROOT / "wiki" / "facts" / "facts.json"
ANSWERS = ROOT / "wiki" / "homework" / "_answers"
MDD = ROOT / "wiki" / "mdd"
COMMITTED_GATE = 0.78        # the promise; see score/src/train.py and verify.py
TEMPLATE_PARTS = ["purpose", "data", "methodology", "assumptions", "performance",
                  "sensitivity", "limitations", "monitoring", "gate"]
POPULATION = re.compile(r"booked|applicants|held.out|rejected|everyone|population", re.I)
AUC_NUMBER = re.compile(r"\b0\.\d{3,4}\b")


class Missing(Exception):
    pass


def _fact(key: str) -> str:
    return json.loads(FACTS_JSON.read_text())[key]["text"]


def _answer(hid: str) -> str:
    p = ANSWERS / f"{hid}.md"
    if not p.exists():
        raise Missing(f"write your answer in wiki/homework/_answers/{hid}.md first")
    return p.read_text()


def gates_intact() -> tuple[bool, str]:
    train = (ROOT / "score/src/train.py").read_text()
    ver = (ROOT / "verify.py").read_text()
    a = re.search(r"^AUC_GATE\s*=\s*([\d.]+)", train, re.M)
    b = re.search(r"^SCORE_AUC_GATE\s*=\s*([\d.]+)", ver, re.M)
    ok = bool(a and b) and float(a.group(1)) == float(b.group(1)) == COMMITTED_GATE
    return ok, (f"the gate is {COMMITTED_GATE} in score/src/train.py and verify.py" if ok
                else "a gate was changed — the exercise is failed; restore it with "
                     "git checkout -- score/src/train.py verify.py")


def h2_1(args):
    ans = _answer("H2.1")
    want = _fact("score.stress.no_bureau.auc")
    yield want in ans, f"you quote the no-bureau held-out AUC ({want}, recomputed)"
    yield re.search(r"\bgate\b", ans, re.I) is not None, "you say what happened to the gate"
    yield gates_intact()


def h2_2(args):
    ans = _answer("H2.2")
    want = _fact("score.pop.booked.auc")
    yield want in ans, f"you give the booked-only AUC ({want})"
    bare = [m.group(0) for m in AUC_NUMBER.finditer(ans)
            if not POPULATION.search(ans[max(0, m.start() - 80): m.end() + 80])]
    yield not bare, ("every AUC names its population" if not bare
                     else f"these AUCs have no population beside them: {', '.join(bare)}")


def h4_1(args):
    from wiki.tools.lint import lint_all
    parts = [args.part] if args.part else TEMPLATE_PARTS
    for part in parts:
        p = MDD / "adjudication" / f"{part}.qmd"
        if not p.exists():
            yield False, f"wiki/mdd/adjudication/{part}.qmd does not exist yet (copy it from mdd/_template/)"
            continue
        text = p.read_text()
        body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
        body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
        yield len(body.split()) >= 150, f"{part}.qmd has at least 150 words of your own"
        yield "{{< var " in body, f"{part}.qmd cites at least one fact"
        problems = lint_all(files=[p]) if p.is_relative_to(ROOT / "wiki") else []
        yield not problems, (f"{part}.qmd lints clean" if not problems else problems[0])
    yield gates_intact()


def h4_2(args):
    ans = _answer("H4.2")
    facts = json.loads(FACTS_JSON.read_text())
    findings = re.findall(r"^F\d+:.*?(?=^F\d+:|\Z)", ans, re.M | re.S)
    yield len(findings) >= 3, f"at least three findings (found {len(findings)})"
    for i, fnd in enumerate(findings, 1):
        ev = re.search(r"evidence:\s*(\S+)", fnd, re.I)
        ref = ev.group(1).strip("`") if ev else ""
        ok = ref in facts or (ROOT / ref).exists()
        yield ok, f"finding {i} cites evidence that exists ({ref or 'none given'})"


CHECKS = {"H2.1": h2_1, "H2.2": h2_2, "H4.1": h4_1, "H4.2": h4_2}


def run(hid: str, part: str | None = None) -> tuple[bool, list[str]]:
    if hid not in CHECKS:
        return False, [f"unknown exercise {hid}; known: {', '.join(CHECKS)}"]
    lines, ok = [], True
    try:
        for passed, msg in CHECKS[hid](argparse.Namespace(part=part)):
            ok &= bool(passed)
            lines.append(("✅ " if passed else "❌ ") + msg)
    except Missing as e:
        return False, [f"❌ {e}"]
    return ok, lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Self-check an agent exercise.")
    ap.add_argument("id")
    ap.add_argument("--part", choices=TEMPLATE_PARTS)
    args = ap.parse_args(argv)
    ok, lines = run(args.id, args.part)
    print("\n".join(lines))
    if ok and args.id == "H4.2":
        print("Now compare your findings with D4.7 — which did the agent miss, and why?")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
