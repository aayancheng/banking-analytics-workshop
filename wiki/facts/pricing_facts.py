"""Facts about the pricing tool (D6), recomputed through the module's own functions exactly
as the platform runs it (app/main.py): price_population over the booked book with the PD
from predict_score_pd, summarised by portfolio_summary, and the engine's own
profit_waterfall / break_even_rate / hurdle_clearing_rate / recommended_rate / price_loan.

Pricing is a deterministic calculation tool (D0): there is no discrimination or
calibration to measure. What it has instead is arithmetic that must hold exactly, inputs
(the market assumptions and the score's PD) whose movement moves every rate, and a what-if
path in the portal that must equal the batch run.

pricing/docs/summary.json is not read for any number. tests/test_wiki_pricing_facts.py
pins that the recomputed values print identically to what it recorded."""
from __future__ import annotations

import ast
import re
from types import SimpleNamespace

import numpy as np
import pandas as pd

from pricing.src.engine import (
    MarketAssumptions, break_even_rate, hurdle_clearing_rate, price_loan,
    profit_waterfall, recommended_rate,
)
from pricing.src.portfolio import portfolio_summary, price_population
from score.src.predict import predict_score_pd
from shared.config import MARKET, RAW, ROOT
from wiki.facts.core import Fact

BOOKED = ("booked book, 8,336 loans (PD from predict_score_pd, EAD = requested_amount, "
          "quoted rate = risk_based_rate)")
ASSUMPTION = "platform assumption"
MODULE_POP = "module constant"
EXAMPLE = ("one booked loan: the upper-median-PD loan of the booked book "
           "(see pricing.example.rule)")

SRC_PP = "pricing.src.portfolio.price_population"
SRC_SUM = "pricing.src.portfolio.portfolio_summary"
SRC_MKT = "shared.config.MARKET"
SRC_WF = "pricing.src.engine.profit_waterfall"
SENS_STEP = 0.10            # each market assumption moved by +-10% (relative)
SENS_FIELDS = ["cost_of_funds", "lgd", "opex_rate", "tax_rate", "capital_ratio", "roe_hurdle"]
SENS_FMT = {"cost_of_funds": ".2%", "lgd": ".1%", "opex_rate": ".1%", "tax_rate": ".1%",
            "capital_ratio": ".1%", "roe_hurdle": ".1%"}
SENS_CHECK = ("cost_of_funds", "up")   # the one scenario re-run through price_population
PD_SCALES = [("down", 0.9), ("up", 1.1)]
FEE_PROBE = 0.005           # a non-zero fee_rate at which the rate identities are re-checked
BANDS = ["D", "C", "B", "A", "AAA"]
WATERFALL = ["interest_income", "cost_of_funds", "expected_loss", "operating_cost",
             "pre_tax_profit", "tax", "net_income", "allocated_equity"]
# MARKET field -> print format. Every field of shared.config.MARKET is a fact.
MARKET_FMT = {"cost_of_funds": ".1%", "lgd": ".0%", "opex_rate": ".1%", "tax_rate": ".0%",
              "capital_ratio": ".0%", "base_margin": ".1%", "roe_hurdle": ".0%"}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _booked_inputs() -> pd.DataFrame:
    """The inputs price_population feeds the engine, row for row, in its order."""
    biz = pd.read_parquet(RAW / "businesses.parquet")
    booked = biz[biz["booked"] == True].copy()  # noqa: E712
    sp = predict_score_pd(booked).reset_index(drop=True)
    booked = booked.reset_index(drop=True)
    return pd.DataFrame({"business_id": booked["business_id"].astype(str),
                         "industry": booked["industry"].astype(str),
                         "score_band": sp["score_band"].astype(str),
                         "pd": sp["pd"].astype(float),
                         "ead": booked["requested_amount"].astype(float),
                         "quoted_rate": booked["risk_based_rate"].astype(float)})


