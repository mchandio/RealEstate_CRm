-- ============================================================
-- QT_CRM Complete SQLite Schema
-- Generated from qt_crm_app.py (all core tables)
-- ============================================================
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;

-- ──────────────────────────────────────────────────────────
-- SYSTEM TABLES
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    full_name     TEXT,
    email         TEXT,
    role          TEXT DEFAULT 'viewer',
    is_active     INTEGER DEFAULT 1,
    last_login    TEXT,
    created_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- ──────────────────────────────────────────────────────────
-- CLIENTS & CONTACTS
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clients (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    contact    TEXT,
    email      TEXT,
    address    TEXT,
    notes      TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS broker_contacts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    contact        TEXT,
    area           TEXT,
    office_address TEXT,
    home_address   TEXT,
    remarks        TEXT,
    created_at     TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_broker_contacts_area ON broker_contacts(area);

-- ──────────────────────────────────────────────────────────
-- PROPERTIES
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS properties (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT,
    owner_name       TEXT,
    owner_phone      TEXT,
    contact_phone    TEXT,
    property_type    TEXT,
    size             TEXT,
    measurement_unit TEXT,
    floor            TEXT,
    location         TEXT,
    facilities       TEXT,
    remarks          TEXT,
    created_at       TEXT DEFAULT (datetime('now','localtime'))
);

-- ──────────────────────────────────────────────────────────
-- RENT MODULE
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rent_requirements (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    date             TEXT,
    client_name      TEXT,
    client_status    TEXT DEFAULT 'Client',
    contact          TEXT,
    contact_phone    TEXT,
    property_requires TEXT,
    size             TEXT,
    measurement      TEXT,
    measurement_unit TEXT DEFAULT 'Sq Ft',
    budget           REAL DEFAULT 0,
    floor            TEXT,
    location         TEXT,
    facilities       TEXT,
    remarks          TEXT,
    created_by       TEXT,
    created_at       TEXT DEFAULT (datetime('now','localtime')),
    is_deleted       INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_rr_location ON rent_requirements(location);
CREATE INDEX IF NOT EXISTS idx_rr_deleted  ON rent_requirements(is_deleted);

CREATE TABLE IF NOT EXISTS rent_availability (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT,
    owner_name          TEXT,
    client_broker       TEXT DEFAULT 'Owner',
    contact             TEXT,
    owner_phone         TEXT,
    contact_phone       TEXT,
    property_availability TEXT,
    size                TEXT,
    measurement         TEXT,
    measurement_unit    TEXT DEFAULT 'Sq Ft',
    monthly_rent        REAL DEFAULT 0,
    deposit             REAL DEFAULT 0,
    maintenance_charge  REAL DEFAULT 0,
    floor               TEXT,
    location            TEXT,
    facilities          TEXT,
    status              TEXT DEFAULT 'Available',
    remarks             TEXT,
    created_by          TEXT,
    created_at          TEXT DEFAULT (datetime('now','localtime')),
    is_deleted          INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ra_location ON rent_availability(location);
CREATE INDEX IF NOT EXISTS idx_ra_status   ON rent_availability(status);

CREATE TABLE IF NOT EXISTS rented_properties (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    date             TEXT,
    tenant_name      TEXT,
    owner_name       TEXT,
    property_type    TEXT,
    location         TEXT,
    monthly_rent     REAL DEFAULT 0,
    deal_value       REAL DEFAULT 0,
    commission_amount REAL DEFAULT 0,
    remarks          TEXT,
    created_by       TEXT,
    created_at       TEXT DEFAULT (datetime('now','localtime'))
);

-- ──────────────────────────────────────────────────────────
-- SALE MODULE
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sale_requirements (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT,
    client_name         TEXT,
    client_status       TEXT DEFAULT 'Client',
    contact             TEXT,
    contact_phone       TEXT,
    property_requires   TEXT,
    size                TEXT,
    measurement         TEXT,
    measurement_unit    TEXT DEFAULT 'Sq Ft',
    budget              REAL DEFAULT 0,
    floor               TEXT,
    location            TEXT,
    facilities          TEXT,
    verification_status TEXT DEFAULT 'Unverified',
    remarks             TEXT,
    created_by          TEXT,
    created_at          TEXT DEFAULT (datetime('now','localtime')),
    is_deleted          INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sale_availability (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT,
    owner_name          TEXT,
    client_broker       TEXT DEFAULT 'Owner',
    contact             TEXT,
    owner_phone         TEXT,
    contact_phone       TEXT,
    property_availability TEXT,
    size                TEXT,
    measurement         TEXT,
    measurement_unit    TEXT DEFAULT 'Sq Ft',
    demand              REAL DEFAULT 0,
    maintenance_charge  REAL DEFAULT 0,
    floor               TEXT,
    location            TEXT,
    facilities          TEXT,
    status              TEXT DEFAULT 'Available',
    verification_status TEXT DEFAULT 'Unverified',
    remarks             TEXT,
    created_by          TEXT,
    created_at          TEXT DEFAULT (datetime('now','localtime')),
    is_deleted          INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sold_properties (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    date             TEXT,
    buyer_name       TEXT,
    seller_name      TEXT,
    property_type    TEXT,
    location         TEXT,
    sale_price       REAL DEFAULT 0,
    commission_amount REAL DEFAULT 0,
    remarks          TEXT,
    created_by       TEXT,
    created_at       TEXT DEFAULT (datetime('now','localtime'))
);

-- ──────────────────────────────────────────────────────────
-- FINANCIAL MODULE
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS income_transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT,
    description TEXT,
    amount      REAL DEFAULT 0,
    category    TEXT,
    created_by  TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS expense_transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT,
    description TEXT,
    amount      REAL DEFAULT 0,
    category    TEXT,
    created_by  TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- ──────────────────────────────────────────────────────────
-- HR / EMPLOYEES MODULE
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employees (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    designation    TEXT,
    department     TEXT,
    contact        TEXT,
    email          TEXT,
    cnic           TEXT,
    address        TEXT,
    base_salary    REAL DEFAULT 0,
    join_date      TEXT,
    reports_to     TEXT,
    is_active      INTEGER DEFAULT 1,
    notes          TEXT,
    created_at     TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS attendance (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id      INTEGER REFERENCES employees(id),
    date             TEXT,
    check_in         TEXT,
    check_out        TEXT,
    shift_name       TEXT,
    scheduled_start  TEXT,
    scheduled_end    TEXT,
    status           TEXT,
    leave_type       TEXT,
    worked_minutes   INTEGER DEFAULT 0,
    late_minutes     INTEGER DEFAULT 0,
    overtime_minutes INTEGER DEFAULT 0,
    last_edited_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_att_emp_date ON attendance(employee_id, date);

CREATE TABLE IF NOT EXISTS salary_payments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id    INTEGER REFERENCES employees(id),
    payment_date   TEXT,
    month          TEXT,
    year           TEXT,
    base_salary    REAL DEFAULT 0,
    bonus          REAL DEFAULT 0,
    deductions     REAL DEFAULT 0,
    net_salary     REAL DEFAULT 0,
    payment_method TEXT,
    notes          TEXT,
    created_at     TEXT DEFAULT (datetime('now','localtime'))
);

-- ──────────────────────────────────────────────────────────
-- USEFUL VIEWS (for LibreOffice Base queries / reports)
-- ──────────────────────────────────────────────────────────
CREATE VIEW IF NOT EXISTS v_active_rent_requirements AS
SELECT * FROM rent_requirements WHERE is_deleted=0;

CREATE VIEW IF NOT EXISTS v_active_rent_availability AS
SELECT * FROM rent_availability WHERE is_deleted=0 AND status='Available';

CREATE VIEW IF NOT EXISTS v_active_sale_requirements AS
SELECT * FROM sale_requirements WHERE is_deleted=0;

CREATE VIEW IF NOT EXISTS v_active_sale_availability AS
SELECT * FROM sale_availability WHERE is_deleted=0 AND status='Available';

CREATE VIEW IF NOT EXISTS v_financial_summary AS
SELECT
    (SELECT COALESCE(SUM(amount),0) FROM income_transactions)  AS total_income,
    (SELECT COALESCE(SUM(amount),0) FROM expense_transactions) AS total_expense,
    (SELECT COALESCE(SUM(amount),0) FROM income_transactions)
      - (SELECT COALESCE(SUM(amount),0) FROM expense_transactions) AS net_profit;

CREATE VIEW IF NOT EXISTS v_employee_salary_summary AS
SELECT
    e.id,
    e.name,
    e.designation,
    e.base_salary,
    COUNT(s.id) AS payments_made,
    COALESCE(SUM(s.net_salary),0) AS total_paid
FROM employees e
LEFT JOIN salary_payments s ON s.employee_id=e.id
WHERE e.is_active=1
GROUP BY e.id;
