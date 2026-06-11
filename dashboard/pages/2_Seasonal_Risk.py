"""Seasonal Risk — real rainfall anomaly + latest CPI/fertilizer -> trained model."""
from _ui import setup, load_rainfall, load_cpi, load_fert, load_risk_model
import pandas as pd, streamlit as st
from config.settings import DISTRICTS
from src.data.preprocessing import label_risk
from src.db.connection import log_risk

setup("Seasonal Risk", "Random Forest / XGBoost · Rainfall + CPI + Fertilizer")
rain, cpi, fert, model = load_rainfall(), load_cpi(), load_fert(), load_risk_model()

c1, c2 = st.columns(2)
district = c1.selectbox("District", DISTRICTS)
season = c2.selectbox("Season", ["A (Mar–May)", "B (Oct–Dec)"])
scode = season[0]

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
                f"<span style='color:#5A7A6A;margin-left:10px'>{district} · Season {scode} · {conf}</span></div>",
                unsafe_allow_html=True)
    st.write("**Contributing factors**")
    clamp = lambda v: max(0.0, min(v, 1.0))
    st.progress(clamp(abs(rain_a)/2), text=f"Rainfall anomaly: {rain_a:+.2f} σ")
    st.progress(clamp(cpi_c/30), text=f"Food CPI change: {cpi_c:.1f}%")
    st.progress(clamp(fert_c/60), text=f"Fertilizer change: {fert_c:.1f}%")
    st.info({"High": "High combined risk — advise conservative planting and minimal input spend.",
             "Medium": "Moderate risk — monitor conditions; consider drought-tolerant varieties.",
             "Low": "Favourable conditions — normal planting and input investment is reasonable."}[level])
else:
    st.info("Pick a district and season, then click **Assess Risk**.")
