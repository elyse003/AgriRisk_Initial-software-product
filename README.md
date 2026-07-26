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

The **same advisory engine** answers every channel, so a figure on the officer's
dashboard is identical to what a farmer is told by SMS or WhatsApp (one source of
truth — see *Architecture* below).

- **Web dashboard (Streamlit)** — for extension officers and the administrator: the
  four tools, a consolidated downloadable advisory, the SMS console, and user/catalogue
  administration.
- **WhatsApp** — a farmer-facing chat in Kinyarwanda and English that answers short
  questions (price, risk, disease, fertilizer). Live via Twilio and a small FastAPI
  webhook (`webhook/app.py`, deployed on Render).
- **SMS** — short price + seasonal-risk alerts for any basic phone, no internet or data.
  Sent from the officer's **Farmer Alerts** console over Africa's Talking. Dry-run-safe
  by default (nothing sends without credentials); farmers opt in/out with a single
  keyword (`YEGO` / `STOP`).
- **USSD Preview** — a `*384#`-style menu simulator for feature phones, using the same
  data and advice as the chat.
- **In-app chat** — the same bot, embedded in the dashboard for officers.

### Under the hood

The advice comes from two trained scikit-learn models (a gradient-boosted price
forecaster and a gradient-boosted seasonal-risk classifier) plus two rule-based engines
(FAO-style disease rules on a live forecast, and an agronomic input planner). The price
model was benchmarked against **ARIMA, Prophet, LSTM, a multi-layer perceptron, Random
Forest and XGBoost** in the notebook; gradient boosting generalised best on the small
monthly series and is what ships. The system is backed by a database — SQLite for local
development, PostgreSQL for production — and one keyless live weather API (Open-Meteo)
powering the real-time disease alerts. Models train on public datasets (WFP prices, NISR
food inflation, World Bank fertilizer costs, CHIRPS rainfall, MINAGRI input prices) with
eSoko farmgate prices as a real-price reference.

## Architecture — one source of truth

Every channel routes through the same two functions, so all channels always agree:

```
 Dashboard · In-app chat · WhatsApp · SMS · USSD
                     │
        answer()  /  price_outlook()          ← the shared advisory engine
                     │
   Price (ML) · Risk (ML) · Disease (rules) · Inputs (rules)
                     │
        Real public data  +  trained models (models_store/*.pkl)
```

- **ML** where outcomes are learnable from history: price and price-spike risk.
- **Rule-based** where authoritative agronomy already exists: FAO disease thresholds and
  MINAGRI/RAB fertilizer rates.

## Live demo

- **Landing page (homepage):** https://elyse003.github.io/AgriRisk_Initial-software-product/
- **Dashboard (the app):** https://agririskinitial-software-appuct-nedmfzzrbgaz7jhb3c74jd.streamlit.app
- **WhatsApp webhook (health):** https://agririsk-webhook.onrender.com/

The landing page's "Open the dashboard" buttons link to the live Streamlit app. The
homepage is published from `landing/` by a GitHub Actions workflow; the app runs on
Streamlit Community Cloud; the WhatsApp webhook runs on Render.

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

To run the WhatsApp/SMS webhook locally:

```bash
pip install -r webhook/requirements.txt
uvicorn webhook.app:app --reload      # POST /whatsapp and /sms return TwiML
```

### Rebuilding the data and models from the real public sources

The models ship pre-trained in `models_store/`. To rebuild everything from scratch:

```bash
pip install openpyxl xlrd                 # for the Excel sources
python scripts/download_data.py           # fetch WFP, rainfall, fertilizer, CPI -> data/raw/
python scripts/prepare_data.py            # clean -> data/processed/
python scripts/train_models.py            # train + serialize models -> models_store/
```

`download_data.py` pulls WFP prices and CHIRPS rainfall from HDX, the fertilizer index
from the World Bank Pink Sheet, and Rwanda CPI from the World Bank API — all open and
free, no account needed. MINAGRI input prices are extracted by hand (PDF bulletins). The
deep-learning comparison in the notebook additionally needs `prophet`, `statsmodels` and
`tensorflow`, which install most easily in Google Colab (see `requirements-research.txt`).

## Accounts and roles

The public landing page is open; the dashboard requires sign-in. Access is role-based:
**super_admin** and **officer** get the full toolset, while **farmer** gets a limited
view (the same advice reaches farmers by SMS and WhatsApp). New sign-ups accept a
**Privacy Policy** and default to the farmer role. Passwords are stored as salted PBKDF2
hashes. Demo accounts (created by `scripts/init_db.py`):

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `admin123` | super_admin |
| `musanze` | `officer123` | officer |
| `jean` | `farmer123` | farmer |

