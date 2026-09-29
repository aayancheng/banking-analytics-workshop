from wiki.tools.lint import lint_text

KEYS = {"score.auc_holdout", "score.gate"}
VIDEOS = {"S2-c5": {"title": "t", "youtube": None, "session": 2}}


def lint(text):
    return lint_text("mdd/x.qmd", text, KEYS, VIDEOS)


def test_hand_typed_metric_is_flagged_with_its_line():
    assert lint("ok line\nAUC is 0.8176 here\n") == [
        "mdd/x.qmd:2: hand-typed number '0.8176' — use {{< var … >}}"]


def test_percent_is_flagged_but_var_code_and_attributes_are_not():
    assert lint("share is 51%\n") != []
    assert lint("AUC {{< var score.auc_holdout >}}\n") == []
    assert lint("`0.8176` in code\n```\nx = 0.8176\n```\n") == []
    assert lint("![roc](fig/roc.svg){#fig-roc width=80%}\n") == []
    assert lint("<!-- 0.8176 -->\n") == []


def test_two_decimals_and_years_are_fine():
    assert lint("PSI above 0.10 means watch; SR 11-7 (2011); 1.5 points\n") == []


def test_unknown_var_is_flagged():
    assert lint("{{< var score.nope >}}\n") == [
        "mdd/x.qmd:1: unknown fact 'score.nope'"]


def test_unknown_video_is_flagged():
    assert lint("{{< yt S9-c1 >}}\n") == ["mdd/x.qmd:1: unknown video 'S9-c1'"]


def test_same_page_xref_must_resolve():
    assert lint("See @fig-roc.\n") == ["mdd/x.qmd:1: cross-reference @fig-roc has no anchor on this page"]
    assert lint("See @fig-roc.\n\n![r](a.svg){#fig-roc}\n") == []
