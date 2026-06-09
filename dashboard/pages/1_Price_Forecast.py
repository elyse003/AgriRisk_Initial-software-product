"""Screen: Price Forecast. Fits a lightweight 4-week-ahead baseline on the
selected crop/market series and shows the forecast with a plain-language advisory.
(The production model is Prophet; see src/models/price_forecasting.py.)
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../.."))

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import RandomForestRegressor

from config.settings import DATA_RAW, data_path

st.set_page_config(page_title="Price Forecast", page_icon="📈")
st.title("📈 Price Forecast")


@st.cache_data
def load_prices():
    return pd.read_csv(data_path("wfp_food_prices_rwanda.csv"), parse_dates=["date"])


prices = load_prices()
c1, c2 = st.columns(2)
crop = c1.selectbox("Crop", sorted(prices.crop.unique()))
market = c2.selectbox("Market / district", sorted(prices.market.unique()))

if st.button("Generate forecast", type="primary"):
    s = (prices[(prices.crop == crop) & (prices.market == market)]
         .sort_values("date").set_index("date")["price_rwf"])
    d = pd.DataFrame({"y": s})
    for lag in [1, 2, 3, 4, 8, 12, 52]:
        d[f"lag{lag}"] = d["y"].shift(lag)
    d["target"] = d["y"].shift(-4)
    train = d.dropna()
    feats = [col for col in d.columns if col.startswith("lag")]
    model = RandomForestRegressor(n_estimators=200, random_state=42).fit(
        train[feats], train["target"])

    latest = d[feats].iloc[[-1]]
    forecast = float(model.predict(latest)[0])
    current = float(s.iloc[-1])
    pct = (forecast - current) / current * 100
    trend = "upward 📈" if pct > 1 else "downward 📉" if pct < -1 else "stable ➡️"

    m1, m2, m3 = st.columns(3)
    m1.metric("Current price", f"{current:,.0f} RWF/kg")
    m2.metric("4-week forecast", f"{forecast:,.0f} RWF/kg", f"{pct:+.1f}%")
    m3.metric("Trend", trend)

    hist = s.tail(52)
    fut_dates = pd.date_range(hist.index[-1], periods=5, freq="W")[1:]
    line = pd.concat([
        hist.rename("history"),
        pd.Series(np.linspace(current, forecast, 4), index=fut_dates, name="forecast"),
    ], axis=1)
    st.line_chart(line)

    if pct > 1:
        st.success(f"{crop.title()} prices in {market} are trending upward. "
                   f"Advise farmers to hold stock 2-3 weeks to capture ~{forecast-current:,.0f} "
                   f"RWF/kg gain.")
    elif pct < -1:
        st.warning(f"{crop.title()} prices in {market} are trending downward. "
                   f"Advise farmers to sell soon before further decline.")
    else:
        st.info(f"{crop.title()} prices in {market} are stable. No urgent action needed.")
    st.caption("Forecast is indicative, not guaranteed. Confirm with local market conditions.")
else:
    st.info("Choose a crop and market, then click **Generate forecast**.")
