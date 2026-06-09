"""Build the REAL-DATA notebook (clean, no outputs) for AgriRisk Rwanda.

Cells are written against the actual uploaded files. The user runs it to
produce outputs. We do NOT execute it here. Run: python scripts/build_real_notebook.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "AgriRisk_Rwanda_Models.ipynb"
CELLS = []
def md(t): CELLS.append(("markdown", t.strip("\n")))
def code(t): CELLS.append(("code", t.strip("\n")))

md(r"""
# AgriRisk Rwanda — ML Models Notebook (real data)

End-to-end ML workflow on the **real** datasets: data loading & engineering, visualization,
model architecture, and performance metrics for the seasonal-risk classifier and the
crop-price forecaster.

### Before you run
Place these downloaded files in `data/raw/` with these names:

| File | Source |
|------|--------|
| `wfp_food_prices_rwa.csv` | WFP / HDX food prices |
| `CPI_time_series_April_2026.xls` | NISR monthly CPI |
| `CMO-Historical-Data-Monthly.xlsx` | World Bank fertilizer index |
| `rwa-rainfall-subnat-full.csv` | HDX / CHIRPS rainfall |
| `minagri_input_prices.csv` | MINAGRI/RAB subsidy prices (provided) |

Install the libraries (Colab recommended for Prophet/LSTM):
```
pip install pandas numpy matplotlib seaborn scikit-learn xgboost prophet statsmodels tensorflow openpyxl xlrd
```

> **Honesty note for the defense:** the seasonal-risk *labels* are derived from the same
> rainfall/CPI/fertilizer thresholds the model is given as features (per the proposal's
> definition), so the classifier is approximating that rule — accuracy will look high for
> that reason. State this plainly. The price forecaster has no such circularity.
""")

code(r"""
import warnings; warnings.filterwarnings("ignore")
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style="whitegrid", palette="deep")
from pathlib import Path

RAW = Path("data/raw")          # adjust if your files live elsewhere
TARGET_CROPS = ["maize", "beans", "potatoes"]
""")

md("## 1. Load WFP crop prices\nReal columns: `date, admin1, admin2 (district), commodity, pricetype, currency, price`. Use retail RWF prices and the well-covered commodity variants.")
code(r"""
w = pd.read_csv(RAW / "wfp_food_prices_rwa.csv", parse_dates=["date"])
w = w[(w["pricetype"] == "Retail") & (w["currency"] == "RWF")]

# map the well-covered commodity variants to our 3 crops
CROP_MAP = {"Maize": "maize", "Beans (dry)": "beans", "Potatoes (Irish)": "potatoes"}
w = w[w["commodity"].isin(CROP_MAP)].copy()
w["crop"] = w["commodity"].map(CROP_MAP)
w = w[w["admin2"] != "Administrative unit not available"]
w = w.rename(columns={"admin2": "district"})

# collapse to monthly average price per crop/district
w["date"] = w["date"].values.astype("datetime64[M]")
prices = (w.groupby(["crop", "district", "date"])["price"]
            .mean().reset_index().rename(columns={"price": "price_rwf"}))
print(prices.shape, "| crops:", prices.crop.unique(), "| districts:", prices.district.nunique())
prices.head()
""")

md("## 2. Load NISR food CPI\nSheet **All Rwanda**, COICOP code `01` = *Food and non-alcoholic beverages* (base 2014). Monthly series.")
code(r"""
# NOTE: legacy .xls needs xlrd (pip install xlrd). If you converted to .xlsx, change the name + engine.
cpi_raw = pd.read_excel(RAW / "CPI_time_series_April_2026.xls", sheet_name="All Rwanda", header=None)

