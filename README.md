# AgriRisk Rwanda

## Overview

AgriRisk Rwanda is a nationwide machine-learning advisory platform for smallholder
farmers. It follows the whole farming cycle and supports four decisions: crop price
forecasting, seasonal climate-inflation risk, climate-driven disease alerts, and
land-size-based fertilizer (input) planning. It covers all 30 districts and Rwanda's
staple crops — maize, beans, and Irish potatoes — in Kinyarwanda and English.

The platform is built farmer-first. The farmer is the primary user, reached on the
basic phone they already own, while extension officers and a national administrator
are supporting roles who use the web dashboard.

### How it is delivered

- **Web dashboard (Streamlit)** — for extension officers and the administrator, to
  view forecasts, risk, disease alerts, and the farmers they support.
- **WhatsApp-style chat** — a farmer-facing conversational tool in Kinyarwanda and
  English that answers short questions (price, risk, disease, fertilizer quantity).
- **SMS** — short Kinyarwanda alerts for any basic phone, with no internet or data
  cost. The subscriber registry and alert logic are implemented; connecting the live
  gateway (Africa's Talking) is a deployment step.
- **USSD Preview** — a menu-based channel for farmers who cannot read or do not use
  smartphones. This is planned future work, in line with the project proposal.

### Under the hood

The advice is produced by trained machine-learning models (price forecasting with
ARIMA, Prophet, and LSTM against a random-forest baseline; seasonal-risk
classification with random forest and XGBoost) and a rule-based fertilizer planner.
The system is backed by a database — SQLite for local development and PostgreSQL for
production — and one keyless live weather API (Open-Meteo) powering the real-time
disease alerts. The models are trained on public datasets (WFP prices, NISR food
inflation, World Bank fertilizer costs, CHIRPS rainfall, and MINAGRI input prices).

## Live demo

- **Landing page (homepage):** https://elyse003.github.io/AgriRisk_Initial-software-product/
- **Dashboard (the app):** https://agririskinitial-software-appuct-nedmfzzrbgaz7jhb3c74jd.streamlit.app

The landing page's "Open the dashboard" buttons link to the live Streamlit app. The
homepage is published from `landing/` by a GitHub Actions workflow; the app is deployed
on Streamlit Community Cloud.

## Repository

https://github.com/elyse003/AgriRisk_Initial-software-product.git

## Setting up the environment and project

Requires Python 3.10 or newer.

```bash
git clone https://github.com/elyse003/AgriRisk_Initial-software-product.git
cd AgriRisk_Initial-software-product

python -m venv venv
venv\Scripts\activate                 # Windows. macOS/Linux: source venv/bin/activate

pip install -r requirements.txt
python scripts/init_db.py             # create and seed the local database
streamlit run dashboard/Home.py
```

The dashboard opens at http://localhost:8501.

### Rebuilding the data and models from the real public sources

The models ship pre-trained in `models_store/`. To rebuild everything from scratch
on freshly downloaded public data:

```bash
pip install openpyxl xlrd                 # for the Excel sources
python scripts/download_data.py           # fetch WFP, rainfall, fertilizer, CPI -> data/raw/
python scripts/prepare_data.py            # clean -> data/processed/
python scripts/train_models.py            # train + serialize models -> models_store/
```

`download_data.py` pulls the WFP prices and CHIRPS rainfall from HDX, the fertilizer
index from the World Bank Pink Sheet, and Rwanda CPI from the World Bank API — all open
and free, no account needed. MINAGRI input prices are extracted by hand (PDF bulletins)
into `data/raw/minagri_input_prices_real.csv`. The deep-learning comparison in the
notebook additionally needs `prophet`, `statsmodels`, and `tensorflow`, which install
most easily in Google Colab.

## Accounts and roles

The public landing page is open; the dashboard requires sign-in. Accounts have a
role that controls access: **super_admin** and **officer** get the full toolset,
while **farmer** gets a limited view (the same advice reaches farmers by SMS and
WhatsApp). Passwords are stored as salted PBKDF2 hashes. Demo accounts (created by
`scripts/init_db.py`):

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `admin123` | super_admin |
| `musanze` | `officer123` | officer |
| `jean` | `farmer123` | farmer |

Sign-in is session-based (a hard refresh signs you out again), which is fine for
the prototype. **Settings** holds a light/dark theme toggle and account details;
the **Ururimi / Language** switch (English / Kinyarwanda) is in the sidebar on
every page.

## Using the app

The dashboard hub links to each tool, also reachable from the sidebar:

- **Price Forecast** takes a crop and district and returns a next-month price estimate with a recommendation.
- **Seasonal Risk** takes a district and season and returns a risk rating with its contributing factors.
- **Disease Alert** takes a district and lists crop disease risks from the live weather forecast.
- **Input Recommender** takes a crop, district, and budget and returns a fertilizer plan sized to the land.
- **WhatsApp Preview** is a farmer chat that answers price, risk, disease, and input questions.

## Designs

Interface screenshots are in `docs/screenshots/`:

![Home](docs/screenshots/home.png)
![Price Forecast](docs/screenshots/price_forecast.png)
![Seasonal Risk](docs/screenshots/seasonal_risk.png)
![Disease Alert](docs/screenshots/disease_alert.png)
![Input Recommender](docs/screenshots/input_recommender.png)
![WhatsApp Preview](docs/screenshots/whatsapp_preview.png)

Figma mockup: <[Figma link](https://www.figma.com/design/xojszh9Hb3OfHGNwGK8eNG/AgriRisk?node-id=3-2&t=hLKZUy3iGXhZkMXo-0)>

## Datasets

Every model is trained on public data. Each source, its key fields, and the module it feeds:

| Dataset | Source | Key fields | Used for |
| --- | --- | --- | --- |
| Crop market prices | WFP (HDX) | date, district, commodity, pricetype, price RWF | Price forecasting (target) |
| Food consumer price index | NISR | date, food CPI (base 2014) | Price regressor + risk feature |
| Fertilizer price index | World Bank Pink Sheet | date, fertilizer index | Price regressor + risk feature |
| District rainfall | CHIRPS (HDX) | date, district, rainfall vs normal | Seasonal-risk climate feature |
| Weather forecast | Open-Meteo (live API) | temperature, humidity, precipitation | Disease alerts |
| Input prices | MINAGRI / Smart Nkunganire | input, type, crop, subsidised and market price | Input recommender |
| Live market prices | eSoko Rwanda | date, market, district, farmgate / wholesale / retail price | Current-price reference and validation |

Prices use the retail, RWF series. The processing and feature steps for each source live in `scripts/prepare_data.py`, and the dashboard shows how current the data is.

## Models

Two models ship in the app, both trained on the real data by `scripts/train_models.py`
and serialized to `models_store/`. Reported numbers are on a temporal/stratified
hold-out the model never trained on.

### Price forecasting (Module 1)

The **deployed** forecaster is a gradient-boosted regression, one model per crop,
pooled across all districts. It predicts the next-month **log return** (scale-free, so
one model works across districts at very different price levels) and reconstructs the
price. WFP prices are monthly, so the horizon is the next month (~4 weeks).

| Crop | Hold-out MAPE | Naive (last-value) |
| --- | --- | --- |
| Maize | 10.4% | 11.4% |
| Beans | 10.9% | 10.9% |
| Potatoes | 9.2% | 9.8% |

Average **10.2% MAPE**, comfortably under the 15% target. Monthly commodity prices are
close to a random walk, so the model edges out the naive last-value baseline rather than
crushing it — an honest result on real data. The heavier **ARIMA / Prophet / LSTM**
comparison from the proposal lives in `notebooks/AgriRisk_Rwanda_Models.ipynb`; those
libraries are awkward to deploy on Windows / Streamlit Cloud, so the scikit-learn model
is what runs in the app.

### Seasonal risk (Module 2)

Risk is framed as a **real, data-derived** prediction: for each district-month the label
is the realized 6-month-ahead change in local staple prices, split into High / Medium /
Low terciles. The classifier (gradient boosting) learns whether pre-season conditions —
the season's rainfall anomaly, food-price inflation (CPI YoY) and fertilizer-cost
momentum — predict that coming price stress.

| Metric | Value |
| --- | --- |
| Accuracy | ~67% |
| Macro F1 | ~0.67 |
| Majority-class baseline | 33% |

About **2× better than chance** on three balanced classes. This deliberately replaces an
earlier version whose labels came from a hand-written rule, which let the classifier
"reproduce the rule" and score a meaningless 100%. ~67% is lower but genuine: predicting
food-price stress from pre-season signals is a real, hard problem.

## Database

The database layer (`src/db/connection.py`) runs on **PostgreSQL in production and
SQLite locally**, through one SQLAlchemy engine. The six tables match the proposal
ERD and `src/db/schema.sql`: `users`, `price_records`, `risk_scores`,
`input_catalogue`, `feedback`, `subscribers`.

- **Local (default):** no setup. With no `DATABASE_URL` set, it uses a SQLite file
  at `data/agririsk.db`, created and seeded by `python scripts/init_db.py`.
- **PostgreSQL:** set the `DATABASE_URL` environment variable (or Streamlit secret)
  to a Postgres connection string and the same code uses Postgres. The tables are
  created automatically on first run; `init_db()` then seeds the sample rows.

```bash
# local Postgres via Docker (uses docker-compose.yml: Postgres 15 + the app)
docker compose up

# or point at any Postgres (e.g. a free Neon / Supabase / Render database)
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DBNAME"
python scripts/init_db.py
```

On Streamlit Community Cloud, add `DATABASE_URL` under **Settings → Secrets** to use
a hosted Postgres (otherwise the app falls back to an ephemeral SQLite file).

## Deployment plan

- **Prototype (now):** runs locally with Streamlit; SQLite by default, PostgreSQL when `DATABASE_URL` is set.
- **Hosting:** the dashboard is deployed on Streamlit Community Cloud; the static landing page on GitHub Pages.
- **Farmer channels:** connect the WhatsApp preview to the WhatsApp Business API through Twilio, and
  SMS to Africa's Talking.
- **Data refresh:** a GitHub Actions workflow (`.github/workflows/refresh-data.yml`) runs monthly, re-downloading the public sources, rebuilding `data/processed/`, retraining the models, and committing the refreshed artifacts so the deployed app stays current. It can also be triggered by hand from the Actions tab.

## Video demo

<[DEMO VIDEO](https://youtu.be/5BUKRpP0X9A)>

## Code files

```
.
├── dashboard/      Streamlit app (Home.py and pages/)
├── src/            models, data preparation, messaging channels, database
├── scripts/        data preparation, training, and database setup
├── notebooks/      modelling notebook with results
├── tests/          system tests
├── data/           raw and processed datasets, SQLite database
├── models_store/   trained models and metrics
├── config/         settings (crops, districts, paths)
├── assets/         logo
├── docs/           screenshots
└── requirements.txt
```

Run the system tests with `pip install pytest` then `pytest tests/test_system.py -v`.

## Tech stack

Python, Streamlit, scikit-learn, pandas, Prophet, statsmodels, TensorFlow, XGBoost, PostgreSQL, SQLite, SQLAlchemy.
