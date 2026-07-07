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

    # ---- editorial result pages (redesign), working draft, review with a native speaker ----
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
    "AgriRisk Assistant": "Umufasha wa AgriRisk",
    "Console": "Ibikoresho",
    "Preferences": "Ibyo uhitamo",
    "Hello! Ask me about price, risk, disease or inputs, for example: 'maize price Musanze'.":
        "Muraho! Mbaza ku giciro, ibyago, indwara cyangwa ifumbire, urugero: 'ibigori igiciro Musanze'.",
    "Ask price, risk, disease, inputs…": "Baza igiciro, ibyago, indwara, ifumbire…",
    # ---- simplified result-page labels ----
    "Current price": "Igiciro cy'ubu",
    "Latest market price": "Igiciro cya vuba ku isoko",
    "Farmgate price": "Igiciro ku murima",
    "Market price": "Igiciro ku isoko",
    "farmgate price": "igiciro ku murima",
    "farmgate · monthly": "ku murima · buri kwezi",
    "estimated": "iteganyijwe",
    "Type": "Ubwoko",
    "All types (average)": "Ubwoko bwose (impuzandengo)",
    "Likely low": "Hasi gishoboka",
    "Likely high": "Hejuru gishoboka",
    "Source": "Inkomoko",
    "WFP market prices": "Ibiciro by'isoko (WFP)",
    "RISK LEVEL": "URWEGO RW'IBYAGO",
    "WHAT IS DRIVING THIS": "IBIBITERA",
    "Food price pressure": "Igitutu cy'ibiciro by'ibiribwa",
    "Fertilizer cost": "Igiciro cy'ifumbire",
    "RAINFALL vs NORMAL": "IMVURA UGERERANYIJE",
    "FOOD PRICES": "IBICIRO BY'IBIRIBWA",
    "Rainfall record": "Amakuru y'imvura",
    "Food price index": "Urutonde rw'ibiciro by'ibiribwa",
    "Based on": "Bishingiye kuri",
    "Rainfall, food prices and fertilizer costs": "Imvura, ibiciro by'ibiribwa n'igiciro cy'ifumbire",
    "Disease": "Indwara",
    "When it strikes": "Igihe igaragara",
    "DISEASE GUIDE": "UBUYOBOZI BW'INDWARA",
    "Open-Meteo 14-day forecast": "Iteganyagihe ry'iminsi 14",
    "Prices": "Ibiciro",
    "Sized to": "Bingana na",
    "Menu": "Ibikubiyemo",
    # ---- USSD preview ----
    "Channels": "Imiyoboro",
    "USSD Preview": "Igerageza rya USSD",
    "simulator": "igerageza",
    "Dial again": "Hamagara nanone",
    "Send": "Ohereza",
    "Cancel": "Hagarika",
    "Your reply": "Igisubizo cyawe",
    "Enter a number": "Andika umubare",
    "Reply with a number.": "Subiza n'umubare.",
    "Session ended.": "Igiterane kirangiye.",
    "Dial the code to open the menu.": "Hamagara iyi kode kugira ngo ufungure menu.",
    "Confirm with soil testing and local extension advice.":
        "Emeza hakozwe isuzuma ry'ubutaka n'abajyanama b'ubuhinzi bo mu karere.",

    # ---- full Kinyarwanda coverage (added 2026-07) ----
    'A good time to buy inputs while prices are low.': 'Igihe cyiza cyo kugura ifumbire mu gihe ibiciro biri hasi.',
    'Acidic {soil} (pH {ph}), apply lime to lift yield, and add organic matter.': "{soil} irimo aside (pH {ph}), shyiraho shokora kugira ngo wongere umusaruro, wongereho n'ifumbire mvaruganda.",
    'Actual farmgate (Esoko)': 'Igiciro nyacyo ku murima (Esoko)',
    'Agro-zone': "Agace k'ubuhinzi",
    'All crops': 'Ibihingwa byose',
    'Altitude': 'Ubutumburuke',
    'Apply lime before planting to fix the acidity, then the fertilizers.': 'Shyiraho shokora mbere yo gutera kugira ngo ukemure aside, hanyuma ushyireho ifumbire.',
    'Ask about crops…': 'Baza ku bihingwa…',
    'Budget': "Ingengo y'imari",
    'Budget inputs carefully; stretch with compost and manure.': "Tegura ifumbire witonze; ongeraho ifumbire mvaruganda n'imborera.",
    'Buy': 'Gura',
    'Crop disease warnings for the next 14 days, based on the local weather forecast.': "Imiburo y'indwara z'ibihingwa mu minsi 14 iri imbere, ishingiye ku iteganyagihe ryo mu karere.",
    'Dial *384#': 'Hamagara *384#',
    'Do now': 'Kora nonaha',
    'Dominant soil': "Ubwoko bw'ubutaka bwiganje",
    'Drainage': "Iyubira ry'amazi",
    'Dry, lower fungal pressure': "Byumye, igitutu cy'uduhumyo kiri hasi",
    'Estimated farmgate for {district}, recent market prices adjusted by the measured farmgate margin; next-month trend from the model.': "Igiciro ku murima giteganyijwe kuri {district}, ibiciro bya vuba by'isoko byahinduwe hakoreshejwe itandukaniro ry'igiciro ku murima; icyerekezo cy'ukwezi gutaha kiva mu cyitegererezo.",
    'Fairly dry ({mm}mm), lower fungal pressure.': "Bikonje gato ({mm}mm), igitutu cy'uduhumyo kiri hasi.",
    'Farmgate history': "Amateka y'igiciro ku murima",
    'Farmgate price from Esoko for {district}; next-month trend from the model.': "Igiciro ku murima kiva kuri Esoko kuri {district}; icyerekezo cy'ukwezi gutaha kiva mu cyitegererezo.",
    'Fertilizer': 'Ifumbire',
    'Fits your budget with {r:,} RWF to spare.': "Bihuye n'ingengo y'imari yawe, hasigaye {r:,} RWF.",
    'Food prices': "Ibiciro by'ibiribwa",
    'For {land:g} ha, buy: {items}.': 'Kuri {land:g} ha, gura: {items}.',
    'Good moisture for planting; drought risk is low.': "Ubuhehere buhagije bwo gutera; ibyago by'amapfa biri hasi.",
    'Great soil moisture and low drought risk, but scout for fungal disease in humid spells.': "Ubutaka bufite ubuhehere buhagije kandi ibyago by'amapfa biri hasi, ariko witegereze indwara z'uduhumyo mu gihe cy'ubuhehere bwinshi.",
    'High drought risk, delay planting or choose drought-tolerant seed; irrigate if you can.': "Ibyago byinshi by'amapfa, tinda gutera cyangwa uhitemo imbuto zihanganira amapfa; uhe amazi niba bishoboka.",
    'High, favours fungal disease': "Bwinshi, bworohereza indwara z'uduhumyo",
    'How a farmer reaches AgriRisk on any phone, no internet, no app, through a *384#-style menu. This is a working simulator; going live needs a short code from an operator, but the menu itself is ready.': "Uko umuhinzi agera kuri AgriRisk kuri telefoni iyo ari yo yose, nta murandasi, nta porogaramu, binyuze kuri menu isa na *384#. Iki ni igerageza rikora; kugira ngo bikore by'ukuri bikeneye kode ngufi ya operateri, ariko menu ubwayo yiteguye.",
    'How likely staple food prices are to rise sharply this season, from rainfall, food prices and fertilizer costs.': "Uko ibiciro by'ibiribwa by'ibanze bishobora kuzamuka cyane muri iki gihembwe, biturutse ku mvura, ibiciro by'ibiribwa n'igiciro cy'ifumbire.",
    'How sure': 'Uko twizeye',
    'Humidity': 'Ubuhehere',
    'Indicative range, farmgate prices can swing wider than market prices, so treat the low/high as a guide.': "Urwego rw'icyerekezo, ibiciro ku murima bishobora guhinduka cyane kurusha ibiciro by'isoko, bityo ufate hasi/hejuru nk'ubuyobozi gusa.",
    'Input costs are rising, plan and buy early.': "Ibiciro by'ifumbire biriyongera, tegura kandi ugure kare.",
    'Kigali City': 'Umujyi wa Kigali',
    'Likely between {lo} and {hi} RWF/kg next month, farmgate can swing wider, so treat it as a guide.': "Bishoboka hagati ya {lo} na {hi} RWF/kg ukwezi gutaha, igiciro ku murima gishobora guhinduka cyane, bityo ubifate nk'ubuyobozi.",
    'Little inflation pressure this season.': "Igitutu gito cy'izamuka ry'ibiciro muri iki gihembwe.",
    'Lower-fertility {soil}, build it up with compost/manure and a balanced fertilizer.': "{soil} ifite uburumbuke buke, uyongere intungamubiri ukoresheje ifumbire mvaruganda/imborera n'ifumbire iringaniye.",
    'Moderate upward pressure on staple prices; hold some stock if you can store it well.': "Igitutu kiringaniye cyo kuzamuka ku biciro by'ibiribwa by'ibanze; bika bimwe niba ushobora kubibika neza.",
    'New accounts are farmers. An administrator can upgrade you to extension officer.': "Konti nshya ni iz'abahinzi. Umuyobozi ashobora kukuzamura ukaba umujyanama w'ubuhinzi.",
    'Next month': 'Ukwezi gutaha',
    'Next-month estimate. Confirm with local market conditions.': "Iteganya ry'ukwezi gutaha. Emeza n'uko isoko ryo mu karere rimeze.",
    'No elevated disease risk in the next 14 days, the steps below are preventive.': "Nta byago byinshi by'indwara mu minsi 14 iri imbere; intambwe zikurikira ni izo kwirinda.",
    "No local market history for {district}, figures fall back to Rwanda's national average.": "Nta mateka y'isoko yo mu karere ka {district}, imibare igarukira ku mpuzandengo y'igihugu y'u Rwanda.",
    "No local price history for {district}, showing Rwanda's national average as a farmgate price; next-month trend from the model.": "Nta mateka y'igiciro yo mu karere ka {district}, twerekana impuzandengo y'igihugu nk'igiciro ku murima; icyerekezo cy'ukwezi gutaha kiva mu cyitegererezo.",
    "No local price history for {district}, so the trend uses Rwanda's national average; the price level is a real Esoko farmgate figure.": "Nta mateka y'igiciro yo mu karere ka {district}, bityo icyerekezo gikoresha impuzandengo y'igihugu; urwego rw'igiciro ni umubare nyawo wa Esoko ku murima.",
    'Normal input budgeting is fine.': "Gutegura ingengo y'ifumbire isanzwe birahagije.",
    'Outside main blight window': "Hanze y'igihe cy'ingenzi cy'indwara",
    'Over budget by {x:,} RWF, buy in stages or start with a smaller area (lime is a one-off).': "Birenze ingengo y'imari ku {x:,} RWF, gura mu byiciro cyangwa utangire ku buso buto (shokora igurwa rimwe gusa).",
    'Pick a district and crop to see disease risk.': "Hitamo akarere n'igihingwa kugira ngo urebe ibyago by'indwara.",
    'Preventive care': 'Kwirinda',
    'Price now': "Igiciro cy'ubu",
    'Prices look steady (~{pct}). No urgent timing pressure.': "Ibiciro bisa nk'ibihagaze (~{pct}). Nta gitutu cyihutirwa cy'igihe.",
    'Prices look to be falling (~{pct}). Selling sooner is likely better than waiting.': "Ibiciro bisa nk'ibigabanuka (~{pct}). Kugurisha vuba birushaho kuba byiza kuruta gutegereza.",
    'Prices look to be rising (~{pct}). If you can store well, holding 2-3 weeks may pay more.': "Ibiciro bisa nk'ibizamuka (~{pct}). Niba ushobora kubika neza, kubika ibyumweru 2-3 bishobora kuguha byinshi.",
    'Rain & leaf wetness': "Imvura n'ubuhehere ku mababi",
    'Rainfall': 'Imvura',
    'Right now': 'Nonaha',
    'SOIL &amp; TERRAIN': "UBUTAKA N'AHANTU",
    'Set crop, district, land size and budget to see the plan.': "Shyiraho igihingwa, akarere, ubuso n'ingengo y'imari kugira ngo urebe gahunda.",
    'Soil': 'Ubutaka',
    'Soil &amp; terrain': "Ubutaka n'ahantu",
    'Soil fertility': "Uburumbuke bw'ubutaka",
    'Soil pH': "pH y'ubutaka",
    'Soil pH is fine, no lime needed; just the fertilizers.': "pH y'ubutaka ni nziza, nta shokora ikenewe; ifumbire gusa.",
    'Solid dots are real Esoko farmgate months; the rest of the line is estimated from market prices.': "Utudomo twuzuye ni amezi nyayo ya Esoko ku murima; ibisigaye ku murongo biteganyijwe hashingiwe ku biciro by'isoko.",
    'Some drought risk, favour drought-tolerant, short-cycle varieties and save water.': "Ibyago bike by'amapfa, hitamo imbuto zihanganira amapfa kandi zeza vuba, ubike n'amazi.",
    'Steady': 'Bihagaze',
    'Strong upward pressure, a good time to sell stored grain, but expect higher costs too.': "Igitutu gikomeye cyo kuzamuka, igihe cyiza cyo kugurisha imyaka wabitse, ariko witegure ko n'ibiciro bizamuka.",
    'Temperature': 'Ubushyuhe',
    'The fertilizer your land needs, priced against your budget, just the few inputs that matter most.': "Ifumbire ubutaka bwawe bukeneye, igereranyijwe n'ingengo y'imari yawe, ifumbire nkeya y'ingenzi gusa.",
    'The full dashboard is for extension officers. Tap the chat button (bottom-right), or open USSD Preview to try the *384# menu, both answer price, risk, disease and input questions.': "Imbonerahamwe yuzuye ni iy'abajyanama b'ubuhinzi. Kanda buto y'ikiganiro (iburyo hasi), cyangwa ufungure USSD Preview ugerageze menu ya *384#, byombi bisubiza ibibazo by'igiciro, ibyago, indwara n'ifumbire.",
    "The model now factors in each district's soil and terrain (about {pct}% of its estimate here). Price-spike risk is still driven mostly by rainfall and market prices; soil and altitude matter more for yield and input planning.": "Icyitegererezo ubu gishyiramo ubutaka n'ubutumburuke bwa buri karere (nka {pct}% by'iteganya hano). Ibyago by'izamuka ry'igiciro biracyaterwa cyane n'imvura n'ibiciro by'isoko; ubutaka n'ubutumburuke bigira uruhare rwinshi ku musaruro no gutegura ifumbire.",
    'Try: 1 (price) → 2 (Northern) → 4 (Musanze). The menu uses the same data and advice as the chat assistant.': "Gerageza: 1 (igiciro) → 2 (Amajyaruguru) → 4 (Musanze). Menu ikoresha amakuru n'inama bimwe n'umufasha w'ikiganiro.",
    'Typical planting conditions for this season.': 'Imiterere isanzwe yo gutera muri iki gihembwe.',
    'WHAT TO DO': 'ICYO GUKORA',
    'Weaker selling prices, sell only what you must; store the rest if you can.': 'Ibiciro byo kugurisha bike, gurisha gusa ibyo ugomba; ubike ibisigaye niba bishoboka.',
    'Wet 14 days ({mm}mm), leaves stay wet, which lets fungal spores spread.': "Iminsi 14 y'imvura ({mm}mm), amababi aguma ahehereye, bituma imbuto z'uduhumyo zikwira.",
    'Wet, sustained leaf wetness': 'Bihehereye, ubuhehere buhoraho ku mababi',
    'What a farmer is likely to be paid next month, the farmgate price, from recent market data.': "Icyo umuhinzi ashobora guhembwa ukwezi gutaha, igiciro ku murima, kivuye ku makuru ya vuba y'isoko.",
    'What this means': 'Icyo ibi bisobanura',
    'What to do': 'Icyo gukora',
    'When to apply': 'Igihe cyo gushyiraho',
    'Within blight-favourable window': 'Mu gihe cyorohereza indwara',
    "You'd be paid about {p} RWF/kg now ({src}).": 'Wahembwa nka {p} RWF/kg ubu ({src}).',
    'a bit wetter than normal': 'bihehereye gato kurusha ibisanzwe',
    'about normal rainfall': 'imvura isanzwe',
    'acidic, lime helps': 'irimo aside, shokora irafasha',
    'active': 'biriho',
    'agro-ecological zone': "agace k'ubuhinzi",
    'bar = model weight': 'umurongo = uburemere mu cyitegererezo',
    'drier than normal': 'byumye kurusha ibisanzwe',
    'elevated, a price spike is more likely; store and spend cautiously': "byiyongereye, izamuka ry'igiciro rirashoboka; bika kandi ukoreshe witonze",
    'estimated farmgate': 'igiciro ku murima giteganyijwe',
    'fertilizer cheaper': 'ifumbire yagabanutse',
    'fertilizer costs stable': "ibiciro by'ifumbire bihagaze",
    'fertilizer getting dearer': 'ifumbire iriyongera',
    'fertilizer much dearer': 'ifumbire yiyongereye cyane',
    'food prices falling': "ibiciro by'ibiribwa biragabanuka",
    'food prices rising': "ibiciro by'ibiribwa birazamuka",
    'food prices rising fast': "ibiciro by'ibiribwa birazamuka vuba",
    'food prices roughly stable': "ibiciro by'ibiribwa bisa n'ibihagaze",
    'free-draining': 'byubira amazi neza',
    'from Esoko farmgate': 'kiva kuri Esoko ku murima',
    'good': 'bwiza',
    'high, sharp price rises are likely; prioritise storage and hardy varieties': "byinshi, izamuka rikomeye ry'ibiciro rirashoboka; ha imbere kubika no guhitamo imbuto zikomeye",
    'low': 'buke',
    'low to moderate, largely stable, but keep an eye on markets': 'buke kugeza biringaniye, ahanini bihagaze, ariko ukomeze ukurikirane isoko',
    'menu': 'menu',
    'moderate': 'biringaniye',
    'moderate, mixed signals; plan carefully and keep a reserve': 'biringaniye, ibimenyetso bivanze; tegura witonze kandi ubike ingoboka',
    'mostly stable, normal planting and input spending is reasonable': 'ahanini bihagaze, gutera no gukoresha ifumbire bisanzwe birashoboka',
    'much drier than normal': 'byumye cyane kurusha ibisanzwe',
    'much wetter than normal': 'bihehereye cyane kurusha ibisanzwe',
    'national average, no local data': "impuzandengo y'igihugu, nta makuru yo mu karere",
    'national avg': "impuzandengo y'igihugu",
    'near neutral': 'hafi kuringana',
    'next 14 days': 'iminsi 14 iri imbere',
    'poor': 'bibi',
    'rich': 'bukungahaye',
    'slightly acidic': 'irimo aside gike',
    'very low': 'buke cyane',
    'vs a year ago': "ugereranyije n'umwaka ushize",
    '{c}°C on average, inside the range blights favour.': '{c}°C impuzandengo, biri mu rwego rworohereza indwara.',
    '{c}°C on average, outside the main blight window.': "{c}°C impuzandengo, hanze y'igihe cy'ingenzi cy'indwara.",
    "{district}'s soil is acidic ({soil}, pH {ph}), so the plan adds lime to correct it, acidic soil locks up phosphorus and wastes fertilizer. Lime is a one-off amendment (good for 2-3 seasons), not an every-season cost like fertilizer.": "Ubutaka bwa {district} burimo aside ({soil}, pH {ph}), bityo gahunda yongeraho shokora kugira ngo ibikemure, ubutaka burimo aside bufunga fosifore kandi bugapfusha ifumbire ubusa. Shokora ishyirwaho rimwe (imara ibihembwe 2-3), si ikiguzi cya buri gihembwe nk'ifumbire.",
    "{district}'s soil is near-neutral ({soil}, pH {ph}), so no lime is needed. Fertilizer types and Smart Nkunganire prices are set nationally.": "Ubutaka bwa {district} buri hafi kuringana ({soil}, pH {ph}), bityo nta shokora ikenewe. Ubwoko bw'ifumbire n'ibiciro bya Smart Nkunganire bishyirwaho ku rwego rw'igihugu.",
    '{h}% humidity, high, which favours fungal disease.': "Ubuhehere {h}%, buri hejuru, buworohereza indwara z'uduhumyo.",
    '{h}% humidity, moderate.': 'Ubuhehere {h}%, buringaniye.',
    '{n} disease(s) at elevated risk for {scope}. Act on the highlighted steps.': 'Indwara {n} zifite ibyago byinshi kuri {scope}. Kora ku ntambwe zagaragajwe.',
    "{soil} at {alt} m, reasonable for the district's staples.": "{soil} ku butumburuke bwa {alt} m, buhagije ku bihingwa by'ibanze by'akarere.",
    'Nyarugenge is largely urban, local farming is limited to peri-urban sectors, and city prices reflect the consumption market more than a farmgate.': "Nyarugenge ahanini ni umujyi, ubuhinzi bwo mu karere bugarukira ku turere twegereye umujyi, kandi ibiciro byo mu mujyi bigaragaza isoko ry'abaguzi kurusha igiciro ku murima.",
    'Gasabo mixes the city with large rural sectors (maize, beans, vegetables), these results apply to its peri-urban farmland.': "Gasabo ivanga umujyi n'imirenge minini yo mu cyaro (ibigori, ibishyimbo, imboga), ibi bisubizo bireba imyaka yo mu turere twegereye umujyi.",
    'Kicukiro is semi-urban with peri-urban farmland, these results apply to its rural sectors (e.g. Masaka, Gahanga).': "Kicukiro ni igice cy'umujyi gifite imyaka yo mu turere twegereye umujyi, ibi bisubizo bireba imirenge yayo yo mu cyaro (urugero: Masaka, Gahanga).",
    'Dry/inflationary conditions raise the chance of a sharp price spike. Advise storage, conservative input spend and drought-tolerant varieties.': "Imiterere y'amapfa n'izamuka ry'ibiciro yongera ibyago by'izamuka rikomeye ry'igiciro. Bisabwa kubika umusaruro, gukoresha ifumbire mu buryo bwitonze no guhitamo imbuto zihanganira amapfa.",
    'Mixed signals. Monitor markets and weather; plan inputs carefully and keep a reserve.': "Ibimenyetso bivanze. Kurikirana isoko n'iteganyagihe; tegura ifumbire witonze kandi ubike ingoboka.",
    'Conditions look stable. Normal planting and input investment is reasonable.': "Imiterere isa n'ihagaze. Guhinga no gushora mu ifumbire bisanzwe birashoboka.",
}


def lang() -> str:
    return st.session_state.get("lang", "en")


def t(s: str) -> str:
    """Translate a source (English) string to the current language."""
    return RW.get(s, s) if lang() == "rw" else s


def crop_label(crop: str) -> str:
    """Display name for a crop value in the current language."""
    return CROPS.get(crop, {}).get(lang(), crop.title())