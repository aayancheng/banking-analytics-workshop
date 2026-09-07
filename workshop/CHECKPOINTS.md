# Where am I? — the checkpoint manual

*One page. Keep it open during the workshop.*

## The only command you must remember

```bash
python verify.py
```

It tells you **where you are** and **whether it works**. Run it any time you feel lost.
It never changes anything — it only checks.

---

## What a "stage" is

The workshop has **six save points**, one per session. Each is a git **tag** — a permanent
bookmark on a moment in the repo's history.

| Tag | You are at the end of | What's new in it | `verify.py` runs |
|---|---|---|---|
| `stage-0` | pre-work | environment only — nothing built yet | 2 checks |
| `stage-1` | Session 1 | your synthetic portfolio + data-quality report | 3 checks |
| `stage-2` | Session 2 | the credit scorecard, trained and gated | 4 checks |
| `stage-3` | Session 3 | adjudication, pricing, the portal, tests | 6 checks |
| `stage-4` | Session 4 | early warning + line increases | 8 checks |
| `stage-5` | Session 5 | the model documentation pack | 9 checks |

The check count grows because each stage adds something new to verify. Nothing is ever
removed — **each stage contains everything the stages before it produced.**

> **That is the important part:** every checkpoint is self-sufficient. If you miss a session,
> or your own code goes sideways, you can jump to any stage and everything up to that point
> is already there, already working. **Missing a week costs you nothing.**

---

## Time travel: three commands

**Go look at any stage:**

```bash
git checkout stage-2
python verify.py
```

```
[1/4] Python 3.11+ ........................... OK
[2/4] Dependencies (pinned) .................. OK
[3/4] Data: synthetic SME portfolio .......... OK
[4/4] Model: scorecard + AUC gate ............ OK
✅ Stage 2 verified — you are here, and it works.
```

**Come back to the latest:**

```bash
git checkout main
```

That's it. You can hop between stages as often as you like.

---

## Two things to know before you jump

**1. Save your own work first.** Jumping stages does not delete your files, but git will stop
you if you have unsaved edits. Park them:

```bash
git stash          # put your changes aside
git stash pop      # get them back later
```

**2. "You are in 'detached HEAD' state" is not an error.** Git prints this whenever you check
out a tag. It only means *"you're looking at a fixed point in history rather than the tip of a
branch."* Look around all you like. `git checkout main` always brings you home.

**3. The notebooks disappear, and that is expected.** `notebooks/` lives on `main` only — no tag
contains it. The notebooks are a *view onto* whatever stage you are at, not part of any stage's
contents, so there is one copy that is kept current rather than five frozen ones. Bring them
along after a jump:

```bash
git checkout main -- workshop notebooks
```

That restores `notebooks/` from `main` without moving you off the stage, and it works from
**any** stage. Afterwards `git status` lists the notebooks as staged new files — that is normal
and harmless; they are simply not part of this stage.

> **Why not `make notebooks`?** There is such a target, and it is friendlier — it refuses rather
> than overwriting if you have unsaved notebook edits. But it only exists on `main`. Each stage
> tag ships the Makefile it had at the time, and the tags never move, so at `stage-2` the target
> is simply not there. The git command above needs nothing but git, which is why it is the one
> printed here.

---

## Keeping your own work — the safe way

`git stash` is fine for a quick look around, but it is easy to forget you stashed something.
If you are doing work you care about, **put it on your own branch instead.** Then it has a
name, it survives every jump, and nothing is ever at risk:

```bash
git checkout -b my-work          # once — creates your branch
git add -A
git commit -m "my session 3 work"
```

Now you can wander anywhere and come home:

```bash
git checkout stage-1     # look around
git checkout my-work     # everything of yours is exactly as you left it
```

## Combining your work with a stage

If you fell behind and want to **catch up without losing your own work**, merge the stage into
your branch:

```bash
git checkout my-work
git merge stage-3
python verify.py
```

You get stage-3's modules *and* keep your files. If git reports a conflict, it means you and
the stage both edited the same lines — open the file, keep the version you want, then
`git add <file> && git commit`.

> **One quirk worth knowing:** if your branch started from `main`, `git merge stage-3` will say
> *"Already up to date."* That is correct, not a failure — the repo's history is a straight
> line, so `main` already contains every stage. Merging only does something when your branch
> started from an **earlier** stage than the one you are merging in.

**Just want one file from a stage?** Simplest of all:

```bash
git checkout stage-3 -- score/src/train.py
```

## Getting the workshop materials back

Slides, lab sheets and prompt cards live on `main`. After jumping to an older stage they will
seem to disappear — they simply didn't exist yet at that point in history. Bring them along:

```bash
git checkout main -- workshop
```

---

## Cheat sheet

| I want to… | Type this |
|---|---|
| Know where I am | `python verify.py` |
| See what stage I'm on | `cat stage.txt` |
| Jump to a stage | `git checkout stage-3` |
| Go back to the latest | `git checkout main` |
| Park my changes | `git stash` |
| Get my changes back | `git stash pop` |
| I'm completely lost | `git stash && git checkout stage-1 && python verify.py` |
| Get slides/labs back after a jump | `git checkout main -- workshop` |
| Rebuild the environment | `make setup` |

---

## Questions people ask

**Do I need to reinstall anything after jumping stages?**
No. Your `.venv` isn't part of the repo, so it survives every jump.

**Can I edit `stage.txt` to skip ahead?**
You can, but it won't help — it only changes which checks run, not what's built. The real
work is in the tags.

**I broke something and I don't know what.**
`git stash && git checkout stage-N && python verify.py`. That is the whole recovery, and it
works from any mess. You are never more than one command from a working state.

**What are `v1.0` / `v1.1` / `v1.2`?**
Release tags for the repo as a whole, not stages. You can ignore them.

**Can I keep my own work permanently?**
Yes — work on your own branch (`git checkout -b my-work`), and push to your own fork if you
want it after the workshop.

**Does `git stash` delete my work?**
No. It parks it and `git stash pop` brings it back — even at a different stage. Two things to
know: stash does *not* include brand-new files you have never added (those simply stay put and
survive the jump anyway), and a stash is easy to forget about. `git stash list` shows anything
you have parked. For work you care about, use a branch.

**Why does `ls` show folders that shouldn't exist at this stage?**
Python leaves `__pycache__` folders behind, and those are ignored by git, so jumping stages
does not clear them. Use `git ls-files` to see what is genuinely part of the stage.
