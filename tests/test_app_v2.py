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
