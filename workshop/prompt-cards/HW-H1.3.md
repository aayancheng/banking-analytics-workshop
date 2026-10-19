# Prompt Card HW-H1.3 — Catch: "Leaking the True PD Gives AUC ≈ 1.0" (Session 1 homework)

**Kind: Catch.** You are the reviewer. Below is an agent's summary of the leakage probe. It
reads well. Find what is wrong with it, have it measured, and write the correction.

**Goal.** A correction that gives each leaked column its own measured AUC, and says why even
the true PD cannot rank defaults perfectly.

---

## The transcript (read it before you go on)

> I ran the leakage probe from the Session 1 lab. Leaking the true PD
> (`pd_default_origination`) pushes the AUC to about 1.0, which is the classic red flag: any
> AUC that close to perfect means something leaked. The honest model gets about 0.73. The
> takeaway is that leakage is easy to catch — look for an AUC near 1.

Mark every claim in it you can check against the repository.

## The brief (copy, fill the blank, send)

> You are in the `banking-analytics-workshop` repo on `main`, at the repo root. Run Python
> with `.venv/bin/python`. Reviewer: **[YOUR NAME]**.
>
> 1. Run the leakage probe exactly as `workshop/labs/S1-lab.md` gives it, from a scratch
>    script outside the repository, and report the three AUCs to four decimals.
> 2. Which leaked column produces the AUC near 1.0? Which produces the one in between?
> 3. Read how `shared/data_generator.py` turns the true PD into `default`. Explain, in two or
>    three sentences, why a model that knows the true PD exactly still cannot reach 1.0.
> 4. Write the correction to `wiki/homework/_answers/H1.3.md`: a table with one row per
>    rung — the leaked column and its AUC — then the explanation.

---

## What "done" looks like

- A table whose rows name the leaked column (`none`, `pd_default_origination`, `default`)
  and give each its AUC.
- An explanation that rests on how the generator draws defaults, not on intuition.
- A sentence on what the transcript's takeaway gets wrong.

## Check it

```bash
python -m wiki.homework.check H1.3
```

The check refits the ladder. It wants the row naming the true PD to carry the true-PD rung's
AUC and the row naming `default` to carry the label rung's, and a sentence outside the table
that says why the true PD cannot rank perfectly.

## The trap

- **Two numbers, swapped.** The transcript is not wrong about the size of either number; it
  pins the 1.0 on the wrong column. A correction that only changes the digits misses that.
- **"Easy to catch."** An AUC near 1.0 is the leak nobody ships. The dangerous leak is the
  one whose number looks like a good model.
