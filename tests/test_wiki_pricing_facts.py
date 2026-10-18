"""D6's facts are recomputed through the pricing module's own functions (price_population,
portfolio_summary and the engine). They must print exactly what pricing/docs/summary.json
recorded. If a pin fails, investigate the computation — never edit the pinned value."""
import json
import os

import pytest

from shared.config import MARKET, ROOT

SUMMARY = json.loads((ROOT / "pricing/docs/summary.json").read_text())
BANDS = ("D", "C", "B", "A", "AAA")


@pytest.fixture(scope="module")
def pf():
    os.chdir(ROOT)
    from wiki.facts import pricing_facts
    return pricing_facts.compute()


@pytest.fixture(scope="module")
def t(pf):
    return {k: v.text() for k, v in pf.items()}


def _n(s: str) -> int:
    return int(s.replace(",", ""))


def test_headline_prints_what_summary_json_recorded(t):
    assert t["pricing.n"] == f"{SUMMARY['n']:,d}" == "8,336"
    assert t["pricing.n_clears"] == f"{SUMMARY['n_clears']:,d}" == "2,534"
    assert t["pricing.share_clears"] == f"{SUMMARY['share_clears']:.1%}" == "30.4%"
    assert t["pricing.median_roe"] == f"{SUMMARY['median_roe']:.1%}" == "10.9%"
    assert t["pricing.mispriced_ead"] == f"{SUMMARY['mispriced_ead']:,.0f}" == "1,276,148,000"
    # the validation report prints the same strings
    report = (ROOT / "pricing/docs/validation_report.md").read_text()
    for k in ("n", "n_clears", "share_clears", "median_roe"):
        assert t[f"pricing.{k}"] in report, k
    assert f"${t['pricing.mispriced_ead']}" in report


def test_segments_print_what_summary_json_recorded(t):
    for r in SUMMARY["by_band"]:
        assert t[f"pricing.band.{r['key']}.mispriced_rate"] == f"{r['mispriced_rate']:.1%}"
        assert t[f"pricing.band.{r['key']}.n"] == f"{r['count']:,d}"
    from wiki.facts.pricing_facts import slug
    for r in SUMMARY["by_industry"]:
        assert t[f"pricing.industry.{slug(r['key'])}.mispriced_rate"] == f"{r['mispriced_rate']:.1%}"
        assert t[f"pricing.industry.{slug(r['key'])}.n"] == f"{r['count']:,d}"
        assert t[f"pricing.industry.{slug(r['key'])}.name"] == r["key"]


def test_mispricing_concentrates_in_the_safest_bands(t):
    assert t["pricing.worst_band"] == "AAA" and t["pricing.second_band"] == "A"
    assert t["pricing.worst_band_rate"] == t["pricing.band.AAA.mispriced_rate"]


def test_no_pricing_fact_reads_summary_json(pf):
    assert not any("summary.json" in f.source for f in pf.values())


def test_every_fact_names_its_population(pf):
    assert all(f.population for f in pf.values())


def test_market_facts_cover_every_market_field(pf):
    keys = {k.split(".", 1)[1] for k in pf if k.startswith("market.")}
    assert keys == set(MARKET)
    for k in keys:
        assert pf[f"market.{k}"].value == MARKET[k]
        assert pf[f"market.{k}"].source == "shared.config.MARKET"
        assert pf[f"market.{k}"].population == "platform assumption"
    assert pf["market.roe_hurdle"].text() == "15%"


def test_counts_add_up(t, pf):
    assert _n(t["pricing.n_clears"]) + _n(t["pricing.n_mispriced"]) == _n(t["pricing.n"])
    assert sum(_n(t[f"pricing.band.{b}.n"]) for b in BANDS) == _n(t["pricing.n"])
    assert sum(pf[f"pricing.band.{b}.ead"].value for b in BANDS) == \
        pytest.approx(pf["pricing.total_ead"].value)
    assert sum(pf[f"pricing.band.{b}.mispriced_ead"].value for b in BANDS) == \
        pytest.approx(pf["pricing.mispriced_ead"].value)
    # quoted below break-even is exactly the negative-ROE set
    assert t["pricing.below_break_even.n"] == t["pricing.negative_roe.n"]


