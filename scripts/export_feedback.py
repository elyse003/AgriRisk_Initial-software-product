"""RQ4: summarise the TAM pilot responses collected by the in-app Feedback page.

    RQ4: "How do agricultural extension officers rate the perceived ease of use,
    perceived usefulness, and overall satisfaction of the AgriRisk Rwanda platform
    ... as measured by a TAM questionnaire, and does platform access produce a
    measurable improvement in their self-reported confidence?"

    python scripts/export_feedback.py            # summary + data/feedback_export.csv

Reports, per construct: n, mean +/- sd, and Cronbach's alpha (internal consistency
across the four items). Then the paired pre/post confidence comparison for the
extension officers, which is the second half of RQ4. Checks the proposal's success
criterion: mean satisfaction >= 4.0 / 5.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.connection import fetch_feedback          # noqa: E402

ITEMS = {
    "Perceived usefulness": ["pu1", "pu2", "pu3", "pu4"],
    "Perceived ease of use": ["peou1", "peou2", "peou3", "peou4"],
    "Satisfaction": ["sat1", "sat2", "sat3", "sat4"],
}
MEANS = {
    "Perceived usefulness": "perceived_usefulness",
    "Perceived ease of use": "perceived_ease_of_use",
    "Satisfaction": "satisfaction_rating",
}
TARGET = 4.0


def cronbach_alpha(df: pd.DataFrame) -> float | None:
    """Standard alpha = k/(k-1) * (1 - sum(item variances) / variance of the total).

    Needs at least 2 respondents and 2 items, and a non-zero total variance (if
    every respondent gives the same total, alpha is undefined, not 1.0).
    """
    d = df.dropna()
    k = d.shape[1]
    if d.shape[0] < 2 or k < 2:
        return None
    item_var = d.var(axis=0, ddof=1).sum()
    total_var = d.sum(axis=1).var(ddof=1)
    if not total_var:
        return None
    return (k / (k - 1)) * (1 - item_var / total_var)


def interpret(a: float | None) -> str:
    if a is None:
        return "n/a (needs >= 2 respondents)"
    if a >= 0.9:
        return "excellent"
    if a >= 0.8:
        return "good"
    if a >= 0.7:
        return "acceptable"
    if a >= 0.6:
        return "questionable"
    return "poor"


def confidence_change(tam: pd.DataFrame) -> None:
    """Paired pre/post confidence for officers: the 'measurable improvement' in RQ4."""
    if "phase" not in tam.columns:
        print("\nNo phase column: pre/post confidence cannot be compared.")
        return

    officers = tam[tam["participant_role"] == "extension_officer"]
    pre = officers[officers["phase"] == "pre"].set_index("participant_code")["confidence"]
    post = officers[officers["phase"] == "post"].groupby("participant_code")["confidence"].mean()
    paired = pd.concat([pre.rename("pre"), post.rename("post")], axis=1).dropna()

    print("\n" + "=" * 68)
    print("CONFIDENCE, pre vs post (extension officers)")
    print("=" * 68)
    if paired.empty:
        print("No officer has both a baseline and a post response yet.")
        print("Each officer must submit the baseline BEFORE using the platform,")
        print("then the full questionnaire afterwards, using the same code.")
        return

    diff = paired["post"] - paired["pre"]
    print(f"paired officers    : {len(paired)}")
    print(f"mean confidence pre : {paired['pre'].mean():.2f}")
    print(f"mean confidence post: {paired['post'].mean():.2f}")
    print(f"mean change         : {diff.mean():+.2f}")

    if len(paired) >= 6 and diff.abs().sum() > 0:
        try:
            from scipy.stats import wilcoxon
            stat, p = wilcoxon(paired["post"], paired["pre"])
            verdict = "significant" if p < 0.05 else "NOT significant"
            print(f"Wilcoxon signed-rank: W={stat:.1f}, p={p:.4f} -> {verdict} at alpha=0.05")
        except ImportError:
            print("(install scipy for the Wilcoxon signed-rank test)")
    else:
        print("(need >= 6 paired officers with some change for a Wilcoxon test)")


def main():
    df = fetch_feedback()
    if df.empty:
        print("No feedback recorded yet. Ask pilot participants to fill the in-app "
              "Feedback page (sidebar -> Feedback).")
        return

    tam = df.dropna(subset=["participant_code"])
    if tam.empty:
        print(f"{len(df)} feedback rows exist but none are TAM responses.")
        return

    if "phase" in tam.columns:
        # rows written before the 12-item migration have phase NULL, and they were
        # full submissions, so count them as "post" rather than dropping them
        post = tam[tam["phase"].fillna("post") == "post"]
    else:
        post = tam

    print("=" * 68)
    print(f"TAM PILOT SUMMARY  (n = {len(post)} completed questionnaires)")
    print("=" * 68)
    print(f"{'construct':26} {'n':>4} {'mean':>6} {'sd':>6} {'alpha':>7}  {'':12} target>=4.0")
    for label, cols in ITEMS.items():
        have = [c for c in cols if c in post.columns]
        items = post[have].apply(pd.to_numeric, errors="coerce") if have else pd.DataFrame()
        # score = mean of the 4 items; fall back to the stored construct mean
        score = items.mean(axis=1) if not items.empty else pd.to_numeric(
            post[MEANS[label]], errors="coerce")
        score = score.dropna()
        alpha = cronbach_alpha(items) if not items.empty else None
        astr = f"{alpha:.3f}" if alpha is not None else "  n/a"
        flag = "PASS" if len(score) and score.mean() >= TARGET else "below"
        sd = score.std(ddof=1) if len(score) > 1 else 0.0
        print(f"{label:26} {len(score):>4} {score.mean():>6.2f} {sd:>6.2f} {astr:>7}  "
              f"{interpret(alpha):12} {flag}")

    conf = pd.to_numeric(post["confidence"], errors="coerce").dropna()
    if len(conf):
        sd = conf.std(ddof=1) if len(conf) > 1 else 0.0
        print(f"{'Confidence (post)':26} {len(conf):>4} {conf.mean():>6.2f} {sd:>6.2f} "
              f"{'  n/a':>7}  {'single item':12} "
              f"{'PASS' if conf.mean() >= TARGET else 'below'}")

    confidence_change(tam)

    if post["participant_role"].notna().any():
        print("\nMean score by participant role")
        cols = [c for c in MEANS.values() if c in post.columns]
        print(post.groupby("participant_role")[cols].mean().round(2).to_string())

    if "module_name" in post.columns and post["module_name"].notna().any():
        print("\nMean satisfaction by module")
        print(post.groupby("module_name")["satisfaction_rating"]
                  .agg(["count", "mean"]).round(2).to_string())

    # distinct participants, not rows: an officer contributes a pre and a post row
    people = tam.groupby("participant_role")["participant_code"].nunique()
    n_eo = int(people.get("extension_officer", 0))
    n_fm = int(people.get("farmer", 0))
    print("\nProposal pilot target: 20 extension officers + 20 farmers.")
    print(f"Participants so far: {n_eo}/20 officers, {n_fm}/20 farmers "
          f"({len(tam)} rows).")

    out = ROOT / "data" / "feedback_export.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    tam.to_csv(out, index=False)
    print(f"\nSaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()