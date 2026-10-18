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
    assert lint("![roc](fig/roc.svg){width=80%}\n") == []
    assert lint('![r](a.svg){fig-align="center" width=80%}\n') == []
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


def test_var_key_segment_quarto_cannot_address_is_flagged():
    keys = KEYS | {"ews.importance.gain.1.share"}
    out = lint_text("mdd/x.qmd", "{{< var ews.importance.gain.1.share >}}\n", keys, VIDEOS)
    assert out == ["mdd/x.qmd:1: fact key 'ews.importance.gain.1.share' has a segment "
                   "Quarto's var lookup cannot address"]
    assert lint_text("mdd/x.qmd", "{{< var ews.importance.gain.top1.share >}}\n",
                     {"ews.importance.gain.top1.share"}, VIDEOS) == []


def test_var_whose_text_markdown_parses_as_structure_is_flagged():
    texts = {"a.op": ">=", "a.h": "# x", "a.pipe": "| x", "a.tag": "<b>x", "a.list": "- x",
             "a.num": "1. x", "a.ok": "< 1e-12", "a.pct": "21.6%", "a.neg": "-0.0132"}
    for k, t in texts.items():
        out = lint_text("mdd/x.qmd", f"{{{{< var {k} >}}}}\n", set(texts), VIDEOS, texts=texts)
        if k in ("a.ok", "a.pct", "a.neg"):
            assert out == [], k
        else:
            assert out == [f"mdd/x.qmd:1: fact '{k}' prints '{t}', which markdown parses as "
                           "structure -- write it as a literal in inline code"], k


def test_build_facts_refuses_a_key_quarto_cannot_address():
    from wiki.facts.build_facts import KEY_SEGMENT
    from wiki.tools.lint import KEY_SEGMENT as LINT_SEGMENT
    assert KEY_SEGMENT.pattern == LINT_SEGMENT.pattern
    assert not KEY_SEGMENT.match("1") and KEY_SEGMENT.match("top1")
    import json
    from pathlib import Path
    facts = json.loads((Path(__file__).parents[1] / "wiki/facts/facts.json").read_text())
    assert all(KEY_SEGMENT.match(seg) for k in facts for seg in k.split("."))
