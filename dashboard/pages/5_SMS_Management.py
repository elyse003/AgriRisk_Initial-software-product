"""Screen: SMS Management (admin). Manage farmer subscribers for weekly alerts."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../.."))

import pandas as pd
import streamlit as st

st.set_page_config(page_title="SMS Management", page_icon="📱")
st.title("📱 Farmer SMS Management")

if "subscribers" not in st.session_state:
    st.session_state.subscribers = pd.DataFrame([
        {"phone": "+250788111222", "district": "Bugesera", "crops": "maize,beans", "lang": "rw"},
        {"phone": "+250788333444", "district": "Musanze", "crops": "potatoes", "lang": "rw"},
    ])

st.metric("Active subscribers", len(st.session_state.subscribers))
st.dataframe(st.session_state.subscribers, use_container_width=True)

st.subheader("Add subscriber")
c1, c2, c3, c4 = st.columns(4)
phone = c1.text_input("Phone")
district = c2.selectbox("District", ["Musanze", "Bugesera", "Nyagatare", "Huye", "Rubavu", "Kayonza"])
crops = c3.text_input("Crops", "maize")
lang = c4.selectbox("Language", ["rw", "en"])
if st.button("Add", type="primary") and phone:
    st.session_state.subscribers = pd.concat([
        st.session_state.subscribers,
        pd.DataFrame([{"phone": phone, "district": district, "crops": crops, "lang": lang}]),
    ], ignore_index=True)
    st.rerun()

st.caption("Weekly SMS broadcasts are sent via the Africa's Talking API (see src/channels/sms_alerts.py).")
