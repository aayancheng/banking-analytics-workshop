#!/usr/bin/env python3
"""verify.py — "you are here, and it works."

One script, run any time you feel lost:

    python verify.py            # verifies the stage recorded in stage.txt
    python verify.py --stage 1  # verifies a specific stage
    python verify.py --json     # machine-readable (facilitator room sweep)

Rules this script lives by:
  1. Every failure ends in plain English WITH the fix — never a stack trace.
  2. Fast (<30s). It runs at the top and bottom of every session.
  3. Track-blind: it does not know or care whether you used an AI agent
     or did the lab by hand. The checkpoint is the same.
  4. Exit code 0 = verified, 1 = something to fix.

Stage checks 2-5 arrive with their sessions' tags. This file only ever
tests the stage you are on — earlier stages' guarantees are folded in.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_STAGE_BUILT = 3  # bumped as each session's tag lands

PYTHON_MIN = (3, 11)

# Committed metric gates. These live HERE, in the tag, on purpose: relaxing the
# gate in your own train.py does not move the checkpoint — verify.py recomputes
# the held-out metric against the values below. (Set beneath the measured
# synthetic ceilings; see Session 2.)
SCORE_AUC_GATE = 0.78
ADJ_AUC_GATE = 0.78
ADJ_LIFT_GATE = 2.0
PRICING_TOLERANCE = 0.02  # relative drift allowed vs the committed pricing summary

# Expected shape of the committed stage-1 data. Deterministic seed + pinned
# numpy means these are exact, not approximate — if they drift, something
# real changed (wrong file, wrong numpy, edited generator).
DATA_EXPECT = {
    "businesses.parquet": {"rows": 12_000},   # applicants
    "portfolio.parquet": {"rows": 8_336},     # booked accounts
    "panel.parquet": {"rows": 200_064},       # 8,336 accounts x 24 months
}


class Check:
    def __init__(self, name: str, fn):
        self.name = name
        self.fn = fn  # returns (ok: bool, detail: str, fix: str | None)


def check_python():
    v = sys.version_info
    if (v.major, v.minor) >= PYTHON_MIN:
        return True, f"Python {v.major}.{v.minor}.{v.micro}", None
    return (False, f"Python {v.major}.{v.minor} found, need 3.11+",
            "Install Python 3.11+ (python.org) or open this repo in GitHub Codespaces.")


def check_dependencies():
    from importlib import metadata
    req_file = ROOT / "requirements.txt"
    if not req_file.exists():
        return False, "requirements.txt missing", \
            "You may be in the wrong folder. cd to the repo root and rerun."
    missing, wrong = [], []
    n_pins = 0
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        n_pins += 1
        pkg, want = line.split("==")
        try:
            have = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            missing.append(pkg)
            continue
        if have != want:
            wrong.append(f"{pkg} {have}!={want}")
    if missing:
        return (False, f"Missing: {', '.join(missing)}",
                "Run: make setup   (or: .venv/bin/pip install -r requirements.txt). "
                "If pip hangs on your network, open this repo in GitHub Codespaces.")
    if wrong:
        return (False, f"Version mismatch: {'; '.join(wrong)}",
                "Run: make setup   — pinned versions keep everyone's numbers identical.")
    return True, f"{n_pins} pinned packages present", None


def check_data():
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return (False, "pyarrow not importable",
                "Run: make setup   (dependency check should have caught this).")
    raw = ROOT / "shared" / "data" / "raw"
    problems = []
    for fname, expect in DATA_EXPECT.items():
        f = raw / fname
        if not f.exists():
            problems.append(f"{fname} missing")
            continue
        rows = pq.read_metadata(f).num_rows
        if expect["rows"] is not None and rows != expect["rows"]:
            problems.append(f"{fname} has {rows:,} rows, expected {expect['rows']:,}")
    if problems:
        return (False, "; ".join(problems),
                "Restore the committed data: git checkout stage-1 -- shared/data/raw "
                "(or regenerate it: make data).")
    counts = ", ".join(f"{pq.read_metadata(raw / f).num_rows:,}" for f in DATA_EXPECT)
    return True, f"3 parquet files ({counts} rows)", None


def check_scorecard():
    models = ROOT / "score" / "models"
    needed = ["scorecard.pkl", "score_scaling.json", "metadata.json"]
    missing = [f for f in needed if not (models / f).exists()]
    if missing:
        return (False, f"Missing artifacts: {', '.join(missing)}",
                "Train it (Session 2 lab): make train-score — or restore the checkpoint "
                "version: git checkout stage-2 -- score/models")
    try:
        import joblib
        import pandas as pd
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import train_test_split
        sys.path.insert(0, str(ROOT))
        from shared.config import RAW, SEED
        from score.src.feature_engineering import FEATURE_COLUMNS, compute_features

        scorecard = joblib.load(models / "scorecard.pkl")
        biz = pd.read_parquet(RAW / "businesses.parquet")
        X = compute_features(biz)[FEATURE_COLUMNS]
        y = biz["default"].to_numpy()
        _, X_te, _, y_te = train_test_split(
            X, y, test_size=0.2, random_state=SEED, stratify=y)
        auc = float(roc_auc_score(y_te, scorecard.predict_proba(X_te)[:, 1]))
    except Exception as e:
        return (False, f"scorecard.pkl failed to load/score: {e}",
                "Retrain it: make train-score — or restore the checkpoint version: "
                "git checkout stage-2 -- score/models")
    if auc < SCORE_AUC_GATE:
        return (False, f"held-out AUC {auc:.4f} is below the committed gate {SCORE_AUC_GATE}",
                "The gate does not move — the model does. Revisit binning/feature choices "
                "(Session 2 lab), or restore the checkpoint: git checkout stage-2 -- score/models")
    return True, f"scorecard loads, held-out AUC {auc:.4f} >= gate {SCORE_AUC_GATE}", None


def check_adjudication():
    models = ROOT / "adjudication" / "models"
    needed = ["adjudication_model.pkl", "policy_config.json", "metadata.json"]
    missing = [f for f in needed if not (models / f).exists()]
    if missing:
        return (False, f"Missing artifacts: {', '.join(missing)}",
                "Train it (Session 3 lab): make train-adjudication — or restore: "
                "git checkout stage-3 -- adjudication/models")
    try:
        import joblib
        import pandas as pd
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import train_test_split
        sys.path.insert(0, str(ROOT))
        from shared.config import RAW, SEED
        from adjudication.src.feature_engineering import (
            ADJ_FEATURE_COLUMNS, compute_adjudication_features)

        model = joblib.load(models / "adjudication_model.pkl")
        biz = pd.read_parquet(RAW / "businesses.parquet")
        X = compute_adjudication_features(biz)[ADJ_FEATURE_COLUMNS]
        y = biz["default"].to_numpy()
        _, X_te, _, y_te = train_test_split(
            X, y, test_size=0.2, random_state=SEED, stratify=y)
        import numpy as np
        p = model.predict_proba(X_te)[:, 1]
        auc = float(roc_auc_score(y_te, p))
        cut = np.quantile(p, 0.80)
        lift = float(y_te[p >= cut].mean() / y_te.mean())
    except Exception as e:
        return (False, f"adjudication model failed to load/score: {e}",
                "Retrain: make train-adjudication — or restore: "
                "git checkout stage-3 -- adjudication/models")
    if auc < ADJ_AUC_GATE or lift < ADJ_LIFT_GATE:
        return (False, f"held-out AUC {auc:.4f} (gate {ADJ_AUC_GATE}) / "
                       f"top-20% lift {lift:.2f}x (gate {ADJ_LIFT_GATE})",
                "The gate does not move — the model does (Session 3 lab), or restore: "
                "git checkout stage-3 -- adjudication/models")
    return True, f"AUC {auc:.4f} >= {ADJ_AUC_GATE}, lift {lift:.2f}x >= {ADJ_LIFT_GATE}", None


def check_apps():
    """Smoke both decision apps in-process (TestClient — no server needed),
    then compare pricing totals to the committed summary."""
    summary_file = ROOT / "pricing" / "docs" / "summary.json"
    if not summary_file.exists():
        return (False, "pricing/docs/summary.json missing",
                "Rebuild the priced book: make price — or restore: "
                "git checkout stage-3 -- pricing/docs")
    try:
        sys.path.insert(0, str(ROOT))
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as client:
            h = client.get("/health")
            assert h.status_code == 200, f"/health -> {h.status_code}"
            ex = client.get("/api/examples").json()
            assert ex, "no examples returned"
            some_id = ex[0]["business_id"]
            adj = client.get(f"/api/adjudicate/{some_id}")
            assert adj.status_code == 200 and adj.json()["decision"] in (
                "Approve", "Refer", "Decline"), "adjudication endpoint broken"
            live = client.get("/api/pricing/summary").json()
        committed = json.loads(summary_file.read_text())
        for k in ("n", "share_clears", "mispriced_ead"):
            want, got = committed[k], live[k]
            if abs(got - want) > PRICING_TOLERANCE * max(abs(want), 1e-9):
                return (False,
                        f"pricing {k} drifted: {got} vs committed {want}",
                        "Your book no longer matches the checkpoint. Rebuild: make price "
                        "— or restore: git checkout stage-3 -- pricing/docs score/models")
    except Exception as e:
        return (False, f"app smoke test failed: {e}",
                "Check artifacts exist (make train-score train-adjudication price), "
                "or restore the checkpoint: git checkout stage-3 && python verify.py")
    return True, f"apps up in-process; pricing matches committed summary (n={committed['n']:,})", None


def checks_for(stage: int) -> list[Check]:
    checks = [
        Check("Python 3.11+", check_python),
        Check("Dependencies (pinned)", check_dependencies),
    ]
    if stage >= 1:
        checks.append(Check("Data: synthetic SME portfolio", check_data))
    if stage >= 2:
        checks.append(Check("Model: scorecard + AUC gate", check_scorecard))
    if stage >= 3:
        checks.append(Check("Model: adjudication + gates", check_adjudication))
        checks.append(Check("Apps: adjudication + pricing smoke", check_apps))
    return checks


def read_stage(cli_stage: int | None) -> int:
    if cli_stage is not None:
        return cli_stage
    f = ROOT / "stage.txt"
    if f.exists():
        try:
            return int(f.read_text().strip())
        except ValueError:
            pass
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="You are here, and it works.")
    ap.add_argument("--stage", type=int, default=None, help="override stage.txt")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    stage = read_stage(args.stage)
    if stage > MAX_STAGE_BUILT:
        msg = (f"Stage {stage} checks arrive with that session's tag. "
               f"This copy of verify.py knows stages 0-{MAX_STAGE_BUILT}.")
        if args.json:
            print(json.dumps({"stage": stage, "ok": False, "error": msg}))
        else:
            print(f"❌ {msg}")
        return 1

    checks = checks_for(stage)
    n = len(checks)
    results = []
    all_ok = True
    for i, c in enumerate(checks, 1):
        try:
            ok, detail, fix = c.fn()
        except Exception as e:  # a verify bug must still end in plain English
            ok, detail = False, f"unexpected error: {e}"
            fix = "This is a verify.py problem, not yours. Tell the facilitator."
        results.append({"name": c.name, "ok": ok, "detail": detail, "fix": fix})
        if not args.json:
            label = f"[{i}/{n}] {c.name} "
            print(f"{label}{'.' * max(2, 46 - len(label))} {'OK' if ok else 'FAIL'}")
            if not ok:
                print(f"      ❌ {detail}")
                if fix:
                    print(f"      Fix: {fix}")
        all_ok = all_ok and ok

    if args.json:
        print(json.dumps({"stage": stage, "ok": all_ok, "checks": results}))
    elif all_ok:
        print(f"✅ Stage {stage} verified — you are here, and it works.")
    else:
        print(f"❌ Stage {stage} not verified yet — fix the line(s) above and rerun. "
              f"Stuck for 5 minutes? Switch to Codespaces and keep moving.")
    return 0 if all_ok else 1


def _reexec_into_venv():
    """Keep the one-command promise: `python verify.py` works even when the
    pinned deps live in ./.venv and you typed the system python."""
    import os
    for rel in (".venv/bin/python", ".venv/Scripts/python.exe"):
        venv_py = ROOT / rel
        if venv_py.exists():
            if Path(sys.executable).resolve() != venv_py.resolve():
                os.execv(str(venv_py), [str(venv_py), str(ROOT / "verify.py"),
                                        *sys.argv[1:]])
            return


if __name__ == "__main__":
    _reexec_into_venv()
    sys.exit(main())
