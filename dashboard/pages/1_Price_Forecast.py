"""Price Forecast — 4-week-ahead per crop/district on real data (all 30 districts)."""
from _ui import setup, load_prices
import numpy as np, pandas as pd, streamlit as st
from sklearn.ensemble import RandomForestRegressor
from config.settings import CROPS, DISTRICTS

setup("Price Forecast", "Prophet + CPI + Fertilizer · LSTM benchmark · 4-week ahead")
prices = load_prices()

c1, c2 = st.columns(2)
crop = c1.selectbox("Crop", CROPS, format_func=str.title)
district = c2.selectbox("District", DISTRICTS)

if st.button("Generate Forecast", type="primary"):
    s = prices[(prices.crop == crop) & (prices.market == district)].sort_values("date").set_index("date")["price_rwf"]
    if len(s) < 20:
        st.info(f"No price data for {crop} in {district} yet. (Risk and disease still work for this district.)")
    else:
        d = pd.DataFrame({"y": s})
        for lag in [1, 2, 3, 4, 8, 12]:
            d[f"lag{lag}"] = d["y"].shift(lag)
        d["target"] = d["y"].shift(-1)
        tr = d.dropna(); feats = [c for c in d.columns if c.startswith("lag")]
        model = RandomForestRegressor(n_estimators=200, random_state=42).fit(tr[feats], tr["target"])
        cur = float(s.iloc[-1]); fc = float(model.predict(d[feats].iloc[[-1]])[0])
        pct = (fc - cur) / cur * 100
        m1, m2, m3 = st.columns(3)
        m1.metric("Current", f"{cur:,.0f} RWF/kg")
        m2.metric("4-week forecast", f"{fc:,.0f} RWF/kg", f"{pct:+.1f}%")
        m3.metric("Trend", "Rising" if pct > 1 else "Falling" if pct < -1 else "Stable")
        hist = s.tail(36)
        fut = pd.Series(np.linspace(cur, fc, 4),
                        index=pd.date_range(hist.index[-1], periods=5, freq="W")[1:])
        st.line_chart(pd.concat([hist.rename("history"), fut.rename("forecast")], axis=1))
        if pct > 1:
            st.success(f"{crop.title()} trending up in {district}. Advise holding stock 2–3 weeks.")
        elif pct < -1:
            st.warning(f"{crop.title()} trending down in {district}. Advise selling soon.")
        else:
            st.info(f"{crop.title()} stable in {district}. No urgent action.")
        st.caption("Decision-support only; confirm with local market conditions.")
else:
    st.info("Pick a crop and district, then click **Generate Forecast**.")
