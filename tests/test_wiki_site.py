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
    assert len(d11) == 6
    assert d11 == _finding_rows((WIKI / "mdd" / "adjudication" / "limitations.qmd").read_text())


def test_signoff_open_findings_are_d6_limitations_word_for_word():
    d11 = _finding_rows(_signoff_section("D6"))
    assert len(d11) == 5
    assert d11 == _finding_rows((WIKI / "mdd" / "pricing" / "limitations.qmd").read_text())


def test_signoff_lists_every_finding_row_once():
    text = (WIKI / "mdd" / "d11-signoff.qmd").read_text()
    assert len(_finding_rows(text)) == 6 + 6 + 5 + 7


def test_d5_has_an_index_and_the_nine_parts_in_order():
    index = (WIKI / "mdd" / "adjudication" / "index.qmd").read_text()
    assert "order: 0" in index and "Status: complete" in index
    for i, part in enumerate(TEMPLATE_PARTS, 1):
        text = (WIKI / "mdd" / "adjudication" / f"{part}.qmd").read_text()
        assert f'title: "5.{i} ' in text and f"order: {i}" in text, part
        assert "TEMPLATE" not in text, f"{part}: template brief not replaced"


def test_d6_has_an_index_and_the_nine_parts_in_order():
    index = (WIKI / "mdd" / "pricing" / "index.qmd").read_text()
    assert "order: 0" in index and "Status: complete" in index
    assert "How the template is adapted for a tool" in index
    for i, part in enumerate(TEMPLATE_PARTS, 1):
        text = (WIKI / "mdd" / "pricing" / f"{part}.qmd").read_text()
        assert f'title: "6.{i} ' in text and f"order: {i}" in text, part
        assert "TEMPLATE" not in text, f"{part}: template brief not replaced"


def test_validation_book_lists_every_model_chapter_page():
    book = (WIKI / "_quarto-validation.yml").read_text()
    for chapter in ("score", "adjudication", "pricing", "ews"):
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
    section = lambda n: text.split(f"## Finding {n}", 1)[1].split("\n## ", 1)[0]
    f3, f6 = section(3), section(6)
    for key in ("adj.zone.everyone.Approve", "adj.zone.booked.Approve"):
        assert f"{key}.ratio" in f3, key
    assert "adj.zone.booked.Decline.ratio" in f6
    assert "adj.zone.booked.Decline.ratio" not in f3
    assert "monitoring.min_band_defaults" in f3 and "monitoring.min_band_defaults" in f6
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


def _facts() -> dict[str, str]:
    import json
    return {k: v["text"] for k, v in json.loads((WIKI / "facts" / "facts.json").read_text()).items()}


def _num(t: str) -> float:
    return float(t.replace(",", "").rstrip("%"))


def test_d5_prose_conclusions_hold_on_the_facts():
    """Sentences in D5 that state a conclusion about a fact: if the fact moves, the prose must."""
    f = _facts()
    # "no file is Approve under one and Decline under the other" (5.3, 5.5)
    assert f["adj.score_zone.opposite.n"] == "0"
    # "business_score rises 0 times": one signal in two columns (5.3)
    assert f["adj.score_pd.order_breaks"] == "0"
    # cutoff sensitivity: "no decision share moves by as much as a percentage point" (5.6)
    for sc in ("t_low_down", "t_low_up", "t_high_down", "t_high_up"):
        for k in ("Approve", "Refer", "Decline"):
            assert abs(_num(f[f"adj.sens.{sc}.{k}"]) - _num(f[f"adj.mix.{k}"])) < 1, (sc, k)
    # "the observed default rate rises from Approve to Refer to Decline" in every population (5.5)
    for pop in ("everyone", "booked", "rejected"):
        dr = [_num(f[f"adj.dec.{pop}.{k}.dr"]) for k in ("Approve", "Refer", "Decline")]
        assert dr == sorted(dr) and len(set(dr)) == 3, pop
    # the top two SHAP features on Declines are the score's two columns; none of the top three
    # is a structural zero (5.2, 5.3, 5.5)
    assert {f["adj.decline.shap1.feature"], f["adj.decline.shap2.feature"]} == {"pd_score",
                                                                                "business_score"}
    zeros = {"industry", "entity_type", "loan_purpose", "term_months", "collateral_flag",
             "trade_lines", "employees"}
    assert not zeros & {f[f"adj.decline.shap{i}.feature"] for i in (1, 2, 3)}
    # "every Decline with a reason string has a knockout behind it" (5.5)
    assert f["adj.decline.rule_share"] == f["adj.decline.knockout_share"]
    # "the interval contains zero": no better, not measurably worse (5.3, 5.5, finding 1)
    for pop in ("everyone", "booked", "rejected"):
        assert _num(f[f"adj.vs_score.{pop}.lo"]) < 0 < _num(f[f"adj.vs_score.{pop}.hi"]), pop
    # "the booked sample's own interval lies wholly below the gate" (finding 1)
    assert _num(f["adj.pop.booked.auc_ci_hi"]) < _num(f["adj.gate_auc"])
    # booked lift "still clears its gate"
    assert _num(f["adj.pop.booked.lift"]) >= _num(f["adj.gate_lift"])


