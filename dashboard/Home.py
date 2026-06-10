"""AgriRisk Rwanda dashboard (Home). Run: streamlit run dashboard/Home.py"""
from _ui import setup, load_metrics
import streamlit as st

setup("Dashboard", "Nationwide agricultural risk advisory platform")

m = load_metrics()
rf = m.get("risk_random_forest", {})
mape = m.get("price_baseline_mape", "—")
rf_acc = f"{rf.get('accuracy', 0)*100:.0f}%" if rf else "—"

st.markdown(f"""
<div class='ar-grid'>
  <div class='ar-card'><div class='ar-num' style='color:#2D6A4F'>30</div><div class='ar-lbl'>Districts</div></div>
  <div class='ar-card'><div class='ar-num' style='color:#40916C'>3</div><div class='ar-lbl'>Crops covered</div></div>
  <div class='ar-card'><div class='ar-num' style='color:#D97706'>3</div><div class='ar-lbl'>Delivery channels</div></div>
  <div class='ar-card'><div class='ar-num' style='color:#7C3AED'>6</div><div class='ar-lbl'>Data sources</div></div>
</div>""", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("""
    <div class='ar-alert'><div class='t'>Active alerts</div>
      <p><b>Late blight, high risk</b> for potatoes in Musanze, Burera, Gakenke</p>
      <p><b>Angular leaf spot, high risk</b> for beans in Bugesera, Kayonza</p></div>""", unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class='ar-card'><div class='ar-label'>Delivery channels</div>
      <div style='display:flex;gap:10px;margin-top:10px'>
        <div style='flex:1;text-align:center;background:#EDF7F0;border-radius:8px;padding:14px 8px'><b style='font-size:13px'>Dashboard</b><br><span style='font-size:11px;color:#5A7A6A'>Active</span></div>
        <div style='flex:1;text-align:center;background:#EDF7F0;border-radius:8px;padding:14px 8px'><b style='font-size:13px'>WhatsApp</b><br><span style='font-size:11px;color:#5A7A6A'>Preview</span></div>
        <div style='flex:1;text-align:center;background:#EDF7F0;border-radius:8px;padding:14px 8px'><b style='font-size:13px'>SMS</b><br><span style='font-size:11px;color:#5A7A6A'>47 subscribers</span></div>
      </div></div>""", unsafe_allow_html=True)

st.markdown(f"""
<div class='ar-card' style='margin-top:14px'><div class='ar-label'>Model performance</div>
  <div style='display:flex;gap:12px;margin-top:10px'>
    <div style='flex:1;text-align:center;background:#EDF7F0;border-radius:8px;padding:14px'><div style='font-size:22px;font-weight:800;color:#2D6A4F'>{mape}%</div><div style='font-size:11px;color:#5A7A6A'>MAPE, target below 15%</div><div style='font-size:12px;font-weight:600'>Price forecast</div></div>
    <div style='flex:1;text-align:center;background:#EDF7F0;border-radius:8px;padding:14px'><div style='font-size:22px;font-weight:800;color:#2D6A4F'>{rf_acc}</div><div style='font-size:11px;color:#5A7A6A'>Accuracy, target above 85%</div><div style='font-size:12px;font-weight:600'>Seasonal risk</div></div>
    <div style='flex:1;text-align:center;background:#EDF7F0;border-radius:8px;padding:14px'><div style='font-size:22px;font-weight:800;color:#2D6A4F'>30</div><div style='font-size:11px;color:#5A7A6A'>districts served</div><div style='font-size:12px;font-weight:600'>Coverage</div></div>
  </div></div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-top:14px'>" + "".join(
    f"<span class='ar-pill'>{s}</span>" for s in
    ["WFP Rwanda", "NISR CPI", "World Bank", "Open-Meteo", "MINAGRI", "HDX Rainfall"]) + "</div>",
    unsafe_allow_html=True)

st.caption("Select a module from the sidebar to begin.")
