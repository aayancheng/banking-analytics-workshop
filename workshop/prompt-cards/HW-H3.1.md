# Prompt Card HW-H3.1 — Move a Policy Threshold (Session 3 homework)

**Kind: Build.** You are the credit officer. The agent re-runs the decision layer with one
policy value moved; you decide whether its explanation of what changed is the real one.

**Goal.** The decision mix before and after the DSCR knockout floor is raised to 1.2, how many
decisions change and between which outcomes, and why — with the committed policy untouched.

---

## The brief (copy, fill the blank, send to your agent)

> You are in the `banking-analytics-workshop` repo on `main`, at the repo root. Run Python
> with `.venv/bin/python`. Reviewer: **[YOUR NAME]**.
>
> **Task:** a what-if on the adjudication policy. The credit committee proposes raising the
> DSCR knockout floor (`dscr_floor`) to 1.2, the value of `dscr_refer_hi`.
>
> 1. Score all 12,000 applicants the way `app/main.py` does at start-up: the saved model in
>    `adjudication/models/adjudication_model.pkl` on `compute_adjudication_features`, then
>    `adjudication.src.policy.decide` with `PolicyConfig.from_dict` of
>    `adjudication/models/policy_config.json`.
> 2. Run `decide` again with only `dscr_floor` changed (use `dataclasses.replace` on the
>    config). Do not edit `policy_config.json` and change no file under `adjudication/`.
>    Work in a scratch script outside the repository.
> 3. Report the decision counts before and after, the number of decisions that change, and a
>    cross-tab of old against new decisions. Name the population.
> 4. Explain the shift from `adjudication/src/policy.py`: which decisions moved, which did
>    not, and which rule explains each.
> 5. Write the report to `wiki/homework/_answers/H3.1.md`.

---

## What "done" looks like

- Counts for Approve, Refer and Decline, before and after, on all applicants.
- The number of changed decisions and where they moved from and to.
- An explanation that names the rule responsible for every number that did *not* move.

## Check it

```bash
python -m wiki.homework.check H3.1
```

The check re-runs `decide` both ways itself. It wants the number of changed decisions, the
new count or share of each decision, the population, a sentence saying Approve does not
change and the rule that explains it, no other Approve count, and nothing changed under
`adjudication/`.

## The trap

- **The expected answer.** Raise a knockout floor and you expect fewer approvals. Look at the
  Approve count before writing the explanation.
- **Editing the policy.** Changing `policy_config.json` changes the platform, not a what-if.
  Every later module, the portal and `verify.py` read it. If that happened:
  `git checkout -- adjudication/`.
- **Which population.** This exercise uses the whole book — all applicants, as the portal
  decides them — not the held-out 20% that D5 measures. The counts differ; say which you used.
  The whole book's PDs are mostly in-sample, so this describes what the platform decides, not
  how well the model performs.
