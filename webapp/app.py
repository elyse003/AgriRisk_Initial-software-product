"""AgriRisk Rwanda - Flask web application.

Serves a single-page dashboard and a JSON API backed by the trained models.
Run:  PYTHONPATH=. python webapp/app.py     (or)     flask --app webapp/app.py run
Then open http://localhost:5000
"""
from __future__ import annotations

import json
import os
import pickle
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request
from sklearn.ensemble import RandomForestRegressor

from config.settings import (CROPS, DATA_RAW, DATA_PROCESSED, DISTRICTS,
                             DISTRICT_COORDS, MODELS_STORE, data_path)
from src.channels.whatsapp_bot import parse_message
from src.models.disease_alert import assess_crop, get_all_alerts
from src.models.input_recommender import recommend

app = Flask(__name__)

# ----------------------------------------------------------------- load assets
PRICES = pd.read_csv(data_path("wfp_food_prices_rwanda.csv"), parse_dates=["date"])
CPI = pd.read_csv(data_path("rwanda_food_cpi.csv"), parse_dates=["date"]).sort_values("date")
FERT = pd.read_csv(data_path("fertilizer_price_index.csv"), parse_dates=["date"]).sort_values("date")
RAIN = pd.read_csv(data_path("district_rainfall_anomalies.csv"), parse_dates=["date"]).sort_values("date")
CATALOGUE = pd.read_csv(data_path("minagri_input_prices.csv"))
CPI["cpi_change"] = CPI["food_cpi"].pct_change(12) * 100
FERT["fert_change"] = FERT["fert_index"].pct_change(12) * 100

try:
    RISK_MODEL = pickle.load(open(MODELS_STORE / "risk_classifier.pkl", "rb"))
except Exception:
    RISK_MODEL = None
try:
    METRICS = json.load(open(MODELS_STORE / "metrics.json"))
except Exception:
    METRICS = {}

_forecast_cache: dict = {}


# ----------------------------------------------------------------- core logic
def forecast_price(crop: str, district: str) -> dict:
    key = (crop, district)
    s = (PRICES[(PRICES.crop == crop) & (PRICES.market == district)]
         .sort_values("date").set_index("date")["price_rwf"])
    if s.empty:
        return {"error": f"No price data for {crop} in {district}."}
    d = pd.DataFrame({"y": s})
    for lag in [1, 2, 3, 4, 8, 12, 52]:
        d[f"lag{lag}"] = d["y"].shift(lag)
    d["target"] = d["y"].shift(-4)
    train = d.dropna()
    feats = [c for c in d.columns if c.startswith("lag")]
    if key not in _forecast_cache:
        _forecast_cache[key] = RandomForestRegressor(
            n_estimators=150, random_state=42).fit(train[feats], train["target"])
    model = _forecast_cache[key]
    current = float(s.iloc[-1])
    forecast = float(model.predict(d[feats].iloc[[-1]])[0])
    pct = (forecast - current) / current * 100
    trend = "upward" if pct > 1 else "downward" if pct < -1 else "stable"

    hist = s.tail(26)
    future_dates = pd.date_range(hist.index[-1], periods=5, freq="W")[1:]
    fut_vals = np.linspace(current, forecast, 4)
    return {
        "crop": crop, "district": district,
        "current": round(current), "forecast": round(forecast),
        "pct": round(pct, 1), "trend": trend,
        "labels": [d.strftime("%b %d") for d in hist.index] + [d.strftime("%b %d") for d in future_dates],
        "history": [round(v) for v in hist.values] + [None] * 4,
        "future": [None] * len(hist) + [round(v) for v in fut_vals],
    }


