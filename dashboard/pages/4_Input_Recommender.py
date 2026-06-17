"""Input Recommender, a fertilizer plan sized to the farmer's land (real MINAGRI prices)."""
from _ui import setup
from _i18n import t, crop_label
from src.db.connection import fetch_catalogue
import streamlit as st
from config.settings import CROPS, DISTRICTS
from src.models.input_recommender import recommend_plan

setup("Input Recommender", "Fertilizer plan for your land and budget", allowed_roles=("officer", "super_admin"))
cat = fetch_catalogue()

c1, c2 = st.columns(2)
crop = c1.selectbox(t("Crop"), CROPS, format_func=crop_label)
district = c2.selectbox(t("District"), DISTRICTS)
c3, c4 = st.columns(2)
land = c3.number_input(t("Land size (hectares)"), min_value=0.05, max_value=10.0, value=0.5, step=0.05,
                       help="1 hectare = 100 ares (1 are = 10m x 10m).")
budget = c4.slider(t("Budget (RWF)"), 10000, 300000, 80000, 5000)

if st.button(t("Build Fertilizer Plan"), type="primary"):
    plan, total, ok, remaining = recommend_plan(cat, crop, float(land), float(budget))
    if plan.empty:
        st.warning(t("No fertilizer plan is defined for that crop yet."))
    else:
        cols = st.columns(len(plan))
        for i, (_, r) in enumerate(plan.iterrows()):
            with cols[i]:
                with st.container(border=True):
                    if i == 0:
                        st.markdown(f"<span class='ar-badge' style='background:#7C3AED;font-size:10px'>{t('AT PLANTING')}</span>",
                                    unsafe_allow_html=True)
                    st.markdown(f"**{r.fertilizer}**")
                    st.caption(r["when"])
                    st.markdown(f"### {int(r.bags_50kg)} {t('bag(s)')}")
                    st.caption(f"{int(r.need_kg)} kg {t('needed')} · {int(r.rate_kg_ha)} kg/ha")
                    st.markdown(f"{int(r.line_cost):,} RWF")
        if ok:
            st.success(t("Total for {land:g} ha: {total:,} RWF, within budget, {remaining:,} RWF to spare.")
                       .format(land=land, total=total, remaining=remaining))
        else:
            st.warning(t("Total for {land:g} ha: {total:,} RWF, over budget by {extra:,} RWF. Use the subsidised "
                         "Smart Nkunganire price, buy in stages, or start with a smaller area.")
                       .format(land=land, total=total, extra=-remaining))
        st.caption(t("Rates follow MINAGRI/RAB recommendations and should be confirmed with soil testing and "
                     "local extension advice. Prices are subsidised (Smart Nkunganire System)."))
else:
    st.info(t("Set crop, land size and budget, then click **Build Fertilizer Plan**."))

