import { useState, useRef, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";
import { Home, TrendingUp, AlertTriangle, Bug, ShoppingCart, ChevronDown, ArrowUp, ArrowDown, Leaf, Bell, MessageSquare, Send, Smartphone, Check, CheckCheck } from "lucide-react";

const C = {
  forest: "#1B4332", emerald: "#2D6A4F", g600: "#40916C", g500: "#52B788", g400: "#74C69D",
  g300: "#95D5B2", g200: "#B7E4C7", g100: "#D8F3DC", g50: "#EDF7F0",
  bg: "#E8F5EC", card: "#FFFFFF", amber: "#D97706", red: "#DC2626", purple: "#7C3AED",
  txt: "#1B4332", mut: "#5A7A6A", light: "#8A9A90", brd: "#D0E8D6", brdL: "#E0F0E4",
  sidebar: "#1B4332", sideHover: "#2D6A4F", sideActive: "#40916C",
  waBg: "#ECE5DD", waGreen: "#DCF8C6", waDark: "#075E54", waLight: "#128C7E",
};

const ALL_DISTRICTS = ["Musanze","Burera","Gakenke","Gicumbi","Rulindo","Huye","Gisagara","Kamonyi","Muhanga","Nyamagabe","Nyanza","Nyaruguru","Ruhango","Bugesera","Gatsibo","Kayonza","Kirehe","Ngoma","Nyagatare","Rwamagana","Karongi","Ngororero","Nyabihu","Nyamasheke","Rubavu","Rusizi","Rutsiro","Gasabo","Kicukiro","Nyarugenge"];
const ALL_CROPS = ["Maize","Beans","Potatoes (Irish)","Cassava","Sorghum","Rice","Banana","Sweet Potatoes"];
const CROP_E = {"Maize":"🌽","Beans":"🫘","Potatoes (Irish)":"🥔","Cassava":"🌿","Sorghum":"🌾","Rice":"🍚","Banana":"🍌","Sweet Potatoes":"🍠"};

const priceData = [{w:"W1 Apr",a:320},{w:"W2 Apr",a:335},{w:"W3 Apr",a:310},{w:"W4 Apr",a:345},{w:"W1 May",a:360},{w:"W2 May",a:375},{w:"W3 May",a:368,f:370},{w:"W4 May",f:385},{w:"W1 Jun",f:402},{w:"W2 Jun",f:418},{w:"W3 Jun",f:430}];
const weather5d = [{day:"Thu",temp:21,hum:89,icon:"🌧️"},{day:"Fri",temp:22,hum:82,icon:"⛅"},{day:"Sat",temp:23,hum:75,icon:"☀️"},{day:"Sun",temp:20,hum:88,icon:"🌧️"},{day:"Mon",temp:19,hum:91,icon:"🌧️"}];

const Badge = ({level}) => {
  const m = {HIGH:{bg:"#FEE2E2",c:"#991B1B"},MEDIUM:{bg:"#FEF3C7",c:"#92400E"},LOW:{bg:"#ECFDF5",c:"#065F46"}};
  const s=m[level]||m.LOW;
  return <span style={{background:s.bg,color:s.c,padding:"4px 14px",borderRadius:20,fontSize:12,fontWeight:700}}>{level}</span>;
};
const Card = ({children,style={}}) => <div style={{background:C.card,borderRadius:12,border:`1px solid ${C.brdL}`,padding:20,boxShadow:"0 1px 3px rgba(0,0,0,.04)",...style}}>{children}</div>;
const Label = ({children}) => <p style={{fontSize:11,fontWeight:700,color:C.light,letterSpacing:1.5,textTransform:"uppercase",marginBottom:10}}>{children}</p>;
const Sel = ({value,onChange,options,label}) => <div style={{flex:1}}><label style={{fontSize:12,fontWeight:600,color:C.mut,display:"block",marginBottom:4}}>{label}</label><select value={value} onChange={e=>onChange(e.target.value)} style={{width:"100%",padding:"8px 12px",borderRadius:8,border:`1px solid ${C.brd}`,fontSize:13,color:C.txt,background:"#FFF"}}>{options.map(o=><option key={o}>{o}</option>)}</select></div>;

// ═══ SIDEBAR ═══
function Sidebar({screen,go}) {
  const items = [{k:"home",icon:<Home size={18}/>,l:"Home"},{k:"price",icon:<TrendingUp size={18}/>,l:"Price Forecast"},{k:"risk",icon:<AlertTriangle size={18}/>,l:"Seasonal Risk"},{k:"disease",icon:<Bug size={18}/>,l:"Disease Alert"},{k:"input",icon:<ShoppingCart size={18}/>,l:"Input Recommender"},{k:"whatsapp",icon:<MessageSquare size={18}/>,l:"WhatsApp Preview"}];
  return <div style={{width:220,background:C.sidebar,height:"100vh",position:"fixed",left:0,top:0,display:"flex",flexDirection:"column",padding:"0",zIndex:10}}>
    <div style={{padding:"20px 16px 16px",display:"flex",alignItems:"center",gap:10,borderBottom:"1px solid rgba(255,255,255,.1)"}}>
      <div style={{width:32,height:32,borderRadius:8,background:C.sideActive,display:"flex",alignItems:"center",justifyContent:"center"}}><Leaf size={18} color="#FFF"/></div>
      <div><p style={{color:"#FFF",fontWeight:800,fontSize:15}}>AgriRisk</p><p style={{color:C.g400,fontSize:10}}>Rwanda • 30 Districts</p></div>
    </div>
    <div style={{flex:1,padding:"12px 8px"}}>
      <p style={{fontSize:10,color:C.g400,letterSpacing:1,textTransform:"uppercase",padding:"8px 10px 4px",fontWeight:600}}>Modules</p>
      {items.map(i=><button key={i.k} onClick={()=>go(i.k)} style={{width:"100%",display:"flex",alignItems:"center",gap:10,padding:"10px 12px",borderRadius:8,border:"none",cursor:"pointer",marginBottom:2,background:screen===i.k?C.sideActive:"transparent",color:screen===i.k?"#FFF":C.g300,fontSize:13,fontWeight:screen===i.k?700:500,textAlign:"left",transition:"all .15s"}}>
        {i.icon}<span>{i.l}</span>
      </button>)}
    </div>
    <div style={{padding:"12px 16px",borderTop:"1px solid rgba(255,255,255,.1)"}}>
      <div style={{display:"flex",alignItems:"center",gap:8}}><div style={{width:28,height:28,borderRadius:"50%",background:C.sideActive,display:"flex",alignItems:"center",justifyContent:"center",fontSize:11,color:"#FFF",fontWeight:700}}>EU</div><div><p style={{color:"#FFF",fontSize:12,fontWeight:600}}>Elyse U.</p><p style={{color:C.g400,fontSize:10}}>Extension Officer</p></div></div>
    </div>
  </div>;
}

// ═══ HOME ═══
function HomeScreen() {
  return <div>
    <h1 style={{fontSize:24,fontWeight:800,color:C.forest,marginBottom:4}}>Dashboard</h1>
    <p style={{color:C.mut,fontSize:14,marginBottom:24}}>Nationwide agricultural risk advisory platform</p>
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr 1fr",gap:12,marginBottom:24}}>
      {[{n:"30",l:"Districts",c:C.emerald},{n:"8",l:"Crops covered",c:C.g600},{n:"3",l:"Channels",c:C.amber},{n:"6",l:"Data sources",c:C.purple}].map((s,i)=><Card key={i}><p style={{fontSize:28,fontWeight:800,color:s.c}}>{s.n}</p><p style={{fontSize:12,color:C.mut,marginTop:2}}>{s.l}</p></Card>)}
    </div>
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:24}}>
      <Card style={{background:"#FFF8EC",borderColor:"#FDE68A"}}><div style={{display:"flex",alignItems:"center",gap:10,marginBottom:8}}><AlertTriangle size={20} color={C.amber}/><p style={{fontWeight:700,color:"#92400E",fontSize:14}}>Active alerts</p></div><p style={{fontSize:13,color:"#B45309"}}>Gray Leaf Spot <strong>HIGH</strong> for maize in Musanze, Burera, Gakenke</p><p style={{fontSize:13,color:"#B45309",marginTop:4}}>Cassava Mosaic Disease <strong>HIGH</strong> in Bugesera, Kayonza</p></Card>
      <Card><Label>Delivery channels</Label><div style={{display:"flex",gap:8}}>{[{i:"🖥️",t:"Dashboard",s:"Active"},{i:"💬",t:"WhatsApp",s:"Active"},{i:"📱",t:"SMS",s:"47 subscribers"}].map((c,i)=><div key={i} style={{flex:1,background:C.g50,borderRadius:8,padding:10,textAlign:"center"}}><p style={{fontSize:20}}>{c.i}</p><p style={{fontWeight:600,fontSize:12,color:C.forest,marginTop:4}}>{c.t}</p><p style={{fontSize:10,color:C.mut}}>{c.s}</p></div>)}</div></Card>
    </div>
    <Card><Label>ML model performance</Label>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr 1fr",gap:12}}>
        {[{m:"Prophet+CPI+Fert",v:"11.2%",l:"MAPE",t:"<15%",ok:true},{m:"LSTM",v:"9.8%",l:"MAPE",t:"<15%",ok:true},{m:"XGBoost",v:"88.3%",l:"Accuracy",t:">85%",ok:true},{m:"Random Forest",v:"86.1%",l:"Accuracy",t:">85%",ok:true}].map((m,i)=><div key={i} style={{background:C.g50,borderRadius:8,padding:12,textAlign:"center"}}><p style={{fontSize:22,fontWeight:800,color:m.ok?C.emerald:C.red}}>{m.v}</p><p style={{fontSize:11,color:C.mut,marginTop:2}}>{m.l} ({m.t})</p><p style={{fontSize:12,fontWeight:600,color:C.forest,marginTop:4}}>{m.m}</p></div>)}
      </div>
    </Card>
    <div style={{display:"flex",flexWrap:"wrap",gap:6,marginTop:16}}>{["WFP Rwanda","FRED CPI","World Bank","Open-Meteo","MINAGRI","HDX Rainfall"].map(s=><span key={s} style={{padding:"4px 12px",borderRadius:16,fontSize:11,fontWeight:600,background:C.g50,color:C.emerald,border:`1px solid ${C.brdL}`}}>{s}</span>)}</div>
  </div>;
}