def test_d6_prose_conclusions_hold_on_the_facts():
    """Sentences in D6 that state a conclusion about a fact: if the fact moves, the prose must."""
    f = _facts()
    n = _num(f["pricing.n"])
    # "the capital charge exceeds the base margin" (6.4, finding 1)
    assert _num(f["pricing.capital_charge"]) > _num(f["market.base_margin"])
    assert _num(f["pricing.capital_charge_less_margin"]) > 0
    # "smaller than the cost of funds" (6.6)
    assert _num(f["pricing.capital_charge"]) < _num(f["market.cost_of_funds"])
    # most of the book misses at its own quote (index, 6.5, finding 1)
    assert _num(f["pricing.share_mispriced"]) > 50
    assert _num(f["pricing.median_roe"]) < _num(f["market.roe_hurdle"])
    assert _num(f["pricing.median_quoted_rate"]) < _num(f["pricing.median_recommended_rate"])
    # below break-even is exactly the negative-ROE set, and part of the mispriced (6.5, finding 2)
    assert f["pricing.below_break_even.n"] == f["pricing.negative_roe.n"]
    assert _num(f["pricing.below_break_even.n"]) < _num(f["pricing.n_mispriced"])
    # "no flips"; every identity and the what-if held to a bound (6.5, 6.9)
    assert f["pricing.whatif.flips"] == "0"
    for k in ("break_even", "hurdle", "recommended", "waterfall", "ead_invariance", "max", "fee"):
        assert f[f"pricing.identity.{k}"] == "< " + f["pricing.test_tolerance"], k
    for k in ("max_diff", "pd_max_diff"):
        assert f[f"pricing.whatif.{k}"] == "< " + f["pricing.test_tolerance"], k
    # by band: highest share AAA then A, lowest C; D the most mispriced EAD and lowest
    # median ROE, with a share below the book's (6.5, finding 3)
    bands = ("D", "C", "B", "A", "AAA")
    rate = {b: _num(f[f"pricing.band.{b}.mispriced_rate"]) for b in bands}
    order = sorted(bands, key=lambda b: -rate[b])
    assert order[:2] == ["AAA", "A"] and order[-1] == "C"
    assert (f["pricing.worst_band"], f["pricing.second_band"], f["pricing.best_band"]) == \
        ("AAA", "A", "C")
    ead = {b: _num(f[f"pricing.band.{b}.mispriced_ead"]) for b in bands}
    roe = {b: _num(f[f"pricing.band.{b}.median_roe"]) for b in bands}
    assert max(ead, key=ead.get) == "D" and min(roe, key=roe.get) == "D"
    assert rate["D"] < _num(f["pricing.share_mispriced"])
    # finding 3: AAA, A, B over-default on the booked; only B on enough defaults; D inside
    lo, hi = _num(f["monitoring.ratio_lo"]), _num(f["monitoring.ratio_hi"])
    floor = _num(f["monitoring.min_band_defaults"])
    for b in ("B", "A", "AAA"):
        assert _num(f[f"score.band_booked.{b}.ratio"]) > hi, b
    assert _num(f["score.band_booked.B.defaults"]) >= floor
    for b in ("A", "AAA"):
        assert _num(f[f"score.band_booked.{b}.defaults"]) < floor, b
    for k in ("score.band.D.ratio", "score.band_booked.D.ratio"):
        assert lo <= _num(f[k]) <= hi, k
    # sensitivity: cost_of_funds dominates; LGD second; capital ratio and hurdle tie; opex
    # and tax the two smallest (6.6, finding 5)
    fields = ("cost_of_funds", "lgd", "capital_ratio", "roe_hurdle", "opex_rate", "tax_rate")
    rng = {fd: _num(f[f"pricing.sens.{fd}.down.n_clears"]) - _num(f[f"pricing.sens.{fd}.up.n_clears"])
           for fd in fields}
    assert f["pricing.sens.dominant"] == "cost_of_funds"
    assert sorted(fields, key=lambda fd: -rng[fd])[:2] == ["cost_of_funds", "lgd"]
    assert rng["capital_ratio"] == rng["roe_hurdle"]
    assert set(sorted(fields, key=lambda fd: rng[fd])[:2]) == {"opex_rate", "tax_rate"}
    for name in ("up", "down"):
        for c in ("n_clears", "mispriced_ead", "share_clears"):
            assert f[f"pricing.sens.capital_ratio.{name}.{c}"] == f[f"pricing.sens.roe_hurdle.{name}.{c}"]
        # "the hurdle moves the verdict, not the ROE"
        assert f[f"pricing.sens.roe_hurdle.{name}.median_roe"] == f["pricing.median_roe"]
        # "identical to the LGD rows": PD enters only as PD x LGD
        for c in ("share_clears", "n_clears", "median_roe", "mispriced_ead"):
            assert f[f"pricing.pd_scale.{name}.{c}"] == f[f"pricing.sens.lgd.{name}.{c}"]
    # "for the median-PD loan PD x LGD is below the cost of funds", and it is the upper
    # median, so that holds for at least half the book (6.6)
    assert _num(f["pricing.example.pd"]) * _num(f["market.lgd"]) / 100 < _num(f["market.cost_of_funds"])
    pos = int(f["pricing.example.rule"].split()[1].replace(",", ""))
    assert pos >= n / 2
    # the worked example: profitable but short of the hurdle; its recommended rate earns more
    assert f["pricing.example.clears"] == "misses"
    assert 0 < _num(f["pricing.example.roe"]) < _num(f["market.roe_hurdle"])
    assert _num(f["pricing.example.roe_at_recommended"]) > _num(f["market.roe_hurdle"])
    # monitoring threshold (6.8): below the cost-of-funds swings, above opex's and tax's
    move = _num(f["monitoring.pricing_share_move"])
    for fd in ("cost_of_funds",):
        for name in ("up", "down"):
            assert abs(_num(f[f"pricing.sens.{fd}.{name}.swing"])) > move
    for fd in ("opex_rate", "tax_rate"):
        for name in ("up", "down"):
            assert abs(_num(f[f"pricing.sens.{fd}.{name}.swing"])) < move


