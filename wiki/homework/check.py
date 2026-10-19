"""Self-check an agent exercise. Recomputes; never trusts a pasted number.

    python -m wiki.homework.check H1.2
    python -m wiki.homework.check H4.1 --part performance

Checked: H1.1, H1.2, H1.3, H2.1, H2.2, H3.1, H3.2, H3.3, H4.1, H4.2. H2.3 and H4.3 have no
check: their answers are explanations and a table of links, judged against the solution.

Answers go in wiki/homework/_answers/<ID>.md (gitignored). Exercises assume `main`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FACTS_JSON = ROOT / "wiki" / "facts" / "facts.json"
ANSWERS = ROOT / "wiki" / "homework" / "_answers"
MDD = ROOT / "wiki" / "mdd"
COMMITTED_GATE = 0.78        # the promise; see score/src/train.py and verify.py
COMMITTED_LEAKAGE = ["pd_default_origination", "default", "risk_based_rate", "booked",
                     "deterioration_next_6_12mo", "line_increase_good"]   # shared/config.py
TEMPLATE_PARTS = ["purpose", "data", "methodology", "assumptions", "performance",
                  "sensitivity", "limitations", "monitoring", "gate"]
POPULATION = re.compile(r"booked|applicant|held.out|rejected|everyone|population", re.I)
NUMBER = re.compile(r"(?<![\w.])(\d+(?:\.(\d+))?)(?![\d.]\d)\s*(%)?")
SENTENCE = re.compile(r"(?<=[.!?;])\s+")
FULL_SENTENCE = re.compile(r"(?<=[.!?])\s+")   # a gate verdict may span a ';'
GATE_FAILS = re.compile(r"\b(fail|fails|failed|below|miss|misses|missed|not met|does not ship|"
                        r"doesn't ship|cannot ship|can't ship)\b"
                        r"|(?:\bnot|n't)\s+(?:pass|clear|meet)\w*", re.I)
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


def _matches(value: float, v: float, dp: int, dps=(3, 4)) -> bool:
    """A number as written (v, with dp decimal places as a fraction) is `value`, rounded."""
    return dp in dps and abs(v - round(value, dp)) < 1e-9


def _quotes(text: str, value: float, msg: str, dps=(3, 4)) -> tuple[bool, str]:
    """Does text quote value, to three or four decimals or as a percentage (77.04%)? On a
    miss, name the nearest number written, so a wrong experiment is easy to spot."""
    nums = list(_numbers(text))
    found = any(_matches(value, v, dp, dps) for _, v, dp in nums)
    if found or not nums:
        return found, msg
    nearest = min(nums, key=lambda n: abs(n[1] - value))[0]
    return False, f"{msg}; the nearest number in your answer is {nearest}"


def _plain(text: str) -> str:
    """Thousands separators out (1,282 -> 1282), so counts and money parse as one number."""
    return re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)


def _counts(text: str) -> set[int]:
    return {int(v) for _, v, dp in _numbers(_plain(text)) if dp == 0}


MONEY = re.compile(r"(\d+(?:\.(\d+))?)\s?(k|mn|m|million|bn|b|billion)?(?![\w])", re.I)
UNIT = {"k": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9}


def _money(text: str):
    """Every amount in text in dollars, with the half-unit it was rounded to:
    $353.8M, 353.8 million, $0.35bn and 353,797,000 are all one amount."""
    for m in MONEY.finditer(_plain(text)):
        unit = UNIT.get((m.group(3) or "").lower(), 1.0)
        dp = len(m.group(2) or "")
        yield float(m.group(1)) * unit, max(0.5 * 10 ** -dp * unit, 1.0)


def _git(*args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def _untouched(*paths: str) -> tuple[bool, str]:
    """Nothing under these paths is modified, added or deleted (an answer belongs in
    wiki/homework/_answers/, which git ignores)."""
    out = _git("status", "--porcelain", "--", *paths)
    if out is None:
        return True, f"could not ask git about {', '.join(paths)}; check git status yourself"
    changed = sorted({line[3:] for line in out.splitlines() if line.strip()})
    if not changed:
        return True, f"nothing changed under {', '.join(paths)}"
    return False, (f"the agent changed {', '.join(changed[:3])}"
                   f"{' …' if len(changed) > 3 else ''}; the exercise must leave them as "
                   f"committed — restore with git checkout -- {' '.join(paths)} "
                   "(and delete new files it created there)")


def _leakage_intact() -> tuple[bool, str]:
    from shared.config import LEAKAGE_COLUMNS
    ok = list(LEAKAGE_COLUMNS) == COMMITTED_LEAKAGE
    return ok, ("the deny-list in shared/config.py is as committed" if ok else
                "LEAKAGE_COLUMNS in shared/config.py was changed — the exercise is failed; "
                "restore it with git checkout -- shared/config.py")


@lru_cache(maxsize=1)
def _ladder() -> dict:
    """The leakage ladder, recomputed through the facts layer's own probe."""
    from wiki.facts import ceiling, leakage
    from wiki.facts.data import score_split
    os.chdir(ROOT)
    split = score_split()
    lk = leakage.compute(split)
    lk.update(ceiling.compute_leakage(split, lk["leakage.honest.auc"].value))
    return lk


