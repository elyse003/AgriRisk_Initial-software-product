# AgriRisk Rwanda 🌱

**AI-powered agricultural risk management for smallholder farmers in Rwanda.**

A machine-learning platform with four advisory modules, served through a web
dashboard for extension officers and a farmer-facing WhatsApp chatbot preview
(Kinyarwanda + English). Covers **all 30 districts** of Rwanda.

> **GitHub repository:** `https://github.com/<your-username>/agririsk-rwanda`  *(replace with your link)*

---

## What's in this submission (Initial Software Demo)

| Deliverable | Location |
|-------------|----------|
| **ML notebook** (data viz, engineering, model architecture, metrics) — *run it to produce outputs* | `notebooks/AgriRisk_Rwanda_Models.ipynb` |
| **Web app MVP** (6 screens, custom UI, real models) | `webapp/` |
| **Trained models + metrics** | `models_store/` |
| **Original UI design** (React mockup, used as the design reference) | `agririsk_web_dashboard.jsx` |

### Modules and metrics (this project's trained models)

| # | Module | Model | Metric | Result | Target |
|---|--------|-------|--------|--------|--------|
| 1 | Crop price forecast | RF baseline *(Prophet/ARIMA/LSTM in full env)* | MAPE | **5.6%** | < 15% |
| 2 | Seasonal climate-inflation risk | Random Forest | Accuracy | **93.5%** | > 85% |
| 3 | Crop disease alert | FAO rules + Open-Meteo | rule-based | — | — |
| 4 | Input recommender | Weighted ranking | top-3 by budget | — | — |

---

## Run the web app (the MVP)

```bash
git clone https://github.com/<your-username>/agririsk-rwanda.git
cd agririsk-rwanda

python -m venv venv
venv\Scripts\activate                # Windows  (Mac/Linux: source venv/bin/activate)

pip install streamlit pandas numpy scikit-learn matplotlib seaborn python-dotenv requests flask

# (data + models already ship in the repo; to regenerate them:)
python scripts/generate_sample_data.py
python scripts/train_models.py

# launch the web app
python webapp/app.py
```

Open **http://localhost:5000**. The dashboard loads with a sidebar of six screens:

```
Home → Price Forecast → Seasonal Risk → Disease Alert → Input Recommender → WhatsApp Preview
```

Every screen is functional — the buttons call the trained models through a small
Flask API (`/api/forecast`, `/api/risk`, `/api/disease`, `/api/inputs`, `/api/chat`),
so the same endpoints also serve as the project's API.

> **Using your real data:** place the downloaded files in `data/raw/` with these names —
> `wfp_food_prices_rwa.csv`, `CPI_time_series_April_2026.xls` (or `.xlsx`),
> `CMO-Historical-Data-Monthly.xlsx`, `rwa-rainfall-subnat-full.csv`,
> `minagri_input_prices_real.csv` — then run:
> ```bash
> pip install openpyxl xlrd xgboost
> python scripts/prepare_data.py
> ```
> This converts them into `data/processed/` (canonical schema) and retrains the risk model.
> Both apps auto-prefer `data/processed/` over the synthetic sample, so they immediately
> show real data. Without this step they run on the bundled synthetic sample.

---

## Screens

- **Home** — key stats, active disease alerts, delivery channels, live ML-model metrics, data sources.
- **Price Forecast** — pick crop + district → 4-week chart + sell/hold advisory.
- **Seasonal Risk** — pick district + season → High/Medium/Low with contributing factors.
- **Disease Alert** — pick district → live Open-Meteo weather + crop-specific FAO disease warnings.
- **Input Recommender** — pick crop + district + budget → top-3 affordable inputs.
- **WhatsApp Preview** — farmer chatbot simulation; type a Kinyarwanda query (e.g. `ibigori igiciro bugesera`) and get a reply from the same models. (Live Twilio/SMS delivery is the deployment phase.)

---

## Notebook

`notebooks/AgriRisk_Rwanda_Models.ipynb` contains the full ML workflow (data viz,
data engineering, model architecture, metrics) as clean code + markdown cells with
**no pre-run outputs**. Open it in Jupyter / VS Code / Colab and **Run All** to
generate the figures and metrics. Running it also writes the figures to
`reports/figures/` and the trained models to `models_store/`.

---

## Designs / visualizations

- **UI design** is based on the project's React mockup (`agririsk_web_dashboard.jsx`),
  re-implemented as the functional Flask web app.
- **Data visualizations** are produced by running the notebook (saved to `reports/figures/`):
  price distributions, seasonality, CPI/fertilizer trends, risk class distribution,
  correlations, confusion matrix, feature importance, forecast chart.
- **App screenshots:** capture each screen at `http://localhost:5000` and add them here.

---

## Deployment plan

1. **Containerize** — `docker compose up` builds the app + a PostgreSQL service (schema in `src/db/schema.sql`).
2. **Host** — deploy to **Railway.app** (free tier) for a public URL; heavy model training runs on Google Colab.
3. **Data refresh** — weekly ingestion updates price / CPI / fertilizer / rainfall; disease calls Open-Meteo live.
4. **Farmer channels (next phase)** — wire the WhatsApp chatbot (Twilio) and weekly SMS (Africa's Talking)
   to the same `/api/chat` logic that already powers the in-app preview.
5. **Pilot** — evaluate with 40 participants in Musanze + Bugesera via a TAM questionnaire.

---

## Project layout

```
agririsk-rwanda/
├── webapp/               # Flask web app (MVP): app.py + templates/ + static/
├── notebooks/            # executed ML notebook
├── reports/figures/      # generated visualizations
├── models_store/         # trained models + metrics.json
├── config/settings.py    # 30 districts, coords, targets, thresholds
├── data/                 # sample datasets (swap for real data)
├── scripts/              # data generation, training, notebook build
├── src/                  # data pipeline, models, db schema, channels
└── dashboard/            # (alternative) simple Streamlit interface
```

## Video demo

A 5–10 min screen recording walking through each screen and the notebook results. *(Add the link here.)*

## License

MIT