// ═══ PRICE ═══
function PriceScreen() {
  const [crop,setCrop]=useState("Maize"),[dist,setDist]=useState("Musanze"),[loaded,setLoaded]=useState(false);
  return <div>
    <h1 style={{fontSize:24,fontWeight:800,color:C.forest,marginBottom:4}}>📈 Price Forecast</h1>
    <p style={{color:C.mut,fontSize:14,marginBottom:20}}>Prophet + CPI + Fertilizer • LSTM benchmark • 4-week ahead</p>
    <Card style={{marginBottom:16}}><div style={{display:"flex",gap:12,marginBottom:12}}><Sel label="Crop" value={crop} onChange={setCrop} options={ALL_CROPS}/><Sel label="District" value={dist} onChange={setDist} options={ALL_DISTRICTS}/></div>
      <button onClick={()=>setLoaded(true)} style={{width:"100%",padding:10,borderRadius:8,border:"none",cursor:"pointer",background:C.emerald,color:"#FFF",fontSize:14,fontWeight:700}}>Generate Forecast</button>
    </Card>
    {loaded&&<><div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12,marginBottom:16}}>
      <Card style={{background:`linear-gradient(135deg,${C.forest},${C.emerald})`,borderColor:"transparent"}}><p style={{color:C.g300,fontSize:11}}>Predicted (W4)</p><p style={{color:"#FFF",fontSize:28,fontWeight:800}}>430 <span style={{fontSize:12,fontWeight:400}}>RWF/kg</span></p></Card>
      <Card><p style={{color:C.mut,fontSize:11}}>Current price</p><p style={{color:C.forest,fontSize:28,fontWeight:800}}>368 <span style={{fontSize:12,fontWeight:400}}>RWF/kg</span></p></Card>
      <Card><p style={{color:C.mut,fontSize:11}}>Change</p><div style={{display:"flex",alignItems:"center",gap:4,marginTop:4}}><ArrowUp size={20} color="#059669"/><p style={{color:"#059669",fontSize:28,fontWeight:800}}>+16.8%</p></div></Card>
    </div>
    <Card style={{marginBottom:16}}><Label>Price trend & forecast — {CROP_E[crop]} {crop}, {dist}</Label>
      <ResponsiveContainer width="100%" height={220}><AreaChart data={priceData} margin={{top:5,right:10,left:0,bottom:0}}><defs><linearGradient id="ga" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={C.emerald} stopOpacity={.15}/><stop offset="95%" stopColor={C.emerald} stopOpacity={0}/></linearGradient><linearGradient id="gf" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={C.amber} stopOpacity={.15}/><stop offset="95%" stopColor={C.amber} stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke={C.brdL}/><XAxis dataKey="w" tick={{fontSize:11,fill:C.light}}/><YAxis tick={{fontSize:11,fill:C.light}}/><Tooltip contentStyle={{borderRadius:8,fontSize:12}}/><Area type="monotone" dataKey="a" stroke={C.emerald} strokeWidth={2.5} fill="url(#ga)" dot={{r:3}} name="Actual"/><Area type="monotone" dataKey="f" stroke={C.amber} strokeWidth={2.5} strokeDasharray="6 3" fill="url(#gf)" dot={{r:3}} name="Forecast"/></AreaChart></ResponsiveContainer>
      <div style={{display:"flex",justifyContent:"center",gap:20,marginTop:8}}><span style={{fontSize:11,color:C.emerald,display:"flex",alignItems:"center",gap:6}}>━━ Actual</span><span style={{fontSize:11,color:C.amber,display:"flex",alignItems:"center",gap:6}}>╌╌ Forecast</span></div>
    </Card>
    <Card style={{background:"#F0FDF4",borderColor:"#A7D8B4"}}><p style={{fontWeight:700,fontSize:13,color:"#166534",marginBottom:6}}>📊 Advisory</p><p style={{fontSize:13,color:"#15803D",lineHeight:1.6}}>{crop} prices in {dist} are trending <strong>upward</strong>. Recommend farmers <strong>hold stock 2–3 weeks</strong> to capture ~RWF 62/kg gain. Model: Prophet+CPI+Fertilizer (MAPE 11.2%). <em style={{fontSize:11,color:"#6B8A6E"}}>This is a decision support tool. Consult local market conditions before acting.</em></p></Card></>}
  </div>;
}

