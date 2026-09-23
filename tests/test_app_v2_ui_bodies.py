"""v2 what-if -- the bodies the UI actually SENDS, not only the empty one.

Every task's invariant test pinned the empty override body `{}`. But after the first
interaction the browser always sends explicit values: the decision ruler posts
{t_low, t_high}; the pricing sliders post quoted_rate plus every market key; the EWS
tab posts both tier cutoffs AND all five trigger thresholds on every drag, whichever
widget moved. That path went untested, and the final review's Critical lived exactly
there: sending the committed EWS cutoffs explicitly re-tiered the book from the 4dp
rounded probability, moving BIZ108170 Medium -> High and BIZ103657 Low -> Medium and
the book 5835/1668/833 -> 5834/1668/834 while the user had only touched a trigger.

These tests post the committed values EXPLICITLY and demand the batch answer back.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from shared.config import EWS_TRIGGERS

pytestmark = pytest.mark.filterwarnings(
    "ignore:LightGBM binary classifier.*list of ndarray:UserWarning")

TRIGGER_KEYS = ["high_utilization", "rising_utilization", "dpd_severe",
                "deposit_decline", "overdraft_recent"]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _ews_bodies(st):
    """The three shapes tab-ews.js sends: the tier bar's cutoffs, the combined body
    (cutoffs + all five trigger thresholds at committed values), and that combined
    body after the user moved an UNRELATED trigger slider -- which must re-flag, and
    must not re-tier anything."""
    cut = {k: st.ews_meta["tiers"][k] for k in ("t_med", "t_high")}
    full = {**cut, **{k: EWS_TRIGGERS[k] for k in TRIGGER_KEYS}}
    return [cut, full, {**full, "overdraft_recent": 7}]


def test_ews_explicit_committed_body_reproduces_every_batch_tier(client):
    """Whole book, all 8,336 accounts, through the same re-tier the endpoint uses."""
    from app.v2.ews_whatif import EwsOverrides, retier_book
    st = client.app.state
    batch = list(st.ews["risk_tier"])
    for body in _ews_bodies(st):
        got = retier_book(st, EwsOverrides(**body))
        assert len(got) == len(batch) == 8336
        bad = [b for b, g, t in zip(st.ews.index, got, batch) if g != t]
        assert not bad, (body, bad)


def test_ews_explicit_committed_body_through_the_endpoint(client):
    """The two accounts that sit on a cutoff once prob is rounded to 4dp, plus the
    book tiles the tab paints on every drag."""
    st = client.app.state
    summary = client.get("/api/ews/summary").json()["tiers"]
    for body in _ews_bodies(st):
        for bid in ("BIZ108170", "BIZ103657", "BIZ100002"):
            live = client.post(f"/api/v2/loan/{bid}/ews/whatif", json=body).json()
            assert live["risk_tier"] == st.ews.loc[bid, "risk_tier"], (body, bid)
            assert live["book_tiers"] == summary, body


def test_ews_explicit_committed_triggers_reproduce_the_batch_flags(client):
    st = client.app.state
    full = _ews_bodies(st)[1]
    for bid in st.ews.index[::400]:
        live = client.post(f"/api/v2/loan/{bid}/ews/whatif", json=full).json()
        assert sorted(t["name"] for t in live["triggers"] if t["fired"]) == \
               sorted(st.ews.loc[bid, "triggers"]), bid


def test_decision_explicit_committed_body_flips_nothing(client):
    """`flipped_count` compares all 12,000 re-decided loans against the batch, so a
    zero here is a whole-book assertion in one request."""
    st = client.app.state
    cfg = st.policy_config.to_dict()
    batch_mix = st.decisions["decision"].value_counts().to_dict()
    for body in ({"t_low": cfg["t_low"], "t_high": cfg["t_high"]}, cfg):
        for bid in ("BIZ100002", "BIZ100052", "BIZ101719"):
            live = client.post(f"/api/v2/loan/{bid}/decision/whatif", json=body).json()
            assert live["flipped_count"] == 0, body
            assert live["book_mix"] == batch_mix, body
            batch = client.get(f"/api/adjudicate/{bid}").json()
            assert live["decision"] == batch["decision"], (body, bid)
            assert sorted(live["rule_hits"]) == sorted(batch["rule_hits"]), (body, bid)


def test_pricing_explicit_committed_body_equals_the_empty_body(client):
    """What the sliders send: quoted_rate plus every market key, all at their seeded
    values. The whole payload must equal the empty-body one, not just two fields."""
    st = client.app.state
    for bid in list(st.priced.index[::500]) + ["BIZ103012"]:
        seed = client.post(f"/api/v2/loan/{bid}/pricing/whatif", json={}).json()
        body = {"quoted_rate": seed["rates"]["quoted"], **seed["market"]}
        live = client.post(f"/api/v2/loan/{bid}/pricing/whatif", json=body).json()
        assert live == seed, bid


def test_pricing_explicit_committed_market_reproduces_the_whole_batch_book(client):
    from app.v2 import pricing
    from app.v2.whatif import PricingOverrides
    st = client.app.state
    body = client.post("/api/v2/loan/BIZ100002/pricing/whatif", json={}).json()["market"]
    market = PricingOverrides(**body).market()
    priced = st.priced
    for bid in priced.index:
        q = float(st.profiles.loc[bid, "risk_based_rate"])
        v = pricing.price_one(st, bid, market, q)["verdict"]
        assert v["roe"] == pytest.approx(priced.loc[bid, "roe_at_quoted"], abs=1e-9), bid
        assert v["clears_hurdle"] == bool(priced.loc[bid, "clears_hurdle"]), bid
    book = client.post("/api/v2/loan/BIZ100002/pricing/whatif", json=body).json()["book"]
    summary = client.get("/api/pricing/summary").json()
    assert book["n_clears"] == summary["n_clears"]
