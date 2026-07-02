"""Train + serialize the production models on the REAL processed data, and write
metrics.json (read by the dashboard's Home screen).

    python scripts/prepare_data.py     # first: build data/processed/ from real sources
    python scripts/train_models.py     # then: train + save models_store/*.pkl

Artifacts written to models_store/:
    price_forecaster.pkl   dict {crop: GradientBoostingRegressor}  (next-month log-return model)
    risk_classifier.pkl    GradientBoostingClassifier              (food-price-stress risk)
    metrics.json           real holdout metrics shown in the app
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATA_PROCESSED, MODELS_STORE, CROPS
from src.models.price_forecasting import train_crop_model, esoko_as_prices, MIN_HISTORY
from src.models import risk_classifier as rc


def _load(name, **kw):
    return pd.read_csv(DATA_PROCESSED / name, **kw)


def train_price(include_esoko=False):
    prices = _load("wfp_food_prices_rwanda.csv", parse_dates=["date"])
    if include_esoko:
        # Stage 2: pool Esoko farmgate series (kept separate via the "(Esoko)"
        # market suffix). Returns are scale-free, so farmgate & retail dynamics
        # both train the model. Series shorter than MIN_HISTORY months contribute
        # nothing yet, so this is safe now and grows more useful over time.
        ep = DATA_PROCESSED / "esoko_farmgate_prices.csv"
        if ep.exists():
            e = pd.read_csv(ep, parse_dates=["date"])
            months = int(e["date"].dt.to_period("M").nunique())
            ea = esoko_as_prices(e)
            if ea is not None:
                prices = pd.concat([prices, ea], ignore_index=True)
            note = ("" if months >= MIN_HISTORY else
                    f" — too shallow to add usable series yet (need >= {MIN_HISTORY} months); "
                    "will help automatically as it grows")
            print(f"  +Esoko farmgate pooled: {len(ea) if ea is not None else 0} rows, "
                  f"{months} month(s){note}")
        else:
            print("  --include-esoko set but no data/processed/esoko_farmgate_prices.csv (skipping)")
    models, mape = {}, {}
    for crop in CROPS:
        model, score, n = train_crop_model(prices, crop)
        if model is not None:
            models[crop] = model
            mape[crop] = score
            print(f"  price[{crop}]: MAPE={score:.2f}%  (n={n})")
    pickle.dump(models, open(MODELS_STORE / "price_forecaster.pkl", "wb"))
    return mape


def train_risk():
    prices = _load("wfp_food_prices_rwanda.csv", parse_dates=["date"])
    rain = _load("district_rainfall_anomalies.csv", parse_dates=["date"])
    cpi = _load("rwanda_food_cpi.csv", parse_dates=["date"])
    fert = _load("fertilizer_price_index.csv", parse_dates=["date"])

    df = rc.build_risk_dataset(prices, rain, cpi, fert)
    X, y = df[rc.FEATURES], df[rc.LABEL]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    rf = rc.fit_random_forest(Xtr, ytr)
    gb = rc.fit_gradient_boosting(Xtr, ytr)
    rf_m, gb_m = rc.evaluate(rf, Xte, yte), rc.evaluate(gb, Xte, yte)
    best = gb if gb_m["macro_f1"] >= rf_m["macro_f1"] else rf
    # refit the winner on all data for deployment
    best.fit(X, y)
    pickle.dump(best, open(MODELS_STORE / "risk_classifier.pkl", "wb"))
    majority = round(float(y.value_counts().max() / len(y)), 3)
    print(f"  risk: n={len(df)} classes={df[rc.LABEL].value_counts().to_dict()}")
    print(f"  risk: RF={rf_m}  GB={gb_m}  majority_baseline={majority}")
    return rf_m, gb_m, len(df), majority


def main(include_esoko=False):
    print("Training production models on real data ...")
    mape = train_price(include_esoko=include_esoko)
    rf_m, gb_m, n_risk, majority = train_risk()
    metrics = {
        "price_mape_by_crop": {k: round(v, 2) for k, v in mape.items()},
        "price_mape_avg": round(sum(mape.values()) / len(mape), 2) if mape else None,
        "risk_random_forest": rf_m,
        "risk_gradient_boosting": gb_m,
        "risk_majority_baseline": majority,
        "n_risk_rows": n_risk,
    }
    json.dump(metrics, open(MODELS_STORE / "metrics.json", "w"), indent=2)
    print("Saved models_store/price_forecaster.pkl, risk_classifier.pkl, metrics.json")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main(include_esoko="--include-esoko" in sys.argv)