"""Tiny i18n layer for the AgriRisk dashboard.

The chosen language lives in st.session_state["lang"] ("en" | "rw") and is set by
the sidebar selector in _ui.setup(), so it persists across pages and can be
changed from any page. t(s) returns the Kinyarwanda string when the language is
"rw", otherwise the English source string.

Kinyarwanda translations are a working draft and should be reviewed by a native
speaker before a real deployment.
"""
from __future__ import annotations

import streamlit as st

LANGUAGES = {"English": "en", "Kinyarwanda": "rw"}

# crop value -> display name per language
CROPS = {
    "maize": {"en": "Maize", "rw": "Ibigori"},
    "beans": {"en": "Beans", "rw": "Ibishyimbo"},
    "potatoes": {"en": "Potatoes", "rw": "Ibirayi"},
}

# English source -> Kinyarwanda. Anything missing falls back to English.
RW = {
    # ---- chrome ----
    "Dashboard": "Imbonerahamwe",
    "Choose a tool to get started": "Hitamo igikoresho kugira ngo utangire",
    "Open": "Fungura",
    # ---- hub cards: stages + descriptions ----
    "At selling": "Mu kugurisha",
    "Before planting": "Mbere yo gutera",
    "While growing": "Mu gukura",
    "At planting": "Mu gutera",
    "For farmers": "Ku bahinzi",
    "Next-month price outlook by crop and district.":
        "Iteganya ry'igiciro cy'ukwezi gutaha ku gihingwa n'akarere.",
    "Planting risk from rainfall, food inflation and fertilizer cost.":
        "Ibyago byo guhinga biturutse ku mvura, izamuka ry'ibiciro by'ibiribwa n'igiciro cy'ifumbire.",
    "Crop disease warnings from the live weather forecast.":
        "Imiburo y'indwara z'ibihingwa ishingiye ku iteganyagihe.",
    "A fertilizer plan sized to your land and budget.":
        "Gahunda y'ifumbire ihuye n'ubuso bwawe n'ingengo y'imari.",
    "Farmer chat answering price, risk, disease and input questions.":
        "Ikiganiro n'umuhinzi gisubiza ibibazo by'igiciro, ibyago, indwara n'ifumbire.",
    # ---- footer ----
    "Tools": "Ibikoresho",
    "Data": "Amakuru",
    "Project": "Umushinga",
    "Home": "Ahabanza",
    "Machine learning decision support for Rwandan agriculture: price forecasts, "
    "seasonal risk, disease alerts and input plans for maize, beans and Irish "
    "potatoes across all 30 districts, in Kinyarwanda and English.":
        "Ubufasha bushingiye ku bwenge bw'ikoranabuhanga ku buhinzi bw'u Rwanda: "
        "iteganya ry'ibiciro, ibyago by'igihembwe, imiburo y'indwara na gahunda "
        "z'ifumbire ku bigori, ibishyimbo n'ibirayi mu turere twose 30, mu "
        "Kinyarwanda no mu Cyongereza.",
    "Decision support only. Confirm with local extension advice.":
        "Ni inama gusa. Emeza n'abajyanama b'ubuhinzi bo mu karere.",

    # ---- Price Forecast ----
    "Price Forecast": "Iteganya ry'igiciro",
    "Next-month price outlook by crop and district":
        "Iteganya ry'igiciro cy'ukwezi gutaha ku gihingwa n'akarere",
    "Crop": "Igihingwa",
    "District": "Akarere",
    "Generate Forecast": "Tanga iteganya",
    "Current": "Ubu",
    "Next-month forecast": "Iteganya ry'ukwezi gutaha",
    "Trend": "Icyerekezo",
    "Advice": "Inama",
    "Recent and forecast price": "Igiciro cya vuba n'iteganyijwe",
    "Rising": "Birazamuka",
    "Falling": "Biragabanuka",
    "Stable": "Bihagaze",
    "Pick a crop and district, then click **Generate Forecast**.":
        "Hitamo igihingwa n'akarere, hanyuma ukande **Tanga iteganya**.",
    "{crop} trending up in {district}. Advise holding stock 2 to 3 weeks.":
        "{crop} biragenda byiyongera muri {district}. Bisabwa kubika ibyumweru 2 kugeza 3.",
    "{crop} trending down in {district}. Advise selling soon.":
        "{crop} biragenda bigabanuka muri {district}. Bisabwa kugurisha vuba.",
    "{crop} stable in {district}. No urgent action.":
        "{crop} bihagaze muri {district}. Nta gikorwa cyihutirwa.",
    "Next-month estimate from the trained model. Confirm with local market conditions.":
        "Iteganya ry'ukwezi gutaha. Emeza n'uko isoko ryo mu karere rimeze.",

    # ---- Seasonal Risk ----
    "Seasonal Risk": "Ibyago by'igihembwe",
    "Planting risk by district and season": "Ibyago byo guhinga ku karere n'igihembwe",
    "Season": "Igihembwe",
    "Season A, short rains (Oct to Dec)": "Igihembwe A, imvura nke (Ukwakira-Ukuboza)",
    "Season B, long rains (Mar to May)": "Igihembwe B, imvura nyinshi (Werurwe-Gicurasi)",
    "Assess Risk": "Suzuma ibyago",
    "confidence": "icyizere",
    "High risk": "Ibyago byinshi",
    "Medium risk": "Ibyago biringaniye",
    "Low risk": "Ibyago bike",
    "High": "Byinshi",
    "Medium": "Biringaniye",
    "Low": "Bike",
    "Risk means how likely staple food prices are to rise sharply over the coming "
    "months, predicted from pre-season conditions.":
        "Ibyago bivuga uko ibiciro by'ibiribwa by'ibanze bishobora kuzamuka cyane mu "
        "mezi ari imbere, biteganyijwe hashingiwe ku miterere ya mbere y'igihembwe.",
    "What's driving this": "Ibibitera",
    "Rainfall compared to normal": "Imvura ugereranyije n'ibisanzwe",
    "Food price pressure (CPI)": "Igitutu cy'ibiciro by'ibiribwa",
    "Fertilizer cost pressure": "Igitutu cy'igiciro cy'ifumbire",
    "High risk. Food prices likely to climb. Advise storing harvest, budgeting for "
    "higher input costs, and conservative spending.":
        "Ibyago byinshi. Ibiciro by'ibiribwa bishobora kuzamuka. Bisabwa kubika "
        "umusaruro, gutegura amafaranga y'ifumbire menshi no kugabanya ikoreshwa.",
    "Moderate risk. Monitor markets and weather; plan inputs carefully.":
        "Ibyago biringaniye. Kurikirana isoko n'iteganyagihe; tegura ifumbire witonze.",
    "Lower risk. Prices likely stable. Normal planting and input investment is reasonable.":
        "Ibyago bike. Ibiciro bishobora guhagarara. Guhinga n'ishoramari mu ifumbire bisanzwe birashoboka.",
    "Pick a district and season, then click **Assess Risk**.":
        "Hitamo akarere n'igihembwe, hanyuma ukande **Suzuma ibyago**.",

    # ---- Disease Alert ----
    "Disease Alert": "Imenyesha ry'indwara",
    "Crop disease warnings from the local weather":
        "Imiburo y'indwara z'ibihingwa ishingiye ku iteganyagihe",
    "Check Risk": "Reba ibyago",
    "Live 14-day weather forecast.": "Iteganyagihe ry'iminsi 14.",
    "Offline mode: showing a sample forecast.": "Nta murandasi: turerekana urugero.",
    "No elevated disease risk for the forecast window.":
        "Nta byago byinshi by'indwara muri iki gihe.",
    "Action:": "Igikorwa:",
    "Triggers:": "Ibibitera:",
    "Pick a district and click **Check Risk**.":
        "Hitamo akarere hanyuma ukande **Reba ibyago**.",

    # ---- Input Recommender ----
    "Input Recommender": "Inama ku ifumbire",
    "Fertilizer plan for your land and budget":
        "Gahunda y'ifumbire ku buso bwawe n'ingengo y'imari",
    "Land size (hectares)": "Ubuso (hegitari)",
    "Budget (RWF)": "Ingengo y'imari (RWF)",
    "Build Fertilizer Plan": "Kora gahunda y'ifumbire",
    "No fertilizer plan is defined for that crop yet.":
        "Nta gahunda y'ifumbire iriho kuri icyo gihingwa.",
    "AT PLANTING": "MU GUTERA",
    "bag(s)": "imifuka",
    "needed": "bikenewe",
    "Total for {land:g} ha: {total:,} RWF, within budget, {remaining:,} RWF to spare.":
        "Igiteranyo kuri {land:g} ha: {total:,} RWF, biri mu ngengo y'imari, {remaining:,} RWF birasagutse.",
    "Total for {land:g} ha: {total:,} RWF, over budget by {extra:,} RWF. Use the subsidised "
    "Smart Nkunganire price, buy in stages, or start with a smaller area.":
        "Igiteranyo kuri {land:g} ha: {total:,} RWF, birenze ingengo y'imari ku {extra:,} RWF. "
        "Koresha igiciro gifashijwe cya Smart Nkunganire, gura mu byiciro, cyangwa utangire ku buso buto.",
    "Rates follow MINAGRI/RAB recommendations and should be confirmed with soil testing and "
    "local extension advice. Prices are subsidised (Smart Nkunganire System).":
        "Ingano ikurikiza inama za MINAGRI/RAB kandi igomba kwemezwa hakozwe isuzuma ry'ubutaka "
        "n'abajyanama b'ubuhinzi bo mu karere. Ibiciro bifashijwe (Smart Nkunganire System).",
    "Set crop, land size and budget, then click **Build Fertilizer Plan**.":
        "Shyiraho igihingwa, ubuso n'ingengo y'imari, hanyuma ukande **Kora gahunda y'ifumbire**.",

    # ---- WhatsApp ----
    "WhatsApp Preview": "Igerageza rya WhatsApp",
    "Ask about price, risk, disease, or inputs":
        "Baza ku giciro, ibyago, indwara, cyangwa ifumbire",

    # ---- auth / settings ----
    "Sign in": "Injira",
    "Sign in to the dashboard": "Injira ku mbonerahamwe",
    "For extension officers and administrators": "Ku bajyanama b'ubuhinzi n'abayobozi",
    "Username": "Izina ry'ukoresha",
    "Password": "Ijambo banga",
    "Wrong username or password.": "Izina cyangwa ijambo banga sibyo.",
    "Create account": "Fungura konti",
    "Full name": "Amazina yombi",
    "Confirm password": "Emeza ijambo banga",
    "Phone (optional)": "Telefoni (si itegeko)",
    "Please fill in name, username and password.":
        "Uzuza amazina, izina ry'ukoresha n'ijambo banga.",
    "Passwords do not match.": "Amagambo banga ntahuye.",
    "Password must be at least 6 characters.":
        "Ijambo banga rigomba kuba nibura inyuguti 6.",
    "That username or phone is already taken.":
        "Iryo zina cyangwa telefoni byamaze gukoreshwa.",
    "In a real deployment, officer access would be approved by an administrator.":
        "Mu ikoreshwa nyaryo, kwemererwa nk'umujyanama byemezwa n'umuyobozi.",
    "Log out": "Sohoka",
    "Signed in as": "Winjiye nka",
    "This screen is for extension officers. As a farmer, you get the same advice "
    "by SMS and WhatsApp.":
        "Iyi paji ni iy'abajyanama b'ubuhinzi. Nk'umuhinzi, ubona inama zimwe "
        "kuri SMS na WhatsApp.",
    "Settings": "Igenamiterere",
    "Your account and preferences": "Konti yawe n'ibyo uhitamo",
    "User Management": "Gucunga abakoresha",
    "Manage accounts and roles": "Gucunga konti n'inshingano",
    "This page is for administrators only.": "Iyi paji ni iy'abayobozi gusa.",
    "Appearance": "Imiboneka",
    "Theme": "Insanganyamatsiko",
    "Light": "Urumuri",
    "Dark": "Umwijima",
    "Language": "Ururimi",
    "Account": "Konti",
    "Name": "Izina",
    "Role": "Uruhare",
    "Welcome": "Murakaza neza",
    "The full dashboard is for extension officers. You can chat with the assistant "
    "on WhatsApp for price, risk, disease and input advice.":
        "Imbonerahamwe yuzuye ni iy'abajyanama b'ubuhinzi. Ushobora kuganira "
        "n'umufasha kuri WhatsApp ku nama z'igiciro, ibyago, indwara n'ifumbire.",

    # ---- editorial result pages (redesign) — working draft, review with a native speaker ----
    "price": "igiciro",
    "Last actual": "Iheruka nyayo",
    "Model MAPE (held-out)": "MAPE y'icyitegererezo",
    "Target": "Intego",
    "Actual": "Nyayo",
    "forecast": "iteganya",
    "band": "urwego",
    "monthly": "buri kwezi",
    "WHAT TO ADVISE": "ICYO WAGIRA INAMA",
    "FOR THE OFFICER": "KU MUJYANAMA",
    "Hold": "Bika",
    "Sell": "Gurisha",
    "FORECAST": "ITEGANYA",
    "DETAIL": "IBISOBANURO",
    "Method": "Uburyo",
    "Training data": "Amakuru y'imyitozo",
    "Note": "Icyitonderwa",
    "MONTHS HISTORY": "AMEZI ASHIZE",
    "MONTH FORECAST": "UKWEZI KW'ITEGANYA",
    # risk
    "Seasonal": "Igihembwe",
    "planting risk": "ibyago byo guhinga",
    "recalculated weekly": "bibarwa buri cyumweru",
    "CLASSIFICATION OUTPUT": "IGISUBIZO",
    "CONTRIBUTING": "IBIGIRA URUHARE",
    "FEATURES": "IBIRANGA",
    "Features": "Ibiranga",
    "Rainfall vs normal": "Imvura ugereranyije n'ibisanzwe",
    "RAINFALL ANOMALY": "IHINDAGURIKA RY'IMVURA",
    "RECENT": "VUBA",
    "FOOD CPI · Y/Y": "CPI Y'IBIRIBWA",
    "MODEL": "ICYITEGEREREZO",
    "BENCHMARKS": "IGERERANYA",
    "Model": "Icyitegererezo",
    "Accuracy": "Ukuri",
    "Status": "Uko bihagaze",
    "Deployed": "Gikoreshwa",
    # disease
    "Climate-driven": "Bishingiye ku kirere",
    "disease alerts": "imiburo y'indwara",
    "14-day horizon": "iminsi 14",
    "updated hourly": "bivugururwa buri saha",
    "WEATHER CONTEXT": "IMITERERE Y'IKIRERE",
    "14-day rainfall": "Imvura y'iminsi 14",
    "Mean temperature": "Ubushyuhe busanzwe",
    "Mean humidity": "Ubuhehere busanzwe",
    "Moderate humidity": "Ubuhehere buringaniye",
    "DAILY DISEASE RISK INDEX": "URWEGO RW'IBYAGO BY'INDWARA BURI MUNSI",
    "ACTIVE": "BIRIHO",
    "ALERTS": "IMIBURO",
    "RISK": "IBYAGO",
    "RULE": "AMATEGEKO",
    "BASE · FAO CALENDARS": "ASHINGIRA · FAO",
    "Pathogen": "Indwara",
    "Trigger conditions": "Ibyangombwa bibitera",
    "Weather": "Ikirere",
    # inputs
    "Affordable inputs": "Ifumbire ihendutse",
    "your land and budget": "ubuso n'ingengo y'imari",
    "items": "ibintu",
    "RANK": "URUTONDE",
    "PER BAG": "KU MUFUKA",
    "RECOMMENDED": "BYASABWE",
    "TOP": "HEJURU",
    "OTHER": "IBINDI",
    "MATCHES": "BIHUYE",
    "over": "birenze",
    "Item": "Ikintu",
    "Type": "Ubwoko",
    "Supplier": "Utanga",
    "Price (RWF)": "Igiciro (RWF)",
    "Bulletin": "Itangazo",
    "Sizing": "Ingano",
    "Chat on WhatsApp": "Ganira kuri WhatsApp",
    "Confirm with soil testing and local extension advice.":
        "Emeza hakozwe isuzuma ry'ubutaka n'abajyanama b'ubuhinzi bo mu karere.",
}


def lang() -> str:
    return st.session_state.get("lang", "en")


def t(s: str) -> str:
    """Translate a source (English) string to the current language."""
    return RW.get(s, s) if lang() == "rw" else s


def crop_label(crop: str) -> str:
    """Display name for a crop value in the current language."""
    return CROPS.get(crop, {}).get(lang(), crop.title())