def _sentences(text: str, splitter: re.Pattern = SENTENCE) -> list[str]:
    return [s for para in re.split(r"\n\s*\n", text)
            for s in splitter.split(" ".join(para.split()))]


def h2_1(args):
    ans = _answer("H2.1")
    fact = json.loads(FACTS_JSON.read_text())["score.stress.no_bureau.auc"]
    value = float(fact["value"])
    yield _quotes(ans, value, f"you quote the no-bureau held-out AUC ({fact['text']}, recomputed)")
    gate = [s for s in _sentences(ans, FULL_SENTENCE) if re.search(r"\bgate\b", s, re.I)]
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
    path = (ROOT / ref).resolve()
    if path.is_relative_to(MDD.resolve()):
        return False, (f"finding {i} cites the documentation ({ref}); the documentation is "
                       "not evidence — cite a fact or the code")
    ok = path.is_relative_to(ROOT) and path.is_file()
    return ok, (f"finding {i} cites a file that exists ({ref})" if ok
                else f"finding {i} cites neither a fact key nor a file in the repo ({ref})")


# --- Session 1 -------------------------------------------------------------------------------
LEAK_LINE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?\*{0,2}LEAK\*{0,2}[ \t]*:\*{0,2}[ \t]*`?([A-Za-z_]\w*)`?"
                       r"[ \t]*[—–:-]*[ \t]*(.*)$", re.M)
DECISION_TIME = re.compile(r"decision|origination|application|underwrit", re.I)
ABSENT = re.compile(r"\b(not exist|doesn't exist|does not exist|not available|unavailable|"
                    r"not known|unknown|never|cannot|can't|no such|not observed|unobserved)\b",
                    re.I)
LABEL_WORD = re.compile(r"(?<![\w])default(?![\w])|\blabel\b|\boutcome\b|\banswer itself\b", re.I)
TRUEPD_WORD = re.compile(r"pd_default_origination|true PD|true probability", re.I)
WHY_NOT_ONE = re.compile(r"bernoulli|binomial|coin|draw|drawn|random|noise|noisy|chance|stochastic|"
                         r"probabilistic", re.I)


