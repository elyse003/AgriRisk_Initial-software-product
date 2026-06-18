"""Input Recommender, a fertilizer plan sized to the farmer's land (real MINAGRI prices).

Rendered in the "Officer console" editorial style: a serif headline, the land-sized
plan shown as ranked recommendation cards (with a budget verdict), and the rest of
the catalogue suitable for the crop as an "other matches" table.
"""
from _ui import setup, page_header
from _i18n import t, crop_label
from src.db.connection import fetch_catalogue
import streamlit as st
from config.settings import CROPS, DISTRICTS
from src.models.input_recommender import recommend_plan

setup("Input Recommender", "Fertilizer plan for your land and budget",
      allowed_roles=("officer", "super_admin"), header=False)
cat = fetch_catalogue()

page_header(
    f"MODULE 04 · {t('Input Recommender').upper()}",
    f"<em>{t('Affordable inputs')}</em> · {t('your land and budget')}",
    t("MINAGRI input prices sized to your land using MINAGRI/RAB application rates, "
      "then priced against your budget. Limited to the few inputs that matter — per "
      "Lobell et al. (2020) on decision paralysis."),
    meta_strong=f"{len(cat)} {t('items')}", meta_sub="MINAGRI · Smart Nkunganire")

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
        st.stop()

    # ---- ranked recommendation cards (the plan stages) ----
    cards = ""
    for i, (_, r) in enumerate(plan.iterrows()):
        r1 = " r1" if i == 0 else ""
        cards += f"""<div class="ag-rank{r1}">
          <div class="tag">{t('RANK')} {i+1:02d}</div>
          <div class="cat">{r['when'].upper()}</div>
          <div class="nm">{r['fertilizer']}</div>
          <div style="font-size:12.5px;color:var(--ag-ink-soft);line-height:1.5;min-height:34px">
            {int(r['need_kg'])} kg {t('needed')} · {int(r['rate_kg_ha'])} kg/ha · {int(r['bags_50kg'])} × 50kg {t('bag(s)')}</div>
          <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-top:12px">
            <div><div class="price">{int(r['line_cost']):,}</div>
              <div style="font-family:var(--f-mono);font-size:10.5px;color:var(--ag-mute);margin-top:4px">RWF · {int(r['bags_50kg'])} {t('bag(s)')}</div></div>
            <div style="text-align:right"><div style="font-family:var(--f-mono);font-size:11px;color:var(--ag-mute)">{t('PER BAG')}</div>
              <div style="font-family:var(--f-serif);font-size:20px;color:var(--ag-ink)">{int(r['price_per_bag']):,}</div></div>
          </div></div>"""
    st.markdown(f"<div class='kicker ag-pagein' style='margin-bottom:10px'>{t('RECOMMENDED')} · {t('TOP')} {len(plan)}</div>",
                unsafe_allow_html=True)
    st.markdown(f"<div class='ag-pagein' style='display:grid;grid-template-columns:repeat({min(len(plan),3)},1fr);gap:14px;margin-bottom:22px'>{cards}</div>",
                unsafe_allow_html=True)

    # ---- budget verdict ----
    note_bg = "var(--ag-sage-bg)" if ok else "var(--ag-terra-bg)"
    note_col = "var(--ag-sage)" if ok else "var(--ag-terra)"
    msg = (t("Total for {land:g} ha: {total:,} RWF, within budget, {remaining:,} RWF to spare.")
           .format(land=land, total=total, remaining=remaining) if ok else
           t("Total for {land:g} ha: {total:,} RWF, over budget by {extra:,} RWF. Use the subsidised "
             "Smart Nkunganire price, buy in stages, or start with a smaller area.")
           .format(land=land, total=total, extra=-remaining))
    st.markdown(f"""<div class="ag-card ag-pagein" style="margin-bottom:22px;border-left:4px solid {note_col}">
      <div style="padding:16px 20px;display:flex;align-items:baseline;gap:14px">
        <span style="font-family:var(--f-serif);font-size:30px;color:{note_col}">{total:,}<span style="font-size:13px;color:var(--ag-mute);font-family:var(--f-mono)"> RWF</span></span>
        <span style="font-size:13.5px;color:var(--ag-ink-soft);line-height:1.5">{msg}</span></div></div>""",
                unsafe_allow_html=True)

    # ---- other matches: catalogue inputs suitable for this crop ----
    suit = cat[cat["crop_suitability"].str.contains(crop, case=False, na=False)].copy()
    if not suit.empty:
        suit = suit.sort_values("price_rwf")
        body = ""
        for i, (_, it) in enumerate(suit.iterrows()):
            over = it["price_rwf"] > budget
            pcol = "var(--ag-terra)" if over else "var(--ag-ink)"
            flag = f"<span style='font-size:10px;margin-left:4px'>{t('over')}</span>" if over else ""
            body += (f"<tr><td class='num muted'>{i+1}</td><td><strong>{it['input_name']}</strong></td>"
                     f"<td class='muted'>{it['input_type']}</td><td class='muted' style='font-size:12px'>{it['supplier']}</td>"
                     f"<td class='num' style='color:{pcol}'>{int(it['price_rwf']):,}{flag}</td></tr>")
        st.markdown(f"""<div class="ag-card ag-pagein">
          <div class="ag-card-head"><div class="title">{t('OTHER')} <strong>{t('MATCHES')} · {len(suit)}</strong></div></div>
          <table class="ag-data"><thead><tr><th class="num">#</th><th>{t('Item')}</th><th>{t('Type')}</th><th>{t('Supplier')}</th><th class="num">{t('Price (RWF)')}</th></tr></thead>
          <tbody>{body}</tbody></table></div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="ag-foot">
      <div><span class="label">{t('Bulletin')}:</span> MINAGRI input prices (Smart Nkunganire)</div>
      <div><span class="label">{t('Sizing')}:</span> MINAGRI/RAB blanket rates × {land:g} ha</div>
      <div><span class="label">{t('Note')}:</span> {t('Confirm with soil testing and local extension advice.')}</div>
    </div>""", unsafe_allow_html=True)
else:
    st.info(t("Set crop, land size and budget, then click **Build Fertilizer Plan**."))