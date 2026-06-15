"""AgriRisk Rwanda dashboard (Home). Run: streamlit run dashboard/Home.py"""
from _ui import setup, load_last_updated, load_metrics
from src.db.connection import subscriber_count
import streamlit as st

setup("Dashboard", "Advice for every stage of the season")

subs = subscriber_count()

st.markdown(f"""
<div class='ar-grid'>
  <div class='ar-card'><div class='ar-num' style='color:#2D6A4F'>30</div><div class='ar-lbl'>Districts</div></div>
  <div class='ar-card'><div class='ar-num' style='color:#40916C'>3</div><div class='ar-lbl'>Crops covered</div></div>
  <div class='ar-card'><div class='ar-num' style='color:#C76E1B'>3</div><div class='ar-lbl'>Ways to reach farmers</div></div>
  <div class='ar-card'><div class='ar-num' style='color:#2D6A4F'>2</div><div class='ar-lbl'>Languages</div></div>
</div>""", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("""
    <div class='ar-alert'><div class='t'>Active alerts</div>
      <p><b>Late blight, high risk</b> for potatoes in Musanze, Burera, Gakenke</p>
      <p><b>Angular leaf spot, high risk</b> for beans in Bugesera, Kayonza</p></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class='ar-card'><div class='ar-label'>How farmers get advice</div>
      <div style='display:flex;gap:10px;margin-top:10px'>
        <div style='flex:1;text-align:center;background:#F6F2E8;border-radius:10px;padding:14px 8px'><b style='font-size:13px'>Dashboard</b><br><span style='font-size:11px;color:#5E7065'>For officers</span></div>
        <div style='flex:1;text-align:center;background:#F6F2E8;border-radius:10px;padding:14px 8px'><b style='font-size:13px'>WhatsApp</b><br><span style='font-size:11px;color:#5E7065'>Chat</span></div>
        <div style='flex:1;text-align:center;background:#F6F2E8;border-radius:10px;padding:14px 8px'><b style='font-size:13px'>SMS</b><br><span style='font-size:11px;color:#5E7065'>{subs} farmers</span></div>
      </div></div>""", unsafe_allow_html=True)

# real model performance (from models_store/metrics.json)
mt = load_metrics()
if mt:
    price = mt.get("price_mape_avg")
    risk = (mt.get("risk_gradient_boosting") or {}).get("accuracy")
    base = mt.get("risk_majority_baseline")
    cols = st.columns(2)
    if price is not None:
        cols[0].markdown(
            f"<div class='ar-card'><div class='ar-label'>Price model</div>"
            f"<div class='ar-num' style='color:#2D6A4F'>{price:.1f}%</div>"
            f"<div class='ar-lbl'>avg error (MAPE), target &lt;15%</div></div>", unsafe_allow_html=True)
    if risk is not None:
        extra = f" vs {base*100:.0f}% baseline" if base else ""
        cols[1].markdown(
            f"<div class='ar-card'><div class='ar-label'>Risk model</div>"
            f"<div class='ar-num' style='color:#C76E1B'>{risk*100:.0f}%</div>"
            f"<div class='ar-lbl'>accuracy{extra}</div></div>", unsafe_allow_html=True)

# data freshness in plain language, no source names or model details
lu = load_last_updated()
months = [v.get("data_through") for v in lu.values() if isinstance(v, dict) and v.get("data_through")]
if months:
    st.caption(f"Information current to {max(months)}. Weather updates live.")

st.caption("Choose a tool from the sidebar to begin.")
