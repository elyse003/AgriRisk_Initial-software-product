"""Screen: Seasonal Risk. Uses the trained Random Forest classifier (or the
proposal thresholds as fallback) to score climate-inflation risk."""
import os, sys, pickle
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../.."))

import pandas as pd
import streamlit as st

from config.settings import MODELS_STORE, DISTRICTS
from src.data.preprocessing import label_risk

st.set_page_config(page_title="Seasonal Risk", page_icon="⚠️")
st.title("⚠️ Seasonal Risk")


@st.cache_resource
def load_model():
    path = MODELS_STORE / "risk_classifier.pkl"
    if path.exists():
        with open(path, "rb") as f:
            return pickle.load(f)
    return None


model = load_model()

c1, c2 = st.columns(2)
district = c1.selectbox("District", DISTRICTS)
season = c2.selectbox("Growing season", ["A (Mar-May)", "B (Oct-Dec)"])

st.markdown("**Adjust current conditions:**")
rain = st.slider("Rainfall anomaly (std-devs)", -2.0, 2.0, -0.5, 0.1)
cpi = st.slider("Food CPI change (YoY %)", 0.0, 30.0, 12.0, 0.5)
fert = st.slider("Fertilizer price change (YoY %)", 0.0, 60.0, 25.0, 0.5)

if st.button("Assess risk", type="primary"):
    if model is not None:
        pred = model.predict(pd.DataFrame(
            [[rain, cpi, fert]], columns=["rainfall_anomaly", "cpi_change", "fert_change"]))[0]
        proba = model.predict_proba(pd.DataFrame(
            [[rain, cpi, fert]], columns=["rainfall_anomaly", "cpi_change", "fert_change"]))[0].max()
        conf = f"{proba*100:.0f}% confidence"
    else:
        pred = label_risk(rain, cpi, fert)
        conf = "rule-based"

    color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}[pred]
    st.markdown(f"## {color} Risk level: **{pred}**  \n_{conf}_")

    st.markdown("**Contributing factors:**")
    st.progress(min(abs(rain) / 2, 1.0), text=f"Rainfall anomaly: {rain:+.1f} σ")
    st.progress(min(cpi / 30, 1.0), text=f"Food CPI change: {cpi:.1f}%")
    st.progress(min(fert / 60, 1.0), text=f"Fertilizer change: {fert:.1f}%")

    advice = {
        "High": "High combined climate-economic risk. Advise conservative planting and "
                "minimal input spend this season.",
        "Medium": "Moderate risk. Advise farmers to monitor conditions and consider "
                  "drought-tolerant varieties.",
        "Low": "Favourable conditions. Normal planting and input investment is reasonable.",
    }[pred]
    st.info(advice)
else:
    st.info("Set the conditions above, then click **Assess risk**.")
