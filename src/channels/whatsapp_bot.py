"""Farmer WhatsApp chatbot logic.

parse_message() turns a natural-language Kinyarwanda/English query into a
structured intent. The web app (and, in production, the Twilio webhook) routes
that intent to the right module and formats a bilingual reply. Keeping parsing
here means the live Twilio integration is a thin wrapper around the same logic.
"""
from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from config.settings import DISTRICTS, data_path

# crop vocabulary: Kinyarwanda + English -> canonical crop
CROP_WORDS = {
    "ibigori": "maize", "maize": "maize",
    "ibishyimbo": "beans", "beans": "beans",
    "ibirayi": "potatoes", "potato": "potatoes", "potatoes": "potatoes",
}
# intent keywords
INTENT_WORDS = {
    "price": ["igiciro", "price", "ibiciro"],
    "risk": ["risk", "ibyago", "ibyago"],
    "disease": ["indwara", "disease"],
    "input": ["input", "ifumbire", "inputs", "imbuto", "fertilizer", "fertiliser"],
    "help": ["help", "ubufasha"],
}


def detect_language(text: str) -> str:
    rw_markers = ("igiciro", "ibigori", "ibirayi", "ibishyimbo", "indwara",
                  "ibyago", "ifumbire", "ubufasha", "muraho")
    return "rw" if any(w in text for w in rw_markers) else "en"


def parse_message(text: str) -> dict:
    """Return {intent, crop, district, budget, lang} parsed from a message."""
    t = text.lower().strip()
    lang = detect_language(t)

    intent = None
    for name, words in INTENT_WORDS.items():
        if any(w in t for w in words):
            intent = name
            break

    crop = next((c for w, c in CROP_WORDS.items() if w in t), None)
    district = next((d for d in DISTRICTS if d.lower() in t), None)
    budget_match = re.search(r"\d{4,}", t.replace(",", ""))
    budget = int(budget_match.group()) if budget_match else None

    # land size: "0.5 ha", "1 hectare", "50 ares" (1 are = 0.01 ha)
    land_match = re.search(r"(\d+(?:\.\d+)?)\s*(hectares|hectare|ha|ares|are)\b", t)
    land_ha = None
    if land_match:
        val = float(land_match.group(1))
        land_ha = val * 0.01 if land_match.group(2).startswith("are") else val

    # infer intent when a crop/district is named without an explicit keyword
    if intent is None and crop and district:
        intent = "price"

    return {"intent": intent, "crop": crop, "district": district,
            "budget": budget, "land_ha": land_ha, "lang": lang}


# ---------------------------------------------------------------------------
# answer(): the full bilingual reply for one message. Used by the Streamlit
# WhatsApp Preview page AND the Twilio webhook, so both behave identically.
# Loads data with plain pandas (no Streamlit cache) so it runs anywhere.
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _prices():
    return pd.read_csv(data_path("wfp_food_prices_rwanda.csv"), parse_dates=["date"])


@lru_cache(maxsize=1)
def _rainfall():
    return pd.read_csv(data_path("district_rainfall_anomalies.csv"), parse_dates=["date"])


@lru_cache(maxsize=1)
def _cpi():
    d = pd.read_csv(data_path("rwanda_food_cpi.csv"), parse_dates=["date"]).sort_values("date")
    d["cpi_change"] = d["food_cpi"].pct_change(12) * 100
    return d


@lru_cache(maxsize=1)
def _fert():
    d = pd.read_csv(data_path("fertilizer_price_index.csv"), parse_dates=["date"]).sort_values("date")
    d["fert_change"] = d["fert_index"].pct_change(12) * 100
    return d


@lru_cache(maxsize=1)
def _catalogue():
    return pd.read_csv(data_path("minagri_input_prices.csv"))


