"""v2 display honesty -- no number printed beside a threshold may disagree with it.

The clause tables got server-chosen precision in fix round 1; the final review found
the same class everywhere else a number sits next to its threshold: pricing's ROE vs
hurdle and its clamped "Shortfall 0 bps", the line-increase caption, the PD ruler and
tier-bar pins, the nearest-flip line, the utilization sparkline, and the caps panel.
These tests format exactly as the browser does (`toFixed(dp)`; a fraction as a
percent at max(2, dp-2) decimals) and demand distinct strings, over the whole book.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.filterwarnings(
    "ignore:LightGBM binary classifier.*list of ndarray:UserWarning")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def fixed(v, dp):                     # Number.prototype.toFixed
    return f"{v:.{dp}f}"


def pct_at(v, dp):                    # util.js fmt.pctAt
    return f"{v * 100:.{max(2, dp - 2)}f}"


def pair(v, t, dp):                   # util.js fmt.pair
    if float(v).is_integer() and float(t).is_integer():
        return str(int(v)), str(int(t))
    return fixed(v, dp), fixed(t, dp)


def test_pricing_margin_is_signed_agrees_with_the_verdict_and_never_prints_zero(client):
    from app.v2 import pricing
    st = client.app.state
    n_pos = 0
    for bid in st.priced.index:
        out = pricing.price_one(st, bid, pricing._MARKET)
        v, r = out["verdict"], out["rates"]
        m = v["rate_margin_bps"]
        assert m == pytest.approx((r["quoted"] - r["hurdle_clearing"]) * 1e4, abs=1e-9)
        if m > 0:
            assert v["clears_hurdle"], bid
            n_pos += 1
        if m < 0:
            assert not v["clears_hurdle"], bid
        if m != 0 and not v["margin_tied"]:
            assert float(fixed(abs(m), v["margin_dp"])) != 0, (bid, m)
        if v["roe"] != v["roe_hurdle"] and not v["roe_tied"]:
            assert pct_at(v["roe"], v["roe_dp"]) != pct_at(v["roe_hurdle"], v["roe_dp"]), bid
        if r["quoted"] != r["hurdle_clearing"]:
            assert pct_at(r["quoted"], r["dp"]) != pct_at(r["hurdle_clearing"], r["dp"]), bid
    assert n_pos == int(st.priced["clears_hurdle"].sum())   # 2,534 clearing loans


def test_biz103012_reads_short_by_a_non_zero_margin(client):
    w = client.post("/api/v2/loan/BIZ103012/pricing/whatif", json={}).json()
    v = w["verdict"]
    assert not v["clears_hurdle"]
    assert v["rate_margin_bps"] < 0
    assert fixed(abs(v["rate_margin_bps"]), v["margin_dp"]) == "0.04"
    assert pct_at(v["roe"], v["roe_dp"]) != pct_at(v["roe_hurdle"], v["roe_dp"])
    li = client.get("/api/v2/loan/BIZ103012/line-increase").json()["incremental"]
    assert pct_at(li["roe"], li["dp"]) != pct_at(li["roe_hurdle"], li["dp"])


def test_line_increase_roe_and_hurdle_print_distinct_from_the_verdicts_market(client):
    from app.v2 import line_increase as li_mod
    from line_increase.src import amount_rules
    st = client.app.state
    for bid in st.li.index:
        d = li_mod.line_increase_detail(st, bid)
        inc = d["incremental"]
        assert inc["roe_hurdle"] == amount_rules._MARKET.roe_hurdle
        clause = next(c for c in d["eligibility"]["clauses"] if c["name"] == "clears_hurdle")
        assert clause["threshold"] == amount_rules._MARKET.roe_hurdle
        if inc["roe"] != inc["roe_hurdle"] and not inc["tied"]:
            assert pct_at(inc["roe"], inc["dp"]) != pct_at(inc["roe_hurdle"], inc["dp"]), bid


def test_amount_steps_lead_to_the_batch_amount_on_every_account(client):
    from app.v2 import line_increase as li_mod
    from line_increase.src.amount_rules import recommended_amount
    st = client.app.state
    negative = zero = rounds_to_zero = above_cap = 0
    for bid in st.li.index:
        d = li_mod.line_increase_detail(st, bid)
        steps, row = d["amount_steps"], st.li.loc[bid]
        assert d["recommended_amount"] == recommended_amount(
            float(row["current_balance"]), float(row["credit_limit"]),
            float(st.profiles.loc[bid, "annual_revenue"])), bid
        if not d["caps"]:
            assert steps is None and d["recommended_amount"] == 0, bid
            continue
        binding = next(c for c in d["caps"] if c["binding"])
        assert steps["min_cap"] == binding["amount"] and steps["binding"] == binding["name"]
        assert steps["recommended"] == d["recommended_amount"], bid
        assert steps["no_headroom"] == (steps["min_cap"] <= 0), bid
        if steps["no_headroom"]:
            negative += steps["min_cap"] < 0
            zero += steps["min_cap"] == 0
            assert steps["recommended"] == 0 == steps["floored_at_zero"], bid
        else:
            assert steps["floored_at_zero"] == steps["min_cap"] > 0, bid
            assert abs(steps["recommended"] - steps["floored_at_zero"]) <= \
                steps["round_to"] / 2, bid
            above_cap += steps["recommended"] > steps["min_cap"]
            rounds_to_zero += steps["recommended"] == 0
    # The review's measured counts: 7,069 negative binding caps (plus BIZ103373's
    # exact $0), 579 rounded ABOVE their cap, 23 positive caps under $500 -> $0.
    assert (negative, zero, above_cap, rounds_to_zero) == (7069, 1, 579, 23)
    s = client.get("/api/v2/loan/BIZ100084/line-increase").json()["amount_steps"]
    assert round(s["min_cap"]) == 14554 and s["recommended"] == 15000


def test_ews_pin_prints_distinct_from_both_cutoffs(client):
    from app.v2.ews import prob_display
    st = client.app.state
    tiers = st.ews_meta["tiers"]
    for bid in st.ews.index:
        p = prob_display(st, bid, tiers)
        for t in (tiers["t_med"], tiers["t_high"]):
            if p["prob_raw"] != t and not p["prob_tied"]:
                assert fixed(p["prob_raw"], p["prob_dp"]) != fixed(t, p["prob_dp"]), bid
    e = client.get("/api/v2/loan/BIZ108170/ews").json()
    assert e["risk_tier"] == "Medium"
    assert fixed(e["prob_raw"], e["prob_dp"]) != fixed(e["tiers"]["t_high"], e["prob_dp"])


def test_decision_numbers_print_distinct_from_their_thresholds(client):
    """PD ruler pin vs both cutoffs, every rules-ledger row, and the nearest-flip
    line (whose PD levers carry the unrounded PD) -- all 12,000 applicants."""
    from app.v2 import explain, rules
    st = client.app.state
    cfg = st.policy_config
    for bid in st.profiles.index:
        pd_model = float(st.decisions.loc[bid, "pd"])
        z = explain.pd_zones(pd_model, cfg)
        for t in (z["t_low"], z["t_high"]):
            if z["pd"] != t and not z["tied"]:
                assert fixed(z["pd"], z["dp"]) != fixed(t, z["dp"]), bid
        p, sc = st.profiles.loc[bid], st.scores.loc[bid]
        raw = rules.loan_values(p, sc)
        led = rules.ledger(p, sc, cfg, z["zone"])
        for r in led["knockouts"] + led["refer_overrides"]:
            # against the RAW value: the payload's value is already rounded at dp,
            # so comparing it would skip exactly the rows a too-coarse dp collapses
            if raw[r["value_key"]] != r["threshold"] and not r["tied"]:
                a, b = pair(r["value"], r["threshold"], r["dp"])
                assert a != b, (bid, r)
        nf = rules.nearest_flip(led, pd_model, cfg)
        if nf["value"] != nf["threshold"] and not nf["tied"]:
            assert pair(nf["value"], nf["threshold"], nf["dp"])[0] != \
                pair(nf["value"], nf["threshold"], nf["dp"])[1], (bid, nf)


def test_nearest_flip_follows_a_dragged_cutoff(client):
    w = client.post("/api/v2/loan/BIZ100002/decision/whatif",
                    json={"t_low": 0.2}).json()
    lows = [c for c in w["nearest_flip"]["candidates"] if c["lever"] == "t_low"]
    assert lows[0]["threshold"] == 0.2 and w["pd_zones"]["t_low"] == 0.2


def test_utilization_marker_is_the_quantity_the_trigger_tests(client):
    """The sparkline's marker is the clause value, checked against the clause
    threshold; both must be what flag_triggers compared, and its verdict must agree
    with that comparison on every account -- committed config and a dragged one."""
    from app.v2.ews import trigger_rows
    from shared.config import EWS_TRIGGERS
    st = client.app.state
    feats = st.v2.ews_feats
    for bid in st.ews.index:
        hu = trigger_rows(feats.loc[bid], EWS_TRIGGERS,
                          set(st.ews.loc[bid, "triggers"]))[0]
        c = hu["clauses"][0]
        assert hu["name"] == "HIGH_UTILIZATION" and c["metric"] == "util_recent"
        assert c["value"] == float(feats.loc[bid, "util_recent"])
        assert hu["fired"] == c["met"] == (c["value"] > c["threshold"]), bid
    for bid in st.ews.index[::500]:
        w = client.post(f"/api/v2/loan/{bid}/ews/whatif",
                        json={"high_utilization": 0.5}).json()
        c = w["triggers"][0]["clauses"][0]
        assert c["threshold"] == 0.5
        assert w["triggers"][0]["fired"] == (c["value"] > c["threshold"]), bid


def test_loan_list_limit_is_validated(client):
    assert client.get("/api/v2/loans", params={"limit": -5}).status_code == 422
    assert client.get("/api/v2/loans", params={"limit": 0}).status_code == 422
    assert client.get("/api/v2/loans", params={"limit": 501}).status_code == 422
    assert client.get("/api/v2/loans", params={"limit": 500}).json()["shown"] == 500
