# AgriRisk Rwanda — Demo Script (ML Track)

Target length: 6 to 8 minutes. Lead with the notebook (the machine learning), then show the app as the deployed result. This matches how the ML track is assessed and answers what Kevin asked to review: code, ML artifacts, and dataset columns.

---

## 0. Open (20 sec)
"This is AgriRisk Rwanda, a machine-learning advisory platform for smallholder farmers. It covers four decisions across the farming season, for maize, beans, and Irish potatoes, in all 30 districts. I'll start with the modelling notebook, then show the working app."

## 1. The data and the problem (1 min) — notebook
Open `notebooks/AgriRisk_Rwanda_Models.ipynb`.
- Show the six datasets and where each comes from (WFP prices, NISR inflation, World Bank fertilizer, CHIRPS rainfall, Open-Meteo weather, MINAGRI inputs).
- Point at the dataset columns as you scroll, since this is what the review asked for.
- "Prices are the forecast target. Inflation and fertilizer cost are both regressors for price and features for risk. Rainfall is the climate feature. Weather drives disease alerts."

## 2. Data engineering and visualization (1 min) — notebook
- Scroll the exploration figures: price trends, distributions, correlations.
- "This is the cleaning and feature engineering: lag features for price, the rainfall anomaly per district, year-on-year change for inflation and fertilizer."

## 3. Model architecture (1.5 min) — notebook
- Risk classifier: random forest vs XGBoost, the three input features.
- Price forecasting: ARIMA, Prophet, the LSTM (show the layers, activation, optimizer), and the random-forest baseline.
- Show the **training loss curve** dropping over the epochs.
- Be honest and confident: "The risk labels come from an expert rule over the three features, so the classifier reproduces that rule and scores near 100%. The real predictive result is the price forecast."

## 4. Performance metrics (1 min) — notebook
- Price: LSTM 4.35% MAPE, ahead of Prophet 6.89%, ARIMA 8.76%, baseline 12.13%, all under the 15% target.
- Risk: show the precision / recall / F1 chart.
- "Lower MAPE is better, so 4.35% is a strong forecast."

## 5. The deployed app (2 min) — Streamlit
Run `streamlit run dashboard/Home.py`.
- **Home**: coverage, alerts, channels, and the data-current-through line.
- **Price Forecast**: pick a crop and district, show the 4-week forecast and the recommendation. Mention every district returns a result, falling back to the national average when a district's own data is old.
- **Seasonal Risk**: pick a district and season (Season A short rains, Season B long rains), show the rating and the contributing factors.
- **Disease Alert**: live weather driving a real-time alert.
- **Input Recommender**: enter land size, show the fertilizer plan in bags and cost against the budget.
- **WhatsApp Preview**: a farmer asking a question in Kinyarwanda.

## 6. Farmer-first and what's next (40 sec)
- "The farmer is the primary user. Officers and a super-admin are supporting roles, with the database distinguishing them by role. Farmers are reached by SMS and WhatsApp in Kinyarwanda."
- Next steps: role-based views, live SMS gateway, richer contextual alerts.

## 7. Close (15 sec)
"So that's the full cycle: real Rwandan data, four trained modules with honest metrics, and a working platform that reaches farmers on a basic phone."

---

### Tips
- Have the notebook already run, with figures visible, before recording.
- Keep the app running in a second window so the switch is instant.
- If asked about accuracy: the price MAPE is the genuine ML result; the risk score is a transparent rule, stated openly.