# locate the header row that holds the monthly dates (the row containing 'Weights')
hdr = cpi_raw[cpi_raw.apply(lambda r: r.astype(str).str.contains("Weights", case=False).any(), axis=1)].index[0]
wcol = cpi_raw.iloc[hdr].astype(str).str.contains("Weights", case=False)
wcol_idx = wcol[wcol].index[0]
date_cols = list(range(wcol_idx + 1, cpi_raw.shape[1]))
dates = pd.to_datetime(cpi_raw.iloc[hdr, date_cols].values, errors="coerce")

# the 'Food and non-alcoholic beverages' row
food_idx = cpi_raw[cpi_raw.apply(lambda r: r.astype(str).str.startswith("Food and non").any(), axis=1)].index[0]
food_vals = pd.to_numeric(cpi_raw.iloc[food_idx, date_cols], errors="coerce").values

cpi = pd.DataFrame({"date": dates, "food_cpi": food_vals}).dropna().sort_values("date")
cpi["date"] = cpi["date"].values.astype("datetime64[M]")
cpi["cpi_change"] = cpi["food_cpi"].pct_change(12) * 100   # YoY %
print(cpi.shape, "| range:", cpi.date.min(), "->", cpi.date.max())
cpi.tail()
""")

md("## 3. Load World Bank fertilizer index\nSheet **Monthly Indices**, column 13 = *Fertilizers* (base 2010), dates in `YYYYMmm`.")
code(r"""
fert_raw = pd.read_excel(RAW / "CMO-Historical-Data-Monthly.xlsx", sheet_name="Monthly Indices", header=None)
mask = fert_raw[0].astype(str).str.match(r"^\d{4}M\d{2}$")
fert = fert_raw.loc[mask, [0, 13]].copy()
fert.columns = ["period", "fert_index"]
fert["date"] = pd.to_datetime(fert["period"].str.replace("M", "-") + "-01", errors="coerce")
fert["fert_index"] = pd.to_numeric(fert["fert_index"], errors="coerce")
fert = fert.dropna().sort_values("date")
fert["date"] = fert["date"].values.astype("datetime64[M]")
fert["fert_change"] = fert["fert_index"].pct_change(12) * 100   # YoY %
print(fert.shape, "| range:", fert.date.min(), "->", fert.date.max())
fert.tail()
""")

md(r"""## 4. Load district rainfall (CHIRPS)
Admin level 2, dekadal. `rfq` is **percent-of-normal** (100 = average) — we convert to a
deviation and standardize per district. The file labels districts by PCODE only, so we map
them to names (verify against the official OCHA COD gazetteer if you can).""")
code(r"""
# Standard Rwanda ADM2 P-codes -> district name. VERIFY against the official COD gazetteer.
PCODE2DISTRICT = {
    "RW11": "Nyarugenge", "RW12": "Gasabo", "RW13": "Kicukiro",
    "RW21": "Nyanza", "RW22": "Gisagara", "RW23": "Nyaruguru", "RW24": "Huye",
    "RW25": "Nyamagabe", "RW26": "Ruhango", "RW27": "Muhanga", "RW28": "Kamonyi",
    "RW31": "Karongi", "RW32": "Rutsiro", "RW33": "Rubavu", "RW34": "Nyabihu",
    "RW35": "Ngororero", "RW36": "Rusizi", "RW37": "Nyamasheke",
    "RW41": "Rulindo", "RW42": "Gakenke", "RW43": "Musanze", "RW44": "Burera", "RW45": "Gicumbi",
    "RW51": "Rwamagana", "RW52": "Nyagatare", "RW53": "Gatsibo", "RW54": "Kayonza",
    "RW55": "Kirehe", "RW56": "Ngoma", "RW57": "Bugesera",
}
rain_raw = pd.read_csv(RAW / "rwa-rainfall-subnat-full.csv", parse_dates=["date"])
r = rain_raw[rain_raw["adm_level"] == 2].copy()
r["district"] = r["PCODE"].map(PCODE2DISTRICT)
r = r.dropna(subset=["district", "rfq"])
r["date"] = r["date"].values.astype("datetime64[M]")

