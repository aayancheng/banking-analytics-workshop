# Prompt Card HW-H1.1 — Which Columns Leak? (Session 1 homework)

**Kind: Ask.** You are the reviewer. The agent reasons about the data first and reads the
deny-list second; you check its list against the one the platform enforces.

**Goal.** Every column of the applicant file that would not exist when the credit decision is
made, each with a reason — compared, honestly, with `LEAKAGE_COLUMNS`.

---

## The brief (copy, fill the blank, send to your agent)

> You are in the `banking-analytics-workshop` repo on `main`, at the repo root. Run Python
> with `.venv/bin/python`. Reviewer: **[YOUR NAME]**.
>
> **Task:** decide which columns of the applicant file would leak into a credit model.
>
> 1. Load `shared/data/raw/businesses.parquet` and list its columns. **Do not open
>    `shared/config.py` yet.**
> 2. For each column, ask one question: would it exist on a new application, at the moment the
>    credit decision is made? A column that would not is a leak, however well it predicts.
>    Read `shared/data_generator.py` to see how each suspect column is made.
> 3. Write one line per leaking column to `wiki/homework/_answers/H1.1.md`, in this form:
>
>        LEAK: <column> — <why it would not exist at decision time>
>
>    Only columns of `businesses.parquet`.
> 4. Now open `shared/config.py` and read `LEAKAGE_COLUMNS`. Under a heading "Compared with
>    the deny-list", say where you agreed and where you did not, and why. If the deny-list
>    names a column that is not in `businesses.parquet`, say where it lives instead; do not
>    add a `LEAK:` line for it.
> 5. Change no file other than the answer.

---

## What "done" looks like

- One `LEAK:` line per leaking column, each with a reason a validator would accept.
- A paragraph on the columns that predict but are not leaks.
- An honest comparison with the deny-list, including any column it got wrong first.

## Check it

```bash
python -m wiki.homework.check H1.1
```

The check reads `LEAKAGE_COLUMNS` and the file's columns itself. It wants every deny-listed
column of `businesses.parquet` as a `LEAK:` line, no other column, a reason on each line, and
the deny-list exactly as committed.

## The trap

- **Paraphrasing the list.** An agent that reads `shared/config.py` first returns the list,
  not a judgement. If your agent has already seen it this session, start a fresh session.
- **Predictive is not leaky.** `net_income` and `requested_amount` predict default because
  they are built from `annual_revenue`. They are on the application; they are not leaks.
- **The quoted rate.** A rate is quoted at origination, so `risk_based_rate` can look safe.
  Read how the generator makes it before deciding.
- **Editing the list.** An agent that adds or removes a column in `LEAKAGE_COLUMNS` to match
  its answer fails the exercise. If that happened: `git checkout -- shared/config.py`.