Sign-in is session-based, carried across page reloads by a short signed URL token.
**Settings** holds a light/dark theme toggle and account details; the **Ururimi /
Language** switch (English / Kinyarwanda) is in the sidebar on every page and translates
the entire interface.

## Using the app

The dashboard hub links to each tool, also reachable from the sidebar:

**Console (officers & admin)**
- **Price Forecast** — next-month price for a crop/district, with a history-range filter,
  a **National average** option, and a "compare all districts" view. Downloads a
  per-crop advisory summary.
- **Seasonal Risk** — a district/season risk rating with its contributing factors, plus a
  "risk across all districts" national view.
- **Disease Alert** — crop disease risks for a district from the live 14-day forecast,
  with a 7-day / 14-day window.
- **Input Recommender** — a fertilizer plan sized to the land and budget, adjusted for the
  district's soil (lime by pH, N-P-K by fertility class).
- **Advisory Summary** — generates **one consolidated advisory** for a district (risk +
  prices + disease + input plan) that the officer previews and downloads.

**Channels**
- **USSD Preview** — a `*384#` menu simulator.
- **Farmer Alerts** — the SMS console: enroll subscribers, preview and send the weekly
  price + risk alert (dry-run-safe).

**Admin (super_admin)**
- **User Management** — add, edit and remove accounts and roles.
- **Input Catalogue** — edit the fertilizer price catalogue the recommender uses; changes
  save to the database and apply immediately.

**Farmers** use the floating chat button, or reach the same advice by SMS, WhatsApp and USSD.

## Designs

Interface screenshots are in `docs/screenshots/`:

![Home](docs/screenshots/home.png)
![Price Forecast](docs/screenshots/price_forecast.png)
![Seasonal Risk](docs/screenshots/seasonal_risk.png)
![Disease Alert](docs/screenshots/disease_alert.png)
![Input Recommender](docs/screenshots/input_recommender.png)
![WhatsApp chat](docs/screenshots/whatsapp_preview.png)

Figma mockup: [AgriRisk on Figma](https://www.figma.com/design/xojszh9Hb3OfHGNwGK8eNG/AgriRisk?node-id=3-2&t=hLKZUy3iGXhZkMXo-0)

## Datasets

Every model is trained on public data. Each source, its key fields, and the module it feeds:

| Dataset | Source | Key fields | Used for |
| --- | --- | --- | --- |
| Crop market prices | WFP (HDX) | date, district, commodity, pricetype, price RWF | Price forecasting (target) |
| Food consumer price index | NISR | date, food CPI (base 2014) | Price regressor + risk feature |
| Fertilizer price index | World Bank Pink Sheet | date, fertilizer index | Price regressor + risk feature |
| District rainfall | CHIRPS (HDX) | date, district, rainfall vs normal | Seasonal-risk climate feature |
| District agro profiles | RAB / MINAGRI AEZ | altitude, soil group, fertility, pH, drainage | Risk feature + district-specific inputs |
| Weather forecast | Open-Meteo (live API) | temperature, humidity, precipitation | Disease alerts |
| Input prices | MINAGRI / Smart Nkunganire | input, type, crop, subsidised and market price | Input recommender |
| Farmgate prices | eSoko Rwanda | date, market, district, farmgate / wholesale / retail price | Farmgate reference and validation |

Prices are expressed in farmgate terms (the price a farmer is paid). Processing and
feature steps live in `scripts/prepare_data.py`; the dashboard shows how current the data is.

## Models

Two models ship in the app, both trained on real data by `scripts/train_models.py` and
serialized to `models_store/`. Reported numbers are on a temporal / stratified hold-out
the model never trained on (also in `models_store/metrics.json`).

### Price forecasting (Module 1)

The deployed forecaster is a **gradient-boosted regression**, one model per crop, pooled
across all districts. It predicts the next-month **log return** — scale-free, so one model
works across districts at very different price levels — and reconstructs the price. WFP
prices are monthly, so the horizon is the next month (~4 weeks). Engineered features:
lagged log-returns (1/2/3/6/12 months), deviation from a 3-month mean, year-on-year trend,
and cyclical month encoding.

| Crop | Hold-out MAPE |
| --- | --- |
| Maize | 10.4% |
| Beans | 10.9% |
| Potatoes | 9.2% |

Average **10.2% MAPE**, comfortably under the 15% target. Monthly commodity prices are
close to a random walk, so the model edges out a naive last-value baseline rather than
crushing it — an honest result. The **ARIMA / Prophet / LSTM / MLP** comparison lives in
`notebooks/AgriRisk_Rwanda_Models.ipynb`; those libraries are awkward to deploy, so the
scikit-learn model ships.

### Seasonal risk (Module 2)

Risk is a **real, data-derived** prediction: for each district-month the label is the
realized 6-month-ahead change in local staple prices, split into High / Medium / Low
terciles. The **gradient-boosting** classifier learns whether pre-season conditions — the
season's rainfall anomaly, food-price inflation (CPI YoY), fertilizer-cost momentum, and
the district's soil/terrain — predict that coming price stress.

| Metric | Value |
| --- | --- |
| Accuracy | ~66% |
| Macro F1 | ~0.67 |
| Majority-class baseline | 33% |

About **2× better than chance** on three balanced classes. This deliberately replaces an
earlier version whose labels came from a hand-written rule, which let the classifier
"reproduce the rule" and score a meaningless 100%. ~66% is lower but genuine: predicting
food-price stress from pre-season signals is a real, hard problem.

### Disease (Module 3) and Inputs (Module 4)

Both are **rule-based**, by design. Disease alerts apply FAO-style climate thresholds
(temperature, humidity, wet days) to Open-Meteo's live 14-day forecast. The input planner
sizes MINAGRI/RAB per-hectare rates to the farmer's land and budget, adds lime by soil pH,
and scales N-P-K by the district's soil-fertility class — authoritative agronomy, no
training data required.

## Database

The database layer (`src/db/connection.py`) runs on **PostgreSQL in production and SQLite
locally**, through one SQLAlchemy engine (`src/db/schema.sql`): `users`, `price_records`,
`risk_scores`, `input_catalogue`, `feedback`, `subscribers`, and `bot_sessions`
(per-farmer conversation memory).

- **Local (default):** no setup. With no `DATABASE_URL`, it uses a SQLite file at
  `data/agririsk.db`, created and seeded by `python scripts/init_db.py`.
- **PostgreSQL:** set `DATABASE_URL` (env var or Streamlit secret) to a Postgres string and
  the same code uses Postgres. Tables are created on first run and seeded by `init_db()`.

```bash
# local Postgres via Docker (docker-compose.yml: Postgres 15 + the app)
docker compose up

# or point at any Postgres (e.g. a free Neon / Supabase / Render database)
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DBNAME"
python scripts/init_db.py
```

On Streamlit Community Cloud, add `DATABASE_URL` under **Settings → Secrets** to use a
hosted Postgres (otherwise the app falls back to an ephemeral SQLite file).

## Deployment

- **Dashboard:** Streamlit Community Cloud, auto-deployed from `main` (entry
  `dashboard/Home.py`).
- **WhatsApp / SMS webhook:** Render free web service (`render.yaml`, entry
  `webhook/app.py`). Point the Twilio WhatsApp sandbox's "When a message comes in" at
  `https://<service>.onrender.com/whatsapp`.
- **Landing page:** GitHub Pages, published from `landing/` by `.github/workflows/pages.yml`.
- **Farmer channels:** WhatsApp via Twilio; SMS via Africa's Talking (sandbox tested — live
  delivery needs account credit and an approved Rwanda sender ID).
