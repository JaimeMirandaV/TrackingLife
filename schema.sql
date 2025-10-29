-- SQLite schema for daily life tracker
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY,
    area TEXT NOT NULL CHECK(area IN ('finanzas','deporte','salud')),
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('acumulativo','promedio','habito')),
    target_value REAL,
    unit TEXT,
    period TEXT NOT NULL CHECK(period IN ('corto','mediano','largo')),
    start_date TEXT NOT NULL,
    end_date TEXT,
    direction TEXT NOT NULL CHECK(direction IN ('>=','<=','==')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS health_daily (
    date TEXT PRIMARY KEY,
    weight_kg REAL,
    sleep_hours REAL,
    steps INTEGER,
    resting_hr INTEGER,
    water_l REAL,
    calories_in REAL,
    calories_out REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS sport_daily (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    activity TEXT NOT NULL,
    duration_min REAL,
    distance_km REAL,
    calories REAL,
    rpe INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS finance_tx (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    account TEXT,
    category TEXT,
    subcategory TEXT,
    description TEXT,
    amount REAL NOT NULL, -- positive for income, negative for expense
    method TEXT CHECK(method IN ('efectivo','transferencia','debito','credito','otro')),
    tags TEXT
);

CREATE VIEW IF NOT EXISTS v_sport_by_day AS
SELECT date,
       SUM(duration_min) AS total_min,
       SUM(distance_km) AS total_km,
       SUM(calories) AS total_cal
FROM sport_daily
GROUP BY date;

