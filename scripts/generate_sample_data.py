"""Generate realistic SAMPLE datasets for AgriRisk Rwanda.

These are SYNTHETIC stand-ins with realistic structure and statistical
properties, used so the notebook and dashboard run end-to-end before the real
WFP / FRED / HDX / World Bank files are downloaded. Replace the files in
data/raw/ with the real downloads and everything else works unchanged.

Run:  python scripts/generate_sample_data.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import DATA_RAW, DISTRICTS

RNG = np.random.default_rng(42)

# eastern lowland districts trend drier (maize/beans); highlands favour potato
DRIER = {"Bugesera", "Nyagatare", "Gatsibo", "Kayonza", "Kirehe", "Ngoma", "Rwamagana"}
CROPS = ["maize", "beans", "potatoes"]
# realistic RWF/kg base price levels per crop
BASE_PRICE = {"maize": 380, "beans": 850, "potatoes": 280}
SEASON_AMP = {"maize": 70, "beans": 140, "potatoes": 90}


def _months(start, end):
    return pd.date_range(start, end, freq="MS")


def gen_cpi() -> pd.DataFrame:
    """Monthly food CPI index, 2015-2024, with a 2022-23 inflation spike."""
    m = _months("2015-01-01", "2024-12-01")
    t = np.arange(len(m))
    base = 100 + 0.30 * t                        # steady underlying inflation
    # 2022-23 food price spike, sized so YoY change peaks near the documented 22.4%
    spike = 26 * np.exp(-((t - 92) ** 2) / 70)
    cpi = base + spike + RNG.normal(0, 0.6, len(m))
    return pd.DataFrame({"date": m, "food_cpi": cpi.round(2)})


def gen_fertilizer() -> pd.DataFrame:
    """Monthly global fertilizer price index, with the 2021-23 +40% surge."""
    m = _months("2015-01-01", "2024-12-01")
    t = np.arange(len(m))
    base = 100 + 0.15 * t
    # Russia-Ukraine driven surge, sized so YoY change peaks near the documented +40%
    surge = 55 * np.exp(-((t - 86) ** 2) / 120)
    idx = base + surge + RNG.normal(0, 1.2, len(m))
    return pd.DataFrame({"date": m, "fert_index": idx.round(2)})


def gen_prices(cpi: pd.DataFrame, fert: pd.DataFrame) -> pd.DataFrame:
    """Weekly crop prices per market, driven by trend + seasonality + CPI."""
    weeks = pd.date_range("2018-01-01", "2024-12-29", freq="W")
    cpi_w = cpi.set_index("date")["food_cpi"].reindex(weeks, method="ffill").bfill()
    rows = []
    for crop in CROPS:
        for market in DISTRICTS:
            woy = weeks.isocalendar().week.to_numpy()
            seasonal = SEASON_AMP[crop] * np.sin(2 * np.pi * (woy - 10) / 52)
            inflation = BASE_PRICE[crop] * (cpi_w.to_numpy() / 100 - 1) * 0.8
            noise = RNG.normal(0, BASE_PRICE[crop] * 0.05, len(weeks))
            price = BASE_PRICE[crop] + seasonal + inflation + noise
            price = np.clip(price, BASE_PRICE[crop] * 0.4, None)
            rows.append(pd.DataFrame({
                "date": weeks, "market": market, "crop": crop,
                "price_rwf": price.round(0),
            }))
    return pd.concat(rows, ignore_index=True)


def gen_rainfall() -> pd.DataFrame:
    """Monthly per-district rainfall anomalies (std-dev units), 2015-2024.

    Includes drought events concentrated in 2021-2023 so that the seasonal
    risk dataset contains genuine High-risk cases (dry season coinciding with
    the inflation/fertilizer spike), plus normal Medium/Low conditions.
    """
    months = _months("2015-01-01", "2024-12-01")
    rows = []
    for d in DISTRICTS:
        # Eastern lowland districts trend drier
        bias = -0.35 if d in DRIER else 0.0
        for m in months:
            anomaly = RNG.normal(bias, 0.5)
            # drought pressure during 2021-2023 (overlaps inflation surge)
            if 2021 <= m.year <= 2023 and RNG.random() < 0.30:
                anomaly -= RNG.uniform(0.5, 1.2)
            season = "A" if m.month in (3, 4, 5) else "B" if m.month in (10, 11, 12) else "off"
            rows.append({"date": m, "district": d, "season": season,
                         "rainfall_anomaly": round(anomaly, 3)})
    df = pd.DataFrame(rows)
    return df[df["season"] != "off"].reset_index(drop=True)


def gen_inputs() -> pd.DataFrame:
    """MINAGRI-style input catalogue for the recommender."""
    items = [
        ("Urea (50kg)", "fertilizer", "maize,potatoes", 32000),
        ("NPK 17-17-17 (50kg)", "fertilizer", "maize,beans,potatoes", 38000),
        ("DAP (50kg)", "fertilizer", "maize,beans", 41000),
        ("Hybrid maize seed (10kg)", "seed", "maize", 12000),
        ("Climbing bean seed (5kg)", "seed", "beans", 8500),
        ("Certified potato seed (50kg)", "seed", "potatoes", 28000),
        ("Mancozeb fungicide (1kg)", "pesticide", "potatoes,beans", 9500),
        ("Lambda-cyhalothrin (1L)", "pesticide", "maize,beans", 14000),
        ("Organic compost (50kg)", "fertilizer", "maize,beans,potatoes", 6000),
        ("Foliar feed (1L)", "fertilizer", "potatoes", 11000),
    ]
    rows = []
    iid = 1
    for name, typ, crops, base in items:
        for d in DISTRICTS:
            price = int(base * RNG.uniform(0.92, 1.12))
            rows.append({"input_id": iid, "input_name": name, "input_type": typ,
                         "crop_suitability": crops, "supplier": f"{d} Agrodealer",
                         "district": d, "price_rwf": price})
            iid += 1
    return pd.DataFrame(rows)


def main():
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    cpi, fert = gen_cpi(), gen_fertilizer()
    cpi.to_csv(DATA_RAW / "rwanda_food_cpi.csv", index=False)
    fert.to_csv(DATA_RAW / "fertilizer_price_index.csv", index=False)
    gen_prices(cpi, fert).to_csv(DATA_RAW / "wfp_food_prices_rwanda.csv", index=False)
    gen_rainfall().to_csv(DATA_RAW / "district_rainfall_anomalies.csv", index=False)
    gen_inputs().to_csv(DATA_RAW / "minagri_input_prices.csv", index=False)
    print("Sample data written to", DATA_RAW)


if __name__ == "__main__":
    main()
