# Data sources

Download each source into `data/raw/` using the filename in the **Save as** column.
All sources are open and free. The preprocessing pipeline (`src/data/preprocessing.py`)
expects these exact names.

| Save as | Source | Link | Period | Module |
|---------|--------|------|--------|--------|
| `wfp_food_prices_rwanda.csv` | WFP / HDX food prices | data.humdata.org/dataset/wfp-food-prices-for-rwanda | 2000–2025 | 1 |
| `rwanda_food_cpi.csv` | FRED food inflation | fred.stlouisfed.org/series/FPCPITOTLZGRWA | 2010–2024 | 1 & 2 |
| `district_rainfall_anomalies.csv` | HDX rainfall indicators | data.humdata.org/dataset/rainfall-indicators-rwanda | 2000–2024 | 2 |
| `fertilizer_price_index.csv` | World Bank Pink Sheet | worldbank.org/en/research/commodity-markets | 2015–2024 | 1 & 2 |
| `minagri_input_prices.csv` | MINAGRI bulletins (manual extract) | minagri.gov.rw | 2020–2024 | 4 |

Module 3 (disease) needs no stored file — it calls the Open-Meteo API live at query time.

## Notes
- The MINAGRI bulletins are PDFs; extract them once by hand into a CSV with columns:
  `input_name, input_type, crop_suitability, supplier, district, price_rwf, quarter`.
- Keep raw files unedited. All cleaning happens in the preprocessing step and writes
  to `data/processed/`.
