"""Seasonal Risk — real rainfall anomaly + latest CPI/fertilizer -> trained model."""
from _ui import setup, load_rainfall, load_cpi, load_fert, load_risk_model, footer
import pandas as pd, streamlit as st
from config.settings import DISTRICTS
from src.data.preprocessing import label_risk
from src.db.connection import log_risk

setup("Seasonal Risk", "Planting risk by district and season")
rain, cpi, fert, model = load_rainfall(), load_cpi(), load_fert(), load_risk_model()

# Rwanda's two main cropping seasons. The rainfall data codes the March-May long
# rains as 'A' and the October-December short rains as 'B'; the official MINAGRI
# calendar names them the other way round, so show the official names and map.
SEASONS = {
    "Season A · short rains (Oct–Dec)": "B",
    "Season B · long rains (Mar–May)": "A",
}

c1, c2 = st.columns(2)
district = c1.selectbox("District", DISTRICTS)
season_label = c2.selectbox("Season", list(SEASONS.keys()))
scode = SEASONS[season_label]

if st.button("Assess Risk", type="primary"):
    r = rain[(rain.district == district) & (rain.season == scode)]
    rain_a = float(r.rainfall_anomaly.iloc[-1]) if len(r) else float(rain.rainfall_anomaly.mean())
    cpi_c = float(cpi.cpi_change.dropna().iloc[-1]); fert_c = float(fert.fert_change.dropna().iloc[-1])
    if model is not None:
        X = pd.DataFrame([[rain_a, cpi_c, fert_c]], columns=["rainfall_anomaly", "cpi_change", "fert_change"])
        level = str(model.predict(X)[0]); conf = f"{model.predict_proba(X).max()*100:.0f}% confidence"
    else:
        level = label_risk(rain_a, cpi_c, fert_c); conf = "rule-based"
    log_risk(district, scode, rain_a, cpi_c, fert_c, level)
    color = {"High": "#DC2626", "Medium": "#D97706", "Low": "#40916C"}[level]
    st.markdown(f"<div class='ar-card'><span class='ar-badge' style='background:{color}'>{level} risk</span>"
                f"<span style='color:#5E7065;margin-left:10px'>{district} · {season_label} · {conf}</span></div>",
                unsafe_allow_html=True)
    st.caption("Risk = how likely staple food prices are to rise sharply over the coming months, "
               "predicted from pre-season conditions.")
    st.write("**What's driving this**")
    clamp = lambda v: max(0.0, min(v, 1.0))
    st.progress(clamp(abs(rain_a)/2), text="Rainfall compared to normal")
    st.progress(clamp(cpi_c/30), text="Food price pressure (CPI)")
    st.progress(clamp(fert_c/60), text="Fertilizer cost pressure")
    st.info({"High": "High risk — food prices likely to climb. Advise storing harvest, budgeting for higher input costs, and conservative spending.",
             "Medium": "Moderate risk — monitor markets and weather; plan inputs carefully.",
             "Low": "Lower risk — prices likely stable. Normal planting and input investment is reasonable."}[level])
else:
    st.info("Pick a district and season, then click **Assess Risk**.")

footer()