def price_with_pd(inp: pd.DataFrame, pd_scale: float, market: MarketAssumptions) -> pd.DataFrame:
    """price_population's loop, re-run over the same booked rows with the PD scaled.
    price_population takes no PD override, so this repeats its per-row call to price_loan;
    compute() asserts that at scale 1.0 it reproduces price_population exactly."""
    rows = []
    for bid, ind, band, p, ead, q in inp[["business_id", "industry", "score_band", "pd", "ead",
                                          "quoted_rate"]].itertuples(index=False):
        r = price_loan(pd_=min(p * pd_scale, 1.0), ead=ead, quoted_rate=q, market=market)
        rows.append({"business_id": bid, "industry": ind, "score_band": band,
                     **{k: r[k] for k in ("ead", "pd", "quoted_rate", "recommended_rate",
                                          "roe_at_quoted", "raroc_at_quoted", "clears_hurdle",
                                          "mispriced", "rate_shortfall")}})
    return pd.DataFrame(rows)


def _printed_share(x: float) -> float:
    """x as its .1% text prints it, back as a fraction (round(x, 3) via the formatter)."""
    return float(f"{x:.1%}"[:-1]) / 100


def n_engine_tests() -> int:
    tree = ast.parse((ROOT / "tests" / "test_engine.py").read_text())
    return sum(isinstance(n, ast.FunctionDef) and n.name.startswith("test_") for n in tree.body)


def engine_test_tolerance() -> float:
    """The absolute tolerance tests/test_engine.py demands of the rate solvers."""
    tols = {float(x) for x in re.findall(r"abs=([0-9.e-]+)",
                                         (ROOT / "tests" / "test_engine.py").read_text())}
    assert len(tols) == 1, f"tests/test_engine.py uses several tolerances: {tols}"
    return tols.pop()


def verify_tolerance() -> float:
    """verify.py's relative tolerance on the committed pricing summary, read from its source."""
    m = re.search(r"^PRICING_TOLERANCE\s*=\s*([0-9.]+)", (ROOT / "verify.py").read_text(), re.M)
    assert m, "verify.py no longer defines PRICING_TOLERANCE"
    return float(m.group(1))


def market_facts() -> dict[str, Fact]:
    """Every field of shared.config.MARKET, cheap: no pricing run needed."""
    assert set(MARKET) == set(MARKET_FMT), "shared.config.MARKET gained or lost a field"
    return {f"market.{k}": Fact(float(MARKET[k]), fmt, SRC_MKT, ASSUMPTION)
            for k, fmt in MARKET_FMT.items()}


