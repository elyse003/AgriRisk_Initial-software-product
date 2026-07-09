"""RQ1 ablation: does adding CPI + fertilizer as Prophet regressors actually
improve price-forecast accuracy over price history alone?

    RQ1: "How accurately can a Prophet model trained on WFP Rwanda crop price data
    and food CPI predict market prices for maize, beans, and potatoes ahead ...,
    as measured by MAPE, and does including CPI as an additional regressor
    significantly improve forecast accuracy compared to price history alone?"

The proposal asks this directly, but the study only ever fitted Prophet *with*
regressors — never the price-only baseline — so the question could not be
answered. This script fits BOTH on the same train/test split for every
crop x pilot-district series, reports MAPE for each, and runs a Wilcoxon
signed-rank test on the paired absolute percentage errors.

    python scripts/rq1_ablation.py

METHODOLOGICAL CAVEAT (state this in the defense): Prophet needs future values of
its regressors. We feed the *actual* future CPI / fertilizer values, which a real
deployment would not know. That makes the "with regressors" arm optimistic - an
upper bound on the benefit. We therefore also run a deployable "last-known"
variant that carries the final observed regressor value forward.

Writes models_store/rq1_ablation.json.
"""
from __future__ import annotations

import json
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import MODELS_STORE, data_path          # noqa: E402

warnings.filterwarnings("ignore")
for noisy in ("prophet", "cmdstanpy", "matplotlib"):
    logging.getLogger(noisy).setLevel(logging.CRITICAL)

TEST_MONTHS = 12          # hold out the most recent year
MIN_TRAIN = 36            # need a few years for Prophet's yearly seasonality
CROPS = ["maize", "beans", "potatoes"]
DISTRICTS = ["Musanze", "Bugesera"]   # the proposal's two pilot districts


def mape(y, yhat) -> float:
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    keep = y != 0
    return float(np.mean(np.abs((y[keep] - yhat[keep]) / y[keep])) * 100)


def ape(y, yhat) -> np.ndarray:
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    keep = y != 0
    return np.abs((y[keep] - yhat[keep]) / y[keep]) * 100


def build_series(prices, cpi, fert, crop, market) -> pd.DataFrame | None:
    s = prices[(prices["crop"] == crop) & (prices["market"] == market)]
    if s.empty:
        return None
    s = (s.set_index("date")["price_rwf"].groupby(level=0).mean()
           .sort_index().rename("y").reset_index().rename(columns={"date": "ds"}))
    s["ds"] = s["ds"].values.astype("datetime64[M]")
    s = s.groupby("ds", as_index=False)["y"].mean()
    s = s.merge(cpi[["date", "food_cpi"]].rename(columns={"date": "ds"}), on="ds", how="left")
    s = s.merge(fert[["date", "fert_index"]].rename(columns={"date": "ds"}), on="ds", how="left")
    s[["food_cpi", "fert_index"]] = s[["food_cpi", "fert_index"]].ffill().bfill()
    return s.dropna(subset=["y"])


def fit_predict(train, future, regressors: list[str]):
    from prophet import Prophet
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    for r in regressors:
        m.add_regressor(r)
    m.fit(train[["ds", "y"] + regressors])
    return m.predict(future[["ds"] + regressors])["yhat"].to_numpy()