def assess_risk(district: str, season: str) -> dict:
    r = RAIN[(RAIN.district == district) & (RAIN.season == season)]
    rain_a = float(r["rainfall_anomaly"].iloc[-1]) if not r.empty else float(RAIN["rainfall_anomaly"].mean())
    cpi_c = float(CPI["cpi_change"].dropna().iloc[-1])
    fert_c = float(FERT["fert_change"].dropna().iloc[-1])

    if RISK_MODEL is not None:
        feat = pd.DataFrame([[rain_a, cpi_c, fert_c]],
                            columns=["rainfall_anomaly", "cpi_change", "fert_change"])
        level = str(RISK_MODEL.predict(feat)[0])
        conf = round(float(RISK_MODEL.predict_proba(feat).max()) * 100)
    else:
        from src.data.preprocessing import label_risk
        level = label_risk(rain_a, cpi_c, fert_c); conf = None

    advisory = {
        "High": "High combined climate-economic risk. Advise conservative planting and minimal input spend.",
        "Medium": "Moderate risk. Monitor conditions; consider drought-tolerant varieties.",
        "Low": "Favourable conditions. Normal planting and input investment is reasonable.",
    }[level]
    return {"district": district, "season": season, "risk_level": level,
            "confidence": conf, "advisory": advisory,
            "factors": {"rainfall_anomaly": round(rain_a, 2),
                        "cpi_change": round(cpi_c, 1), "fert_change": round(fert_c, 1)}}


def disease_alerts(district: str) -> dict:
    lat, lon = DISTRICT_COORDS.get(district, (-1.94, 30.06))

    def icon(precip, hum):
        return "🌧️" if precip and precip > 5 else "⛅" if hum and hum > 80 else "☀️"

    try:
        from src.models.disease_alert import fetch_forecast
        daily = fetch_forecast(lat, lon)
        temps = [round((lo + hi) / 2) for lo, hi in
                 zip(daily["temperature_2m_min"], daily["temperature_2m_max"])]
        days = ["Day " + str(i + 1) for i in range(5)]
        weather = [{"day": days[i], "temp": temps[i],
                    "hum": round(daily["relative_humidity_2m_mean"][i]),
                    "icon": icon(daily["precipitation_sum"][i], daily["relative_humidity_2m_mean"][i])}
                   for i in range(5)]
        alerts = []
        for c in CROPS:
            alerts.extend(assess_crop(c, daily))
        order = {"High": 0, "Medium": 1, "Low": 2}
        alerts = sorted(alerts, key=lambda a: order[a["risk"]])
        live = True
    except Exception:
        sample = {"temperature_2m_min": [17] * 14, "temperature_2m_max": [23] * 14,
                  "relative_humidity_2m_mean": [88] * 14, "precipitation_sum": [6] * 14}
        weather = [{"day": f"Day {i+1}", "temp": 20, "hum": 88, "icon": "🌧️"} for i in range(5)]
        alerts = []
        for c in CROPS:
            alerts.extend(assess_crop(c, sample))
        live = False
    return {"district": district, "live": live, "weather": weather, "alerts": alerts}


# ----------------------------------------------------------------- routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/meta")
def meta():
    rf = METRICS.get("risk_random_forest", {})
    gb = METRICS.get("risk_gradient_boosting", {})
    return jsonify({
        "districts": DISTRICTS,
        "crops": CROPS,
        "seasons": [{"value": "A", "label": "Season A (Mar-May)"},
                    {"value": "B", "label": "Season B (Oct-Dec)"}],
        "metrics": {
            "price_mape": METRICS.get("price_baseline_mape"),
            "rf_accuracy": round(rf.get("accuracy", 0) * 100, 1) if rf else None,
            "gb_accuracy": round(gb.get("accuracy", 0) * 100, 1) if gb else None,
        },
        "data_sources": ["WFP Rwanda", "FRED CPI", "World Bank", "Open-Meteo", "MINAGRI", "HDX Rainfall"],
    })


@app.route("/api/forecast", methods=["POST"])
def api_forecast():
    j = request.get_json(force=True)
    return jsonify(forecast_price(j["crop"], j["district"]))


