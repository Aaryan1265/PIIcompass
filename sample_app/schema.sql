-- ============================================================================
-- SYNTHETIC SAMPLE SCHEMA (NOT A REAL SYSTEM, NO REAL PERSONAL DATA)
-- ============================================================================
-- This is the fictional "MapleHealth" patient portal used only as a scan
-- target for PIICompass. Every table and column here is invented. No real
-- individual, clinic or payment processor is described. Column names are
-- deliberately realistic so the scanner has meaningful work to do, including a
-- few tricky cases (a free-text notes column, a reference-data city table).
-- ============================================================================

CREATE TABLE cities (
    city_id     INTEGER PRIMARY KEY,   -- surrogate key, not personal
    city_name   TEXT NOT NULL,         -- reference data (a place, not a person)
    population  INTEGER                 -- reference data
);

CREATE TABLE patients (
    patient_id            INTEGER PRIMARY KEY,   -- surrogate key
    first_name            TEXT NOT NULL,
    last_name             TEXT NOT NULL,
    date_of_birth         DATE,
    national_insurance_no TEXT,                  -- government identifier
    email                 TEXT,
    phone                 TEXT,
    address_line1         TEXT,
    postal_code           TEXT,
    notes                 TEXT,                  -- free text, may embed PII
    city_id               INTEGER REFERENCES cities(city_id),
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE contacts (
    contact_id     INTEGER PRIMARY KEY,
    patient_id     INTEGER REFERENCES patients(patient_id),
    contact_name   TEXT NOT NULL,   -- third-party (emergency contact) name
    contact_phone  TEXT,
    contact_type   TEXT,            -- enum: 'home' | 'work' (not personal)
    relationship   TEXT             -- e.g. 'spouse' (not identifying alone)
);

CREATE TABLE payments (
    payment_id   INTEGER PRIMARY KEY,
    patient_id   INTEGER REFERENCES patients(patient_id),
    card_number  TEXT,             -- payment instrument
    card_expiry  TEXT,
    amount_cents INTEGER,
    currency     TEXT
);

CREATE TABLE health_records (
    record_id      INTEGER PRIMARY KEY,
    patient_id     INTEGER REFERENCES patients(patient_id),
    diagnosis_code TEXT,           -- Article 9 special-category health data
    blood_type     TEXT,           -- Article 9 special-category health data
    consent_flag   BOOLEAN DEFAULT 0
);

CREATE TABLE appointments (
    appointment_id INTEGER PRIMARY KEY,
    patient_id     INTEGER REFERENCES patients(patient_id),
    scheduled_for  TIMESTAMP,
    clinician_name TEXT            -- staff name is still personal data
);

CREATE TABLE analytics_events (
    event_id    INTEGER PRIMARY KEY,
    ip_address  TEXT,
    user_agent  TEXT,
    device_id   TEXT,
    session_id  TEXT,
    geo_region  TEXT,              -- coarse region (review: reference-grade?)
    page_url    TEXT
);

CREATE TABLE audit_log (
    log_id      INTEGER PRIMARY KEY,
    actor_email TEXT,              -- staff email of the person who acted
    action      TEXT,
    payload     TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
