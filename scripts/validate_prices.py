"""Validate the WFP + Esoko price integration (the evidence it's methodologically
sound).

The model forecasts a scale-free next-month RETURN, so we can learn the DYNAMICS
from WFP's long retail history and set the LEVEL from Esoko farmgate, provided
farmgate and retail move together. This script quantifies that:

  * coverage          how many crop/districts each source covers
  * calibration       the robust farmgate/retail ratio per crop
                      (farmgate is ~k x retail)
  * trend transfer    the correlation of month-over-month returns between WFP
                      retail and Esoko farmgate (needs >= 3 Esoko months)

    python scripts/validate_prices.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATA_PROCESSED
from src.models.price_forecasting import farmgate_retail_ratio

WFP = DATA_PROCESSED / "wfp_food_prices_rwanda.csv"
ESOKO = DATA_PROCESSED / "esoko_farmgate_prices.csv"


def _monthly_returns(df, crop):
    """National monthly-median price -> month-over-month log returns for one crop."""
    s = (df[df["crop"] == crop].assign(m=df["date"].values.astype("datetime64[M]"))
         .groupby("m")["price_rwf"].median().sort_index())
    return np.log(s).diff().dropna()


def main():
    if not WFP.exists():
        print("Missing", WFP); return
    prices = pd.read_csv(WFP, parse_dates=["date"])
    esoko = pd.read_csv(ESOKO, parse_dates=["date"]) if ESOKO.exists() else pd.DataFrame()

    print("=== COVERAGE ===")
    print(f"WFP retail : {prices['crop'].nunique()} crops · {prices['market'].nunique()} markets · "
          f"{prices['date'].dt.to_period('M').nunique()} months "
          f"({prices['date'].min():%Y-%m}..{prices['date'].max():%Y-%m})")
    if len(esoko):
        print(f"Esoko farm : {esoko['crop'].nunique()} crops · {esoko['district'].nunique()} districts · "
              f"{esoko['date'].dt.to_period('M').nunique()} months "
              f"({esoko['date'].min():%Y-%m}..{esoko['date'].max():%Y-%m})")
    else:
        print("Esoko farm : none ingested yet (run scripts/prepare_esoko.py)"); return

    print("\n=== CALIBRATION: farmgate / retail ratio (robust median) ===")
    for crop, r in farmgate_retail_ratio(prices, esoko).items():
        print(f"  {crop:9}: farmgate ~= {r['ratio']:.2f} x retail   "
              f"(n={r['n']} obs, {r['months']} month(s))")

    print("\n=== TREND TRANSFER: retail vs farmgate return correlation ===")
    months = esoko["date"].dt.to_period("M").nunique()
    if months < 3:
        print(f"  Only {months} Esoko month(s), need >= 3 to correlate month-over-month")
        print("  returns. Keep accumulating Esoko exports (this is the check that")
        print("  justifies applying WFP's trend to the farmgate level).")
    else:
        for crop in sorted(esoko["crop"].unique()):
            rw = _monthly_returns(prices, crop)
            re = _monthly_returns(esoko.rename(columns={"district": "market"}), crop)
            j = pd.concat([rw.rename("wfp"), re.rename("esoko")], axis=1).dropna()
            if len(j) >= 3:
                print(f"  {crop:9}: r = {j['wfp'].corr(j['esoko']):+.2f}  (n={len(j)} months)")
            else:
                print(f"  {crop:9}: not enough overlapping months yet ({len(j)})")

    print("\nInterpretation: a high positive return correlation means WFP's monthly")
    print("dynamics transfer to farmgate, so anchoring the WFP trend to the Esoko")
    print("farmgate level is sound. Once Esoko has ~12+ months, retrain on it:")
    print("    python scripts/train_models.py --include-esoko")


if __name__ == "__main__":
    main()