- **Data refresh:** `.github/workflows/refresh-data.yml` runs monthly — re-downloading the
  public sources, rebuilding `data/processed/`, retraining the models, and committing the
  refreshed artifacts so the deployed app stays current. Can also be triggered by hand.

## Video demo

<[DEMO VIDEO](https://youtu.be/5BUKRpP0X9A)>

## Code structure

```
.
├── dashboard/      Streamlit app — Home.py (landing) + pages/ (tools, channels, admin)
│   ├── _ui.py        shared theme, sidebar nav, cached loaders, SVG charts
│   ├── _auth.py      session auth, roles, privacy policy
│   └── _i18n.py      English / Kinyarwanda translation
├── webhook/        FastAPI webhook for Twilio WhatsApp + SMS (deployed on Render)
├── src/
│   ├── models/       price forecasting, risk classifier, disease alert, input recommender
│   ├── channels/     whatsapp_bot (answer/converse), sms_alerts, sms_gateway, ussd_menu
│   ├── data/         preprocessing helpers
│   └── db/           SQLAlchemy connection + schema
├── scripts/        download / prepare / train, the RQ ablations, SHAP, feedback export
├── notebooks/      AgriRisk_Rwanda_Models.ipynb — model comparison, RQs, SHAP
├── data/           raw + processed datasets, local SQLite database
├── models_store/   trained models, metrics.json, RQ + SHAP outputs
├── config/         settings (crops, districts, thresholds), district agro profiles
├── landing/        static landing page (GitHub Pages)
├── tests/          system tests
└── requirements.txt
```

Run the system tests with `pip install pytest` then `pytest tests/test_system.py -v`.

## Tech stack

Python, Streamlit, FastAPI, scikit-learn, pandas, NumPy, SQLAlchemy, PostgreSQL / SQLite,
Twilio (WhatsApp), Africa's Talking (SMS), Open-Meteo (weather). Research notebook:
Prophet, statsmodels, TensorFlow, XGBoost.