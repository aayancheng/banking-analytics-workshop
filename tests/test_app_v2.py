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


def test_score_ledger_is_exactly_additive(client):
    """intercept + sum(WoE x beta) == logit(pd). This identity is the whole reason a
    scorecard is explainable, and the screen claims it -- so assert it."""
    import math
    d = client.get("/api/v2/loan/BIZ100002/decision").json()
    led = d["score_ledger"]
    total = led["intercept"] + sum(c["contribution"] for c in led["contributions"])
    assert len(led["contributions"]) == 15
    assert total == pytest.approx(led["logit_pd"], abs=1e-9)
    assert led["logit_pd"] == pytest.approx(
        math.log(led["pd"] / (1 - led["pd"])), abs=1e-6)


def test_shap_is_exactly_additive(client):
    d = client.get("/api/v2/loan/BIZ100002/decision").json()
    sh = d["shap"]
    total = sh["base_value"] + sum(c["contribution"] for c in sh["contributions"])
    assert len(sh["contributions"]) == 21
    assert total == pytest.approx(sh["logit_pd_model"], abs=1e-6)


def test_decision_matches_the_batch_pipeline(client):
    """v2's decision detail must agree with what v1 already decided."""
    v1 = client.get("/api/adjudicate/BIZ100002").json()
    v2 = client.get("/api/v2/loan/BIZ100002").json()
    assert v1["decision"] == v2["decision"]
