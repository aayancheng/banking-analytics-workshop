"""v2 loan workbench — API tests.

TestClient boots the whole platform (~7.4s), so the client is module-scoped and
every test shares it.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_v1_still_works(client):
    """v2 is additive. If this breaks, v2 has damaged the side-by-side demo."""
    assert client.get("/health").json()["applicants"] == 12000
    assert client.get("/api/dashboard/summary").status_code == 200


def test_v2_health(client):
    r = client.get("/api/v2/health")
    assert r.status_code == 200
    body = r.json()
    assert body["applicants"] == 12000
    assert body["booked"] == 8336
    assert body["panel_accounts"] == 8336
    assert body["panel_months"] == 24


def test_facets_cover_every_filter(client):
    f = client.get("/api/v2/filters").json()
    assert set(f) == {"decision", "score_band", "industry", "region",
                      "booked", "ews_tier", "mispriced", "li_eligible"}
    assert {o["value"] for o in f["decision"]} == {"Approve", "Refer", "Decline"}
    assert {o["value"] for o in f["score_band"]} == {"AAA", "A", "B", "C", "D"}
    assert sum(o["count"] for o in f["decision"]) == 12000
    # On-book facets are scoped to the booked population, not the applicant one.
    for on_book in ("mispriced", "ews_tier", "li_eligible"):
        assert sum(o["count"] for o in f[on_book]) == 8336, on_book


def test_search_unfiltered_reports_true_total_and_caps_the_list(client):
    r = client.get("/api/v2/loans").json()
    assert r["total"] == 12000
    assert r["shown"] == 200
    assert len(r["loans"]) == 200


def test_filters_compose(client):
    """The demo path: mispriced D-band loans on the High watchlist."""
    r = client.get("/api/v2/loans", params={
        "score_band": "D", "mispriced": "true", "ews_tier": "High"}).json()
    assert 0 < r["total"] < 12000
    assert all(x["score_band"] == "D" for x in r["loans"])


def test_search_counts_match_pandas(client):
    """The endpoint must not invent its own filtering semantics."""
    import pandas as pd
    from shared.config import RAW
    biz = pd.read_parquet(RAW / "businesses.parquet")
    expected = int((biz["industry"] == "Retail").sum())
    assert client.get("/api/v2/loans", params={"industry": "Retail"}).json()["total"] == expected


def test_free_text_id_search(client):
    r = client.get("/api/v2/loans", params={"q": "BIZ100002"}).json()
    assert r["total"] == 1
    assert r["loans"][0]["business_id"] == "BIZ100002"


def test_on_book_filters_return_the_count_their_facet_advertises(client):
    """The bug this guards: coercing the unbooked null to False made
    mispriced=false return 6,198 while its own facet said 2,534."""
    f = client.get("/api/v2/filters").json()
    for facet, values in (("mispriced", (True, False)), ("li_eligible", (True, False))):
        advertised = {str(o["value"]).lower(): o["count"] for o in f[facet]}
        for v in values:
            got = client.get("/api/v2/loans",
                             params={facet: str(v).lower()}).json()["total"]
            assert got == advertised[str(v).lower()], f"{facet}={v}"
        assert sum(advertised.values()) == 8336, facet


def test_header_of_a_booked_loan(client):
    h = client.get("/api/v2/loan/BIZ100002").json()
    assert h["business_id"] == "BIZ100002"
    assert h["identity"]["industry"] == "Transport"
    assert h["terms"]["requested_amount"] == 209000.0
    assert h["booked"] is True
    assert h["decision"] in ("Approve", "Refer", "Decline")
    assert 300 <= h["score"]["business_score"] <= 850
    assert set(h["modules_present"]) == {"score", "adjudication", "pricing",
                                         "ews", "line_increase"}


def test_header_of_an_unbooked_applicant(client):
    """Not booked is not an error. Only the two application-time modules apply."""
    unbooked = client.get("/api/v2/loans", params={"booked": "false"}).json()["loans"][0]
    h = client.get(f"/api/v2/loan/{unbooked['business_id']}").json()
    assert h["booked"] is False
    assert set(h["modules_present"]) == {"score", "adjudication"}


def test_unknown_id_is_404_not_500(client):
    assert client.get("/api/v2/loan/NOPE").status_code == 404


def test_internal_keyerror_does_not_become_a_404(client, monkeypatch):
    """_guard must catch only explain.UnknownLoan. A bare KeyError raised inside a
    detail function -- a renamed column, a typo in a metadata path -- is a bug, and
    reporting it as "unknown business_id" would hide it as a 404 for a loan the demo
    audience can see sitting in the dropdown."""
    from app.v2 import explain

    def boom(app_state, business_id, *rest):
        raise KeyError("industry")

    monkeypatch.setattr(explain, "header", boom)
    with pytest.raises(KeyError):
        client.get("/api/v2/loan/BIZ100002")


def test_decision_detail_rules_ledger(client):
    d = client.get("/api/v2/loan/BIZ100002/decision").json()
    names = {r["rule"] for r in d["rules"]["knockouts"]}
    assert names == {"dscr_floor", "public_records_cap",
                     "prior_delinq_cap", "leverage_cap"}
    dscr = next(r for r in d["rules"]["knockouts"] if r["rule"] == "dscr_floor")
    assert dscr["threshold"] == 1.0
    assert dscr["value"] == pytest.approx(1.78)
    assert dscr["fired"] is False


def test_pd_zones_match_the_committed_policy(client):
    d = client.get("/api/v2/loan/BIZ100002/decision").json()
    assert d["pd_zones"]["t_low"] == 0.0955
    assert d["pd_zones"]["t_high"] == 0.4943
    assert d["pd_zones"]["zone"] in ("Approve", "Refer", "Decline")


@pytest.fixture(scope="module")
def sample_ids(client):
    """A numeric identity asserted on ONE hardcoded loan passes by luck. BIZ100002's
    SHAP gap happens to be exactly 0.0 and its PD sits nowhere near the tails, which
    is why a single-loan version of these tests stayed green while 62 of 120 loans
    breached the tolerance. Always sample."""
    return [l["business_id"] for l in
            client.get("/api/v2/loans", params={"limit": 40}).json()["loans"]]


def test_score_ledger_is_exactly_additive(client, sample_ids):
    """intercept + sum(WoE x beta) == logit(pd). This identity is the whole reason a
    scorecard is explainable, and the screen claims it -- so assert it, on many loans."""
    import math
    for bid in sample_ids:
        led = client.get(f"/api/v2/loan/{bid}/decision").json()["score_ledger"]
        total = led["intercept"] + sum(c["contribution"] for c in led["contributions"])
        assert len(led["contributions"]) == 15, bid
        assert total == pytest.approx(led["logit_pd"], abs=1e-9), bid
        assert led["logit_pd"] == pytest.approx(
            math.log(led["pd"] / (1 - led["pd"])), abs=1e-6), bid


def test_shap_is_exactly_additive(client, sample_ids):
    for bid in sample_ids:
        sh = client.get(f"/api/v2/loan/{bid}/decision").json()["shap"]
        total = sh["base_value"] + sum(c["contribution"] for c in sh["contributions"])
        assert len(sh["contributions"]) == 21, bid
        assert total == pytest.approx(sh["logit_pd_model"], abs=1e-6), bid


def test_ledger_identities_hold_at_the_pd_extremes(client):
    """The tails are where rounding a PD before recomputing its logit does the most
    damage -- 5.85e-4 on the lowest-PD applicant, 585x the tolerance.

    The IDs are hardcoded because they ARE the measured extremes: BIZ101650 has the
    population's minimum modelled PD (0.000419) and BIZ111827 its maximum (0.991464).
    Do not swap these for the first and last rows of /api/v2/loans -- that endpoint
    sorts by business_id and does not even return pd, so it would silently test two
    ordinary mid-book loans while claiming to test the tails.
    """
    import math
    for bid in ("BIZ101650", "BIZ111827"):
        led = client.get(f"/api/v2/loan/{bid}/decision").json()["score_ledger"]
        assert led["logit_pd"] == pytest.approx(
            math.log(led["pd"] / (1 - led["pd"])), abs=1e-6), bid


def test_nearest_flip_can_rank_a_zero_threshold_rule(client):
    """public_records_cap is committed at 0 and 11,041 of 12,000 applicants sit exactly
    on it. An earlier version skipped every zero threshold, so the tightest margin a
    rule can have was invisible on 92% of the book."""
    nf = client.get("/api/v2/loan/BIZ100002/decision").json()["nearest_flip"]
    levers = {c["lever"] for c in nf["candidates"]}
    assert "public_records_cap" in levers
    pr = next(c for c in nf["candidates"] if c["lever"] == "public_records_cap")
    assert pr["at_threshold"] is True          # value 0, cap 0
    assert pr["distance_to_cross"] == 1.0      # one whole record, not zero
    gaps = [c["gap"] for c in nf["candidates"]]
    assert gaps == sorted(gaps)                 # candidates come back ranked
    assert nf["lever"] == nf["candidates"][0]["lever"]


def test_decision_endpoint_matches_the_batch_pipeline(client, sample_ids):
    """v2's DECISION endpoint -- not just the header -- must agree with what v1
    already decided, and must report the same reasons."""
    for bid in sample_ids:
        v1 = client.get(f"/api/adjudicate/{bid}").json()
        v2 = client.get(f"/api/v2/loan/{bid}/decision").json()
        assert v1["decision"] == v2["decision"], bid
        assert sorted(v1["rule_hits"]) == sorted(v2["rule_hits"]), bid


def test_decision_whatif_with_no_overrides_reproduces_the_batch_pipeline(client):
    """THE invariant test. If this ever fails, the demo is lying: the what-if and the
    production pipeline have drifted apart."""
    ids = [l["business_id"] for l in
           client.get("/api/v2/loans", params={"limit": 25}).json()["loans"]]
    for bid in ids:
        batch = client.get(f"/api/adjudicate/{bid}").json()
        live = client.post(f"/api/v2/loan/{bid}/decision/whatif", json={}).json()
        assert live["decision"] == batch["decision"], bid
        assert sorted(live["rule_hits"]) == sorted(batch["rule_hits"]), bid


def test_decision_whatif_book_mix_sums_to_the_population(client):
    r = client.post("/api/v2/loan/BIZ100002/decision/whatif", json={}).json()
    assert sum(r["book_mix"].values()) == 12000


def test_dragging_t_low_to_zero_removes_every_approval(client):
    r = client.post("/api/v2/loan/BIZ100002/decision/whatif",
                    json={"t_low": 0.0}).json()
    assert r["book_mix"].get("Approve", 0) == 0
    assert r["flipped_count"] > 0


def test_whatif_rejects_out_of_range_overrides(client):
    """A slider that silently clamps produces a number that looks real and is not."""
    assert client.post("/api/v2/loan/BIZ100002/decision/whatif",
                       json={"t_low": 1.5}).status_code == 422
    assert client.post("/api/v2/loan/BIZ100002/decision/whatif",
                       json={"dscr_floor": -1}).status_code == 422


def test_whatif_rejects_an_inverted_pd_band(client):
    """Per-field bounds are not enough. t_low=0.9 is in range on its own, but merged
    with the committed t_high of 0.4943 it inverts the band: decide() tests
    `pd <= t_low` first, so the Refer zone vanishes and 643 loans change decision
    while the response still looks like an ordinary book."""
    r = client.post("/api/v2/loan/BIZ100002/decision/whatif", json={"t_low": 0.9})
    assert r.status_code == 422, r.json()
    assert "t_high" in r.json()["detail"]
    # Explicitly-paired values that are coherent must still be accepted.
    ok = client.post("/api/v2/loan/BIZ100002/decision/whatif",
                     json={"t_low": 0.20, "t_high": 0.60})
    assert ok.status_code == 200
    assert sum(ok.json()["book_mix"].values()) == 12000


def test_whatif_rejects_an_inverted_dscr_band(client):
    r = client.post("/api/v2/loan/BIZ100002/decision/whatif", json={"dscr_floor": 5.0})
    assert r.status_code == 422, r.json()


WATERFALL_LINES = ["interest_income", "cost_of_funds", "expected_loss",
                   "operating_cost", "pre_tax_profit", "tax", "net_income",
                   "allocated_equity"]


@pytest.fixture(scope="module")
def booked_sample_ids(client):
    """sample_ids is drawn from the unfiltered (12,000-applicant) list and can include
    unbooked ids; pricing is only defined for the 8,336 booked, so this fixture filters
    to booked from the start rather than filtering sample_ids down per-test."""
    return [l["business_id"] for l in
            client.get("/api/v2/loans", params={"booked": "true", "limit": 40}).json()["loans"]]


def test_pricing_detail_has_every_waterfall_line_in_dollars_and_bps(client, booked_sample_ids):
    for bid in booked_sample_ids:
        p = client.get(f"/api/v2/loan/{bid}/pricing").json()
        assert [w["line"] for w in p["waterfall"]] == WATERFALL_LINES, bid
        ead = p["ead"]
        for w in p["waterfall"]:
            assert w["bps"] == pytest.approx(w["dollars"] / ead * 10_000, abs=1e-6), bid


def test_pricing_detail_matches_the_batch_priced_book(client, booked_sample_ids):
    for bid in booked_sample_ids:
        v1 = client.get(f"/api/pricing/{bid}").json()
        v2 = client.get(f"/api/v2/loan/{bid}/pricing").json()
        assert v2["verdict"]["roe"] == pytest.approx(v1["roe_at_quoted"], abs=1e-9), bid
        assert v2["rates"]["recommended"] == pytest.approx(v1["recommended_rate"], abs=1e-9), bid
        assert v2["verdict"]["clears_hurdle"] == v1["clears_hurdle"], bid


def test_rate_ladder_is_ordered(client, booked_sample_ids):
    for bid in booked_sample_ids:
        r = client.get(f"/api/v2/loan/{bid}/pricing").json()["rates"]
        assert r["break_even"] < r["hurdle_clearing"] < r["recommended"], bid


def test_pricing_is_null_for_an_unbooked_applicant(client):
    unbooked = client.get("/api/v2/loans", params={"booked": "false"}).json()["loans"][0]
    r = client.get(f"/api/v2/loan/{unbooked['business_id']}/pricing")
    assert r.status_code == 200
    assert r.json() is None


def test_pricing_whatif_with_no_overrides_reproduces_the_batch_pipeline(client, booked_sample_ids):
    """The invariant test for pricing. Loops over booked_sample_ids (40 booked loans)
    rather than a single hardcoded id -- Task 4 found defects that a single-loan
    identity assertion missed."""
    for bid in booked_sample_ids:
        batch = client.get(f"/api/pricing/{bid}").json()
        live = client.post(f"/api/v2/loan/{bid}/pricing/whatif", json={}).json()
        assert live["verdict"]["roe"] == pytest.approx(batch["roe_at_quoted"], abs=1e-9), bid
        assert live["verdict"]["clears_hurdle"] == batch["clears_hurdle"], bid


def test_pricing_whatif_book_matches_the_committed_summary(client):
    """All four fields, not just the two that are easiest to compare. n_clears and
    mispriced_ead currently match exactly, and nothing would catch a regression in
    either -- an off-by-one in _book_under's clears mask would move both and leave
    n and share_clears looking fine."""
    summary = client.get("/api/pricing/summary").json()
    live = client.post("/api/v2/loan/BIZ100002/pricing/whatif", json={}).json()["book"]
    assert live["n"] == summary["n"]
    assert live["n_clears"] == summary["n_clears"]
    assert live["share_clears"] == pytest.approx(summary["share_clears"], abs=1e-4)
    assert live["mispriced_ead"] == pytest.approx(summary["mispriced_ead"], rel=1e-9)


def test_raising_lgd_hurts_the_book(client):
    base = client.post("/api/v2/loan/BIZ100002/pricing/whatif", json={}).json()
    worse = client.post("/api/v2/loan/BIZ100002/pricing/whatif",
                        json={"lgd": 0.90}).json()
    assert worse["book"]["share_clears"] < base["book"]["share_clears"]
    assert worse["waterfall"][2]["line"] == "expected_loss"
    assert abs(worse["waterfall"][2]["dollars"]) > abs(base["waterfall"][2]["dollars"])


def test_raising_the_quoted_rate_lifts_roe(client):
    base = client.post("/api/v2/loan/BIZ100002/pricing/whatif", json={}).json()
    up = client.post("/api/v2/loan/BIZ100002/pricing/whatif",
                     json={"quoted_rate": 0.15}).json()
    assert up["verdict"]["roe"] > base["verdict"]["roe"]


def test_pricing_whatif_rejects_out_of_range(client):
    assert client.post("/api/v2/loan/BIZ100002/pricing/whatif",
                       json={"lgd": 1.5}).status_code == 422
    assert client.post("/api/v2/loan/BIZ100002/pricing/whatif",
                       json={"capital_ratio": 0.0}).status_code == 422


def test_pricing_whatif_rejects_tax_rate_at_the_unity_boundary(client):
    """tax_rate == 1.0 would zero net_income for every clearing loan; the Field bound
    is `lt=1.0`, so this must be a 422, not a 200 with a degenerate book."""
    assert client.post("/api/v2/loan/BIZ100002/pricing/whatif",
                       json={"tax_rate": 1.0}).status_code == 422


def test_pricing_whatif_is_none_for_an_unbooked_applicant(client):
    unbooked = client.get("/api/v2/loans", params={"booked": "false"}).json()["loans"][0]
    r = client.post(f"/api/v2/loan/{unbooked['business_id']}/pricing/whatif", json={})
    assert r.status_code == 200
    assert r.json() is None


def test_pricing_whatif_404s_for_an_unknown_business_id(client):
    r = client.post("/api/v2/loan/BIZ999999/pricing/whatif", json={})
    assert r.status_code == 404


TRIGGER_NAMES = ["HIGH_UTILIZATION", "RISING_UTILIZATION", "DELINQUENCY",
                 "DEPOSIT_DECLINE", "FREQUENT_OVERDRAFTS"]


def test_ews_detail_returns_the_full_24_month_panel(client):
    e = client.get("/api/v2/loan/BIZ100002/ews").json()
    assert e["panel"]["months"] == list(range(24))
    for name in ["utilization", "balance", "deposit_inflow",
                 "days_past_due", "overdraft_count"]:
        assert len(e["panel"]["series"][name]) == 24


def test_ews_triggers_show_thresholds_and_values_not_just_names(client):
    e = client.get("/api/v2/loan/BIZ100002/ews").json()
    assert [t["name"] for t in e["triggers"]] == TRIGGER_NAMES
    hu = next(t for t in e["triggers"] if t["name"] == "HIGH_UTILIZATION")
    assert hu["clauses"][0]["threshold"] == 0.90
    assert isinstance(hu["fired"], bool)
    delinq = next(t for t in e["triggers"] if t["name"] == "DELINQUENCY")
    assert [c["metric"] for c in delinq["clauses"]] == ["dpd_max", "dpd_recent"]


def test_every_fired_trigger_can_explain_itself(client):
    """`fired` is the module's verdict; `met` on each clause is the explanation the
    screen shows. If they ever disagree the screen contradicts itself.

    This is not hypothetical. Representing DELINQUENCY as its dpd_max clause alone
    made all 4,225 fired accounts -- 50.7% of the book -- render as
    "value 2, threshold 30, FIRED", because every one of them trips the
    `dpd_recent > 0` clause instead. A banker who sees that stops believing every
    other number on the screen.

    WHOLE BOOK, not a sample, and called directly rather than over HTTP. A
    self-consistency check is only worth having if it covers the rare states, and
    8,336 accounts x 5 triggers costs 0.5s this way."""
    from shared.config import EWS_TRIGGERS
    from app.v2 import ews as ews_mod
    st = client.app.state
    for bid in st.ews.index:
        rows = ews_mod.trigger_rows(st.v2.ews_feats.loc[bid], EWS_TRIGGERS,
                                    set(st.ews.loc[bid, "triggers"]))
        for t in rows:
            assert t["fired"] == any(c["met"] for c in t["clauses"]), (bid, t["name"])


def test_ews_fired_triggers_match_the_batch_watchlist(client, booked_sample_ids):
    """Looped over a sample of booked loans, not one hardcoded id -- three Task 4
    defects survived review that way."""
    for bid in booked_sample_ids:
        v1 = client.get(f"/api/ews/{bid}").json()
        v2 = client.get(f"/api/v2/loan/{bid}/ews").json()
        assert v2["prob"] == pytest.approx(v1["prob"], abs=1e-9), bid
        assert v2["risk_tier"] == v1["risk_tier"], bid
        assert (sorted(t["name"] for t in v2["triggers"] if t["fired"])
                == sorted(v1["triggers"])), bid


def test_ews_quotes_the_metadata_numbers_not_recomputed_ones(client):
    """Held-out capture, not the in-sample figure. AUC is reported, never gated."""
    c = client.get("/api/v2/loan/BIZ100002/ews").json()["model_caveat"]
    assert c["top_decile_capture"] == 0.2159
    assert c["auc"] == 0.6622
    assert c["auc_is_gated"] is False


def test_ews_is_null_for_an_unbooked_applicant(client):
    unbooked = client.get("/api/v2/loans", params={"booked": "false"}).json()["loans"][0]
    assert client.get(f"/api/v2/loan/{unbooked['business_id']}/ews").json() is None


def test_ews_404s_for_an_unknown_business_id(client):
    r = client.get("/api/v2/loan/BIZ999999/ews")
    assert r.status_code == 404


def test_ews_whatif_with_no_overrides_reproduces_the_batch_pipeline(client, booked_sample_ids):
    for bid in booked_sample_ids:
        batch = client.get(f"/api/ews/{bid}").json()
        live = client.post(f"/api/v2/loan/{bid}/ews/whatif", json={}).json()
        assert live["risk_tier"] == batch["risk_tier"], bid
        assert sorted(t["name"] for t in live["triggers"] if t["fired"]) == \
               sorted(batch["triggers"]), bid


def test_ews_whatif_book_tiers_match_the_batch_summary(client):
    summary = client.get("/api/ews/summary").json()
    live = client.post("/api/v2/loan/BIZ100002/ews/whatif", json={}).json()
    assert live["book_tiers"] == summary["tiers"]


def test_lowering_the_high_cutoff_grows_the_high_tier(client):
    base = client.post("/api/v2/loan/BIZ100002/ews/whatif", json={}).json()
    loose = client.post("/api/v2/loan/BIZ100002/ews/whatif",
                        json={"t_high": 0.25}).json()
    assert loose["book_tiers"]["High"] > base["book_tiers"]["High"]


def test_lowering_a_trigger_threshold_fires_it_for_more_accounts(client):
    loose = client.post("/api/v2/loan/BIZ100002/ews/whatif",
                        json={"high_utilization": 0.10}).json()
    hu = next(t for t in loose["triggers"] if t["name"] == "HIGH_UTILIZATION")
    assert hu["clauses"][0]["threshold"] == 0.10
    assert loose["book_trigger_counts"]["HIGH_UTILIZATION"] > 0


def test_ews_whatif_rejects_out_of_range(client):
    assert client.post("/api/v2/loan/BIZ100002/ews/whatif",
                       json={"t_high": 2.0}).status_code == 422


def test_ews_whatif_rejects_an_inverted_tier_band(client):
    """Per-field bounds are not enough. t_med=0.9 is in range on its own, but merged
    with the committed t_high of 0.5073 it inverts the band and empties the Medium
    tier -- the same trap DecisionOverrides guards against for t_low/t_high."""
    r = client.post("/api/v2/loan/BIZ100002/ews/whatif", json={"t_med": 0.9})
    assert r.status_code == 422, r.json()
    assert "t_high" in r.json()["detail"]
    # Explicitly-paired values that are coherent must still be accepted.
    ok = client.post("/api/v2/loan/BIZ100002/ews/whatif",
                     json={"t_med": 0.1, "t_high": 0.2})
    assert ok.status_code == 200
    assert sum(ok.json()["book_tiers"].values()) == 8336


def test_ews_whatif_is_null_for_an_unbooked_applicant(client):
    unbooked = client.get("/api/v2/loans", params={"booked": "false"}).json()["loans"][0]
    r = client.post(f"/api/v2/loan/{unbooked['business_id']}/ews/whatif", json={})
    assert r.status_code == 200
    assert r.json() is None


def test_ews_whatif_404s_for_an_unknown_business_id(client):
    r = client.post("/api/v2/loan/BIZ999999/ews/whatif", json={})
    assert r.status_code == 404


def test_line_increase_shows_which_cap_binds(client):
    li = client.get("/api/v2/loan/BIZ100002/line-increase").json()
    assert [c["name"] for c in li["caps"]] == [
        "headroom_to_target_util", "pct_cap", "revenue_ceiling"]
    binding = [c for c in li["caps"] if c["binding"]]
    assert len(binding) == 1


def test_eligibility_explains_itself_on_every_booked_account(client):
    """`eligible` is candidates()' verdict; the clauses explain it. They must agree.

    WHOLE BOOK, not a sample. The 40-loan `booked_sample_ids` fixture contains ZERO
    eligible accounts and only 2 with a positive recommended amount, so a sampled
    version of this test is structurally blind to the exact states it exists to
    check -- a comparator flip on one clause surfaces on 57 of 8,336 rows and the
    sample misses all of them. Called directly rather than over HTTP, all 8,336
    cost 0.6s."""
    from app.v2 import line_increase as li_mod
    st = client.app.state
    for bid in st.li.index:
        e = li_mod.line_increase_detail(st, bid)["eligibility"]
        assert e["eligible"] == all(c["pass"] for c in e["clauses"]), (bid, e)


def test_eligibility_is_four_clauses_not_one_number(client):
    """The documented trap: 95 accounts are eligible, 1,243 have a positive
    recommended amount. Showing the clauses is what makes the gap legible."""
    li = client.get("/api/v2/loan/BIZ100002/line-increase").json()
    names = [c["name"] for c in li["eligibility"]["clauses"]]
    assert names == ["prob_above_threshold", "pd_within_appetite",
                     "amount_positive", "clears_hurdle"]
    assert li["eligibility"]["eligible"] == all(
        c["pass"] for c in li["eligibility"]["clauses"])


def test_line_increase_matches_the_batch_pipeline(client, booked_sample_ids):
    """Tolerance 6e-5, not 1e-4: the batch rounds incremental_roe to 4dp, so half an
    ulp (5e-5) is the tightest honest bound and anything looser stops catching the
    real failure -- recomputing ROE from the PERSISTED 4dp pd instead of the unrounded
    scorecard pd, which differs by up to 1.4e-4.

    clears_hurdle is compared exactly, because that is where the difference bites: on
    one of the 1,243 loans with a positive amount the rounded pd flips it, and it is
    the fourth eligibility clause."""
    for bid in booked_sample_ids:
        v1 = client.get(f"/api/line-increase/{bid}").json()
        v2 = client.get(f"/api/v2/loan/{bid}/line-increase").json()
        assert v2["recommended_amount"] == pytest.approx(v1["recommended_amount"], abs=1e-6), bid
        assert v2["eligibility"]["eligible"] == v1["eligible"], bid
        assert v2["incremental"]["clears_hurdle"] == v1["clears_hurdle"], bid
        assert v2["incremental"]["roe"] == pytest.approx(v1["incremental_roe"], abs=6e-5), bid


def test_clears_hurdle_matches_the_batch_on_every_loan_with_an_amount(client):
    """Whole book. The flip this guards happens on exactly ONE of 1,243 loans, so a
    40-loan sample cannot see it -- the same blindness that let the eligibility
    comparator bug through."""
    from app.v2 import line_increase as li_mod
    st = client.app.state
    for bid in st.li.index:
        if float(st.li.loc[bid, "recommended_amount"]) <= 0:
            continue
        v2 = li_mod.line_increase_detail(st, bid)
        assert v2["incremental"]["clears_hurdle"] == bool(st.li.loc[bid, "clears_hurdle"]), bid


def test_eligible_count_is_95_not_the_positive_amount_count(client):
    """Guards the gotcha directly."""
    eligible = client.get("/api/v2/loans", params={"li_eligible": "true"}).json()
    assert eligible["total"] == 95


def test_line_increase_is_null_for_an_unbooked_applicant(client):
    unbooked = client.get("/api/v2/loans", params={"booked": "false"}).json()["loans"][0]
    assert client.get(
        f"/api/v2/loan/{unbooked['business_id']}/line-increase").json() is None


def test_line_increase_404s_for_an_unknown_business_id(client):
    r = client.get("/api/v2/loan/BIZ999999/line-increase")
    assert r.status_code == 404
