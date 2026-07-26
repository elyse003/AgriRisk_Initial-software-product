"""Input Catalogue (super_admin only): view and update the fertilizer/input price
catalogue the Input Recommender uses. Edits save to the shared database, so a new
price takes effect immediately for every officer's recommendation.
"""
from _ui import setup
from _i18n import t
import streamlit as st
import pandas as pd

from src.db.connection import fetch_catalogue, save_catalogue

setup("Input Catalogue", "Update the input prices the recommender uses",
      allowed_roles=("super_admin",))

st.caption(t("Edit a price, add a row, or delete one — then Save. Changes apply immediately "
             "to the Input Recommender. Every row needs an input name and a price."))

COLS = ["input_name", "input_type", "crop_suitability", "supplier", "district", "price_rwf"]
cat = fetch_catalogue()
base = cat[[c for c in COLS if c in cat.columns]] if len(cat) else pd.DataFrame(columns=COLS)

edited = st.data_editor(
    base, num_rows="dynamic", use_container_width=True, hide_index=True, key="cat_editor",
    column_config={
        "input_name": st.column_config.TextColumn(t("Input name"), required=True),
        "input_type": st.column_config.TextColumn(t("Type")),
        "crop_suitability": st.column_config.TextColumn(t("Crops (comma-separated)")),
        "supplier": st.column_config.TextColumn(t("Supplier")),
        "district": st.column_config.TextColumn(t("District")),
        "price_rwf": st.column_config.NumberColumn(t("Price (RWF)"), min_value=0, step=100, format="%d"),
    },
)

c1, c2 = st.columns([1, 3])
if c1.button(t("Save catalogue"), type="primary"):
    if save_catalogue(edited):
        st.cache_data.clear()   # refresh any cached CSV read of the catalogue
        st.success(t("Saved. {n} items are now in the catalogue.").format(n=len(edited)))
    else:
        st.error(t("Could not save — every row needs an input name and a numeric price."))
c2.caption(t("{n} items currently in the catalogue.").format(n=len(cat)))