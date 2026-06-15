"""Data preprocessing helpers for AgriRisk Rwanda.

The real cleaning pipeline that turns the downloaded public sources into the
canonical tables in data/processed/ lives in **scripts/prepare_data.py**
(prices, CPI, fertilizer, rainfall, inputs). The labelled training sets for the
models are built in the model modules:

  - price forecaster : src/models/price_forecasting.py  (_training_rows / make_features)
  - risk classifier  : src/models/risk_classifier.py    (build_risk_dataset, data-derived labels)

This module keeps `label_risk`, the original transparent rule, which the
Seasonal Risk page uses as an offline fallback when the trained model file is
absent.
"""
from __future__ import annotations

from config.settings import RISK_THRESHOLDS


def label_risk(rainfall_anomaly: float, cpi_change: float, fert_change: float) -> str:
    """Transparent High/Medium/Low rule (proposal thresholds).

    Used only as the dashboard's offline fallback. The shipped model instead
    learns risk from realized price outcomes (see src/models/risk_classifier.py).
    """
    hi, med = RISK_THRESHOLDS["high"], RISK_THRESHOLDS["medium"]

    if rainfall_anomaly < hi["rain"] and (cpi_change > hi["cpi"] or fert_change > hi["fert"]):
        return "High"
    if rainfall_anomaly < med["rain"] or cpi_change > med["cpi"] or fert_change > med["fert"]:
        return "Medium"
    return "Low"
