"""Seasonal Risk, real rainfall anomaly + latest CPI/fertilizer -> trained model."""
from _ui import setup, load_rainfall, load_cpi, load_fert, load_risk_model
from _i18n import t
import pandas as pd, streamlit as st
from config.settings import DISTRICTS
from src.data.preprocessing import label_risk
from src.db.connection import log_risk

setup("Seasonal Risk", "Planting risk by district and season", allowed_roles=("officer", "super_admin"))
rain, cpi, fert, model = load_rainfall(), load_cpi(), load_fert(), load_risk_model()

# Rwanda's two main cropping seasons. The rainfall data codes the March-May long
# rains as 'A' and the October-December short rains as 'B'; the official MINAGRI
# calendar names them the other way round, so show the official names and map.
# (English source label, rainfall code)
SEASONS = [
    ("Season A, short rains (Oct to Dec)", "B"),
    ("Season B, long rains (Mar to May)", "A"),
]
SEASON_CODE = {t(lbl): code for lbl, code in SEASONS}

c1, c2 = st.columns(2)
district = c1.selectbox(t("District"), DISTRICTS)
season_label = c2.selectbox(t("Season"), [t(lbl) for lbl, _ in SEASONS])
scode = SEASON_CODE[season_label]

if st.button(t("Assess Risk"), type="primary"):
    r = rain[(rain.district == district) & (rain.season == scode)]
    rain_a = float(r.rainfall_anomaly.iloc[-1]) if len(r) else float(rain.rainfall_anomaly.mean())
    cpi_c = float(cpi.cpi_change.dropna().iloc[-1]); fert_c = float(fert.fert_change.dropna().iloc[-1])
    if model is not None:
        X = pd.DataFrame([[rain_a, cpi_c, fert_c]], columns=["rainfall_anomaly", "cpi_change", "fert_change"])
        level = str(model.predict(X)[0]); conf = f"{model.predict_proba(X).max()*100:.0f}% {t('confidence')}"
    else:
        level = label_risk(rain_a, cpi_c, fert_c); conf = "rule-based"
    log_risk(district, scode, rain_a, cpi_c, fert_c, level)
    color = {"High": "#DC2626", "Medium": "#D97706", "Low": "#40916C"}[level]

    # risk hero card
    st.markdown(f"""<div class="ar-card" style="border-left:5px solid {color}">
      <div class="ar-label">{district} &middot; {season_label}</div>
      <div style="display:flex;align-items:baseline;gap:14px;margin-top:6px">
        <span class="ar-num" style="color:{color}">{t(level + ' risk')}</span>
        <span style="color:#5E7065;font-size:12.5px;font-family:'JetBrains Mono',monospace">{conf}</span>
      </div>
      <div style="color:#5E7065;font-size:13.5px;margin-top:8px;max-width:46em">{t('Risk means how likely staple food prices are to rise sharply over the coming months, predicted from pre-season conditions.')}</div>
    </div>""", unsafe_allow_html=True)

    # drivers as a stat row
    driving = t("What's driving this")
    st.markdown(f"<div class='ar-label' style='margin:18px 0 -4px'>{driving}</div>",
                unsafe_allow_html=True)
    st.markdown(f"""<div class="ar-grid">
      <div class="ar-card"><div class="ar-label">{t('Rainfall compared to normal')}</div>
        <div class="ar-num">{rain_a:+.2f}<small style="font-size:14px;color:#5E7065"> &sigma;</small></div></div>
      <div class="ar-card"><div class="ar-label">{t('Food price pressure (CPI)')}</div>
        <div class="ar-num">{cpi_c:+.1f}<small style="font-size:15px;color:#5E7065">%</small></div></div>
      <div class="ar-card"><div class="ar-label">{t('Fertilizer cost pressure')}</div>
        <div class="ar-num">{fert_c:+.1f}<small style="font-size:15px;color:#5E7065">%</small></div></div>
    </div>""", unsafe_allow_html=True)

    advice = t({"High": "High risk. Food prices likely to climb. Advise storing harvest, budgeting for higher input costs, and conservative spending.",
                "Medium": "Moderate risk. Monitor markets and weather; plan inputs carefully.",
                "Low": "Lower risk. Prices likely stable. Normal planting and input investment is reasonable."}[level])
    st.markdown(f"""<div style="background:#fff;border:1px solid #DED7C4;border-left:4px solid {color};
      border-radius:12px;padding:14px 18px;margin-top:6px">
      <div class="ar-label" style="color:{color}">{t('Advice')}</div>
      <div style="margin-top:5px;font-size:15px;color:#1C2A22">{advice}</div></div>""", unsafe_allow_html=True)
else:
    st.info(t("Pick a district and season, then click **Assess Risk**."))