def h1_1(args):
    import pandas as pd
    from shared.config import LEAKAGE_COLUMNS, RAW
    ans = _answer("H1.1")
    cols = set(pd.read_parquet(RAW / "businesses.parquet").columns)
    want = [c for c in LEAKAGE_COLUMNS if c in cols]
    lines = LEAK_LINE.findall(ans)
    claimed = [c for c, _ in lines]
    yield bool(claimed), (f"you list {len(claimed)} column(s) as LEAK" if claimed else
                          "no 'LEAK: <column> — <why>' lines found")
    not_here = [c for c in claimed if c not in cols]
    for c in not_here:
        where = (" — it is on the deny-list, but it lives in portfolio.parquet only"
                 if c in LEAKAGE_COLUMNS else "")
        yield False, f"`{c}` is not a column of businesses.parquet{where}"
    missing = [c for c in want if c not in claimed]
    yield not missing, ("every deny-listed column of businesses.parquet is listed" if not missing
                        else f"missing from your LEAK lines: {', '.join(missing)}")
    extra = [c for c in claimed if c in cols and c not in LEAKAGE_COLUMNS]
    yield not extra, ("every column you list is on the deny-list" if not extra else
                      f"not on the deny-list: {', '.join(extra)} — a column that predicts is "
                      "not a leak unless it would not exist when the decision is made")
    thin = [c for c, why in lines if len(why.split()) < 4]
    yield not thin, ("every LEAK line says why" if not thin else
                     f"say why in a few words: {', '.join(thin)}")
    yield _leakage_intact()


def h1_2(args):
    ans = _answer("H1.2")
    lk = _ladder()
    truepd, honest = lk["leakage.truepd.auc"], lk["leakage.honest.auc"]
    yield _quotes(ans, truepd.value, f"you quote the true-PD rung ({truepd.text()}, recomputed)")
    yield _quotes(ans, honest.value, f"you quote the honest rung ({honest.text()}, recomputed)")
    said = any(DECISION_TIME.search(s) and ABSENT.search(s) for s in _sentences(ans))
    yield said, ("you say the true PD does not exist when the decision is made" if said else
                 "say, in one sentence, why this rung cannot ship: the true PD does not exist "
                 "at decision time")
    probes = _probes_left()
    if probes is not None:
        yield not probes, ("no probe script left in the repository" if not probes else
                           f"delete the probe now you have its number: {', '.join(probes)}")
    yield _leakage_intact()


def _probes_left() -> list[str] | None:
    """Untracked scripts in the repository that fit or score a model on the true PD
    (None if git cannot be asked)."""
    left = _git("ls-files", "--others", "--exclude-standard")
    if left is None:
        return None
    return [f for f in left.splitlines() if f.endswith((".py", ".ipynb"))
            and _is_probe((ROOT / f).read_text(errors="ignore"))]


def _is_probe(code: str) -> bool:
    """A script that fits or scores a model with the true PD in it."""
    return "pd_default_origination" in code and bool(re.search(r"roc_auc_score|\.fit\(", code))


def h1_3(args):
    ans = _answer("H1.3")
    lk = _ladder()
    truepd, label = lk["leakage.truepd.auc"], lk["leakage.label.auc"]
    rows = [l for l in ans.splitlines() if l.lstrip().startswith("|")]
    pd_rows = [r for r in rows if TRUEPD_WORD.search(r)]
    lab_rows = [r for r in rows if LABEL_WORD.search(r) and not TRUEPD_WORD.search(r)]
    ok_pd = any(_matches(truepd.value, v, dp) for r in pd_rows for _, v, dp in _numbers(r))
    yield ok_pd, (f"your table gives the true-PD leak its AUC ({truepd.text()}, recomputed)"
                  if ok_pd else f"no table row naming the true PD (pd_default_origination) "
                                f"carries its recomputed AUC, {truepd.text()}")
    ok_lab = any(_matches(label.value, v, dp, (1, 2, 3, 4))
                 for r in lab_rows for _, v, dp in _numbers(r))
    yield ok_lab, (f"your table gives the label leak its AUC ({label.text()}, recomputed)"
                   if ok_lab else f"no table row naming the label (`default`) carries its "
                                  f"recomputed AUC, {label.text()}")
    why = [s for s in _sentences("\n".join(l for l in ans.splitlines() if l not in rows))
           if WHY_NOT_ONE.search(s)]
    yield bool(why), ("you say why even the true PD cannot rank perfectly" if why else
                      "say why leaking the true PD cannot reach 1.0: what turns a PD into a "
                      "default in the generator?")


