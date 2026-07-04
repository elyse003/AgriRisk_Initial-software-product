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


# ---------------------------------------------------------------------------
# Land-size-aware fertilizer plan (addresses the "quantity without land size" gap)
# ---------------------------------------------------------------------------
import math

BAG_KG = 50  # standard fertilizer bag size in Rwanda

# Blanket application rates (kg per hectare) by crop, with the fertilizer type
# and the stage it is applied. These follow general MINAGRI/RAB recommendations
# and are a starting point only; real rates depend on soil testing and should be
# confirmed with local extension advice.
CROP_PLAN = {
    "maize":    [("NPK 17-17-17", 150, "at planting (basal)"),
                 ("Urea", 100, "topdressing, 4-6 weeks after planting")],
    "potatoes": [("NPK 17-17-17", 350, "at planting (basal)"),
                 ("Urea", 100, "topdressing, at hilling")],
    "beans":    [("DAP", 100, "at planting (basal)")],
}

# Agricultural lime for acidic soils. Rwanda's central/highland ferralsols are
# often acidic (pH < 5.5), which locks up phosphorus and cuts fertilizer response,
# so the plan varies by district: more acidic soil -> more lime. Travertine lime is
# subsidised; ~5,000 RWF per 50 kg is a nationwide estimate. Rates are indicative —
# confirm with a soil test.
LIME_PRICE_RWF = 5000


def _lime_rate_kg_ha(ph) -> int:
    """Indicative agricultural-lime rate (kg/ha) from topsoil pH; 0 if not acidic."""
    if ph is None:
        return 0
    if ph < 5.0:
        return 2000
    if ph < 5.3:
        return 1500
    if ph < 5.6:
        return 1000
    return 0


def recommend_plan(catalogue: pd.DataFrame, crop: str, land_ha: float,
                   budget_rwf: float, district: str | None = None):
    """Size a fertilizer plan to the farmer's land — and, when a district is given,
    add a soil-correction step (lime) sized to that district's soil acidity, so the
    plan genuinely differs where the soil differs.

    Converts land area into the kilograms and 50 kg bags needed using per-hectare
    application rates, then prices them from the catalogue.

    Returns (plan_df, total_cost, within_budget, remaining_rwf).
    """
    crop = crop.lower()
    rows = []

    # district-specific soil correction: lime for acidic districts (before planting)
    if district:
        from config.district_agro import agro_profile
        ap = agro_profile(district)
        lime_rate = _lime_rate_kg_ha(ap.get("ph"))
        if lime_rate:
            need_kg = lime_rate * land_ha
            bags = max(1, math.ceil(need_kg / BAG_KG))
            rows.append({
                "fertilizer": "Agricultural lime (50kg bag)",
                "when": f"soil correction, before planting (pH {ap['ph']:.1f})",
                "rate_kg_ha": lime_rate,
                "need_kg": round(need_kg),
                "bags_50kg": bags,
                "price_per_bag": LIME_PRICE_RWF,
                "line_cost": int(bags * LIME_PRICE_RWF),
            })

    for name_key, rate, stage in CROP_PLAN.get(crop, []):
        match = catalogue[catalogue["input_name"].str.contains(name_key, case=False, na=False)]
        if match.empty:
            continue
        row = match.iloc[0]
        price = float(row["price_rwf"])
        required_kg = rate * land_ha
        bags = max(1, math.ceil(required_kg / BAG_KG))
        rows.append({
            "fertilizer": row["input_name"],
            "when": stage,
            "rate_kg_ha": rate,
            "need_kg": round(required_kg),
            "bags_50kg": bags,
            "price_per_bag": int(price),
            "line_cost": int(bags * price),
        })

    plan_df = pd.DataFrame(rows)
    total = int(plan_df["line_cost"].sum()) if not plan_df.empty else 0
    return plan_df, total, total <= budget_rwf, int(budget_rwf - total)
