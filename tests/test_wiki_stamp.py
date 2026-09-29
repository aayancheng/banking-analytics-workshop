from shared.config import ROOT
from wiki.tools import stamp


def test_artifact_table_hashes_every_cited_artifact():
    md = stamp.artifact_table(ROOT)
    for rel in stamp.ARTIFACTS:
        assert f"`{rel}`" in md
    row = next(l for l in md.splitlines() if "score/models/scorecard.pkl" in l)
    assert len(row.split("|")[2].strip().strip("`")) == 16