def test_d6_code_claims_hold():
    """D6 statements about the code, not the facts."""
    import pandas as pd
    from shared.config import MARKET
    from pricing.src.engine import MarketAssumptions, price_loan
    from pricing.src.portfolio import portfolio_summary
    m = MarketAssumptions.from_market(MARKET)
    # the quote never sets a rate the engine produces (6.2, 6.3)
    a, b = price_loan(0.05, 1e5, 0.02, m), price_loan(0.05, 1e5, 0.30, m)
    assert a["recommended_rate"] == b["recommended_rate"]
    assert a["hurdle_clearing_rate"] == b["hurdle_clearing_rate"]
    # fee_rate is outside MARKET and no engine test sets it (6.1, finding 4)
    assert "fee_rate" not in MARKET and m.fee_rate == 0.0
    assert "fee_rate" not in (ROOT / "tests" / "test_engine.py").read_text()
    # the summary has no break-even measure (finding 2)
    df = pd.DataFrame({"clears_hurdle": [True, False], "mispriced": [False, True],
                       "roe_at_quoted": [0.2, -0.1], "ead": [1.0, 2.0],
                       "score_band": ["A", "D"], "industry": ["Retail", "Retail"]})
    assert set(portfolio_summary(df)) == {"n", "n_clears", "share_clears", "median_roe",
                                          "mispriced_ead", "by_band", "by_industry"}
    # verify.py compares exactly these three figures (6.9)
    src = (ROOT / "verify.py").read_text()
    assert 'for k in ("n", "share_clears", "mispriced_ead"):' in src


