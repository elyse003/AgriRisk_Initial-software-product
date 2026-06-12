"""Price Forecast — 4-week-ahead per crop/district on real data (all 30 districts)."""
from _ui import setup, load_prices
import numpy as np, pandas as pd, streamlit as st
from sklearn.ensemble import RandomForestRegressor
from config.settings import CROPS, DISTRICTS
from src.db.connection import log_price

setup("Price Forecast", "Four-week price outlook by crop and district")
prices = load_prices()

c1, c2 = st.columns(2)
crop = c1.selectbox("Crop", CROPS, format_func=str.title)
district = c2.selectbox("District", DISTRICTS)

if st.button("Generate Forecast", type="primary"):
    s_district = prices[(prices.crop == crop) & (prices.market == district)].sort_values("date").set_index("date")["price_rwf"]
    crop_all = prices[prices.crop == crop].sort_values("date")
    crop_latest = crop_all["date"].max()
    national = crop_all.set_index("date")["price_rwf"].groupby(level=0).median().sort_index()

    if len(s_district) >= 20:
        last_date = s_district.index[-1]
        if (crop_latest - last_date).days > 540:          # district's own data older than ~18 months
            s = national
            src_note = (f"Showing the national recent average. {district}'s own {crop} prices end "
                        f"{last_date:%b %Y}, so a current district figure isn't available.")
        else:
            s = s_district
            src_note = f"Current price as of {last_date:%b %Y}."
    else:
        s = national
        src_note = f"{district} has no local market in the price data, so this is the national recent average."

    d = pd.DataFrame({"y": s})
    for lag in [1, 2, 3, 4, 8, 12]:
        d[f"lag{lag}"] = d["y"].shift(lag)
    d["target"] = d["y"].shift(-1)
    tr = d.dropna(); feats = [c for c in d.columns if c.startswith("lag")]
    model = RandomForestRegressor(n_estimators=200, random_state=42).fit(tr[feats], tr["target"])
    cur = float(s.iloc[-1]); fc = float(model.predict(d[feats].iloc[[-1]])[0])
    log_price(crop, district, str(s.index[-1].date()), cur)
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
    st.caption(src_note + " Decision-support only; confirm with local market conditions.")
else:
    st.info("Pick a crop and district, then click **Generate Forecast**.")
