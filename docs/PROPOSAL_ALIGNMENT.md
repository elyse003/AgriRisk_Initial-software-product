# AgriRisk Rwanda — Proposal Alignment & Research Results

This document maps every commitment in the research proposal ("AgriRisk Rwanda:
AI-Powered Agricultural Risk Management for Smallholder Farmers") to what the
implementation actually does, records the results of the four research questions,
and states plainly where the delivered system deviates from the proposal and why.

It exists so nothing in the defense is a surprise.

---

## 1. Research questions — answered

All four RQs are now backed by reproducible scripts. Run them yourself:

```bash
pip install -r requirements-research.txt
python scripts/rq1_ablation.py            # RQ1
python scripts/rq2_ablation.py            # RQ2
python scripts/rq3_disease_validation.py  # RQ3
python scripts/export_feedback.py         # RQ4 (once pilot responses exist)
```

### RQ1 — Does adding CPI as a Prophet regressor improve price forecasts?

Prophet, 12-month hold-out, maize/beans/potatoes × Musanze/Bugesera (6 series).

| Arm | Pooled mean MAPE |
|---|---|
| Price history alone | **14.55 %** |
| + CPI & fertilizer regressors (*actual* future values) | **12.82 %** |
| + CPI & fertilizer regressors (*last-known*, deployable) | **15.10 %** |

Wilcoxon signed-rank on paired absolute percentage errors:

* price-only vs +regressors (actual): **p = 0.197 → not significant**
* price-only vs +regressors (last-known): **p = 0.480 → not significant**

**Answer.** Adding CPI and the fertilizer index as Prophet regressors does **not
significantly improve** forecast accuracy. Even the optimistic arm — which feeds
Prophet the *true* future CPI a live system could never know — fails significance.
The deployable variant (carrying the last observed CPI forward) is actually
*worse* than price history alone.

Per-series, maize benefits (Musanze 14.14 → 9.43; Bugesera 26.48 → 17.11) while
beans and potatoes get worse, which is why the pooled effect washes out.

**Consequence.** This directly justifies the shipped model, which forecasts from
price history only (scale-free log-returns) and does **not** use CPI regressors.
The proposal assumed the regressors would help; the experiment says otherwise.

> Methodological caveat, stated openly: Prophet requires future regressor values.
> The "actual" arm is an upper bound on any benefit, not a deployable result.

### RQ2 — Does combining rainfall with CPI beat either in isolation?

Random Forest, identical stratified hold-out (n = 286 test rows), majority-class
baseline = 0.336.

| Features | Accuracy | Macro-F1 |
|---|---|---|
| rainfall_anomaly | **0.318** | 0.316 |
| cpi_change | **0.696** | 0.698 |
| fert_change | **0.699** | 0.700 |
| rainfall + cpi | 0.570 | 0.575 |
| rainfall + fert | 0.570 | 0.571 |
| cpi + fert | 0.696 | 0.698 |
| all three | 0.605 | 0.608 |

McNemar (exact) on the RQ2 comparison:

* rainfall+cpi **vs rainfall alone**: Δacc = +0.252, p < 0.0001 → **combined better**
* rainfall+cpi **vs cpi alone**: Δacc = −0.126, p < 0.0001 → **combined significantly WORSE**

**Answer.** Combining rainfall with CPI does **not** improve on CPI alone — it
*significantly degrades* it. Rainfall anomaly on its own performs **below the
majority baseline** (0.318 < 0.336), i.e. it carries essentially no signal for
6-month-ahead price stress. The economic signals (food CPI, fertilizer index)
dominate.

This is a genuine negative result and an honest contribution: for *price*-stress
prediction in Rwanda, macroeconomic pressure — not local rainfall — is what
matters. (Rainfall matters for *yield*, which this module does not predict.)

### RQ3 — Does the disease module fire in the right seasons?

**Scope correction (important).** The proposal promised validation "against RAB
historical disease outbreak records". Those records are **not publicly
available**, so outbreak-level validation was not possible. Instead the FAO rules
were replayed over **five years of real historical weather** (Open-Meteo ERA5
archive, 2020-2024) for both pilot districts, and tested for concentration in
Rwanda's rainy seasons (Mar–May, Oct–Dec), when blight and fungal disease
actually occur.

| District | Disease (crop) | Alert rate, rainy | Alert rate, dry | Wet/dry lift |
|---|---|---|---|---|
| Musanze | Late Blight (potatoes) | 1.00 | 0.75 | 1.34 |
| Musanze | Angular Leaf Spot (beans) | 0.99 | 0.59 | 1.69 |
| Musanze | Northern Leaf Blight (maize) | 0.98 | 0.51 | 1.94 |
| Musanze | Gray Leaf Spot (maize) | 0.75 | 0.39 | 1.94 |
| Bugesera | Late Blight (potatoes) | 0.97 | 0.58 | 1.67 |
| Bugesera | Gray Leaf Spot (maize) | 0.94 | 0.52 | 1.81 |
| Bugesera | Angular Leaf Spot (beans) | 0.93 | 0.50 | 1.85 |
| Bugesera | Northern Leaf Blight (maize) | 0.93 | 0.42 | 2.22 |

**Answer.** Every disease in both districts shows a **wet/dry lift of 1.34–2.22**:
the rules fire 1.3–2.2× more often in the rainy seasons. Directionally, the module
behaves correctly.

**But** the wet-season alert rate is 0.93–1.00, i.e. the rules fire in *almost
every* 14-day window of the rainy season. That is **high sensitivity and low
specificity** — the thresholds are permissive. Calibrating them requires exactly
the RAB outbreak data that is unavailable. This is stated as a limitation, not
hidden.

### RQ4 — TAM evaluation

The **instrument is built and working**; the pilot itself has not yet been run.

* In-app questionnaire: `dashboard/pages/8_Feedback.py` (sidebar → Feedback), for
  officers and farmers, in Kinyarwanda and English.
* Captures the four TAM constructs on a 1–5 Likert scale: **perceived usefulness,
  perceived ease of use, satisfaction, confidence in data-driven advisories**,
  plus free-text comments.
* Stores them **anonymously** in the `feedback` table — only the participant code
  (`EO-01`…`EO-20`, `FM-01`…`FM-20`), never a name or phone number, matching the
  proposal's consent and anonymisation protocol.
* **Anonymity is enforced, not just asserted.** An earlier version also wrote the
  signed-in account's `user_id` onto each response, which made it *pseudonymous*:
  every answer was linkable back to a named user. The proposal requires that "no
  names, phone numbers, or identifying information are recorded alongside
  evaluation responses", so `submit_tam_feedback()` now takes no `user_id` at all.
  Verified by inserting a row and reading it back: `user_id IS NULL`.
* The code-to-identity mapping must be kept **offline**, in a password-protected
  file, and deleted within 30 days of study completion, per the proposal's ethics
  section. It is that sheet, not the database, that could re-identify a participant.
* `scripts/export_feedback.py` reports n, mean ± sd per construct, a breakdown by
  role and module, tracks progress toward the 20 + 20 target, checks the
  **mean satisfaction ≥ 4.0 / 5** success criterion, and exports a CSV.

#### The 12-item instrument (closed)

The questionnaire now matches the proposal exactly:

| Construct | Items | Stored as |
| --- | --- | --- |
| Perceived usefulness | 4 | `pu1`…`pu4` |
| Perceived ease of use | 4 | `peou1`…`peou4` |
| Satisfaction | 4 | `sat1`…`sat4` |
| Confidence (officers, **pre and post**) | 1, asked twice | `confidence` + `phase` |

* Items are stored **individually**, not as construct means, because Cronbach's
  alpha needs per-item variance: it cannot be recovered from the mean alone.
  `scripts/export_feedback.py` reports alpha per construct with an
  interpretation (poor / questionable / acceptable / good / excellent).
* Extension officers answer a **confidence baseline before** using the platform
  (`phase="pre"`, that one item only) and the **full questionnaire after**
  (`phase="post"`). `export_feedback.py` pairs the two by participant code and
  runs a **Wilcoxon signed-rank test**, which is what lets RQ4 report a
  *measurable improvement* rather than a single post-hoc rating. Farmers answer
  once.
* The construct means are still written to the original columns, so rows
  collected before this change (which have `phase = NULL`) are treated as
  `post` and still count toward the summary.

Verified end-to-end in a browser: the baseline form renders 1 slider, the full
form renders 13 (12 items + confidence), both rows store `user_id IS NULL`, and
a synthetic 8-officer / 6-farmer pilot produces alpha per construct and a
significant pre/post confidence change.

**Status.** The instrument is complete, anonymous, and matches the proposal. The
pilot with 40 participants across Musanze and Bugesera remains to be conducted.

---

## 2. Performance targets

| Target (proposal) | Result | Status |
|---|---|---|
| Price forecasting MAPE < 15 % | maize 10.39 %, beans 10.89 %, potatoes 9.21 % (**avg 10.16 %**) | ✅ **Met** |
| Seasonal risk accuracy > 85 % | **66.4 %** accuracy, 0.665 macro-F1 (baseline 33.3 %) | ❌ **Not met** |
| TAM mean satisfaction ≥ 4 / 5 | instrument ready, pilot not yet run | ⏳ Pending |

### Why the 85 % risk target is not met — and why the 66 % is the better number

The 85 % figure was set before the labelling method was decided. There are two
ways to build this classifier:

1. **Train it to reproduce a hand-written threshold rule.** It then trivially
   scores ~100 % — because it is simply re-learning the rule that generated its
   own labels. An earlier version of this project did exactly that. The number is
   meaningless: it measures nothing about the future.
2. **Label from the realized outcome.** The label used here is the **tercile of
   the realized 6-month-ahead change in staple prices** per district-month. The
   model must predict a genuine future outcome from conditions known at planting.

The delivered system uses (2). Against a 33.3 % majority baseline, **66.4 % is
roughly double chance** on a hard, honest prediction problem. The 85 % target was
achievable only under approach (1), which would have been scientifically empty.

The RQ2 ablation reinforces this: the ceiling here is set by how much pre-season
information actually predicts price stress — and rainfall, one of the three
proposed inputs, turns out to contribute nothing.

---

## 3. Deviations from the proposal (disclosed)

| # | Proposal said | Implementation does | Why |
|---|---|---|---|
| 1 | Price model: **Prophet** (primary), LSTM, ARIMA baseline | Ships **GradientBoostingRegressor** on scale-free log-returns, pooled across districts | Prophet fits one series at a time; district series are short/sparse. Pooled returns borrow strength, deploy anywhere, and score **10.2 % vs Prophet's 14.6 %** pooled MAPE. All three are still compared in the notebook. |
| 2 | Risk model: **Random Forest** vs XGBoost | Ships **GradientBoostingClassifier**; RF and XGBoost compared | GB won on the same hold-out (66.4 % vs RF 61.2 %). Both are reported in `metrics.json`. |
| 3 | Price model uses **CPI + fertilizer as regressors** | Shipped model uses price history only | **RQ1 shows the regressors do not significantly help**, and hurt in the deployable variant. |
| 4 | CPI source: **NBR / FRED monthly food CPI** | **World Bank CPI (2010=100), annual, interpolated to monthly** | No public monthly *food* CPI API exists for Rwanda. This is a real weakness: an interpolated annual series is smoother than true monthly food inflation. |
| 5 | **Weekly** prices, **4-week-ahead** forecast | **Monthly** WFP prices, **next-month** forecast | The WFP Rwanda series is published monthly, not weekly. The horizon (~4 weeks) is preserved. |
| 6 | Hosting on **Railway.app** | **Streamlit Cloud** (app) + **Render** (webhook) | Free tiers, same outcome: a public URL. `Dockerfile` + `docker-compose.yml` are in the repo for one-command local deployment as promised. |
| 7 | Validate disease vs **RAB outbreak records** | **Climatological consistency check** on 5 yrs of ERA5 weather | RAB outbreak records are not publicly available. See RQ3. |
| 8 | Explainability via **SHAP** | Dashboard shows impurity importances; **SHAP now computed** in `scripts/shap_risk.py` | SHAP added. It also *corrects* the picture (below). |
| 9 | §3.3 documents the **five public data sources** | The **UI no longer names the providers** (WFP, World Bank, CHIRPS, Open-Meteo, MINAGRI / Smart Nkunganire) | Removed from the landing page and every dashboard page at the product owner's request. The proposal requires the sources be *documented and openly licensed*, not displayed in-product. They remain in §3.3 of the proposal, in this document, and in the README. The Price Forecast page still distinguishes a **measured** farmgate figure from an **estimated** one, since that is data quality, not attribution. |
| 10 | **§3.5 ERD:** "FEEDBACK stores user satisfaction ratings with **user_id as a foreign key referencing USERS**" — vs **§ethics:** "no names, phone numbers, or **identifying information are recorded alongside evaluation responses**" | TAM rows store **no `user_id`** | **The proposal contradicts itself.** The ERD makes every response linkable to a named account; the ethics protocol forbids exactly that. The ethics commitment is the one made to participants under informed consent, so it wins. The legacy `submit_feedback()` (a per-module star rating, not a TAM response) still carries `user_id`, which is what the ERD was describing. |
| 11 | Authentication is username + password against the USERS table; the proposal never mentions OAuth, Google, or an email field | Adds **Google sign-in** (OpenID Connect via `st.login`) alongside the password form, and a `users.email` column | An **addition beyond scope**, requested after the proposal was written. It is optional: the button only renders when `[auth.google]` is configured, so the system still runs exactly as specified without it. Google accounts store no `password_hash` and default to the least-privileged `farmer` role. The `email` column is a departure from the §3.5 ERD. |

### SHAP vs impurity importance (risk classifier)

| Feature | SHAP share | Impurity share |
|---|---|---|
| cpi_change | 36.7 % | 36.6 % |
| fert_change | 36.5 % | 39.7 % |
| rainfall_anomaly | 12.9 % | 16.7 % |
| soil_ph | 7.9 % | 3.2 % |
| altitude_m | 5.0 % | 2.9 % |
| soil_fertility | 0.7 % | 0.3 % |
| drainage | 0.3 % | 0.5 % |

Soil & terrain account for **13.9 % of SHAP importance** versus 7.2 % by impurity —
impurity importance was *under*-crediting soil. Consistent with RQ2, the economic
signals dominate and rainfall is modest.

---

## 4. Development tools — promised vs present

| Tool | Status |
|---|---|
| Python, pandas/NumPy, scikit-learn, Streamlit, Requests/Open-Meteo | ✅ core of the app |
| Facebook Prophet, statsmodels (ARIMA), XGBoost | ✅ in the notebook + `scripts/rq1_ablation.py`, `rq2_ablation.py` |
| **SHAP** | ✅ `scripts/shap_risk.py` (was missing) |
| **MLflow** | ✅ `scripts/train_models.py` logs params, metrics and artifacts to a local SQLite backend (`mlflow ui`) (was missing) |
| PostgreSQL | ✅ SQLAlchemy; set `DATABASE_URL`, else SQLite |
| Docker Compose | ✅ `Dockerfile` + `docker-compose.yml` |
| draw.io UML | ✅ in the proposal document |
| GitHub, **MIT license** | ✅ repo + `LICENSE` (was missing) |

Research dependencies are isolated in `requirements-research.txt` so the deployed
app and webhook keep lean build requirements.

---

## 5. Delivered beyond the proposal

* **USSD channel** (`*384#`-style menu simulator) — a fifth delivery channel that
  was not promised, reaching feature phones with no internet and no data cost.
* **Esoko farmgate integration** — the proposal forecasts *market* prices; the
  system now reports **farmgate** prices (what the farmer is actually paid), using
  WFP for the trend and Esoko for the level, with a data-gated upgrade roadmap.
* **District soil & terrain features** (RAB/MINAGRI agro-ecological zones) added to
  the risk model, and **soil-pH-driven lime advice** in the input recommender.
* **Conversation memory** in the chatbot (multi-turn: "price" → "beans" → "Musanze").
* **Role-based access** (farmer / officer / administrator) with PBKDF2 password
  hashing and session persistence.
* **12 automated system tests** (`pytest tests/test_system.py`).
* **One shared advisory core** — dashboard, chatbot, SMS, USSD and WhatsApp all call
  the same functions, so every channel returns identical figures by construction.

---

## 6. Honest limitations

1. **Esoko farmgate history is ~1 month.** A farmgate model cannot yet be trained;
   the hybrid borrows dynamics from WFP. Upgrades are gated on data volume
   (seasonal margin at ~6 months, direct training at ~14).
2. **Seasonal risk is 66 %.** Bounded by how much pre-season information predicts
   price stress; RQ2 shows rainfall contributes nothing.
3. **Disease rules are permissive** (high sensitivity, low specificity) and cannot
   be calibrated without RAB outbreak data.
4. **CPI is interpolated from an annual series**, not true monthly food inflation.
5. **The TAM pilot has not been run.** The instrument is ready.
6. **Live SMS/WhatsApp need a production CPaaS account.** The pipeline is dry-run
   safe by default so nothing sends or bills accidentally.
7. **Kinyarwanda translations are a working draft** pending native-speaker review.

All model results in this document are reproducible from the scripts listed in §1.