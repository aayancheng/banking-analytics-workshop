# Lab 4 — Draft D5 with an agent, then turn it into a validator (S4, 30 + 12 min)

**Checkpoint:** `main` — where you already are after Sessions 2 and 3. No stage jump tonight:
the wiki lives on `main` only, like `notebooks/` and `workshop/`.

> **First commands**, in your Codespace terminal:
>
> ```bash
> git stash -u && git checkout main && git pull
> python verify.py        # ✅ Stage 5 verified — you are here, and it works
> ```
>
> The first line works wherever you are — on `main`, or on a stage tag from an earlier session —
> and stashes any local changes rather than losing them. "Stage 5 verified" is the right answer.
> Did not rebuild the container? You lose the rendered preview and nothing else: the lint and
> the check below are plain Python.

**What you are building.** D5, the Loan Adjudication chapter of the model documentation, is a
stub (`wiki/mdd/adjudication/index.qmd`). D4, the Business Credit Score, is complete and is
your worked example. Every model chapter has the same nine parts; tonight each pair drafts
**one** of them for D5, with an AI agent, until a machine check says it is done.

---

## Part A — draft one part of D5 (H4.1, 30 min)

### Step 1 — pick your part (1 min)

The facilitator assigns parts in chat so all nine are covered:

`purpose` · `data` · `methodology` · `assumptions` · `performance` · `sensitivity` ·
`limitations` · `monitoring` · `gate`

### Step 2 — copy the template (1 min)

```bash
cp wiki/mdd/_template/<part>.qmd wiki/mdd/adjudication/
```

Open the copy. The HTML comment at the top says what the part must cover. It stays in the
file; it does not count towards your words.

### Step 3 — see which facts exist (2 min)

```bash
grep -A5 '"adj\.' wiki/facts/facts.json
```

These are the adjudication model's numbers: its held-out AUC and lift, both gates, the two
PD-zone cutoffs, the decision mix, the row counts and the number of features. For each key,
`text` is what the page will show and `population` is who it was measured on — the sentence
that uses it must name that population. A `score.*` key is
the **scorecard's** number, not the adjudication model's; use one only when you mean the
scorecard.

Anything the facts do not contain is **"not yet measured"**. Do not let the agent invent it.

### Step 4 — brief the agent (15–20 min)

Open [`workshop/prompt-cards/HW-H4.1.md`](../prompt-cards/HW-H4.1.md), copy the brief, fill
in your name and your part, and send it to your agent (Copilot Chat in agent mode, or Claude
Code). The brief tells it to read D4's version of the same part
(`wiki/mdd/score/<part>.qmd`) as the example, to cite every number as
`{{< var key >}}`, and to change no other file.

While it works, one of you reads the matching D4 page; the other reads the code it will
describe (`adjudication/src/policy.py` for the cutoffs and rules, `adjudication/src/train.py`
for the gates).

### Step 5 — check, and iterate until every line is ✅ (5–10 min)

```bash
python -m wiki.homework.check H4.1 --part <part>
```

A passing check looks like this:

```text
✅ performance.qmd has at least 150 words of your own
✅ performance.qmd cites at least one fact
✅ performance.qmd lints clean
✅ the gate is 0.78 in score/src/train.py and verify.py
```

Paste any ❌ line back to the agent and ask it to fix that, and only that.

### Step 6 — read two claims yourself (3 min)

The check proves every number is traceable. It does not prove the sentence around it is true.
Pick two claims the draft makes about the model and find them in `adjudication/src/`. If one
is wrong, that is the most useful thing you will learn tonight — tell the room at 1:08.

### Optional — see it rendered (needs the rebuilt Codespace)

```bash
make wiki          # Quarto preview; open the forwarded port it prints
```

---

## If your check fails

| The ❌ line says | What it means | Fix |
|---|---|---|
| `<part>.qmd does not exist yet` | the copy did not happen, or went to the wrong folder | `cp wiki/mdd/_template/<part>.qmd wiki/mdd/adjudication/` |
| `has at least 150 words of your own` | the template comment and the front matter do not count | ask the agent for more substance, not padding: the population, the decision, what is not yet measured |
| `cites at least one fact` | no `{{< var … >}}` in the prose | cite the fact the sentence is about, e.g. `{{< var adj.auc >}}` |
| `hand-typed number '…' — use {{< var … >}}` | a number typed into the prose: a decimal with three or more places, or any percentage — including "the top 20%" | use or add a fact. Use: `grep -A5 '"adj\.' wiki/facts/facts.json`. None fits: write "not yet measured", or rephrase without the number |
| `unknown fact '…'` | the key is misspelled, or it does not exist | check the spelling against `facts.json`. If you pulled new facts, `make wiki-facts`. A genuinely new number is added in `wiki/facts/adj_facts.py`, then `make wiki-facts` — homework, not tonight |
| `broken link …` or `cross-reference … has no anchor` | a link to a page or anchor that does not exist | point it at a real page, e.g. `../score/performance.qmd` |
| `a gate was changed — the exercise is failed` | `AUC_GATE` in `score/src/train.py` or `SCORE_AUC_GATE` in `verify.py` is no longer 0.78 | `git checkout -- score/src/train.py verify.py` |

**Never** add a number to `wiki/tools/lint_allow.txt` to make the lint pass. That silences the
check and leaves the number untraceable — the exact failure this chapter exists to prevent.

**After the lab**, `python verify.py` lints every page in the wiki, yours included. A draft
that does not lint clean turns `[9/10] Docs: model wiki` red. That is correct: the
documentation is part of the platform. Finish the draft, or move it aside
(`mv wiki/mdd/adjudication/<part>.qmd /tmp/`) until you do.

---

## Part B — turn the agent into a validator (H4.2, 12 min, together)

The facilitator runs this one live; follow along, or run it yourself if you are ahead.

1. Open [`workshop/prompt-cards/HW-H4.2.md`](../prompt-cards/HW-H4.2.md). The agent reviews
   D4 **without** opening `wiki/mdd/score/limitations.qmd` — D4's own five findings.
2. It writes at least three findings to `wiki/homework/_answers/H4.2.md` (a folder git
   ignores), each with one piece of evidence: a fact key or a file in the repo.
3. Check it:

   ```bash
   python -m wiki.homework.check H4.2
   ```

4. **The room judges.** For each finding: a real finding, an observation, or noise? Then open
   `limitations.qmd` and compare. Which of D4's five did the agent miss — did it not look, or
   could it not have seen it?

Evidence is never the documentation: "the chapter says so" proves what the document claims,
not what the model does. The check rejects a page from `wiki/mdd/` as evidence.

---

## Homework

The *Course* tab of the wiki → **Session 4 homework** (`wiki/course/homework-s4.qmd`), each
exercise with a worked solution:

- **H4.1** — finish D5: all nine parts. `python -m wiki.homework.check H4.1` (no `--part`)
  checks the whole chapter.
- **H4.2** — the validator review, if you did not run it yourself.
- **H4.3** — extend the regulatory crosswalk for one module.

After any exercise, `python verify.py` should still be green. If it is not, the agent changed
something it was told not to: `git status` shows what, and `git checkout -- <path>` puts it
back.
