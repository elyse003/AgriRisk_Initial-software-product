"""Price Forecast, next-month price per crop/district from the trained model.

Rendered in the "Officer console" editorial style: kicker + serif headline, a
three-up stat grid, an agriculture-themed forecast chart (crop-tinted line with
an empirical 80% band) and a two-column advice / forecast-table section.

Loads the serialized per-crop forecaster (models_store/price_forecaster.pkl,
built by scripts/train_models.py on real WFP data) instead of training on the
fly. WFP prices are monthly, so the horizon is the next month (~4 weeks).
"""
from _ui import (setup, load_prices, load_price_forecaster,
                 page_header, price_chart_svg, CROP_TINT)
from _i18n import t, crop_label
import numpy as np, pandas as pd, streamlit as st
from config.settings import CROPS, DISTRICTS
from src.models.price_forecasting import forecast_next, MIN_HISTORY
from src.db.connection import log_price

setup("Price Forecast", "Next-month price outlook by crop and district",
      allowed_roles=("officer", "super_admin"), header=False)
prices = load_prices()
models = load_price_forecaster()

c1, c2 = st.columns(2)
crop = c1.selectbox(t("Crop"), CROPS, format_func=crop_label)
district = c2.selectbox(t("District"), DISTRICTS)
cl = crop_label(crop)
tint = CROP_TINT.get(crop, "#6F5A34")

page_header(
    t('Price Forecast').upper(),
    f"{cl} <em>{t('price')}</em> · {district}",
    t("Where prices are likely to head next month, based on recent market data."),
    meta_strong="RWF/kg", meta_sub=t("monthly"))

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
            src_note = (f"Showing the national recent trend. {district}'s own {cl} prices end "
                        f"{last_date:%b %Y}, so a current district figure isn't available.")
        else:
            s = s_district
            src_note = f"Based on {district}'s prices through {last_date:%b %Y}."
    else:
        s = national
        src_note = f"{district} has little local price history, so this uses the national trend."

    s = s.sort_index()
    cur = float(s.iloc[-1])
    fc = forecast_next(model, s)
    log_price(crop, district, str(s.index[-1].date()), cur)
    pct = (fc - cur) / cur * 100

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
      <div class="ag-stat"><div class="label">{t('Current price')}</div>
        <div class="value">{cur:,.0f}<span class="unit">RWF/kg</span></div>
        <div class="delta flat">{t('Latest market price')}</div></div>
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