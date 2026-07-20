"""Central configuration for AgriRisk Rwanda.

All tunable constants live here so the rest of the codebase reads from one
place. Thresholds below are taken directly from the proposal (Chapter 3.4.1
preprocessing rules and Chapter 1/2 disease conditions).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- paths ---
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
MODELS_STORE = ROOT / "models_store"
MODELS_STORE.mkdir(exist_ok=True)


def data_path(name):
    """Prefer real processed data; fall back to the synthetic sample file."""
    p = DATA_PROCESSED / name
    return p if p.exists() else DATA_RAW / name

# --- target crops & pilot districts ---
CROPS = ["maize", "beans", "potatoes"]
PILOT_DISTRICTS = ["Musanze", "Bugesera"]
LANGUAGES = ["rw", "en"]  # Kinyarwanda, English

# --- all 30 districts of Rwanda ---
# Ordered for the farmer audience: Musanze (a key farming district) leads and is
# the sensible default; the three Kigali City districts are urban, so they sit
# LAST. This order drives every district dropdown in the app.
DISTRICTS = [
    # Northern (Musanze first — default)
    "Musanze", "Burera", "Gakenke", "Gicumbi", "Rulindo",
    # Southern
    "Gisagara", "Huye", "Kamonyi", "Muhanga", "Nyamagabe", "Nyanza", "Nyaruguru", "Ruhango",
    # Eastern
    "Bugesera", "Gatsibo", "Kayonza", "Kirehe", "Ngoma", "Nyagatare", "Rwamagana",
    # Western
    "Karongi", "Ngororero", "Nyabihu", "Nyamasheke", "Rubavu", "Rusizi", "Rutsiro",
    # Kigali City (urban — listed last)
    "Nyarugenge", "Gasabo", "Kicukiro",
]

# approximate district-centre coordinates (lat, lon) for the weather API
DISTRICT_COORDS = {
    "Nyarugenge": (-1.950, 30.060), "Gasabo": (-1.920, 30.100), "Kicukiro": (-1.980, 30.100),
    "Burera": (-1.470, 29.850), "Gakenke": (-1.700, 29.780), "Gicumbi": (-1.580, 30.100),
    "Musanze": (-1.499, 29.635), "Rulindo": (-1.770, 29.990),
    "Gisagara": (-2.620, 29.830), "Huye": (-2.595, 29.739), "Kamonyi": (-2.000, 29.900),
    "Muhanga": (-2.080, 29.750), "Nyamagabe": (-2.470, 29.430), "Nyanza": (-2.350, 29.750),
    "Nyaruguru": (-2.650, 29.550), "Ruhango": (-2.180, 29.780),
    "Bugesera": (-2.211, 30.193), "Gatsibo": (-1.580, 30.420), "Kayonza": (-1.880, 30.620),
    "Kirehe": (-2.220, 30.710), "Ngoma": (-2.150, 30.500), "Nyagatare": (-1.293, 30.327),
    "Rwamagana": (-1.950, 30.430),
    "Karongi": (-2.000, 29.380), "Ngororero": (-1.870, 29.620), "Nyabihu": (-1.650, 29.500),
    "Nyamasheke": (-2.350, 29.130), "Rubavu": (-1.677, 29.260), "Rusizi": (-2.480, 28.900),
    "Rutsiro": (-1.930, 29.320),
}

# --- performance targets ---
MAPE_TARGET = 0.15        # price forecasting: MAPE < 15%
ACCURACY_TARGET = 0.85    # risk classification: accuracy > 85%
FORECAST_HORIZON_WEEKS = 4

# --- module 2: seasonal risk labels (rainfall anomaly in std-devs) ---
# High:   anomaly < -0.8 AND (cpi_change > 15% OR fertilizer_change > 30%)
# Medium: anomaly < -0.3  OR cpi_change > 10% OR fertilizer_change > 20%
# Low:    otherwise
RISK_THRESHOLDS = {
    "high": {"rain": -0.8, "cpi": 15.0, "fert": 30.0},
    "medium": {"rain": -0.3, "cpi": 10.0, "fert": 20.0},
}

# --- module 3: disease rule base (FAO-style climate conditions) ---
# Triggered when forecast weather sustains these conditions.
DISEASE_RULES = {
    "maize": [
        {"name": "Gray Leaf Spot",
         "temp_c": (22, 30), "humidity_pct": 80, "rain_days": 3,
         "action": "Apply preventive fungicide; improve field drainage."},
        {"name": "Northern Leaf Blight",
         "temp_c": (18, 27), "humidity_pct": 85, "rain_days": 4,
         "action": "Scout lower leaves; rotate with non-host crop next season."},
    ],
    "potatoes": [
        {"name": "Late Blight",
         "temp_c": (15, 24), "humidity_pct": 90, "rain_days": 2,
         "action": "Apply protectant fungicide before rains; remove infected foliage."},
    ],
    "beans": [
        {"name": "Angular Leaf Spot",
         "temp_c": (18, 25), "humidity_pct": 85, "rain_days": 3,
         "action": "Use certified seed; avoid overhead irrigation."},
    ],
}

# --- module 4: input recommender ---
MAX_RECOMMENDATIONS = 3   # Lobell et al. (2020): cap at 3 to avoid decision paralysis

# --- external APIs ---
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/agririsk")
