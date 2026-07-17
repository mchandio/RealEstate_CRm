"""Database schema initialization and migrations."""
from __future__ import annotations
import sqlite3
from datetime import datetime
from typing import Any
from crm_core import DB_PATH
from crm_core.constants import CLOSED_AVAILABILITY_ARCHIVES, FLOOR_OPTIONS, FACILITY_OPTIONS, PROPERTY_TYPE_OPTIONS, MEASUREMENT_UNIT_OPTIONS, COMMON_AREAS, EXPENSE_CATEGORIES
from CRM.utils import quote_identifier

def ensure_database() -> None:
    """Create core tables (if missing) then run Qt-schema migrations."""
    _create_core_tables()
    ensure_qt_schema()


def _create_core_tables() -> None:
    """Create the foundational tables that professional_crm.Database.init_all() used to handle."""
    import hashlib as _hashlib
    with sqlite3.connect(str(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA foreign_keys=ON")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_settings
            (key TEXT PRIMARY KEY, value TEXT)""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             username TEXT UNIQUE NOT NULL,
             password_hash TEXT NOT NULL,
             full_name TEXT, email TEXT,
             role TEXT DEFAULT 'Staff',
             is_active INTEGER DEFAULT 1,
             created_at TIMESTAMP, last_login TIMESTAMP)""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS login_logs
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id INTEGER, login_time TIMESTAMP, status TEXT)""")

        for tbl, cols in [
            ("rent_requirements",
             "date TEXT, client_name TEXT, contact TEXT, property_requires TEXT, "
             "size TEXT, measurement TEXT, budget REAL, floor TEXT, location TEXT, "
             "option1 TEXT, option2 TEXT, facilities TEXT, client_broker TEXT, "
             "bachelor_family TEXT, remarks TEXT, "
             "workflow_stage TEXT DEFAULT 'Lead', priority TEXT DEFAULT 'Medium', "
             "next_follow_up TEXT, assigned_to TEXT, last_contacted TEXT, "
             "deal_probability REAL DEFAULT 10.0, expected_close_value REAL DEFAULT 0, "
             "closed_at TIMESTAMP, lost_reason TEXT, "
             "property_type TEXT, sq_ft_yards TEXT, budget_min REAL, budget_max REAL, "
             "maintenance REAL, notes TEXT, status TEXT DEFAULT 'Open', "
             "approval_status TEXT DEFAULT 'Pending', approval_comment TEXT, "
             "approved_by TEXT, approved_at TIMESTAMP, "
             "created_by TEXT, created_at TIMESTAMP"),
            ("rent_availability",
             "date TEXT, owner_name TEXT, contact TEXT, property_availability TEXT, "
             "size TEXT, measurement TEXT, monthly_rent REAL, floor TEXT, location TEXT, "
             "deposit REAL, maintenance_charge REAL, facilities TEXT, "
             "client_broker TEXT, bachelor_family TEXT, remarks TEXT, "
             "workflow_stage TEXT DEFAULT 'Lead', priority TEXT DEFAULT 'Medium', "
             "next_follow_up TEXT, assigned_to TEXT, last_contacted TEXT, "
             "deal_probability REAL DEFAULT 10.0, expected_close_value REAL DEFAULT 0, "
             "closed_at TIMESTAMP, lost_reason TEXT, "
             "property_type TEXT, sq_ft_yards TEXT, posted_by TEXT, notes TEXT, "
             "status TEXT DEFAULT 'Available', "
             "approval_status TEXT DEFAULT 'Pending', approval_comment TEXT, "
             "approved_by TEXT, approved_at TIMESTAMP, "
             "created_by TEXT, created_at TIMESTAMP"),
            ("sale_requirements",
             "date TEXT, client_name TEXT, contact TEXT, property_requires TEXT, "
             "size TEXT, measurement TEXT, budget REAL, floor TEXT, location TEXT, "
             "option1 TEXT, option2 TEXT, facilities TEXT, client_broker TEXT, "
             "bachelor_family TEXT, remarks TEXT, "
             "workflow_stage TEXT DEFAULT 'Lead', priority TEXT DEFAULT 'Medium', "
             "next_follow_up TEXT, assigned_to TEXT, last_contacted TEXT, "
             "deal_probability REAL DEFAULT 10.0, expected_close_value REAL DEFAULT 0, "
             "closed_at TIMESTAMP, lost_reason TEXT, "
             "approval_status TEXT DEFAULT 'Pending', approval_comment TEXT, "
             "approved_by TEXT, approved_at TIMESTAMP, "
             "created_by TEXT, created_at TIMESTAMP"),
            ("sale_availability",
             "date TEXT, owner_name TEXT, contact TEXT, property_availability TEXT, "
             "size TEXT, measurement TEXT, demand REAL, floor TEXT, location TEXT, "
             "option1 TEXT, option2 TEXT, facilities TEXT, client_broker TEXT, "
             "bachelor_family TEXT, remarks TEXT, "
             "workflow_stage TEXT DEFAULT 'Lead', priority TEXT DEFAULT 'Medium', "
             "next_follow_up TEXT, assigned_to TEXT, last_contacted TEXT, "
             "deal_probability REAL DEFAULT 10.0, expected_close_value REAL DEFAULT 0, "
             "closed_at TIMESTAMP, lost_reason TEXT, "
             "approval_status TEXT DEFAULT 'Pending', approval_comment TEXT, "
             "approved_by TEXT, approved_at TIMESTAMP, "
             "created_by TEXT, created_at TIMESTAMP"),
            ("income_transactions",
             "transaction_date TEXT, income_type TEXT, amount REAL, "
             "tenant_name TEXT, description TEXT, receipt_no TEXT, "
             "payment_method TEXT DEFAULT 'Cash', "
             "created_by TEXT, created_at TIMESTAMP"),
            ("expense_transactions",
             "transaction_date TEXT, expense_category TEXT, amount REAL, "
             "vendor_name TEXT, description TEXT, invoice_no TEXT, "
             "payment_method TEXT DEFAULT 'Cash', "
             "created_by TEXT, created_at TIMESTAMP"),
            ("employees",
             "employee_id TEXT, full_name TEXT, cnic TEXT, phone TEXT, email TEXT, "
             "position TEXT, department TEXT, hire_date TEXT, base_salary REAL, "
             "commission_rate REAL DEFAULT 5.0, status TEXT DEFAULT 'Active', "
             "address TEXT, notes TEXT, created_at TIMESTAMP"),
            ("attendance",
             "employee_id INTEGER, date TEXT, check_in TEXT, check_out TEXT, "
             "status TEXT DEFAULT 'Present', notes TEXT"),
            ("salary_payments",
             "employee_id INTEGER, payment_date TEXT, month TEXT, year TEXT, "
             "base_salary REAL, bonus REAL DEFAULT 0, deductions REAL DEFAULT 0, "
             "net_salary REAL, payment_method TEXT, notes TEXT, created_at TIMESTAMP"),
            ("properties",
             "property_code TEXT, title TEXT, property_type TEXT, "
             "status TEXT DEFAULT 'Available', owner_name TEXT, owner_contact TEXT, "
             "location TEXT, area TEXT, floor TEXT, monthly_rent REAL, sale_price REAL, "
             "maintenance_charge REAL, facilities TEXT, description TEXT, "
             "created_at TIMESTAMP"),
            ("clients",
             "client_name TEXT, cnic TEXT, phone TEXT, email TEXT, "
             "address TEXT, client_type TEXT DEFAULT 'Tenant', "
             "notes TEXT, status TEXT DEFAULT 'Active', created_at TIMESTAMP"),
        ]:
            cur.execute(f"CREATE TABLE IF NOT EXISTS {tbl} (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})")

        conn.commit()

        # Seed default admin user if none exist
        cur.execute("SELECT COUNT(*) as cnt FROM users")
        if cur.fetchone()[0] == 0:
            pwd_hash = _hashlib.sha256("admin".encode()).hexdigest()
            cur.execute(
                "INSERT INTO users (username, password_hash, full_name, email, role, is_active, created_at) "
                "VALUES (?,?,?,?,?,1,?)",
                ("admin", pwd_hash, "Administrator", "admin@company.com",
                 "Super Admin", datetime.now().isoformat()),
            )
            conn.commit()

        # Seed default settings if empty
        cur.execute("SELECT COUNT(*) as cnt FROM app_settings")
        if cur.fetchone()[0] == 0:
            defaults = {
                "company_name": "Real Estate Management",
                "company_address": "Karachi, Pakistan",
                "currency": "PKR",
                "currency_symbol": "Rs.",
                "date_format": "DD/MM/YYYY",
                "phase1_theme": "Light",
            }
            for k, v in defaults.items():
                cur.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES (?,?)", (k, v))
            conn.commit()


def ensure_qt_schema() -> None:
    """Add Qt-screen columns that older deployed databases may be missing."""
    additions = {
        "rent_requirements": [
            ("client_status", "TEXT DEFAULT 'Client'"),
            ("broker", "TEXT"),
            ("contact_person", "TEXT"),
            ("contact_phone", "TEXT"),
            ("property_requires", "TEXT"),
            ("size", "TEXT"),
            ("measurement", "TEXT"),
            ("measurement_unit", "TEXT"),
            ("persons", "TEXT"),
            ("building_name", "TEXT"),
            ("is_deleted", "INTEGER DEFAULT 0"),
            ("deleted_by", "TEXT"),
            ("deleted_at", "TEXT"),
            ("last_edited_by", "TEXT"),
            ("last_edited_at", "TEXT"),
        ],
        "rent_availability": [
            ("client_broker", "TEXT"),
            ("owner_phone", "TEXT"),
            ("contact_phone", "TEXT"),
            ("property_availability", "TEXT"),
            ("size", "TEXT"),
            ("measurement", "TEXT"),
            ("measurement_unit", "TEXT"),
            ("status", "TEXT DEFAULT 'Available'"),
            ("persons", "TEXT"),
            ("building_name", "TEXT"),
            ("is_deleted", "INTEGER DEFAULT 0"),
            ("deleted_by", "TEXT"),
            ("deleted_at", "TEXT"),
            ("last_edited_by", "TEXT"),
            ("last_edited_at", "TEXT"),
        ],
        "sale_requirements": [
            ("client_status", "TEXT DEFAULT 'Client'"),
            ("broker", "TEXT"),
            ("contact_person", "TEXT"),
            ("contact_phone", "TEXT"),
            ("property_requires", "TEXT"),
            ("size", "TEXT"),
            ("measurement", "TEXT"),
            ("measurement_unit", "TEXT"),
            ("persons", "TEXT"),
            ("building_name", "TEXT"),
            ("maintenance_charge", "REAL DEFAULT 0"),
            ("is_deleted", "INTEGER DEFAULT 0"),
            ("deleted_by", "TEXT"),
            ("deleted_at", "TEXT"),
            ("last_edited_by", "TEXT"),
            ("last_edited_at", "TEXT"),
        ],
        "sale_availability": [
            ("client_broker", "TEXT"),
            ("owner_phone", "TEXT"),
            ("contact_phone", "TEXT"),
            ("property_availability", "TEXT"),
            ("size", "TEXT"),
            ("measurement", "TEXT"),
            ("measurement_unit", "TEXT"),
            ("status", "TEXT DEFAULT 'Available'"),
            ("persons", "TEXT"),
            ("building_name", "TEXT"),
            ("maintenance_charge", "REAL DEFAULT 0"),
            ("is_deleted", "INTEGER DEFAULT 0"),
            ("deleted_by", "TEXT"),
            ("deleted_at", "TEXT"),
            ("last_edited_by", "TEXT"),
            ("last_edited_at", "TEXT"),
        ],
        "attendance": [
            ("shift_name", "TEXT DEFAULT 'Office'"),
            ("scheduled_start", "TEXT DEFAULT '09:30'"),
            ("scheduled_end", "TEXT DEFAULT '18:00'"),
            ("leave_type", "TEXT"),
            ("worked_minutes", "INTEGER DEFAULT 0"),
            ("late_minutes", "INTEGER DEFAULT 0"),
            ("early_leave_minutes", "INTEGER DEFAULT 0"),
            ("overtime_minutes", "INTEGER DEFAULT 0"),
            ("approved_by", "TEXT"),
            ("last_edited_at", "TEXT"),
        ],
    }
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA wal_autocheckpoint=1000")
        cur.execute("PRAGMA synchronous=FULL")
        cur.execute("PRAGMA cache_size=5000")
        cur.execute("PRAGMA foreign_keys=ON")
        for table, columns in additions.items():
            existing = {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}
            for column, column_type in columns:
                if column not in existing:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                    existing.add(column)
            if "is_deleted" in existing:
                cur.execute(f"UPDATE {table} SET is_deleted=0 WHERE is_deleted IS NULL")
            if table in {"rent_requirements", "sale_requirements"}:
                if "client_status" in existing:
                    cur.execute(
                        f"""UPDATE {table}
                            SET client_status=CASE
                                WHEN LOWER(client_status) IN ('o', 'owner') THEN 'Owner'
                                WHEN LOWER(client_status) IN ('b', 'broker') THEN 'Broker'
                                WHEN client_status IS NULL OR client_status='' THEN 'Client'
                            ELSE client_status
                            END"""
                    )
                if {"client_name", "contact_person"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET contact_person=client_name "
                        "WHERE (contact_person IS NULL OR contact_person='') AND client_name IS NOT NULL"
                    )
                if {"contact", "contact_phone"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET contact_phone=contact "
                        "WHERE (contact_phone IS NULL OR contact_phone='') AND contact IS NOT NULL AND contact<>''"
                    )
                    cur.execute(
                        f"UPDATE {table} SET contact=contact_phone "
                        "WHERE (contact IS NULL OR contact='') AND contact_phone IS NOT NULL AND contact_phone<>''"
                    )
                if {"budget", "budget_max"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET budget=budget_max "
                        "WHERE (budget IS NULL OR budget=0) AND budget_max IS NOT NULL AND budget_max<>0"
                    )
                if {"budget", "budget_min"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET budget=budget_min "
                        "WHERE (budget IS NULL OR budget=0) AND budget_min IS NOT NULL AND budget_min<>0"
                    )
                if {"property_requires", "property_type"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET property_requires=property_type "
                        "WHERE (property_requires IS NULL OR property_requires='') AND property_type IS NOT NULL AND property_type<>''"
                    )
                if {"property_requires", "property_requirement"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET property_requires=property_requirement "
                        "WHERE (property_requires IS NULL OR property_requires='') AND property_requirement IS NOT NULL AND property_requirement<>''"
                    )
                if "broker" in existing:
                    broker_sources = [column for column in ("preferred_broker", "client_broker") if column in existing]
                    if broker_sources:
                        fallback_values = [f"NULLIF({column}, '')" for column in broker_sources]
                        fallback = (
                            f"COALESCE({', '.join(fallback_values)})"
                            if len(fallback_values) > 1
                            else fallback_values[0]
                        )
                        cur.execute(
                            f"UPDATE {table} SET broker={fallback} "
                            "WHERE broker IS NULL OR broker=''"
                        )
            if table in {"rent_availability", "sale_availability"} and "client_broker" in existing:
                cur.execute(
                    f"""UPDATE {table}
                        SET client_broker=CASE
                            WHEN LOWER(client_broker) IN ('o', 'owner') THEN 'Owner'
                            WHEN LOWER(client_broker) IN ('b', 'broker') THEN 'Broker'
                            WHEN client_broker IS NULL OR client_broker='' THEN 'Owner'
                            ELSE client_broker
                        END"""
                )
                if {"contact", "owner_phone"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET owner_phone=contact "
                        "WHERE (owner_phone IS NULL OR owner_phone='') AND contact IS NOT NULL AND contact<>''"
                    )
                    cur.execute(
                        f"UPDATE {table} SET contact=owner_phone "
                        "WHERE (contact IS NULL OR contact='') AND owner_phone IS NOT NULL AND owner_phone<>''"
                    )
                if {"contact_phone", "owner_phone"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET contact_phone=owner_phone "
                        "WHERE (contact_phone IS NULL OR contact_phone='') AND owner_phone IS NOT NULL AND owner_phone<>''"
                    )
                    cur.execute(
                        f"UPDATE {table} SET owner_phone=contact_phone "
                        "WHERE (owner_phone IS NULL OR owner_phone='') AND contact_phone IS NOT NULL AND contact_phone<>''"
                    )
                if "status" in existing:
                    cur.execute(
                        f"""UPDATE {table}
                            SET status=CASE
                                WHEN status IS NULL OR status='' THEN 'Available'
                                WHEN LOWER(status)='available' THEN 'Available'
                                WHEN LOWER(status)='reserved' THEN 'Reserved'
                                WHEN LOWER(status)='hold' THEN 'Reserved'
                                WHEN LOWER(status)='withdrawn' THEN 'Withdrawn'
                                WHEN LOWER(status)='inactive' THEN 'Inactive'
                                WHEN LOWER(status) IN ('sold', 'sale') THEN 'Sold'
                                WHEN LOWER(status) IN ('rented', 'rent') THEN 'Rented'
                                ELSE status
                            END"""
                    )
                    if table == "rent_availability":
                        cur.execute(f"UPDATE {table} SET status='Available' WHERE status='Sold'")
                    elif table == "sale_availability":
                        cur.execute(f"UPDATE {table} SET status='Available' WHERE status='Rented'")
                if {"property_availability", "property_type"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET property_availability=property_type "
                        "WHERE (property_availability IS NULL OR property_availability='') AND property_type IS NOT NULL AND property_type<>''"
                    )
            if {"size", "size_beds"} <= existing:
                cur.execute(
                    f"UPDATE {table} SET size=size_beds "
                    "WHERE (size IS NULL OR size='') AND size_beds IS NOT NULL AND size_beds<>''"
                )
            if {"measurement", "sq_ft"} <= existing:
                cur.execute(
                    f"UPDATE {table} SET measurement=sq_ft "
                    "WHERE (measurement IS NULL OR measurement='') AND sq_ft IS NOT NULL AND sq_ft<>''"
                )
            if {"measurement", "sq_ft_yards"} <= existing:
                cur.execute(
                    f"UPDATE {table} SET measurement=sq_ft_yards "
                    "WHERE (measurement IS NULL OR measurement='') AND sq_ft_yards IS NOT NULL AND sq_ft_yards<>''"
                )
            if {"measurement_unit", "sq_ft_yards"} <= existing:
                cur.execute(
                    f"""UPDATE {table}
                        SET measurement_unit=CASE
                            WHEN LOWER(sq_ft_yards) LIKE '%yard%' OR LOWER(sq_ft_yards) LIKE '%yd%' THEN 'Yards'
                            ELSE 'Sq Ft'
                        END
                        WHERE (measurement_unit IS NULL OR measurement_unit='')
                          AND sq_ft_yards IS NOT NULL AND sq_ft_yards<>''"""
                )
            if {"measurement_unit", "sq_ft"} <= existing:
                cur.execute(
                    f"UPDATE {table} SET measurement_unit='Sq Ft' "
                    "WHERE (measurement_unit IS NULL OR measurement_unit='') AND sq_ft IS NOT NULL AND sq_ft<>''"
                )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS broker_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                contact TEXT,
                area TEXT,
                office_address TEXT,
                home_address TEXT,
                remarks TEXT,
                created_at TEXT
            )
            """
        )
        broker_existing = {row[1] for row in cur.execute("PRAGMA table_info(broker_contacts)")}
        for column, column_type in (
            ("name", "TEXT"),
            ("contact", "TEXT"),
            ("area", "TEXT"),
            ("office_address", "TEXT"),
            ("home_address", "TEXT"),
            ("remarks", "TEXT"),
            ("created_at", "TEXT"),
        ):
            if column not in broker_existing:
                cur.execute(f"ALTER TABLE broker_contacts ADD COLUMN {column} {column_type}")
                broker_existing.add(column)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_broker_contacts_area ON broker_contacts(area)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_broker_contacts_office_address ON broker_contacts(office_address)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_broker_contacts_home_address ON broker_contacts(home_address)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id INTEGER,
                payload TEXT,
                requested_by TEXT,
                requested_at TEXT,
                status TEXT DEFAULT 'Pending',
                reviewed_by TEXT,
                reviewed_at TEXT,
                review_comment TEXT
            )
            """
        )
        archive_table_sql = """
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_table TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                deal_type TEXT,
                closed_status TEXT,
                closed_at TEXT,
                archived_at TEXT,
                archived_by TEXT,
                date TEXT,
                owner_name TEXT,
                owner_phone TEXT,
                contact_phone TEXT,
                contact TEXT,
                property_availability TEXT,
                size TEXT,
                measurement TEXT,
                measurement_unit TEXT,
                monthly_rent REAL DEFAULT 0,
                demand REAL DEFAULT 0,
                deposit REAL DEFAULT 0,
                maintenance_charge REAL DEFAULT 0,
                floor TEXT,
                location TEXT,
                bedrooms TEXT,
                bathrooms TEXT,
                furnishing TEXT,
                parking TEXT,
                nearby_landmarks TEXT,
                area_notes TEXT,
                verification_status TEXT,
                photo_paths TEXT,
                facilities TEXT,
                client_broker TEXT,
                bachelor_family TEXT,
                remarks TEXT,
                persons TEXT,
                building_name TEXT,
                workflow_stage TEXT DEFAULT 'Deal Done',
                priority TEXT DEFAULT 'Medium',
                assigned_to TEXT,
                deal_probability REAL DEFAULT 100,
                expected_close_value REAL DEFAULT 0,
                approval_status TEXT,
                created_by TEXT,
                created_at TEXT,
                original_payload TEXT,
                UNIQUE(source_table, source_id)
            )
        """
        for archive_table in ("rented_properties", "sold_properties"):
            cur.execute(archive_table_sql.format(table_name=archive_table))
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{archive_table}_closed_at "
                f"ON {archive_table}(closed_at)"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{archive_table}_location "
                f"ON {archive_table}(location)"
            )
        for source_table, (closed_status, archive_table, deal_type) in CLOSED_AVAILABILITY_ARCHIVES.items():
            source_columns = {row[1] for row in cur.execute(f"PRAGMA table_info({source_table})")}
            archive_columns = {row[1] for row in cur.execute(f"PRAGMA table_info({archive_table})")}
            if not source_columns or not archive_columns:
                continue
            copy_columns = [
                column for column in (
                    "date", "owner_name", "owner_phone", "contact_phone", "contact",
                    "property_availability", "size", "measurement", "measurement_unit",
                    "monthly_rent", "demand", "deposit", "maintenance_charge", "floor",
                    "location", "bedrooms", "bathrooms", "furnishing", "parking",
                    "nearby_landmarks", "area_notes", "verification_status", "photo_paths",
                    "facilities", "client_broker", "bachelor_family", "remarks", "persons",
                    "building_name", "workflow_stage", "priority", "assigned_to",
                    "deal_probability", "expected_close_value", "approval_status",
                    "created_by", "created_at",
                )
                if column in source_columns and column in archive_columns
            ]
            insert_columns = [
                "source_table", "source_id", "deal_type", "closed_status",
                "closed_at", "archived_at", "archived_by",
                *copy_columns,
            ]
            select_values = [
                "?",
                "id",
                "?",
                "?",
                "COALESCE(CAST(closed_at AS TEXT), datetime('now'))" if "closed_at" in source_columns else "datetime('now')",
                "datetime('now')",
                "'migration'",
                *[quote_identifier(column) for column in copy_columns],
            ]
            cur.execute(
                f"""INSERT OR IGNORE INTO {archive_table}
                    ({', '.join(quote_identifier(column) for column in insert_columns)})
                    SELECT {', '.join(select_values)}
                    FROM {source_table}
                    WHERE LOWER(COALESCE(status,''))=LOWER(?)
                      AND COALESCE(is_deleted,0)=0""",
                (source_table, deal_type, closed_status, closed_status),
            )
            updates = ["is_deleted=1"]
            params: list[Any] = []
            if "deleted_by" in source_columns:
                updates.append("deleted_by=COALESCE(NULLIF(deleted_by,''), ?)")
                params.append("deal_archive")
            if "deleted_at" in source_columns:
                updates.append("deleted_at=COALESCE(deleted_at, ?)")
                params.append(datetime.now().isoformat(timespec="seconds"))
            if "workflow_stage" in source_columns:
                updates.append("workflow_stage='Deal Done'")
            if "deal_probability" in source_columns:
                updates.append("deal_probability=100")
            if "closed_at" in source_columns:
                updates.append("closed_at=COALESCE(closed_at, ?)")
                params.append(datetime.now().isoformat(timespec="seconds"))
            params.append(closed_status)
            cur.execute(
                f"""UPDATE {source_table}
                    SET {', '.join(updates)}
                    WHERE LOWER(COALESCE(status,''))=LOWER(?)
                      AND COALESCE(is_deleted,0)=0""",
                tuple(params),
            )
        # SuccessFactors tables
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sf_employee_id TEXT UNIQUE,
                full_name TEXT NOT NULL,
                email TEXT,
                department TEXT,
                job_title TEXT,
                manager_name TEXT,
                hire_date TEXT,
                employment_status TEXT DEFAULT 'Active',
                location TEXT,
                cost_center TEXT,
                notes TEXT,
                synced_at TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_code TEXT UNIQUE,
                position_title TEXT NOT NULL,
                department TEXT,
                location TEXT,
                headcount_max INTEGER DEFAULT 1,
                headcount_current INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Open',
                reports_to TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_performance_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                employee_name TEXT,
                goal_title TEXT NOT NULL,
                goal_description TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'In Progress',
                progress_pct REAL DEFAULT 0,
                rating TEXT,
                review_period TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TEXT,
                FOREIGN KEY (employee_id) REFERENCES sf_employees(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_must_win_battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                battle_code TEXT UNIQUE,
                battle_title TEXT NOT NULL,
                owner_name TEXT,
                department TEXT,
                objective TEXT,
                start_date TEXT,
                end_date TEXT,
                priority TEXT DEFAULT 'High',
                status TEXT DEFAULT 'Active',
                target_value REAL DEFAULT 0,
                current_value REAL DEFAULT 0,
                progress_pct REAL DEFAULT 0,
                business_impact TEXT,
                risks TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_kpis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kpi_code TEXT UNIQUE,
                kpi_name TEXT NOT NULL,
                employee_name TEXT,
                department TEXT,
                category TEXT,
                period TEXT,
                start_date TEXT,
                end_date TEXT,
                target_value REAL DEFAULT 0,
                actual_value REAL DEFAULT 0,
                unit TEXT,
                weight_pct REAL DEFAULT 0,
                achievement_pct REAL DEFAULT 0,
                status TEXT DEFAULT 'On Track',
                owner_name TEXT,
                review_date TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_learning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                employee_name TEXT,
                course_title TEXT NOT NULL,
                course_code TEXT,
                category TEXT,
                assigned_date TEXT,
                due_date TEXT,
                completion_date TEXT,
                status TEXT DEFAULT 'Assigned',
                score REAL,
                instructor TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_recruiting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_requisition_id TEXT,
                job_title TEXT NOT NULL,
                department TEXT,
                location TEXT,
                hiring_manager TEXT,
                recruiter TEXT,
                open_date TEXT,
                close_date TEXT,
                status TEXT DEFAULT 'Open',
                applications_count INTEGER DEFAULT 0,
                shortlisted_count INTEGER DEFAULT 0,
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_compensation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                employee_name TEXT,
                base_salary REAL DEFAULT 0,
                bonus REAL DEFAULT 0,
                allowances REAL DEFAULT 0,
                total_compensation REAL DEFAULT 0,
                currency TEXT DEFAULT 'PKR',
                effective_date TEXT,
                review_cycle TEXT,
                approved_by TEXT,
                status TEXT DEFAULT 'Active',
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_onboarding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                employee_name TEXT,
                task_title TEXT NOT NULL,
                task_category TEXT,
                assigned_to TEXT,
                due_date TEXT,
                completion_date TEXT,
                status TEXT DEFAULT 'Pending',
                priority TEXT DEFAULT 'Medium',
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )

        # Workflow Engine tables
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_name TEXT NOT NULL,
                workflow_type TEXT,
                description TEXT,
                trigger_event TEXT,
                status TEXT DEFAULT 'Active',
                version INTEGER DEFAULT 1,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_workflow_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER,
                step_order INTEGER DEFAULT 1,
                step_name TEXT NOT NULL,
                step_type TEXT,
                assignee_role TEXT,
                assignee_name TEXT,
                sla_hours INTEGER DEFAULT 24,
                action_on_approve TEXT,
                action_on_reject TEXT,
                is_conditional INTEGER DEFAULT 0,
                condition_field TEXT,
                condition_value TEXT,
                created_by TEXT,
                created_at TEXT,
                FOREIGN KEY (workflow_id) REFERENCES wf_workflows(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER,
                workflow_name TEXT,
                reference_table TEXT,
                reference_id INTEGER,
                initiated_by TEXT,
                initiated_at TEXT,
                current_step INTEGER DEFAULT 1,
                current_assignee TEXT,
                status TEXT DEFAULT 'Running',
                due_at TEXT,
                completed_at TEXT,
                priority TEXT DEFAULT 'Normal',
                notes TEXT,
                FOREIGN KEY (workflow_id) REFERENCES wf_workflows(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_id INTEGER,
                workflow_name TEXT,
                step_name TEXT,
                assigned_to TEXT,
                assigned_at TEXT,
                due_at TEXT,
                completed_at TEXT,
                action_taken TEXT,
                comments TEXT,
                status TEXT DEFAULT 'Pending',
                priority TEXT DEFAULT 'Normal',
                reference_table TEXT,
                reference_id INTEGER,
                FOREIGN KEY (instance_id) REFERENCES wf_instances(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                workflow_name TEXT,
                approval_type TEXT,
                requested_by TEXT,
                requested_at TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                decision TEXT,
                comments TEXT,
                reference_table TEXT,
                reference_id INTEGER,
                status TEXT DEFAULT 'Pending'
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                channel TEXT DEFAULT 'In-App',
                sent_at TEXT,
                read_at TEXT,
                status TEXT DEFAULT 'Unread',
                reference_table TEXT,
                reference_id INTEGER,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_sla_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_id INTEGER,
                task_id INTEGER,
                sla_target_hours INTEGER,
                actual_hours REAL,
                breached INTEGER DEFAULT 0,
                logged_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                performed_by TEXT,
                performed_at TEXT,
                reference_table TEXT,
                reference_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                ip_address TEXT,
                session_id TEXT
            )
            """
        )
        default_settings = {
            "phase1_areas": "\n".join(COMMON_AREAS),
            "phase1_facilities": "\n".join(FACILITY_OPTIONS),
            "phase1_floors": "\n".join(FLOOR_OPTIONS),
            "phase1_property_types": "\n".join(PROPERTY_TYPE_OPTIONS),
            "phase1_measurement_units": "\n".join(MEASUREMENT_UNIT_OPTIONS),
            "expense_categories": "\n".join(EXPENSE_CATEGORIES),
            "phase1_theme": "Light",
        }
        for key, value in default_settings.items():
            cur.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()


