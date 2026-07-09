"""RQ4: summarise the TAM pilot responses collected by the in-app Feedback page.

    RQ4: "How do agricultural extension officers rate the perceived ease of use,
    perceived usefulness, and overall satisfaction of the AgriRisk Rwanda platform
    ... as measured by a TAM questionnaire, and does platform access produce a
    measurable improvement in their self-reported confidence?"

    python scripts/export_feedback.py            # summary + data/feedback_export.csv

Reports n, mean +/- sd per TAM construct, overall and by participant role, and
checks the proposal's success criterion: mean satisfaction >= 4.0 / 5.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.connection import fetch_feedback          # noqa: E402

CONSTRUCTS = {
    "perceived_usefulness": "Perceived usefulness",
    "perceived_ease_of_use": "Perceived ease of use",
    "satisfaction_rating": "Satisfaction",
    "confidence": "Confidence in data-driven advice",
}
TARGET = 4.0


def main():
    df = fetch_feedback()
    if df.empty:
        print("No feedback recorded yet. Ask pilot participants to fill the in-app "
              "Feedback page (sidebar -> Feedback).")
        return

    tam = df.dropna(subset=["perceived_usefulness"])          # TAM rows only
    if tam.empty:
        print(f"{len(df)} feedback rows exist but none are TAM responses.")
        return

    print("=" * 68)
    print(f"TAM PILOT SUMMARY  (n = {len(tam)} responses)")
    print("=" * 68)
    print(f"{'construct':34} {'n':>4} {'mean':>6} {'sd':>6}  target>=4.0")
    for col, label in CONSTRUCTS.items():
        s = tam[col].dropna().astype(float)
        flag = "PASS" if s.mean() >= TARGET else "below"
        print(f"{label:34} {len(s):>4} {s.mean():>6.2f} {s.std(ddof=1) if len(s)>1 else 0:>6.2f}  {flag}")

    if tam["participant_role"].notna().any():
        print("\nBy participant role")
        by = tam.groupby("participant_role")[list(CONSTRUCTS)].mean().round(2)
        print(by.to_string())
        print("\nResponses per role:")
        print(tam["participant_role"].value_counts().to_string())

    if tam["module_name"].notna().any():
        print("\nMean satisfaction by module")
        print(tam.groupby("module_name")["satisfaction_rating"].agg(["count", "mean"])
                 .round(2).to_string())

    n_eo = int((tam["participant_role"] == "extension_officer").sum())
    n_fm = int((tam["participant_role"] == "farmer").sum())
    print(f"\nProposal pilot target: 20 extension officers + 20 farmers.")
    print(f"Collected so far: {n_eo} officers, {n_fm} farmers.")

    out = ROOT / "data" / "feedback_export.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    tam.to_csv(out, index=False)
    print(f"\nSaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()