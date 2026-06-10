"""WhatsApp Preview — farmer chatbot (Kinyarwanda + English) using the same models."""
from _ui import setup, load_prices, load_rainfall, load_cpi, load_fert, load_catalogue, load_risk_model
import pandas as pd, streamlit as st
from src.channels.whatsapp_bot import parse_message
from src.models.input_recommender import recommend
from src.data.preprocessing import label_risk

setup("WhatsApp Preview", "Farmer-facing chatbot · Kinyarwanda + English")

st.markdown("**Supported commands:** `ibigori igiciro bugesera` · `risk musanze` · "
            "`indwara ibirayi musanze` · `input maize bugesera 60000` · `ubufasha`")

def reply(msg):
    p = parse_message(msg)
    crop = p["crop"] or "maize"; district = p["district"] or "Bugesera"; lang = p["lang"]
    if p["intent"] == "help" or p["intent"] is None:
        return ("Ndashobora kugufasha: igiciro, ibyago (risk), indwara, input." if lang == "rw"
                else "I can help with: price, risk, disease, inputs.")
    if p["intent"] == "price":
        s = load_prices(); ser = s[(s.crop == crop) & (s.market == district)]["price_rwf"]
        if len(ser) == 0: return f"No price data for {crop} in {district}."
        return f"{crop.title()}, {district}: about {ser.iloc[-1]:,.0f} RWF/kg"
    if p["intent"] == "risk":
        rain = load_rainfall(); cpi = load_cpi(); fert = load_fert()
        r = rain[rain.district == district]
        ra = float(r.rainfall_anomaly.iloc[-1]) if len(r) else 0.0
        lvl = label_risk(ra, float(cpi.cpi_change.dropna().iloc[-1]), float(fert.fert_change.dropna().iloc[-1]))
        return f"{district}: risk {lvl}"
    if p["intent"] == "disease":
        return f"{district}: see the Disease Alert screen for {crop}."
    if p["intent"] == "input":
        recs = recommend(load_catalogue(), crop, district, float(p["budget"] or 50000))
        if recs.empty: return "No inputs match that budget."
        return "Recommended: " + "; ".join(f"{r.input_name} {int(r.price_rwf):,} RWF" for _, r in recs.iterrows())
    return "Type 'help' / 'ubufasha'."

if "chat" not in st.session_state:
    st.session_state.chat = [("assistant", "Muraho. Andika: igiciro, risk, indwara, cyangwa input.")]
for role, txt in st.session_state.chat:
    with st.chat_message(role): st.write(txt)
if msg := st.chat_input("Andika hano… (e.g. ibigori igiciro bugesera)"):
    st.session_state.chat.append(("user", msg))
    st.session_state.chat.append(("assistant", reply(msg)))
    st.rerun()
