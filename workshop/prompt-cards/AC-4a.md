# Prompt Card AC-4a — Train the EWS, Report It Honestly (Session 4)

**Review focus tonight:** does the agent's evaluation *report the honest gate* — or does it slip back to raw AUC and start apologizing (or worse, "improving")?

---

## The brief (copy, fill blank, send)

> You are in the `banking-analytics-workshop` repo at `stage-4` (venv at `.venv`). Reviewer: **[YOUR NAME]**.
>
> **Task:** train the Early Warning deterioration model and write me an evaluation report.
>
> 1. Run `make train-ews`. Report every metric the trainer prints.
> 2. Write `ews_eval_[YOUR NAME].md`: model purpose (one paragraph), the metrics, and a **verdict paragraph judging the model against its committed gate** — read the gate's definition and rationale from `verify.py` and `ews/src/train.py` before writing.
> 3. In the verdict, answer explicitly: is AUC gated for this model? Why or why not? What IS gated, and did the model pass?
> 4. Do not tune hyperparameters. Do not modify any file. If any gate fails, STOP and report.

---

## Your review checklist

- [ ] The trap: does the verdict treat AUC 0.662 as a problem to fix? If it proposes "improvements to reach 0.78," it has missed the entire point — send it back with one question: *"what is the oracle ceiling of this target?"*
- [ ] Does the verdict cite capture (2.16×) and PR-AUC vs base (0.308 > 0.180) as the operative gates?
- [ ] Run `python workshop/labs/oracle_ceiling.py` yourself; check the agent's verdict is consistent with the three numbers.
- [ ] `python verify.py` — as always, the checkpoint is yours to run.
