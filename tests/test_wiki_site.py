"""The wiki's structure promises: profiles exist, outputs are ignored, prose is licensed."""
from pathlib import Path

ROOT = Path(__file__).parents[1]
WIKI = ROOT / "wiki"


def test_three_profiles_exist_with_distinct_output_dirs():
    outs = {}
    for prof in ("site", "validation", "book"):
        text = (WIKI / f"_quarto-{prof}.yml").read_text()
        line = next(l for l in text.splitlines() if "output-dir:" in l)
        outs[prof] = line.split(":", 1)[1].strip()
    assert outs == {"site": "_site", "validation": "_validation", "book": "_book"}


def test_render_outputs_and_answers_are_gitignored():
    ignore = (ROOT / ".gitignore").read_text()
    for pattern in ("wiki/_site/", "wiki/_validation/", "wiki/_book/", "wiki/.quarto/",
                    "wiki/mdd/_artifacts.qmd", "wiki/homework/_answers/*"):
        assert pattern in ignore, pattern


def test_prose_licence_is_declared():
    assert "Attribution-NonCommercial-NoDerivatives 4.0" in (ROOT / "LICENSE-CONTENT").read_text()
    assert "LICENSE-CONTENT" in (ROOT / "README.md").read_text()


TEMPLATE_PARTS = ["purpose", "data", "methodology", "assumptions", "performance",
                  "sensitivity", "limitations", "monitoring", "gate"]


def test_template_has_the_nine_parts_in_order():
    for i, part in enumerate(TEMPLATE_PARTS, 1):
        text = (WIKI / "mdd" / "_template" / f"{part}.qmd").read_text()
        assert text.startswith("---\ntitle:"), part
        assert f"order: {i}" in text, part


def test_every_spine_chapter_exists():
    for rel in ["course/index.qmd", "course/c0-start.qmd", "course/c4-governance.qmd",
                "mdd/index.qmd", "mdd/d0-summary.qmd", "mdd/d1-purpose.qmd",
                "mdd/d2-data.qmd", "mdd/d3-dependencies.qmd", "mdd/d9-implementation.qmd",
                "mdd/d10-agents.qmd", "mdd/d11-signoff.qmd", "reference/crosswalk.qmd",
                "reference/glossary.qmd", "explain/index.qmd"]:
        assert (WIKI / rel).exists(), rel


def test_all_pages_lint_clean_including_links():
    from wiki.tools.lint import lint_all
    assert lint_all() == []


def test_d4_has_an_index_and_the_nine_parts_in_order():
    assert "order: 0" in (WIKI / "mdd" / "score" / "index.qmd").read_text()
    for i, part in enumerate(TEMPLATE_PARTS, 1):
        text = (WIKI / "mdd" / "score" / f"{part}.qmd").read_text()
        assert f'title: "4.{i} ' in text and f"order: {i}" in text, part
        assert "TEMPLATE" not in text, f"{part}: template brief not replaced"


def _finding_rows(text: str) -> list[str]:
    return [l for l in text.splitlines() if l[:4] in {f"| {n} " for n in "123456789"}]


def _signoff_section(chapter: str) -> str:
    """D11's open-findings subsection for one chapter ("D4", "D5", ...)."""
    text = (WIKI / "mdd" / "d11-signoff.qmd").read_text()
    return text.split(f"\n### {chapter} ", 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]


def test_signoff_open_findings_are_d4_limitations_word_for_word():
    d11 = _finding_rows(_signoff_section("D4"))
    assert len(d11) == 6
    assert d11 == _finding_rows((WIKI / "mdd" / "score" / "limitations.qmd").read_text())


def test_signoff_open_findings_are_d5_limitations_word_for_word():
    d11 = _finding_rows(_signoff_section("D5"))
    assert len(d11) == 5
    assert d11 == _finding_rows((WIKI / "mdd" / "adjudication" / "limitations.qmd").read_text())


def test_signoff_lists_every_finding_row_once():
    text = (WIKI / "mdd" / "d11-signoff.qmd").read_text()
    assert len(_finding_rows(text)) == 6 + 5


def test_d5_has_an_index_and_the_nine_parts_in_order():
    index = (WIKI / "mdd" / "adjudication" / "index.qmd").read_text()
    assert "order: 0" in index and "Status: complete" in index
    for i, part in enumerate(TEMPLATE_PARTS, 1):
        text = (WIKI / "mdd" / "adjudication" / f"{part}.qmd").read_text()
        assert f'title: "5.{i} ' in text and f"order: {i}" in text, part
        assert "TEMPLATE" not in text, f"{part}: template brief not replaced"


