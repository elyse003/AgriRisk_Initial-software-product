"""WhatsApp Preview, farmer chatbot (Kinyarwanda + English) using the same models."""
from _ui import setup, load_prices, load_rainfall, load_cpi, load_fert, load_catalogue, footer
import streamlit as st
from src.channels.whatsapp_bot import parse_message
from src.models.input_recommender import recommend_plan
from src.data.preprocessing import label_risk

setup("WhatsApp Preview", "Ask about price, risk, disease, or inputs")

st.markdown("**Examples:** `ibigori igiciro bugesera` · `risk musanze` · "
            "`indwara ibirayi musanze` · `ifumbire ibigori 0.5 ha` · `ubufasha`")


def reply(msg):
    p = parse_message(msg)
    crop, district, intent = p["crop"], p["district"], p["intent"]
    rw = p["lang"] == "rw"

    def say(rw_text, en_text):
        return rw_text if rw else en_text

    # no recognised request, or a help request: explain what the bot can do
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
        ser = load_prices().query("crop == @crop and market == @district")["price_rwf"]
        if len(ser) == 0:
            return say(f"Nta makuru y'igiciro cy'{crop} muri {district} ahari.",
                       f"No price data for {crop} in {district}.")
        return say(f"{crop.title()}, {district}: hafi {ser.iloc[-1]:,.0f} RWF/kg",
                   f"{crop.title()}, {district}: about {ser.iloc[-1]:,.0f} RWF/kg")

    if intent == "risk":
        if not district:
            return say("Ni mu karere ka he? Urugero: 'risk Musanze'.",
                       "Which district? For example: 'risk Musanze'.")
        rain, cpi, fert = load_rainfall(), load_cpi(), load_fert()
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
            load_catalogue(), crop, float(p["land_ha"]), float(p["budget"]) if p["budget"] else 1e12)
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


if "chat" not in st.session_state:
    st.session_state.chat = [("assistant", "Muraho. Andika: igiciro, risk, indwara, cyangwa input.")]
for role, txt in st.session_state.chat:
    with st.chat_message(role):
        st.write(txt)
if msg := st.chat_input("Andika hano… (e.g. ibigori igiciro bugesera)"):
    st.session_state.chat.append(("user", msg))
    st.session_state.chat.append(("assistant", reply(msg)))
    st.rerun()

footer()
