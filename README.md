# AgriRisk Rwanda

## Description

AgriRisk Rwanda is a decision-support application for agricultural extension officers and
smallholder farmers. It brings four tools together for maize, beans, and Irish potatoes
across all 30 districts of Rwanda:

- **Crop price forecasting** for four weeks ahead, per crop and district.
- **Seasonal risk** rated low, medium, or high from rainfall, food inflation, and fertilizer cost.
- **Crop disease alerts** from live weather and FAO disease guidance.
- **Input recommender** that ranks affordable fertilizer for a chosen crop, district, and budget.

The application runs as a Streamlit dashboard with a farmer-facing WhatsApp chat in
Kinyarwanda and English. It is backed by trained machine learning models and a PostgreSQL database (SQLite for local development).

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
- **Data refresh:** schedule `scripts/download_data.py` + `prepare_data.py` to update prices, inflation, fertilizer, and rainfall.

## Video demo

<add your 5 to 10 minute video link>

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
