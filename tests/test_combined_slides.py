from pathlib import Path


ROOT = Path(__file__).parents[1]
SLIDE = ROOT / "workshop/slides/S3_4.md"
HTML = ROOT / "workshop/slides/S3_4.html"


def test_combined_slide_deck_has_lifecycle_flow_and_timing():
    source = SLIDE.read_text()
    sections = [
        "A decision is not a score",
        "Policy parameters banks actually use",
        "ROE and RAROC",
        "Three loans, one pricing decision",
        "The portfolio wakes up",
        "The 54% vs 21.6% trap",
        "Precise line-increase offer rules",
        "Lab handoff",
    ]
    positions = [source.index("# " + section) for section in sections]

    assert positions == sorted(positions)
    assert "03_04_adjudication_pricing_monitoring.ipynb" in source
    assert "0:00" in source and "0:48" in source
    assert "0.3121" in source and "0.0741" in source


def test_combined_slide_deck_has_rendered_html():
    html = HTML.read_text()
    assert "S3_4" in html
    assert '<section class="slide">' in html
    assert "No slide overflows" in html