def main():
    prices = pd.read_csv(data_path("wfp_food_prices_rwanda.csv"), parse_dates=["date"])
    cpi = pd.read_csv(data_path("rwanda_food_cpi.csv"), parse_dates=["date"])
    fert = pd.read_csv(data_path("fertilizer_price_index.csv"), parse_dates=["date"])
    for d in (cpi, fert):
        d["date"] = d["date"].values.astype("datetime64[M]")

    rows, ape_none, ape_reg, ape_last = [], [], [], []
    for crop in CROPS:
        for market in DISTRICTS:
            s = build_series(prices, cpi, fert, crop, market)
            if s is None or len(s) < MIN_TRAIN + TEST_MONTHS:
                print(f"  skip {crop}/{market}: only {0 if s is None else len(s)} months")
                continue
            train, test = s.iloc[:-TEST_MONTHS], s.iloc[-TEST_MONTHS:]

            # (a) price history alone
            p_none = fit_predict(train, test, [])
            # (b) with CPI + fertilizer, using ACTUAL future regressor values (optimistic)
            p_reg = fit_predict(train, test, ["food_cpi", "fert_index"])
            # (c) deployable: carry the last observed regressor value forward
            fut = test.copy()
            fut["food_cpi"] = train["food_cpi"].iloc[-1]
            fut["fert_index"] = train["fert_index"].iloc[-1]
            p_last = fit_predict(train, fut, ["food_cpi", "fert_index"])

            y = test["y"].to_numpy()
            rows.append({"crop": crop, "district": market, "test_months": len(test),
                         "mape_price_only": round(mape(y, p_none), 2),
                         "mape_with_regressors": round(mape(y, p_reg), 2),
                         "mape_regressors_lastknown": round(mape(y, p_last), 2)})
            ape_none.append(ape(y, p_none)); ape_reg.append(ape(y, p_reg))
            ape_last.append(ape(y, p_last))
            print(f"  done {crop}/{market}")

    if not rows:
        print("No series had enough history."); return

    res = pd.DataFrame(rows)
    a_none = np.concatenate(ape_none); a_reg = np.concatenate(ape_reg); a_last = np.concatenate(ape_last)

    from scipy.stats import wilcoxon
    def test_vs(a, b, label):
        stat, p = wilcoxon(a, b)
        better = "regressors BETTER" if np.mean(b) < np.mean(a) else "regressors WORSE"
        verdict = better if p < 0.05 else "no significant difference"
        return {"comparison": label, "mean_ape_price_only": round(float(np.mean(a)), 2),
                "mean_ape_other": round(float(np.mean(b)), 2),
                "p_value": round(float(p), 5), "significant_at_0.05": bool(p < 0.05),
                "verdict": verdict}

    t_reg = test_vs(a_none, a_reg, "price-only vs with-regressors (actual future values)")
    t_last = test_vs(a_none, a_last, "price-only vs with-regressors (last-known, deployable)")

    print("\n" + "=" * 84)
    print("RQ1 ABLATION — Prophet, %d-month hold-out per series" % TEST_MONTHS)
    print("=" * 84)
    print(res.to_string(index=False))
    print(f"\nPooled mean MAPE  price-only            : {np.mean(a_none):.2f}%")
    print(f"Pooled mean MAPE  + regressors (actual) : {np.mean(a_reg):.2f}%")
    print(f"Pooled mean MAPE  + regressors (last-kn): {np.mean(a_last):.2f}%")
    print("\nWilcoxon signed-rank on paired absolute percentage errors:")
    for tst in (t_reg, t_last):
        print(f"  {tst['comparison']:58} p={tst['p_value']:.5f} -> {tst['verdict']}")

    out = {"test_months": TEST_MONTHS, "per_series": rows,
           "pooled_mean_ape": {"price_only": round(float(np.mean(a_none)), 2),
                               "with_regressors_actual": round(float(np.mean(a_reg)), 2),
                               "with_regressors_lastknown": round(float(np.mean(a_last)), 2)},
           "tests": [t_reg, t_last],
           "caveat": ("The 'actual future values' arm feeds Prophet true future CPI/fertilizer, "
                      "which a live system would not know; it is an optimistic upper bound. The "
                      "'last-known' arm is what is actually deployable.")}
    MODELS_STORE.mkdir(parents=True, exist_ok=True)
    (MODELS_STORE / "rq1_ablation.json").write_text(json.dumps(out, indent=2))
    print("\nSaved models_store/rq1_ablation.json")


if __name__ == "__main__":
    main()