BOUND_KEYS = [f"pricing.identity.{k}" for k in
              ("break_even", "hurdle", "recommended", "waterfall", "ead_invariance", "max")] + \
             ["pricing.whatif.max_diff", "pricing.whatif.pd_max_diff"]


def test_residuals_print_as_the_test_tolerance_bound(pf):
    """compute() raises if any residual reaches the tolerance; the page prints the bound,
    so the text is the same on every platform."""
    tol = pf["pricing.test_tolerance"].value
    assert tol == 1e-12 and pf["pricing.n_engine_tests"].value == 6
    for k in BOUND_KEYS:
        assert pf[k].text() == "< 1e-12" and pf[k].fmt == "", k
        assert "tests/test_engine.py" in pf[k].source and "asserted" in pf[k].source, k
    assert "pricing.whatif.n_pd_differ" not in pf


def test_identity_residuals_are_below_the_tolerance_on_every_booked_loan():
    """The real values behind the bounds, recomputed here, not trusted from compute()."""
    os.chdir(ROOT)
    from pricing.src.engine import (MarketAssumptions, break_even_rate,
                                    hurdle_clearing_rate, profit_waterfall, recommended_rate)
    from wiki.facts.pricing_facts import _booked_inputs, engine_test_tolerance
    m, tol = MarketAssumptions.from_market(MARKET), engine_test_tolerance()
    worst = 0.0
    for p, e, q in _booked_inputs()[["pd", "ead", "quoted_rate"]].itertuples(index=False):
        hc = hurdle_clearing_rate(p, e, m)
        worst = max(worst, abs(profit_waterfall(p, e, break_even_rate(p, e, m), m)["roe"]),
                    abs(profit_waterfall(p, e, hc, m)["roe"] - m.roe_hurdle),
                    abs(recommended_rate(p, e, m) - hc - m.base_margin),
                    abs(profit_waterfall(p, e, q, m)["roe"] - profit_waterfall(p, 1.0, q, m)["roe"]))
    assert worst < tol


def test_portal_and_batch_pds_agree_below_the_tolerance():
    os.chdir(ROOT)
    import pandas as pd
    from score.src.predict import predict_score_pd
    from shared.config import RAW
    from wiki.facts.pricing_facts import _booked_inputs, engine_test_tolerance
    biz = pd.read_parquet(RAW / "businesses.parquet")
    portal = predict_score_pd(biz).set_axis(biz["business_id"], axis=0)["pd"]
    batch = _booked_inputs().set_index("business_id")["pd"]
    assert (portal.loc[batch.index] - batch).abs().max() < engine_test_tolerance()


def test_worked_example_adds_up(pf):
    v = lambda k: pf[f"pricing.example.{k}"].value
    wf = lambda k: v(f"wf.{k}")
    assert wf("pre_tax_profit") == pytest.approx(
        wf("interest_income") - wf("cost_of_funds") - wf("expected_loss") - wf("operating_cost"))
    assert wf("net_income") == pytest.approx(wf("pre_tax_profit") - wf("tax"))
    assert v("roe") == pytest.approx(wf("net_income") / wf("allocated_equity"))
    assert v("break_even") < v("hurdle_clearing") < v("recommended")
    assert v("recommended") - v("hurdle_clearing") == pytest.approx(MARKET["base_margin"])
    assert (v("quoted_rate") >= v("hurdle_clearing")) == (v("clears") == "clears")


def test_whatif_equals_batch(pf):
    assert pf["pricing.whatif.flips"].value == 0


SCENARIOS = [(fd, n) for fd in ("cost_of_funds", "lgd", "opex_rate", "tax_rate",
                                "capital_ratio", "roe_hurdle") for n in ("down", "up")]


@pytest.mark.parametrize("field,name", SCENARIOS)
def test_printed_swing_is_printed_share_minus_printed_base(t, field, name):
    k = f"pricing.sens.{field}.{name}"
    share, base = float(t[f"{k}.share_clears"].rstrip("%")), float(t["pricing.share_clears"].rstrip("%"))
    assert float(t[f"{k}.swing"].rstrip("%")) == pytest.approx(round(share - base, 1), abs=1e-9)


def test_shares_are_unrounded_counts_over_n(pf):
    n = pf["pricing.n"].value
    assert pf["pricing.share_clears"].value == pf["pricing.n_clears"].value / n
    for fd, name in SCENARIOS:
        k = f"pricing.sens.{fd}.{name}"
        assert pf[f"{k}.share_clears"].value == pf[f"{k}.n_clears"].value / n


