"""Price Forecast, next-month price per crop/district from the trained model.

Loads the serialized per-crop forecaster (models_store/price_forecaster.pkl,
built by scripts/train_models.py on real WFP data) instead of training on the
fly. WFP prices are monthly, so the horizon is the next month (~4 weeks).
"""
from _ui import setup, load_prices, load_price_forecaster
from _i18n import t, crop_label
import numpy as np, pandas as pd, altair as alt, streamlit as st
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
    cl = crop_label(crop)

    color = "#2D6A4F" if pct > 1 else "#DC2626" if pct < -1 else "#5E7065"
    arrow = "&uarr;" if pct > 1 else "&darr;" if pct < -1 else "&rarr;"
    trend = t("Rising") if pct > 1 else t("Falling") if pct < -1 else t("Stable")

    # editorial stat row (reuses the .ar-card / .ar-num / .ar-label theme)
    st.markdown(f"""<div class="ar-grid">
      <div class="ar-card"><div class="ar-label">{t('Current')}</div>
        <div class="ar-num">{cur:,.0f}<small style="font-size:14px;color:#5E7065"> RWF/kg</small></div></div>
      <div class="ar-card"><div class="ar-label">{t('Next-month forecast')}</div>
        <div class="ar-num">{fc:,.0f}<small style="font-size:14px;color:#5E7065"> RWF/kg</small></div>
        <div class="ar-lbl" style="color:{color};font-weight:700">{arrow} {pct:+.1f}%</div></div>
      <div class="ar-card"><div class="ar-label">{t('Trend')}</div>
        <div class="ar-num" style="color:{color}">{trend}</div></div>
    </div>""", unsafe_allow_html=True)

    # themed chart: history (forest) + the forecast step (harvest)
    hist = s.tail(36)
    nxt = hist.index[-1] + pd.offsets.MonthBegin(1)
    h_df = pd.DataFrame({"date": hist.index, "price": hist.values, "series": t("Recent and forecast price")})
    f_df = pd.DataFrame({"date": [hist.index[-1], nxt], "price": [cur, fc], "series": "forecast"})
    base = alt.Chart(pd.concat([h_df, f_df])).mark_line(point=False).encode(
        x=alt.X("date:T", title=None),
        y=alt.Y("price:Q", title="RWF/kg", scale=alt.Scale(zero=False)),
        color=alt.Color("series:N", legend=None,
                        scale=alt.Scale(domain=[t("Recent and forecast price"), "forecast"],
                                        range=["#40916C", "#C76E1B"])),
        strokeDash=alt.condition("datum.series == 'forecast'", alt.value([5, 4]), alt.value([0])),
    ).properties(height=260).configure_view(strokeWidth=0)
    st.altair_chart(base, use_container_width=True)

    advice = (t("{crop} trending up in {district}. Advise holding stock 2 to 3 weeks.") if pct > 1
              else t("{crop} trending down in {district}. Advise selling soon.") if pct < -1
              else t("{crop} stable in {district}. No urgent action.")).format(crop=cl, district=district)
    st.markdown(f"""<div style="background:#fff;border:1px solid #DED7C4;border-left:4px solid {color};
      border-radius:12px;padding:14px 18px;margin-top:6px">
      <div class="ar-label" style="color:{color}">{t('Advice')}</div>
      <div style="margin-top:5px;font-size:15px;color:#1C2A22">{advice}</div></div>""", unsafe_allow_html=True)
    st.caption(src_note + " " + t("Next-month estimate from the trained model. Confirm with local market conditions."))
else:
    st.info(t("Pick a crop and district, then click **Generate Forecast**."))
