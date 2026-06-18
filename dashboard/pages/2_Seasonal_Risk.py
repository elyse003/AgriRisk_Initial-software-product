"""Seasonal Risk, real rainfall anomaly + latest CPI/fertilizer -> trained model.

Rendered in the "Officer console" editorial style: a circular risk-index gauge,
classifier feature contributions as driver bars, two agriculture-themed trend
charts (rainfall anomaly + food CPI from real data) and a benchmark table read
straight from the model's metrics.json.
"""
from _ui import (setup, load_rainfall, load_cpi, load_fert, load_risk_model, load_metrics,
                 page_header, gauge_svg, trend_svg, driver_bar)
from _i18n import t
import numpy as np, pandas as pd, streamlit as st
from config.settings import DISTRICTS
from src.data.preprocessing import label_risk
from src.db.connection import log_risk

setup("Seasonal Risk", "Planting risk by district and season",
      allowed_roles=("officer", "super_admin"), header=False)
rain, cpi, fert, model = load_rainfall(), load_cpi(), load_fert(), load_risk_model()
metrics = load_metrics()

# Rwanda's two main cropping seasons (official MINAGRI names; rainfall codes A/B swapped).
SEASONS = [("Season A, short rains (Oct to Dec)", "B"), ("Season B, long rains (Mar to May)", "A")]
SEASON_CODE = {t(lbl): code for lbl, code in SEASONS}

c1, c2 = st.columns(2)
district = c1.selectbox(t("District"), DISTRICTS)
season_label = c2.selectbox(t("Season"), [t(lbl) for lbl, _ in SEASONS])
scode = SEASON_CODE[season_label]

page_header(
    t('Seasonal Risk').upper(),
    f"<em>{t('Seasonal')}</em> {t('planting risk')} · {district}",
    t("How likely staple food prices are to rise sharply this season — from rainfall, "
      "food prices and fertilizer costs."),
    meta_strong=season_label, meta_sub=t("recalculated weekly"))

