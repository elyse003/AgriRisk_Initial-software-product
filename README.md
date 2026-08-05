# AgriRisk Rwanda

Timely, trustworthy farming advice for every Rwandan smallholder, on the phone they already carry.

## The problem, and the idea

A smallholder farmer in Rwanda faces the same four questions every season. When should I sell? Does this season look risky? Is disease coming? What inputs should I buy, and can I afford them? The data to answer all four already exists, but it sits scattered across price bulletins, weather services, and fertilizer catalogues, and almost none of it reaches the farmer in time to act.

AgriRisk Rwanda closes that gap. It turns real public data into four clear answers and delivers them on whatever device the farmer has, from a smartphone chat down to a basic-phone SMS, in Kinyarwanda and English, across all 30 districts and the country's staple crops: maize, beans, and Irish potatoes.

The design is farmer-first. The farmer is the primary user, reached on the phone they already own. Extension officers and a national administrator are the supporting roles who work in the web dashboard.

## One engine, every channel

There is a single advisory engine behind everything. A price on the officer's dashboard is the exact number a farmer receives by SMS or WhatsApp, because both come from the same two functions. That is the guarantee at the heart of the system, and it is why the advice is consistent no matter how a farmer reaches it.

* **Web dashboard (Streamlit):** for extension officers and the administrator. The four tools, a consolidated downloadable advisory, the SMS console, and user and catalogue administration.
* **WhatsApp:** a farmer-facing chat, in Kinyarwanda and English, that answers short questions about price, risk, disease, and fertilizer. Live through Twilio and a small FastAPI webhook (`webhook/app.py`) hosted on Render.
* **SMS:** short price and seasonal-risk alerts for any basic phone, with no internet or data cost. Sent from the officer's **Farmer Alerts** console over Africa's Talking. It is dry-run-safe by default, so nothing is sent without credentials, and farmers opt in or out with a single keyword (`YEGO` or `STOP`).
* **USSD Preview:** a `*384#`-style menu simulator for feature phones, drawing on the same data and advice as the chat.
* **In-app chat:** the same assistant, embedded in the dashboard for officers, and opened full-screen as the farmer's home.

## What powers the advice

Two of the four modules are trained machine-learning models; the other two are rule engines, and that split is deliberate. Learning is used where history teaches a signal (crop prices and price-spike risk). Rules are used where authoritative agronomy already exists (FAO disease thresholds and MINAGRI fertilizer rates), because a model would only be guessing at something already known.

The price forecaster was not chosen on faith. It was benchmarked against **ARIMA, Prophet, LSTM, a multi-layer perceptron, Random Forest, and XGBoost** in the notebook, and gradient boosting generalised best on the short monthly series, so that is what ships. The system runs on one database (SQLite for local development, PostgreSQL in production) and one keyless live weather API (Open-Meteo) driving the real-time disease alerts. Every model trains on public data: WFP prices, NISR food inflation, World Bank fertilizer costs, CHIRPS rainfall, and MINAGRI input prices, with eSoko farmgate prices as a real-price reference.

## Architecture: one source of truth

Every channel flows through the same two functions, so all of them always agree.

```
 Channels   Dashboard, in-app chat, WhatsApp, SMS, USSD
                |
                v   (all call the same functions)
 Engine     answer()  and  price_outlook()
                |
                v
 Modules    Price (ML), Risk (ML), Disease (rules), Inputs (rules)
                |
                v
 Data       real public datasets  +  trained models (models_store/*.pkl)
```

Machine learning where outcomes are learnable from history (price and price-spike risk). Rules where authoritative agronomy already exists (FAO disease thresholds and MINAGRI/RAB fertilizer rates).

## Live demo

* Landing page: https://elyse003.github.io/AgriRisk_Initial-software-product/
* Dashboard (the app): https://agririskinitial-software-appuct-nedmfzzrbgaz7jhb3c74jd.streamlit.app
* WhatsApp webhook (health check): https://agririsk-webhook.onrender.com/

