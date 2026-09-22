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