def test_worked_example_is_the_upper_median_loan(t, pf):
    assert t["pricing.example.rule"].startswith("position 4,169 of 8,336")
    assert "upper-median" in pf["pricing.example.business_id"].population


def _v(pf, field, name, col):
    return pf[f"pricing.sens.{field}.{name}.{col}"].value


@pytest.mark.parametrize("field", ["cost_of_funds", "lgd", "opex_rate", "tax_rate",
                                   "capital_ratio", "roe_hurdle"])
def test_raising_a_cost_or_the_hurdle_cannot_raise_share_clears(pf, field):
    base = pf["pricing.n_clears"].value
    assert _v(pf, field, "up", "n_clears") <= base <= _v(pf, field, "down", "n_clears")
    assert _v(pf, field, "up", "mispriced_ead") >= pf["pricing.mispriced_ead"].value \
        >= _v(pf, field, "down", "mispriced_ead")


def test_the_hurdle_moves_the_verdict_not_the_roe(pf):
    for name in ("up", "down"):
        assert _v(pf, "roe_hurdle", name, "median_roe") == pf["pricing.median_roe"].value


def test_pd_scaling_moves_the_book_the_right_way(pf):
    up, down = (pf[f"pricing.pd_scale.{n}.n_clears"].value for n in ("up", "down"))
    assert up <= pf["pricing.n_clears"].value <= down
    # PD enters the engine only as PD x LGD, so scaling the PD is scaling the LGD
    for n in ("up", "down"):
        for c in ("n_clears", "median_roe", "mispriced_ead"):
            assert pf[f"pricing.pd_scale.{n}.{c}"].value == _v(pf, "lgd", n, c)


def test_pd_scaling_at_one_reproduces_price_population():
    os.chdir(ROOT)
    from pricing.src.engine import MarketAssumptions
    from pricing.src.portfolio import price_population
    from wiki.facts.pricing_facts import _booked_inputs, price_with_pd
    m = MarketAssumptions.from_market(MARKET)
    a, b = price_with_pd(_booked_inputs(), 1.0, m), price_population()
    cols = list(b.columns)
    assert a[cols].equals(b[cols])


def test_tables_render_from_the_facts(t):
    from wiki.facts import build_facts, tables
    from wiki.facts.core import load_facts
    committed = load_facts(build_facts.FACTS_JSON)
    files = tables.render_all({**{k: d["text"] for k, d in committed.items()}, **t}, committed)
    for name in ("market", "headline", "bands", "industries", "sensitivity", "pd-scaling",
                 "waterfall"):
        body = files[f"_generated/pricing-{name}.md"]
        assert body.startswith(tables.HEADER) and "| " in body
    assert t["pricing.mispriced_ead"] in files["_generated/pricing-headline.md"]
    assert t["pricing.example.business_id"] in files["_generated/pricing-waterfall.md"]
    assert t["pricing.sens.cost_of_funds.up.share_clears"] in \
        files["_generated/pricing-sensitivity.md"]


def test_rate_identities_hold_at_a_non_zero_fee(pf, t):
    """No unit test sets fee_rate, though the v2 what-if exposes it (D6.7): the facts
    re-check break-even and hurdle-clearing at FEE_PROBE on every booked loan."""
    from pricing.src.engine import (MarketAssumptions, break_even_rate,
                                    hurdle_clearing_rate, profit_waterfall)
    assert pf["pricing.fee_probe"].value > 0
    assert t["pricing.identity.fee"] == "< 1e-12"
    m = MarketAssumptions.from_market(MARKET).replace(fee_rate=pf["pricing.fee_probe"].value)
    for p in (0.001, 0.05, 0.4):
        assert profit_waterfall(p, 5e4, break_even_rate(p, 5e4, m), m)["roe"] == \
            pytest.approx(0.0, abs=1e-12)
        assert profit_waterfall(p, 5e4, hurdle_clearing_rate(p, 5e4, m), m)["roe"] == \
            pytest.approx(m.roe_hurdle, abs=1e-12)


def test_verify_tolerance_is_read_from_verify_py(pf):
    import verify
    assert pf["pricing.verify_tolerance"].value == verify.PRICING_TOLERANCE
