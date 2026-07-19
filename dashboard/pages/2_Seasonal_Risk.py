"""Seasonal Risk, real rainfall anomaly + latest CPI/fertilizer -> trained model.

Rendered in the "Officer console" editorial style: a circular risk-index gauge,
classifier feature contributions as driver bars, two agriculture-themed trend
charts (rainfall anomaly + food CPI from real data) and a benchmark table read
straight from the model's metrics.json.
"""
from _ui import (setup, load_rainfall, load_cpi, load_fert, load_risk_model, load_metrics,
                 page_header, urban_notice, insight_panel, gauge_svg, trend_svg, driver_bar)
from _i18n import t
import numpy as np, pandas as pd, streamlit as st
from config.settings import DISTRICTS
from config.district_agro import agro_profile
from src.data.preprocessing import label_risk
from src.models import risk_classifier as rc
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
    t("How likely staple food prices are to rise sharply this season, from rainfall, "
      "food prices and fertilizer costs."),
    meta_strong=season_label, meta_sub=t("recalculated weekly"))
urban_notice(district)

# live: recompute + redraw whenever the district or season filter changes, no button
if district and season_label:
    r = rain[(rain.district == district) & (rain.season == scode)]
    rain_a = float(r.rainfall_anomaly.iloc[-1]) if len(r) else float(rain.rainfall_anomaly.mean())
    cpi_c = float(cpi.cpi_change.dropna().iloc[-1]); fert_c = float(fert.fert_change.dropna().iloc[-1])

    if model is not None:
        # dynamic signals + this district's static soil/terrain profile (shared with the bot)
        X = rc.feature_row(rain_a, cpi_c, fert_c, district)
        level = str(model.predict(X)[0])
        proba = model.predict_proba(X)[0]
        classes = list(model.classes_)
        conf = f"{proba.max()*100:.0f}% {t('confidence')}"
        wmap = {"High": 1.0, "Medium": 0.55, "Low": 0.2}
        score = float(sum(proba[i] * wmap.get(classes[i], 0.5) for i in range(len(classes))))
        imp = getattr(model, "feature_importances_", None)
        w = (np.asarray(imp, float) / np.sum(imp)) if imp is not None else np.array([0.4, 0.35, 0.25, 0, 0, 0, 0])
        # rain / cpi / fert are the first three features; the rest are soil & terrain
        weights = [float(w[0]), float(w[1]), float(w[2]), float(np.sum(w[3:]))]
        deployed = type(model).__name__
    else:
        level = label_risk(rain_a, cpi_c, fert_c); conf = "rule-based"
        score = {"High": 0.85, "Medium": 0.55, "Low": 0.25}[level]
        weights = [0.4, 0.32, 0.22, 0.06]; deployed = "rule-based"

    log_risk(district, scode, rain_a, cpi_c, fert_c, level)
    tone = "terra" if level == "High" else "amber" if level == "Medium" else "sage"
    tcol = f"var(--ag-{tone})"
    tbg = f"var(--ag-{tone}-bg)"
    level_txt = t(level + " risk")
    explain = t({"High": "Dry/inflationary conditions raise the chance of a sharp price spike. Advise storage, conservative input spend and drought-tolerant varieties.",
                 "Medium": "Mixed signals. Monitor markets and weather; plan inputs carefully and keep a reserve.",
                 "Low": "Conditions look stable. Normal planting and input investment is reasonable."}[level])

    # ---- plain-language reading of every number, plus a suggestion ----
    ap = agro_profile(district)
    s100 = round(score * 100)

    # risk index (0-100): what the digits mean
    if s100 <= 35:
        idx_read = t("mostly stable, normal planting and input spending is reasonable")
    elif s100 <= 45:
        idx_read = t("low to moderate, largely stable, but keep an eye on markets")
    elif s100 <= 60:
        idx_read = t("moderate, mixed signals; plan carefully and keep a reserve")
    elif s100 <= 75:
        idx_read = t("elevated, a price spike is more likely; store and spend cautiously")
    else:
        idx_read = t("high, sharp price rises are likely; prioritise storage and hardy varieties")

    # rainfall anomaly (z-score): 0 = this district's normal, each 1.0 = one std dev
    if rain_a >= 1.0:
        rain_note, rain_tip = t("much wetter than normal"), t("Great soil moisture and low drought risk, but scout for fungal disease in humid spells.")
    elif rain_a >= 0.3:
        rain_note, rain_tip = t("a bit wetter than normal"), t("Good moisture for planting; drought risk is low.")
    elif rain_a > -0.3:
        rain_note, rain_tip = t("about normal rainfall"), t("Typical planting conditions for this season.")
    elif rain_a > -1.0:
        rain_note, rain_tip = t("drier than normal"), t("Some drought risk, favour drought-tolerant, short-cycle varieties and save water.")
    else:
        rain_note, rain_tip = t("much drier than normal"), t("High drought risk, delay planting or choose drought-tolerant seed; irrigate if you can.")
    rain_note = f"{rain_a:+.2f} SD · {rain_note}"

    # food price pressure (CPI year-on-year %)
    if cpi_c >= 15:
        cpi_note, cpi_tip = t("food prices rising fast"), t("Strong upward pressure, a good time to sell stored grain, but expect higher costs too.")
    elif cpi_c >= 5:
        cpi_note, cpi_tip = t("food prices rising"), t("Moderate upward pressure on staple prices; hold some stock if you can store it well.")
    elif cpi_c >= 0:
        cpi_note, cpi_tip = t("food prices roughly stable"), t("Little inflation pressure this season.")
    else:
        cpi_note, cpi_tip = t("food prices falling"), t("Weaker selling prices, sell only what you must; store the rest if you can.")
    cpi_note = f"{cpi_c:+.1f}% {t('vs a year ago')} · {cpi_note}"

    # fertilizer cost (year-on-year %)
    if fert_c >= 20:
        fert_note, fert_tip = t("fertilizer much dearer"), t("Budget inputs carefully; stretch with compost and manure.")
    elif fert_c >= 5:
        fert_note, fert_tip = t("fertilizer getting dearer"), t("Input costs are rising, plan and buy early.")
    elif fert_c > -5:
        fert_note, fert_tip = t("fertilizer costs stable"), t("Normal input budgeting is fine.")
    else:
        fert_note, fert_tip = t("fertilizer cheaper"), t("A good time to buy inputs while prices are low.")
    fert_note = f"{fert_c:+.1f}% {t('vs a year ago')} · {fert_note}"

    # soil & terrain suggestion
    if ap["ph"] < 5.3:
        soil_tip = t("Acidic {soil} (pH {ph}), apply lime to lift yield, and add organic matter.").format(soil=ap["soil"], ph=f"{ap['ph']:.1f}")
    elif ap["fertility"] <= 2:
        soil_tip = t("Lower-fertility {soil}, build it up with compost/manure and a balanced fertilizer.").format(soil=ap["soil"])
    else:
        soil_tip = t("{soil} at {alt} m, reasonable for the district's staples.").format(soil=ap["soil"], alt=f"{ap['altitude_m']:,}")
    soil_note = f"{ap['soil']} · {ap['altitude_m']:,} m"

    drivers = [
        (t("Rainfall vs normal"), f"{rain_a:+.2f}", float(weights[0]), "var(--ag-slate)", rain_note),
        (t("Food price pressure"), f"{cpi_c:+.1f}%", float(weights[1]), "var(--ag-terra)", cpi_note),
        (t("Fertilizer cost"), f"{fert_c:+.1f}%", float(weights[2]), "var(--ag-sage)", fert_note),
        (t("Soil &amp; terrain"), ap["soil"], float(weights[3]), "var(--ag-soil)", soil_note),
    ]
    bars = "".join(driver_bar(*d) for d in drivers)
    st.markdown(f"""<div class="ag-pagein ag-grid" style="--cols:1.3fr 1fr;gap:18px;margin-bottom:22px">
      <div class="ag-card" style="background:{tbg};border-color:{tcol}">
        <div class="ag-flexrow" style="padding:24px;gap:26px">
          <div style="flex-shrink:0">{gauge_svg(score, tcol)}</div>
          <div><div class="kicker" style="color:var(--ag-ink-soft)">{t('RISK LEVEL')}</div>
            <div style="font-family:var(--f-serif);font-size:52px;line-height:1;font-style:italic;color:{tcol};margin-bottom:4px">{level_txt}</div>
            <div style="font-family:var(--f-mono);font-size:12px;color:var(--ag-ink-soft);margin-bottom:10px">
              {s100} / 100 · {idx_read}</div>
            <div style="font-size:13.5px;color:var(--ag-ink-soft);line-height:1.55;max-width:360px">{explain}</div>
          </div></div></div>
      <div class="ag-card"><div class="ag-card-head"><div class="title"><strong>{t('WHAT IS DRIVING THIS')}</strong></div>
        <div style="font-family:var(--f-mono);font-size:10px;color:var(--ag-mute)">{t('bar = model weight')}</div></div>
        <div class="ag-card-body" style="padding-top:4px">{bars}</div></div>
    </div>""", unsafe_allow_html=True)

    # ---- "what this means & what to do": one clear suggestion per signal ----
    insight_panel([
        ("var(--ag-slate)", t("Rainfall"), rain_tip),
        ("var(--ag-terra)", t("Food prices"), cpi_tip),
        ("var(--ag-sage)", t("Fertilizer"), fert_tip),
        ("var(--ag-soil)", t("Soil"), soil_tip),
    ], lead=t("What this means"), strong=t("What to do"), meta=f"{district} · {season_label}")

    # ---- district soil & terrain profile (now part of the model) ----
    ph_note = t("acidic, lime helps") if ap["ph"] < 5.3 else (t("slightly acidic") if ap["ph"] < 6.0 else t("near neutral"))
    fert_lbl = {1: t("very low"), 2: t("low"), 3: t("moderate"), 4: t("good"), 5: t("rich")}[ap["fertility"]]
    drain_lbl = {1: t("poor"), 2: t("poor"), 3: t("moderate"), 4: t("free-draining"), 5: t("free-draining")}[ap["drainage"]]
    cells = [
        (t("Agro-zone"), ap["zone"]),
        (t("Altitude"), f"{ap['altitude_m']:,} m"),
        (t("Dominant soil"), ap["soil"]),
        (t("Soil fertility"), fert_lbl),
        (t("Soil pH"), f"{ap['ph']:.1f} · {ph_note}"),
        (t("Drainage"), drain_lbl),
    ]
    cell_html = "".join(
        f"<div style='padding:12px 14px;border:1px solid var(--ag-line);border-radius:10px;background:var(--ag-surface)'>"
        f"<div style='font-family:var(--f-mono);font-size:10px;letter-spacing:.06em;color:var(--ag-mute);text-transform:uppercase'>{k}</div>"
        f"<div style='font-size:14.5px;color:var(--ag-ink);margin-top:3px'>{v}</div></div>" for k, v in cells)
    st.markdown(f"""<div class="ag-card ag-pagein" style="margin-bottom:22px">
      <div class="ag-card-head"><div class="title">{t('SOIL &amp; TERRAIN')} · <strong>{district}</strong></div>
        <div style="font-family:var(--f-mono);font-size:10.5px;color:var(--ag-mute)">{t('agro-ecological zone')}</div></div>
      <div class="ag-card-body">
        <div class="ag-grid" style="--cols:repeat(3,1fr);gap:12px">{cell_html}</div>
        <div style="font-size:11.5px;color:var(--ag-mute);margin-top:12px;line-height:1.5">
          {t("The model now factors in each district's soil and terrain (about {pct}% of its estimate here). "
             "Price-spike risk is still driven mostly by rainfall and market prices; soil and altitude "
             "matter more for yield and input planning.").format(pct=round(weights[3]*100))}</div>
      </div></div>""", unsafe_allow_html=True)

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
    st.markdown(f"""<div class="ag-pagein ag-grid" style="--cols:1fr 1fr;gap:18px;margin-bottom:22px">
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

    # ---- national view: risk level across every district this season ----
    with st.expander(t("Risk across all districts (national view)")):
        latest = (rain[rain.season == scode].sort_values("date")
                  .groupby("district").tail(1).set_index("district")["rainfall_anomaly"])
        rows = []
        for d in DISTRICTS:
            ra = float(latest[d]) if d in latest.index else float(rain.rainfall_anomaly.mean())
            if model is not None:
                lvl = str(model.predict(rc.feature_row(ra, cpi_c, fert_c, d))[0])
            else:
                lvl = label_risk(ra, cpi_c, fert_c)
            rows.append({t("District"): d, t("Risk"): t(lvl + " risk"),
                         t("Rainfall vs normal"): round(ra, 2), "_o": {"High": 0, "Medium": 1, "Low": 2}[lvl]})
        comp = pd.DataFrame(rows)
        hi = int((comp["_o"] == 0).sum()); md = int((comp["_o"] == 1).sum()); lo = int((comp["_o"] == 2).sum())
        st.caption(t("This season, nationally: {hi} High, {md} Medium, {lo} Low. "
                     "Food prices and fertilizer costs are national; rainfall differs by district.").format(
                     hi=hi, md=md, lo=lo))
        st.dataframe(comp.sort_values("_o").drop(columns="_o"),
                     use_container_width=True, hide_index=True)
else:
    st.info(t("Pick a district and season, then click **Assess Risk**."))