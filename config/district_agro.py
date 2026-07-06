"""District agro-ecological profiles for all 30 districts of Rwanda.

These are approximations from Rwanda's agro-ecological zones (RAB / MINAGRI AEZ
classification) — mean altitude, dominant soil group and coarse agronomic scores
— NOT plot-level soil tests. They are static per district, so they let the
seasonal-risk model tell districts apart by terrain and soil (which vary a lot
across Rwanda) rather than only by rainfall.

Scores:
  fertility  1 (poor) .. 5 (rich)     e.g. volcanic andosols = 5, acidic humic ferralsols = 2
  ph         typical topsoil pH (many Rwandan soils are acidic, ~4.8-6.2)
  drainage   1 (waterlogged) .. 5 (free-draining)

Model features exposed to the classifier: altitude_m, soil_fertility, soil_ph, drainage.
"""
from __future__ import annotations

AGRO_FEATURES = ["altitude_m", "soil_fertility", "soil_ph", "drainage"]

# district -> profile. zone/soil are for display; the four numbers feed the model.
DISTRICT_AGRO = {
    # Kigali City — central plateau, weathered ferralsols
    "Nyarugenge": {"zone": "Central Plateau", "soil": "Ferralsol", "altitude_m": 1500, "fertility": 3, "ph": 5.4, "drainage": 3},
    "Gasabo":     {"zone": "Central Plateau", "soil": "Ferralsol", "altitude_m": 1500, "fertility": 3, "ph": 5.4, "drainage": 3},
    "Kicukiro":   {"zone": "Central Plateau", "soil": "Ferralsol", "altitude_m": 1500, "fertility": 3, "ph": 5.4, "drainage": 3},
    # Northern — Birunga volcanic + Buberuka highlands
    "Burera":  {"zone": "Birunga Volcanic", "soil": "Andosol", "altitude_m": 2100, "fertility": 5, "ph": 6.0, "drainage": 4},
    "Gakenke": {"zone": "Buberuka Highlands", "soil": "Humic Ferralsol", "altitude_m": 1850, "fertility": 3, "ph": 5.2, "drainage": 3},
    "Gicumbi": {"zone": "Buberuka Highlands", "soil": "Acidic Ferralsol", "altitude_m": 2000, "fertility": 2, "ph": 5.0, "drainage": 3},
    "Musanze": {"zone": "Birunga Volcanic", "soil": "Andosol", "altitude_m": 1860, "fertility": 5, "ph": 6.2, "drainage": 4},
    "Rulindo": {"zone": "Buberuka Highlands", "soil": "Ferralsol", "altitude_m": 1900, "fertility": 3, "ph": 5.2, "drainage": 3},
    # Southern — central plateau, Mayaga, Congo-Nile divide (SW)
    "Gisagara":  {"zone": "Mayaga Plateau", "soil": "Ferralsol", "altitude_m": 1600, "fertility": 3, "ph": 5.3, "drainage": 3},
    "Huye":      {"zone": "Central Plateau", "soil": "Ferralsol", "altitude_m": 1700, "fertility": 3, "ph": 5.3, "drainage": 3},
    "Kamonyi":   {"zone": "Central Plateau", "soil": "Ferralsol", "altitude_m": 1550, "fertility": 3, "ph": 5.4, "drainage": 3},
    "Muhanga":   {"zone": "Central Plateau", "soil": "Ferralsol", "altitude_m": 1800, "fertility": 3, "ph": 5.2, "drainage": 3},
    "Nyamagabe": {"zone": "Congo-Nile Divide", "soil": "Humic Ferralsol", "altitude_m": 2050, "fertility": 2, "ph": 4.9, "drainage": 3},
    "Nyanza":    {"zone": "Mayaga Plateau", "soil": "Ferralsol", "altitude_m": 1700, "fertility": 3, "ph": 5.4, "drainage": 3},
    "Nyaruguru": {"zone": "Congo-Nile Divide", "soil": "Humic Ferralsol", "altitude_m": 1950, "fertility": 2, "ph": 4.9, "drainage": 3},
    "Ruhango":   {"zone": "Central Plateau", "soil": "Ferralsol", "altitude_m": 1650, "fertility": 3, "ph": 5.4, "drainage": 3},
    # Eastern — savanna lowlands, drier, sandier
    "Bugesera":  {"zone": "Eastern Savanna", "soil": "Sandy Lixisol", "altitude_m": 1400, "fertility": 3, "ph": 5.8, "drainage": 4},
    "Gatsibo":   {"zone": "Eastern Savanna", "soil": "Lixisol", "altitude_m": 1500, "fertility": 3, "ph": 5.7, "drainage": 4},
    "Kayonza":   {"zone": "Eastern Savanna", "soil": "Lixisol", "altitude_m": 1450, "fertility": 3, "ph": 5.8, "drainage": 4},
    "Kirehe":    {"zone": "Eastern Lowland", "soil": "Lixisol / Vertisol", "altitude_m": 1450, "fertility": 3, "ph": 5.8, "drainage": 3},
    "Ngoma":     {"zone": "Eastern Plateau", "soil": "Ferralsol", "altitude_m": 1500, "fertility": 3, "ph": 5.6, "drainage": 3},
    "Nyagatare": {"zone": "Eastern Savanna (semi-arid)", "soil": "Sandy Lixisol", "altitude_m": 1400, "fertility": 2, "ph": 5.9, "drainage": 4},
    "Rwamagana": {"zone": "Eastern Plateau", "soil": "Ferralsol", "altitude_m": 1500, "fertility": 3, "ph": 5.6, "drainage": 3},
    # Western — Congo-Nile crest, Kivu lakeshore, Imbo lowland
    "Karongi":    {"zone": "Kivu / Congo-Nile", "soil": "Humic Ferralsol", "altitude_m": 1900, "fertility": 3, "ph": 5.1, "drainage": 3},
    "Ngororero":  {"zone": "Congo-Nile Divide", "soil": "Humic Ferralsol", "altitude_m": 2050, "fertility": 2, "ph": 5.0, "drainage": 3},
    "Nyabihu":    {"zone": "Birunga Volcanic", "soil": "Andosol", "altitude_m": 2200, "fertility": 5, "ph": 6.0, "drainage": 4},
    "Nyamasheke": {"zone": "Kivu Lakeshore", "soil": "Ferralsol", "altitude_m": 1700, "fertility": 3, "ph": 5.3, "drainage": 3},
    "Rubavu":     {"zone": "Kivu / Birunga Foothills", "soil": "Andosol influence", "altitude_m": 1600, "fertility": 4, "ph": 5.8, "drainage": 4},
    "Rusizi":     {"zone": "Imbo (Rusizi valley)", "soil": "Alluvial", "altitude_m": 1400, "fertility": 4, "ph": 5.9, "drainage": 3},
    "Rutsiro":    {"zone": "Congo-Nile Divide", "soil": "Humic Ferralsol", "altitude_m": 2000, "fertility": 2, "ph": 5.0, "drainage": 3},
}

