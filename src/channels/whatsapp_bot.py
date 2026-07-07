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
    "price": ["igiciro", "ibiciro", "price", "prices", "isoko", "market", "sell", "selling", "kugurisha"],
    "risk": ["risk", "risky", "ibyago", "igihembwe", "season", "seasonal", "drought", "amapfa"],
    "disease": ["indwara", "disease", "diseases", "blight", "fungus", "pest", "uburwayi"],
    "input": ["input", "inputs", "ifumbire", "imbuto", "fertilizer", "fertiliser",
              "npk", "urea", "dap", "seed", "manure"],
    "help": ["help", "ubufasha", "menu"],
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


@lru_cache(maxsize=1)
def _price_forecasters():
    """The trained per-crop price models {crop: model}, or None if not built yet."""
    import pickle
    from config.settings import MODELS_STORE
    p = MODELS_STORE / "price_forecaster.pkl"
    try:
        return pickle.load(open(p, "rb")) if p.exists() else None
    except Exception:
        return None


@lru_cache(maxsize=1)
def _risk_clf():
    """The trained seasonal-risk classifier, or None if not built yet."""
    import pickle
    from config.settings import MODELS_STORE
    p = MODELS_STORE / "risk_classifier.pkl"
    try:
        return pickle.load(open(p, "rb")) if p.exists() else None
    except Exception:
        return None


@lru_cache(maxsize=1)
def _esoko():
    """Esoko farmgate prices, or None if none ingested yet."""
    from config.settings import DATA_PROCESSED
    p = DATA_PROCESSED / "esoko_farmgate_prices.csv"
    try:
        return pd.read_csv(p, parse_dates=["date"]) if p.exists() else None
    except Exception:
        return None


@lru_cache(maxsize=1)
def _ratios():
    """{crop: farmgate/retail ratio} for expressing non-Esoko districts in farmgate."""
    from src.models.price_forecasting import crop_ratios
    try:
        return crop_ratios(_prices(), _esoko())
    except Exception:
        return None


def crop_varieties(crop):
    """Variety/grade names for a crop from Esoko (beans & potatoes), sorted; [] otherwise.
    Shared so the dashboard, chat and USSD offer the SAME types."""
    e = _esoko()
    if e is None or "variety" not in getattr(e, "columns", []):
        return []
    return sorted(v for v in e[e["crop"] == crop]["variety"].dropna().unique() if v != "Grain")


def _detect_variety(text, crop):
    """Find a variety name mentioned in a free-text message (e.g. 'beans colta ...')."""
    vs = crop_varieties(crop)
    tl = (text or "").lower()
    for v in sorted(vs, key=len, reverse=True):          # longest first ('Kinigi Grade 1')
        if v.lower() in tl:
            return v
    for v in vs:                                         # else a distinctive first word
        w = v.lower().split()[0]
        if w and w != "standard" and w in tl:
            return v
    return None