# monthly mean rfq per district -> deviation from normal -> per-district z-score (SD units)
rain = r.groupby(["district", "date"])["rfq"].mean().reset_index()
rain["dev"] = rain["rfq"] / 100 - 1
rain["rainfall_anomaly"] = rain.groupby("district")["dev"].transform(lambda s: (s - s.mean()) / s.std())
rain["season"] = rain["date"].dt.month.map(lambda m: "A" if m in (3, 4, 5) else ("B" if m in (10, 11, 12) else "off"))
print(rain.shape, "| districts:", rain.district.nunique())
rain.head()
""")

md("## 5. Data visualization")
code(r"""
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
sns.boxplot(data=prices, x="crop", y="price_rwf", ax=ax[0]); ax[0].set_title("Price by crop (RWF/kg)")
for c in prices.crop.unique():
    sns.kdeplot(prices[prices.crop == c]["price_rwf"], label=c, ax=ax[1], fill=True, alpha=.25)
ax[1].set_title("Price density by crop"); ax[1].legend(); plt.tight_layout()
""")
code(r"""
plt.figure(figsize=(13, 4.5))
for c in prices.crop.unique():
    s = prices[prices.crop == c].groupby("date")["price_rwf"].mean()
    plt.plot(s.index, s.values, label=c)
plt.title("National average monthly crop prices (real WFP data)"); plt.ylabel("RWF/kg"); plt.legend(); plt.tight_layout()
""")
code(r"""
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
ax[0].plot(cpi.date, cpi.food_cpi, color="darkred"); ax[0].set_title("NISR food CPI (base 2014)")
ax[1].plot(fert.date, fert.fert_index, color="darkblue"); ax[1].set_title("World Bank fertilizer index (base 2010)")
plt.tight_layout()
print("Food CPI YoY peak: %.1f%%  | Fertilizer YoY peak: %.1f%%" % (cpi.cpi_change.max(), fert.fert_change.max()))
""")

md("## 6. Data engineering — seasonal-risk dataset\nMerge district rainfall anomalies with national food-CPI and fertilizer YoY change, then label High/Medium/Low per the proposal thresholds.")
code(r"""
def label_risk(rain_a, cpi_c, fert_c):
    if rain_a < -0.8 and (cpi_c > 15 or fert_c > 30): return "High"
    if rain_a < -0.3 or cpi_c > 10 or fert_c > 20:    return "Medium"
    return "Low"

risk = rain[rain.season != "off"].merge(cpi[["date", "cpi_change"]], on="date", how="left")
risk = risk.merge(fert[["date", "fert_change"]], on="date", how="left").dropna(
    subset=["rainfall_anomaly", "cpi_change", "fert_change"])
risk["risk_level"] = risk.apply(lambda x: label_risk(x.rainfall_anomaly, x.cpi_change, x.fert_change), axis=1)
print("Risk rows:", len(risk)); print(risk.risk_level.value_counts())
""")
code(r"""
plt.figure(figsize=(6, 4))
sns.countplot(data=risk, x="risk_level", order=["Low", "Medium", "High"],
              palette=["#2e7d32", "#f9a825", "#c62828"])
plt.title("Seasonal risk class distribution"); plt.tight_layout()
""")
code(r"""
feat = ["rainfall_anomaly", "cpi_change", "fert_change"]
plt.figure(figsize=(5.5, 4.5))
sns.heatmap(risk[feat].corr(), annot=True, cmap="vlag", center=0, fmt=".2f", square=True)
plt.title("Risk feature correlations"); plt.tight_layout()
""")

md(r"""## 7. Seasonal-risk model — Random Forest vs XGBoost
- **Random Forest**: 100 trees, balanced class weights, Gini.
- **XGBoost**: 100 estimators, learning rate 0.1, softmax objective.

Stratified 80/20 split. Metrics: accuracy, precision, recall, macro-F1.""")
code(r"""
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             classification_report, confusion_matrix)
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder

X, y = risk[feat], risk["risk_level"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42).fit(Xtr, ytr)

