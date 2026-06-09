"""Screen: Disease Alert. Calls Open-Meteo live; falls back to a sample forecast
if offline so the screen always renders for a demo."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../.."))

import streamlit as st

from src.models.disease_alert import assess_crop, get_all_alerts
from config.settings import DISTRICT_COORDS as COORDS, CROPS

st.set_page_config(page_title="Disease Alert", page_icon="🦠")
st.title("🦠 Disease Alert")

district = st.selectbox("District", list(COORDS))

if st.button("Check disease risk", type="primary"):
    lat, lon = COORDS[district]
    try:
        alerts = get_all_alerts(lat, lon, CROPS)
        st.caption("Live 14-day forecast via Open-Meteo.")
    except Exception:
        # offline fallback: a sample high-humidity forecast
        sample = {
            "temperature_2m_min": [17] * 14, "temperature_2m_max": [23] * 14,
            "relative_humidity_2m_mean": [92] * 14, "precipitation_sum": [6] * 14,
        }
        alerts = []
        for c in CROPS:
            alerts.extend(assess_crop(c, sample))
        st.caption("⚠️ Offline — showing a sample high-humidity forecast.")

    if not alerts:
        st.success("No elevated disease risk detected for the forecast window.")
    for a in alerts:
        badge = {"High": "🔴", "Medium": "🟡"}.get(a["risk"], "🟢")
        with st.container(border=True):
            st.markdown(f"### {badge} {a['crop'].title()} — {a['disease']}  ({a['risk']} risk)")
            st.write(f"**Recommended action:** {a['action']}")
            st.caption(f"Triggers: {a['why']}")
else:
    st.info("Select a district and click **Check disease risk**.")
