-- AgriRisk Rwanda — database schema (six tables, matching the proposal ERD)

CREATE TABLE IF NOT EXISTS users (
    user_id     SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    role        VARCHAR(40)  NOT NULL,        -- 'farmer' | 'officer' | 'super_admin'
    district    VARCHAR(60),
    phone       VARCHAR(20) UNIQUE,
    language    VARCHAR(5) DEFAULT 'rw'
);

CREATE TABLE IF NOT EXISTS price_records (
    record_id   SERIAL PRIMARY KEY,
    crop        VARCHAR(40)  NOT NULL,
    market      VARCHAR(80)  NOT NULL,
    record_date DATE         NOT NULL,
    price_rwf   NUMERIC(10,2) NOT NULL,
    UNIQUE (crop, market, record_date)        -- one price per crop/market/date
);

CREATE TABLE IF NOT EXISTS risk_scores (
    score_id          SERIAL PRIMARY KEY,
    district          VARCHAR(60) NOT NULL,
    season            VARCHAR(20),             -- 'A' (Mar-May) | 'B' (Oct-Dec)
    rainfall_anomaly  NUMERIC(6,3),            -- std-devs from long-term mean
    cpi_change        NUMERIC(6,3),            -- food CPI YoY %
    fertilizer_change NUMERIC(6,3),            -- global fertilizer index YoY %
    risk_level        VARCHAR(10),             -- 'High' | 'Medium' | 'Low'
    scored_at         TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS input_catalogue (
    input_id        SERIAL PRIMARY KEY,
    input_name      VARCHAR(120) NOT NULL,
    input_type      VARCHAR(40),              -- 'seed' | 'fertilizer' | 'pesticide'
    crop_suitability VARCHAR(120),            -- comma-separated crops
    supplier        VARCHAR(120),
    district        VARCHAR(60),
    price_rwf       NUMERIC(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id        SERIAL PRIMARY KEY,
    user_id            INTEGER REFERENCES users(user_id),
    module_name        VARCHAR(40),            -- which of the 4 modules
    satisfaction_rating INTEGER CHECK (satisfaction_rating BETWEEN 1 AND 5),
    submitted_at       TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS subscribers (
    subscriber_id SERIAL PRIMARY KEY,
    phone_number  VARCHAR(20) UNIQUE NOT NULL,
    district      VARCHAR(60),
    crops         VARCHAR(120),               -- comma-separated
    language      VARCHAR(5) DEFAULT 'rw'     -- 'rw' | 'en'
);
