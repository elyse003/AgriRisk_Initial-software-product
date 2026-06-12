"""
Automated data refresh.

Pulls the latest figures from each public source so the models can be retrained
on current data. Sources differ in how reachable they are:

  - WFP food prices and CHIRPS rainfall live on HDX, which exposes a CKAN API,
    so they can be fetched automatically by dataset name.
  - The World Bank fertilizer "Pink Sheet" is a single monthly workbook at a
    stable-ish URL.
  - NISR food CPI is published as a manual download with no clean API, so it is
    left to the existing file and flagged as a manual step.

Nothing here runs on its own. Call refresh_all() (or run scripts/refresh_data.py)
on a schedule, for example once a month after the new releases are out. Network
access and the requests package are required.

The module also records, for every source, the latest date actually present in
the data ("data_through"). That is what the dashboard shows, because it is the
honest measure of how current the system is: these sources publish monthly, so
the freshest the platform can ever be is the most recent release.
"""
from __future__ import annotations

import json
import datetime as dt
from pathlib import Path

try:
    import requests
except ImportError:  # keeps the dashboard importable without requests installed
    requests = None

import pandas as pd

from config.settings import DATA_RAW, DATA_PROCESSED

# ---- source locations (verify these once; HDX slugs and the WB URL can move) ----
HDX_API = "https://data.humdata.org/api/3/action/package_show"
WFP_DATASET = "wfp-food-prices-for-rwanda"          # verified slug
RAINFALL_DATASET = "rwanda-rainfall-subnational"    # verify if the fetch 404s
WB_PINK_SHEET = (
    "https://thedocs.worldbank.org/en/doc/"
    "18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx"
)

STATUS_FILE = Path(DATA_PROCESSED) / "last_updated.json"

# processed file -> date column, used to read how current each series is
_PROCESSED = {
    "wfp_prices": ("wfp_food_prices_rwanda.csv", "date"),
    "cpi": ("rwanda_food_cpi.csv", "date"),
    "fertilizer": ("fertilizer_price_index.csv", "date"),
    "rainfall": ("district_rainfall_anomalies.csv", "date"),
}


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


# ----------------------------- fetching ---------------------------------------
def _require_requests():
    if requests is None:
        raise RuntimeError("the requests package is required: pip install requests")


def _hdx_csv_url(dataset_id: str) -> str:
    """Look up the first CSV resource download URL for an HDX dataset."""
    _require_requests()
    r = requests.get(HDX_API, params={"id": dataset_id}, timeout=60)
    r.raise_for_status()
    resources = r.json()["result"]["resources"]
    for res in resources:
        if (res.get("format") or "").lower() == "csv":
            return res.get("download_url") or res.get("url")
    raise RuntimeError(f"no CSV resource found for HDX dataset '{dataset_id}'")


def _download(url: str, dest: Path) -> Path:
    _require_requests()
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def fetch_wfp_prices() -> Path:
    return _download(_hdx_csv_url(WFP_DATASET), Path(DATA_RAW) / "wfp_food_prices_rwa.csv")


def fetch_rainfall() -> Path:
    return _download(_hdx_csv_url(RAINFALL_DATASET), Path(DATA_RAW) / "rwa-rainfall-subnat-full.csv")


def fetch_fertilizer() -> Path:
    return _download(WB_PINK_SHEET, Path(DATA_RAW) / "CMO-Historical-Data-Monthly.xlsx")


# auto-fetchable sources only; CPI stays manual
FETCHERS = {
    "wfp_prices": fetch_wfp_prices,
    "rainfall": fetch_rainfall,
    "fertilizer": fetch_fertilizer,
}


# ----------------------------- status -----------------------------------------
def load_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_status(status: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def update_data_through(status: dict | None = None) -> dict:
    """Record the latest date present in each processed series."""
    status = status or load_status()
    for key, (fname, col) in _PROCESSED.items():
        p = Path(DATA_PROCESSED) / fname
        entry = status.get(key, {})
        if p.exists():
            try:
                d = pd.read_csv(p, parse_dates=[col])
                entry["data_through"] = d[col].max().strftime("%Y-%m")
            except Exception as e:
                entry["data_through_error"] = str(e)
        status[key] = entry
    save_status(status)
    return status


def refresh_all() -> dict:
    """Fetch every auto-fetchable source, then record how current the data is."""
    _require_requests()
    status = load_status()
    for name, fetch in FETCHERS.items():
        entry = status.get(name, {})
        try:
            fetch()
            entry["refreshed"] = _now()
            entry["ok"] = True
            entry.pop("error", None)
        except Exception as e:
            entry["ok"] = False
            entry["error"] = str(e)
        status[name] = entry
    # CPI is a manual NISR download
    cpi = status.get("cpi", {})
    cpi.setdefault("note", "manual NISR download")
    status["cpi"] = cpi
    save_status(status)
    return status


if __name__ == "__main__":
    s = update_data_through()
    print(json.dumps(s, indent=2))
