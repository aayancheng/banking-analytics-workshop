#!/usr/bin/env python3
"""Derive one cuts file per chapter from a master cuts file.

    python split.py S2.cuts.json            # writes S2-ch1.cuts.json ... S2-chN.cuts.json

The master describes the stitched video: every keep carries a `chapter` number, every chapter
carries a `hook` (the composition that opens that chapter's standalone video). A derived file
is the same document with `stem` = "<stem>-ch<n>", `cards.intro` = the hook, only that
chapter's keeps and callouts, and no chapter freezes -- the hook is the chapter mark there.
Keeps may carry a `mark`: build.py turns it into a YouTube chapter without a freeze, so each
standalone video still has a chapter list. build.py is unchanged otherwise: `stem` keys every
output, so the derived files and the master never clobber each other.
"""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    master = Path(sys.argv[1])
    doc = json.loads(master.read_text())
    stem = doc["stem"]
    by_num = {c["num"]: c for c in doc["chapters"]}
    written = []
    for num in sorted(by_num):
        ch = by_num[num]
        keeps = [k for k in doc["keeps"] if k.get("chapter") == num]
        if not keeps:
            sys.exit(f"chapter {num} has no keeps")
        callouts = [c for c in doc["callouts"]
                    if any(k.get("source") == c.get("source") and k["in"] <= c["at"] and c["at"] + c["dur"] <= k["out"]
                           for k in keeps)]
        out = dict(doc)
        out["_comment"] = (f"DERIVED from {master.name} by split.py -- edit the master, not this file. "
                           f"Chapter {num}: {ch['title']}")
        out["stem"] = f"{stem}-ch{num}"
        out["cards"] = {"intro": ch["hook"], "outro": doc["cards"]["outro"]}
        out["keeps"] = keeps
        out["chapters"] = []
        out["callouts"] = callouts
        out["title"] = ch["title"]
        target = master.with_name(f"{stem}-ch{num}.cuts.json")
        target.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        dur = sum(k["out"] - k["in"] for k in keeps)
        written.append(target.name)
        print(f"  {target.name:<22} {len(keeps)} keeps  {len(callouts)} callouts  {dur/60:4.1f} min  hook={ch['hook']}")
    print(f"wrote {len(written)} files")


if __name__ == "__main__":
    main()
