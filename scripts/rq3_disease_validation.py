"""RQ3: does the climate-driven disease alert module fire when it should?

    RQ3: "How effectively does the climate-driven crop disease alert module using
    Open-Meteo weather forecast data and FAO seasonal disease calendar rules
    identify documented high-risk disease periods for maize, beans, and potato in
    the target districts, as validated against RAB historical disease outbreak
    records?"

HONEST SCOPE. RAB historical outbreak records are not publicly available, so this
script CANNOT perform the outbreak-level validation the proposal promised. What it
CAN do - and what is defensible - is a CLIMATOLOGICAL CONSISTENCY CHECK: replay the
FAO rules over several years of REAL historical weather (Open-Meteo archive) and
test whether alerts concentrate in Rwanda's two rainy seasons, when blight and
fungal disease actually occur agronomically.

Rwanda's cropping seasons: Season A short rains (Oct-Dec), Season B long rains
(Mar-May). Late Blight in the Musanze highlands is the canonical wet-season risk.

    python scripts/rq3_disease_validation.py            # 2020-2024, Musanze + Bugesera

Writes models_store/rq3_disease_validation.json. Requires internet (free API, no key).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import DISTRICT_COORDS, MODELS_STORE, CROPS   # noqa: E402
from src.models.disease_alert import assess_crop_full              # noqa: E402

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
START, END = "2020-01-01", "2024-12-31"
DISTRICTS = ["Musanze", "Bugesera"]      # the proposal's pilot districts
WINDOW = 14                              # same horizon the live module uses
RAINY_MONTHS = {3, 4, 5, 10, 11, 12}     # Season B (Mar-May) + Season A (Oct-Dec)


def fetch_archive(lat: float, lon: float) -> dict:
    """Daily temp / precip / mean-RH for START..END (ERA5 reanalysis, free, no key)."""
    r = requests.get(ARCHIVE, timeout=120, params={
        "latitude": lat, "longitude": lon, "start_date": START, "end_date": END,
        "daily": ("temperature_2m_max,temperature_2m_min,precipitation_sum,"
                  "relative_humidity_2m_mean"),
        "timezone": "Africa/Kigali"})
    r.raise_for_status()
    d = r.json()["daily"]
    return {k: d[k] for k in ("time", "temperature_2m_max", "temperature_2m_min",
                              "precipitation_sum", "relative_humidity_2m_mean")}


def windows(daily: dict, size: int = WINDOW):
    """Yield (end_date, 14-day slice shaped like the live forecast payload)."""
    n = len(daily["time"])
    for i in range(0, n - size + 1, 7):          # step a week
        sl = slice(i, i + size)
        yield daily["time"][i + size - 1], {
            "temperature_2m_min": daily["temperature_2m_min"][sl],
            "temperature_2m_max": daily["temperature_2m_max"][sl],
            "relative_humidity_2m_mean": daily["relative_humidity_2m_mean"][sl],
            "precipitation_sum": daily["precipitation_sum"][sl],
        }


def main():
    out = {"period": f"{START}..{END}", "window_days": WINDOW,
           "note": ("Climatological consistency check against real historical weather. "
                    "NOT validated against RAB outbreak records (not publicly available)."),
           "districts": {}}

    for dist in DISTRICTS:
        lat, lon = DISTRICT_COORDS[dist]
        print(f"fetching {dist} ({START}..{END}) ...")
        daily = fetch_archive(lat, lon)

        # alerts[disease][month] = count of elevated (Medium/High) windows
        alerts = defaultdict(lambda: defaultdict(int))
        per_month_windows = defaultdict(int)
        for end_iso, win in windows(daily):
            month = int(end_iso[5:7])
            per_month_windows[month] += 1
            for crop in CROPS:
                for a in assess_crop_full(crop, win):
                    if a["risk"] != "Low":
                        alerts[f"{a['disease']} ({crop})"][month] += 1

        dres = {}
        for disease, months in alerts.items():
            rate = {m: months.get(m, 0) / per_month_windows[m] for m in range(1, 13)}
            wet = np.mean([rate[m] for m in sorted(RAINY_MONTHS)])
            dry = np.mean([rate[m] for m in range(1, 13) if m not in RAINY_MONTHS])
            lift = (wet / dry) if dry > 0 else float("inf")
            peak = max(rate, key=rate.get)
            dres[disease] = {
                "alert_rate_rainy_seasons": round(float(wet), 3),
                "alert_rate_dry_months": round(float(dry), 3),
                "wet_over_dry_lift": (round(float(lift), 2) if np.isfinite(lift) else "inf"),
                "peak_month": peak,
                "peak_in_rainy_season": peak in RAINY_MONTHS,
                "monthly_rate": {str(m): round(float(rate[m]), 3) for m in range(1, 13)},
            }
        out["districts"][dist] = dres

        print(f"\n=== {dist} ===")
        print(f"{'disease (crop)':34} {'wet':>6} {'dry':>6} {'lift':>7} {'peak':>5} {'in-season':>10}")
        for k, v in sorted(dres.items(), key=lambda kv: -kv[1]["alert_rate_rainy_seasons"]):
            print(f"{k:34} {v['alert_rate_rainy_seasons']:>6.2f} {v['alert_rate_dry_months']:>6.2f} "
                  f"{str(v['wet_over_dry_lift']):>7} {v['peak_month']:>5} "
                  f"{'YES' if v['peak_in_rainy_season'] else 'no':>10}")

    MODELS_STORE.mkdir(parents=True, exist_ok=True)
    (MODELS_STORE / "rq3_disease_validation.json").write_text(json.dumps(out, indent=2))
    print("\nSaved models_store/rq3_disease_validation.json")
    print("Interpretation: lift > 1 and a peak month inside Oct-Dec / Mar-May means the\n"
          "rules fire in the agronomically correct season. This is consistency evidence,\n"
          "not outbreak-level validation.")


if __name__ == "__main__":
    main()