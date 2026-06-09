const nav = document.getElementById("nav");
nav.addEventListener("click", e => {
  const a = e.target.closest("a"); if (!a) return;
  document.querySelectorAll("#nav a").forEach(x => x.classList.remove("active"));
  a.classList.add("active");
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById("screen-" + a.dataset.screen).classList.add("active");
});
const post = (u, b) => fetch(u, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(b)}).then(r => r.json());
const val = id => document.getElementById(id).value;
const cap = s => s ? s[0].toUpperCase()+s.slice(1) : s;

// ---- meta ----
fetch("/api/meta").then(r => r.json()).then(m => {
  const opt = a => a.map(d => `<option>${d}</option>`).join("");
  ["price-district","risk-district","disease-district","inputs-district"].forEach(id => document.getElementById(id).innerHTML = opt(m.districts));
  ["price-crop","inputs-crop"].forEach(id => document.getElementById(id).innerHTML = m.crops.map(c => `<option value="${c}">${cap(c)}</option>`).join(""));
  document.getElementById("risk-season").innerHTML = m.seasons.map(s => `<option value="${s.value}">${s.label}</option>`).join("");
  const t = m.metrics;
  document.getElementById("perf-row").innerHTML = `
    <div class="m"><div class="v">${t.price_mape}%</div><div class="k">MAPE (&lt;15%)</div><div class="t">Price baseline</div></div>
    <div class="m"><div class="v">&lt;15%</div><div class="k">target</div><div class="t">Prophet / LSTM*</div></div>
    <div class="m"><div class="v">${t.rf_accuracy}%</div><div class="k">Accuracy (&gt;85%)</div><div class="t">Random Forest</div></div>
    <div class="m"><div class="v">${t.gb_accuracy}%</div><div class="k">Accuracy (&gt;85%)</div><div class="t">Gradient Boosting</div></div>`;
  document.getElementById("pills").innerHTML = m.data_sources.map(s => `<span class="pill">${s}</span>`).join("");
});

// ---- price ----
let priceChart;
function runForecast(){
  const box = document.getElementById("price-results");
  box.innerHTML = `<div class="loading">Generating forecast…</div>`;
  post("/api/forecast", {crop:val("price-crop"), district:val("price-district")}).then(f => {
    if (f.error){ box.innerHTML = `<div class="muted">${f.error}</div>`; return; }
    const cls = f.trend==="upward"?"up":f.trend==="downward"?"down":"flat";
    const arrow = f.trend==="upward"?"▲":f.trend==="downward"?"▼":"▬";
    const adv = f.trend==="upward"
      ? `${cap(f.crop)} prices in ${f.district} are trending <b>upward</b>. Recommend farmers <b>hold stock 2–3 weeks</b> to capture ~RWF ${f.forecast-f.current}/kg gain.`
      : f.trend==="downward"
      ? `${cap(f.crop)} prices in ${f.district} are trending <b>downward</b>. Advise selling soon before further decline.`
      : `${cap(f.crop)} prices in ${f.district} are <b>stable</b>. No urgent action needed.`;
    box.innerHTML = `
      <div class="three">
        <div class="card kpi grad"><div class="k">Predicted (W4)</div><div class="v">${f.forecast.toLocaleString()} <span class="u">RWF/kg</span></div></div>
        <div class="card kpi"><div class="k">Current price</div><div class="v">${f.current.toLocaleString()} <span class="u">RWF/kg</span></div></div>
        <div class="card kpi"><div class="k">Change</div><div class="v" style="color:${f.pct>=0?'#059669':'#DC2626'}">${arrow} ${f.pct>0?'+':''}${f.pct}%</div></div>
      </div>
      <div class="card" style="margin-bottom:16px"><div class="label">Price trend & forecast — ${cap(f.crop)}, ${f.district}</div><canvas id="priceChart" height="110"></canvas></div>
      <div class="card advisory ${cls}"><b>📊 Advisory</b><br>${adv}<br><span class="note">This is a decision support tool. Confirm with local market conditions before acting.</span></div>`;
    if (priceChart) priceChart.destroy();
    priceChart = new Chart(document.getElementById("priceChart"), {
      type:"line",
      data:{labels:f.labels, datasets:[
        {label:"Actual", data:f.history, borderColor:"#2D6A4F", backgroundColor:"rgba(45,106,79,.12)", borderWidth:2.5, tension:.3, fill:true, pointRadius:2},
        {label:"Forecast", data:f.future, borderColor:"#D97706", borderDash:[6,3], borderWidth:2.5, tension:.3, pointRadius:2, spanGaps:true}
      ]},
      options:{plugins:{legend:{position:"bottom"}}, scales:{y:{title:{display:true,text:"RWF/kg"}}}}});
  });
}

