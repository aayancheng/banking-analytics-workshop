from pathlib import Path


ROOT = Path(__file__).parents[1]
LAB = ROOT / "workshop/labs/S3_4-lab.md"


def test_combined_lab_teaches_the_four_stage_lifecycle_in_order():
    source = LAB.read_text()
    sections = [
        "Adjudication",
        "Pricing",
        "Monitoring",
        "Line increases",
        "Integrated lifecycle decision",
    ]
    positions = [source.index("## " + section) for section in sections]

    assert positions == sorted(positions)
    assert "03_04_adjudication_pricing_monitoring.ipynb" in source
    assert "80 min" in source


def test_combined_lab_preserves_reusable_commands_and_evidence_checks():
    source = LAB.read_text()

    for command in [
        "make train-adjudication",
        "make price",
        "make train-ews",
        "python workshop/labs/oracle_ceiling.py",
        "make train-line-increase",
        "python verify.py",
    ]:
        assert command in source

    for evidence in [
        "30.8%",
        "36.8%",
        "32.4%",
        "0.662",
        "0.308",
        "21.6%",
        "0.3121",
        "0.0741",
        "15%",
        "named triggers",
    ]:
        assert evidence.lower() in source.lower()


def test_combined_lab_requires_an_integrated_student_deliverable():
    source = LAB.read_text()

    for phrase in [
        "model or rule",
        "ROE",
        "held-out",
        "four simultaneous gates",
        "decision memo",
        "what to notice",
    ]:
        assert phrase.lower() in source.lower()
