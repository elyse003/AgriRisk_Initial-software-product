"""AgriRisk Rwanda — the landing page IS the app home.

Renders landing/index.html (the same file published to GitHub Pages) inside the
Streamlit app so the homepage and the dashboard are one product. The sidebar
still gives access to the tools; the landing's "Open the dashboard" buttons jump
to the Price Forecast page.

Run: streamlit run dashboard/Home.py
"""
from _ui import CSS, LOGO_PATH, ROOT
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(page_title="AgriRisk Rwanda", layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)
# let the landing fill the whole content area (drop Streamlit's padding / max-width)
st.markdown(
    "<style>.block-container,[data-testid='stMainBlockContainer']"
    "{padding:0 !important;max-width:100% !important}</style>",
    unsafe_allow_html=True)
try:
    st.logo(LOGO_PATH, size="large")
except Exception:
    st.sidebar.image(LOGO_PATH)

html = (Path(ROOT) / "landing" / "index.html").read_text(encoding="utf-8")
# Inside the app, the "Open the dashboard" CTA opens the first tool page.
# Streamlit's component iframe is sandboxed without top-navigation, so we open
# the tool in a new tab (allow-popups + allow-same-origin make the root-relative
# /Price_Forecast resolve against the app's own origin, locally and on cloud).
html = html.replace(
    'href="https://agririskinitial-software-appuct-nedmfzzrbgaz7jhb3c74jd.streamlit.app"',
    'href="/Price_Forecast" target="_blank"')
components.html(html, height=3300, scrolling=True)