"""Module 1: crop price forecasting (production model).

The DEPLOYED forecaster is a gradient-boosted regression on engineered
time-series features, trained on real WFP monthly prices. One model per crop,
pooled across all districts so sparse district series borrow strength from the
rest.

Key design choice: the model predicts the next-month **log return**
(log p[t+1] - log p[t]), not the raw price. Returns are scale-free, so one
pooled model works across districts at very different price levels, and the
model never has to extrapolate a price level it never saw during training
(which is what tree models cannot do). The level is reconstructed afterwards as
p[t+1] = p[t] * exp(predicted_return).

WFP prices are monthly, so the "4-week-ahead" forecast is the next month.

The ARIMA / Prophet / LSTM comparison from the proposal lives in
notebooks/AgriRisk_Rwanda_Models.ipynb (those libraries are heavy to deploy on
Windows / Streamlit Cloud); this scikit-learn model is what ships in the app.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

# past log-returns (months) used as features; keep train & predict in sync here.
RET_LAGS = [1, 2, 3, 6, 12]
MIN_HISTORY = 14                     # months needed before a feature row is usable
FEATURES = ([f"ret{l}" for l in RET_LAGS]
            + ["dev_roll3", "dev_year", "month_sin", "month_cos"])


def mape(y_true, y_pred) -> float:
    """Mean Absolute Percentage Error (%), the proposal's primary metric."""
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    keep = y_true != 0
    return float(np.mean(np.abs((y_true[keep] - y_pred[keep]) / y_true[keep])) * 100)


def make_features(series: pd.Series) -> pd.DataFrame:
    """Turn one monthly price series (DatetimeIndex) into a scale-free feature frame.

    Columns include the current level `y` and `target_ret` (next-month log return,
    NaN on the last row). The last row is the one to forecast the next month from.
    """
    s = series.sort_index().astype(float)
    logp = np.log(s)
    d = pd.DataFrame({"y": s, "logp": logp})
    ret1 = logp.diff()                                   # 1-month log return
    for l in RET_LAGS:
        d[f"ret{l}"] = logp.diff(l).shift(0) if l == 1 else logp.shift(1) - logp.shift(1 + l)
    d["ret1"] = ret1                                     # most recent return
    roll3 = s.shift(1).rolling(3).mean()
    d["dev_roll3"] = np.log(s / roll3)                   # deviation from recent mean (mean reversion)
    d["dev_year"] = logp - logp.shift(12)                # YoY trend
    month = d.index.month
    d["month_sin"] = np.sin(2 * np.pi * month / 12)
    d["month_cos"] = np.cos(2 * np.pi * month / 12)
    d["target_ret"] = logp.shift(-1) - logp             # next-month log return (target)
    return d


def _training_rows(prices: pd.DataFrame, crop: str) -> pd.DataFrame:
    """Pool every district's series for one crop into one labelled feature frame."""
    frames = []
    for _, g in prices[prices["crop"] == crop].groupby("market"):
        s = g.set_index("date")["price_rwf"].groupby(level=0).mean().sort_index()
        if len(s) < MIN_HISTORY:
            continue
        f = make_features(s)
        f["market"] = g["market"].iloc[0]
        frames.append(f)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames).reset_index().rename(columns={"index": "date"})


def train_crop_model(prices: pd.DataFrame, crop: str, test_frac: float = 0.2):
    """Fit one crop's forecaster; return (model, holdout_mape, n_train).

    Temporal hold-out: the most recent `test_frac` of rows (by date) are the test
    set, so we never train on the future. MAPE is computed on the reconstructed
    price level (p[t]*exp(pred_return)) vs the actual next-month price.
    """
    rows = _training_rows(prices, crop).dropna(subset=FEATURES + ["target_ret", "y"])
    if rows.empty:
        return None, None, 0
    rows = rows.sort_values("date")
    cut = int(len(rows) * (1 - test_frac))
    tr, te = rows.iloc[:cut], rows.iloc[cut:]
    model = GradientBoostingRegressor(n_estimators=300, max_depth=3,
                                      learning_rate=0.05, random_state=42)
    model.fit(tr[FEATURES], tr["target_ret"])
    score = None
    if len(te):
        pred_price = te["y"].to_numpy() * np.exp(model.predict(te[FEATURES]))
        actual = te["y"].to_numpy() * np.exp(te["target_ret"].to_numpy())
        score = mape(actual, pred_price)
    # refit on all rows for the deployed artifact (more data = better in production)
    model.fit(rows[FEATURES], rows["target_ret"])
    return model, score, len(rows)


def forecast_next(model, series: pd.Series) -> float:
    """Predict next month's price for one series using a fitted crop model."""
    f = make_features(series).iloc[[-1]]
    ret = float(model.predict(f[FEATURES])[0])
    return float(f["y"].iloc[0] * np.exp(ret))


# ---------------------------------------------------------------------------
# Canonical outlook shared by EVERY channel (dashboard, chat, USSD) so they
# always agree. The single source of truth for which series is used and what
# the next-month figure is.
# ---------------------------------------------------------------------------
def price_outlook(prices: pd.DataFrame, models, crop: str, district: str,
                  stale_days: int = 540) -> dict | None:
    """Next-month price outlook for one crop/district.

    Picks the district's own monthly series when it has enough history and isn't
    stale; otherwise falls back to the crop's national (cross-market median)
    series. Returns dict(series, current, forecast, pct, source, last_date) or
    None when there's no data. `models` is {crop: fitted model}.
    """
    crop_all = prices[prices["crop"] == crop]
    if crop_all.empty:
        return None
    s_d = (crop_all[crop_all["market"] == district]
           .set_index("date")["price_rwf"].groupby(level=0).mean().sort_index())
    national = (crop_all.set_index("date")["price_rwf"]
                .groupby(level=0).median().sort_index())
    crop_latest = crop_all["date"].max()

    if len(s_d) >= MIN_HISTORY and (crop_latest - s_d.index[-1]).days <= stale_days:
        s, source = s_d, "district"
    else:
        s, source = national, "national"
    if len(s) == 0:
        return None

    cur = float(s.iloc[-1])
    model = (models or {}).get(crop)
    fc = None
    if model is not None and len(s) >= MIN_HISTORY:
        try:
            fc = forecast_next(model, s)
        except Exception:
            fc = None
    pct = ((fc - cur) / cur * 100) if (fc is not None and cur) else None
    return {"series": s, "current": cur, "forecast": fc, "pct": pct,
            "source": source, "last_date": s.index[-1]}