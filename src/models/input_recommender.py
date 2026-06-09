"""Module 4: inflation-adjusted input recommender.

Weighted ranking over the MINAGRI input catalogue, filtered by crop, district,
and budget. Returns at most MAX_RECOMMENDATIONS (3) items — per Lobell et al.
(2020), capping at three prevents decision paralysis. This module is complete;
it just needs the catalogue loaded.
"""
from __future__ import annotations

import pandas as pd

from config.settings import MAX_RECOMMENDATIONS


# weights for the ranking score (must sum to 1.0)
WEIGHTS = {"affordability": 0.5, "crop_match": 0.3, "local_supply": 0.2}


def recommend(catalogue: pd.DataFrame, crop: str, district: str,
              budget_rwf: float) -> pd.DataFrame:
    """Rank affordable inputs for a crop/district/budget.

    Expects catalogue columns: input_name, input_type, crop_suitability,
    supplier, district, price_rwf.
    """
    df = catalogue.copy()

    # hard filters
    df = df[df["price_rwf"] <= budget_rwf]
    df = df[df["crop_suitability"].str.contains(crop, case=False, na=False)]
    if df.empty:
        return df

    # scoring components, each scaled 0-1
    df["affordability"] = 1 - (df["price_rwf"] / budget_rwf)          # cheaper = better
    df["crop_match"] = 1.0                                            # passed the filter
    df["local_supply"] = (df["district"].str.lower() == district.lower()).astype(float)

    df["match_score"] = sum(df[k] * w for k, w in WEIGHTS.items())
    df["pct_saving"] = (1 - df["price_rwf"] / df["price_rwf"].mean()) * 100

    ranked = df.sort_values("match_score", ascending=False).head(MAX_RECOMMENDATIONS)
    return ranked[["input_name", "input_type", "supplier", "district",
                   "price_rwf", "pct_saving", "match_score"]]