// ═══ RISK ═══
function RiskScreen() {
  const [dist,setDist]=useState("Bugesera"),[season,setSeason]=useState("2026A"),[loaded,setLoaded]=useState(false);
  const factors=[{icon:"🌧️",l:"Rainfall anomaly",v:"−1.4 SD",pct:82,d:true},{icon:"📈",l:"Food CPI change",v:"+22.4%",pct:91,d:true},{icon:"🧪",l:"Fertilizer price change",v:"+38%",pct:76,d:true},{icon:"🌾",l:"Historical yield",v:"Moderate",pct:58,d:false}];
  return <div>
    <h1 style={{fontSize:24,fontWeight:800,color:C.forest,marginBottom:4}}>⚠️ Seasonal Risk</h1>
    <p style={{color:C.mut,fontSize:14,marginBottom:20}}>Random Forest / XGBoost • Rainfall + CPI + Fertilizer</p>
    <Card style={{marginBottom:16}}><div style={{display:"flex",gap:12,marginBottom:12}}><Sel label="District" value={dist} onChange={setDist} options={ALL_DISTRICTS}/><Sel label="Season" value={season} onChange={setSeason} options={["2025B (Oct–Dec)","2026A (Mar–May)"]}/></div>
      <button onClick={()=>setLoaded(true)} style={{width:"100%",padding:10,borderRadius:8,border:"none",cursor:"pointer",background:C.amber,color:"#FFF",fontSize:14,fontWeight:700}}>Assess Risk</button>
    </Card>
    {loaded&&<><div style={{display:"grid",gridTemplateColumns:"1fr 2fr",gap:16,marginBottom:16}}>
      <Card style={{background:"#FEE2E2",borderColor:"#FCA5A5",textAlign:"center",display:"flex",flexDirection:"column",justifyContent:"center",alignItems:"center"}}><AlertTriangle size={36} color="#991B1B" style={{marginBottom:8}}/><p style={{fontSize:28,fontWeight:800,color:"#991B1B"}}>HIGH</p><p style={{fontSize:12,color:"#B91C1C"}}>{dist} — {season.split(" ")[0]}</p><p style={{fontSize:11,color:"#B91C1C",marginTop:4}}>Confidence: 87%</p></Card>
      <Card><Label>Contributing factors</Label><div style={{display:"flex",flexDirection:"column",gap:10}}>{factors.map((f,i)=><div key={i}><div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}><span style={{fontSize:13,color:C.txt}}>{f.icon} {f.l}</span><span style={{fontSize:13,fontWeight:700,color:f.d?"#DC2626":C.amber}}>{f.v}</span></div><div style={{background:C.g100,borderRadius:4,height:6,overflow:"hidden"}}><div style={{width:`${f.pct}%`,height:"100%",background:f.d?"linear-gradient(90deg,#F87171,#DC2626)":"linear-gradient(90deg,#FDE68A,#D97706)",borderRadius:4}}/></div></div>)}</div></Card>
    </div>
    <Card style={{background:"#FEF2F2",borderColor:"#FECACA"}}><p style={{fontWeight:700,fontSize:13,color:"#991B1B",marginBottom:6}}>⚠️ Advisory</p><p style={{fontSize:13,color:"#B91C1C",lineHeight:1.6}}>Below-average rainfall + high CPI + fertilizer surge = elevated food shortage risk in {dist}. Advise: <strong>drought-tolerant varieties</strong>, <strong>reduce input spend 20%</strong>, <strong>prioritize food crops</strong>.</p></Card></>}
  </div>;
}