# national-median fallback for an unknown district (keeps prediction robust)
_FALLBACK = {"zone": "Central Plateau", "soil": "Ferralsol",
             "altitude_m": 1650, "fertility": 3, "ph": 5.4, "drainage": 3}

# Kigali City is mostly urban; farming here is peri-urban (chiefly Gasabo & Kicukiro
# rural sectors — maize, beans, vegetables). So results still apply, but a city-centre
# "farmgate" figure reads more as the consumption market — flag that for the officer.
URBAN_NOTE = {
    "Nyarugenge": "Nyarugenge is largely urban — local farming is limited to peri-urban "
                  "sectors, and city prices reflect the consumption market more than a farmgate.",
    "Gasabo": "Gasabo mixes the city with large rural sectors (maize, beans, vegetables) — "
              "these results apply to its peri-urban farmland.",
    "Kicukiro": "Kicukiro is semi-urban with peri-urban farmland — these results apply to "
                "its rural sectors (e.g. Masaka, Gahanga).",
}


def urban_note(district: str):
    """A peri-urban/urban caveat for Kigali City districts, or None."""
    return URBAN_NOTE.get(district)


def agro_profile(district: str) -> dict:
    """Full display profile (zone, soil, altitude, fertility, ph, drainage)."""
    return DISTRICT_AGRO.get(district, _FALLBACK)


def agro_row(district: str) -> dict:
    """Just the four numeric model features for a district (with fallback)."""
    p = agro_profile(district)
    return {"altitude_m": p["altitude_m"], "soil_fertility": p["fertility"],
            "soil_ph": p["ph"], "drainage": p["drainage"]}


def agro_features():
    """DataFrame [district, altitude_m, soil_fertility, soil_ph, drainage] for
    merging into the risk training set."""
    import pandas as pd
    rows = [{"district": d, **agro_row(d)} for d in DISTRICT_AGRO]
    return pd.DataFrame(rows)