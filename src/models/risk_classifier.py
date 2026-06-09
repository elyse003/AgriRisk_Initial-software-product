"""Module 2: seasonal climate-inflation risk classifier.

Compares Random Forest vs XGBoost on three features (rainfall_anomaly,
cpi_change, fertilizer_change) to predict High/Medium/Low risk. Stratified
80/20 split with 5-fold CV; best model chosen by macro-F1. Target accuracy > 85%.
"""
from __future__ import annotations

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

FEATURES = ["rainfall_anomaly", "cpi_change", "fertilizer_change"]
LABEL = "risk_level"


def split(df: pd.DataFrame):
    """Stratified 80/20 split on the risk label."""
    X, y = df[FEATURES], df[LABEL]
    return train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)


def fit_random_forest(X, y):
    """RF with 100 trees and balanced class weights."""
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(n_estimators=100, class_weight="balanced",
                                 random_state=42)
    return clf.fit(X, y)


def fit_xgboost(X, y):
    """XGBoost, 100 estimators, learning rate 0.1."""
    raise NotImplementedError  # from xgboost import XGBClassifier (encode labels first)


def evaluate(model, X_test, y_test) -> dict:
    pred = model.predict(X_test)
    return {
        "accuracy": accuracy_score(y_test, pred),
        "macro_f1": f1_score(y_test, pred, average="macro"),
    }