def answer(text: str) -> str:
    """Return the bilingual reply for a farmer's message."""
    from src.models.input_recommender import recommend_plan
    from src.data.preprocessing import label_risk

    p = parse_message(text or "")
    crop, district, intent = p["crop"], p["district"], p["intent"]
    rw = p["lang"] == "rw"

    def say(rw_text, en_text):
        return rw_text if rw else en_text

    if intent in (None, "help"):
        return say("Ndashobora kugufasha: igiciro, ibyago (risk), indwara, cyangwa ifumbire. "
                   "Urugero: 'ibigori igiciro Bugesera'.",
                   "I can help with: price, risk, disease, or inputs. "
                   "For example: 'maize price Bugesera'.")

    if intent == "price":
        if not crop:
            return say("Ni igihingwa ki? (ibigori, ibishyimbo, cyangwa ibirayi)",
                       "Which crop? (maize, beans, or potatoes)")
        if not district:
            return say(f"Ni mu karere ka he? Urugero: '{crop} igiciro Musanze'.",
                       f"Which district? For example: '{crop} price Musanze'.")
        ser = _prices().query("crop == @crop and market == @district")["price_rwf"]
        if len(ser) == 0:
            return say(f"Nta makuru y'igiciro cy'{crop} muri {district} ahari.",
                       f"No price data for {crop} in {district}.")
        return say(f"{crop.title()}, {district}: hafi {ser.iloc[-1]:,.0f} RWF/kg",
                   f"{crop.title()}, {district}: about {ser.iloc[-1]:,.0f} RWF/kg")

    if intent == "risk":
        if not district:
            return say("Ni mu karere ka he? Urugero: 'risk Musanze'.",
                       "Which district? For example: 'risk Musanze'.")
        rain, cpi, fert = _rainfall(), _cpi(), _fert()
        r = rain[rain.district == district]
        ra = float(r.rainfall_anomaly.iloc[-1]) if len(r) else 0.0
        lvl = label_risk(ra, float(cpi.cpi_change.dropna().iloc[-1]),
                         float(fert.fert_change.dropna().iloc[-1]))
        return say(f"{district}: ibyago bingana {lvl}", f"{district}: risk {lvl}")

    if intent == "disease":
        if not district:
            return say("Ni mu karere ka he?", "Which district?")
        c = crop or ("igihingwa cyawe" if rw else "your crop")
        return say(f"{district}: reba urupapuro 'Disease Alert' ku {c}.",
                   f"{district}: see the Disease Alert screen for {c}.")

    if intent == "input":
        if not crop:
            return say("Ni igihingwa ki? (ibigori, ibishyimbo, cyangwa ibirayi)",
                       "Which crop? (maize, beans, or potatoes)")
        if not p["land_ha"]:
            return say("Ubuso bwawe bungana iki? Urugero: 'ifumbire ibigori 0.5 ha'.",
                       "What is your land size? For example: 'fertilizer maize 0.5 ha'.")
        plan, total, ok, remaining = recommend_plan(
            _catalogue(), crop, float(p["land_ha"]), float(p["budget"]) if p["budget"] else 1e12)
        if plan.empty:
            return say("Nta gahunda y'ifumbire kuri icyo gihingwa.", "No fertilizer plan for that crop.")
        bw = lambda n: ("umufuka" if n == 1 else "imifuka") if rw else ("bag" if n == 1 else "bags")
        parts = [f"{int(r.bags_50kg)} {bw(int(r.bags_50kg))} {r.fertilizer.replace(' (50kg bag)', '')}"
                 for _, r in plan.iterrows()]
        detail = ", ".join(parts)
        out = say(f"{crop.title()}, {p['land_ha']:g} ha: {detail}. Igiteranyo {total:,} RWF.",
                  f"{crop.title()}, {p['land_ha']:g} ha: {detail}. Total {total:,} RWF.")
        if p["budget"] and not ok:
            out += say(f" Irenga ingengo yawe {int(-remaining):,} RWF.",
                       f" Over budget by {int(-remaining):,} RWF.")
        return out

    return say("Andika 'ubufasha'.", "Type 'help'.")
