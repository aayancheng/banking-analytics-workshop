"""The score split, exactly as score/src/train.py draws it (same seed, same stratification),
so every held-out number here is held out for the committed model too."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from shared.config import RAW, SEED


@dataclass(frozen=True)
class ScoreSplit:
    biz: pd.DataFrame
    y: np.ndarray
    idx_tr: np.ndarray
    idx_te: np.ndarray


@lru_cache(maxsize=1)
def score_split() -> ScoreSplit:
    biz = pd.read_parquet(RAW / "businesses.parquet")
    y = biz["default"].to_numpy()
    idx_tr, idx_te = train_test_split(np.arange(len(biz)), test_size=0.2,
                                      random_state=SEED, stratify=y)
    return ScoreSplit(biz, y, idx_tr, idx_te)
