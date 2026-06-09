"""AgriRisk Rwanda - extension officer dashboard (Home screen).

Run with:  streamlit run dashboard/Home.py
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import streamlit as st

st.set_page_config(page_title="AgriRisk Rwanda", page_icon="🌱", layout="wide")

st.title("🌱 AgriRisk Rwanda")
st.caption("Agricultural risk intelligence for Rwanda's extension officers")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Districts served", "30")
c2.metric("Crops covered", "3")
c3.metric("Advisory modules", "4")
c4.metric("Delivery channels", "3")

st.divider()
st.subheader("Modules")
cols = st.columns(2)
mods = [
    ("📈 Price Forecast", "4-week crop price predictions (maize, beans, potatoes)."),
    ("⚠️ Seasonal Risk", "Climate + inflation risk scoring per district."),
    ("🦠 Disease Alert", "Live weather-driven crop disease warnings."),
    ("🛒 Input Recommender", "Affordable seeds, fertilizers & pesticides by budget."),
]
for i, (title, desc) in enumerate(mods):
    with cols[i % 2]:
        st.markdown(f"### {title}")
        st.write(desc)

st.info("Select a module from the sidebar to begin. ← ")
st.divider()
st.caption("Data sources: WFP Rwanda · MINAGRI · RAB · NISR · Open-Meteo · World Bank")
