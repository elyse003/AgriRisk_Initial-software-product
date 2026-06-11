"""Input Recommender — affordable inputs by crop/district/budget (real MINAGRI prices)."""
from _ui import setup
from src.db.connection import fetch_catalogue
import streamlit as st
from config.settings import CROPS, DISTRICTS
from src.models.input_recommender import recommend

setup("Input Recommender", "MINAGRI data · Budget-smart ranking · RWF")
cat = fetch_catalogue()

c1, c2 = st.columns(2)
crop = c1.selectbox("Crop", CROPS, format_func=str.title)
district = c2.selectbox("District", DISTRICTS)
budget = st.slider("Farmer budget (RWF)", 10000, 150000, 60000, 5000)

if st.button("Get Recommendations", type="primary"):
    recs = recommend(cat, crop, district, float(budget))
    if recs.empty:
        st.warning("No inputs match that crop within budget. Try increasing the budget.")
    else:
        cols = st.columns(len(recs))
        for i, (_, r) in enumerate(recs.iterrows()):
            with cols[i]:
                with st.container(border=True):
                    if i == 0:
                        st.markdown("<span class='ar-badge' style='background:#7C3AED;font-size:10px'>BEST MATCH</span>", unsafe_allow_html=True)
                    st.markdown(f"**{r.input_name}**")
                    st.caption(f"{r.input_type} · {r.supplier}")
                    st.markdown(f"### {int(r.price_rwf):,} RWF")
        st.info(f"Top {len(recs)} · total {int(recs.price_rwf.sum()):,} RWF · "
                f"{budget - int(recs.price_rwf.sum()):,} RWF left of budget.")
else:
    st.info("Set crop, district and budget, then click **Get Recommendations**.")