def test_d6_aaa_calibration_miss_reads_as_noise():
    """Finding 3: an AAA default rate ratio x PD would, by finding 1's algebra, lift the
    typical AAA quote over the capital-charge gap; most AAA loans are mispriced instead."""
    f = _facts()
    lift = (_num(f["score.band_booked.AAA.ratio"]) - 1) * _num(f["pricing.band.AAA.mean_pd"]) \
        * _num(f["market.lgd"]) / 100
    assert lift > _num(f["pricing.capital_charge_less_margin"])
    assert _num(f["pricing.band.AAA.mispriced_rate"]) > 50
    # band D over-predicts on the booked, inside the tolerance (6.5)
    d = _num(f["score.band_booked.D.ratio"])
    assert _num(f["monitoring.ratio_lo"]) <= d < 1
    # "capital_ratio swings more on the -10% side alone" (6.6)
    assert _num(f["pricing.sens.capital_ratio.down.swing"]) > _num(f["pricing.sens.lgd.down.swing"])


def test_signoff_open_findings_are_d7_limitations_word_for_word():
    d11 = _finding_rows(_signoff_section("D7"))
    assert len(d11) == 7
    assert d11 == _finding_rows((WIKI / "mdd" / "ews" / "limitations.qmd").read_text())


def test_d7_has_an_index_and_the_nine_parts_in_order():
    index = (WIKI / "mdd" / "ews" / "index.qmd").read_text()
    assert "order: 0" in index and "Status: complete" in index
    for i, part in enumerate(TEMPLATE_PARTS, 1):
        text = (WIKI / "mdd" / "ews" / f"{part}.qmd").read_text()
        assert f'title: "7.{i} ' in text and f"order: {i}" in text, part
        assert "TEMPLATE" not in text, f"{part}: template brief not replaced"


def test_d7_tier_calibration_findings_follow_the_monitoring_floor():
    """D7.7 applies the floor rule to the tiers (events = deteriorations): a tier outside the
    tolerance on at least the floor's events is finding 5; below it, an observation."""
    f = _facts()
    lo, hi = _num(f["monitoring.ratio_lo"]), _num(f["monitoring.ratio_hi"])
    floor = _num(f["monitoring.min_band_defaults"])
    findings, observations = set(), set()
    for T in ("High", "Medium", "Low"):
        if not lo <= _num(f[f"ews.tier_ho.{T}.ratio"]) <= hi:
            (findings if _num(f[f"ews.tier_ho.{T}.events"]) >= floor else observations).add(T)
    assert findings == {"Low"} and observations == set()
    assert _num(f["ews.tier_ho.Low.ratio"]) > hi            # under-predicts
    for T in ("High", "Medium", "Low"):
        want = "finding" if T in findings else "within tolerance"
        assert f[f"ews.tier_ho.{T}.status"] == want, T
    text = (WIKI / "mdd" / "ews" / "limitations.qmd").read_text()
    f5 = text.split("## Finding 5", 1)[1].split("\n## ", 1)[0]
    assert "ews.tier_ho.Low.ratio" in f5 and "monitoring.min_band_defaults" in f5


