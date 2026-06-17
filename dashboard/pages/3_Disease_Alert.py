"""Disease Alert, live Open-Meteo weather + FAO rules (offline fallback)."""
from _ui import setup
from _i18n import t, crop_label
import streamlit as st
from config.settings import DISTRICT_COORDS, CROPS
from src.models.disease_alert import assess_crop, get_all_alerts

setup("Disease Alert", "Crop disease warnings from the local weather", allowed_roles=("officer", "super_admin"))
district = st.selectbox(t("District"), list(DISTRICT_COORDS))

if st.button(t("Check Risk"), type="primary"):
    lat, lon = DISTRICT_COORDS[district]
    try:
        alerts = get_all_alerts(lat, lon, CROPS); st.caption(t("Live 14-day weather forecast."))
    except Exception:
        sample = {"temperature_2m_min": [17]*14, "temperature_2m_max": [23]*14,
                  "relative_humidity_2m_mean": [90]*14, "precipitation_sum": [6]*14}
        alerts = [a for c in CROPS for a in assess_crop(c, sample)]
        st.caption(t("Offline mode: showing a sample forecast."))
    if not alerts:
        st.success(t("No elevated disease risk for the forecast window."))
    for a in alerts:
        color = {"High": "#DC2626", "Medium": "#D97706"}.get(a["risk"], "#40916C")
        why = a["why"]
        tick = lambda b: "✓" if b else "✗"
        triggers = (f"temp {tick(why.get('temperature'))} &middot; "
                    f"humidity {tick(why.get('humidity'))} &middot; "
                    f"{why.get('rainy_days', 0)} rainy days")
        st.markdown(f"""<div class="ar-card" style="border-left:5px solid {color};margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
            <div><div class="ar-label">{crop_label(a['crop'])}</div>
              <div style="font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:19px;color:#1B4332">{a['disease']}</div></div>
            <span class="ar-badge" style="background:{color};white-space:nowrap">{t(a['risk'])}</span>
          </div>
          <div style="margin-top:10px;font-size:14.5px;color:#1C2A22"><b style="color:{color}">{t('Action:')}</b> {a['action']}</div>
          <div style="margin-top:6px;font-size:12px;color:#5E7065;font-family:'JetBrains Mono',monospace">{t('Triggers:')} {triggers}</div>
        </div>""", unsafe_allow_html=True)
else:
    st.info(t("Pick a district and click **Check Risk**."))