def test_validation_book_lists_every_model_chapter_page():
    book = (WIKI / "_quarto-validation.yml").read_text()
    for chapter in ("score", "adjudication"):
        pos = [book.index(f"mdd/{chapter}/{p}.qmd") for p in ["index"] + TEMPLATE_PARTS]
        assert pos == sorted(pos), chapter


def test_calibration_findings_follow_the_monitoring_floor():
    """D4.7 raises a band's calibration breach as a finding exactly when the monitoring rule
    would count it: ratio outside the tolerance on at least the floor's defaults. Below the
    floor it is an observation. If the facts move a band across the line, the prose must move."""
    import json
    f = {k: v["text"] for k, v in json.loads((WIKI / "facts" / "facts.json").read_text()).items()}
    lo, hi = float(f["monitoring.ratio_lo"]), float(f["monitoring.ratio_hi"])
    floor = int(f["monitoring.min_band_defaults"])
    breach = lambda pre, b: not lo <= float(f[f"{pre}.{b}.ratio"]) <= hi
    findings, observations = set(), set()
    for pre in ("score.band", "score.band_booked"):
        for b in ("D", "C", "B", "A", "AAA"):
            if breach(pre, b):
                n = int(f[f"{pre}.{b}.defaults"].replace(",", ""))
                (findings if n >= floor else observations).add(f"{pre}.{b}")
    assert findings == {"score.band_booked.B"}
    assert observations == {"score.band.A", "score.band.AAA",
                            "score.band_booked.A", "score.band_booked.AAA"}
    text = (WIKI / "mdd" / "score" / "limitations.qmd").read_text()
    f6 = text.split("## Finding 6", 1)[1].split("\n## ", 1)[0]
    assert "score.band_booked.B.ratio" in f6 and "monitoring.min_band_defaults" in f6
    obs = next(l for l in text.splitlines() if l.startswith("| Bands A and AAA"))
    for key in observations:
        assert f"{key}.ratio" in obs, key
    assert "score.band_booked.B." not in obs


def test_d5_zone_calibration_findings_follow_the_monitoring_floor():
    """D5.7 applies D4's floor rule to the PD zones: a zone outside the tolerance on at least
    the floor's defaults is part of finding 3; below the floor it would be an observation."""
    import json
    f = {k: v["text"] for k, v in json.loads((WIKI / "facts" / "facts.json").read_text()).items()}
    lo, hi = float(f["monitoring.ratio_lo"]), float(f["monitoring.ratio_hi"])
    floor = int(f["monitoring.min_band_defaults"])
    findings, observations = set(), set()
    for pop in ("everyone", "booked"):
        for z in ("Approve", "Refer", "Decline"):
            key = f"adj.zone.{pop}.{z}"
            if not lo <= float(f[f"{key}.ratio"]) <= hi:
                n = int(f[f"{key}.defaults"].replace(",", ""))
                (findings if n >= floor else observations).add(key)
    assert findings == {"adj.zone.everyone.Approve", "adj.zone.booked.Approve",
                        "adj.zone.booked.Decline"}
    assert observations == set()
    text = (WIKI / "mdd" / "adjudication" / "limitations.qmd").read_text()
    f3 = text.split("## Finding 3", 1)[1].split("\n## ", 1)[0]
    for key in findings:
        assert f"{key}.ratio" in f3, key
    assert "monitoring.min_band_defaults" in f3
    obs = next(l for l in text.splitlines() if l.startswith("| No calibration miss below the floor"))
    assert "monitoring.min_band_defaults" in obs


def test_d5_inert_rules_finding_matches_the_facts():
    """Finding 2 names exactly the rules that fire on no applicant."""
    import json
    f = {k: v["text"] for k, v in json.loads((WIKI / "facts" / "facts.json").read_text()).items()}
    rules = ["dscr_floor", "public_records", "prior_delinquencies", "leverage",
             "thin_dscr", "weak_score", "large_request"]
    dead = {r for r in rules if f[f"adj.rule.{r}.n_all"] == "0"}
    assert dead == {"leverage", "large_request"}
    text = (WIKI / "mdd" / "adjudication" / "limitations.qmd").read_text()
    f2 = text.split("## Finding 2", 1)[1].split("\n## ", 1)[0]
    for r in dead:
        assert f"adj.rule.{r}.n_all" in f2, r
