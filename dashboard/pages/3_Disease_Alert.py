"""Disease Alert, live Open-Meteo weather + FAO rules (offline fallback).

Rendered in the "Officer console" editorial style: a 14-day weather-context strip
(rainfall / temp / humidity tiles + a daily risk heatmap built from the real
forecast), disease rows with risk meters, and the FAO rule-base table.
"""
from _ui import setup, page_header, risk_meter
from _i18n import t, crop_label
import streamlit as st
from config.settings import DISTRICT_COORDS, CROPS, DISEASE_RULES
from src.models.disease_alert import fetch_forecast, assess_crop_full

setup("Disease Alert", "Crop disease warnings from the local weather",
      allowed_roles=("officer", "super_admin"), header=False)


@st.cache_data(ttl=3600, show_spinner=False)
def _forecast(district):
    """14-day forecast for a district, cached an hour so changing the crop filter
    doesn't re-hit the weather API."""
    lat, lon = DISTRICT_COORDS[district]
    return fetch_forecast(lat, lon)


c1, c2 = st.columns(2)
district = c1.selectbox(t("District"), list(DISTRICT_COORDS))
_ALL = t("All crops")
crop_pick = c2.selectbox(t("Crop"), [_ALL] + list(CROPS),
                         format_func=lambda c: c if c == _ALL else crop_label(c))
sel_crop = None if crop_pick == _ALL else crop_pick
scope_label = _ALL if sel_crop is None else crop_label(sel_crop)

page_header(
    t('Disease Alert').upper(),
    f"<em>{t('Climate-driven')}</em> {t('disease alerts')} · {district} · {scope_label}",
    t("Crop disease warnings for the next 14 days, based on the local weather forecast."),
    meta_strong=t("14-day horizon"), meta_sub=t("updated hourly"))

