"""Shared helpers for the AgriRisk Streamlit dashboard: path fix, CSS theme
(matching the JSX design), cached real-data loaders, and small HTML card helpers.
"""
import os
import sys
import pickle

# --- make the project root importable from any page ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pandas as pd
import streamlit as st

from config.settings import CROPS, DISTRICTS, DISTRICT_COORDS, MODELS_STORE, data_path
from _i18n import t, LANGUAGES

# JSX design tokens
FOREST = "#1B4332"; EMERALD = "#2D6A4F"; G600 = "#40916C"; G50 = "#EDF7F0"
AMBER = "#D97706"; RED = "#DC2626"; PURPLE = "#7C3AED"; MUT = "#5A7A6A"; BRD = "#E0F0E4"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&display=swap');
:root{ --forest:#1B4332; --emerald:#2D6A4F; --harvest:#C76E1B; --paper:#F6F2E8; --ink:#1C2A22; --mut:#5E7065; --line:#DED7C4; }
/* Hide the menu / Deploy / decoration, but keep the toolbar itself so the
   sidebar reopen arrow survives on mobile (where the sidebar can collapse). */
#MainMenu, footer, [data-testid="stToolbarActions"], [data-testid="stDecoration"] { display:none; }
.stApp { background: var(--paper); }
html, body, [class*="css"] { font-family:'Geist',sans-serif; color:var(--ink); }
.block-container { padding-top: 2rem; max-width: 1050px; }
section[data-testid="stSidebar"] { background:#FFFFFF; }
section[data-testid="stSidebar"] * { color:var(--ink); }
section[data-testid="stSidebar"] a { border-radius:8px; }
/* Desktop: pin the sidebar open so it can't vanish; hide its collapse button. */
@media (min-width: 769px) {
  section[data-testid="stSidebar"] {
    transform: none !important; visibility: visible !important;
    margin-left: 0 !important; min-width: 300px !important;
  }
  [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] { display:none !important; }
}
/* Mobile/tablet: let the sidebar collapse to an overlay so it doesn't blanket
   the page; Streamlit's own close / reopen controls stay usable. */
@media (max-width: 768px) {
  section[data-testid="stSidebar"] { min-width: 0 !important; }
}
h1,h2,h3,.ar-head { font-family:'Geist',sans-serif; color:var(--forest); letter-spacing:-.01em; }
.ar-head { font-size:32px; font-weight:600; }
.ar-sub { color:var(--mut); font-size:13px; margin-bottom:6px; font-family:'Geist',sans-serif; letter-spacing:.02em; }
.ar-grid { display:flex; gap:14px; flex-wrap:wrap; margin:16px 0; }
.ar-card { background:#fff; border:1px solid var(--line); border-radius:16px; padding:20px 22px;
           box-shadow:0 1px 2px rgba(27,67,50,.04); flex:1; min-width:150px; }
.ar-num { font-family:'Geist',sans-serif; font-size:30px; font-weight:600; letter-spacing:-.02em; }
.ar-lbl { color:var(--mut); font-size:13px; margin-top:2px; }
.ar-alert { background:#FCF3E5; border:1px solid #F0DBBE; border-radius:16px; padding:16px 18px; }
.ar-alert b { color:#9A4D10; } .ar-alert .t { color:#9A4D10; font-weight:600; margin-bottom:6px; font-family:'Geist',sans-serif; font-size:18px; }
.ar-alert p { color:#B45309; font-size:13.5px; margin:4px 0; }
.ar-pill { display:inline-block; background:#fff; border:1px solid var(--line); color:var(--emerald);
           border-radius:30px; padding:6px 15px; font-size:12.5px; font-weight:500; margin:3px; font-family:'Geist',sans-serif; }
.ar-badge { padding:4px 14px; border-radius:20px; font-size:13px; font-weight:700; color:#fff; }
.ar-label { font-size:11px; font-weight:700; color:var(--mut); letter-spacing:.12em; text-transform:uppercase; font-family:'Geist',sans-serif; }
.stButton>button { font-weight:600; border-radius:9px; background:var(--forest); color:#fff; border:none; }
.stButton>button:hover { background:#15392a; color:#fff; }
[data-testid="stMetricValue"] { font-family:'Geist',sans-serif; color:var(--forest); }
</style>
"""

# Dark theme: re-declares the colour tokens and overrides the white surfaces.
# Injected by setup() when session_state["theme"] == "dark" (toggled in Settings).
DARK_CSS = """
<style>
:root{ --paper:#0F1A15; --ink:#E6F0EA; --mut:#9FB8AC; --line:#26392F; }
.stApp{ background:#0F1A15 !important; }
.ar-head, h1, h2, h3 { color:#E6F0EA !important; }
.ar-card, .tool-card, .ar-foot-brand, [data-testid="stForm"],
div[data-testid="stVerticalBlockBorderWrapper"] { background:#16241D !important; border-color:#26392F !important; }
.tc-title { color:#E6F0EA !important; }
.tc-desc, .ar-lbl, .ar-sub, p, label, [data-testid="stWidgetLabel"],
[data-testid="stMarkdownContainer"] { color:#CFE0D6 !important; }
.ar-alert { background:#27200F !important; border-color:#5A3F1E !important; }
[data-baseweb="select"] > div, [data-baseweb="input"] > div,
.stTextInput input, .stNumberInput input { background:#16241D !important; color:#E6F0EA !important; }
[data-testid="stMetricValue"] { color:#E6F0EA !important; }
</style>
"""


# ===========================================================================
#  Editorial "Officer console" design system (ported from the sample bundle)
#  + agriculture-themed SVG charts. Used by the four result pages.
# ===========================================================================
EDITORIAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600&family=Geist+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap');
:root{
  --ag-bg: oklch(0.975 0.010 80); --ag-bg-deep: oklch(0.955 0.012 78);
  --ag-surface: oklch(0.992 0.005 80); --ag-surface-2: oklch(0.985 0.008 80);
  --ag-line: oklch(0.88 0.012 70); --ag-line-soft: oklch(0.92 0.010 75);
  --ag-ink: oklch(0.22 0.018 50); --ag-ink-soft: oklch(0.36 0.015 55);
  --ag-mute: oklch(0.55 0.015 60); --ag-mute-2: oklch(0.70 0.012 65);
  /* earthy / agriculture accent palette */
  --ag-sage: oklch(0.55 0.085 145); --ag-sage-bg: oklch(0.94 0.030 145);
  --ag-terra: oklch(0.55 0.115 45); --ag-terra-bg: oklch(0.94 0.045 50);
  --ag-amber: oklch(0.66 0.120 80); --ag-amber-bg: oklch(0.95 0.045 80);
  --ag-slate: oklch(0.52 0.055 235); --ag-slate-bg: oklch(0.94 0.025 235);
  --ag-soil: oklch(0.45 0.055 60);
  /* One font everywhere (Geist); --f-brand (Instrument Serif) is for the AgriRisk wordmark only */
  --f-serif: "Geist", ui-sans-serif, system-ui, sans-serif;
  --f-sans:  "Geist", ui-sans-serif, system-ui, sans-serif;
  --f-mono:  "Geist", ui-sans-serif, system-ui, sans-serif;
  --f-brand: "Instrument Serif","Newsreader",Georgia,serif;
}
/* Geist display text needs weight to read as a heading (serif was a single weight) */
.ag-head h1, .ag-stat .value, .ag-rank .nm, .ag-rank .price, .ag-wtile .val,
.ag-disease .name, .ag-advice .badge{ font-weight:600; }
.ag-head{ display:flex; align-items:flex-end; justify-content:space-between; gap:24px;
  margin:2px 0 22px; border-bottom:1px solid var(--ag-line); padding-bottom:18px; }
.ag-head h1{ font-family:var(--f-serif); font-weight:400; font-size:42px; line-height:1.05;
  letter-spacing:-.01em; margin:0 0 6px; color:var(--ag-ink); }
.ag-head h1 em{ color:var(--ag-terra); font-style:italic; }
.ag-head .sub{ color:var(--ag-mute); font-size:14px; max-width:600px; line-height:1.5;
  font-family:var(--f-sans); }
.ag-head .meta{ font-family:var(--f-mono); font-size:11px; letter-spacing:.04em;
  color:var(--ag-mute); text-align:right; white-space:nowrap; }
.ag-head .meta strong{ color:var(--ag-ink); font-weight:500; display:block; font-size:13px;
  font-family:var(--f-sans); letter-spacing:0; margin-bottom:2px; }
.kicker{ font-family:var(--f-mono); font-size:10.5px; letter-spacing:.10em; text-transform:uppercase;
  color:var(--ag-mute); margin-bottom:8px; }
.kicker .pip{ display:inline-block; width:5px; height:5px; background:var(--ag-terra);
  border-radius:50%; margin-right:8px; transform:translateY(-1px); }
.ag-stat-grid{ display:grid; gap:14px; margin-bottom:22px; }
.ag-stat{ background:var(--ag-surface); border:1px solid var(--ag-line); border-radius:10px;
  padding:16px 18px; display:flex; flex-direction:column; gap:6px; }
.ag-stat .label{ font-size:10.5px; letter-spacing:.07em; text-transform:uppercase; color:var(--ag-mute);
  font-family:var(--f-mono); }
.ag-stat .value{ font-family:var(--f-serif); font-size:34px; line-height:1.05; letter-spacing:-.01em;
  color:var(--ag-ink); }
.ag-stat .value .unit{ font-family:var(--f-mono); font-size:12px; color:var(--ag-mute);
  margin-left:4px; letter-spacing:0; }
.ag-stat .delta{ font-family:var(--f-mono); font-size:11.5px; display:flex; align-items:center; gap:6px; }
.ag-stat .delta.up{ color:var(--ag-sage); } .ag-stat .delta.down{ color:var(--ag-terra); }
.ag-stat .delta.flat{ color:var(--ag-mute); }
.ag-stat.is-warn{ background:var(--ag-amber-bg); border-color:oklch(0.88 0.05 80); }
.ag-stat.is-alert{ background:var(--ag-terra-bg); border-color:oklch(0.85 0.06 50); }
.ag-stat.is-ok{ background:var(--ag-sage-bg); border-color:oklch(0.85 0.045 145); }
.ag-card{ background:var(--ag-surface); border:1px solid var(--ag-line); border-radius:10px; }
.ag-card-head{ display:flex; align-items:center; justify-content:space-between; padding:14px 18px;
  border-bottom:1px solid var(--ag-line-soft); }
.ag-card-head .title{ font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--ag-mute);
  font-family:var(--f-mono); }
.ag-card-head .title strong{ color:var(--ag-ink); font-weight:600; }
.ag-card-body{ padding:18px; }
.ag-legend{ display:flex; gap:18px; flex-wrap:wrap; font-family:var(--f-mono); font-size:11px;
  color:var(--ag-mute); margin-bottom:10px; }
.ag-legend .swatch{ display:inline-block; width:18px; height:8px; vertical-align:middle; margin-right:6px;
  border-radius:2px; }
.ag-two-col{ display:grid; grid-template-columns:1fr 320px; gap:18px; align-items:start; }
.ag-note{ padding:14px 16px; border-radius:10px; background:var(--ag-bg-deep); font-size:12.5px;
  line-height:1.55; color:var(--ag-ink-soft); }
.ag-note strong{ color:var(--ag-ink); font-weight:600; } .ag-note em{ font-style:italic; color:var(--ag-terra); }
.ag-advice{ display:flex; gap:14px; align-items:flex-start; }
.ag-advice .badge{ width:56px; height:56px; border-radius:50%; display:grid; place-items:center;
  font-family:var(--f-serif); font-size:21px; flex-shrink:0; }
table.ag-data{ width:100%; border-collapse:separate; border-spacing:0; font-size:13px; }
table.ag-data th{ text-align:left; font-size:10.5px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--ag-mute); font-weight:500; padding:10px 14px; border-bottom:1px solid var(--ag-line);
  background:var(--ag-surface-2); font-family:var(--f-mono); }
table.ag-data td{ padding:11px 14px; border-bottom:1px solid var(--ag-line-soft); color:var(--ag-ink); }
table.ag-data tr:last-child td{ border-bottom:none; }
table.ag-data td.num, table.ag-data th.num{ font-family:var(--f-mono); font-variant-numeric:tabular-nums; text-align:right; }
table.ag-data td.muted{ color:var(--ag-mute); }
.ag-foot{ margin-top:28px; padding-top:18px; border-top:1px solid var(--ag-line-soft); font-size:11px;
  color:var(--ag-mute); line-height:1.6; display:flex; gap:24px; flex-wrap:wrap; font-family:var(--f-sans); }
.ag-foot .label{ color:var(--ag-ink); font-weight:600; margin-right:4px; }
.risk-meter{ display:flex; gap:4px; width:100%; }
.risk-meter .seg{ flex:1; height:8px; border-radius:2px; background:oklch(0.92 0.012 75); }
.risk-meter .seg.on.low{ background:var(--ag-sage); }
.risk-meter .seg.on.med{ background:var(--ag-amber); }
.risk-meter .seg.on.high{ background:var(--ag-terra); }
.ag-driver{ display:flex; flex-direction:column; gap:4px; padding:10px 0; border-bottom:1px solid var(--ag-line-soft); }
.ag-driver .top{ display:flex; justify-content:space-between; font-size:12.5px; color:var(--ag-ink); }
.ag-driver .top .v{ font-family:var(--f-mono); }
.ag-driver .track{ display:flex; align-items:center; gap:8px; }
.ag-driver .bar{ flex:1; height:5px; border-radius:3px; background:var(--ag-line); overflow:hidden; }
.ag-driver .bar > span{ display:block; height:100%; }
.ag-driver .pct{ font-family:var(--f-mono); font-size:10.5px; color:var(--ag-mute); width:38px; text-align:right; }
.week-strip{ display:grid; grid-template-columns:repeat(14,1fr); gap:3px; }
.week-strip .day{ height:36px; border-radius:3px; background:oklch(0.92 0.010 75); }
.week-strip .day.r1{ background:var(--ag-sage-bg); }
.week-strip .day.r2{ background:oklch(0.86 0.06 80); }
.week-strip .day.r3{ background:oklch(0.78 0.10 60); }
.week-strip .day.r4{ background:var(--ag-terra); }
.week-strip .axis{ grid-column:1 / -1; display:grid; grid-template-columns:repeat(14,1fr);
  font-family:var(--f-mono); font-size:9.5px; color:var(--ag-mute); margin-top:4px; text-align:center; }
.ag-wtile{ display:flex; flex-direction:column; gap:6px; padding-right:16px; border-right:1px solid var(--ag-line-soft); }
.ag-wtile .lab{ display:flex; align-items:center; gap:8px; font-size:11px; color:var(--ag-mute);
  letter-spacing:.06em; text-transform:uppercase; font-family:var(--f-mono); }
.ag-wtile .val{ font-family:var(--f-serif); font-size:32px; line-height:1; color:var(--ag-ink); }
.ag-wtile .note{ font-size:11.5px; color:var(--ag-ink-soft); line-height:1.5; }
.ag-disease{ display:grid; grid-template-columns:220px 1fr 150px; gap:16px; align-items:center;
  padding:16px 18px; border-bottom:1px solid var(--ag-line-soft); }
.ag-disease:last-child{ border-bottom:none; }
.ag-disease .name{ font-family:var(--f-serif); font-size:20px; line-height:1.1; color:var(--ag-ink); }
.ag-disease .crop{ font-size:11px; color:var(--ag-mute); letter-spacing:.04em; text-transform:uppercase; margin-top:4px; }
.ag-disease .cond{ display:inline-flex; align-items:center; gap:6px; margin-right:14px; font-size:12px; color:var(--ag-ink-soft); }
.ag-disease .cond .lbl{ color:var(--ag-mute); }
.ag-rank{ background:var(--ag-surface); border:1px solid var(--ag-line); border-radius:10px; padding:26px 22px 18px; position:relative; }
.ag-rank.r1{ border-color:var(--ag-ink); }
.ag-rank .tag{ position:absolute; top:-10px; left:16px; padding:3px 10px; border-radius:999px;
  font-family:var(--f-mono); font-size:10.5px; letter-spacing:.06em; border:1px solid var(--ag-ink);
  background:var(--ag-surface); color:var(--ag-ink); }
.ag-rank.r1 .tag{ background:var(--ag-ink); color:var(--ag-bg); }
.ag-rank .cat{ font-family:var(--f-mono); font-size:10.5px; letter-spacing:.06em; color:var(--ag-mute); }
.ag-rank .nm{ font-family:var(--f-serif); font-size:22px; line-height:1.15; margin:6px 0 10px; color:var(--ag-ink); }
.ag-rank .price{ font-family:var(--f-serif); font-size:28px; line-height:1; color:var(--ag-ink); }
.ag-rank .budget-note{ margin-top:14px; padding:8px 10px; border-radius:6px; font-size:11.5px; font-family:var(--f-mono); }
.ag-pagein{ animation:agIn 320ms cubic-bezier(.2,.7,.2,1) both; }
@keyframes agIn{ from{ opacity:0; transform:translateY(6px);} to{ opacity:1; transform:translateY(0);} }
/* live line charts: the path draws itself in on every (re)render, so changing a
   filter gives immediate visual feedback. */
.ag-draw{ stroke-dasharray:2200; stroke-dashoffset:2200; animation:agDraw 900ms cubic-bezier(.3,.7,.2,1) forwards; }
@keyframes agDraw{ to{ stroke-dashoffset:0; } }
/* the forecast leg is itself dashed, so it fades in (delayed) instead of drawing */
.ag-fade{ opacity:0; animation:agFade .5s ease-out .7s forwards; }
@keyframes agFade{ to{ opacity:1; } }
/* CSS-only hover: a vertical crosshair, a dot and a value pill reveal as the
   cursor scrubs across the chart (no JS needed inside st.markdown). */
.ag-hp .cross,.ag-hp .hdot,.ag-hp .htip{ opacity:0; transition:opacity .09s ease; pointer-events:none; }
.ag-hp:hover .cross,.ag-hp:hover .hdot,.ag-hp:hover .htip{ opacity:1; }
.ag-hp .hit{ cursor:crosshair; }
@media (max-width:820px){ .ag-two-col{ grid-template-columns:1fr; } }
</style>
"""

# per-crop chart tint (earthy: gold maize, red-brown beans, soil potatoes)
CROP_TINT = {"maize": "#C2891F", "beans": "#9A3B26", "potatoes": "#6F5A34"}


def page_header(kicker, title_html, sub, meta_strong="", meta_sub=""):
    """Render the sample's editorial page header (kicker + serif h1 + sub + meta)."""
    meta = (f"<div class='meta'><strong>{meta_strong}</strong>{meta_sub}</div>"
            if meta_strong or meta_sub else "")
    st.markdown(f"""<div class="ag-head ag-pagein">
      <div><div class="kicker"><span class="pip"></span>{kicker}</div>
        <h1>{title_html}</h1><div class="sub">{sub}</div></div>{meta}</div>""",
                unsafe_allow_html=True)


def _nice_bounds(lo, hi, pad=0.06):
    span = (hi - lo) or 1.0
    return lo - span * pad, hi + span * pad


def price_chart_svg(dates, vals, fc_date, fc_val, lo, hi, tint, real_flags=None):
    """Agri-themed price line: ink history + crop-tinted forecast point with an
    empirical band and a 'now' divider. dates are datetimes, vals/lo/hi floats.
    real_flags (aligned to vals) marks months backed by REAL Esoko farmgate — those
    get a solid tinted marker and an 'actual' tag; the rest are labelled 'est'."""
    real_flags = real_flags or [False] * len(vals)
    import pandas as pd
    W, H = 760, 280
    padL, padR, padT, padB = 56, 20, 22, 34
    iw, ih = W - padL - padR, H - padT - padB
    xs = list(dates) + [fc_date]
    n = len(xs)
    allv = list(vals) + [fc_val, lo, hi]
    ymin, ymax = _nice_bounds(min(allv), max(allv))
    def X(i): return padL + (i / (n - 1)) * iw
    def Y(v): return padT + (1 - (v - ymin) / (ymax - ymin)) * ih
    hist_i = len(vals) - 1
    hpath = " ".join(f"{'M' if i==0 else 'L'} {X(i):.1f} {Y(v):.1f}" for i, v in enumerate(vals))
    band = (f"M {X(hist_i):.1f} {Y(vals[-1]):.1f} L {X(n-1):.1f} {Y(hi):.1f} "
            f"L {X(n-1):.1f} {Y(lo):.1f} Z")
    yticks = [ymin + (ymax - ymin) * k / 4 for k in range(5)]
    yt = "".join(f'<line x1="{padL}" x2="{W-padR}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="oklch(0.92 0.010 75)"/>'
                 f'<text x="{padL-8}" y="{Y(v)+3:.1f}" font-size="10" fill="var(--ag-mute)" text-anchor="end">{v:,.0f}</text>'
                 for v in yticks)
    idxs = sorted(set([0, hist_i // 2, hist_i, n - 1]))
    xt = ""
    for i in idxs:
        lab = "now" if i == hist_i else ("next" if i == n - 1 else pd.Timestamp(xs[i]).strftime("%b '%y"))
        col = "var(--ag-terra)" if i == n - 1 else "var(--ag-mute)"
        xt += f'<text x="{X(i):.1f}" y="{H-padB+16}" font-size="9.5" fill="{col}" text-anchor="middle">{lab}</text>'

    # interactive hover layer: as the cursor scrubs across, each month reveals a
    # crosshair, a dot and a value pill. Pure CSS (:hover) — no JS in st.markdown.
    step = iw / (n - 1)
    ally = list(vals) + [fc_val]
    hov = ""
    for i, v in enumerate(ally):
        cx, cy = X(i), Y(v)
        fore = i == n - 1
        if fore:
            lab = f"next ~{v:,.0f}"
        else:
            tag = "" if real_flags[i] else "  est"
            lab = f"{pd.Timestamp(xs[i]).strftime('%b '+chr(39)+'%y')}  {v:,.0f}{tag}"
        tipw = max(52, len(lab) * 5.9 + 16)
        tx = min(max(cx, padL + tipw / 2), W - padR - tipw / 2)   # keep pill on-canvas
        ty = cy - 30 if cy - 30 > padT else cy + 14               # flip below near the top
        dotc = tint if fore else "var(--ag-ink)"
        hitx = min(max(cx - step / 2, 0), W - step)
        hov += (f'<g class="ag-hp">'
                f'<line class="cross" x1="{cx:.1f}" x2="{cx:.1f}" y1="{padT}" y2="{padT+ih}" '
                f'stroke="{dotc}" stroke-width="1" stroke-dasharray="3 3" opacity="0.5"/>'
                f'<circle class="hdot" cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="var(--ag-surface)" '
                f'stroke="{dotc}" stroke-width="2"/>'
                f'<g class="htip"><rect x="{tx-tipw/2:.1f}" y="{ty:.1f}" width="{tipw:.1f}" height="20" '
                f'rx="5" fill="var(--ag-ink)"/>'
                f'<text x="{tx:.1f}" y="{ty+13.5:.1f}" text-anchor="middle" fill="var(--ag-bg)" '
                f'font-size="10.5">{lab}</text></g>'
                f'<rect class="hit" x="{hitx:.1f}" y="{padT}" width="{step:.1f}" height="{ih}" fill="transparent"/>'
                f'</g>')

    # solid tinted dots on months backed by REAL Esoko farmgate (visible without hover)
    realmk = "".join(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.2" fill="{tint}" '
                     f'stroke="var(--ag-surface)" stroke-width="1.2"/>'
                     for i, v in enumerate(vals) if real_flags[i])

    return f"""<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" style="display:block;font-family:var(--f-mono)">
      <rect x="{X(hist_i):.1f}" y="{padT}" width="{X(n-1)-X(hist_i):.1f}" height="{ih}" fill="var(--ag-bg-deep)" opacity="0.55"/>
      <line x1="{X(hist_i):.1f}" x2="{X(hist_i):.1f}" y1="{padT}" y2="{padT+ih}" stroke="oklch(0.7 0.015 60)" stroke-dasharray="3 3"/>
      <text x="{X(hist_i)+6:.1f}" y="{padT+11}" fill="var(--ag-mute)" font-size="9.5" letter-spacing="0.06em">FORECAST &#8594;</text>
      {yt}{xt}
      <path d="{band}" fill="{tint}" opacity="0.16"/>
      <path class="ag-draw" d="{hpath}" fill="none" stroke="var(--ag-ink)" stroke-width="1.7" stroke-linejoin="round"/>
      <path class="ag-fade" d="M {X(hist_i):.1f} {Y(vals[-1]):.1f} L {X(n-1):.1f} {Y(fc_val):.1f}" fill="none" stroke="{tint}" stroke-width="2.2" stroke-dasharray="6 4"/>
      {realmk}
      <circle cx="{X(n-1):.1f}" cy="{Y(fc_val):.1f}" r="4.5" fill="var(--ag-surface)" stroke="{tint}" stroke-width="2"/>
      {hov}
    </svg>"""


def trend_svg(data, color, unit_pct=True, months=None):
    """Small anomaly trend (mirrors the sample TrendCard): zero line + line + last marker."""
    W, H = 360, 140
    padL, padR, padT, padB = 38, 12, 14, 26
    iw, ih = W - padL - padR, H - padT - padB
    mn = min(0, *data) - 4; mx = max(0, *data) + 4
    def X(i): return padL + (i / (len(data) - 1)) * iw
    def Y(v): return padT + (1 - (v - mn) / (mx - mn)) * ih
    path = " ".join(f"{'M' if i==0 else 'L'} {X(i):.1f} {Y(v):.1f}" for i, v in enumerate(data))
    pts = "".join(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="{3.5 if i==len(data)-1 else 1.8}" fill="{color}"/>'
                  for i, v in enumerate(data))
    last = data[-1]
    suff = "%" if unit_pct else ""
    months = months or ["" for _ in data]
    mt = "".join(f'<text x="{X(i):.1f}" y="{H-padB+14}" font-size="9" font-family="var(--f-mono)" fill="var(--ag-mute)" text-anchor="middle">{m}</text>'
                 for i, m in enumerate(months) if m)
    # hover scrubber: each point reveals a dot + value pill on hover (CSS-only)
    step = iw / max(1, len(data) - 1)
    hov = ""
    for i, v in enumerate(data):
        cx, cy = X(i), Y(v)
        lab = f"{'+' if v > 0 else ''}{v:.1f}{suff}"
        tipw = max(34, len(lab) * 6.2 + 12)
        tx = min(max(cx, padL + tipw / 2), W - padR - tipw / 2)
        ty = cy - 26 if cy - 26 > padT else cy + 12
        hitx = min(max(cx - step / 2, 0), W - step)
        hov += (f'<g class="ag-hp">'
                f'<circle class="hdot" cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="var(--ag-surface)" stroke="{color}" stroke-width="2"/>'
                f'<g class="htip"><rect x="{tx-tipw/2:.1f}" y="{ty:.1f}" width="{tipw:.1f}" height="17" rx="4" fill="var(--ag-ink)"/>'
                f'<text x="{tx:.1f}" y="{ty+11.5:.1f}" text-anchor="middle" fill="var(--ag-bg)" font-size="9.5">{lab}</text></g>'
                f'<rect class="hit" x="{hitx:.1f}" y="{padT}" width="{step:.1f}" height="{ih}" fill="transparent"/>'
                f'</g>')
    return f"""<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" style="display:block">
      <line x1="{padL}" x2="{W-padR}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="oklch(0.85 0.015 60)" stroke-dasharray="2 3"/>
      <text x="{padL-6}" y="{Y(0)+3:.1f}" font-size="9" fill="var(--ag-mute)" text-anchor="end" font-family="var(--f-mono)">0</text>
      <path class="ag-draw" d="{path}" fill="none" stroke="{color}" stroke-width="1.7" stroke-linejoin="round"/>{pts}
      <text x="{X(len(data)-1):.1f}" y="{Y(last)-10:.1f}" font-family="var(--f-mono)" font-size="10" fill="{color}" text-anchor="end">{'+' if last>0 else ''}{last:.1f}{suff}</text>
      {mt}{hov}</svg>"""


def gauge_svg(score, color):
    """Circular risk-index gauge (0..1)."""
    import math
    r = 56; c = 2 * math.pi * r; off = c * (1 - max(0, min(1, score)))
    return f"""<svg viewBox="0 0 140 140" width="140" height="140">
      <circle cx="70" cy="70" r="{r}" fill="none" stroke="oklch(0.92 0.012 75)" stroke-width="10"/>
      <circle cx="70" cy="70" r="{r}" fill="none" stroke="{color}" stroke-width="10"
        stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}" stroke-linecap="round" transform="rotate(-90 70 70)"/>
      <text x="70" y="68" text-anchor="middle" font-family="var(--f-serif)" font-size="32" fill="var(--ag-ink)">{score*100:.0f}</text>
      <text x="70" y="86" text-anchor="middle" font-family="var(--f-mono)" font-size="9.5" letter-spacing="0.08em" fill="var(--ag-mute)">RISK INDEX</text>
    </svg>"""


def risk_meter(level):
    """3-segment meter. level in {Low, Medium/Med, High}."""
    on = 1 if level in ("Low", "LOW") else 3 if level in ("High", "HIGH") else 2
    cls = "low" if on == 1 else "high" if on == 3 else "med"
    segs = "".join(f'<div class="seg {("on " + cls) if i <= on else ""}"></div>' for i in (1, 2, 3))
    return f'<div class="risk-meter">{segs}</div>'


def driver_bar(label, value, weight, color):
    return (f'<div class="ag-driver"><div class="top"><span>{label}</span><span class="v">{value}</span></div>'
            f'<div class="track"><div class="bar"><span style="width:{weight*100:.0f}%;background:{color}"></span></div>'
            f'<span class="pct">{weight*100:.0f}%</span></div></div>')


LOGO_PATH = os.path.join(ROOT, "assets", "logo.png")

# --- sidebar: custom icon nav (replaces Streamlit's auto page list) ---------
# (page path, English label key for t(), Material icon)
NAV_CONSOLE = [
    ("pages/0_Dashboard.py",         "Dashboard",         ":material/space_dashboard:"),
    ("pages/1_Price_Forecast.py",    "Price Forecast",    ":material/trending_up:"),
    ("pages/2_Seasonal_Risk.py",     "Seasonal Risk",     ":material/thermostat:"),
    ("pages/3_Disease_Alert.py",     "Disease Alert",     ":material/coronavirus:"),
    ("pages/4_Input_Recommender.py", "Input Recommender", ":material/compost:"),
]

SIDEBAR_CSS = """
<style>
/* hide Streamlit's auto page list; we render our own icon nav */
[data-testid="stSidebarNav"]{ display:none; }
/* white sidebar with dark text */
section[data-testid="stSidebar"]{ background:#FFFFFF; border-right:1px solid var(--line); }
section[data-testid="stSidebar"] *{ color:var(--ink); }
section[data-testid="stSidebar"] .nav-sec{ font-family:'Geist',sans-serif; font-size:10px;
  letter-spacing:.14em; text-transform:uppercase; color:#6E8377; margin:16px 14px 4px; }
/* brand at the top of the sidebar (logo.png text is light, so we draw our own) */
section[data-testid="stSidebar"] .ag-brand{ display:flex; align-items:center; gap:11px; padding:2px 8px 14px; }
section[data-testid="stSidebar"] .ag-brand .seed{ width:26px; height:26px; flex:0 0 26px;
  border-radius:50% 50% 50% 0; background:var(--emerald); transform:rotate(-45deg);
  box-shadow:inset -3px -3px 0 rgba(0,0,0,.08); }
section[data-testid="stSidebar"] .ag-brand .nm{ font-family:'Instrument Serif',serif; font-size:24px;
  color:var(--forest); line-height:1; }
section[data-testid="stSidebar"] .ag-brand .sub{ font-family:'Geist',sans-serif; font-size:9.5px;
  letter-spacing:.08em; text-transform:uppercase; color:#6E8377; margin-top:3px; }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]{ padding:9px 12px; border-radius:9px; margin:1px 6px; }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] p{ font-size:14.5px; font-weight:500; color:#3A4A41; }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover{ background:#EEF5EE; }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"]{ background:#E2F0E5; }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] *{ color:var(--forest) !important; font-weight:600; }
/* pin the bottom group (language + account + logout) to the foot of the sidebar */
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"]:first-of-type{
  min-height: calc(100vh - 7.5rem); }
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"]:first-of-type > :last-child{
  margin-top:auto; }
section[data-testid="stSidebar"] .stButton>button{ background:var(--forest); border:none; color:#fff !important;
  font-weight:600; padding:11px; }
section[data-testid="stSidebar"] .stButton>button *{ color:#fff !important; }
section[data-testid="stSidebar"] .stButton>button:hover{ background:#15392a; }
/* floating chat: round button bottom-right + small popover panel.
   The container collapses to nothing; the button itself is fixed bottom-right. */
.st-key-ag_chatfab{ position:fixed !important; right:0; bottom:0; width:0 !important; height:0 !important;
  min-width:0 !important; margin:0 !important; padding:0 !important; z-index:1000; }
.st-key-ag_chatfab > div{ width:auto !important; }
.st-key-ag_chatfab button{ position:fixed !important; right:22px !important; bottom:20px !important;
  width:58px !important; height:58px !important; min-height:58px !important; border-radius:50% !important;
  background:#1B8A4B !important; color:#fff !important; border:none !important; padding:0 !important;
  box-shadow:0 8px 22px rgba(0,0,0,.22) !important; }
.st-key-ag_chatfab button:hover{ background:#15723d !important; }
.st-key-ag_chatfab button p, .st-key-ag_chatfab button span, .st-key-ag_chatfab button [data-testid="stIconMaterial"]{ color:#fff !important; }
[data-testid="stPopoverBody"]{ width:344px; max-width:92vw; }
.ag-chat-head{ font-family:'Geist',sans-serif; font-weight:600; font-size:18px; color:var(--forest);
  border-bottom:1px solid var(--line); padding-bottom:8px; margin-bottom:6px; display:flex; align-items:center; gap:8px; }
.ag-chat-head .dot{ width:8px; height:8px; border-radius:50%; background:#1B8A4B; flex:0 0 8px; }
</style>
"""


def render_sidebar_nav(user):
    """Custom icon navigation in the sidebar (replaces Streamlit's auto page list)."""
    sb = st.sidebar
    sb.markdown("<div class='ag-brand'><span class='seed'></span>"
                "<div><div class='nm'>AgriRisk</div><div class='sub'>Rwanda · 30 districts</div></div></div>",
                unsafe_allow_html=True)
    role = (user or {}).get("role")

    # Farmers get a chat-only view: just Home + Settings (the analytical tools are
    # for extension officers; farmers use the chat button / SMS / WhatsApp).
    if role == "farmer":
        sb.markdown(f"<div class='nav-sec'>{t('Menu')}</div>", unsafe_allow_html=True)
        sb.page_link("pages/0_Dashboard.py", label=t("Home"), icon=":material/home:")
        sb.page_link("pages/5_USSD_Preview.py", label=t("USSD Preview"), icon=":material/dialpad:")
        sb.page_link("pages/6_Settings.py", label=t("Settings"), icon=":material/settings:")
        return

    sb.markdown(f"<div class='nav-sec'>{t('Console')}</div>", unsafe_allow_html=True)
    for path, label, icon in NAV_CONSOLE:
        sb.page_link(path, label=t(label), icon=icon)
    sb.markdown(f"<div class='nav-sec'>{t('Channels')}</div>", unsafe_allow_html=True)
    sb.page_link("pages/5_USSD_Preview.py", label=t("USSD Preview"), icon=":material/dialpad:")
    sb.markdown(f"<div class='nav-sec'>{t('Account')}</div>", unsafe_allow_html=True)
    sb.page_link("pages/6_Settings.py", label=t("Settings"), icon=":material/settings:")
    if role == "super_admin":
        sb.page_link("pages/7_User_Management.py", label=t("User Management"), icon=":material/group:")


@st.fragment
def _chat_body():
    """Chat UI inside the popover. A fragment, so sending a message reruns only
    this widget and the popover stays open. Reuses the WhatsApp bot's answer()."""
    from src.channels.whatsapp_bot import converse
    st.markdown(f"<div class='ag-chat-head'><span class='dot'></span>{t('AgriRisk Assistant')}</div>",
                unsafe_allow_html=True)
    if "chat" not in st.session_state:
        st.session_state.chat = [("assistant", t("Hello! Ask me about price, risk, disease or inputs — "
                                                 "for example: 'maize price Musanze'."))]
    st.session_state.setdefault("chat_ctx", {})
    box = st.container(height=300)
    for role, txt in st.session_state.chat:
        with box.chat_message("user" if role == "user" else "assistant"):
            st.write(txt)
    with st.form("ag_chat_form", clear_on_submit=True, border=False):
        c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
        q = c1.text_input("msg", label_visibility="collapsed",
                          placeholder=t("Ask price, risk, disease, inputs…"))
        send = c2.form_submit_button("➤", use_container_width=True)
    if send and (q or "").strip():
        reply, st.session_state.chat_ctx = converse(q, st.session_state.chat_ctx)
        st.session_state.chat.append(("user", q))
        st.session_state.chat.append(("assistant", reply))
        st.rerun(scope="fragment")


def floating_chat():
    """Round floating chat button (bottom-right) opening a small assistant popover.

    Wrapped so a chat/import hiccup can never blank out the host page — the rest
    of the page (e.g. the USSD Preview) still renders."""
    try:
        with st.container(key="ag_chatfab"):
            with st.popover("", icon=":material/forum:"):
                _chat_body()
    except Exception:
        pass


def _language_selector(dg=None):
    """Sidebar language switch. Persists in session_state so it applies to every
    page. `dg` is the target container (defaults to the sidebar)."""
    dg = dg or st.sidebar
    st.session_state.setdefault("lang", "en")
    names = list(LANGUAGES)                       # ["English", "Kinyarwanda"]
    current = next(n for n, code in LANGUAGES.items() if code == st.session_state["lang"])
    choice = dg.radio("Ururimi / Language", names, index=names.index(current),
                      horizontal=True, key="_lang_radio")
    st.session_state["lang"] = LANGUAGES[choice]


def setup(title, subtitle, allowed_roles=None, header=True):
    """Page scaffold: config, CSS/theme, sidebar, login gate, header.

    Returns the logged-in user. If `allowed_roles` is given, callers without one
    of those roles are stopped with a notice (used to keep tools officer-only).
    Pass `header=False` on the editorial result pages, which render their own
    `page_header(...)` in the "Officer console" style instead of the plain title.
    """
    # "auto": expanded on desktop (pinned open by the CSS), collapsed on mobile
    # so the sidebar doesn't blanket the screen.
    st.set_page_config(page_title="AgriRisk Rwanda", layout="wide", initial_sidebar_state="auto")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(EDITORIAL_CSS, unsafe_allow_html=True)
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
    if st.session_state.get("theme") == "dark":
        st.markdown(DARK_CSS, unsafe_allow_html=True)

    from _auth import current_user, require_login, require_role, sidebar_account
    user = current_user()
    if not user:
        # The sidebar (nav, language, account) only appears once signed in, so the
        # login / sign-up screen is clean.
        st.markdown("<style>section[data-testid='stSidebar'],"
                    "[data-testid='stSidebarCollapsedControl']{display:none !important;}</style>",
                    unsafe_allow_html=True)
        require_login()   # renders sign in / sign up, then st.stop()

    # signed in -> full sidebar: brand + custom icon nav, then a bottom group
    # (language + account + logout) that the CSS pins to the foot of the sidebar.
    render_sidebar_nav(user)
    # bottom group: render into one sidebar container (the CSS pins it to the foot).
    # Use the container's own methods so placement is reliable regardless of context.
    bottom = st.sidebar.container()
    bottom.markdown(f"<div class='nav-sec'>{t('Preferences')}</div>", unsafe_allow_html=True)
    _language_selector(bottom)
    sidebar_account(user, bottom)

    # role gate after the sidebar, so a blocked user can still navigate elsewhere
    if allowed_roles:
        require_role(allowed_roles)

    if header:
        st.markdown(f"<div class='ar-head'>{t(title)}</div><div class='ar-sub'>{t(subtitle)}</div>",
                    unsafe_allow_html=True)
    floating_chat()
    return user


GITHUB_URL = "https://github.com/elyse003/AgriRisk_Initial-software-product"


def footer():
    """Render the shared site footer. Call at the end of a page (after setup)."""
    st.markdown(f"""<style>
.ar-foot {{ margin-top:56px; padding-top:30px; border-top:1px solid var(--line); color:var(--mut); font-size:13.5px; }}
.ar-foot a {{ color:var(--mut) !important; text-decoration:none !important; }}
.ar-foot a:hover {{ color:var(--forest) !important; }}
.ar-foot-grid {{ display:flex; flex-wrap:wrap; gap:28px 48px; justify-content:space-between; }}
.ar-foot-brand {{ max-width:24em; }}
.ar-foot .fb {{ display:flex; align-items:center; gap:9px; font-family:'Instrument Serif',serif;
                font-weight:400; font-size:19px; color:var(--forest); }}
.ar-foot .fb .seed {{ width:18px; height:18px; border-radius:50% 50% 50% 0; background:var(--emerald);
                      transform:rotate(-45deg); }}
.ar-foot .fcol h5 {{ font-family:'Geist',sans-serif; font-size:11px; letter-spacing:.12em;
                     text-transform:uppercase; color:var(--harvest); margin-bottom:10px; font-weight:700; }}
.ar-foot .fcol a, .ar-foot .fcol span {{ display:block; margin:6px 0; }}
.ar-foot-bottom {{ margin-top:26px; padding-top:16px; border-top:1px solid var(--line); display:flex;
                   justify-content:space-between; flex-wrap:wrap; gap:8px; font-size:12.5px; }}
</style>
<div class="ar-foot">
  <div class="ar-foot-grid">
    <div class="ar-foot-brand">
      <div class="fb"><span class="seed"></span>AgriRisk Rwanda</div>
      <p style="margin-top:10px">{t("Machine learning decision support for Rwandan agriculture: "
      "price forecasts, seasonal risk, disease alerts and input plans for maize, beans and Irish "
      "potatoes across all 30 districts, in Kinyarwanda and English.")}</p>
    </div>
    <div class="fcol"><h5>{t("Tools")}</h5>
      <a href="/Price_Forecast" target="_self">{t("Price Forecast")}</a>
      <a href="/Seasonal_Risk" target="_self">{t("Seasonal Risk")}</a>
      <a href="/Disease_Alert" target="_self">{t("Disease Alert")}</a>
      <a href="/Input_Recommender" target="_self">{t("Input Recommender")}</a>
    </div>
    <div class="fcol"><h5>{t("Data")}</h5>
      <span>WFP market prices</span>
      <span>World Bank CPI &amp; fertilizer</span>
      <span>CHIRPS rainfall</span>
      <span>Open-Meteo &middot; MINAGRI</span>
    </div>
    <div class="fcol"><h5>{t("Project")}</h5>
      <a href="/" target="_self">{t("Home")}</a>
      <a href="/Dashboard" target="_self">{t("Dashboard")}</a>
      <a href="{GITHUB_URL}" target="_blank">GitHub</a>
    </div>
  </div>
  <div class="ar-foot-bottom">
    <span>&copy; 2026 AgriRisk Rwanda &middot; BSc Software Engineering capstone</span>
    <span>{t("Decision support only. Confirm with local extension advice.")}</span>
  </div>
</div>""", unsafe_allow_html=True)


# ---------------- cached real-data loaders (prefer data/processed) ----------------
@st.cache_data
def load_prices():
    return pd.read_csv(data_path("wfp_food_prices_rwanda.csv"), parse_dates=["date"])

@st.cache_data
def load_esoko():
    """Esoko farmgate prices (date, province, district, crop, price_rwf), or empty
    if no Esoko data has been ingested yet (scripts/prepare_esoko.py)."""
    from config.settings import DATA_PROCESSED
    p = DATA_PROCESSED / "esoko_farmgate_prices.csv"
    if p.exists():
        return pd.read_csv(p, parse_dates=["date"])
    return pd.DataFrame(columns=["date", "province", "district", "crop", "variety", "price_rwf"])

@st.cache_data
def load_farmgate_ratios():
    """{crop: farmgate/retail ratio} used to express non-Esoko districts in farmgate."""
    from src.models.price_forecasting import crop_ratios
    return crop_ratios(load_prices(), load_esoko())

@st.cache_data
def load_cpi():
    df = pd.read_csv(data_path("rwanda_food_cpi.csv"), parse_dates=["date"]).sort_values("date")
    df["cpi_change"] = df["food_cpi"].pct_change(12) * 100
    return df

@st.cache_data
def load_fert():
    df = pd.read_csv(data_path("fertilizer_price_index.csv"), parse_dates=["date"]).sort_values("date")
    df["fert_change"] = df["fert_index"].pct_change(12) * 100
    return df

@st.cache_data
def load_rainfall():
    return pd.read_csv(data_path("district_rainfall_anomalies.csv"), parse_dates=["date"])

@st.cache_data
def load_catalogue():
    return pd.read_csv(data_path("minagri_input_prices.csv"))

@st.cache_data
def load_metrics():
    import json
    p = MODELS_STORE / "metrics.json"
    return json.load(open(p)) if p.exists() else {}

def _safe_pickle(name):
    """Load a pickled model, returning None on any failure (missing file or an
    unpickling/version error) so a model problem degrades to the rule-based
    fallback instead of crashing the whole page on deploy."""
    p = MODELS_STORE / name
    if not p.exists():
        return None
    try:
        return pickle.load(open(p, "rb"))
    except Exception:
        return None

@st.cache_resource
def load_risk_model():
    return _safe_pickle("risk_classifier.pkl")

@st.cache_resource
def load_price_forecaster():
    """dict {crop: fitted model} trained by scripts/train_models.py, or None."""
    return _safe_pickle("price_forecaster.pkl")

@st.cache_data(ttl=300)
def load_last_updated():
    """How current each series is. Reads data/processed/last_updated.json, written
    by the refresh script; falls back to the latest date inside each processed file."""
    import json
    from config.settings import DATA_PROCESSED
    status_file = DATA_PROCESSED / "last_updated.json"
    if status_file.exists():
        try:
            return json.loads(status_file.read_text())
        except Exception:
            pass
    out = {}
    files = {"wfp_prices": "wfp_food_prices_rwanda.csv", "cpi": "rwanda_food_cpi.csv",
             "fertilizer": "fertilizer_price_index.csv", "rainfall": "district_rainfall_anomalies.csv"}
    for key, fname in files.items():
        p = DATA_PROCESSED / fname
        if p.exists():
            try:
                d = pd.read_csv(p, parse_dates=["date"])
                out[key] = {"data_through": d["date"].max().strftime("%Y-%m")}
            except Exception:
                pass
    return out
