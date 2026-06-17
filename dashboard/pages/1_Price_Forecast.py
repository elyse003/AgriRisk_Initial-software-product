"""Price Forecast, next-month price per crop/district from the trained model.

Loads the serialized per-crop forecaster (models_store/price_forecaster.pkl,
built by scripts/train_models.py on real WFP data) instead of training on the
fly. WFP prices are monthly, so the horizon is the next month (~4 weeks).
"""
from _ui import setup, load_prices, load_price_forecaster
from _i18n import t, crop_label
import numpy as np, pandas as pd, streamlit as st
from config.settings import CROPS, DISTRICTS
from src.models.price_forecasting import forecast_next, MIN_HISTORY
from src.db.connection import log_price

setup("Price Forecast", "Next-month price outlook by crop and district", allowed_roles=("officer", "super_admin"))
prices = load_prices()
models = load_price_forecaster()

c1, c2 = st.columns(2)
crop = c1.selectbox(t("Crop"), CROPS, format_func=crop_label)
district = c2.selectbox(t("District"), DISTRICTS)

if st.button(t("Generate Forecast"), type="primary"):
    model = (models or {}).get(crop)
    if model is None:
        st.error("The price model isn't available. Run `python scripts/train_models.py` first.")
        st.stop()

    s_district = prices[(prices.crop == crop) & (prices.market == district)].sort_values("date").set_index("date")["price_rwf"]
    crop_all = prices[prices.crop == crop].sort_values("date")
    crop_latest = crop_all["date"].max()
    national = crop_all.set_index("date")["price_rwf"].groupby(level=0).median().sort_index()

    if len(s_district) >= MIN_HISTORY:
        last_date = s_district.index[-1]
        if (crop_latest - last_date).days > 540:          # district's own data older than ~18 months
            s = national
            src_note = (f"Showing the national recent trend. {district}'s own {crop} prices end "
                        f"{last_date:%b %Y}, so a current district figure isn't available.")
        else:
            s = s_district
            src_note = f"Based on {district}'s prices through {last_date:%b %Y}."
    else:
        s = national
        src_note = f"{district} has little local price history, so this uses the national trend."

    cur = float(s.iloc[-1])
    fc = forecast_next(model, s)
    log_price(crop, district, str(s.index[-1].date()), cur)
    pct = (fc - cur) / cur * 100
    m1, m2, m3 = st.columns(3)
    m1.metric(t("Current"), f"{cur:,.0f} RWF/kg")
    m2.metric(t("Next-month forecast"), f"{fc:,.0f} RWF/kg", f"{pct:+.1f}%")
    m3.metric(t("Trend"), t("Rising") if pct > 1 else t("Falling") if pct < -1 else t("Stable"))
    hist = s.tail(36)
    fut = pd.Series([fc], index=[hist.index[-1] + pd.offsets.MonthBegin(1)])
    st.line_chart(pd.concat([hist.rename("history"),
                             pd.concat([hist.tail(1), fut]).rename("forecast")], axis=1))
    cl = crop_label(crop)
    if pct > 1:
        st.success(t("{crop} trending up in {district}. Advise holding stock 2 to 3 weeks.").format(crop=cl, district=district))
    elif pct < -1:
        st.warning(t("{crop} trending down in {district}. Advise selling soon.").format(crop=cl, district=district))
    else:
        st.info(t("{crop} stable in {district}. No urgent action.").format(crop=cl, district=district))
    st.caption(src_note + " " + t("Next-month estimate from the trained model. Confirm with local market conditions."))
else:
    st.info(t("Pick a crop and district, then click **Generate Forecast**."))
