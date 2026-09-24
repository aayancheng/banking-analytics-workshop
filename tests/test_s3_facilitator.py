from pathlib import Path


ROOT = Path(__file__).parents[1]
RUN_OF_SHOW = ROOT / "workshop/facilitator/S3-run-of-show.md"
POLLS = ROOT / "workshop/facilitator/S3-polls.md"


def test_s3_run_of_show_is_a_90_minute_slide_notebook_lab_flow():
    source = RUN_OF_SHOW.read_text()

    for marker in ["0:00", "0:50", "1:20", "1:27", "1:30"]:
        assert marker in source

    assert "90 minutes" in source
    assert "S3_4.html" in source
    assert "03_04_adjudication_pricing_monitoring.ipynb" in source
    assert "SCREEN: SLIDES" in source
    assert "SWITCH → NOTEBOOK §1" in source
    assert "SWITCH → NOTEBOOK §2" in source
    assert "SWITCH → NOTEBOOK §3" in source
    assert "SWITCH → NOTEBOOK §4" in source
    assert "RETURN → SLIDES" in source


def test_s3_run_of_show_uses_the_top_two_of_four_interest_areas():
    source = RUN_OF_SHOW.read_text().lower()

    for application in [
        "adjudication",
        "pricing",
        "monitoring",
        "line increases",
    ]:
        assert application in source

    assert "top two" in source
    assert "15 minutes each" in source
    assert "poll c" in source
    assert "interest" in source


def test_s3_polls_include_interest_ranking_and_exit_pulse():
    source = POLLS.read_text()
    lower = source.lower()

    for poll in ["Poll A", "Poll B", "Poll C", "Poll D"]:
        assert poll in source

    assert "most interested" in lower
    assert "select up to two" in lower
    assert "top two" in lower
    for application in [
        "credit approval / adjudication",
        "risk-based pricing",
        "early warning / monitoring",
        "line management",
    ]:
        assert application in lower

    assert "too slow" in lower
    assert "about right" in lower
    assert "too fast" in lower
    assert "stuck on setup" in lower
