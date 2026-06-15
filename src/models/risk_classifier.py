"""Module 2: seasonal food-price-stress risk classifier.

What "risk" means here (data-derived, not a hand-written rule):
for each district-month we measure the REAL outcome = the realized 6-month-ahead
change in that district's staple food prices, then label the top / middle /
bottom third as High / Medium / Low risk. The model learns whether conditions
known around planting time -- the season's rainfall anomaly, food-price
inflation momentum (CPI YoY) and fertilizer-cost momentum (YoY) -- predict that
coming price stress.

This is a genuine (and genuinely imperfect) prediction problem, unlike the
earlier version that trained a classifier to reproduce its own labelling rule
and so scored a meaningless 100%.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

FEATURES = ["rainfall_anomaly", "cpi_change", "fert_change"]
LABEL = "risk_level"
OUTCOME_HORIZON = 6   # months ahead used to measure realized price stress


def build_risk_dataset(prices: pd.DataFrame, rain: pd.DataFrame,
                       cpi: pd.DataFrame, fert: pd.DataFrame) -> pd.DataFrame:
    """Join real sources into a labelled training set.

    prices: [date, market, crop, price_rwf]   rain: [date, district, season, rainfall_anomaly]
    cpi:    [date, food_cpi]                   fert: [date, fert_index]
    Returns rows with FEATURES + LABEL (+ future_change for inspection).
    """
    cpi = cpi.sort_values("date").copy()
    fert = fert.sort_values("date").copy()
    cpi["cpi_change"] = cpi["food_cpi"].pct_change(12) * 100
    fert["fert_change"] = fert["fert_index"].pct_change(12) * 100

    # realized OUTCOME: 6-month-ahead price change per district+crop, then averaged
    p = prices.sort_values("date").copy()
    p["fut"] = p.groupby(["crop", "market"])["price_rwf"].shift(-OUTCOME_HORIZON)
    p["future_change"] = (p["fut"] - p["price_rwf"]) / p["price_rwf"] * 100
    outcome = (p.dropna(subset=["future_change"])
                 .groupby(["market", "date"])["future_change"].mean()
                 .reset_index().rename(columns={"market": "district"}))

    # FEATURES known around planting time
    df = rain[rain["season"] != "off"].merge(outcome, on=["district", "date"], how="inner")
    df = pd.merge_asof(df.sort_values("date"), cpi[["date", "cpi_change"]], on="date")
    df = pd.merge_asof(df.sort_values("date"), fert[["date", "fert_change"]], on="date")
    df = df.dropna(subset=FEATURES + ["future_change"])

    # LABEL: terciles of realized future price change
    q_lo, q_hi = df["future_change"].quantile([1 / 3, 2 / 3])
    df[LABEL] = np.where(df["future_change"] > q_hi, "High",
                np.where(df["future_change"] < q_lo, "Low", "Medium"))
    return df.reset_index(drop=True)


def fit_random_forest(X, y):
    return RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                  random_state=42).fit(X, y)


def fit_gradient_boosting(X, y):
    return GradientBoostingClassifier(n_estimators=200, learning_rate=0.1,
                                      random_state=42).fit(X, y)


def evaluate(model, X_test, y_test) -> dict:
    pred = model.predict(X_test)
    return {"accuracy": round(float(accuracy_score(y_test, pred)), 3),
            "macro_f1": round(float(f1_score(y_test, pred, average="macro")), 3)}