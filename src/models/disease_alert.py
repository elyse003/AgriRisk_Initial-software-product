"""Module 3: climate-driven crop disease alerts.

Fully rule-based (no trained model). Pulls a 14-day forecast from the
Open-Meteo API and evaluates the FAO-style disease conditions defined in
config.settings.DISEASE_RULES. This module is complete enough to run once
`requests` is installed and you pass real coordinates.
"""
from __future__ import annotations

import requests

from config.settings import DISEASE_RULES, OPEN_METEO_URL


def fetch_forecast(lat: float, lon: float) -> dict:
    """Get daily temp / humidity / precipitation for the next 14 days."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,"
                 "relative_humidity_2m_mean,precipitation_sum",
        "forecast_days": 14,
        "timezone": "Africa/Kigali",
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()["daily"]


def assess_crop_full(crop: str, daily: dict) -> list[dict]:
    """Assess EVERY disease for one crop (including Low risk), each with its
    current risk level and the recommended action — so the app can always show a
    recommendation, not only when a threshold is crossed."""
    out = []
    temps = [(lo + hi) / 2 for lo, hi in
             zip(daily["temperature_2m_min"], daily["temperature_2m_max"])]
    humidity = daily["relative_humidity_2m_mean"]
    rain = daily["precipitation_sum"]
    rain_days = sum(1 for r in rain if r and r > 1.0)

    for rule in DISEASE_RULES.get(crop, []):
        lo, hi = rule["temp_c"]
        temp_ok = any(lo <= t <= hi for t in temps)
        humid_ok = any(h >= rule["humidity_pct"] for h in humidity)
        rain_ok = rain_days >= rule["rain_days"]

        triggers = sum([temp_ok, humid_ok, rain_ok])
        level = "High" if triggers == 3 else "Medium" if triggers == 2 else "Low"
        out.append({
            "crop": crop,
            "disease": rule["name"],
            "risk": level,
            "action": rule["action"],
            "why": {"temperature": temp_ok, "humidity": humid_ok,
                    "rainy_days": rain_days},
        })
    return out


def assess_crop(crop: str, daily: dict) -> list[dict]:
    """Return only the triggered (Medium/High) disease alerts for one crop."""
    return [a for a in assess_crop_full(crop, daily) if a["risk"] != "Low"]


def get_all_alerts(lat: float, lon: float, crops: list[str]) -> list[dict]:
    """Convenience wrapper: forecast once, assess every crop, sort by severity."""
    daily = fetch_forecast(lat, lon)
    out: list[dict] = []
    for crop in crops:
        out.extend(assess_crop(crop, daily))
    order = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(out, key=lambda a: order[a["risk"]])
