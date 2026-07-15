-- Simplified SQLite schema extracted from qt_crm_app.py

PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT,
    full_name TEXT,
    email TEXT,
    role TEXT,
    is_active INTEGER DEFAULT 1,
    last_login TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS broker_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    contact TEXT,
    area TEXT,
    office_address TEXT,
    home_address TEXT,
    remarks TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_broker_contacts_area ON broker_contacts(area);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    contact TEXT,
    email TEXT,
    address TEXT,
    notes TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    owner_name TEXT,
    owner_phone TEXT,
    contact_phone TEXT,
    property_type TEXT,
    size TEXT,
    measurement_unit TEXT,
    floor TEXT,
    location TEXT,
    facilities TEXT,
    remarks TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS rent_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    client_name TEXT,
    client_status TEXT,
    contact TEXT,
    contact_phone TEXT,
    property_requires TEXT,
    size TEXT,
    measurement TEXT,
    measurement_unit TEXT,
    budget REAL DEFAULT 0,
    floor TEXT,
    location TEXT,
    facilities TEXT,
    remarks TEXT,
    created_by TEXT,
    created_at TEXT,
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rent_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    owner_name TEXT,
    client_broker TEXT,
    contact TEXT,
    owner_phone TEXT,
    contact_phone TEXT,
    property_availability TEXT,
    size TEXT,
    measurement TEXT,
    measurement_unit TEXT,
    monthly_rent REAL DEFAULT 0,
    deposit REAL DEFAULT 0,
    maintenance_charge REAL DEFAULT 0,
    floor TEXT,
    location TEXT,
    facilities TEXT,
    status TEXT DEFAULT 'Available',
    remarks TEXT,
    created_by TEXT,
    created_at TEXT,
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sale_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    client_name TEXT,
    client_status TEXT,
    contact TEXT,
    contact_phone TEXT,
    property_requires TEXT,
    size TEXT,
    measurement TEXT,
    measurement_unit TEXT,
    budget REAL DEFAULT 0,
    floor TEXT,
    location TEXT,
    facilities TEXT,
    verification_status TEXT DEFAULT 'Unverified',
    remarks TEXT,
    created_by TEXT,
    created_at TEXT,
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sale_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    owner_name TEXT,
    client_broker TEXT,
    contact TEXT,
    owner_phone TEXT,
    contact_phone TEXT,
    property_availability TEXT,
    size TEXT,
    measurement TEXT,
    measurement_unit TEXT,
    demand REAL DEFAULT 0,
    maintenance_charge REAL DEFAULT 0,
    floor TEXT,
    location TEXT,
    facilities TEXT,
    status TEXT DEFAULT 'Available',
    verification_status TEXT DEFAULT 'Unverified',
    remarks TEXT,
    created_by TEXT,
    created_at TEXT,
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS income_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    description TEXT,
    amount REAL DEFAULT 0,
    category TEXT,
    created_by TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS expense_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    description TEXT,
    amount REAL DEFAULT 0,
    category TEXT,
    created_by TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    date TEXT,
    check_in TEXT,
    check_out TEXT,
    shift_name TEXT,
    scheduled_start TEXT,
    scheduled_end TEXT,
    status TEXT,
    leave_type TEXT,
    worked_minutes INTEGER DEFAULT 0,
    late_minutes INTEGER DEFAULT 0,
    overtime_minutes INTEGER DEFAULT 0,
    last_edited_at TEXT
);

CREATE TABLE IF NOT EXISTS salary_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    payment_date TEXT,
    month TEXT,
    year TEXT,
    base_salary REAL DEFAULT 0,
    bonus REAL DEFAULT 0,
    deductions REAL DEFAULT 0,
    net_salary REAL DEFAULT 0,
    payment_method TEXT,
    notes TEXT,
    created_at TEXT
);

-- End of schema
