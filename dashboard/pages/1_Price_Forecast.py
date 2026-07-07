"""Price Forecast, next-month price per crop/district from the trained model.

Rendered in the "Officer console" editorial style: kicker + serif headline, a
three-up stat grid, an agriculture-themed forecast chart (crop-tinted line with
an empirical 80% band) and a two-column advice / forecast-table section.

Loads the serialized per-crop forecaster (models_store/price_forecaster.pkl,
built by scripts/train_models.py on real WFP data) instead of training on the
fly. WFP prices are monthly, so the horizon is the next month (~4 weeks).
"""
from _ui import (setup, load_prices, load_price_forecaster, load_esoko, load_farmgate_ratios,
                 page_header, urban_notice, price_chart_svg, CROP_TINT)
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

# beans & potatoes have varieties/grades in the Esoko data — let the user pick one
variety = None
if crop in ("beans", "potatoes") and "variety" in esoko.columns:
    vlist = sorted(v for v in esoko[esoko["crop"] == crop]["variety"].dropna().unique()
                   if v not in ("Grain",))
    if vlist:
        _all = t("All types (average)")
        pick = st.selectbox(t("Type"), [_all] + vlist)
        variety = None if pick == _all else pick

page_header(
    t('Price Forecast').upper(),
    f"{cl}{f' · {variety}' if variety else ''} <em>{t('farmgate price')}</em> · {district}",
    t("What a farmer is likely to be paid next month — the farmgate price, from "
      "recent market data."),
    meta_strong="RWF/kg", meta_sub=t("farmgate · monthly"))
urban_notice(district)

# live: recompute + redraw whenever any filter (crop / district / type) changes — no button
if crop and district:
    # one shared outlook so the dashboard, chat and USSD always agree (all farmgate)
    outlook = price_outlook(prices, models, crop, district, esoko=esoko, ratios=ratios, variety=variety)
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
    national = outlook["source"] == "national"     # no local history -> national average
    badge = "Esoko" if real_fg else (t("national avg") if national else t("estimated"))
    if national and real_fg:
        src_note = t("No local price history for {district}, so the trend uses Rwanda's national "
                     "average; the price level is a real Esoko farmgate figure.").format(district=district)
    elif national:
        src_note = t("No local price history for {district} — showing Rwanda's national average as a "
                     "farmgate price; next-month trend from the model.").format(district=district)
    elif real_fg:
        src_note = t("Farmgate price from Esoko for {district}; next-month trend from the model.").format(district=district)
    else:
        src_note = t("Estimated farmgate for {district} — recent market prices adjusted by the "
                     "measured farmgate margin; next-month trend from the model.").format(district=district)
    log_price(crop, district, str(last_date.date()), cur)

    # empirical 80% band from recent monthly log-return volatility (1.28σ). Because
    # the series is retail scaled by a constant ratio, that sigma is RETAIL
    # volatility — inflate it so the range reflects farmgate's wider swings (see
    # FARMGATE_VOL_UPLIFT; an assumption until Esoko history lets us measure it).
    from src.models.price_forecasting import FARMGATE_VOL_UPLIFT
    rets = np.log(s).diff().dropna().tail(12)
    sigma = (float(rets.std()) if len(rets) > 2 else 0.05) * FARMGATE_VOL_UPLIFT
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
    if national:
        st.markdown(
            f'<div class="ag-pagein" style="font-family:var(--f-mono);font-size:11.5px;color:var(--ag-ink-soft);'
            f'margin:-8px 0 16px;padding:8px 14px;border-radius:8px;background:var(--ag-bg-deep)">'
            f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--ag-slate);margin-right:8px"></span>'
            f'{t("No local market history for {district} — figures fall back to Rwanda\'s national average.").format(district=district)}'
            f'</div>', unsafe_allow_html=True)

    # ---- chart card ----
    hist = s.tail(24)
    real_set = set(outlook.get("real_dates", []))
    real_flags = [d in real_set for d in hist.index]
    n_real = sum(real_flags)
    nxt = hist.index[-1] + pd.offsets.MonthBegin(1)
    svg = price_chart_svg(list(hist.index), [float(v) for v in hist.values],
                          nxt, fc, lo, hi, tint, real_flags=real_flags)
    # Build the legend as one joined string. An empty conditional on its own line
    # would read as a blank line and break Streamlit's HTML block (raw-text dump).
    legend = f'<span><span class="swatch" style="background:var(--ag-ink)"></span>{t("Farmgate history")}</span>'
    if n_real:
        legend += (f'<span><span class="swatch" style="background:{tint};border-radius:50%"></span>'
                   f'{t("Actual farmgate (Esoko)")}</span>')
    legend += f'<span><span class="swatch" style="background:{tint}"></span>{cl} {t("forecast")}</span>'
    legend += f'<span><span class="swatch" style="background:{tint};opacity:.25"></span>≈80% {t("band")}</span>'
    note = t("Solid dots are real Esoko farmgate months; the rest of the line is estimated from market prices.")
    st.markdown(
        f'<div class="ag-card ag-pagein" style="margin-bottom:18px">'
        f'<div class="ag-card-head"><div class="title">24 {t("MONTHS HISTORY")} · <strong>1 {t("MONTH FORECAST")}</strong></div>'
        f'<div style="font-family:var(--f-mono);font-size:10.5px;color:var(--ag-mute)">{district}</div></div>'
        f'<div class="ag-card-body"><div class="ag-legend">{legend}</div>{svg}'
        f'<div style="font-size:10.5px;font-family:var(--f-mono);color:var(--ag-mute);margin-top:6px">{note}</div>'
        f'</div></div>', unsafe_allow_html=True)

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
          </tbody></table>
          <div style="font-size:10.5px;font-family:var(--f-mono);color:var(--ag-mute);padding:10px 14px 2px;line-height:1.5">
            {t("Indicative range — farmgate prices can swing wider than market prices, so treat the low/high as a guide.")}</div></div>
      </div></div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="ag-foot">
      <div><span class="label">{t('Source')}:</span> {t('WFP market prices')}</div>
      <div><span class="label">{t('Note')}:</span> {t('Next-month estimate. Confirm with local market conditions.')}</div>
    </div>""", unsafe_allow_html=True)
else:
    st.info(t("Pick a crop and district, then click **Generate Forecast**."))