// ═══ DISEASE ═══
function DiseaseScreen() {
  const [dist,setDist]=useState("Musanze"),[loaded,setLoaded]=useState(false);
  const diseases=[{crop:"Maize",disease:"Gray Leaf Spot",risk:"HIGH",emoji:"🌽",cond:"Humidity 89%, Temp 21°C — critical",action:"Apply fungicide within 48hrs."},{crop:"Cassava",disease:"Mosaic Disease",risk:"HIGH",emoji:"🌿",cond:"Humidity 72%, Temp 28°C — vector active",action:"Remove infected plants. Use certified cuttings."},{crop:"Potatoes (Irish)",disease:"Late Blight",risk:"MEDIUM",emoji:"🥔",cond:"Humidity 78%, Temp 17°C — approaching",action:"Monitor. Prepare copper-based fungicide."},{crop:"Beans",disease:"Angular Leaf Spot",risk:"LOW",emoji:"🫘",cond:"Humidity 62%, Temp 23°C — below",action:"No immediate action."}];
  return <div>
    <h1 style={{fontSize:24,fontWeight:800,color:C.forest,marginBottom:4}}>🦠 Disease Alert</h1>
    <p style={{color:C.mut,fontSize:14,marginBottom:20}}>Open-Meteo live weather + FAO disease rules • 8 crops</p>
    <Card style={{marginBottom:16}}><div style={{display:"flex",gap:12,alignItems:"flex-end"}}><Sel label="District" value={dist} onChange={setDist} options={ALL_DISTRICTS}/><button onClick={()=>setLoaded(true)} style={{padding:"8px 24px",borderRadius:8,border:"none",cursor:"pointer",background:C.red,color:"#FFF",fontSize:13,fontWeight:700,whiteSpace:"nowrap",marginBottom:1}}>Check Risk</button></div></Card>
    {loaded&&<><Card style={{marginBottom:16}}><Label>5-day weather — {dist} (live Open-Meteo)</Label><div style={{display:"flex",gap:8}}>{weather5d.map((w,i)=><div key={i} style={{flex:1,textAlign:"center",background:i===0?C.g50:"#FFF",borderRadius:8,padding:"8px 0"}}><p style={{fontSize:11,color:C.mut}}>{w.day}</p><p style={{fontSize:24,margin:"4px 0"}}>{w.icon}</p><p style={{fontSize:14,fontWeight:700,color:C.forest}}>{w.temp}°C</p><p style={{fontSize:10,color:C.mut}}>💧{w.hum}%</p></div>)}</div></Card>
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>{diseases.map((d,i)=><Card key={i} style={{borderColor:d.risk==="HIGH"?"#FCA5A5":d.risk==="MEDIUM"?"#FDE68A":C.brdL}}><div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}><div style={{display:"flex",alignItems:"center",gap:8}}><span style={{fontSize:24}}>{d.emoji}</span><div><p style={{fontWeight:700,fontSize:14,color:C.forest}}>{d.crop}</p><p style={{fontSize:11,color:C.mut}}>{d.disease}</p></div></div><Badge level={d.risk}/></div><div style={{background:C.g50,borderRadius:6,padding:"6px 10px",marginBottom:6}}><p style={{fontSize:11,color:C.mut}}>🌡️ {d.cond}</p></div><p style={{fontSize:12,color:d.risk==="HIGH"?"#991B1B":d.risk==="MEDIUM"?"#92400E":"#065F46",lineHeight:1.5}}><strong>Action:</strong> {d.action}</p></Card>)}</div></>}
  </div>;
}