The landing page's "Open the dashboard" buttons link to the live Streamlit app. The homepage is published from `landing/` by a GitHub Actions workflow, the app runs on Streamlit Community Cloud, and the WhatsApp webhook runs on Render.

## Repository

https://github.com/elyse003/AgriRisk_Initial-software-product.git

## Getting started

Requires Python 3.10 or newer.

```bash
git clone https://github.com/elyse003/AgriRisk_Initial-software-product.git
cd AgriRisk_Initial-software-product

python -m venv venv
venv\Scripts\activate                 # Windows. macOS or Linux: source venv/bin/activate

pip install -r requirements.txt
python scripts/init_db.py             # create and seed the local database
streamlit run dashboard/Home.py
```

The dashboard opens at http://localhost:8501.

To run the WhatsApp and SMS webhook locally:

```bash
pip install -r webhook/requirements.txt
uvicorn webhook.app:app --reload      # POST /whatsapp and /sms return TwiML
```

### Rebuilding the data and models from scratch

The models ship pre-trained in `models_store/`. To rebuild everything from the real public sources:

```bash
pip install openpyxl xlrd                 # for the Excel sources
python scripts/download_data.py           # fetch WFP, rainfall, fertilizer, CPI into data/raw/
python scripts/prepare_data.py            # clean into data/processed/
python scripts/train_models.py            # train and serialize into models_store/
```

`download_data.py` pulls WFP prices and CHIRPS rainfall from HDX, the fertilizer index from the World Bank Pink Sheet, and Rwanda CPI from the World Bank API. All of it is open and free, no account needed. MINAGRI input prices are extracted by hand from PDF bulletins. The deep-learning comparison in the notebook also needs `prophet`, `statsmodels`, and `tensorflow`, which install most easily in Google Colab (see `requirements-research.txt`).

## Accounts and roles

The public landing page is open; the dashboard requires sign-in. Access is role-based. **super_admin** and **officer** get the full toolset, while **farmer** gets a chat-only home (the same advice reaches farmers by SMS and WhatsApp). New sign-ups accept a **Privacy Policy** and default to the farmer role. Passwords are stored as salted PBKDF2 hashes. Demo accounts, created by `scripts/init_db.py`:

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `admin123` | super_admin |
| `musanze` | `officer123` | officer |
| `jean` | `farmer123` | farmer |

Sign-in is session-based, carried across page reloads by a short signed URL token. **Settings** holds a light or dark theme toggle and account details. The **Ururimi / Language** switch (English or Kinyarwanda) sits in the sidebar on every page and translates the entire interface.

## Using the app

The dashboard hub links to each tool, also reachable from the sidebar.

**Console (officers and admin)**

* **Price Forecast:** next-month price for a crop and district, with a history-range filter, a **National average** option, and a "compare all districts" view. Downloads a per-crop advisory summary.
* **Seasonal Risk:** a district and season risk rating with its contributing factors, plus a "risk across all districts" national view.
* **Disease Alert:** crop disease risks for a district from the live 14-day forecast, with a 7-day or 14-day window.
* **Input Recommender:** a fertilizer plan sized to the land and budget, adjusted for the district's soil (lime by pH, N-P-K by fertility class).
* **Advisory Summary:** generates one consolidated advisory for a district (risk, prices, disease, and input plan) that the officer previews and downloads.

**Channels**

* **USSD Preview:** a `*384#` menu simulator.
* **Farmer Alerts:** the SMS console. Enroll subscribers, then preview and send the weekly price and risk alert, all dry-run-safe.

**Admin (super_admin)**

* **User Management:** add, edit, and remove accounts and roles.
* **Input Catalogue:** edit the fertilizer price catalogue the recommender uses. Changes save to the database and apply immediately.

Farmers land straight in the assistant, and reach the same advice by SMS, WhatsApp, and USSD.

## Screens

Interface screenshots live in `docs/screenshots/`.

