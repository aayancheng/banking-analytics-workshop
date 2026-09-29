"""Stamp the validation PDF: SHA-256 of every artifact the documentation cites, so a
validator can confirm the copy they hold matches the repository at its tag."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = [
    "shared/data/raw/businesses.parquet", "shared/data/raw/portfolio.parquet",
    "score/models/scorecard.pkl", "score/models/score_scaling.json",
    "score/models/metadata.json", "adjudication/models/adjudication_model.pkl",
    "adjudication/models/metadata.json", "adjudication/models/policy_config.json",
    "wiki/facts/facts.json",
]


def artifact_table(root: Path = ROOT) -> str:
    rows = ["| Artifact | SHA-256 (first 16) |", "|---|---|"]
    for rel in ARTIFACTS:
        digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()[:16]
        rows.append(f"| `{rel}` | `{digest}` |")
    return "\n".join(rows) + "\n"


def main() -> None:
    out = ROOT / "wiki" / "mdd" / "_artifacts.qmd"
    out.write_text(artifact_table())
    print(f"stamped {len(ARTIFACTS)} artifacts → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