# --- Session 3 -------------------------------------------------------------------------------
DECISIONS = ["Approve", "Refer", "Decline"]
BOOK_WORD = re.compile(r"book|applicant|12000|population|portal", re.I)
OVERRIDE_WORD = re.compile(r"override|dscr_refer_hi|thin", re.I)
ROUND_WORD = re.compile(r"\bround|\b4 ?dp\b|four decimal|decimal places|precision", re.I)
RAW_WORD = re.compile(r"unrounded|raw prob|full[- ]precision|predict_proba|not rounded|"
                      r"before (it is |it's )?round|ews_prob_raw", re.I)
MONEY_WORD = re.compile(r"\bEAD\b|exposure|dollar|\$|money|amount|balance|million|\bbn\b|"
                        r"billion", re.I)
WORST_WORD = re.compile(r"\b(worst|most|highest|largest|biggest)\b", re.I)


@lru_cache(maxsize=1)
def _h3_1_decisions():
    """decide() over all 12,000 applicants exactly as app/main.py runs it at start-up, with
    the committed policy and with the exercise's what-if: the DSCR knockout floor raised to
    the thin-margin override's upper edge, dscr_refer_hi."""
    from dataclasses import replace

    import joblib
    import pandas as pd
    from adjudication.src.feature_engineering import (ADJ_FEATURE_COLUMNS,
                                                      compute_adjudication_features)
    from adjudication.src.policy import PolicyConfig, decide
    from shared.config import RAW
    models = ROOT / "adjudication" / "models"
    biz = pd.read_parquet(RAW / "businesses.parquet")
    cfg = PolicyConfig.from_dict(json.loads((models / "policy_config.json").read_text()))
    X_all = compute_adjudication_features(biz)
    p = joblib.load(models / "adjudication_model.pkl").predict_proba(
        X_all[ADJ_FEATURE_COLUMNS])[:, 1]
    base = decide(X_all, p, cfg)["decision"].to_numpy()
    moved = decide(X_all, p, replace(cfg, dscr_floor=cfg.dscr_refer_hi))["decision"].to_numpy()
    return base, moved


def h3_1(args):
    ans = _answer("H3.1")
    base, moved = _h3_1_decisions()
    flipped = int((base != moved).sum())
    counts = _counts(ans)
    yield flipped in counts, (f"you give the number of decisions that change ({flipped:,}, "
                              "recomputed)" if flipped in counts else
                              f"the number of decisions that change is missing ({flipped:,}, "
                              "recomputed over all applicants)")
    for k in DECISIONS:
        n, share = int((moved == k).sum()), float((moved == k).mean())
        ok = n in counts or any(_matches(share, v, dp) for _, v, dp in _numbers(ans))
        yield ok, (f"you give the new {k} count or share ({n:,}, {share:.1%})" if ok else
                   f"the new {k} count or share is missing ({n:,}, {share:.1%}, recomputed)")
    scoped = [s for s in _sentences(_plain(ans)) if str(flipped) in s]
    named = any(BOOK_WORD.search(s) for s in scoped)
    yield named or not scoped, ("you say which population the change is counted on" if named
                                or not scoped else
                                "the sentence that gives the changed decisions does not say "
                                "on whom: all applicants, as the portal decides them")
    why = bool(OVERRIDE_WORD.search(ans))
    yield why, ("you name the override that explains why Approve does not move" if why else
                "explain the Approve count: which rule already holds the files between the "
                "old and the new floor?")
    yield _untouched("adjudication")


@lru_cache(maxsize=1)
def _by_band() -> tuple[dict, dict]:
    """Mispriced share and mispriced EAD by score band, as the portal prices the book."""
    from pricing.src.portfolio import portfolio_summary, price_population
    os.chdir(ROOT)
    df = price_population()
    rate = {r["key"]: r["mispriced_rate"] for r in portfolio_summary(df)["by_band"]}
    return rate, df[df["mispriced"]].groupby("score_band")["ead"].sum().to_dict()