// ═══ INPUT ═══
function InputScreen() {
  const [crop,setCrop]=useState("Maize"),[dist,setDist]=useState("Musanze"),[budget,setBudget]=useState(60000),[loaded,setLoaded]=useState(false);
  const recs=[{rank:1,name:"DAP Fertilizer (50kg)",type:"Fertilizer",price:45000,supplier:"Agro-Dealers Musanze",saving:"12% below avg",match:96},{rank:2,name:"Imidacloprid 200SL (1L)",type:"Pesticide",price:8500,supplier:"RAB Input Shop",saving:"8% below avg",match:91},{rank:3,name:"Hybrid Maize Seed PAN 53",type:"Seed",price:6200,supplier:"Rwanda Seed Co.",saving:"Best value",match:87}];
  return <div>
    <h1 style={{fontSize:24,fontWeight:800,color:C.forest,marginBottom:4}}>🛒 Input Recommender</h1>
    <p style={{color:C.mut,fontSize:14,marginBottom:20}}>MINAGRI data • Budget-smart ranking • RWF</p>
    <Card style={{marginBottom:16}}><div style={{display:"flex",gap:12,marginBottom:12}}><Sel label="Crop" value={crop} onChange={setCrop} options={ALL_CROPS}/><Sel label="District" value={dist} onChange={setDist} options={ALL_DISTRICTS}/></div>
      <div style={{marginBottom:12}}><label style={{fontSize:12,fontWeight:600,color:C.mut}}>Farmer budget: <strong style={{color:C.purple}}>RWF {budget.toLocaleString()}</strong></label><input type="range" min={10000} max={150000} step={5000} value={budget} onChange={e=>setBudget(Number(e.target.value))} style={{width:"100%",accentColor:C.purple}}/></div>
      <button onClick={()=>setLoaded(true)} style={{width:"100%",padding:10,borderRadius:8,border:"none",cursor:"pointer",background:C.purple,color:"#FFF",fontSize:14,fontWeight:700}}>Get Recommendations</button>
    </Card>
    {loaded&&<div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12}}>{recs.map((r,i)=><Card key={i} style={{borderColor:i===0?C.purple:C.brdL,position:"relative"}}>{i===0&&<div style={{position:"absolute",top:-9,right:10,background:C.purple,color:"#FFF",fontSize:9,fontWeight:700,padding:"2px 8px",borderRadius:6}}>BEST MATCH</div>}<div style={{display:"flex",alignItems:"center",gap:8,marginBottom:10}}><div style={{width:28,height:28,borderRadius:"50%",background:`${C.purple}15`,color:C.purple,display:"flex",alignItems:"center",justifyContent:"center",fontSize:13,fontWeight:800}}>{r.rank}</div><div><p style={{fontWeight:700,fontSize:13,color:C.forest}}>{r.name}</p><p style={{fontSize:10,color:C.mut}}>{r.type}</p></div></div><p style={{fontSize:10,color:C.mut,marginBottom:6}}>{r.supplier}</p><div style={{display:"flex",justifyContent:"space-between",alignItems:"center",paddingTop:8,borderTop:`1px solid ${C.brdL}`}}><span style={{fontSize:18,fontWeight:800,color:C.forest}}>RWF {r.price.toLocaleString()}</span><span style={{fontSize:9,fontWeight:600,color:"#065F46",background:"#ECFDF5",padding:"2px 7px",borderRadius:6}}>{r.saving}</span></div></Card>)}</div>}
  </div>;
}

