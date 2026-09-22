"""The selectable loan universe: one row per applicant with every filter facet on it.

Built once from the frames v1 already computed, so a filter can never disagree with
the module that produced the column. On-book facets (ews_tier, mispriced,
li_eligible) are None for the 3,664 applicants that were never booked — that null is
correct and the UI says so rather than hiding them.
"""
from __future__ import annotations

import pandas as pd

FACETS = ["decision", "score_band", "industry", "region",
          "booked", "ews_tier", "mispriced", "li_eligible"]

LIST_COLUMNS = ["business_id", "decision", "score_band", "industry",
                "region", "requested_amount", "booked"]


def build_index(app_state) -> pd.DataFrame:
    p, s, d = app_state.profiles, app_state.scores, app_state.decisions
    idx = pd.DataFrame({
        "industry": p["industry"].astype(str),
        "region": p["region"].astype(str),
        "entity_type": p["entity_type"].astype(str),
        "requested_amount": p["requested_amount"].astype(float),
        "booked": p["booked"].astype(bool),
        "score_band": s["score_band"].astype(str),
        "business_score": s["business_score"].astype(int),
        "pd": s["pd"].astype(float),
        "decision": d["decision"].astype(str),
    }, index=p.index)
    idx["mispriced"] = app_state.priced["mispriced"].astype(bool).reindex(idx.index)
    idx["ews_tier"] = app_state.ews["risk_tier"].astype(str).reindex(idx.index)
    idx["li_eligible"] = app_state.li["eligible"].astype(bool).reindex(idx.index)
    idx.index.name = "business_id"
    return idx


def facets(index: pd.DataFrame) -> dict:
    """Distinct values and counts per facet. NaN (not booked) is dropped, so an
    on-book facet's counts sum to 8,336 and an application facet's to 12,000."""
    out = {}
    for f in FACETS:
        counts = index[f].dropna().value_counts()
        out[f] = [{"value": _jsonable(k), "count": int(v)}
                  for k, v in counts.sort_index().items()]
    return out


def _jsonable(v):
    return bool(v) if isinstance(v, bool) else str(v)


def _as_bool(v: str | None):
    if v is None:
        return None
    return str(v).lower() in ("true", "1", "yes")


def search(index: pd.DataFrame, *, decision=None, score_band=None, industry=None,
           region=None, booked=None, ews_tier=None, mispriced=None,
           li_eligible=None, q=None, limit: int = 200) -> dict:
    m = pd.Series(True, index=index.index)
    for col, val in (("decision", decision), ("score_band", score_band),
                     ("industry", industry), ("region", region),
                     ("ews_tier", ews_tier)):
        if val:
            m &= index[col] == val
    for col, val in (("booked", booked), ("mispriced", mispriced),
                     ("li_eligible", li_eligible)):
        b = _as_bool(val)
        if b is not None:
            m &= index[col].fillna(False).astype(bool) == b
    if q:
        m &= index.index.str.contains(str(q).strip(), case=False, regex=False)

    hits = index[m].sort_index()
    shown = hits.head(limit).reset_index()
    return {
        "total": int(len(hits)),
        "shown": int(len(shown)),
        "limit": limit,
        "loans": shown[LIST_COLUMNS].to_dict(orient="records"),
    }