def answer(text: str, ctx: dict | None = None) -> str:
    """Return the bilingual reply for a farmer's message.

    `ctx` carries unfilled slots (intent/crop/district/...) from an earlier turn
    so a stateful caller (the in-app chat) can follow up: after "Which crop?" a
    bare "potatoes" is understood as the crop for the pending question. Callers
    with their own state (USSD menus) leave ctx=None and behave exactly as before.
    """
    from src.models.input_recommender import recommend_plan
    from src.data.preprocessing import label_risk

    p = parse_message(text or "")
    if ctx:                                          # inherit anything this turn didn't name
        for k in ("intent", "crop", "district", "land_ha", "budget"):
            if not p.get(k):
                p[k] = ctx.get(k)
    crop, district, intent = p["crop"], p["district"], p["intent"]
    rw = p["lang"] == "rw"

    def say(rw_text, en_text):
        return rw_text if rw else en_text

    # a crop/district named without a topic -> ask which topic (and remember the crop),
    # rather than falling through to the generic "off-topic" decline.
    if intent is None and (crop or district):
        subj = crop.title() if crop else district
        return say(f"{subj}: urashaka iki, igiciro, ibyago (risk), indwara, cyangwa ifumbire?",
                   f"{subj}: what would you like, price, seasonal risk, disease, or inputs?")

    if intent in (None, "help"):
        return say("Ndi umufasha w'ubuhinzi gusa. Nshobora kugufasha ku: igiciro, ibyago "
                   "(risk), indwara, cyangwa ifumbire, ku bigori, ibishyimbo n'ibirayi. "
                   "Urugero: 'ibigori igiciro Bugesera' cyangwa 'indwara ibirayi Musanze'.",
                   "I'm a farming assistant only. I can help with crop price, seasonal risk, "
                   "disease alerts, or input plans, for maize, beans and potatoes. "
                   "For example: 'maize price Bugesera' or 'disease potato Musanze'.")

    if intent == "price":
        if not crop:
            return say("Ni igihingwa ki? (ibigori, ibishyimbo, cyangwa ibirayi)",
                       "Which crop? (maize, beans, or potatoes)")
        if not district:
            return say(f"Ni mu karere ka he? Urugero: '{crop} igiciro Musanze'.",
                       f"Which district? For example: '{crop} price Musanze'.")
        # SAME canonical outlook the dashboard uses, so the figures always agree
        from src.models.price_forecasting import price_outlook
        variety = _detect_variety(text, crop) or (ctx or {}).get("variety")  # e.g. "beans colta price Gicumbi"
        o = price_outlook(_prices(), _price_forecasters(), crop, district,
                          esoko=_esoko(), ratios=_ratios(), variety=variety)
        if o is None:
            return say(f"Nta makuru y'igiciro cy'{crop} muri {district} ahari.",
                       f"No price data for {crop} in {district}.")
        cur, fc = o["current"], o["forecast"]
        real = o["level"] == "farmgate"                  # real Esoko vs estimated farmgate
        lvl_rw = "ku murima" if real else "ku murima (~)"
        lvl_en = "farmgate" if real else "farmgate ~"
        name = f"{crop.title()} {variety}" if variety else crop.title()
        if fc is None:                                   # fall back to the latest price
            return say(f"{name}, {district} ({lvl_rw}): hafi {cur:,.0f} RWF/kg ubu.",
                       f"{name}, {district} ({lvl_en}): about {cur:,.0f} RWF/kg now.")
        pct = o["pct"] or 0.0
        tr_rw, tr_en = (("birazamuka", "rising") if pct > 1 else
                        ("biragabanuka", "falling") if pct < -1 else ("bihagaze", "stable"))
        return say(f"{name}, {district} ({lvl_rw}): ubu {cur:,.0f}, ukwezi gutaha ~{fc:,.0f} RWF/kg ({tr_rw}).",
                   f"{name}, {district} ({lvl_en}): now {cur:,.0f}, next month ~{fc:,.0f} RWF/kg ({tr_en}).")

    if intent == "risk":
        if not district:
            return say("Ni mu karere ka he? Urugero: 'risk Musanze'.",
                       "Which district? For example: 'risk Musanze'.")
        rain, cpi, fert = _rainfall(), _cpi(), _fert()
        r = rain[rain.district == district]
        ra = float(r.rainfall_anomaly.iloc[-1]) if len(r) else 0.0
        cc = float(cpi.cpi_change.dropna().iloc[-1])
        ff = float(fert.fert_change.dropna().iloc[-1])
        model = _risk_clf()
        lvl = None
        if model is not None:
            try:
                from src.models.risk_classifier import feature_row
                lvl = str(model.predict(feature_row(ra, cc, ff, district))[0])
            except Exception:
                lvl = None
        if lvl is None:                                  # fall back to the rule-based label
            lvl = label_risk(ra, cc, ff)
        return say(f"{district}: ibyago bingana {lvl}.", f"{district}: risk {lvl}.")

    if intent == "disease":
        if not district:
            return say("Ni mu karere ka he? Urugero: 'indwara ibirayi Musanze'.",
                       "Which district? For example: 'disease potato Musanze'.")
        from config.settings import DISTRICT_COORDS, CROPS
        from src.models.disease_alert import fetch_forecast, assess_crop
        coords = DISTRICT_COORDS.get(district)
        if not coords:
            return say(f"Nta makuru y'ikirere kuri {district}.", f"No weather data for {district}.")
        try:
            daily = fetch_forecast(*coords)
        except Exception:
            return say("Sinabashije kubona iteganyagihe ubu. Ongera ugerageze.",
                       "I couldn't fetch the weather just now. Please try again shortly.")
        check = [crop] if crop else CROPS
        order = {"High": 0, "Medium": 1, "Low": 2}
        alerts = sorted((a for c in check for a in assess_crop(c, daily)),
                        key=lambda a: order.get(a["risk"], 3))
        if not alerts:
            return say(f"{district}: nta byago byinshi by'indwara mu minsi 14 iri imbere.",
                       f"{district}: no elevated disease risk in the next 14 days.")
        parts = "; ".join(f"{a['disease']} ({a['crop']}), {a['risk']}" for a in alerts[:3])
        tip = alerts[0]["action"]
        return say(f"{district}: {parts}. {tip}", f"{district}: {parts}. {tip}")

    if intent == "input":
        if not crop:
            return say("Ni igihingwa ki? (ibigori, ibishyimbo, cyangwa ibirayi)",
                       "Which crop? (maize, beans, or potatoes)")
        if not p["land_ha"]:
            return say("Ubuso bwawe bungana iki? Urugero: 'ifumbire ibigori 0.5 ha'.",
                       "What is your land size? For example: 'fertilizer maize 0.5 ha'.")
        plan, total, ok, remaining = recommend_plan(
            _catalogue(), crop, float(p["land_ha"]), float(p["budget"]) if p["budget"] else 1e12,
            district=district)   # district -> soil-specific lime, matching the dashboard
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


