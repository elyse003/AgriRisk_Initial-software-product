"""Shared helpers for the AgriRisk Streamlit dashboard: path fix, CSS theme
(matching the JSX design), cached real-data loaders, and small HTML card helpers.
"""
import os
import sys
import pickle

# --- make the project root importable from any page ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pandas as pd
import streamlit as st

from config.settings import CROPS, DISTRICTS, DISTRICT_COORDS, MODELS_STORE, data_path

# JSX design tokens
FOREST = "#1B4332"; EMERALD = "#2D6A4F"; G600 = "#40916C"; G50 = "#EDF7F0"
AMBER = "#D97706"; RED = "#DC2626"; PURPLE = "#7C3AED"; MUT = "#5A7A6A"; BRD = "#E0F0E4"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;700&display=swap');
:root{ --forest:#1B4332; --emerald:#2D6A4F; --harvest:#C76E1B; --paper:#F6F2E8; --ink:#1C2A22; --mut:#5E7065; --line:#DED7C4; }
/* Hide the menu / Deploy / decoration, but keep the toolbar itself so the
   sidebar reopen arrow survives on mobile (where the sidebar can collapse). */
#MainMenu, footer, [data-testid="stToolbarActions"], [data-testid="stDecoration"] { display:none; }
.stApp { background: var(--paper); }
html, body, [class*="css"] { font-family:'Inter',sans-serif; color:var(--ink); }
.block-container { padding-top: 2rem; max-width: 1050px; }
section[data-testid="stSidebar"] { background: var(--forest); }
section[data-testid="stSidebar"] * { color:#D8F3DC; }
section[data-testid="stSidebar"] a { border-radius:8px; }
/* Desktop: pin the sidebar open so it can't vanish; hide its collapse button. */
@media (min-width: 769px) {
  section[data-testid="stSidebar"] {
    transform: none !important; visibility: visible !important;
    margin-left: 0 !important; min-width: 300px !important;
  }
  [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] { display:none !important; }
}
/* Mobile/tablet: let the sidebar collapse to an overlay so it doesn't blanket
   the page; Streamlit's own close / reopen controls stay usable. */
@media (max-width: 768px) {
  section[data-testid="stSidebar"] { min-width: 0 !important; }
}
h1,h2,h3,.ar-head { font-family:'Bricolage Grotesque',sans-serif; color:var(--forest); letter-spacing:-.02em; }
.ar-head { font-size:30px; font-weight:800; }
.ar-sub { color:var(--mut); font-size:13px; margin-bottom:6px; font-family:'JetBrains Mono',monospace; letter-spacing:.02em; }
.ar-grid { display:flex; gap:14px; flex-wrap:wrap; margin:16px 0; }
.ar-card { background:#fff; border:1px solid var(--line); border-radius:16px; padding:20px 22px;
           box-shadow:0 1px 2px rgba(27,67,50,.04); flex:1; min-width:150px; }
.ar-num { font-family:'JetBrains Mono',monospace; font-size:30px; font-weight:700; letter-spacing:-.02em; }
.ar-lbl { color:var(--mut); font-size:13px; margin-top:2px; }
.ar-alert { background:#FCF3E5; border:1px solid #F0DBBE; border-radius:16px; padding:16px 18px; }
.ar-alert b { color:#9A4D10; } .ar-alert .t { color:#9A4D10; font-weight:700; margin-bottom:6px; font-family:'Bricolage Grotesque',sans-serif; }
.ar-alert p { color:#B45309; font-size:13.5px; margin:4px 0; }
.ar-pill { display:inline-block; background:#fff; border:1px solid var(--line); color:var(--emerald);
           border-radius:30px; padding:6px 15px; font-size:12.5px; font-weight:500; margin:3px; font-family:'JetBrains Mono',monospace; }
.ar-badge { padding:4px 14px; border-radius:20px; font-size:13px; font-weight:700; color:#fff; }
.ar-label { font-size:11px; font-weight:700; color:var(--mut); letter-spacing:.12em; text-transform:uppercase; font-family:'JetBrains Mono',monospace; }
.stButton>button { font-weight:600; border-radius:9px; background:var(--forest); color:#fff; border:none; }
.stButton>button:hover { background:#15392a; color:#fff; }
[data-testid="stMetricValue"] { font-family:'JetBrains Mono',monospace; color:var(--forest); }
</style>
"""


LOGO_PATH = os.path.join(ROOT, "assets", "logo.png")


def setup(title, subtitle):
    # "auto": expanded on desktop (pinned open by the CSS), collapsed on mobile
    # so the sidebar doesn't blanket the screen.
    st.set_page_config(page_title="AgriRisk Rwanda", layout="wide", initial_sidebar_state="auto")
    st.markdown(CSS, unsafe_allow_html=True)
    try:
        st.logo(LOGO_PATH, size="large")
    except Exception:
        st.sidebar.image(LOGO_PATH)
    st.sidebar.markdown("---")
    st.markdown(f"<div class='ar-head'>{title}</div><div class='ar-sub'>{subtitle}</div>",
                unsafe_allow_html=True)


GITHUB_URL = "https://github.com/elyse003/AgriRisk_Initial-software-product"


def footer():
    """Render the shared site footer. Call at the end of a page (after setup)."""
    st.markdown(f"""<style>
.ar-foot {{ margin-top:56px; padding-top:30px; border-top:1px solid var(--line); color:var(--mut); font-size:13.5px; }}
.ar-foot a {{ color:var(--mut) !important; text-decoration:none !important; }}
.ar-foot a:hover {{ color:var(--forest) !important; }}
.ar-foot-grid {{ display:flex; flex-wrap:wrap; gap:28px 48px; justify-content:space-between; }}
.ar-foot-brand {{ max-width:24em; }}
.ar-foot .fb {{ display:flex; align-items:center; gap:9px; font-family:'Bricolage Grotesque',sans-serif;
                font-weight:800; font-size:17px; color:var(--forest); }}
.ar-foot .fb .seed {{ width:18px; height:18px; border-radius:50% 50% 50% 0; background:var(--emerald);
                      transform:rotate(-45deg); }}
.ar-foot .fcol h5 {{ font-family:'JetBrains Mono',monospace; font-size:11px; letter-spacing:.12em;
                     text-transform:uppercase; color:var(--harvest); margin-bottom:10px; font-weight:700; }}
.ar-foot .fcol a, .ar-foot .fcol span {{ display:block; margin:6px 0; }}
.ar-foot-bottom {{ margin-top:26px; padding-top:16px; border-top:1px solid var(--line); display:flex;
                   justify-content:space-between; flex-wrap:wrap; gap:8px; font-size:12.5px; }}
</style>
<div class="ar-foot">
  <div class="ar-foot-grid">
    <div class="ar-foot-brand">
      <div class="fb"><span class="seed"></span>AgriRisk Rwanda</div>
      <p style="margin-top:10px">Machine-learning decision support for Rwandan agriculture — price
      forecasts, seasonal risk, disease alerts and input plans for maize, beans and Irish potatoes
      across all 30 districts, in Kinyarwanda and English.</p>
    </div>
    <div class="fcol"><h5>Tools</h5>
      <a href="/Price_Forecast" target="_self">Price Forecast</a>
      <a href="/Seasonal_Risk" target="_self">Seasonal Risk</a>
      <a href="/Disease_Alert" target="_self">Disease Alert</a>
      <a href="/Input_Recommender" target="_self">Input Recommender</a>
    </div>
    <div class="fcol"><h5>Data</h5>
      <span>WFP market prices</span>
      <span>World Bank CPI &amp; fertilizer</span>
      <span>CHIRPS rainfall</span>
      <span>Open-Meteo &middot; MINAGRI</span>
    </div>
    <div class="fcol"><h5>Project</h5>
      <a href="/" target="_self">Home</a>
      <a href="/Dashboard" target="_self">Dashboard</a>
      <a href="{GITHUB_URL}" target="_blank">GitHub</a>
    </div>
  </div>
  <div class="ar-foot-bottom">
    <span>&copy; 2026 AgriRisk Rwanda &middot; BSc Software Engineering capstone</span>
    <span>Decision support only — confirm with local extension advice.</span>
  </div>
</div>""", unsafe_allow_html=True)


# ---------------- cached real-data loaders (prefer data/processed) ----------------
@st.cache_data
def load_prices():
    return pd.read_csv(data_path("wfp_food_prices_rwanda.csv"), parse_dates=["date"])

@st.cache_data
def load_cpi():
    df = pd.read_csv(data_path("rwanda_food_cpi.csv"), parse_dates=["date"]).sort_values("date")
    df["cpi_change"] = df["food_cpi"].pct_change(12) * 100
    return df

@st.cache_data
def load_fert():
    df = pd.read_csv(data_path("fertilizer_price_index.csv"), parse_dates=["date"]).sort_values("date")
    df["fert_change"] = df["fert_index"].pct_change(12) * 100
    return df

@st.cache_data
def load_rainfall():
    return pd.read_csv(data_path("district_rainfall_anomalies.csv"), parse_dates=["date"])

@st.cache_data
def load_catalogue():
    return pd.read_csv(data_path("minagri_input_prices.csv"))

@st.cache_data
def load_metrics():
    import json
    p = MODELS_STORE / "metrics.json"
    return json.load(open(p)) if p.exists() else {}

@st.cache_resource
def load_risk_model():
    p = MODELS_STORE / "risk_classifier.pkl"
    return pickle.load(open(p, "rb")) if p.exists() else None

@st.cache_resource
def load_price_forecaster():
    """dict {crop: fitted model} trained by scripts/train_models.py, or None."""
    p = MODELS_STORE / "price_forecaster.pkl"
    return pickle.load(open(p, "rb")) if p.exists() else None

@st.cache_data(ttl=300)
def load_last_updated():
    """How current each series is. Reads data/processed/last_updated.json, written
    by the refresh script; falls back to the latest date inside each processed file."""
    import json
    from config.settings import DATA_PROCESSED
    status_file = DATA_PROCESSED / "last_updated.json"
    if status_file.exists():
        try:
            return json.loads(status_file.read_text())
        except Exception:
            pass
    out = {}
    files = {"wfp_prices": "wfp_food_prices_rwanda.csv", "cpi": "rwanda_food_cpi.csv",
             "fertilizer": "fertilizer_price_index.csv", "rainfall": "district_rainfall_anomalies.csv"}
    for key, fname in files.items():
        p = DATA_PROCESSED / fname
        if p.exists():
            try:
                d = pd.read_csv(p, parse_dates=["date"])
                out[key] = {"data_through": d["date"].max().strftime("%Y-%m")}
            except Exception:
                pass
    return out
