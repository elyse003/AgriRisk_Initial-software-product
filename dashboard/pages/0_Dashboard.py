"""Dashboard hub, a card for each tool. This page (and the tools) keep the sidebar.

Reached from the landing page's "Open the dashboard" button.
"""
from _ui import setup
from _i18n import t
import streamlit as st

user = setup("Dashboard", "Choose a tool to get started")

# (title, page URL, description, accent colour, season stage)
ALL_TOOLS = [
    ("Price Forecast", "/Price_Forecast", "Next-month price outlook by crop and district.", "#2D6A4F", "At selling"),
    ("Seasonal Risk", "/Seasonal_Risk", "Planting risk from rainfall, food inflation and fertilizer cost.", "#C76E1B", "Before planting"),
    ("Disease Alert", "/Disease_Alert", "Crop disease warnings from the live weather forecast.", "#DC2626", "While growing"),
    ("Input Recommender", "/Input_Recommender", "A fertilizer plan sized to your land and budget.", "#7C3AED", "At planting"),
]

# Farmers get a limited view: a welcome note pointing them to the chat assistant
# (the analytical tools are for extension officers).
if user["role"] == "farmer":
    st.info(f"{t('Welcome')}, {user['name']}. " + t(
        "The full dashboard is for extension officers. Tap the chat button (bottom-right), "
        "or open USSD Preview to try the *384# menu, both answer price, risk, disease and "
        "input questions."))
    TOOLS = []
else:
    TOOLS = ALL_TOOLS

cards = "".join(
    f'''<a class="tool-card" href="{url}" target="_self">
        <div class="tc-stage" style="color:{color}">{t(stage)}</div>
        <div class="tc-title">{t(title)}</div>
        <div class="tc-desc">{t(desc)}</div>
        <div class="tc-go" style="color:{color}">{t("Open")} &rarr;</div>
    </a>''' for title, url, desc, color, stage in TOOLS)

st.markdown(f"""<style>
.tool-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;margin-top:26px}}
@media(max-width:760px){{.tool-grid{{grid-template-columns:1fr}}}}
.tool-card{{display:block;background:#fff;border:1px solid #DED7C4;border-radius:16px;
  padding:24px;text-decoration:none !important;transition:transform .14s ease, box-shadow .14s ease}}
.tool-card:hover{{transform:translateY(-3px);box-shadow:0 14px 34px rgba(27,67,50,.10)}}
.tc-stage{{font-family:'Geist',sans-serif;font-size:11px;letter-spacing:.12em;text-transform:uppercase}}
.tc-title{{font-family:'Geist',sans-serif;font-weight:600;font-size:21px;color:#1B4332;margin:6px 0 6px}}
.tc-desc{{color:#5E7065;font-size:14.5px;line-height:1.5}}
.tc-go{{margin-top:14px;font-weight:600;font-size:14px}}
</style>
<div class="tool-grid">{cards}</div>""", unsafe_allow_html=True)