def _slots_complete(m: dict) -> bool:
    """True when the merged slots are enough to fully answer, so the chat can
    stop carrying context. Mirrors the 'ask for the missing piece' checks above."""
    intent = m.get("intent")
    if intent == "price":
        return bool(m.get("crop") and m.get("district"))
    if intent == "risk":
        return bool(m.get("district"))
    if intent == "disease":
        return bool(m.get("district"))          # crop optional (checks all crops)
    if intent == "input":
        return bool(m.get("crop") and m.get("land_ha"))
    return False                                # None/help: keep any crop we learned


def _variety_prompt(crop: str, vs: list, rw: bool) -> str:
    """The 'Which type?' menu for beans/potatoes (numbered, 0 = all types)."""
    rows = ["0) " + ("Byose" if rw else "All types")]
    rows += [f"{i + 1}) {v}" for i, v in enumerate(vs)]
    body = "  \n".join(rows)                              # markdown hard-breaks -> one per line
    crop_rw = {"beans": "ibishyimbo", "potatoes": "ibirayi"}.get(crop, crop)
    if rw:
        return f"Ni ubuhe bwoko bw'{crop_rw}? Andika umubare cyangwa izina:  \n{body}"
    return f"Which type of {crop}? Reply with the number or name:  \n{body}"


def _resolve_variety(text: str, vs: list, crop: str):
    """Map a reply to the type menu -> a variety, or None for 'all types'."""
    tl = (text or "").strip().lower()
    if tl in ("0", "all", "any", "all types", "byose", "zose", "bwose"):
        return None
    if tl.isdigit():
        i = int(tl)
        return vs[i - 1] if 1 <= i <= len(vs) else None
    return _detect_variety(text, crop)                   # a typed name, else None (all)


def converse(text: str, state: dict | None = None):
    """Stateful chat wrapper: (reply, new_state).

    Remembers unfilled slots across turns so a follow-up like 'potatoes' (after
    'Which crop?') or 'Musanze' (after 'Which district?') continues the pending
    request. For beans & potatoes it also asks 'Which type?' (like the USSD menu)
    before quoting a price. Explicit new values in `text` override what was
    remembered, and the state resets once a request is fully answered. The
    advisory logic is the shared answer()/price_outlook, so replies match the
    dashboard and USSD.
    """
    state = state or {}
    p = parse_message(text or "")
    rw = p["lang"] == "rw"

    # Does THIS message say anything on-topic, a crop, district, intent keyword,
    # land size or budget, or a valid answer to a pending menu step? If not, it's
    # gibberish/off-topic: give the domain decline and CLEAR the sticky state, so a
    # leftover "price" intent doesn't keep re-asking "Which crop?" for junk input.
    recognized = bool(p["intent"] or p["crop"] or p["district"] or p["land_ha"] or p["budget"])
    if not recognized and state.get("variety_asked"):
        tl = (text or "").strip().lower()
        if (tl.isdigit() or tl in ("0", "all", "any", "all types", "byose", "zose", "bwose")
                or _detect_variety(text, state.get("crop") or "")):
            recognized = True
    if not recognized:
        return answer(text), {}

    intent = p["intent"] or state.get("intent")
    crop = p["crop"] or state.get("crop")
    district = p["district"] or state.get("district")
    variety = (_detect_variety(text, crop) if crop else None) or state.get("variety")
    land_ha = p["land_ha"] or state.get("land_ha")
    budget = p["budget"] or state.get("budget")
    if intent is None and crop and district:             # crop + district across turns -> price
        intent = "price"

    # guided type step: beans & potatoes have varieties -> ask which one, once
    if intent == "price" and district and variety is None and crop in ("beans", "potatoes"):
        vs = crop_varieties(crop)
        if vs and state.get("variety_asked"):
            variety = _resolve_variety(text, vs, crop)   # this turn is the menu reply
        elif vs:
            return _variety_prompt(crop, vs, rw), {
                "intent": intent, "crop": crop, "district": district,
                "land_ha": land_ha, "budget": budget, "variety": None, "variety_asked": True}

    merged = {"intent": intent, "crop": crop, "district": district,
              "land_ha": land_ha, "budget": budget, "variety": variety}
    reply = answer(text, ctx=merged)
    return reply, ({} if _slots_complete(merged) else merged)
