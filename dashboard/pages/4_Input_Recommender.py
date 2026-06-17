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
        cards = ""
        for i, (_, r) in enumerate(plan.iterrows()):
            badge = (f"<span class='ar-badge' style='background:#7C3AED;font-size:10px'>{t('AT PLANTING')}</span>"
                     if i == 0 else "")
            cards += (
                f'<div class="ar-card" style="flex:1;min-width:200px">{badge}'
                f'<div class="ar-label" style="margin-top:{"8px" if i == 0 else "0"}">{r["when"]}</div>'
                f'<div style="font-family:\'Bricolage Grotesque\',sans-serif;font-weight:700;font-size:18px;color:#1B4332;margin:4px 0">{r.fertilizer}</div>'
                f'<div class="ar-num" style="font-size:26px">{int(r.bags_50kg)}<small style="font-size:13px;color:#5E7065"> {t("bag(s)")}</small></div>'
                f'<div class="ar-lbl">{int(r.need_kg)} kg {t("needed")} &middot; {int(r.rate_kg_ha)} kg/ha</div>'
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-weight:700;color:#C76E1B;margin-top:8px;font-size:15px">{int(r.line_cost):,} RWF</div>'
                f'</div>')
        st.markdown(f"<div class='ar-grid'>{cards}</div>", unsafe_allow_html=True)

        tcolor = "#2D6A4F" if ok else "#D97706"
        msg = (t("Total for {land:g} ha: {total:,} RWF, within budget, {remaining:,} RWF to spare.")
               .format(land=land, total=total, remaining=remaining) if ok else
               t("Total for {land:g} ha: {total:,} RWF, over budget by {extra:,} RWF. Use the subsidised "
                 "Smart Nkunganire price, buy in stages, or start with a smaller area.")
               .format(land=land, total=total, extra=-remaining))
        st.markdown(f"""<div style="background:#fff;border:1px solid #DED7C4;border-left:4px solid {tcolor};
          border-radius:12px;padding:14px 18px;margin-top:8px">
          <div class="ar-num" style="font-size:24px;color:{tcolor}">{total:,}<small style="font-size:13px;color:#5E7065"> RWF</small></div>
          <div style="margin-top:4px;font-size:14px;color:#1C2A22">{msg}</div></div>""", unsafe_allow_html=True)
        st.caption(t("Rates follow MINAGRI/RAB recommendations and should be confirmed with soil testing and "
                     "local extension advice. Prices are subsidised (Smart Nkunganire System)."))
else:
    st.info(t("Set crop, land size and budget, then click **Build Fertilizer Plan**."))

