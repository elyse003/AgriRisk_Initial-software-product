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
        with st.container(border=True):
            st.markdown(f"**{crop_label(a['crop'])}: {a['disease']}** "
                        f"<span class='ar-badge' style='background:{color}'>{t(a['risk'])}</span>", unsafe_allow_html=True)
            st.write(f"**{t('Action:')}** {a['action']}")
            st.caption(f"{t('Triggers:')} {a['why']}")
else:
    st.info(t("Pick a district and click **Check Risk**."))

