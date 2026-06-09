"""Data preprocessing & feature engineering for AgriRisk Rwanda.

Reads raw files from data/raw/, cleans them, engineers features, and writes
analysis-ready tables to data/processed/.

The risk-labelling function below is fully implemented from the proposal
thresholds. The per-source cleaning functions are stubbed with the expected
steps; fill them in once you've inspected the actual column names in each
downloaded file.
"""
from __future__ import annotations

import pandas as pd

from config.settings import DATA_RAW, DATA_PROCESSED, RISK_THRESHOLDS


# ---------------------------------------------------------------- price data
def load_price_data() -> pd.DataFrame:
    """WFP weekly crop prices -> tidy [crop, market, date, price_rwf]."""
    df = pd.read_csv(DATA_RAW / "wfp_food_prices_rwanda.csv")
    # TODO: standardise column names, parse dates, filter to CROPS,
    #       drop non-RWF rows, resample to weekly.
    return df


def load_cpi() -> pd.DataFrame:
    """Food CPI -> [date, food_cpi]; compute YoY % change as cpi_change."""
    df = pd.read_csv(DATA_RAW / "rwanda_food_cpi.csv")
    # TODO: parse dates, sort, df["cpi_change"] = df["food_cpi"].pct_change(12) * 100
    return df


def load_fertilizer() -> pd.DataFrame:
    """World Bank fertilizer index -> [date, fert_index, fert_change (YoY %)]."""
    df = pd.read_csv(DATA_RAW / "fertilizer_price_index.csv")
    # TODO: parse dates, df["fert_change"] = df["fert_index"].pct_change(12) * 100
    return df


def load_rainfall() -> pd.DataFrame:
    """District rainfall anomalies -> [district, season, date, rainfall_anomaly]."""
    df = pd.read_csv(DATA_RAW / "district_rainfall_anomalies.csv")
    # TODO: anomalies are already in std-dev units in the HDX file; verify and
    #       align to Season A (Mar-May) and Season B (Oct-Dec).
    return df


# -------------------------------------------------------------- risk labels
def label_risk(rainfall_anomaly: float, cpi_change: float, fert_change: float) -> str:
    """Engineer the High/Medium/Low label exactly as defined in the proposal."""
    hi, med = RISK_THRESHOLDS["high"], RISK_THRESHOLDS["medium"]

    if rainfall_anomaly < hi["rain"] and (cpi_change > hi["cpi"] or fert_change > hi["fert"]):
        return "High"
    if rainfall_anomaly < med["rain"] or cpi_change > med["cpi"] or fert_change > med["fert"]:
        return "Medium"
    return "Low"


def build_risk_dataset() -> pd.DataFrame:
    """Merge rainfall + CPI + fertilizer into the labelled training set for module 2."""
    rain = load_rainfall()
    cpi = load_cpi()
    fert = load_fertilizer()
    # TODO: merge on date/season, forward-fill monthly CPI & fertilizer onto
    #       the rainfall cadence, then apply label_risk row-wise:
    # df["risk_level"] = df.apply(
    #     lambda r: label_risk(r.rainfall_anomaly, r.cpi_change, r.fert_change), axis=1)
    raise NotImplementedError("merge sources, then apply label_risk row-wise")


def build_price_dataset() -> pd.DataFrame:
    """Merge price history with CPI + fertilizer regressors for module 1."""
    # TODO: weekly prices left-joined with forward-filled monthly CPI & fertilizer.
    raise NotImplementedError


if __name__ == "__main__":
    DATA_PROCESSED.mkdir(exist_ok=True)
    print("Run individual build_*_dataset() functions once raw files are in place.")