// ---- risk ----
function runRisk(){
  const box = document.getElementById("risk-results");
  box.innerHTML = `<div class="loading">Assessing risk…</div>`;
  post("/api/risk", {district:val("risk-district"), season:val("risk-season")}).then(r => {
    const f = r.factors;
    const fac = (label,v,max,kind)=>`<div class="factor"><div class="top"><span>${label}</span><span style="font-weight:700">${v}</span></div><div class="bar"><i class="${kind}" style="width:${Math.min(Math.abs(v)/max*100,100)}%"></i></div></div>`;
    const advCls = r.risk_level==='High'?'down':r.risk_level==='Medium'?'flat':'up';
    box.innerHTML = `
      <div class="grid" style="grid-template-columns:1fr 2fr;gap:16px;margin-bottom:16px">
        <div class="card risk-hero ${r.risk_level}"><div style="font-size:32px">⚠️</div><div class="lv">${r.risk_level.toUpperCase()}</div>
          <small>${r.district} — Season ${r.season}</small>${r.confidence?`<small>Confidence: ${r.confidence}%</small>`:''}</div>
        <div class="card"><div class="label">Contributing factors</div>
          ${fac("🌧️ Rainfall anomaly (σ)", f.rainfall_anomaly, 2, f.rainfall_anomaly<-0.3?'bad':'good')}
          ${fac("📈 Food CPI change (%)", f.cpi_change, 30, f.cpi_change>10?'ok':'good')}
          ${fac("🧪 Fertilizer change (%)", f.fert_change, 60, f.fert_change>20?'ok':'good')}
        </div></div>
      <div class="card advisory ${advCls}"><b>⚠️ Advisory</b><br>${r.advisory}</div>`;
  });
}

// ---- disease ----
function runDisease(){
  const box = document.getElementById("disease-results");
  box.innerHTML = `<div class="loading">Checking live weather…</div>`;
  post("/api/disease", {district:val("disease-district")}).then(d => {
    const emoji = {maize:"🌽", beans:"🫘", potatoes:"🥔"};
    let w = d.weather.map((x,i)=>`<div class="wcell ${i===0?'first':''}"><div class="d">${x.day}</div><div class="ic">${x.icon}</div><div class="t">${x.temp}°C</div><div class="hu">💧${x.hum}%</div></div>`).join("");
    let html = `<div class="card" style="margin-bottom:16px"><div class="label">5-day weather — ${d.district} ${d.live?'(live Open-Meteo)':'(sample — offline)'}</div><div class="weather-row">${w}</div></div>`;
    if (!d.alerts.length) html += `<div class="card advisory up">No elevated disease risk detected for the forecast window.</div>`;
    else {
      html += `<div class="grid" style="grid-template-columns:1fr 1fr;gap:12px">`;
      d.alerts.forEach(a => {
        const col = a.risk==="High"?"#991B1B":a.risk==="Medium"?"#92400E":"#065F46";
        html += `<div class="card dz-card" style="border-color:${a.risk==='High'?'#FCA5A5':a.risk==='Medium'?'#FDE68A':'var(--brdL)'}">
          <div class="dz-head"><div class="left"><span class="emoji">${emoji[a.crop]||"🌱"}</span><div><b>${cap(a.crop)}</b><small>${a.disease}</small></div></div><span class="badge ${a.risk}">${a.risk.toUpperCase()}</span></div>
          <div class="dz-cond">🌡️ ${JSON.stringify(a.why).replace(/[{}"]/g,'').replace(/,/g,', ')}</div>
          <div class="dz-action" style="color:${col}"><b>Action:</b> ${a.action}</div></div>`;
      });
      html += `</div>`;
    }
    box.innerHTML = html;
  });
}

// ---- inputs ----
function runInputs(){
  const box = document.getElementById("inputs-results");
  box.innerHTML = `<div class="loading">Ranking inputs…</div>`;
  post("/api/inputs", {crop:val("inputs-crop"), district:val("inputs-district"), budget:+document.getElementById("inputs-budget").value}).then(d => {
    if (!d.recommendations.length){ box.innerHTML = `<div class="card advisory down">No inputs match that crop within budget. Try increasing the budget.</div>`; return; }
    let html = `<div class="grid" style="grid-template-columns:1fr 1fr 1fr;gap:12px">`;
    d.recommendations.forEach((r,i) => {
      html += `<div class="card rec" style="border-color:${i===0?'var(--purple)':'var(--brdL)'}">
        ${i===0?'<div class="best">BEST MATCH</div>':''}
        <div class="head"><div class="rank">${i+1}</div><div><div class="name">${r.input_name}</div><div class="type">${r.input_type}</div></div></div>
        <div class="sup">${r.supplier} (${r.district})</div>
        <div class="foot"><span class="price">RWF ${r.price_rwf.toLocaleString()}</span><span class="save">${r.pct_saving>0?r.pct_saving+'% below avg':'best value'}</span></div></div>`;
    });
    html += `</div><div class="card advisory up" style="margin-top:12px">Top ${d.recommendations.length} inputs · total RWF ${d.total.toLocaleString()} · RWF ${d.remaining.toLocaleString()} remaining of budget.</div>`;
    box.innerHTML = html;
  });
}

// ---- whatsapp ----
function addBubble(text, cls){
  const b = document.createElement("div"); b.className = "bub " + cls; b.textContent = text;
  const body = document.getElementById("wa-body"); body.appendChild(b); body.scrollTop = body.scrollHeight;
}
function sendChat(){
  const inp = document.getElementById("wa-input"); const msg = inp.value.trim(); if (!msg) return;
  addBubble(msg, "out"); inp.value = "";
  post("/api/chat", {message:msg}).then(d => addBubble(d.reply.replace(/\*/g,""), "in"));
}
addBubble("Muraho AgriRisk 👋", "out");
post("/api/chat", {message:"ubufasha"}).then(d => addBubble(d.reply.replace(/\*/g,""), "in"));