if st.button(t("Assess Risk"), type="primary"):
    r = rain[(rain.district == district) & (rain.season == scode)]
    rain_a = float(r.rainfall_anomaly.iloc[-1]) if len(r) else float(rain.rainfall_anomaly.mean())
    cpi_c = float(cpi.cpi_change.dropna().iloc[-1]); fert_c = float(fert.fert_change.dropna().iloc[-1])

    if model is not None:
        X = pd.DataFrame([[rain_a, cpi_c, fert_c]], columns=["rainfall_anomaly", "cpi_change", "fert_change"])
        level = str(model.predict(X)[0])
        proba = model.predict_proba(X)[0]
        classes = list(model.classes_)
        conf = f"{proba.max()*100:.0f}% {t('confidence')}"
        wmap = {"High": 1.0, "Medium": 0.55, "Low": 0.2}
        score = float(sum(proba[i] * wmap.get(classes[i], 0.5) for i in range(len(classes))))
        imp = getattr(model, "feature_importances_", None)
        weights = (np.asarray(imp, float) / np.sum(imp)) if imp is not None else np.array([0.4, 0.35, 0.25])
        deployed = type(model).__name__
    else:
        level = label_risk(rain_a, cpi_c, fert_c); conf = "rule-based"
        score = {"High": 0.85, "Medium": 0.55, "Low": 0.25}[level]
        weights = np.array([0.4, 0.35, 0.25]); deployed = "rule-based"

    log_risk(district, scode, rain_a, cpi_c, fert_c, level)
    tone = "terra" if level == "High" else "amber" if level == "Medium" else "sage"
    tcol = f"var(--ag-{tone})"
    tbg = f"var(--ag-{tone}-bg)"
    level_txt = t(level + " risk")
    explain = t({"High": "Dry/inflationary conditions raise the chance of a sharp price spike. Advise storage, conservative input spend and drought-tolerant varieties.",
                 "Medium": "Mixed signals. Monitor markets and weather; plan inputs carefully and keep a reserve.",
                 "Low": "Conditions look stable. Normal planting and input investment is reasonable."}[level])

    # ---- gauge + classification + driver bars ----
    drivers = [
        (t("Rainfall vs normal"), f"{rain_a:+.2f}", float(weights[0]), "var(--ag-slate)"),
        (t("Food price pressure"), f"{cpi_c:+.1f}%", float(weights[1]), "var(--ag-terra)"),
        (t("Fertilizer cost"), f"{fert_c:+.1f}%", float(weights[2]), "var(--ag-sage)"),
    ]
    bars = "".join(driver_bar(*d) for d in drivers)
    st.markdown(f"""<div class="ag-pagein" style="display:grid;grid-template-columns:1.3fr 1fr;gap:18px;margin-bottom:22px">
      <div class="ag-card" style="background:{tbg};border-color:{tcol}">
        <div style="padding:24px;display:flex;gap:26px;align-items:center">
          <div style="flex-shrink:0">{gauge_svg(score, tcol)}</div>
          <div><div class="kicker" style="color:var(--ag-ink-soft)">{t('RISK LEVEL')}</div>
            <div style="font-family:var(--f-serif);font-size:52px;line-height:1;font-style:italic;color:{tcol};margin-bottom:10px">{level_txt}</div>
            <div style="font-size:13.5px;color:var(--ag-ink-soft);line-height:1.55;max-width:360px">{explain}</div>
          </div></div></div>
      <div class="ag-card"><div class="ag-card-head"><div class="title"><strong>{t('WHAT IS DRIVING THIS')}</strong></div></div>
        <div class="ag-card-body" style="padding-top:4px">{bars}</div></div>
    </div>""", unsafe_allow_html=True)

    # ---- two trend charts (real data) ----
    rseries = (rain[rain.district == district].sort_values("date").rainfall_anomaly.tail(12)
               .astype(float).tolist())
    cseries = cpi.cpi_change.dropna().tail(12).astype(float).tolist()
    def month_labels(n):
        return [("" if i not in (0, n // 4, n // 2, 3 * n // 4, n - 1) else m)
                for i, m in enumerate(["·"] * n)]
    rmonths = [("" if i not in (0, 3, 6, 9, len(rseries) - 1) else lab)
               for i, lab in enumerate([f"t-{len(rseries)-1-i}" for i in range(len(rseries))])]
    rain_trend = trend_svg(rseries, "var(--ag-slate)", unit_pct=False, months=rmonths) if len(rseries) > 2 else ""
    cpi_trend = trend_svg(cseries, "var(--ag-terra)", unit_pct=True, months=rmonths[:len(cseries)]) if len(cseries) > 2 else ""
    st.markdown(f"""<div class="ag-pagein" style="display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:22px">
      <div class="ag-card"><div class="ag-card-head"><div class="title">{t('RAINFALL vs NORMAL')} · <strong>{t('RECENT')}</strong></div></div>
        <div class="ag-card-body" style="padding-top:8px">{rain_trend}
          <div style="font-size:10.5px;font-family:var(--f-mono);color:var(--ag-mute);margin-top:6px">{t('Rainfall record')}</div></div></div>
      <div class="ag-card"><div class="ag-card-head"><div class="title">{t('FOOD PRICES')} · <strong>{t('RECENT')}</strong></div>
        <div style="font-family:var(--f-mono);font-size:10.5px;color:var(--ag-mute)">%</div></div>
        <div class="ag-card-body" style="padding-top:8px">{cpi_trend}
          <div style="font-size:10.5px;font-family:var(--f-mono);color:var(--ag-mute);margin-top:6px">{t('Food price index')}</div></div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="ag-foot">
      <div><span class="label">{t('Based on')}:</span> {t('Rainfall, food prices and fertilizer costs')}</div>
      <div><span class="label">{t('Note')}:</span> {t('Decision support only. Confirm with local extension advice.')}</div>
    </div>""", unsafe_allow_html=True)
else:
    st.info(t("Pick a district and season, then click **Assess Risk**."))