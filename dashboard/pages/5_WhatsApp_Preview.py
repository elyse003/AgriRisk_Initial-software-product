"""WhatsApp Preview: farmer chatbot (Kinyarwanda + English).

Uses the same src.channels.whatsapp_bot.answer() as the live Twilio webhook, so
the in-app preview and real WhatsApp/SMS replies are identical.
"""
from _ui import setup
import streamlit as st
from src.channels.whatsapp_bot import answer

setup("WhatsApp Preview", "Ask about price, risk, disease, or inputs")

st.markdown("**Examples:** `ibigori igiciro bugesera` · `risk musanze` · "
            "`indwara ibirayi musanze` · `ifumbire ibigori 0.5 ha` · `ubufasha`")

if "chat" not in st.session_state:
    st.session_state.chat = [("assistant", "Muraho. Andika: igiciro, risk, indwara, cyangwa input.")]
for role, txt in st.session_state.chat:
    with st.chat_message(role):
        st.write(txt)
if msg := st.chat_input("Andika hano… (e.g. ibigori igiciro bugesera)"):
    st.session_state.chat.append(("user", msg))
    st.session_state.chat.append(("assistant", answer(msg)))
    st.rerun()