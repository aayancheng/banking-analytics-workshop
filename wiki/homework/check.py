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
POPULATION = re.compile(r"booked|applicant|held.out|rejected|everyone|population", re.I)
NUMBER = re.compile(r"(?<![\w.])(\d+(?:\.(\d+))?)(?![\d.]\d)\s*(%)?")
SENTENCE = re.compile(r"(?<=[.!?;])\s+")
GATE_FAILS = re.compile(r"\b(fail|fails|failed|below|miss|misses|missed|not met|does not ship|"
                        r"doesn't ship|cannot ship|can't ship)\b", re.I)
GATE_PASSES = re.compile(r"(?<!not )(?<!n't )(?<!to )\b(pass|passes|passed|is met|clears|cleared)\b",
                         re.I)
FINDING = re.compile(r"^[ \t]*\*{0,2}F(\d+)\*{0,2}:\*{0,2}", re.M)
EVIDENCE = re.compile(r"(?:^|\s)\*{0,2}evidence\*{0,2}:\*{0,2}[ \t]*(.*)$", re.I | re.M)
VAR_KEY = re.compile(r"\{\{<\s*var\s+([\w.]+)\s*>\}\}")


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


def _numbers(text: str):
    """Every number in text as (as written, value as a fraction, decimal places as a fraction)."""
    for m in NUMBER.finditer(text):
        dp = len(m.group(2) or "")
        v = float(m.group(1))
        if m.group(3):
            v, dp = v / 100, dp + 2
        yield m.group(0).strip(), v, dp


def _sentences(text: str) -> list[str]:
    return [s for para in re.split(r"\n\s*\n", text)
            for s in SENTENCE.split(" ".join(para.split()))]


def h2_1(args):
    ans = _answer("H2.1")
    fact = json.loads(FACTS_JSON.read_text())["score.stress.no_bureau.auc"]
    value = float(fact["value"])
    nums = list(_numbers(ans))
    found = any(dp in (3, 4) and abs(v - round(value, dp)) < 1e-9 for _, v, dp in nums)
    if found or not nums:
        msg = f"you quote the no-bureau held-out AUC ({fact['text']}, recomputed)"
    else:
        nearest = min(nums, key=lambda n: abs(n[1] - value))[0]
        msg = (f"you quote the no-bureau held-out AUC ({fact['text']}, recomputed); "
               f"the nearest number in your answer is {nearest}")
    yield found, msg
    gate = [s for s in _sentences(ans) if re.search(r"\bgate\b", s, re.I)]
    fails = any(GATE_FAILS.search(s) for s in gate)
    passes = [s for s in gate if GATE_PASSES.search(s)]
    yield fails and not passes, ("you say the refit fails the gate" if fails and not passes
                                 else "the refit fails the gate: say so beside the word "
                                      "'gate' (and do not say it passes)")
    yield gates_intact()


def h2_2(args):
    ans = _answer("H2.2")
    want = _fact("score.pop.booked.auc")
    yield want in ans, f"you give the booked-only AUC ({want})"
    aucs = {round(float(v["value"]), 4) for k, v in json.loads(FACTS_JSON.read_text()).items()
            if ".auc" in k and isinstance(v.get("value"), (int, float))}
    bare = [shown for shown, value, context in _claims(ans)
            if round(value, 4) in aucs and not POPULATION.search(context)]
    yield not bare, ("every AUC names its population" if not bare
                     else f"these AUCs have no population in their sentence or table row: "
                          f"{', '.join(bare)}")


def _claims(text: str):
    """(number as written, value, context): the context is the number's sentence, or for a
    markdown table its row plus the table's header row."""
    lines, i = text.splitlines(), 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            header = lines[i]
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                for shown, value, _ in _numbers(lines[i]):
                    yield shown, value, lines[i] + " " + header
                i += 1
        else:
            j = i
            while j < len(lines) and not lines[j].lstrip().startswith("|"):
                j += 1
            for sentence in _sentences("\n".join(lines[i:j])):
                for shown, value, _ in _numbers(sentence):
                    yield shown, value, sentence
            i = j


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
    heads = list(FINDING.finditer(ans))
    findings = [ans[h.end(): nxt.start() if nxt else len(ans)]
                for h, nxt in zip(heads, heads[1:] + [None])]
    yield len(findings) >= 3, f"at least three findings (found {len(findings)})"
    for i, fnd in enumerate(findings, 1):
        ev = EVIDENCE.search(fnd)
        if not ev:
            yield False, f"finding {i} has no 'Evidence:' line"
            continue
        yield _evidence(ev.group(1), facts, i)


def _evidence(raw: str, facts: dict, i: int) -> tuple[bool, str]:
    var = VAR_KEY.search(raw)
    ref = var.group(1) if var else (raw.split() or [""])[0]
    ref = ref.strip("`*").rstrip(".,;").strip("`*")
    if not ref:
        return False, f"finding {i} gives no evidence after 'Evidence:'"
    if ref in facts:
        return True, f"finding {i} cites a fact ({ref})"
    if ref.startswith("wiki/mdd/"):
        return False, (f"finding {i} cites the documentation ({ref}); the documentation is "
                       "not evidence — cite a fact or the code")
    path = (ROOT / ref).resolve()
    ok = path.is_relative_to(ROOT) and path.is_file()
    return ok, (f"finding {i} cites a file that exists ({ref})" if ok
                else f"finding {i} cites neither a fact key nor a file in the repo ({ref})")


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
