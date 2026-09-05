# Reading notes — the longer version

Post-session material for people who want more than the session had time for. **None of it is
needed to pass a checkpoint.** Nothing here is assigned; nothing here is assessed.

| Note | After | What it goes into |
|---|---|---|
| `S1-data-generation.pdf` | Session 1 | the data-generating process in full: every weight in the default logit, which columns have no causal role, the two places noise enters, and the computable ceiling that the AUC gate was set against |

## Reading them

Open the `.pdf`. That is all.

## Re-rendering them

The `.html` is the source of truth and the `.pdf` is committed beside it, so students never need
a toolchain. If you edit a note:

```bash
make reading
```

Renders every `.html` in this folder to a PDF of the same name using headless Chrome (or
Chromium). No npm, no LaTeX, no pandoc.

## The house rule for these notes

Every number in a reading note is **recomputed from the committed data**, and each note ends with
an appendix containing the code to reproduce it. If a note and your machine disagree, your machine
is right and the note is a bug — that is the same contract `verify.py` makes, applied to prose.
