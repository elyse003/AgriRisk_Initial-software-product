"""SHAP explainability for the deployed seasonal-risk classifier.

The proposal lists SHAP under Development Tools ("feature importance visualization
showing which factors drove the risk score") but the study used scikit-learn's
impurity-based `feature_importances_` instead. Impurity importance is biased
toward high-cardinality / continuous features; SHAP attributes each prediction to
each feature additively and is the defensible choice.

    python scripts/shap_risk.py

Writes:
    models_store/shap_risk.json   mean |SHAP| per feature (global importance)
    models_store/shap_risk.png    beeswarm summary plot (for the report/defense)
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore")

from config.settings import MODELS_STORE, data_path          # noqa: E402
from src.models import risk_classifier as rc                  # noqa: E402


def _load(name):
    return pd.read_csv(data_path(name), parse_dates=["date"])


def main():
    import pickle
    import shap
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    model = pickle.load(open(MODELS_STORE / "risk_classifier.pkl", "rb"))
    df = rc.build_risk_dataset(_load("wfp_food_prices_rwanda.csv"),
                              _load("district_rainfall_anomalies.csv"),
                              _load("rwanda_food_cpi.csv"),
                              _load("fertilizer_price_index.csv"))
    X = df[rc.FEATURES]

    # TreeExplainer is exact and fast, but SHAP does not support MULTICLASS
    # GradientBoostingClassifier. Fall back to the model-agnostic permutation
    # explainer on predict_proba, which is exact enough for 7 features.
    try:
        explainer = shap.TreeExplainer(model)
        Xs = X.sample(min(600, len(X)), random_state=42)
        sv = explainer.shap_values(Xs)
        plot_sv = sv
        arr = (np.stack([np.abs(s) for s in sv]).mean(axis=0) if isinstance(sv, list)
               else (np.abs(sv).mean(axis=2) if sv.ndim == 3 else np.abs(sv)))
        print("(exact TreeExplainer)")
    except Exception as e:
        print(f"(TreeExplainer unavailable: {type(e).__name__}; using permutation explainer)")
        Xs = X.sample(min(200, len(X)), random_state=42)
        bg = shap.utils.sample(X, 100, random_state=42)
        explainer = shap.Explainer(model.predict_proba, bg, algorithm="permutation")
        expl = explainer(Xs, max_evals=2 * len(rc.FEATURES) + 1)
        plot_sv = expl
        v = expl.values                       # (rows, features, classes)
        arr = np.abs(v).mean(axis=2) if v.ndim == 3 else np.abs(v)

    mean_abs = arr.mean(axis=0)
    total = float(mean_abs.sum()) or 1.0
    imp = sorted(
        [{"feature": f, "mean_abs_shap": round(float(v), 5),
          "share_pct": round(float(v) / total * 100, 1)}
         for f, v in zip(rc.FEATURES, mean_abs)],
        key=lambda d: -d["mean_abs_shap"])

    # impurity importance, for the honest side-by-side comparison
    fi = getattr(model, "feature_importances_", None)
    if fi is not None:
        fi = np.asarray(fi, float) / np.sum(fi)
        for row in imp:
            row["impurity_share_pct"] = round(
                float(fi[rc.FEATURES.index(row["feature"])] * 100), 1)

    print("\n" + "=" * 66)
    print("SHAP global importance — deployed risk classifier (%s)" % type(model).__name__)
    print("=" * 66)
    print(f"{'feature':20} {'SHAP %':>9} {'impurity %':>12}")
    for r in imp:
        print(f"{r['feature']:20} {r['share_pct']:>8.1f}% {r.get('impurity_share_pct', float('nan')):>11.1f}%")

    agro = sum(r["share_pct"] for r in imp if r["feature"] in rc.AGRO_FEATURES)
    print(f"\nSoil & terrain (agro) share of SHAP importance: {agro:.1f}%")

    MODELS_STORE.mkdir(parents=True, exist_ok=True)
    (MODELS_STORE / "shap_risk.json").write_text(json.dumps(
        {"model": type(model).__name__, "n_explained": int(len(Xs)),
         "importance": imp, "agro_share_pct": round(agro, 1)}, indent=2))

    try:
        plt.figure()
        shap.summary_plot(plot_sv, Xs, plot_type="bar", show=False,
                          class_names=list(getattr(model, "classes_", [])))
        plt.tight_layout()
        plt.savefig(MODELS_STORE / "shap_risk.png", dpi=150)
        plt.close()
        print("Saved models_store/shap_risk.png")
    except Exception as e:                                   # plotting is optional
        print(f"(plot skipped: {type(e).__name__}: {e})")
    print("Saved models_store/shap_risk.json")


if __name__ == "__main__":
    main()