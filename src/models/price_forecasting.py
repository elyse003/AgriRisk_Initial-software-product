"""Module 1: crop price forecasting.

Compares ARIMA (baseline), Prophet (+ CPI & fertilizer regressors), and an
LSTM. Models are evaluated by MAPE on a temporal 80/20 hold-out; the best is
serialized for the dashboard to load. The evaluation + comparison harness is
written for you; the three fit functions are stubbed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def mape(y_true, y_pred) -> float:
    """Mean Absolute Percentage Error (the proposal's primary metric)."""
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    return float(np.mean(np.abs((y_true - y_pred) / y_true)))


def temporal_split(df: pd.DataFrame, test_frac: float = 0.2):
    """Hold out the most recent `test_frac` of rows (no shuffling)."""
    cut = int(len(df) * (1 - test_frac))
    return df.iloc[:cut].copy(), df.iloc[cut:].copy()


# ------------------------------------------------------------- candidate models
def fit_arima(train: pd.DataFrame):
    """Baseline. statsmodels SARIMAX on the price series alone."""
    raise NotImplementedError  # from statsmodels.tsa.arima.model import ARIMA

def fit_prophet(train: pd.DataFrame, with_regressors: bool = True):
    """Primary model. Prophet with CPI + fertilizer index as add_regressor()."""
    raise NotImplementedError  # from prophet import Prophet

def fit_lstm(train: pd.DataFrame, hidden_units: int = 50, window: int = 12):
    """Comparison. Single-layer LSTM, 50 units, 12-week sliding window."""
    raise NotImplementedError  # tensorflow.keras Sequential([LSTM(50), Dense(1)])


def compare(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Fit all candidates, score by MAPE, return {name: mape}. Lower is better."""
    # results = {}
    # results["arima"]   = mape(test.y, predict(fit_arima(train), test))
    # results["prophet"] = mape(test.y, predict(fit_prophet(train), test))
    # results["lstm"]    = mape(test.y, predict(fit_lstm(train), test))
    # return results
    raise NotImplementedError