def test_d7_prose_conclusions_hold_on_the_facts():
    """Sentences in D7 that state a conclusion about a fact: if the fact moves, the prose must."""
    f = _facts()
    n_book, n_train = _num(f["ews.n_book"]), _num(f["ews.n_train"])
    # "most of the book is the model's own training rows"; training AUC "almost perfect"
    assert n_train / n_book > 0.5 and _num(f["ews.train.auc"]) > 0.99
    # gates met (headline, 7.9); capture "narrowly": small margin, interval straddles the gate,
    # "a quarter of resamples" below it (finding 3)
    gate = _num(f["ews.gate.capture_min"])
    assert _num(f["ews.capture"]) >= gate
    assert 0 < _num(f["ews.gate.capture_events_margin"]) <= 10
    assert _num(f["ews.boot.capture.lo"]) < gate < _num(f["ews.boot.capture.hi"])
    assert 20 <= _num(f["ews.boot.capture_below_gate"]) <= 30
    assert _num(f["ews.capture_events"]) - _num(f["ews.gate.capture_events_needed"]) == \
        _num(f["ews.gate.capture_events_margin"])
    # PR-AUC "firmly": interval wholly above the base rate, no resample at or below it
    base = _num(f["ews.base_rate"]) / 100
    assert _num(f["ews.boot.pr_auc.lo"]) > base and f["ews.boot.pr_auc_at_or_below_base"] == "0.0%"
    # AUC interval wholly above the sanity floor
    assert _num(f["ews.boot.auc.lo"]) > _num(f["ews.gate.auc_floor"])
    # the ceiling: "a hair below" the observable oracle, well inside the AUC interval; the
    # noise-free logit higher on the held-out rows than on the book; the origination gate
    # unreachable even for the noise-free logit; the capture gate below the noise-free capture
    # but "most of what is possible" (7.5, 7.9)
    oracle, auc = _num(f["ceiling.ews.oracle_model.auc"]), _num(f["ews.auc"])
    assert 0 <= oracle - auc < 0.01
    assert oracle - auc < (_num(f["ews.boot.auc.hi"]) - _num(f["ews.boot.auc.lo"])) / 4
    assert _num(f["ceiling.ews.latent_holdout"]) > _num(f["ceiling.ews.latent_book"]) > auc
    assert _num(f["score.gate"]) > _num(f["ceiling.ews.latent_holdout"])
    lat_cap = _num(f["ceiling.ews.latent_capture_holdout"])
    assert lat_cap / 2 < gate < lat_cap
    # the brief's targets (enhancement_notes: AUC 0.75, capture 3x) are out of reach even for
    # the noise-free logit on the held-out accounts (finding 3, 7.9)
    notes = (ROOT / "ews" / "docs" / "enhancement_notes.md").read_text()
    assert "AUC ≥ 0.75" in notes and "capture ≥ 3×" in notes
    assert _num(f["ceiling.ews.latent_holdout"]) < 0.75 and lat_cap < 30
    # benchmark: the paired interval contains zero; pd_score alone misses the capture gate
    assert _num(f["ews.pd_score.diff_lo"]) < 0 < _num(f["ews.pd_score.diff_hi"])
    assert _num(f["ews.pd_score.capture"]) < gate
    # importance: no feature dominates; pd_score not in the top five by gain or split
    assert _num(f["ews.importance.gain.1.share"]) < 15
    assert _num(f["ews.importance.gain.pd_score_rank"]) > 5
    assert _num(f["ews.importance.split.pd_score_rank"]) > 5
    gain_top = {f[f"ews.importance.gain.{i}.feature"] for i in range(1, 6)}
    assert not gain_top & {"industry", "entity_type", "pd_score", "business_score"}
    # whole book far stronger than held out ("severalfold", finding 2)
    assert _num(f["ews.whole.capture"]) > 2 * _num(f["ews.capture"])
    assert _num(f["ews.whole.auc"]) > _num(f["ews.boot.auc.hi"])
    # tiers: rank monotonically; High holds "far fewer" than intended; Medium "a third"
    obs = [_num(f[f"ews.tier_ho.{T}.observed"]) for T in ("High", "Medium", "Low")]
    assert obs == sorted(obs, reverse=True) and len(set(obs)) == 3
    for T, q in (("High", 10.0), ("Medium", 20.0), ("Low", 70.0)):
        assert _num(f[f"ews.tier.{T}.share"]) == q, T
    assert _num(f["ews.tier_ho.High.share"]) < _num(f["ews.tier.High.share"]) / 2
    assert 30 <= _num(f["ews.tier_ho.Medium.share"]) <= 36
    # tier-mix PSI in the watch band at development (7.4, 7.8)
    psi = _num(f["ews.tier_ho.psi_vs_book"])
    assert _num(f["monitoring.psi_watch"]) < psi < _num(f["monitoring.psi_act"])
    # watchlist: almost all training rows; every one High; in-sample rate near perfect
    assert _num(f["ews.watchlist.n_train"]) >= 0.9 * _num(f["ews.watchlist.n"])
    assert f["ews.watchlist.high_n"] == f["ews.watchlist.n"]
    assert _num(f["ews.watchlist.rate"]) > 90
    assert _num(f["ews.watchlist.n_holdout"]) < 10
    # triggers: none dead, exactly one dead clause, and it is dpd_max; DELINQUENCY is
    # dpd_recent alone, "about half the book"; deposit decline "very few"
    assert f["ews.trigger.n_dead"] == "0" and f["ews.trigger.n_dead_clauses"] == "1"
    d = "ews.trigger.delinquency"
    assert f[f"{d}.clause.dpd_max.n_alone"] == "0"
    assert _num(f[f"{d}.clause.dpd_max.feature_max"]) < _num(f[f"{d}.clause.dpd_max.threshold"])
    assert f[f"{d}.clause.dpd_recent.n_alone"] == f[f"{d}.n"]
    assert 45 <= _num(f[f"{d}.share"]) <= 55
    assert _num(f["ews.trigger.deposit_decline.share"]) <= 2
    dd = "ews.trigger.deposit_decline.clause.deposit_decline_pct"
    assert _num(f[f"{dd}.threshold"]) < _num(f[f"{dd}.feature_max"])
    # the other clauses can fire: threshold below the feature's maximum
    for t, c in (("high_utilization", "util_recent"), ("rising_utilization", "util_drift"),
                 ("frequent_overdrafts", "overdraft_recent")):
        k = f"ews.trigger.{t}.clause.{c}"
        assert _num(f[f"{k}.threshold"]) < _num(f[f"{k}.feature_max"]), t
    # triggers "barely beat the base rate", every one below the High tier's lift, together on
    # "most of the book"; precision range quoted from DELINQUENCY (lowest) to HIGH_UTILIZATION
    slugs = ("high_utilization", "rising_utilization", "delinquency", "deposit_decline",
             "frequent_overdrafts")
    lifts = {t: _num(f[f"ews.trigger.{t}.lift"]) for t in slugs}
    assert min(lifts, key=lifts.get) == "delinquency"
    assert max(lifts, key=lifts.get) == "high_utilization"
    assert all(1 < v < 2 and v < _num(f["ews.tier_ho.High.lift"]) for v in lifts.values())
    assert _num(f["ews.trigger.any.share"]) > 50
    assert _num(f["ews.trigger.any.precision"]) > _num(f["ews.trigger.none.rate"])
    # most High accounts carry a trigger, some none; most triggered accounts are not High
    assert _num(f["ews.overlap.high_with_trigger.share"]) > 50
    assert _num(f["ews.overlap.high_no_trigger.n"]) > 0
    assert _num(f["ews.overlap.triggered_not_high.share"]) > 50
    # lift is over the book base rate, equal to the held-out one at the printed precision
    assert f["ews.base_rate"] == f["ews.base_rate_holdout"]


