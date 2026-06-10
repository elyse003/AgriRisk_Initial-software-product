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

CSS = f"""
<style>
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display:none; }}
.block-container {{ padding-top: 2rem; max-width: 1050px; }}
section[data-testid="stSidebar"] {{ background: {FOREST}; }}
section[data-testid="stSidebar"] * {{ color: #D8F3DC; }}
section[data-testid="stSidebar"] a {{ border-radius: 8px; }}
h1, h2, h3 {{ color: {FOREST}; }}
.ar-head {{ font-size: 26px; font-weight: 800; color: {FOREST}; }}
.ar-sub {{ color: {MUT}; font-size: 14px; margin-bottom: 6px; }}
.ar-grid {{ display:flex; gap:14px; flex-wrap:wrap; margin:14px 0; }}
.ar-card {{ background:#fff; border:1px solid {BRD}; border-radius:12px; padding:18px 20px;
           box-shadow:0 1px 3px rgba(0,0,0,.04); flex:1; min-width:150px; }}
.ar-num {{ font-size:30px; font-weight:800; }}
.ar-lbl {{ color:{MUT}; font-size:13px; margin-top:2px; }}
.ar-alert {{ background:#FFF8EC; border:1px solid #FDE68A; border-radius:12px; padding:16px 18px; }}
.ar-alert b {{ color:#92400E; }} .ar-alert .t {{ color:#92400E; font-weight:700; margin-bottom:6px; }}
.ar-alert p {{ color:#B45309; font-size:13.5px; margin:4px 0; }}
.ar-pill {{ display:inline-block; background:{G50}; border:1px solid {BRD}; color:{EMERALD};
           border-radius:16px; padding:5px 13px; font-size:12px; font-weight:600; margin:3px; }}
.ar-badge {{ padding:4px 14px; border-radius:20px; font-size:13px; font-weight:700; color:#fff; }}
.ar-label {{ font-size:11px; font-weight:700; color:{MUT}; letter-spacing:.1em; text-transform:uppercase; }}
.stButton>button {{ font-weight:700; border-radius:8px; }}
</style>
"""


LOGO_PATH = os.path.join(ROOT, "assets", "logo.png")


def setup(title, subtitle):
    st.set_page_config(page_title="AgriRisk Rwanda", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    try:
        st.logo(LOGO_PATH, size="large")
    except Exception:
        st.sidebar.image(LOGO_PATH)
    st.sidebar.markdown("---")
    st.markdown(f"<div class='ar-head'>{title}</div><div class='ar-sub'>{subtitle}</div>",
                unsafe_allow_html=True)


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
