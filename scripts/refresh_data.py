"""
Refresh the data and retrain.

Run this on a schedule (for example monthly, after the new releases are out):

    python scripts/refresh_data.py

Steps:
  1. fetch the latest WFP prices, CHIRPS rainfall and World Bank fertilizer data
  2. rebuild the processed files and retrain the models (scripts/prepare_data.py)
  3. record how current each series is, for the dashboard's "data through" line

Requires network access and: pip install requests openpyxl xlrd
NISR food CPI has no clean API, so download it manually when a new month is out.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.refresh import refresh_all, update_data_through


def main():
    print("Fetching latest data from sources ...")
    status = refresh_all()
    for name, info in status.items():
        if "ok" in info:
            state = "ok" if info["ok"] else f"FAILED ({info.get('error', '')[:80]})"
            print(f"  {name:12s} {state}")
        elif info.get("note"):
            print(f"  {name:12s} {info['note']}")

    print("\nRebuilding processed files and retraining ...")
    try:
        import importlib
        prep = importlib.import_module("scripts.prepare_data")
        if hasattr(prep, "main"):
            prep.main()
        print("  done")
    except Exception as e:
        print(f"  could not run prepare_data automatically: {e}")
        print("  run it yourself:  python scripts/prepare_data.py")

    update_data_through(status)
    print("\nData recency recorded. Restart the dashboard to see the new 'data through' dates.")


if __name__ == "__main__":
    main()