# live: recompute whenever the district or crop changes — no button
if district:
    try:
        daily = _forecast(district)
        live = True
    except Exception:
        daily = {"temperature_2m_min": [16] * 14, "temperature_2m_max": [22] * 14,
                 "relative_humidity_2m_mean": [90] * 14, "precipitation_sum": [6] * 14}
        live = False

    temps = [(lo + hi) / 2 for lo, hi in zip(daily["temperature_2m_min"], daily["temperature_2m_max"])]
    rh = daily["relative_humidity_2m_mean"]
    rain = daily["precipitation_sum"]
    n = len(temps)
    rain_total = sum(r or 0 for r in rain)
    temp_mean = sum(temps) / n
    rh_mean = sum(rh) / n

    # per-day disease-risk index 0..4 from the real forecast
    def day_risk(tm, h, rn):
        return (2 if (h or 0) >= 85 else 1 if (h or 0) >= 75 else 0) + \
               (1 if 13 <= tm <= 24 else 0) + (1 if (rn or 0) > 1 else 0)
    days = [min(4, day_risk(temps[i], rh[i], rain[i])) for i in range(n)]

    # assess the chosen crop (or all), keeping EVERY disease so we can always give
    # a recommendation — elevated ones first, low-risk "preventive" ones after
    scope_crops = [sel_crop] if sel_crop else list(CROPS)
    full = []
    for c in scope_crops:
        full.extend(assess_crop_full(c, daily))
    full.sort(key=lambda a: {"High": 0, "Medium": 1, "Low": 2}[a["risk"]])
    n_active = sum(1 for a in full if a["risk"] != "Low")

    st.caption(t("Live 14-day weather forecast.") if live else t("Offline mode: showing a sample forecast."))

    # ---- weather context strip ----
    def tile(label, value, note, color):
        return (f'<div class="ag-wtile"><div class="lab">'
                f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-right:7px"></span>{label}</div>'
                f'<div class="val">{value}</div><div class="note">{note}</div></div>')
    rain_tone = "var(--ag-slate)" if rain_total >= 40 else "var(--ag-terra)"
    rh_tone = "var(--ag-terra)" if rh_mean >= 85 else "var(--ag-sage)"
    temp_tone = "var(--ag-terra)" if 13 <= temp_mean <= 24 else "var(--ag-amber)"
    tiles = (
        tile(t("14-day rainfall"), f"{rain_total:.0f}mm",
             t("Wet — sustained leaf wetness") if rain_total >= 40 else t("Dry — lower fungal pressure"), rain_tone) +
        tile(t("Mean temperature"), f"{temp_mean:.1f}°C",
             t("Within blight-favourable window") if 13 <= temp_mean <= 24 else t("Outside main blight window"), temp_tone) +
        tile(t("Mean humidity"), f"{rh_mean:.0f}%",
             t("High — favours fungal disease") if rh_mean >= 85 else t("Moderate humidity"), rh_tone))
    strip = "".join(f'<div class="day r{r}" title="Day +{i}: risk {r}/4"></div>' for i, r in enumerate(days))
    axis = "".join(f"<div>+{i}</div>" for i in range(n))
    st.markdown(f"""<div class="ag-card ag-pagein" style="margin-bottom:18px">
      <div class="ag-card-head"><div class="title">14-DAY <strong>{t('WEATHER CONTEXT')}</strong></div>
        <div style="font-family:var(--f-mono);font-size:10.5px;color:var(--ag-mute)">Open-Meteo · {district}</div></div>
      <div class="ag-card-body">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:24px;margin-bottom:18px">{tiles}</div>
        <div class="kicker">{t('DAILY DISEASE RISK INDEX')}</div>
        <div class="week-strip" style="margin-top:4px">{strip}<div class="axis">{axis}</div></div>
      </div></div>""", unsafe_allow_html=True)

    # ---- recommendations: one clear "what to do" per disease (always shown) ----
    risk_col = {"High": "var(--ag-terra)", "Medium": "var(--ag-amber)", "Low": "var(--ag-sage)"}
    tick = lambda b: "✓" if b else "✗"
    if n_active == 0:
        summary = t("No elevated disease risk in the next 14 days — the steps below are preventive.")
    else:
        summary = t("{n} disease(s) at elevated risk for {scope}. Act on the highlighted steps.").format(
            n=n_active, scope=scope_label)
    rows = ""
    for a in full:
        why = a["why"]
        col = risk_col[a["risk"]]
        pct = 80 if a["risk"] == "High" else 55 if a["risk"] == "Medium" else 20
        act_lbl = t("Do now") if a["risk"] != "Low" else t("Preventive care")
        rows += f"""<div class="ag-disease">
          <div><div class="name">{a['disease']}</div><div class="crop">{crop_label(a['crop'])}</div></div>
          <div><span class="cond"><span class="lbl">Temp</span> {tick(why.get('temperature'))}</span>
            <span class="cond"><span class="lbl">RH</span> {tick(why.get('humidity'))}</span>
            <span class="cond"><span class="lbl">Rain days</span> {why.get('rainy_days', 0)}</span>
            <div style="margin-top:8px;padding:8px 11px;border-radius:8px;background:var(--ag-bg-deep);border-left:3px solid {col}">
              <div style="font-family:var(--f-mono);font-size:9.5px;letter-spacing:.06em;color:var(--ag-mute);text-transform:uppercase">{act_lbl}</div>
              <div style="font-size:13px;color:var(--ag-ink);margin-top:2px;line-height:1.5">{a['action']}</div></div></div>
          <div><div style="font-family:var(--f-mono);font-size:10.5px;color:var(--ag-mute);margin-bottom:4px">{t('RISK')} · {pct}%</div>
            {risk_meter(a['risk'])}
            <div style="font-size:11px;color:var(--ag-mute);margin-top:6px">{t(a['risk'] + ' risk')}</div></div>
        </div>"""
    st.markdown(f"""<div class="ag-card ag-pagein" style="margin-bottom:18px">
      <div class="ag-card-head"><div class="title">{t('WHAT TO DO')} · <strong>{scope_label}</strong></div>
        <div style="font-family:var(--f-mono);font-size:10.5px;color:var(--ag-mute)">{n_active} {t('active')}</div></div>
      <div class="ag-card-body" style="padding-bottom:6px"><div style="font-size:12.5px;color:var(--ag-ink-soft);margin-bottom:6px">{summary}</div></div>
      <div>{rows}</div></div>""", unsafe_allow_html=True)

    # ---- rule base table (only the chosen crop, or all if none picked) ----
    rule_rows = ""
    for crop in scope_crops:
        for rule in DISEASE_RULES.get(crop, []):
            lo, hi = rule["temp_c"]
            rule_rows += (f"<tr><td>{rule['name']}</td><td>{crop_label(crop)}</td>"
                          f"<td class='muted'>{lo}–{hi}°C · RH ≥ {rule['humidity_pct']}% · ≥ {rule['rain_days']} wet days</td></tr>")
    st.markdown(f"""<div class="ag-card ag-pagein">
      <div class="ag-card-head"><div class="title">{t('DISEASE GUIDE')} · <strong>{scope_label}</strong></div></div>
      <table class="ag-data" style="font-size:12px"><thead><tr><th>{t('Disease')}</th><th>{t('Crop')}</th><th>{t('When it strikes')}</th></tr></thead>
      <tbody>{rule_rows}</tbody></table></div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="ag-foot">
      <div><span class="label">{t('Weather')}:</span> {t('Open-Meteo 14-day forecast')}</div>
      <div><span class="label">{t('Note')}:</span> {t('Decision support only. Confirm with local extension advice.')}</div>
    </div>""", unsafe_allow_html=True)
else:
    st.info(t("Pick a district and crop to see disease risk."))