def h3_2(args):
    ans = _answer("H3.2")
    rate, ead = _by_band()
    by_rate, by_ead = max(rate, key=rate.get), max(ead, key=ead.get)
    band = lambda b: re.compile(rf"(?<![\w.]){re.escape(b)}(?![\w])")
    ok = any(band(by_rate).search(ctx) and _matches(rate[by_rate], v, dp)
             for ctx in _contexts(ans) for _, v, dp in _numbers(ctx))
    yield ok, (f"by share, band {by_rate} with its mispriced share ({rate[by_rate]:.1%}, "
               "recomputed)" if ok else
               f"name the band with the highest mispriced share and the share: recomputed, "
               f"band {by_rate} at {rate[by_rate]:.1%}, in one sentence or table row")
    ok = any(band(by_ead).search(ctx) and abs(v - ead[by_ead]) <= tol
             for ctx in _contexts(ans) for v, tol in _money(ctx))
    yield ok, (f"by money, band {by_ead} with its mispriced EAD (${ead[by_ead]:,.0f}, "
               "recomputed)" if ok else
               f"name the band with the most mispriced EAD and the amount: recomputed, band "
               f"{by_ead} at ${ead[by_ead]:,.0f}, in one sentence or table row")
    own = "\n".join(l for l in ans.splitlines()        # the claim, quoted, is not yours
                    if not l.lstrip().startswith(("#", ">")))
    own = re.sub(r'"[^"\n]*"|“[^”\n]*”', '""', own)
    bare = [s for s in _sentences(own) if re.search(rf"\bband {by_ead}\b", s, re.I)
            and WORST_WORD.search(s) and not MONEY_WORD.search(s)]
    yield not bare, ("every 'worst' says by what measure" if not bare else
                     f"'worst' without its measure: \"{bare[0][:90]}\" — by share or by EAD?")


@lru_cache(maxsize=1)
def _rounded_flips() -> list[str]:
    """Accounts whose tier changes when the book is re-tiered from the persisted prob with
    the committed cutoffs -- score_population's own columns, nothing else."""
    from ews.src import watchlist as wl
    os.chdir(ROOT)
    book = wl.score_population()
    tiers = json.loads((ROOT / "ews" / "models" / "metadata.json").read_text())["tiers"]
    rounded = [wl.risk_tier(p, tiers) for p in book["prob"]]
    return sorted(book["business_id"][book["risk_tier"].to_numpy() != rounded])


def h3_3(args):
    ans = _answer("H3.3")
    flipped = _rounded_flips()
    missed = [b for b in flipped if b not in ans]
    yield not missed, (f"you name every account the defect re-tiers ({', '.join(flipped)}, "
                       "recomputed)" if not missed else
                       f"the defect re-tiers {len(flipped)} account(s) with the committed "
                       f"cutoffs; your answer does not name {', '.join(missed)}")
    yield bool(ROUND_WORD.search(ans)), ("you name the cause: the persisted prob is rounded"
                                         if ROUND_WORD.search(ans) else
                                         "name the cause: what was done to the prob column "
                                         "before it was stored?")
    yield bool(RAW_WORD.search(ans)), ("you name the fix: re-tier from the unrounded "
                                       "probability" if RAW_WORD.search(ans) else
                                       "name the fix: which probability should a what-if "
                                       "re-tier from?")
    yield _untouched("ews", "app")


def _contexts(text: str):
    """Each sentence, and each markdown table row with its header row."""
    seen = set()
    for _, _, ctx in _claims(text):
        if ctx not in seen:
            seen.add(ctx)
            yield ctx


CHECKS = {"H1.1": h1_1, "H1.2": h1_2, "H1.3": h1_3, "H2.1": h2_1, "H2.2": h2_2,
          "H3.1": h3_1, "H3.2": h3_2, "H3.3": h3_3, "H4.1": h4_1, "H4.2": h4_2}


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