// ═══ WHATSAPP PREVIEW ═══
function WhatsAppScreen() {
  const msgs = [
    {from:"farmer",text:"Muraho AgriRisk",time:"10:32"},
    {from:"bot",text:"🌱 *AgriRisk Rwanda*\n\nNdashobora kukubwira:\n📈 *Ibiciro* — \"maize price bugesera\"\n⚠️ *Ibyago* — \"risk musanze\"\n🦠 *Indwara* — \"disease potato musanze\"\n🛒 *Ifumbire* — \"input maize bugesera 60000\"\n\nAndika igiciro, crop, na district.",time:"10:32"},
    {from:"farmer",text:"ibigori igiciro bugesera",time:"10:33"},
    {from:"bot",text:"🌽 *Maize — Bugesera*\n\n💰 Igiciro (mu byumweru 4): *RWF 430/kg*\n📈 Ibiciro biriyongera (+16.8%)\n\n💡 *Inama:* Bika umusaruro byibuze ibyumweru 2-3 kugira ngo ubone ibiciro byiza.\n\n⚠️ Ibi ni igikoresho cy'ubufasha mu gufata ibyemezo. Banza usabe inama umujyanama w'ubuhinzi.",time:"10:33"},
    {from:"farmer",text:"indwara ibirayi musanze",time:"10:35"},
    {from:"bot",text:"🥔 *Potato — Musanze*\n🦠 Late Blight: 🟡 MEDIUM\n🌡️ Humidity 78%, Temp 17°C\n\n➡️ Kurikirana neza. Tegura umuti wa copper-based fungicide niba humidity izamutse hejuru ya 85%.",time:"10:35"},
    {from:"farmer",text:"murakoze",time:"10:36"},
    {from:"bot",text:"Murakaza neza! 🌱 Andika *help* igihe cyose ukeneye ubufasha.",time:"10:36"},
  ];
  return <div>
    <h1 style={{fontSize:24,fontWeight:800,color:C.forest,marginBottom:4}}>💬 WhatsApp Preview</h1>
    <p style={{color:C.mut,fontSize:14,marginBottom:20}}>Farmer-facing chatbot • Kinyarwanda + English</p>
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:20}}>
      {/* Phone mockup */}
      <div style={{width:320,margin:"0 auto"}}>
        <div style={{background:"#000",borderRadius:28,padding:8,boxShadow:"0 8px 32px rgba(0,0,0,.2)"}}>
          <div style={{background:C.waBg,borderRadius:20,overflow:"hidden"}}>
            {/* WA Header */}
            <div style={{background:C.waDark,padding:"12px 14px",display:"flex",alignItems:"center",gap:10}}>
              <div style={{width:32,height:32,borderRadius:"50%",background:C.waLight,display:"flex",alignItems:"center",justifyContent:"center"}}><Leaf size={16} color="#FFF"/></div>
              <div><p style={{color:"#FFF",fontWeight:700,fontSize:13}}>AgriRisk Rwanda</p><p style={{color:"rgba(255,255,255,.7)",fontSize:10}}>online</p></div>
            </div>
            {/* Messages */}
            <div style={{padding:"12px 10px",height:420,overflowY:"auto"}}>
              {msgs.map((m,i)=><div key={i} style={{display:"flex",justifyContent:m.from==="farmer"?"flex-end":"flex-start",marginBottom:6}}>
                <div style={{maxWidth:"85%",background:m.from==="farmer"?C.waGreen:"#FFF",borderRadius:8,padding:"6px 10px",boxShadow:"0 1px 1px rgba(0,0,0,.1)"}}>
                  <p style={{fontSize:12,color:"#303030",whiteSpace:"pre-line",lineHeight:1.5}}>{m.text}</p>
                  <div style={{display:"flex",justifyContent:"flex-end",alignItems:"center",gap:3,marginTop:2}}><span style={{fontSize:9,color:"#8A8A8A"}}>{m.time}</span>{m.from==="farmer"&&<CheckCheck size={12} color="#53BDEB"/>}</div>
                </div>
              </div>)}
            </div>
            {/* Input */}
            <div style={{padding:"6px 8px",background:"#F0F0F0",display:"flex",gap:6,alignItems:"center"}}>
              <div style={{flex:1,background:"#FFF",borderRadius:20,padding:"8px 14px",fontSize:12,color:"#999"}}>Andika hano...</div>
              <div style={{width:32,height:32,borderRadius:"50%",background:C.waLight,display:"flex",alignItems:"center",justifyContent:"center"}}><Send size={14} color="#FFF"/></div>
            </div>
          </div>
        </div>
      </div>
      {/* Description */}
      <div>
        <Card style={{marginBottom:12}}><Label>Supported commands (Kinyarwanda)</Label>
          <div style={{display:"flex",flexDirection:"column",gap:8}}>
            {[{cmd:"ibigori igiciro bugesera",desc:"Maize price forecast for Bugesera"},{cmd:"risk musanze",desc:"Seasonal risk for Musanze"},{cmd:"indwara ibirayi musanze",desc:"Potato disease alert in Musanze"},{cmd:"input maize bugesera 60000",desc:"Input recommendations within RWF 60,000"},{cmd:"help / ubufasha",desc:"Show all available commands"}].map((c,i)=><div key={i} style={{background:C.g50,borderRadius:6,padding:"8px 10px"}}><p style={{fontSize:12,fontWeight:600,color:C.forest,fontFamily:"monospace"}}>{c.cmd}</p><p style={{fontSize:11,color:C.mut,marginTop:2}}>{c.desc}</p></div>)}
          </div>
        </Card>
        <Card><Label>Farmer reach</Label>
          <div style={{display:"flex",gap:8}}>
            {[{n:"47",l:"Subscribers"},{n:"30",l:"Districts"},{n:"🇷🇼",l:"Kinyarwanda"}].map((s,i)=><div key={i} style={{flex:1,textAlign:"center",background:C.g50,borderRadius:8,padding:10}}><p style={{fontSize:20,fontWeight:800,color:C.forest}}>{s.n}</p><p style={{fontSize:10,color:C.mut}}>{s.l}</p></div>)}
          </div>
        </Card>
      </div>
    </div>
  </div>;
}

// ═══ MAIN ═══
export default function App() {
  const [screen,setScreen]=useState("home");
  return <div style={{fontFamily:"'Inter',-apple-system,sans-serif",background:C.bg,minHeight:"100vh"}}>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
    <Sidebar screen={screen} go={setScreen}/>
    <div style={{marginLeft:220,padding:"24px 32px",maxWidth:960}}>
      {screen==="home"&&<HomeScreen/>}
      {screen==="price"&&<PriceScreen/>}
      {screen==="risk"&&<RiskScreen/>}
      {screen==="disease"&&<DiseaseScreen/>}
      {screen==="input"&&<InputScreen/>}
      {screen==="whatsapp"&&<WhatsAppScreen/>}
    </div>
  </div>;
}