def compute() -> dict[str, Fact]:
    m = MarketAssumptions.from_market(MARKET)
    f: dict[str, Fact] = market_facts()

    def put(key, value, fmt, source, population):
        f[key] = Fact(value, fmt, source, population)

    # --- the engine's one default outside MARKET, and the capital charge it implies ---
    put("pricing.fee_rate", float(m.fee_rate), ".1%",
        "pricing.src.engine.MarketAssumptions.fee_rate (default; not set in MARKET)", ASSUMPTION)
    cap = hurdle_clearing_rate(0.0, 1.0, m) - break_even_rate(0.0, 1.0, m)
    put("pricing.capital_charge", cap, ".1%",
        "hurdle_clearing_rate - break_even_rate (= roe_hurdle x capital_ratio / (1 - tax_rate))",
        ASSUMPTION)
    put("pricing.capital_charge_less_margin", cap - m.base_margin, ".1%",
        "hurdle_clearing_rate - break_even_rate - MARKET.base_margin", ASSUMPTION)

    # --- headline: price_population + portfolio_summary, exactly as the portal runs them ---
    df = price_population()
    s = portfolio_summary(df)
    put("pricing.n", s["n"], ",d", SRC_SUM, BOOKED)
    put("pricing.n_clears", s["n_clears"], ",d", SRC_SUM, BOOKED)
    put("pricing.n_mispriced", int(df["mispriced"].sum()), ",d", SRC_PP, BOOKED)
    put("pricing.share_clears", s["n_clears"] / s["n"], ".1%", SRC_SUM + " (n_clears / n, unrounded)",
        BOOKED)
    put("pricing.share_mispriced", float(df["mispriced"].mean()), ".1%", SRC_PP, BOOKED)
    put("pricing.median_roe", s["median_roe"], ".1%", SRC_SUM, BOOKED)
    put("pricing.mispriced_ead", s["mispriced_ead"], ",.0f", SRC_SUM, BOOKED)
    put("pricing.total_ead", float(df["ead"].sum()), ",.0f", SRC_PP, BOOKED)
    put("pricing.mispriced_ead_share", float(df.loc[df["mispriced"], "ead"].sum() / df["ead"].sum()),
        ".1%", SRC_PP, BOOKED)
    mis = df[df["mispriced"]]
    put("pricing.median_shortfall_bps", float(mis["rate_shortfall"].median() * 1e4), ".0f",
        SRC_PP + " (rate_shortfall, in basis points)", BOOKED + " -- mispriced loans only")
    put("pricing.median_quoted_rate", float(df["quoted_rate"].median()), ".2%", SRC_PP, BOOKED)
    put("pricing.median_recommended_rate", float(df["recommended_rate"].median()), ".2%",
        SRC_PP, BOOKED)

    # --- where the mispricing concentrates: band and industry (portfolio_summary's segments) ---
    by_band = {r["key"]: r for r in s["by_band"]}
    assert set(by_band) == set(BANDS), f"unexpected score bands {sorted(by_band)}"
    for b in BANDS:
        g = df[df["score_band"] == b]
        pop = f"booked book, score band {b}"
        put(f"pricing.band.{b}.n", by_band[b]["count"], ",d", SRC_SUM, pop)
        put(f"pricing.band.{b}.mispriced_rate", by_band[b]["mispriced_rate"], ".1%", SRC_SUM, pop)
        put(f"pricing.band.{b}.ead", float(g["ead"].sum()), ",.0f", SRC_PP, pop)
        put(f"pricing.band.{b}.mispriced_ead", float(g.loc[g["mispriced"], "ead"].sum()), ",.0f",
            SRC_PP, pop)
        put(f"pricing.band.{b}.median_roe", float(g["roe_at_quoted"].median()), ".1%", SRC_PP, pop)
        put(f"pricing.band.{b}.mean_pd", float(g["pd"].mean()), ".2%", SRC_PP, pop)
        put(f"pricing.band.{b}.mean_quoted", float(g["quoted_rate"].mean()), ".2%", SRC_PP, pop)
        put(f"pricing.band.{b}.mean_recommended", float(g["recommended_rate"].mean()), ".2%",
            SRC_PP, pop)
    ranked = sorted(BANDS, key=lambda b: (-by_band[b]["mispriced_rate"], b))
    for tag, b in (("worst_band", ranked[0]), ("second_band", ranked[1]),
                   ("best_band", ranked[-1])):
        put(f"pricing.{tag}", b, "", SRC_SUM + " (bands ranked by mispriced rate)", BOOKED)
        put(f"pricing.{tag}_rate", by_band[b]["mispriced_rate"], ".1%", SRC_SUM,
            f"booked book, score band {b}")

    by_ind = {r["key"]: r for r in s["by_industry"]}
    for name, r in by_ind.items():
        k, pop = slug(name), f"booked book, industry {name}"
        put(f"pricing.industry.{k}.name", name, "", "businesses.industry", pop)
        put(f"pricing.industry.{k}.n", r["count"], ",d", SRC_SUM, pop)
        put(f"pricing.industry.{k}.mispriced_rate", r["mispriced_rate"], ".1%", SRC_SUM, pop)
    ranked_i = sorted(by_ind, key=lambda i: (-by_ind[i]["mispriced_rate"], i))
    for tag, name in (("worst_industry", ranked_i[0]), ("best_industry", ranked_i[-1])):
        put(f"pricing.{tag}", name, "", SRC_SUM + " (industries ranked by mispriced rate)",
            BOOKED)
        put(f"pricing.{tag}_rate", by_ind[name]["mispriced_rate"], ".1%", SRC_SUM,
            f"booked book, industry {name}")

    # --- the arithmetic, worked on one loan: the upper-median-PD loan, chosen deterministically ---
    inp = _booked_inputs()
    order = inp.sort_values(["pd", "business_id"], kind="stable").index
    ex = inp.loc[order[len(order) // 2]]
    put("pricing.example.rule", f"position {len(order) // 2 + 1:,d} of {len(order):,d} when "
        "the booked book is ordered by score PD, then business_id", "",
        "wiki.facts.pricing_facts (worked-example selection)", EXAMPLE)
    pd_, ead, q = float(ex["pd"]), float(ex["ead"]), float(ex["quoted_rate"])
    r = price_loan(pd_, ead, q, m)
    w = profit_waterfall(pd_, ead, q, m)
    put("pricing.example.business_id", str(ex["business_id"]), "", SRC_PP, EXAMPLE)
    put("pricing.example.band", str(ex["score_band"]), "", "predict_score_pd", EXAMPLE)
    put("pricing.example.industry", str(ex["industry"]), "", "businesses.industry", EXAMPLE)
    put("pricing.example.pd", pd_, ".2%", "predict_score_pd", EXAMPLE)
    put("pricing.example.ead", ead, ",.0f", "businesses.requested_amount", EXAMPLE)
    put("pricing.example.quoted_rate", q, ".2%", "businesses.risk_based_rate", EXAMPLE)
    for k in WATERFALL:
        put(f"pricing.example.wf.{k}", float(w[k]), ",.0f", SRC_WF + " at the quoted rate", EXAMPLE)
    put("pricing.example.roe", float(w["roe"]), ".1%", SRC_WF + " at the quoted rate", EXAMPLE)
    put("pricing.example.raroc", float(w["raroc"]), ".1%", SRC_WF + " at the quoted rate", EXAMPLE)
    put("pricing.example.break_even", break_even_rate(pd_, ead, m), ".2%",
        "pricing.src.engine.break_even_rate", EXAMPLE)
    put("pricing.example.hurdle_clearing", hurdle_clearing_rate(pd_, ead, m), ".2%",
        "pricing.src.engine.hurdle_clearing_rate", EXAMPLE)
    put("pricing.example.recommended", recommended_rate(pd_, ead, m), ".2%",
        "pricing.src.engine.recommended_rate", EXAMPLE)
    put("pricing.example.shortfall_bps", r["rate_shortfall"] * 1e4, ".0f",
        "pricing.src.engine.price_loan (rate_shortfall, in basis points)", EXAMPLE)
    put("pricing.example.clears", "clears" if r["clears_hurdle"] else "misses", "",
        "pricing.src.engine.price_loan (clears_hurdle)", EXAMPLE)
    put("pricing.example.roe_at_recommended", float(r["roe_at_recommended"]), ".1%",
        "pricing.src.engine.price_loan", EXAMPLE)

    # --- identities the engine's tests rely on, checked on every booked loan ---
    res = {k: 0.0 for k in ("break_even", "hurdle", "recommended", "waterfall", "ead_invariance")}
    be_all = np.empty(len(inp))
    for i, (p, e, qr) in enumerate(inp[["pd", "ead", "quoted_rate"]].itertuples(index=False)):
        be, hc = break_even_rate(p, e, m), hurdle_clearing_rate(p, e, m)
        be_all[i] = be
        res["break_even"] = max(res["break_even"], abs(profit_waterfall(p, e, be, m)["roe"]))
        res["hurdle"] = max(res["hurdle"],
                            abs(profit_waterfall(p, e, hc, m)["roe"] - m.roe_hurdle))
        res["recommended"] = max(res["recommended"],
                                 abs(recommended_rate(p, e, m) - hc - m.base_margin))
        wq = profit_waterfall(p, e, qr, m)
        res["waterfall"] = max(res["waterfall"], abs(
            wq["pre_tax_profit"] - (wq["interest_income"] - wq["cost_of_funds"]
                                    - wq["expected_loss"] - wq["operating_cost"])) / e,
            abs(wq["net_income"] - wq["pre_tax_profit"] * (1 - m.tax_rate)) / e,
            abs(wq["roe"] - wq["net_income"] / wq["allocated_equity"]))
        res["ead_invariance"] = max(res["ead_invariance"],
                                    abs(wq["roe"] - profit_waterfall(p, 1.0, qr, m)["roe"]))
    labels = {
        "break_even": "|ROE at break_even_rate - 0|",
        "hurdle": "|ROE at hurdle_clearing_rate - roe_hurdle|",
        "recommended": "|recommended_rate - hurdle_clearing_rate - base_margin|",
        "waterfall": "waterfall sums (per $ of EAD) and ROE = net income / equity",
        "ead_invariance": "|ROE at the loan's EAD - ROE at EAD 1|",
    }
    # Residuals are ~1e-16 and their last digits depend on the platform, so each is
    # asserted below the engine tests' tolerance and printed as that bound.
    tol = engine_test_tolerance()
    bound = f"< {tol:.0e}"
    src_bound = (" -- asserted below tests/test_engine.py's tolerance (pytest.approx abs=) "
                 "in wiki.facts.pricing_facts.compute")
    labels["max"] = "the largest of the pricing.identity.* residuals"
    res["max"] = max(res.values())
    for k, lab in labels.items():
        if not res[k] < tol:
            raise AssertionError(f"pricing identity {k} residual {res[k]:.3e} >= {tol:.0e}")
        put(f"pricing.identity.{k}", bound, "",
            f"pricing.src.engine, max over the booked book of {lab}{src_bound}", BOOKED)
    # --- the same two rate identities with a non-zero fee_rate (no unit test sets one) ---
    mf = m.replace(fee_rate=FEE_PROBE)
    fee_res = 0.0
    for p, e in inp[["pd", "ead"]].itertuples(index=False):
        fee_res = max(fee_res,
                      abs(profit_waterfall(p, e, break_even_rate(p, e, mf), mf)["roe"]),
                      abs(profit_waterfall(p, e, hurdle_clearing_rate(p, e, mf), mf)["roe"]
                          - mf.roe_hurdle))
    if not fee_res < tol:
        raise AssertionError(f"fee_rate identity residual {fee_res:.3e} >= {tol:.0e}")
    put("pricing.fee_probe", FEE_PROBE, ".1%", "wiki.facts.pricing_facts.FEE_PROBE", MODULE_POP)
    put("pricing.identity.fee", bound, "",
        "pricing.src.engine with fee_rate = wiki.facts.pricing_facts.FEE_PROBE, max over the "
        "booked book of |ROE at break_even_rate - 0| and |ROE at hurdle_clearing_rate - "
        "roe_hurdle|" + src_bound, BOOKED)
    put("pricing.verify_tolerance", verify_tolerance(), ".0%",
        "verify.py PRICING_TOLERANCE (relative drift of n, share_clears and mispriced_ead "
        "against the committed pricing summary)", MODULE_POP)
    put("pricing.n_engine_tests", n_engine_tests(), "d",
        "tests/test_engine.py (test_ functions, counted with ast)", MODULE_POP)
    put("pricing.test_tolerance", tol, ".0e",
        "tests/test_engine.py (pytest.approx abs= for the rate solvers)", MODULE_POP)

    # --- loss-making at its own quoted rate: quoted below break-even ---
    below = inp["quoted_rate"].to_numpy() < be_all
    put("pricing.below_break_even.n", int(below.sum()), ",d",
        "pricing.src.engine.break_even_rate vs the quoted rate", BOOKED)
    put("pricing.below_break_even.share", float(below.mean()), ".1%",
        "pricing.src.engine.break_even_rate vs the quoted rate", BOOKED)
    put("pricing.below_break_even.ead", float(inp.loc[below, "ead"].sum()), ",.0f",
        "pricing.src.engine.break_even_rate vs the quoted rate", BOOKED)
    negative = (df["roe_at_quoted"] < 0).to_numpy()
    assert np.array_equal(below, negative), "below break-even is no longer the negative-ROE set"
    put("pricing.negative_roe.n", int(negative.sum()), ",d", SRC_PP, BOOKED)

    # --- the what-if equals the batch: the portal's v2 price_one vs price_population ---
    from app.v2.pricing import price_one
    biz = pd.read_parquet(RAW / "businesses.parquet")
    state = SimpleNamespace(profiles=biz.set_index("business_id"),
                            scores=predict_score_pd(biz).set_axis(biz["business_id"], axis=0))
    pd_batch = df.set_index("business_id")["pd"]
    pd_diff = float((state.scores.loc[pd_batch.index, "pd"] - pd_batch).abs().max())
    if not pd_diff < tol:
        raise AssertionError(f"portal and batch PDs differ by {pd_diff:.3e} >= {tol:.0e}")
    put("pricing.whatif.pd_max_diff", bound, "",
        "predict_score_pd on all 12,000 applicants (the portal) vs on the booked rows alone "
        "(price_population): max abs PD difference" + src_bound, BOOKED)
    worst = 0.0
    flips = 0
    for row in df.itertuples(index=False):
        v = price_one(state, row.business_id, m)
        worst = max(worst, abs(v["verdict"]["roe"] - row.roe_at_quoted),
                    abs(v["rates"]["recommended"] - row.recommended_rate),
                    abs(v["rates"]["quoted"] - row.quoted_rate))
        flips += v["verdict"]["clears_hurdle"] != row.clears_hurdle
    if not worst < tol:
        raise AssertionError(f"what-if and batch differ by {worst:.3e} >= {tol:.0e}")
    put("pricing.whatif.max_diff", bound, "",
        "app.v2.pricing.price_one (the portal's what-if path) vs price_population, max abs "
        "difference in ROE, recommended and quoted rate" + src_bound, BOOKED)
    put("pricing.whatif.flips", int(flips), ",d",
        "app.v2.pricing.price_one vs price_population (clears_hurdle disagreements)", BOOKED)

    # --- PD dependency: the same rows re-priced with the score's PD scaled ---
    base = price_with_pd(inp, 1.0, m)
    cols = ["business_id", "ead", "pd", "quoted_rate", "recommended_rate", "roe_at_quoted",
            "clears_hurdle", "mispriced", "rate_shortfall"]
    assert base[cols].equals(df[cols]), "price_with_pd(1.0) no longer reproduces price_population"
    for name, k in PD_SCALES:
        s2 = portfolio_summary(price_with_pd(inp, k, m))
        s2["share_clears"] = s2["n_clears"] / s2["n"]      # unrounded
        src = f"price_loan over the booked rows with predict_score_pd's pd x {k}"
        pop = BOOKED + f" -- PD scaled x {k}"
        put(f"pricing.pd_scale.{name}.factor", k, ".1f", "wiki.facts.pricing_facts.PD_SCALES",
            MODULE_POP)
        put(f"pricing.pd_scale.{name}.share_clears", s2["share_clears"], ".1%", src, pop)
        put(f"pricing.pd_scale.{name}.n_clears", s2["n_clears"], ",d", src, pop)
        put(f"pricing.pd_scale.{name}.median_roe", s2["median_roe"], ".1%", src, pop)
        put(f"pricing.pd_scale.{name}.mispriced_ead", s2["mispriced_ead"], ",.0f", src, pop)

    # --- sensitivity to each market assumption, +-10% relative ---
    # Priced through price_with_pd (price_population's per-row price_loan loop over inputs
    # read once) with the stressed MarketAssumptions; one stressed scenario is checked
    # against a real price_population(market=...) call, which must match exactly.
    put("pricing.sens.step", SENS_STEP, ".0%", "wiki.facts.pricing_facts.SENS_STEP", MODULE_POP)
    base_share = s["n_clears"] / s["n"]
    for field in SENS_FIELDS:
        for name, factor in (("down", 1 - SENS_STEP), ("up", 1 + SENS_STEP)):
            m2 = m.replace(**{field: getattr(m, field) * factor})
            priced = price_with_pd(inp, 1.0, m2)
            if (field, name) == SENS_CHECK:
                assert priced[cols].equals(price_population(market=m2)[cols]), \
                    f"price_with_pd no longer reproduces price_population(market=...) ({field} {name})"
            s2 = portfolio_summary(priced)
            share = s2["n_clears"] / s2["n"]
            src = (f"price_loan over the booked rows (wiki.facts.pricing_facts.price_with_pd, "
                   f"checked equal to {SRC_PP}(market=...) on {SENS_CHECK[0]} {SENS_CHECK[1]}) "
                   f"with MARKET's {field} x {factor:.2f}")
            pop = BOOKED + f" -- {field} x {factor:.2f}"
            key = f"pricing.sens.{field}.{name}"
            put(f"{key}.value", float(getattr(m2, field)), SENS_FMT[field], src, ASSUMPTION)
            put(f"{key}.share_clears", share, ".1%", src, pop)
            put(f"{key}.n_clears", s2["n_clears"], ",d", src, pop)
            put(f"{key}.median_roe", s2["median_roe"], ".1%", src, pop)
            put(f"{key}.mispriced_ead", s2["mispriced_ead"], ",.0f", src, pop)
            # the swing is built from the shares as printed (to 0.1%), so the page's
            # "share - base = swing" holds by construction, not by luck of rounding
            put(f"{key}.swing", _printed_share(share) - _printed_share(base_share), "+.1%",
                src + " (printed shares: each rounded to 0.1% before subtracting)", pop)
    swing = {fd: abs(f[f"pricing.sens.{fd}.up.n_clears"].value
                     - f[f"pricing.sens.{fd}.down.n_clears"].value) for fd in SENS_FIELDS}
    top = sorted(SENS_FIELDS, key=lambda fd: (-swing[fd], fd))[0]
    put("pricing.sens.dominant", top, "",
        "wiki.facts.pricing_facts (largest |n_clears(+10%) - n_clears(-10%)|)", BOOKED)
    return f
