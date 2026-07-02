"""Price Forecast, next-month price per crop/district from the trained model.

Rendered in the "Officer console" editorial style: kicker + serif headline, a
three-up stat grid, an agriculture-themed forecast chart (crop-tinted line with
an empirical 80% band) and a two-column advice / forecast-table section.

Loads the serialized per-crop forecaster (models_store/price_forecaster.pkl,
built by scripts/train_models.py on real WFP data) instead of training on the
fly. WFP prices are monthly, so the horizon is the next month (~4 weeks).
"""
from _ui import (setup, load_prices, load_price_forecaster, load_esoko, load_farmgate_ratios,
                 page_header, price_chart_svg, CROP_TINT)
from _i18n import t, crop_label
import numpy as np, pandas as pd, streamlit as st
from config.settings import CROPS, DISTRICTS
from src.models.price_forecasting import price_outlook
from src.db.connection import log_price

setup("Price Forecast", "Next-month farmgate price by crop and district",
      allowed_roles=("officer", "super_admin"), header=False)
prices = load_prices()
models = load_price_forecaster()
esoko = load_esoko()
ratios = load_farmgate_ratios()

c1, c2 = st.columns(2)
crop = c1.selectbox(t("Crop"), CROPS, format_func=crop_label)
district = c2.selectbox(t("District"), DISTRICTS)
cl = crop_label(crop)
tint = CROP_TINT.get(crop, "#6F5A34")

page_header(
    t('Price Forecast').upper(),
    f"{cl} <em>{t('farmgate price')}</em> · {district}",
    t("What a farmer is likely to be paid next month — the farmgate price, from "
      "recent market data."),
    meta_strong="RWF/kg", meta_sub=t("farmgate · monthly"))

if st.button(t("Generate Forecast"), type="primary"):
    # one shared outlook so the dashboard, chat and USSD always agree (all farmgate)
    outlook = price_outlook(prices, models, crop, district, esoko=esoko, ratios=ratios)
    if outlook is None:
        st.error(f"No price data for {cl} in {district}.")
        st.stop()
    if outlook["forecast"] is None:
        st.error("The price model isn't available. Run `python scripts/train_models.py` first.")
        st.stop()

    s = outlook["series"]
    cur, fc, pct = outlook["current"], outlook["forecast"], outlook["pct"]
    last_date = outlook["last_date"]
    price_kind = t("Farmgate price")
    real_fg = outlook["level"] == "farmgate"
    badge = "Esoko" if real_fg else t("estimated")
    if real_fg:
        src_note = f"Farmgate price from Esoko for {district}; next-month trend from the model."
    else:
        src_note = (f"Estimated farmgate for {district} — recent market prices adjusted by the "
                    f"measured farmgate margin; next-month trend from the model.")
    log_price(crop, district, str(last_date.date()), cur)

    # empirical 80% band from recent monthly log-return volatility (1.28σ)
    rets = np.log(s).diff().dropna().tail(12)
    sigma = float(rets.std()) if len(rets) > 2 else 0.05
    lo, hi = fc * np.exp(-1.28 * sigma), fc * np.exp(1.28 * sigma)
    band_pct = (hi - lo) / 2 / fc * 100

    up, down = pct > 1, pct < -1
    color = "var(--ag-sage)" if up else "var(--ag-terra)" if down else "var(--ag-mute)"
    dcls = "up" if up else "down" if down else "flat"
    arrow = "▲" if up else "▼" if down else "→"
    trend = t("Rising") if up else t("Falling") if down else t("Stable")

    # ---- stat grid (2) ----
    st.markdown(f"""<div class="ag-stat-grid ag-pagein" style="grid-template-columns:repeat(2,1fr)">
      <div class="ag-stat"><div class="label">{price_kind}</div>
        <div class="value">{cur:,.0f}<span class="unit">RWF/kg</span></div>
        <div class="delta flat">{badge}</div></div>
      <div class="ag-stat is-warn"><div class="label">{t('Next-month forecast')}</div>
        <div class="value">{fc:,.0f}<span class="unit">RWF/kg</span></div>
        <div class="delta {dcls}"><span>{arrow}</span>{pct:+.1f}% · {trend}</div></div>
    </div>""", unsafe_allow_html=True)

    # ---- chart card ----
    hist = s.tail(24)
    nxt = hist.index[-1] + pd.offsets.MonthBegin(1)
    svg = price_chart_svg(list(hist.index), [float(v) for v in hist.values],
                          nxt, fc, lo, hi, tint)
    st.markdown(f"""<div class="ag-card ag-pagein" style="margin-bottom:18px">
      <div class="ag-card-head"><div class="title">24 {t('MONTHS HISTORY')} · <strong>1 {t('MONTH FORECAST')}</strong></div>
        <div style="font-family:var(--f-mono);font-size:10.5px;color:var(--ag-mute)">{district}</div></div>
      <div class="ag-card-body">
        <div class="ag-legend">
          <span><span class="swatch" style="background:var(--ag-ink)"></span>{t('Actual')}</span>
          <span><span class="swatch" style="background:{tint}"></span>{cl} {t('forecast')}</span>
          <span><span class="swatch" style="background:{tint};opacity:.25"></span>≈80% {t('band')}</span>
        </div>{svg}</div></div>""", unsafe_allow_html=True)

    # ---- two-col: advice + forecast table / RQ note ----
    tone = "hold" if up else "sell" if down else "flat"
    badge_bg = "var(--ag-sage-bg)" if up else "var(--ag-terra-bg)" if down else "var(--ag-bg-deep)"
    badge_word = t("Hold") if up else t("Sell") if down else "—"
    advice = (t("{crop} trending up in {district}. Advise holding stock 2 to 3 weeks.") if up
              else t("{crop} trending down in {district}. Advise selling soon.") if down
              else t("{crop} stable in {district}. No urgent action.")).format(crop=cl, district=district)

    st.markdown(f"""<div class="ag-two-col ag-pagein">
      <div class="ag-card"><div class="ag-card-head"><div class="title">{t('WHAT TO ADVISE')} · <strong>{t('FOR THE OFFICER')}</strong></div></div>
        <div class="ag-card-body"><div class="ag-advice">
          <div class="badge" style="background:{badge_bg};color:{color}">{badge_word}</div>
          <div><div style="font-size:14px;line-height:1.55;color:var(--ag-ink)">{advice}</div>
            <div style="font-size:11.5px;color:var(--ag-mute);margin-top:8px">{src_note}</div></div>
        </div></div></div>
      <div style="display:flex;flex-direction:column;gap:14px">
        <div class="ag-card"><div class="ag-card-head"><div class="title">{t('FORECAST')} <strong>{t('DETAIL')}</strong></div></div>
          <table class="ag-data"><tbody>
            <tr><td>{t('Current price')}</td><td class="num">{cur:,.0f}</td></tr>
            <tr><td>{t('Next-month forecast')}</td><td class="num" style="color:{tint}">{fc:,.0f}</td></tr>
            <tr><td class="muted">{t('Likely low')}</td><td class="num muted">{lo:,.0f}</td></tr>
            <tr><td class="muted">{t('Likely high')}</td><td class="num muted">{hi:,.0f}</td></tr>
          </tbody></table></div>
      </div></div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="ag-foot">
      <div><span class="label">{t('Source')}:</span> {t('WFP market prices')}</div>
      <div><span class="label">{t('Note')}:</span> {t('Next-month estimate. Confirm with local market conditions.')}</div>
    </div>""", unsafe_allow_html=True)
else:
    st.info(t("Pick a crop and district, then click **Generate Forecast**."))