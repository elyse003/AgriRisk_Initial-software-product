"""Dashboard hub, a card for each tool. This page (and the tools) keep the sidebar.

Reached from the landing page's "Open the dashboard" button.
"""
from _ui import setup, open_chat
from _i18n import t
import streamlit as st

user = setup("Dashboard", "Choose a tool to get started", header=False)

# Farmers don't use the analytical tools — open the assistant as their home, filling
# the page (no empty tool grid). setup() suppresses the floating chat for farmers.
if user["role"] == "farmer":
    open_chat(user.get("name", ""))
    st.stop()

# --- Officers / admin: the tool hub ---
st.markdown(f"<div class='ar-head'>{t('Dashboard')}</div>"
            f"<div class='ar-sub'>{t('Choose a tool to get started')}</div>", unsafe_allow_html=True)

# (title, page file, description, accent colour, season stage). The page file is
# used with st.page_link so a card click navigates client-side (like the sidebar).
TOOLS = [
    ("Price Forecast", "pages/1_Price_Forecast.py", "Next-month price outlook by crop and district.", "#2D6A4F", "At selling"),
    ("Seasonal Risk", "pages/2_Seasonal_Risk.py", "Planting risk from rainfall, food inflation and fertilizer cost.", "#C76E1B", "Before planting"),
    ("Disease Alert", "pages/3_Disease_Alert.py", "Crop disease warnings from the live weather forecast.", "#DC2626", "While growing"),
    ("Input Recommender", "pages/4_Input_Recommender.py", "A fertilizer plan sized to your land and budget.", "#7C3AED", "At planting"),
]

st.markdown("""<style>
/* each card is a keyed st.container; style it to match the old tool-card look */
div[class*="st-key-toolcard"]{ background:#fff; border:1px solid #DED7C4; border-radius:16px;
  padding:22px 24px; margin-top:18px; transition:transform .14s ease, box-shadow .14s ease; }
div[class*="st-key-toolcard"]:hover{ transform:translateY(-3px); box-shadow:0 14px 34px rgba(27,67,50,.10); }
.tc-stage{ font-size:11px; letter-spacing:.12em; text-transform:uppercase; font-weight:600; }
.tc-title{ font-weight:600; font-size:21px; color:#1B4332; margin:6px 0 6px; letter-spacing:-.01em; }
.tc-desc{ color:#5E7065; font-size:14.5px; line-height:1.5; margin-bottom:6px; }
/* the page_link rendered as the card's "Open" action */
div[class*="st-key-toolcard"] a[data-testid="stPageLink-NavLink"]{ padding:2px 0; font-weight:600; font-size:14px; }
div[class*="st-key-toolcard"] a[data-testid="stPageLink-NavLink"] p{ font-weight:600; }
</style>""", unsafe_allow_html=True)

# two-per-row grid of cards; st.page_link keeps the login session on click
for i in range(0, len(TOOLS), 2):
    cols = st.columns(2, gap="medium")
    for col, (title, page_file, desc, color, stage) in zip(cols, TOOLS[i:i + 2]):
        card = col.container(key=f"toolcard_{title.replace(' ', '')}")
        card.markdown(
            f"<div class='tc-stage' style='color:{color}'>{t(stage)}</div>"
            f"<div class='tc-title'>{t(title)}</div>"
            f"<div class='tc-desc'>{t(desc)}</div>", unsafe_allow_html=True)
        card.page_link(page_file, label=t("Open"), icon=":material/arrow_forward:")