le = LabelEncoder().fit(y)
xgb = XGBClassifier(n_estimators=100, learning_rate=0.1, eval_metric="mlogloss", random_state=42)
xgb.fit(Xtr, le.transform(ytr))
""")
code(r"""
def scores(name, yt, yp):
    return {"model": name, "accuracy": accuracy_score(yt, yp),
            "precision": precision_score(yt, yp, average="macro", zero_division=0),
            "recall": recall_score(yt, yp, average="macro", zero_division=0),
            "macro_f1": f1_score(yt, yp, average="macro")}

rf_pred = rf.predict(Xte)
xgb_pred = le.inverse_transform(xgb.predict(Xte))
res = pd.DataFrame([scores("Random Forest", yte, rf_pred), scores("XGBoost", yte, xgb_pred)]).set_index("model")
print(res.round(3).to_string())
print("\n", classification_report(yte, rf_pred, zero_division=0))
""")
code(r"""
cm = confusion_matrix(yte, rf_pred, labels=["Low", "Medium", "High"])
plt.figure(figsize=(5, 4))
sns.heatmap(cm, annot=True, fmt="d", cmap="Greens",
            xticklabels=["Low", "Medium", "High"], yticklabels=["Low", "Medium", "High"])
plt.title("Confusion matrix — Random Forest"); plt.ylabel("Actual"); plt.xlabel("Predicted"); plt.tight_layout()
""")
code(r"""
pd.Series(rf.feature_importances_, index=feat).sort_values().plot.barh(
    figsize=(6, 3), color="#2e7d32"); plt.title("RF feature importance"); plt.tight_layout()
""")

md(r"""## 8. Price forecasting — ARIMA, Prophet, LSTM, RF baseline
4-week / 1-month-ahead. We use one crop+district series with food-CPI and fertilizer as
regressors for Prophet. Metric: **MAPE** (target < 15%).""")
code(r"""
CROP, DISTRICT = "maize", "Musanze"   # change as needed
s = (prices[(prices.crop == CROP) & (prices.district == DISTRICT)]
     .merge(cpi[["date", "food_cpi"]], on="date", how="left")
     .merge(fert[["date", "fert_index"]], on="date", how="left")
     .sort_values("date").dropna().reset_index(drop=True))
print(s.shape, "months of data for", CROP, DISTRICT)

def mape(yt, yp): return float(np.mean(np.abs((np.array(yt) - np.array(yp)) / np.array(yt))) * 100)
cut = int(len(s) * 0.8)
train_s, test_s = s.iloc[:cut], s.iloc[cut:]
""")
code(r"""
# --- ARIMA baseline (statsmodels) ---
from statsmodels.tsa.arima.model import ARIMA
ar = ARIMA(train_s["price_rwf"], order=(2, 1, 2)).fit()
ar_pred = ar.forecast(steps=len(test_s))
print("ARIMA MAPE: %.2f%%" % mape(test_s["price_rwf"].values, ar_pred.values))
""")
code(r"""
# --- Prophet with CPI + fertilizer regressors ---
from prophet import Prophet
dfp = train_s.rename(columns={"date": "ds", "price_rwf": "y"})
m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
m.add_regressor("food_cpi"); m.add_regressor("fert_index")
m.fit(dfp[["ds", "y", "food_cpi", "fert_index"]])
future = test_s.rename(columns={"date": "ds"})[["ds", "food_cpi", "fert_index"]]
fc = m.predict(future)
print("Prophet MAPE: %.2f%%" % mape(test_s["price_rwf"].values, fc["yhat"].values))
""")
code(r"""
# --- LSTM (single layer, 50 units, sliding window) ---
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

WINDOW = 12
series = s["price_rwf"].values.reshape(-1, 1)
sc = MinMaxScaler().fit(series[:cut])
scaled = sc.transform(series)
def make_xy(arr, w):
    X, Y = [], []
    for i in range(len(arr) - w):
        X.append(arr[i:i+w]); Y.append(arr[i+w])
    return np.array(X), np.array(Y)
