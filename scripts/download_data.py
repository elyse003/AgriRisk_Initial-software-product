"""Download the REAL public source files AgriRisk is built on, into data/raw/
under the exact names scripts/prepare_data.py expects.

All sources are open and free. After this runs, run:
    python scripts/prepare_data.py     # clean -> data/processed/
    python scripts/train_models.py     # train + serialize models

Sources
-------
- WFP / HDX        crop market prices (Maize, Beans, Irish potatoes), RWF
- HDX (CHIRPS)     subnational rainfall indicators, per district
- World Bank       Pink Sheet monthly commodity indices (Fertilizers)
- World Bank API   Rwanda consumer price index (macro inflation feature)

Run:  python scripts/download_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATA_RAW

DATA_RAW.mkdir(parents=True, exist_ok=True)

# Direct download URLs (resolved from the HDX / World Bank dataset pages).
WFP_PRICES_URL = ("https://data.humdata.org/dataset/a4a84c1c-81d1-491b-9fbe-1955ae736508/"
                  "resource/8c22eeb5-cc2e-46bc-8a0d-08b7486b2486/download/wfp_food_prices_rwa.csv")
RAINFALL_URL = ("https://data.humdata.org/dataset/80e9b2b6-a772-4390-89d8-5c50ad80c663/"
                "resource/a3eaa5a2-56ce-41a8-ad91-7ecbd65de8e8/download/rwa-rainfall-subnat-full.csv")
PINKSHEET_URL = ("https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/"
                 "related/CMO-Historical-Data-Monthly.xlsx")
# World Bank indicator FP.CPI.TOTL = Consumer Price Index (2010 = 100), Rwanda.
WB_CPI_URL = "https://api.worldbank.org/v2/country/RWA/indicator/FP.CPI.TOTL?format=json&per_page=500"


def _download(url: str, dest: Path, binary: bool = False) -> None:
    print(f"  downloading {dest.name} ...", end=" ", flush=True)
    r = requests.get(url, timeout=240, headers={"User-Agent": "AgriRisk/1.0"})
    r.raise_for_status()
    dest.write_bytes(r.content) if binary else dest.write_text(r.text, encoding="utf-8")
    print(f"{len(r.content):,} bytes")


def fetch_cpi() -> None:
    """World Bank annual CPI -> data/raw/worldbank_cpi_rwanda.csv [year, cpi]."""
    print("  downloading World Bank CPI ...", end=" ", flush=True)
    r = requests.get(WB_CPI_URL, timeout=120, headers={"User-Agent": "AgriRisk/1.0"})
    r.raise_for_status()
    rows = r.json()[1]
    cpi = pd.DataFrame([{"year": int(x["date"]), "cpi": x["value"]}
                        for x in rows if x["value"] is not None]).sort_values("year")
    out = DATA_RAW / "worldbank_cpi_rwanda.csv"
    cpi.to_csv(out, index=False)
    print(f"{len(cpi)} years ({cpi.year.min()}-{cpi.year.max()})")


def main() -> None:
    print("Downloading real public data -> data/raw/ ...")
    _download(WFP_PRICES_URL, DATA_RAW / "wfp_food_prices_rwa.csv")
    _download(RAINFALL_URL, DATA_RAW / "rwa-rainfall-subnat-full.csv")
    _download(PINKSHEET_URL, DATA_RAW / "CMO-Historical-Data-Monthly.xlsx", binary=True)
    fetch_cpi()
    print("Done. Next: python scripts/prepare_data.py")


if __name__ == "__main__":
    main()