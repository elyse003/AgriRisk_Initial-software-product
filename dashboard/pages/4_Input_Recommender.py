"""Screen: Input Recommender. Ranks affordable inputs by crop/district/budget."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../.."))

import pandas as pd
import streamlit as st

from config.settings import DATA_RAW, data_path
from src.models.input_recommender import recommend

st.set_page_config(page_title="Input Recommender", page_icon="🛒")
st.title("🛒 Input Recommender")


@st.cache_data
def load_catalogue():
    return pd.read_csv(data_path("minagri_input_prices.csv"))


cat = load_catalogue()
c1, c2 = st.columns(2)
crop = c1.selectbox("Crop", ["maize", "beans", "potatoes"])
district = c2.selectbox("District", sorted(cat.district.unique()))
budget = st.slider("Budget (RWF)", 10_000, 150_000, 50_000, 5_000)

if st.button("Get recommendations", type="primary"):
    recs = recommend(cat, crop, district, float(budget))
    if recs.empty:
        st.warning("No inputs match that crop within the budget. Try increasing the budget.")
    else:
        for _, r in recs.iterrows():
            with st.container(border=True):
                st.markdown(f"### {r.input_name}  ·  {int(r.price_rwf):,} RWF")
                st.write(f"**Type:** {r.input_type}  |  **Supplier:** {r.supplier} ({r.district})")
                st.caption(f"Match score: {r.match_score:.2f}  ·  "
                           f"{r.pct_saving:+.0f}% vs district average")
        spent = int(recs.price_rwf.sum())
        st.info(f"Top {len(recs)} inputs · total {spent:,} RWF · "
                f"{budget - spent:,} RWF remaining of budget.")
else:
    st.info("Set crop, district and budget, then click **Get recommendations**.")
