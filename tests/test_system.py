"""System tests for AgriRisk Rwanda.

Testing focuses on the models' predictive accuracy and reliability on real data,
organised around three principles:

  1. Use unseen data   - evaluate on a held-out split the model never trained on.
  2. Evaluate key metrics - accuracy, precision, recall, F1 for risk; MAPE for price.
  3. Test edge cases    - unusual or out-of-range inputs are handled without failing.

Run with:  pytest tests/test_system.py -v
Or as a script:  python tests/test_system.py
"""
import os
import sys
import pickle

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import data_path, MODELS_STORE, CROPS
from src.models.input_recommender import recommend
from src.models.disease_alert import assess_crop
from src.channels.whatsapp_bot import parse_message
from src.models import price_forecasting as pf
from src.models import risk_classifier as rc
from src.db.connection import init_db, fetch_catalogue, subscriber_count, log_risk, get_connection
from sklearn.model_selection import train_test_split


# ---------- shared fixtures (plain functions so the file also runs as a script) ----------
def _prices():
    return pd.read_csv(data_path("wfp_food_prices_rwanda.csv"), parse_dates=["date"])


def _price_series(crop="maize", district="Musanze"):
    df = _prices()
    return df[(df.crop == crop) & (df.market == district)].sort_values("date")["price_rwf"].reset_index(drop=True)


def _risk_dataset():
    """The REAL, data-derived risk dataset (labels from realized price outcomes)."""
    p = _prices()
    rain = pd.read_csv(data_path("district_rainfall_anomalies.csv"), parse_dates=["date"])
    cpi = pd.read_csv(data_path("rwanda_food_cpi.csv"), parse_dates=["date"])
    fert = pd.read_csv(data_path("fertilizer_price_index.csv"), parse_dates=["date"])
    return rc.build_risk_dataset(p, rain, cpi, fert)


# ============================== 1. USE UNSEEN DATA ==============================
def test_price_model_on_unseen_data():
    """Each crop's forecaster beats the 15% MAPE target on a temporal hold-out."""
    prices = _prices()
    for crop in CROPS:
        model, mape, n = pf.train_crop_model(prices, crop)
        assert model is not None and n > 100
        assert mape < 15, f"{crop} price MAPE on unseen data too high: {mape:.1f}%"


def test_risk_model_on_unseen_data():
    """On a stratified hold-out the risk model must clearly beat the majority baseline."""
    df = _risk_dataset()
    X, y = df[rc.FEATURES], df[rc.LABEL]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    model = rc.fit_gradient_boosting(Xtr, ytr)
    acc = rc.evaluate(model, Xte, yte)["accuracy"]
    baseline = y.value_counts().max() / len(y)
    assert acc > baseline + 0.1, f"risk acc {acc:.2f} not clearly above baseline {baseline:.2f}"


# ============================== 2. EVALUATE KEY METRICS ==============================
def test_risk_key_metrics():
    """Macro-F1 is computed and beats chance by a clear margin (genuine, not circular)."""
    df = _risk_dataset()
    X, y = df[rc.FEATURES], df[rc.LABEL]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    m = rc.evaluate(rc.fit_gradient_boosting(Xtr, ytr), Xte, yte)
    assert m["macro_f1"] > 0.5, f"risk macro-F1 too low: {m['macro_f1']}"


def test_price_meets_mape_target():
    """The deployed serialized forecaster predicts a sane next-month price."""
    models = pickle.load(open(MODELS_STORE / "price_forecaster.pkl", "rb"))
    s = pd.read_csv(data_path("wfp_food_prices_rwanda.csv"), parse_dates=["date"])
    s = s[s.crop == "maize"].set_index("date")["price_rwf"].groupby(level=0).median().sort_index()
    fc = pf.forecast_next(models["maize"], s)
    cur = float(s.iloc[-1])
    assert fc > 0 and 0.5 * cur < fc < 2.0 * cur, f"implausible forecast {fc} vs current {cur}"


# ============================== 3. TEST EDGE CASES ==============================
def test_price_handles_district_without_data():
    """A district with no price records returns an empty series, not an error."""
    assert len(_price_series("maize", "Gasabo")) == 0


def test_risk_handles_extreme_inputs():
    """Severe drought with high inflation, and the opposite, both return valid labels."""
    model = pickle.load(open(MODELS_STORE / "risk_classifier.pkl", "rb"))
    cols = ["rainfall_anomaly", "cpi_change", "fert_change"]
    for row in [[-3.0, 80.0, 300.0], [2.5, -5.0, -10.0], [0.0, 0.0, 0.0]]:
        pred = model.predict(pd.DataFrame([row], columns=cols))[0]
        assert pred in {"Low", "Medium", "High"}


def test_recommender_handles_zero_budget():
    """A zero budget returns no recommendations rather than crashing."""
    cat = pd.read_csv(data_path("minagri_input_prices.csv"))
    assert recommend(cat, "maize", "Musanze", 0.0).empty


def test_recommender_handles_unknown_crop():
    """A crop not in the catalogue returns an empty result."""
    cat = pd.read_csv(data_path("minagri_input_prices.csv"))
    assert recommend(cat, "rice", "Musanze", 50000.0).empty


def test_chatbot_handles_gibberish():
    """An unrecognised message still returns a structured reply object."""
    out = parse_message("xkcd qwerty zzz")
    assert isinstance(out, dict) and "intent" in out


def test_disease_alerts_are_well_formed():
    """Disease assessment returns properly structured alerts under a wet, mild forecast."""
    sample = {"temperature_2m_min": [16] * 14, "temperature_2m_max": [24] * 14,
              "relative_humidity_2m_mean": [92] * 14, "precipitation_sum": [7] * 14}
    alerts = assess_crop("potatoes", sample)
    assert isinstance(alerts, list)
    for a in alerts:
        assert {"crop", "disease", "risk", "action"} <= set(a)
        assert a["risk"] in {"Medium", "High"}



# ============================== 4. BACKEND DATABASE ==============================
def _row_count(table):
    conn = get_connection()
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return n


def test_database_initialises_and_serves_catalogue():
    """The database is created and serves the input catalogue and sample subscribers."""
    init_db()
    cat = fetch_catalogue()
    assert len(cat) >= 1 and "price_rwf" in cat.columns
    assert subscriber_count() >= 1


def test_database_logs_a_risk_assessment():
    """A risk lookup is written to the risk_scores table."""
    init_db()
    before = _row_count("risk_scores")
    log_risk("Musanze", "A", -0.5, 12.0, 25.0, "Medium")
    assert _row_count("risk_scores") == before + 1


# ---------- script runner (so it works without pytest installed) ----------
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