Xall, Yall = make_xy(scaled, WINDOW)
split = cut - WINDOW
Xtr_l, Ytr_l = Xall[:split], Yall[:split]
Xte_l, Yte_l = Xall[split:], Yall[split:]
lstm = Sequential([LSTM(50, activation="tanh", input_shape=(WINDOW, 1)), Dense(1)])
lstm.compile(optimizer="adam", loss="mse")
lstm.fit(Xtr_l, Ytr_l, epochs=100, batch_size=8, verbose=0)
pred_l = sc.inverse_transform(lstm.predict(Xte_l, verbose=0))
true_l = sc.inverse_transform(Yte_l)
print("LSTM MAPE: %.2f%%" % mape(true_l.ravel(), pred_l.ravel()))
""")
code(r"""
# --- Random Forest lag baseline + comparison chart ---
from sklearn.ensemble import RandomForestRegressor
d = s[["date", "price_rwf"]].copy()
for lag in [1, 2, 3, 6, 12]:
    d[f"lag{lag}"] = d["price_rwf"].shift(lag)
d["target"] = d["price_rwf"].shift(-1)
d = d.dropna()
feats = [c for c in d.columns if c.startswith("lag")]
cc = int(len(d) * 0.8)
reg = RandomForestRegressor(n_estimators=200, random_state=42).fit(d[feats][:cc], d["target"][:cc])
rf_fore = reg.predict(d[feats][cc:])
print("RF baseline MAPE: %.2f%%" % mape(d["target"][cc:].values, rf_fore))

plt.figure(figsize=(13, 4.5))
plt.plot(d["date"][cc:], d["target"][cc:].values, label="actual", linewidth=2)
plt.plot(d["date"][cc:], rf_fore, "--", label="RF forecast")
plt.title(f"{CROP.title()} price forecast — {DISTRICT}"); plt.ylabel("RWF/kg"); plt.legend(); plt.tight_layout()
""")

md("## 9. Persist the trained models")
code(r"""
import pickle, json
store = Path("models_store"); store.mkdir(exist_ok=True)
pickle.dump(rf, open(store / "risk_classifier.pkl", "wb"))
pickle.dump(reg, open(store / "price_baseline.pkl", "wb"))
metrics = {
    "risk_random_forest": {k: round(v, 3) for k, v in scores("rf", yte, rf_pred).items() if k != "model"},
    "price_baseline_mape": round(mape(d["target"][cc:].values, rf_fore), 2),
    "n_risk_rows": len(risk),
}
json.dump(metrics, open(store / "metrics.json", "w"), indent=2)
print("Saved models + metrics.json:", metrics)
""")

md(r"""## 10. Deployment — the MVP
The trained models serve the **Flask web app** (`webapp/`): a dashboard for extension
officers plus a farmer WhatsApp chatbot preview, across all 30 districts.

```bash
python webapp/app.py   # http://localhost:5000
```

**Next steps:** verify the rainfall PCODE→district map against the official COD gazetteer;
add the live WhatsApp (Twilio) and SMS (Africa's Talking) channels for farmers.""")

# ---- build clean notebook (no outputs) ----
def lines(t): return t.splitlines(keepends=True) or [""]
nb = {"cells": [], "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                "language_info": {"name": "python", "version": "3.10"}},
      "nbformat": 4, "nbformat_minor": 5}
for typ, src in CELLS:
    if typ == "markdown":
        nb["cells"].append({"cell_type": "markdown", "metadata": {}, "source": lines(src)})
    else:
        nb["cells"].append({"cell_type": "code", "metadata": {}, "execution_count": None,
                            "outputs": [], "source": lines(src)})
OUT.write_text(json.dumps(nb, indent=1))
print("Wrote", OUT, "with", len(nb["cells"]), "cells (no outputs)")
