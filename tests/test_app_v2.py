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