@app.route("/api/risk", methods=["POST"])
def api_risk():
    j = request.get_json(force=True)
    return jsonify(assess_risk(j["district"], j.get("season", "B")))


@app.route("/api/disease", methods=["POST"])
def api_disease():
    j = request.get_json(force=True)
    return jsonify(disease_alerts(j["district"]))


@app.route("/api/inputs", methods=["POST"])
def api_inputs():
    j = request.get_json(force=True)
    recs = recommend(CATALOGUE, j["crop"], j["district"], float(j["budget"]))
    items = [] if recs.empty else recs.to_dict("records")
    for it in items:
        it["price_rwf"] = int(it["price_rwf"])
        it["pct_saving"] = round(it["pct_saving"])
        it["match_score"] = round(it["match_score"], 2)
    total = sum(it["price_rwf"] for it in items)
    return jsonify({"recommendations": items, "total": total,
                    "remaining": int(j["budget"]) - total})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    j = request.get_json(force=True)
    p = parse_message(j["message"])
    lang = p["lang"]
    crop, district, budget = p["crop"], p["district"], p["budget"]

    if p["intent"] == "help" or p["intent"] is None and not (crop and district):
        reply = ("🌱 *AgriRisk Rwanda*\nNdashobora kugufasha:\n"
                 "📈 \"ibigori igiciro bugesera\"\n⚠️ \"risk musanze\"\n"
                 "🦠 \"indwara ibirayi musanze\"\n🛒 \"input maize bugesera 60000\""
                 if lang == "rw" else
                 "🌱 *AgriRisk Rwanda*\nI can help with:\n"
                 "📈 \"maize price bugesera\"\n⚠️ \"risk musanze\"\n"
                 "🦠 \"disease potato musanze\"\n🛒 \"input maize bugesera 60000\"")
        return jsonify({"reply": reply})

    district = district or "Bugesera"
    crop = crop or "maize"

    if p["intent"] == "price":
        f = forecast_price(crop, district)
        if lang == "rw":
            reply = (f"🌽 *{crop.title()} — {district}*\nIgiciro ubu: *{f['current']} RWF/kg*\n"
                     f"Mu byumweru 4: *{f['forecast']} RWF/kg* ({f['pct']:+}%)")
        else:
            reply = (f"🌽 *{crop.title()} — {district}*\nCurrent: *{f['current']} RWF/kg*\n"
                     f"In 4 weeks: *{f['forecast']} RWF/kg* ({f['pct']:+}%)")
    elif p["intent"] == "risk":
        r = assess_risk(district, "B")
        reply = (f"⚠️ *{district}*\nIbyago: *{r['risk_level']}*" if lang == "rw"
                 else f"⚠️ *{district}*\nRisk level: *{r['risk_level']}*")
    elif p["intent"] == "disease":
        a = disease_alerts(district)["alerts"]
        if crop:
            a = [x for x in a if x["crop"] == crop] or a
        if a:
            top = a[0]
            reply = f"🦠 *{district}* — {top['disease']} ({top['risk']})\n{top['action']}"
        else:
            reply = (f"🦠 *{district}*: nta byago by'indwara biri hejuru." if lang == "rw"
                     else f"🦠 *{district}*: no elevated disease risk.")
    elif p["intent"] == "input":
        recs = recommend(CATALOGUE, crop, district, float(budget or 50000))
        if recs.empty:
            reply = "Nta nyongeramusaruro ihuye n'ingengo y'imari." if lang == "rw" else "No inputs match that budget."
        else:
            lines = [f"{i}. {r.input_name} — {int(r.price_rwf):,} RWF"
                     for i, r in enumerate(recs.itertuples(), start=1)]
            head = f"🛒 *{crop.title()} — {district}*\n"
            reply = head + "\n".join(lines)
    else:
        reply = "Ntabwo numvise. Andika \"ubufasha\"." if lang == "rw" else "Sorry, I didn't understand. Type \"help\"."

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