![Home](docs/screenshots/home.png)
![Price Forecast](docs/screenshots/price_forecast.png)
![Seasonal Risk](docs/screenshots/seasonal_risk.png)
![Disease Alert](docs/screenshots/disease_alert.png)
![Input Recommender](docs/screenshots/input_recommender.png)
![Advisory Summary](docs/screenshots/advisory_summary.png)
![Farmer chat](docs/screenshots/whatsapp_preview.png)

Figma mockup: [AgriRisk on Figma](https://www.figma.com/design/xojszh9Hb3OfHGNwGK8eNG/AgriRisk?node-id=3-2&t=hLKZUy3iGXhZkMXo-0)

## Data sources

Every model trains on public data. Each source, its key fields, and the module it feeds:

| Dataset | Source | Key fields | Used for |
| --- | --- | --- | --- |
| Crop market prices | WFP (HDX) | date, district, commodity, pricetype, price RWF | Price forecasting (target) |
| Food consumer price index | NISR | date, food CPI (base 2014) | Price regressor and risk feature |
| Fertilizer price index | World Bank Pink Sheet | date, fertilizer index | Price regressor and risk feature |
| District rainfall | CHIRPS (HDX) | date, district, rainfall vs normal | Seasonal-risk climate feature |
| District agro profiles | RAB / MINAGRI AEZ | altitude, soil group, fertility, pH, drainage | Risk feature and district-specific inputs |
| Weather forecast | Open-Meteo (live API) | temperature, humidity, precipitation | Disease alerts |
| Input prices | MINAGRI / Smart Nkunganire | input, type, crop, subsidised and market price | Input recommender |
| Farmgate prices | eSoko Rwanda | date, market, district, farmgate, wholesale, retail price | Farmgate reference and validation |

Prices are expressed in farmgate terms (the price a farmer is actually paid). The processing and feature steps for each source live in `scripts/prepare_data.py`, and the dashboard shows how current the data is.

## The models

Two models ship in the app, both trained on real data by `scripts/train_models.py` and serialized to `models_store/`. Reported numbers are measured on a hold-out the model never trained on (temporal for price, stratified for risk), and are also written to `models_store/metrics.json`.

### Price forecasting (Module 1)

The deployed forecaster is a gradient-boosted regression, one model per crop, pooled across all districts. It predicts the next-month log return, which is scale-free, so one model works across districts at very different price levels, and then reconstructs the price. WFP prices are monthly, so the horizon is the next month, roughly four weeks. The engineered features are lagged log-returns (1, 2, 3, 6, and 12 months), deviation from a 3-month mean, year-on-year trend, and a cyclical month encoding.

| Crop | Hold-out MAPE |
| --- | --- |
| Maize | 10.4% |
| Beans | 10.9% |
| Potatoes | 9.2% |

The average is 10.2% MAPE, comfortably under the 15% target. Monthly commodity prices sit close to a random walk, so an honest model edges out a naive last-value baseline rather than crushing it. The ARIMA, Prophet, LSTM, and MLP comparison lives in `notebooks/AgriRisk_Rwanda_Models.ipynb`; those libraries are awkward to deploy, so the scikit-learn model ships.

### Seasonal risk (Module 2)

Risk is a genuine, data-derived prediction. For each district-month the label is the realized six-month-ahead change in local staple prices, split into High, Medium, and Low terciles. The gradient-boosting classifier learns whether pre-season conditions (the season's rainfall anomaly, food-price inflation, fertilizer-cost momentum, and the district's soil and terrain) predict that coming price stress.

| Metric | Value |
| --- | --- |
| Accuracy | about 66% |
| Macro F1 | about 0.67 |
| Majority-class baseline | 33% |

That is roughly twice chance on three balanced classes. It deliberately replaces an earlier version whose labels came from a hand-written rule, which let the classifier reproduce its own rule and post a meaningless 100%. About 66% is lower but real: predicting food-price stress from pre-season signals is a hard problem, and this figure is honest about it.

### Disease (Module 3) and Inputs (Module 4)

Both are rule-based by design. Disease alerts apply FAO-style climate thresholds (temperature, humidity, and wet days) to Open-Meteo's live 14-day forecast. The input planner sizes MINAGRI and RAB per-hectare rates to the farmer's land and budget, adds lime by soil pH, and scales N-P-K by the district's soil-fertility class. That is authoritative agronomy, and it needs no training data.

## Database

The database layer (`src/db/connection.py`) runs on PostgreSQL in production and SQLite locally, through one SQLAlchemy engine (`src/db/schema.sql`). The tables are `users`, `price_records`, `risk_scores`, `input_catalogue`, `feedback`, `subscribers`, and `bot_sessions` (per-farmer conversation memory).

* **Local (default):** no setup. With no `DATABASE_URL`, it uses a SQLite file at `data/agririsk.db`, created and seeded by `python scripts/init_db.py`.
* **PostgreSQL:** set `DATABASE_URL` (an environment variable or a Streamlit secret) to a Postgres connection string, and the same code uses Postgres. Tables are created on first run and seeded by `init_db()`.

```bash
# local Postgres via Docker (docker-compose.yml runs Postgres 15 plus the app)
docker compose up

# or point at any Postgres (for example a free Neon, Supabase, or Render database)
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DBNAME"
python scripts/init_db.py
```

On Streamlit Community Cloud, add `DATABASE_URL` under Settings, then Secrets, to use a hosted Postgres. Without it, the app falls back to an ephemeral SQLite file.

## Deployment

* **Dashboard:** Streamlit Community Cloud, auto-deployed from `main` (entry `dashboard/Home.py`).
* **WhatsApp and SMS webhook:** a Render free web service (`render.yaml`, entry `webhook/app.py`). Point the Twilio WhatsApp sandbox's "When a message comes in" at `https://<service>.onrender.com/whatsapp`.
* **Landing page:** GitHub Pages, published from `landing/` by `.github/workflows/pages.yml`.
* **Farmer channels:** WhatsApp through Twilio, SMS through Africa's Talking (sandbox tested; live delivery needs account credit and an approved Rwanda sender ID).
* **Data refresh:** `.github/workflows/refresh-data.yml` runs monthly. It re-downloads the public sources, rebuilds `data/processed/`, retrains the models, and commits the refreshed artifacts so the deployed app stays current. It can also be triggered by hand.

## Project structure

```
dashboard/     Streamlit app: Home.py (landing) and pages/ (tools, channels, admin)
  _ui.py         shared theme, sidebar nav, cached loaders, SVG charts
  _auth.py       session auth, roles, privacy policy
  _i18n.py       English and Kinyarwanda translation
webhook/       FastAPI webhook for Twilio WhatsApp and SMS (hosted on Render)
src/
  models/        price forecasting, risk classifier, disease alert, input recommender
  channels/      whatsapp_bot (answer, converse), sms_alerts, sms_gateway, ussd_menu
  data/          preprocessing helpers
  db/            SQLAlchemy connection and schema
scripts/       download, prepare, train, the RQ ablations, SHAP, feedback export
notebooks/     AgriRisk_Rwanda_Models.ipynb: model comparison, research questions, SHAP
data/          raw and processed datasets, local SQLite database
models_store/  trained models, metrics.json, RQ and SHAP outputs
config/        settings (crops, districts, thresholds) and district agro profiles
landing/       static landing page (GitHub Pages)
tests/         system tests
```

Run the system tests with `pip install pytest`, then `pytest tests/test_system.py -v`.

## Video demo

[Watch the demo](https://youtu.be/5BUKRpP0X9A)

## Tech stack

Python, Streamlit, FastAPI, scikit-learn, pandas, NumPy, SQLAlchemy, PostgreSQL and SQLite, Twilio (WhatsApp), Africa's Talking (SMS), and Open-Meteo (weather). The research notebook adds Prophet, statsmodels, TensorFlow, and XGBoost.