def test_d7_code_claims_hold():
    """D7 statements about the code, not the facts."""
    import inspect
    from ews.src import triggers, watchlist
    src = inspect.getsource(triggers.flag_triggers)
    # DELINQUENCY's second clause is hard-coded, not in EWS_TRIGGERS (7.3, finding 6)
    assert '(dpd_max >= cfg["dpd_severe"]) | (dpd_recent > 0)' in src
    from shared.config import EWS_TRIGGERS
    assert not any("recent" in k and "dpd" in k for k in EWS_TRIGGERS)
    # the pages print each clause's operator as a literal (a var shortcode drops ">"): the
    # facts must still agree with what is printed
    f = _facts()
    ops = {"high_utilization.clause.util_recent": ">", "rising_utilization.clause.util_drift": ">",
           "delinquency.clause.dpd_max": ">=", "delinquency.clause.dpd_recent": ">",
           "deposit_decline.clause.deposit_decline_pct": ">",
           "frequent_overdrafts.clause.overdraft_recent": ">="}
    pages = "".join(p.read_text() for p in (WIKI / "mdd" / "ews").glob("*.qmd"))
    for k, op in ops.items():
        assert f[f"ews.trigger.{k}.op"] == op, k
        assert f"`{k.rsplit('.', 1)[1]} {op}`" in pages, k
    assert ".op >}}" not in pages
    # the only trigger unit test fires DELINQUENCY through dpd_max with dpd_recent zero
    test = (ROOT / "tests" / "test_triggers_and_rules.py").read_text()
    assert '"dpd_max": 45, "dpd_recent": 0' in test and '"dpd_recent": 1' not in test
    # no EWS leakage test (7.2 observation)
    assert "ews" not in (ROOT / "tests" / "test_leakage.py").read_text().lower()
    # watchlist default length 100; the v1 endpoint's 25 (7.1)
    assert inspect.signature(watchlist.watchlist).parameters["top_n"].default == 100
    assert "def ews_watchlist_endpoint(n: int = 25):" in (ROOT / "app" / "main.py").read_text()
    # verify.py computes capture with its own lines and gates on the three (7.9)
    v = (ROOT / "verify.py").read_text()
    assert "capture = float(y_te[np.argsort(p)[::-1][:k]].sum() / y_te.sum())" in v
    assert "if capture < EWS_CAPTURE_GATE or pr <= base or auc < EWS_AUC_FLOOR:" in v
    # train.py asserts all three, last
    t = (ROOT / "ews" / "src" / "train.py").read_text()
    for line in ("assert capture >= CAPTURE_GATE", "assert pr_auc > base",
                 "assert auc >= AUC_REPORT_FLOOR"):
        assert line in t and t.index(line) > t.index('(DOCS / "validation_report.md").write_text'), line
