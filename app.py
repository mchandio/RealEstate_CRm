import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import tkinter.simpledialog as simpledialog
import tkinter.font as tkfont
import sqlite3
import os
import sys
import json
import socket
import threading
from datetime import datetime, timedelta
import csv
import random
import string
import shutil
import hashlib
from enum import Enum
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

# Always use absolute paths (prevents "saved but not showing" when app is launched
# from different working directories / shortcuts).
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    RESOURCE_DIR = getattr(sys, '_MEIPASS', BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = BASE_DIR

DB_PATH = os.path.join(BASE_DIR, "real_estate_crm.db")
LOGO_DIR = os.path.join(BASE_DIR, "company_logo")
RESOURCE_LOGO_DIR = os.path.join(RESOURCE_DIR, "company_logo")
APP_ICON_PATH = os.path.join(RESOURCE_LOGO_DIR, "RealEstateCRM.ico")
APP_ICON_PNG = os.path.join(RESOURCE_LOGO_DIR, "RealEstateCRM_logo.png")
os.makedirs(LOGO_DIR, exist_ok=True)
LOCAL_SERVICE_PORT = 6090

if getattr(sys, 'frozen', False):
    bundled_db = os.path.join(RESOURCE_DIR, "real_estate_crm.db")
    if not os.path.exists(DB_PATH) and os.path.exists(bundled_db):
        shutil.copy2(bundled_db, DB_PATH)

COLORS = {
    'primary':    '#2563eb',
    'primary_dk': '#1d4ed8',
    'secondary':  '#64748b',
    'success':    '#16a34a',
    'danger':     '#dc2626',
    'warning':    '#ea580c',
    'light':      '#f8fafc',
    'dark':       '#0f172a',
    'border':     '#e2e8f0',
    'bg':         '#f1f5f9',
    'card':       '#ffffff',
    'muted':      '#94a3b8',
    'income_bg':  '#dcfce7',
    'expense_bg': '#fee2e2',
    'sidebar':    '#1e293b',
    'sidebar_txt':'#cbd5e1',
}

COMMON_AREAS = [
    'Gulshan', 'Gulistan-e-Johar', 'Gulberg', 'Clifton', 'DHA', 'Defence',
    'Saddar', 'Korangi', 'Landhi', 'Malir', 'North Nazimabad',
    'Nazimabad', 'PECHS', 'Scheme 33', 'Shah Faisal', 'Tariq Road',
    'Bahadurabad', 'KDA Scheme', 'Military Account', 'Hyderi',
    'Water Pump', 'FB Area', 'Liaquatabad', 'Jamshed Road',
    'University Road', 'Super Highway', 'Rashid Minhas', 'Airport',
    'Cantt', 'Garden', 'Boat Basin', 'Sea View', 'Marina',
    'Gizri', 'Clifton Block 1', 'Clifton Block 2', 'Clifton Block 3',
    'Clifton Block 4', 'Clifton Block 5', 'Clifton Block 6', 'Clifton Block 7',
    'Clifton Block 8', 'Clifton Block 9', 'DHA Phase 1', 'DHA Phase 2',
    'DHA Phase 4', 'DHA Phase 5', 'DHA Phase 6', 'DHA Phase 7', 'DHA Phase 8',
]

DEAL_STAGES = [
    'Lead',
    'Contacted',
    'Visit Scheduled',
    'Negotiation',
    'Closed',
    'Deal Done',
]
DEAL_PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']
STAGE_PROBABILITY = {
    'Lead': 10.0,
    'Contacted': 25.0,
    'Visit Scheduled': 45.0,
    'Negotiation': 70.0,
    'Closed': 90.0,
    'Deal Done': 100.0,
}


def set_app_icon(window):
    try:
        if os.path.exists(APP_ICON_PATH):
            window.iconbitmap(APP_ICON_PATH)
            return
        if PIL_AVAILABLE and os.path.exists(APP_ICON_PNG):
            icon_img = Image.open(APP_ICON_PNG)
            icon_photo = ImageTk.PhotoImage(icon_img)
            window.iconphoto(True, icon_photo)
            window._app_icon_photo = icon_photo
    except Exception:
        pass


def fit_window_to_screen(window, preferred_w, preferred_h, min_w=600, min_h=420,
                         width_ratio=0.92, height_ratio=0.88):
    """Size and center a window so it never starts larger than the monitor."""
    try:
        sw = max(1, window.winfo_screenwidth())
        sh = max(1, window.winfo_screenheight())
    except Exception:
        sw, sh = preferred_w, preferred_h
    width = min(preferred_w, int(sw * width_ratio))
    height = min(preferred_h, int(sh * height_ratio))
    width = max(min(min_w, sw - 40), width)
    height = max(min(min_h, sh - 80), height)
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    try:
        window.minsize(min(min_w, width), min(min_h, height))
    except Exception:
        pass
    window.geometry(f"{width}x{height}+{x}+{y}")


def short_label(text, max_chars=28):
    text = str(text or "")
    return text if len(text) <= max_chars else text[:max_chars - 1].rstrip() + "..."
DEAL_TABLES = (
    'rent_requirements',
    'rent_availability',
    'sale_requirements',
    'sale_availability',
)

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

class Database:
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _table_columns(conn, table):
        try:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            return {row[1] for row in cur.fetchall()}  # row[1] = column name
        except Exception:
            return set()

    @staticmethod
    def _ensure_columns(conn, table, columns):
        """
        columns: list of (col_name, col_type_sql, default_sql_or_None)
        Adds missing columns with ALTER TABLE.
        """
        existing = Database._table_columns(conn, table)
        cur = conn.cursor()
        for col, col_type, default_sql in columns:
            if col in existing:
                continue
            if default_sql:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type} DEFAULT {default_sql}")
            else:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")

    @staticmethod
    def migrate_schema():
        """
        Migrates older DB files to the current expected schema.
        Safe to run multiple times.
        """
        conn = Database.get_connection()
        try:
            # Rent tables (very old DBs might miss many columns)
            Database._ensure_columns(conn, "rent_requirements", [
                ("date", "TEXT", None),
                ("client_name", "TEXT", None),
                ("client_status", "TEXT", "'Client'"),
                ("broker", "TEXT", None),
                ("contact", "TEXT", None),
                ("size", "TEXT", None),
                ("sq_ft_yards", "TEXT", None),
                # Excel-aligned fields
                ("property_requires", "TEXT", None),
                ("measurement", "TEXT", None),
                ("budget", "REAL", None),
                ("option1", "TEXT", None),
                ("option2", "TEXT", None),
                ("bachelor_family", "TEXT", None),
                ("remarks", "TEXT", None),
                # legacy fields kept for backward compatibility
                ("property_type", "TEXT", None),
                ("floor", "TEXT", None),
                ("location", "TEXT", None),
                ("budget_min", "REAL", None),
                ("budget_max", "REAL", None),
                ("maintenance", "REAL", None),
                ("facilities", "TEXT", None),
                ("client_broker", "TEXT", None),
                ("notes", "TEXT", None),
                ("status", "TEXT", "'Open'"),
                ("approval_status", "TEXT", "'Pending'"),
                ("approval_comment", "TEXT", None),
                ("approved_by", "TEXT", None),
                ("approved_at", "TIMESTAMP", None),
                ("created_by", "TEXT", None),
                ("created_at", "TIMESTAMP", None),
            ])
            Database._ensure_columns(conn, "rent_availability", [
                ("date", "TEXT", None),
                ("owner_name", "TEXT", None),
                ("contact", "TEXT", None),
                ("property_availability", "TEXT", None),
                ("property_type", "TEXT", None),
                ("size", "TEXT", None),
                ("sq_ft_yards", "TEXT", None),
                ("measurement", "TEXT", None),
                ("floor", "TEXT", None),
                ("location", "TEXT", None),
                ("monthly_rent", "REAL", None),
                ("deposit", "REAL", None),
                ("maintenance_charge", "REAL", None),
                ("facilities", "TEXT", None),
                ("posted_by", "TEXT", None),
                ("notes", "TEXT", None),
                ("status", "TEXT", "'Available'"),
                ("approval_status", "TEXT", "'Pending'"),
                ("approval_comment", "TEXT", None),
                ("approved_by", "TEXT", None),
                ("approved_at", "TIMESTAMP", None),
                ("client_broker", "TEXT", None),
                ("bachelor_family", "TEXT", None),
                ("remarks", "TEXT", None),
                ("created_by", "TEXT", None),
                ("created_at", "TIMESTAMP", None),
            ])

            # Financial tables
            Database._ensure_columns(conn, "income_transactions", [
                ("transaction_date", "TEXT", None),
                ("income_type", "TEXT", None),
                ("amount", "REAL", None),
                ("tenant_name", "TEXT", None),
                ("description", "TEXT", None),
                ("receipt_no", "TEXT", None),
                ("payment_method", "TEXT", "'Cash'"),
                ("created_by", "TEXT", None),
                ("created_at", "TIMESTAMP", None),
            ])
            Database._ensure_columns(conn, "expense_transactions", [
                ("transaction_date", "TEXT", None),
                ("expense_category", "TEXT", None),
                ("amount", "REAL", None),
                ("vendor_name", "TEXT", None),
                ("description", "TEXT", None),
                ("invoice_no", "TEXT", None),
                ("payment_method", "TEXT", "'Cash'"),
                ("created_by", "TEXT", None),
                ("created_at", "TIMESTAMP", None),
            ])

            # Employees: older DBs may not have department/commission/address/notes
            Database._ensure_columns(conn, "employees", [
                ("employee_id", "TEXT", None),
                ("full_name", "TEXT", None),
                ("cnic", "TEXT", None),
                ("phone", "TEXT", None),
                ("email", "TEXT", None),
                ("position", "TEXT", None),
                ("department", "TEXT", None),
                ("hire_date", "TEXT", None),
                ("base_salary", "REAL", None),
                ("commission_rate", "REAL", "5.0"),
                ("status", "TEXT", "'Active'"),
                ("address", "TEXT", None),
                ("notes", "TEXT", None),
            ])

            # Clients: very old DBs may miss phone/email/etc.
            Database._ensure_columns(conn, "clients", [
                ("client_name", "TEXT", None),
                ("cnic", "TEXT", None),
                ("phone", "TEXT", None),
                ("email", "TEXT", None),
                ("address", "TEXT", None),
                ("client_type", "TEXT", "'Tenant'"),
                ("notes", "TEXT", None),
                ("status", "TEXT", "'Active'"),
                ("created_at", "TIMESTAMP", None),
            ])

            # Properties: guard against older DBs missing later-added fields
            Database._ensure_columns(conn, "properties", [
                ("property_code", "TEXT", None),
                ("title", "TEXT", None),
                ("property_type", "TEXT", None),
                ("status", "TEXT", "'Available'"),
                ("owner_name", "TEXT", None),
                ("owner_contact", "TEXT", None),
                ("location", "TEXT", None),
                ("area", "TEXT", None),
                ("floor", "TEXT", None),
                ("monthly_rent", "REAL", None),
                ("sale_price", "REAL", None),
                ("maintenance_charge", "REAL", None),
                ("facilities", "TEXT", None),
                ("description", "TEXT", None),
                ("created_at", "TIMESTAMP", None),
            ])

            # Sale tables (new feature)
            Database._ensure_columns(conn, "sale_requirements", [
                ("date", "TEXT", None),
                ("client_name", "TEXT", None),
                ("client_status", "TEXT", "'Client'"),
                ("broker", "TEXT", None),
                ("contact", "TEXT", None),
                ("property_requires", "TEXT", None),
                ("size", "TEXT", None),
                ("measurement", "TEXT", None),
                ("budget", "REAL", None),
                ("floor", "TEXT", None),
                ("location", "TEXT", None),
                ("option1", "TEXT", None),
                ("option2", "TEXT", None),
                ("facilities", "TEXT", None),
                ("client_broker", "TEXT", None),
                ("bachelor_family", "TEXT", None),
                ("remarks", "TEXT", None),
                ("approval_status", "TEXT", "'Pending'"),
                ("approval_comment", "TEXT", None),
                ("approved_by", "TEXT", None),
                ("approved_at", "TIMESTAMP", None),
                ("created_by", "TEXT", None),
                ("created_at", "TIMESTAMP", None),
            ])
            Database._ensure_columns(conn, "sale_availability", [
                ("date", "TEXT", None),
                ("owner_name", "TEXT", None),
                ("contact", "TEXT", None),
                ("property_availability", "TEXT", None),
                ("size", "TEXT", None),
                ("measurement", "TEXT", None),
                ("demand", "REAL", None),
                ("floor", "TEXT", None),
                ("location", "TEXT", None),
                ("option1", "TEXT", None),
                ("option2", "TEXT", None),
                ("facilities", "TEXT", None),
                ("client_broker", "TEXT", None),
                ("bachelor_family", "TEXT", None),
                ("remarks", "TEXT", None),
                ("approval_status", "TEXT", "'Pending'"),
                ("approval_comment", "TEXT", None),
                ("approved_by", "TEXT", None),
                ("approved_at", "TIMESTAMP", None),
                ("created_by", "TEXT", None),
                ("created_at", "TIMESTAMP", None),
            ])

            workflow_columns = [
                ("workflow_stage", "TEXT", "'Lead'"),
                ("priority", "TEXT", "'Medium'"),
                ("next_follow_up", "TEXT", None),
                ("assigned_to", "TEXT", None),
                ("last_contacted", "TEXT", None),
                ("deal_probability", "REAL", "10.0"),
                ("expected_close_value", "REAL", "0"),
                ("closed_at", "TIMESTAMP", None),
                ("lost_reason", "TEXT", None),
            ]
            for deal_table in DEAL_TABLES:
                Database._ensure_columns(conn, deal_table, workflow_columns)

            # Backfill: copy legacy transaction_date -> date when needed
            cur = conn.cursor()
            rr_cols = Database._table_columns(conn, "rent_requirements")
            if "client_status" in rr_cols:
                cur.execute("UPDATE rent_requirements SET client_status='Client' WHERE client_status IS NULL OR client_status=''")
            if "broker" in rr_cols and "client_broker" in rr_cols:
                cur.execute("""UPDATE rent_requirements
                               SET broker=client_broker
                               WHERE (broker IS NULL OR broker='')
                                 AND client_broker IS NOT NULL AND client_broker<>''""")
            if "workflow_stage" in rr_cols:
                cur.execute("UPDATE rent_requirements SET workflow_stage='Lead' WHERE workflow_stage IS NULL OR workflow_stage=''")
            if "priority" in rr_cols:
                cur.execute("UPDATE rent_requirements SET priority='Medium' WHERE priority IS NULL OR priority=''")
            if "date" in rr_cols and "transaction_date" in rr_cols:
                cur.execute("UPDATE rent_requirements SET date=transaction_date WHERE (date IS NULL OR date='') AND transaction_date IS NOT NULL")
            if "date" in rr_cols and "date_created" in rr_cols:
                cur.execute("UPDATE rent_requirements SET date=date_created WHERE (date IS NULL OR date='') AND date_created IS NOT NULL")
            if "contact" in rr_cols and "contact_phone" in rr_cols:
                cur.execute("UPDATE rent_requirements SET contact=contact_phone WHERE (contact IS NULL OR contact='') AND contact_phone IS NOT NULL")
            # Backfill Excel fields from legacy columns
            if "property_requires" in rr_cols and "property_type" in rr_cols:
                cur.execute("""UPDATE rent_requirements
                               SET property_requires=property_type
                               WHERE (property_requires IS NULL OR property_requires='')
                                 AND property_type IS NOT NULL""")
            if "size" in rr_cols and "size_beds" in rr_cols:
                cur.execute("""UPDATE rent_requirements
                               SET size=CAST(size_beds AS TEXT) || '-bed'
                               WHERE (size IS NULL OR size='')
                                 AND size_beds IS NOT NULL""")
            if "measurement" in rr_cols and "sq_ft_yards" in rr_cols:
                cur.execute("""UPDATE rent_requirements
                               SET measurement=sq_ft_yards
                               WHERE (measurement IS NULL OR measurement='')
                                 AND sq_ft_yards IS NOT NULL""")
            if "measurement" in rr_cols and "sq_ft" in rr_cols:
                cur.execute("""UPDATE rent_requirements
                               SET measurement=CAST(sq_ft AS TEXT) || ' sqft'
                               WHERE (measurement IS NULL OR measurement='')
                                 AND sq_ft IS NOT NULL""")
            if "budget" in rr_cols and "budget_max" in rr_cols:
                cur.execute("""UPDATE rent_requirements
                               SET budget=budget_max
                               WHERE budget IS NULL AND budget_max IS NOT NULL""")
            if "expected_close_value" in rr_cols and "budget" in rr_cols:
                cur.execute("""UPDATE rent_requirements
                               SET expected_close_value=COALESCE(budget, budget_max, 0)
                               WHERE expected_close_value IS NULL OR expected_close_value=0""")
            if "remarks" in rr_cols and "notes" in rr_cols:
                cur.execute("""UPDATE rent_requirements
                               SET remarks=notes
                               WHERE (remarks IS NULL OR remarks='')
                                 AND notes IS NOT NULL""")
            ra_cols = Database._table_columns(conn, "rent_availability")
            if "workflow_stage" in ra_cols:
                cur.execute("UPDATE rent_availability SET workflow_stage='Lead' WHERE workflow_stage IS NULL OR workflow_stage=''")
            if "priority" in ra_cols:
                cur.execute("UPDATE rent_availability SET priority='Medium' WHERE priority IS NULL OR priority=''")
            if "date" in ra_cols and "transaction_date" in ra_cols:
                cur.execute("UPDATE rent_availability SET date=transaction_date WHERE (date IS NULL OR date='') AND transaction_date IS NOT NULL")
            if "date" in ra_cols and "date_posted" in ra_cols:
                cur.execute("UPDATE rent_availability SET date=date_posted WHERE (date IS NULL OR date='') AND date_posted IS NOT NULL")
            if "contact" in ra_cols and "contact_phone" in ra_cols:
                cur.execute("UPDATE rent_availability SET contact=contact_phone WHERE (contact IS NULL OR contact='') AND contact_phone IS NOT NULL")
            # Backfill new availability fields from legacy columns
            if "property_availability" in ra_cols and "property_type" in ra_cols:
                cur.execute("""UPDATE rent_availability
                               SET property_availability=property_type
                               WHERE (property_availability IS NULL OR property_availability='')
                                 AND property_type IS NOT NULL""")
            if "size" in ra_cols and "size_beds" in ra_cols:
                cur.execute("""UPDATE rent_availability
                               SET size=CAST(size_beds AS TEXT) || '-bed'
                               WHERE (size IS NULL OR size='')
                                 AND size_beds IS NOT NULL""")
            if "measurement" in ra_cols and "sq_ft_yards" in ra_cols:
                cur.execute("""UPDATE rent_availability
                               SET measurement=sq_ft_yards
                               WHERE (measurement IS NULL OR measurement='')
                                 AND sq_ft_yards IS NOT NULL""")
            if "measurement" in ra_cols and "sq_ft" in ra_cols:
                cur.execute("""UPDATE rent_availability
                               SET measurement=CAST(sq_ft AS TEXT) || ' sqft'
                               WHERE (measurement IS NULL OR measurement='')
                                 AND sq_ft IS NOT NULL""")
            if "expected_close_value" in ra_cols and "monthly_rent" in ra_cols:
                cur.execute("""UPDATE rent_availability
                               SET expected_close_value=COALESCE(monthly_rent, 0)
                               WHERE expected_close_value IS NULL OR expected_close_value=0""")
            if "remarks" in ra_cols and "notes" in ra_cols:
                cur.execute("""UPDATE rent_availability
                               SET remarks=notes
                               WHERE (remarks IS NULL OR remarks='')
                                 AND notes IS NOT NULL""")

            sr_cols = Database._table_columns(conn, "sale_requirements")
            if "client_status" in sr_cols:
                cur.execute("UPDATE sale_requirements SET client_status='Client' WHERE client_status IS NULL OR client_status=''")
            if "broker" in sr_cols and "client_broker" in sr_cols:
                cur.execute("""UPDATE sale_requirements
                               SET broker=client_broker
                               WHERE (broker IS NULL OR broker='')
                                 AND client_broker IS NOT NULL AND client_broker<>''""")
            if "workflow_stage" in sr_cols:
                cur.execute("UPDATE sale_requirements SET workflow_stage='Lead' WHERE workflow_stage IS NULL OR workflow_stage=''")
            if "priority" in sr_cols:
                cur.execute("UPDATE sale_requirements SET priority='Medium' WHERE priority IS NULL OR priority=''")
            if "date" in sr_cols and "date_created" in sr_cols:
                cur.execute("UPDATE sale_requirements SET date=date_created WHERE (date IS NULL OR date='') AND date_created IS NOT NULL")
            if "contact" in sr_cols and "contact_phone" in sr_cols:
                cur.execute("UPDATE sale_requirements SET contact=contact_phone WHERE (contact IS NULL OR contact='') AND contact_phone IS NOT NULL")
            if "property_requires" in sr_cols and "property_type" in sr_cols:
                cur.execute("""UPDATE sale_requirements
                               SET property_requires=property_type
                               WHERE (property_requires IS NULL OR property_requires='')
                                 AND property_type IS NOT NULL""")
            if "size" in sr_cols and "size_beds" in sr_cols:
                cur.execute("""UPDATE sale_requirements
                               SET size=CAST(size_beds AS TEXT) || '-bed'
                               WHERE (size IS NULL OR size='')
                                 AND size_beds IS NOT NULL""")
            if "measurement" in sr_cols and "sq_ft" in sr_cols:
                cur.execute("""UPDATE sale_requirements
                               SET measurement=CAST(sq_ft AS TEXT) || ' sqft'
                               WHERE (measurement IS NULL OR measurement='')
                                 AND sq_ft IS NOT NULL""")
            if "budget" in sr_cols and "budget_max" in sr_cols:
                cur.execute("""UPDATE sale_requirements
                               SET budget=budget_max
                               WHERE budget IS NULL AND budget_max IS NOT NULL""")
            if "expected_close_value" in sr_cols and "budget" in sr_cols:
                cur.execute("""UPDATE sale_requirements
                               SET expected_close_value=COALESCE(budget, budget_max, 0)
                               WHERE expected_close_value IS NULL OR expected_close_value=0""")

            sa_cols = Database._table_columns(conn, "sale_availability")
            if "workflow_stage" in sa_cols:
                cur.execute("UPDATE sale_availability SET workflow_stage='Lead' WHERE workflow_stage IS NULL OR workflow_stage=''")
            if "priority" in sa_cols:
                cur.execute("UPDATE sale_availability SET priority='Medium' WHERE priority IS NULL OR priority=''")
            if "date" in sa_cols and "date_posted" in sa_cols:
                cur.execute("UPDATE sale_availability SET date=date_posted WHERE (date IS NULL OR date='') AND date_posted IS NOT NULL")
            if "contact" in sa_cols and "contact_phone" in sa_cols:
                cur.execute("UPDATE sale_availability SET contact=contact_phone WHERE (contact IS NULL OR contact='') AND contact_phone IS NOT NULL")
            if "property_availability" in sa_cols and "property_type" in sa_cols:
                cur.execute("""UPDATE sale_availability
                               SET property_availability=property_type
                               WHERE (property_availability IS NULL OR property_availability='')
                                 AND property_type IS NOT NULL""")
            if "size" in sa_cols and "size_beds" in sa_cols:
                cur.execute("""UPDATE sale_availability
                               SET size=CAST(size_beds AS TEXT) || '-bed'
                               WHERE (size IS NULL OR size='')
                                 AND size_beds IS NOT NULL""")
            if "measurement" in sa_cols and "sq_ft" in sa_cols:
                cur.execute("""UPDATE sale_availability
                               SET measurement=CAST(sq_ft AS TEXT) || ' sqft'
                               WHERE (measurement IS NULL OR measurement='')
                                 AND sq_ft IS NOT NULL""")
            if "demand" in sa_cols and "asking_price" in sa_cols:
                cur.execute("""UPDATE sale_availability
                               SET demand=asking_price
                               WHERE demand IS NULL AND asking_price IS NOT NULL""")
            if "expected_close_value" in sa_cols and "demand" in sa_cols:
                cur.execute("""UPDATE sale_availability
                               SET expected_close_value=COALESCE(demand, asking_price, 0)
                               WHERE expected_close_value IS NULL OR expected_close_value=0""")

            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def execute(query, params=(), fetch=False):
        conn = None
        try:
            conn = Database.get_connection()
            c = conn.cursor()
            c.execute(query, params)
            result = c.fetchall() if fetch else None
            conn.commit()
            return result
        except Exception as e:
            print(f"DB Error: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def insert(query, params=()):
        conn = None
        try:
            conn = Database.get_connection()
            c = conn.cursor()
            c.execute(query, params)
            row_id = c.lastrowid
            conn.commit()
            return row_id
        except Exception as e:
            print(f"DB Error: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def init_all():
        conn = Database.get_connection()
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS app_settings
                     (key TEXT PRIMARY KEY, value TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE NOT NULL,
                      password_hash TEXT NOT NULL,
                      full_name TEXT,
                      email TEXT,
                      role TEXT DEFAULT 'Staff',
                      is_active INTEGER DEFAULT 1,
                      created_at TIMESTAMP,
                      last_login TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS login_logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      login_time TIMESTAMP,
                      status TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS rent_requirements
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      date TEXT,
                      client_name TEXT,
                      client_status TEXT DEFAULT 'Client',
                      broker TEXT,
                      contact TEXT,
                      property_requires TEXT,
                      size TEXT, measurement TEXT,
                      budget REAL,
                      floor TEXT, location TEXT,
                      option1 TEXT, option2 TEXT,
                      facilities TEXT,
                      client_broker TEXT,
                      bachelor_family TEXT,
                      remarks TEXT,
                      workflow_stage TEXT DEFAULT 'Lead',
                      priority TEXT DEFAULT 'Medium',
                      next_follow_up TEXT,
                      assigned_to TEXT,
                      last_contacted TEXT,
                      deal_probability REAL DEFAULT 10.0,
                      expected_close_value REAL DEFAULT 0,
                      closed_at TIMESTAMP,
                      lost_reason TEXT,
                      -- legacy fields (kept so older code/exports won't break)
                      property_type TEXT, sq_ft_yards TEXT,
                      budget_min REAL, budget_max REAL,
                      maintenance REAL, notes TEXT,
                      status TEXT DEFAULT 'Open',
                      approval_status TEXT DEFAULT 'Pending',
                      approval_comment TEXT,
                      approved_by TEXT,
                      approved_at TIMESTAMP,
                      created_by TEXT, created_at TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS rent_availability
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      date TEXT,
                      owner_name TEXT, contact TEXT,
                      property_availability TEXT,
                      size TEXT, measurement TEXT,
                      monthly_rent REAL,
                      floor TEXT, location TEXT,
                      deposit REAL,
                      maintenance_charge REAL,
                      facilities TEXT,
                      client_broker TEXT,
                      bachelor_family TEXT,
                      remarks TEXT,
                      workflow_stage TEXT DEFAULT 'Lead',
                      priority TEXT DEFAULT 'Medium',
                      next_follow_up TEXT,
                      assigned_to TEXT,
                      last_contacted TEXT,
                      deal_probability REAL DEFAULT 10.0,
                      expected_close_value REAL DEFAULT 0,
                      closed_at TIMESTAMP,
                      lost_reason TEXT,
                      -- legacy fields
                      property_type TEXT, sq_ft_yards TEXT,
                      posted_by TEXT, notes TEXT,
                      status TEXT DEFAULT 'Available',
                      approval_status TEXT DEFAULT 'Pending',
                      approval_comment TEXT,
                      approved_by TEXT,
                      approved_at TIMESTAMP,
                      created_by TEXT, created_at TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS sale_requirements
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      date TEXT,
                      client_name TEXT,
                      client_status TEXT DEFAULT 'Client',
                      broker TEXT,
                      contact TEXT,
                      property_requires TEXT,
                      size TEXT, measurement TEXT,
                      budget REAL,
                      floor TEXT, location TEXT,
                      option1 TEXT, option2 TEXT,
                      facilities TEXT,
                      client_broker TEXT,
                      bachelor_family TEXT,
                      remarks TEXT,
                      workflow_stage TEXT DEFAULT 'Lead',
                      priority TEXT DEFAULT 'Medium',
                      next_follow_up TEXT,
                      assigned_to TEXT,
                      last_contacted TEXT,
                      deal_probability REAL DEFAULT 10.0,
                      expected_close_value REAL DEFAULT 0,
                      closed_at TIMESTAMP,
                      lost_reason TEXT,
                      approval_status TEXT DEFAULT 'Pending',
                      approval_comment TEXT,
                      approved_by TEXT,
                      approved_at TIMESTAMP,
                      created_by TEXT, created_at TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS sale_availability
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      date TEXT,
                      owner_name TEXT, contact TEXT,
                      property_availability TEXT,
                      size TEXT, measurement TEXT,
                      demand REAL,
                      floor TEXT, location TEXT,
                      option1 TEXT, option2 TEXT,
                      facilities TEXT,
                      client_broker TEXT,
                      bachelor_family TEXT,
                      remarks TEXT,
                      workflow_stage TEXT DEFAULT 'Lead',
                      priority TEXT DEFAULT 'Medium',
                      next_follow_up TEXT,
                      assigned_to TEXT,
                      last_contacted TEXT,
                      deal_probability REAL DEFAULT 10.0,
                      expected_close_value REAL DEFAULT 0,
                      closed_at TIMESTAMP,
                      lost_reason TEXT,
                      approval_status TEXT DEFAULT 'Pending',
                      approval_comment TEXT,
                      approved_by TEXT,
                      approved_at TIMESTAMP,
                      created_by TEXT, created_at TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS income_transactions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      transaction_date TEXT, income_type TEXT,
                      amount REAL, tenant_name TEXT, description TEXT,
                      receipt_no TEXT, payment_method TEXT DEFAULT 'Cash',
                      created_by TEXT, created_at TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS expense_transactions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      transaction_date TEXT, expense_category TEXT,
                      amount REAL, vendor_name TEXT, description TEXT,
                      invoice_no TEXT, payment_method TEXT DEFAULT 'Cash',
                      created_by TEXT, created_at TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS employees
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      employee_id TEXT, full_name TEXT,
                      cnic TEXT, phone TEXT, email TEXT,
                      position TEXT, department TEXT,
                      hire_date TEXT, base_salary REAL,
                      commission_rate REAL DEFAULT 5.0,
                      status TEXT DEFAULT 'Active',
                      address TEXT, notes TEXT,
                      created_at TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS attendance
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      employee_id INTEGER, date TEXT,
                      check_in TEXT, check_out TEXT,
                      status TEXT DEFAULT 'Present',
                      notes TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS salary_payments
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      employee_id INTEGER, payment_date TEXT,
                      month TEXT, year TEXT,
                      base_salary REAL, bonus REAL DEFAULT 0,
                      deductions REAL DEFAULT 0, net_salary REAL,
                      payment_method TEXT, notes TEXT,
                      created_at TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS properties
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      property_code TEXT, title TEXT,
                      property_type TEXT, status TEXT DEFAULT 'Available',
                      owner_name TEXT, owner_contact TEXT,
                      location TEXT, area TEXT, floor TEXT,
                      monthly_rent REAL, sale_price REAL,
                      maintenance_charge REAL, facilities TEXT,
                      description TEXT, created_at TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS clients
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      client_name TEXT, cnic TEXT,
                      phone TEXT, email TEXT,
                      address TEXT, client_type TEXT DEFAULT 'Tenant',
                      notes TEXT, status TEXT DEFAULT 'Active',
                      created_at TIMESTAMP)''')

        conn.commit()
        conn.close()

        # Ensure older DB files get upgraded to current schema.
        # IMPORTANT: run migrations after closing the initializer connection to avoid
        # "database is locked" and partially-applied ALTERs on Windows.
        try:
            Database.migrate_schema()
        except Exception as e:
            print(f"DB Migration Error: {e}")

        # Seed default admin user (after migrations)
        conn2 = Database.get_connection()
        c2 = conn2.cursor()
        c2.execute("SELECT COUNT(*) as cnt FROM users")
        count = c2.fetchone()['cnt']
        if count == 0:
            pwd_hash = hashlib.sha256("admin".encode()).hexdigest()
            c2.execute("""INSERT INTO users
                        (username, password_hash, full_name, email, role, is_active, created_at)
                        VALUES (?,?,?,?,?,1,?)""",
                       ("admin", pwd_hash, "Administrator", "admin@company.com",
                        "Super Admin", datetime.now()))
            conn2.commit()
        conn2.close()

        defaults = {
            'company_name': 'Real Estate Management',
            'company_address': 'Karachi, Pakistan',
            'company_phone': '+92-300-0000000',
            'company_email': 'info@company.com',
            'company_logo': '',
            'currency': 'PKR',
            'currency_symbol': 'Rs.',
            'date_format': 'DD/MM/YYYY',
            'theme': 'Light',
            'default_commission': '5.0',
            'bank_account': 'Not Configured',
            'tax_rate': '17',
            'language': 'English',
            'max_login_attempts': '3',
            'session_timeout': '60',
        }
        for k, v in defaults.items():
            Database.execute(
                "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?,?)", (k, v))


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

class Settings:
    DEFAULTS = {
        'company_name': 'Real Estate Management',
        'company_address': 'Karachi, Pakistan',
        'company_phone': '+92-300-0000000',
        'company_email': 'info@company.com',
        'company_logo': '',
        'currency': 'PKR',
        'currency_symbol': 'Rs.',
        'date_format': 'DD/MM/YYYY',
        'theme': 'Light',
        'default_commission': '5.0',
        'bank_account': 'Not Configured',
        'tax_rate': '17',
        'language': 'English',
    }

    @staticmethod
    def get(key, default=None):
        if default is None:
            default = Settings.DEFAULTS.get(key, '')
        result = Database.execute(
            "SELECT value FROM app_settings WHERE key=?", (key,), fetch=True)
        return result[0]['value'] if result else default

    @staticmethod
    def set(key, value):
        Database.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?,?)", (key, value))


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════════════════

class UserRole(Enum):
    SUPER_ADMIN = "Super Admin"
    ADMIN = "Admin"
    MANAGER = "Manager"
    STAFF = "Staff"
    VIEWER = "Viewer"

ROLE_PERMISSIONS = {
    'Super Admin': ['dashboard','rent','financial','employees','reports','settings','users','backup','delete'],
    'Admin':       ['dashboard','rent','financial','employees','reports','settings','users','backup','delete'],
    'Manager':     ['dashboard','rent','financial_view','employees','reports'],
    'Staff':       ['rent'],
    'Viewer':      ['dashboard','rent_view','employees_view','reports'],
}

def has_permission(role, perm):
    perms = ROLE_PERMISSIONS.get(role, [])
    return perm in perms

class Auth:
    @staticmethod
    def hash_pw(pw):
        return hashlib.sha256(pw.encode()).hexdigest()

    @staticmethod
    def verify(pw, h):
        return hashlib.sha256(pw.encode()).hexdigest() == h

    @staticmethod
    def login(username, password):
        result = Database.execute(
            "SELECT * FROM users WHERE username=? AND is_active=1",
            (username,), fetch=True)
        if result:
            user = result[0]
            if Auth.verify(password, user['password_hash']):
                Database.execute(
                    "UPDATE users SET last_login=? WHERE id=?",
                    (datetime.now(), user['id']))
                Database.execute(
                    "INSERT INTO login_logs (user_id, login_time, status) VALUES (?,?,?)",
                    (user['id'], datetime.now(), 'Success'))
                return dict(user)
        Database.execute(
            "INSERT INTO login_logs (user_id, login_time, status) VALUES (?,?,?)",
            (None, datetime.now(), 'Failed'))
        return None

    @staticmethod
    def create_user(username, password, full_name, email, role):
        existing = Database.execute(
            "SELECT id FROM users WHERE username=?", (username,), fetch=True)
        if existing:
            return False, "Username already exists"
        try:
            Database.execute(
                """INSERT INTO users (username, password_hash, full_name, email, role, is_active, created_at)
                   VALUES (?,?,?,?,?,1,?)""",
                (username, Auth.hash_pw(password), full_name, email, role, datetime.now()))
            return True, "User created successfully"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def change_password(user_id, old_pw, new_pw):
        result = Database.execute(
            "SELECT password_hash FROM users WHERE id=?", (user_id,), fetch=True)
        if not result:
            return False, "User not found"
        if not Auth.verify(old_pw, result[0]['password_hash']):
            return False, "Current password is incorrect"
        Database.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (Auth.hash_pw(new_pw), user_id))
        return True, "Password changed successfully"


def gen_id(prefix=""):
    return f"{prefix}{''.join(random.choices(string.digits, k=4))}"


# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Professional Real Estate CRM — Login")
        set_app_icon(self.root)
        fit_window_to_screen(self.root, 460, 580, min_w=380, min_h=500,
                             width_ratio=0.92, height_ratio=0.90)
        self.root.resizable(True, True)
        self.root.configure(bg='#f1f5f9')
        self.current_user = None
        self._build()

    def _center(self):
        fit_window_to_screen(self.root, 460, 580, min_w=380, min_h=500,
                             width_ratio=0.92, height_ratio=0.90)

    def _build(self):
        hdr = tk.Frame(self.root, bg=COLORS['primary'], height=160)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)

        tk.Label(hdr, text="🏢", bg=COLORS['primary'], fg='white',
                 font=('Segoe UI', 36)).pack(pady=(20, 0))
        tk.Label(hdr, text=Settings.get('company_name'),
                 bg=COLORS['primary'], fg='white',
                 font=('Segoe UI', 15, 'bold')).pack()
        tk.Label(hdr, text="Real Estate CRM — Secure Login",
                 bg=COLORS['primary'], fg='#bfdbfe',
                 font=('Segoe UI', 9)).pack()

        card = tk.Frame(self.root, bg='white', relief='flat')
        card.pack(fill='both', expand=True, padx=30, pady=20)

        tk.Label(card, text="Sign In to Your Account",
                 bg='white', fg=COLORS['dark'],
                 font=('Segoe UI', 13, 'bold')).pack(pady=(20, 15))

        tk.Label(card, text="Username", bg='white', fg=COLORS['secondary'],
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=20)
        self.username_var = tk.StringVar(value="admin")
        ue = tk.Entry(card, textvariable=self.username_var,
                      font=('Segoe UI', 11), relief='solid', bd=1,
                      bg='#f8fafc')
        ue.pack(fill='x', padx=20, ipady=7, pady=(3, 12))

        tk.Label(card, text="Password", bg='white', fg=COLORS['secondary'],
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=20)
        self.pw_var = tk.StringVar(value="admin")
        pe = tk.Entry(card, textvariable=self.pw_var, show='●',
                      font=('Segoe UI', 11), relief='solid', bd=1,
                      bg='#f8fafc')
        pe.pack(fill='x', padx=20, ipady=7, pady=(3, 5))
        pe.bind('<Return>', lambda e: self._login())

        self._show_pw = tk.BooleanVar()
        def toggle_pw():
            pe.config(show='' if self._show_pw.get() else '●')
        tk.Checkbutton(card, text="Show password", variable=self._show_pw,
                       command=toggle_pw, bg='white', fg=COLORS['secondary'],
                       font=('Segoe UI', 8)).pack(anchor='w', padx=20, pady=(0,15))

        self.status_lbl = tk.Label(card, text="", bg='white', fg=COLORS['danger'],
                                   font=('Segoe UI', 9))
        self.status_lbl.pack(pady=(0, 8))

        btn = tk.Button(card, text="🔓  SIGN IN",
                        font=('Segoe UI', 12, 'bold'),
                        bg=COLORS['primary'], fg='white',
                        relief='flat', cursor='hand2',
                        activebackground=COLORS['primary_dk'],
                        activeforeground='white',
                        command=self._login)
        btn.pack(fill='x', padx=20, ipady=10, pady=(0, 20))

        info = tk.Frame(self.root, bg='#eff6ff')
        info.pack(fill='x', padx=30, pady=(0, 15))
        tk.Label(info, text="Default: admin / admin  •  Change after first login",
                 bg='#eff6ff', fg='#1d4ed8',
                 font=('Segoe UI', 8), pady=6).pack()

        ue.focus()

    def _login(self):
        u = self.username_var.get().strip()
        p = self.pw_var.get()
        if not u or not p:
            self.status_lbl.config(text="⚠ Please enter username and password")
            return
        user = Auth.login(u, p)
        if user:
            self.current_user = user
            self.root.destroy()
        else:
            self.status_lbl.config(text="✗ Invalid username or password")
            self.pw_var.set("")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def safe_float(val, default=0.0):
    """FIX: safely convert a string to float, return default on failure."""
    try:
        text = clean_number_text(val)
        return float(text) if text else default
    except (ValueError, TypeError):
        return default


NUMERIC_FORM_KEYS = {
    'amount', 'area', 'base_salary', 'bonus', 'budget', 'commission_rate',
    'default_commission', 'deal_probability',
    'deductions', 'demand', 'deposit', 'maintenance_charge',
    'expected_close_value', 'monthly_rent', 'net_salary', 'sale_price',
    'tax_rate',
}

DATE_FORM_KEYS = {'date', 'transaction_date', 'hire_date', 'next_follow_up'}
EMAIL_FORM_KEYS = {'email', 'company_email'}
PHONE_FORM_KEYS = {'contact', 'phone', 'owner_contact', 'company_phone'}
CNIC_FORM_KEYS = {'cnic'}
PERCENT_FORM_KEYS = {'commission_rate', 'deal_probability', 'default_commission', 'tax_rate'}


def clean_number_text(val):
    text = str(val or '').strip()
    if not text:
        return ''
    for token in ('PKR', 'Pkr', 'pkr', 'Rs.', 'Rs', 'rs.', 'rs', '$'):
        text = text.replace(token, '')
    return text.replace(',', '').strip()


def is_valid_number_text(val):
    text = clean_number_text(val)
    if not text:
        return True
    try:
        float(text)
        return True
    except (TypeError, ValueError):
        return False


def is_valid_date_text(val):
    text = str(val or '').strip()
    if not text:
        return True
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_valid_email_text(val):
    text = str(val or '').strip()
    if not text:
        return True
    if ' ' in text or text.count('@') != 1:
        return False
    local, domain = text.split('@', 1)
    return bool(local) and '.' in domain and not domain.startswith('.') and not domain.endswith('.')


def is_valid_phone_text(val):
    text = str(val or '').strip()
    if not text:
        return True
    allowed = set("0123456789+-() ")
    digits = ''.join(ch for ch in text if ch.isdigit())
    return all(ch in allowed for ch in text) and 7 <= len(digits) <= 15


def is_valid_cnic_text(val):
    text = str(val or '').strip()
    if not text:
        return True
    digits = ''.join(ch for ch in text if ch.isdigit())
    return len(digits) == 13 and all(ch.isdigit() or ch == '-' for ch in text)


def validate_form_value(key, label, value, *, required=False, numeric=False,
                        options=None, strict_options=False):
    text = str(value or '').strip()
    if required and not text:
        raise ValueError(f"Please enter {label}.")
    if numeric and text and not is_valid_number_text(text):
        raise ValueError(f"Please enter a valid number for {label}.")
    if key in DATE_FORM_KEYS and text and not is_valid_date_text(text):
        raise ValueError(f"{label} must be in YYYY-MM-DD format.")
    if key in EMAIL_FORM_KEYS and text and not is_valid_email_text(text):
        raise ValueError(f"Please enter a valid email address for {label}.")
    if key in PHONE_FORM_KEYS and text and not is_valid_phone_text(text):
        raise ValueError(f"Please enter a valid phone/contact number for {label}.")
    if key in CNIC_FORM_KEYS and text and not is_valid_cnic_text(text):
        raise ValueError(f"{label} must contain exactly 13 digits.")
    if key in PERCENT_FORM_KEYS and text and is_valid_number_text(text):
        number = safe_float(text)
        if number < 0 or number > 100:
            raise ValueError(f"{label} must be between 0 and 100.")
    if strict_options and text and options and text not in options:
        raise ValueError(f"Please select a valid option for {label}.")


# ═══════════════════════════════════════════════════════════════════════════════
# MODERN UI WIDGETS
# ═══════════════════════════════════════════════════════════════════════════════

class AutocompleteCombobox(ttk.Combobox):
    """Combobox with real-time filtering as user types."""

    def __init__(self, master=None, **kwargs):
        self._completion_list = sorted(kwargs.pop('completion_list', []), key=str.lower)
        self._match_anywhere = kwargs.pop('match_anywhere', True)
        super().__init__(master=master, **kwargs)
        self._current_values = self._completion_list[:]
        self.configure(values=self._current_values)
        self.bind('<KeyRelease>', self._on_keyrelease)
        self.bind('<FocusOut>', self._on_focus_out)
        self._focus_out_skip = False

    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list, key=str.lower)
        self._current_values = self._completion_list[:]
        self.configure(values=self._current_values)

    def _on_keyrelease(self, event):
        if event.keysym in ('BackSpace', 'Delete', 'Left', 'Right', 'Up', 'Down', 'Home', 'End', 'Return', 'Tab'):
            return
        self._focus_out_skip = True
        text = self.get().strip().lower()
        if not text:
            self._current_values = self._completion_list[:]
            self.configure(values=self._current_values)
            self.event_generate('<<ComboboxSelected>>')
            return
        if self._match_anywhere:
            matches = [item for item in self._completion_list if text in item.lower()]
        else:
            matches = [item for item in self._completion_list if item.lower().startswith(text)]
        if matches:
            self._current_values = matches
            self.configure(values=matches)
            self.event_generate('<<ComboboxSelected>>')
        else:
            self._current_values = [self.get()]
            self.configure(values=self._current_values)

    def _on_focus_out(self, event):
        if self._focus_out_skip:
            self._focus_out_skip = False
            return
        self.set_completion_list(self._completion_list)


class TreeCellTooltip:
    """Show full Treeview cell text when a value is wider than its column."""

    def __init__(self, tree):
        self.tree = tree
        self.tip = None
        self.active_cell = None
        self.font = tkfont.Font(family="Segoe UI", size=10)
        tree.bind('<Motion>', self._on_motion, add='+')
        tree.bind('<Leave>', self._hide, add='+')
        tree.bind('<ButtonPress>', self._hide, add='+')
        tree.bind('<MouseWheel>', self._hide, add='+')

    def _on_motion(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            self._hide()
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id.startswith('#'):
            self._hide()
            return
        try:
            col_index = int(col_id[1:]) - 1
            col_name = list(self.tree['columns'])[col_index]
        except (ValueError, IndexError):
            self._hide()
            return
        text = str(self.tree.set(row_id, col_name) or '').strip()
        col_width = int(self.tree.column(col_name, 'width') or 0)
        if not text or (len(text) <= 18 and self.font.measure(text) <= max(40, col_width - 18)):
            self._hide()
            return
        cell = (row_id, col_name, text)
        if cell != self.active_cell:
            self._show(text, event.x_root + 16, event.y_root + 18)
            self.active_cell = cell
        elif self.tip:
            self.tip.geometry(f"+{event.x_root + 16}+{event.y_root + 18}")

    def _show(self, text, x, y):
        self._hide()
        self.tip = tk.Toplevel(self.tree)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip,
            text=text,
            justify='left',
            wraplength=520,
            bg='#111827',
            fg='white',
            relief='solid',
            bd=1,
            padx=10,
            pady=7,
            font=('Segoe UI', 9)
        )
        label.pack()

    def _hide(self, event=None):
        self.active_cell = None
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None


class TreeCellSelector:
    """Visual cell selection for ttk.Treeview while preserving row-based actions."""

    def __init__(self, tree):
        self.tree = tree
        self.label = tk.Label(
            tree,
            bg=COLORS['primary'],
            fg='white',
            anchor='w',
            padx=6,
            font=('Segoe UI', 10),
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS['primary_dk'],
        )
        self.label.place_forget()
        tree._active_cell = None
        tree.bind('<ButtonRelease-1>', self._on_click, add='+')
        tree.bind('<Up>', self._on_key_nav, add='+')
        tree.bind('<Down>', self._on_key_nav, add='+')
        tree.bind('<Left>', self._on_key_nav, add='+')
        tree.bind('<Right>', self._on_key_nav, add='+')
        tree.bind('<Tab>', self._on_key_nav, add='+')
        tree.bind('<Shift-Tab>', self._on_key_nav, add='+')
        tree.bind('<ISO_Left_Tab>', self._on_key_nav, add='+')
        tree.bind('<Home>', self._on_key_nav, add='+')
        tree.bind('<End>', self._on_key_nav, add='+')
        tree.bind('<Prior>', self._on_key_nav, add='+')
        tree.bind('<Next>', self._on_key_nav, add='+')
        tree.bind('<Control-Home>', self._on_key_nav, add='+')
        tree.bind('<Control-End>', self._on_key_nav, add='+')
        tree.bind('<Configure>', lambda _e: self.refresh_later(), add='+')
        tree.bind('<MouseWheel>', lambda _e: self.refresh_later(), add='+')
        tree.bind('<Button-4>', lambda _e: self.refresh_later(), add='+')
        tree.bind('<Button-5>', lambda _e: self.refresh_later(), add='+')

    def _on_click(self, event):
        if self.tree.identify_region(event.x, event.y) != 'cell':
            self.clear()
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id.startswith('#'):
            self.clear()
            return
        try:
            col_index = int(col_id[1:]) - 1
            col_name = list(self.tree['columns'])[col_index]
        except (ValueError, IndexError):
            self.clear()
            return
        self.select(row_id, col_name)

    def _on_key_nav(self, event):
        rows = list(self.tree.get_children(''))
        cols = self._display_columns()
        if not rows or not cols:
            return 'break'

        active = getattr(self.tree, '_active_cell', None)
        row_id = active[0] if active and self.tree.exists(active[0]) else self.tree.focus()
        if not row_id:
            selection = self.tree.selection()
            row_id = selection[0] if selection else rows[0]
        col_name = active[1] if active and active[1] in cols else cols[0]

        row_idx = rows.index(row_id) if row_id in rows else 0
        col_idx = cols.index(col_name) if col_name in cols else 0
        key = event.keysym
        shift_tab = key == 'ISO_Left_Tab' or (key == 'Tab' and bool(event.state & 0x0001))

        if key == 'Up':
            row_idx = max(0, row_idx - 1)
        elif key == 'Down':
            row_idx = min(len(rows) - 1, row_idx + 1)
        elif key == 'Left':
            col_idx = max(0, col_idx - 1)
        elif key == 'Right':
            col_idx = min(len(cols) - 1, col_idx + 1)
        elif key == 'Tab' and not shift_tab:
            if col_idx < len(cols) - 1:
                col_idx += 1
            elif row_idx < len(rows) - 1:
                row_idx += 1
                col_idx = 0
        elif key in ('Tab', 'ISO_Left_Tab') and shift_tab:
            if col_idx > 0:
                col_idx -= 1
            elif row_idx > 0:
                row_idx -= 1
                col_idx = len(cols) - 1
        elif key == 'Home' and bool(event.state & 0x0004):
            row_idx = 0
            col_idx = 0
        elif key == 'End' and bool(event.state & 0x0004):
            row_idx = len(rows) - 1
            col_idx = len(cols) - 1
        elif key == 'Prior':
            row_idx = max(0, row_idx - max(1, self._visible_row_count()))
        elif key == 'Next':
            row_idx = min(len(rows) - 1, row_idx + max(1, self._visible_row_count()))
        elif key == 'Home':
            col_idx = 0
        elif key == 'End':
            col_idx = len(cols) - 1

        self.select(rows[row_idx], cols[col_idx], ensure_visible=True)
        return 'break'

    def select(self, row_id, col_name, ensure_visible=False):
        if not row_id or not self.tree.exists(row_id):
            self.clear()
            return
        self.tree._active_cell = (row_id, col_name)
        try:
            self.tree.focus_set()
            self.tree.focus(row_id)
            self.tree.selection_set(row_id)
        except Exception:
            pass
        if ensure_visible:
            self._ensure_visible(row_id, col_name)
        self.render()

    def render(self):
        active = getattr(self.tree, '_active_cell', None)
        if not active:
            self.label.place_forget()
            return
        row_id, col_name = active
        if not self.tree.exists(row_id):
            self.clear()
            return
        text = str(self.tree.set(row_id, col_name) or '')
        heading = self.tree.heading(col_name).get('text') or col_name
        self.tree._active_cell_heading = heading
        self.tree._active_cell_value = text
        try:
            bbox = self.tree.bbox(row_id, col_name)
        except Exception:
            bbox = ''
        if not bbox:
            self.label.place_forget()
            return
        x, y, width, height = bbox
        self.label.configure(text=text, font=('Segoe UI', 10))
        self.label.place(x=x + 1, y=y + 1, width=max(1, width - 2), height=max(1, height - 2))
        self.label.lift()

    def refresh_later(self):
        self.tree.after_idle(self.render)

    def _display_columns(self):
        display = self.tree['displaycolumns']
        if not display or display == ('#all',) or display == '#all':
            return list(self.tree['columns'])
        return [c for c in display if c in self.tree['columns']]

    def _visible_row_count(self):
        try:
            height = max(1, self.tree.winfo_height())
            rowheight = tkfont.Font(family="Segoe UI", size=10).metrics('linespace') + 14
            return max(1, height // max(1, rowheight))
        except Exception:
            return 10

    def _ensure_visible(self, row_id, col_name):
        try:
            self.tree.see(row_id)
        except Exception:
            pass
        self._ensure_column_visible(col_name)
        self.refresh_later()

    def _ensure_column_visible(self, col_name):
        cols = self._display_columns()
        if col_name not in cols:
            return
        widths = []
        for col in cols:
            try:
                widths.append(max(1, int(self.tree.column(col, 'width') or 1)))
            except Exception:
                widths.append(100)
        total_width = max(1, sum(widths))
        target_index = cols.index(col_name)
        target_left = sum(widths[:target_index])
        target_right = target_left + widths[target_index]
        visible_width = max(1, self.tree.winfo_width() - 4)
        try:
            current_left = int(self.tree.xview()[0] * total_width)
        except Exception:
            current_left = 0
        current_right = current_left + visible_width
        if target_left < current_left:
            self.tree.xview_moveto(max(0, target_left) / total_width)
        elif target_right > current_right:
            new_left = max(0, target_right - visible_width)
            self.tree.xview_moveto(min(1, new_left / total_width))

    def clear(self):
        self.tree._active_cell = None
        self.tree._active_cell_heading = ''
        self.tree._active_cell_value = ''
        self.label.place_forget()


def enable_tree_cell_selection(tree, hscrollbar=None, vscrollbar=None):
    if not hasattr(tree, '_cell_selector'):
        tree._cell_selector = TreeCellSelector(tree)
    if not hasattr(tree, '_cell_tooltip'):
        tree._cell_tooltip = TreeCellTooltip(tree)

    if vscrollbar is not None and not getattr(vscrollbar, '_cell_selection_wrapped', False):
        def _yview(*args, tr=tree):
            tr.yview(*args)
            tr._cell_selector.refresh_later()
        vscrollbar.configure(command=_yview)
        vscrollbar._cell_selection_wrapped = True

    if hscrollbar is not None and not getattr(hscrollbar, '_cell_selection_wrapped', False):
        def _xview(*args, tr=tree):
            tr.xview(*args)
            tr._cell_selector.refresh_later()
        hscrollbar.configure(command=_xview)
        hscrollbar._cell_selection_wrapped = True

    return tree


class GlassCard(tk.Frame):
    """Modern card with glassmorphism effect — rounded corners, shadow, hover accent."""

    def __init__(self, master=None, **kwargs):
        self._accent_color = kwargs.pop('accent', COLORS['primary'])
        self._hover_color = kwargs.pop('hover', None)
        self._elevation = kwargs.pop('elevation', 2)
        super().__init__(master=master, bg='white', **kwargs)
        self._build()

    def _build(self):
        self.config(relief='flat', bd=0, highlightthickness=0)
        self.config(padx=0, pady=0)
        # Accent top stripe
        self.accent_bar = tk.Frame(self, bg=self._accent_color, height=4)
        self.accent_bar.pack(fill='x')
        # Content area
        self.content = tk.Frame(self, bg='white', padx=16, pady=12)
        self.content.pack(fill='both', expand=True)
        # Bind hover effect
        if self._hover_color:
            self._bind_hover()

    def _bind_hover(self):
        def on_enter(e):
            self.configure(bg=self._hover_color)
            self.content.configure(bg=self._hover_color)
            for w in self.content.winfo_children():
                try:
                    if isinstance(w, (tk.Label, tk.Frame)):
                        w.configure(bg=self._hover_color)
                except Exception:
                    pass
        def on_leave(e):
            self.configure(bg='white')
            self.content.configure(bg='white')
            for w in self.content.winfo_children():
                try:
                    if isinstance(w, (tk.Label, tk.Frame)):
                        w.configure(bg='white')
                except Exception:
                    pass
        self.bind('<Enter>', on_enter)
        self.bind('<Leave>', on_leave)
        self.content.bind('<Enter>', on_enter)
        self.content.bind('<Leave>', on_leave)
        self.accent_bar.bind('<Enter>', on_enter)
        self.accent_bar.bind('<Leave>', on_leave)

    def set_content_bg(self, color):
        """Change background of card and content area."""
        self.configure(bg=color)
        self.content.configure(bg=color)


class PropertyTemplateBar(tk.Frame):
    """Quick-fill property type template buttons."""

    def __init__(self, master=None, form_entries=None, **kwargs):
        self._form_entries = form_entries or {}
        super().__init__(master=master, bg=COLORS['bg'], **kwargs)
        self._build()

    def _build(self):
        tk.Label(self, text="🏷️ Quick Templates:", bg=COLORS['bg'],
                 fg=COLORS['secondary'], font=('Segoe UI', 8, 'bold')).pack(anchor='w', padx=2, pady=(0, 4))
        row = tk.Frame(self, bg=COLORS['bg'])
        row.pack(fill='x')
        templates = [
            ("Apartment", {'property_requires': 'flat', 'size': 'double-bed', 'floor': '3rd'}),
            ("Shop",  {'property_requires': 'shop', 'size': 'ground floor', 'floor': 'Ground'}),
            ("House", {'property_requires': 'banglow', 'size': 'single story', 'floor': 'Ground'}),
            ("Office",{'property_requires': 'office', 'size': 'any floor', 'floor': '1st'}),
            ("Plot",  {'property_requires': 'plot', 'size': 'any floor', 'floor': '-'}),
            ("Villa", {'property_requires': 'villa', 'size': 'double story', 'floor': 'Ground'}),
        ]
        for label, vals in templates:
            btn = tk.Button(row, text=label, font=('Segoe UI', 8),
                           bg=COLORS['light'], fg=COLORS['dark'],
                           relief='flat', padx=6, pady=2, cursor='hand2',
                           activebackground=COLORS['primary'],
                           activeforeground='white',
                           command=lambda v=vals: self._apply(v))
            btn.pack(side='left', padx=2, pady=2)

    def _apply(self, vals):
        if not self._form_entries:
            return
        for key, value in vals.items():
            widget_info = self._form_entries.get(key)
            if widget_info:
                widget, ftype, other_data = widget_info
                if ftype in ('combo', 'combo_other'):
                    widget.set(value)
                elif ftype == 'entry':
                    widget.delete(0, 'end')
                    widget.insert(0, value)

    def set_form_entries(self, entries):
        self._form_entries = entries


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CRM APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class RealEstateCRM:
    def __init__(self, root, current_user):
        self.root = root
        self.current_user = dict(current_user)
        self.role = self.current_user.get('role', UserRole.STAFF.value)
        if self._staff_restriction_applies(self.current_user):
            self.role = UserRole.STAFF.value
            self.current_user['role'] = self.role

        self.root.title(f"🏢 Professional Real Estate CRM — {self.current_user['full_name']} ({self.role})")
        set_app_icon(self.root)
        self.root.configure(bg=COLORS['bg'])
        self._responsive_after = None
        self._layout_profile = None
        self._dashboard_profile = None
        self._right_panel_visible = True
        self._fullscreen = False
        self._fullscreen_var = tk.BooleanVar(value=False)
        self._setup_main_window()

        self.currency_symbol = Settings.get('currency_symbol', 'Rs.')
        self.company_name = Settings.get('company_name')
        self.local_ip = self._get_local_ip()
        self.local_service_url = f"http://{self.local_ip}:{LOCAL_SERVICE_PORT}"
        self._api_server = None

        self._setup_styles()
        self._start_local_service()
        self._build_ui()
        self._setup_shortcuts()
        self.root.bind('<Configure>', self._schedule_responsive_layout, add='+')
        self.root.after_idle(self._apply_responsive_layout)
        self._refresh_all()

    def _setup_main_window(self):
        sw = max(1, self.root.winfo_screenwidth())
        sh = max(1, self.root.winfo_screenheight())
        min_w = min(960, max(760, sw - 160))
        min_h = min(640, max(500, sh - 180))
        self.root.minsize(min_w, min_h)
        fit_window_to_screen(
            self.root,
            preferred_w=1366,
            preferred_h=820,
            min_w=min_w,
            min_h=min_h,
            width_ratio=0.96,
            height_ratio=0.90,
        )
        try:
            self.root.state('zoomed')
        except Exception:
            pass

    def _set_fullscreen(self, enabled):
        enabled = bool(enabled)
        if enabled:
            try:
                self._pre_fullscreen_state = self.root.state()
                self._pre_fullscreen_geometry = self.root.geometry()
            except Exception:
                pass
        try:
            self.root.attributes('-fullscreen', enabled)
        except Exception:
            pass
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        try:
            actual = bool(self.root.attributes('-fullscreen'))
        except Exception:
            actual = False
        if enabled and not actual:
            try:
                sw = self.root.winfo_screenwidth()
                sh = self.root.winfo_screenheight()
                self.root.overrideredirect(True)
                self.root.geometry(f"{sw}x{sh}+0+0")
            except Exception:
                try:
                    self.root.state('zoomed')
                except Exception:
                    pass
        elif not enabled:
            try:
                self.root.overrideredirect(False)
            except Exception:
                pass
            try:
                if getattr(self, '_pre_fullscreen_state', '') == 'zoomed':
                    self.root.state('zoomed')
                else:
                    self.root.state('normal')
            except Exception:
                pass
        self._fullscreen = enabled
        try:
            self._fullscreen_var.set(enabled)
        except Exception:
            pass
        return 'break'

    def _toggle_fullscreen(self, event=None):
        try:
            current = bool(self.root.attributes('-fullscreen'))
        except Exception:
            current = self._fullscreen
        return self._set_fullscreen(not current)

    def _exit_fullscreen(self, event=None):
        if self._fullscreen:
            return self._set_fullscreen(False)
        return None

    def _schedule_responsive_layout(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        if self._responsive_after:
            try:
                self.root.after_cancel(self._responsive_after)
            except Exception:
                pass
        self._responsive_after = self.root.after(80, self._apply_responsive_layout)

    def _pack_widget(self, widget, show, **pack_opts):
        try:
            if show:
                if not widget.winfo_manager():
                    widget.pack(**pack_opts)
            else:
                if widget.winfo_manager():
                    widget.pack_forget()
        except Exception:
            pass

    def _apply_responsive_layout(self):
        self._responsive_after = None
        width = self.root.winfo_width() or self.root.winfo_screenwidth()
        if width >= 1240:
            profile = 'desktop'
        elif width >= 980:
            profile = 'medium'
        else:
            profile = 'compact'
        self._layout_profile = profile

        left_w = {'desktop': 200, 'medium': 170, 'compact': 148}[profile]
        show_right = width >= 1180
        if hasattr(self, '_left_sidebar_frame'):
            self._left_sidebar_frame.configure(width=left_w)
        if hasattr(self, '_right_panel_frame'):
            if show_right:
                if not self._right_panel_frame.winfo_manager():
                    self._right_panel_frame.grid(row=0, column=2, sticky='ns')
                self._right_panel_frame.configure(width=220 if profile == 'desktop' else 190)
            else:
                self._right_panel_frame.grid_remove()
            self._right_panel_visible = show_right

        if hasattr(self, '_main_content'):
            self._main_content.grid_columnconfigure(0, minsize=left_w, weight=0)
            self._main_content.grid_columnconfigure(1, weight=1)
            self._main_content.grid_columnconfigure(2, minsize=(220 if show_right else 0), weight=0)

        if hasattr(self, '_topbar_brand_label'):
            brand = f"🏢  {self.company_name}"
            if profile == 'medium':
                brand = f"🏢  {short_label(self.company_name, 22)}"
            elif profile == 'compact':
                brand = "🏢  CRM"
            self._topbar_brand_label.config(text=brand, font=('Segoe UI', 12 if profile == 'compact' else 14, 'bold'))
        if hasattr(self, '_topbar_network_frame'):
            self._pack_widget(self._topbar_network_frame, profile == 'desktop', side='right', padx=6)
        if hasattr(self, '_topbar_user_frame'):
            self._pack_widget(self._topbar_user_frame, profile != 'compact', side='right', padx=6)
        if hasattr(self, '_topbar_clock_lbl'):
            self._pack_widget(self._topbar_clock_lbl, profile == 'desktop', side='right', padx=8)

        for btn, full_text, short_text in getattr(self, '_nav_buttons', []):
            btn.configure(text=short_text if profile == 'compact' else full_text,
                          padx=8 if profile == 'compact' else 16,
                          font=('Segoe UI', 9 if profile == 'compact' else 10))

        if hasattr(self, 'nb'):
            for idx, labels in enumerate(getattr(self, '_notebook_labels', [])):
                full_text, compact_text = labels
                self.nb.tab(idx, text=compact_text if profile == 'compact' else full_text)
            pad = [6, 4] if profile == 'compact' else ([8, 5] if profile == 'medium' else [12, 5])
            self.style.configure('TNotebook.Tab',
                                 font=('Segoe UI', 8 if profile == 'compact' else 9, 'bold'),
                                 padding=pad)

        if profile != self._dashboard_profile and hasattr(self, 'dash_frame'):
            self._dashboard_profile = profile
            self.root.after_idle(self._build_dashboard_content)

    def _setup_styles(self):
        style = ttk.Style()
        self.style = style
        try:
            style.theme_use('clam')
        except Exception:
            pass

        # Global styles
        style.configure('TNotebook', background=COLORS['bg'])
        style.configure('TNotebook.Tab', font=('Segoe UI', 9, 'bold'), padding=[12, 5])
        
        style.configure('Treeview',
                        rowheight=34,
                        font=('Segoe UI', 10),
                        background='white',
                        fieldbackground='white',
                        foreground=COLORS['dark'])
        style.configure('Treeview.Heading',
                        font=('Segoe UI', 10, 'bold'),
                        background=COLORS['primary'],
                        foreground='white',
                        padding=(8, 7))
        style.map('Treeview',
                  background=[('selected', 'white')],
                  foreground=[('selected', COLORS['dark'])])
        
        style.configure('TLabel', font=('Segoe UI', 9), background=COLORS['bg'])
        style.configure('Form.TFrame', background='white')
        style.configure('Form.TLabel', font=('Segoe UI', 10, 'bold'), background='white', foreground=COLORS['dark'])
        style.configure('TEntry', padding=(6, 4))
        style.configure('TCombobox', padding=(6, 4))
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'), background=COLORS['primary'], foreground='white')
        style.configure('Card.TFrame', background='white', relief='flat')
        style.configure('TLabelframe', background=COLORS['bg'])
        style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'), foreground=COLORS['primary'], background=COLORS['bg'])

    def _autofit_columns(self, tree):
        """Adjust treeview column widths based on content."""
        font = tkfont.Font(family="Segoe UI", size=10)
        header_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        compact_cols = {'ID', '#', 'Beds', 'Year', 'Month'}
        long_cols = {
            'Name', 'Full Name', 'Title', 'Owner', 'Client', 'Contact', 'Phone',
            'Email', 'Location', 'Location / Match', 'Property Requires',
            'Property Availability', 'Facilities', 'Description', 'Remarks',
            'Notes', 'Admin Comment', 'Contact / Detail', 'Assigned'
        }
        money_cols = {
            'Budget', 'Rent', 'Demand', 'Deposit', 'Maintenance', 'Amount',
            'Value', 'Close Value', 'Salary', 'Base Salary', 'Net Salary',
            'Bonus', 'Deductions', 'Rent/Sale'
        }

        for col in tree['columns']:
            heading = tree.heading(col).get('text') or col
            try:
                current_width = int(tree.column(col, 'width') or 0)
            except Exception:
                current_width = 0
            if not tree.heading(col).get('text') and current_width == 0:
                tree.column(col, width=0, minwidth=0, stretch=False)
                continue
            max_w = header_font.measure(str(heading)) + 36
            for item in tree.get_children()[:250]:
                value = str(tree.set(item, col) or '').replace('\n', ' ')
                max_w = max(max_w, font.measure(value) + 34)

            if col in compact_cols:
                min_w, cap = 70, 90
            elif col in money_cols:
                min_w, cap = 120, 180
            elif col in long_cols:
                min_w, cap = 170, 680
            else:
                min_w, cap = 105, 320

            width = min(max(max_w, min_w), cap)
            tree.heading(col, anchor='w')
            tree.column(col, width=width, minwidth=min_w, anchor='w', stretch=False)
        self._stripe_tree(tree)

    def _stripe_tree(self, tree):
        """Apply alternating row colors without removing existing row tags."""
        try:
            tree.tag_configure('oddrow', background='#f8fafc')
            tree.tag_configure('evenrow', background='white')
            for idx, item in enumerate(tree.get_children()):
                tags = tuple(t for t in tree.item(item, 'tags') if t not in ('oddrow', 'evenrow'))
                tags += ('evenrow' if idx % 2 == 0 else 'oddrow',)
                tree.item(item, tags=tags)
        except Exception:
            pass


    # ─────────────────────────────────────────────────────────────────────────
    # TOP BAR
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_topbar()
        self._build_menubar()

        # Main content area with three-panel split layout
        self._main_content = tk.Frame(self.root, bg=COLORS['bg'])
        self._main_content.pack(fill='both', expand=True)
        self._main_content.grid_rowconfigure(0, weight=1)
        self._main_content.grid_columnconfigure(0, weight=0)
        self._main_content.grid_columnconfigure(1, weight=1)
        self._main_content.grid_columnconfigure(2, weight=0)

        # ── Left sidebar (workflow pipeline + nav) ──
        self._left_sidebar_frame = tk.Frame(self._main_content, bg=COLORS['sidebar'], width=200)
        self._left_sidebar_frame.grid(row=0, column=0, sticky='ns')
        self._left_sidebar_frame.grid_propagate(False)
        self._build_left_sidebar(self._left_sidebar_frame)

        # ── Center (main notebook content) ──
        self._center_frame = tk.Frame(self._main_content, bg=COLORS['bg'])
        self._center_frame.grid(row=0, column=1, sticky='nsew')
        self._build_notebook(self._center_frame)

        # ── Right panel (quick actions + AI) ──
        self._right_panel_frame = tk.Frame(self._main_content, bg='white', width=220)
        self._right_panel_frame.grid(row=0, column=2, sticky='ns')
        self._right_panel_frame.grid_propagate(False)
        self._build_right_panel(self._right_panel_frame)

    def _build_topbar(self):
        bar = tk.Frame(self.root, bg=COLORS['primary'], height=56)
        bar.pack(side='top', fill='x')
        bar.pack_propagate(False)

        # Company branding
        brand = tk.Frame(bar, bg=COLORS['primary'])
        brand.pack(side='left', fill='y', padx=16)
        self._topbar_brand_label = tk.Label(
            brand, text=f"🏢  {self.company_name}",
            bg=COLORS['primary'], fg='white',
            font=('Segoe UI', 14, 'bold')
        )
        self._topbar_brand_label.pack(side='left')
        self._topbar_crm_label = tk.Label(
            brand, text="CRM", bg=COLORS['primary'], fg='#93c5fd',
            font=('Segoe UI', 10, 'bold')
        )
        self._topbar_crm_label.pack(side='left', padx=(4, 0))

        # Right section
        right = tk.Frame(bar, bg=COLORS['primary'])
        right.pack(side='right', padx=12)

        # Notification / pending badge
        self.pending_lbl = None
        if not self._is_staff_restricted():
            self.pending_lbl = tk.Label(right, bg=COLORS['primary_dk'], fg='#fde68a',
                                        font=('Segoe UI', 9, 'bold'),
                                        padx=8, pady=2)
            self.pending_lbl.pack(side='right', padx=6)
            self._update_pending_badge()

        # Logout button
        logout_btn = tk.Button(right, text="⏻ Logout", font=('Segoe UI', 9),
                  bg='#dc2626', fg='white', relief='flat', cursor='hand2',
                  activebackground='#b91c1c', activeforeground='white',
                  command=self._logout, padx=10, pady=2)
        logout_btn.pack(side='right', padx=6)

        # User info
        self._topbar_user_frame = tk.Frame(right, bg=COLORS['primary'])
        self._topbar_user_frame.pack(side='right', padx=6)
        tk.Label(self._topbar_user_frame, text=f"👤 {self.current_user['full_name']}",
                 bg=COLORS['primary'], fg='white',
                 font=('Segoe UI', 9, 'bold')).pack(anchor='e')
        tk.Label(self._topbar_user_frame, text=f"[{self.role}]",
                 bg=COLORS['primary'], fg='#93c5fd',
                 font=('Segoe UI', 8)).pack(anchor='e')

        # Network status
        self._topbar_network_frame = tk.Frame(right, bg=COLORS['primary'])
        self._topbar_network_frame.pack(side='right', padx=6)
        tk.Label(self._topbar_network_frame, text=f"🌐 {self.local_service_url}",
                 bg=COLORS['primary'], fg='#bbf7d0',
                 font=('Segoe UI', 8, 'bold')).pack(anchor='e')

        # Clock
        self.clock_lbl = tk.Label(right, bg=COLORS['primary'], fg='#bfdbfe',
                                  font=('Segoe UI', 9))
        self._topbar_clock_lbl = self.clock_lbl
        self.clock_lbl.pack(side='right', padx=8)
        self._tick()

    def _tick(self):
        self.clock_lbl.config(text=datetime.now().strftime("📅 %d %b %Y   🕐 %H:%M:%S"))
        self.root.after(1000, self._tick)

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _start_local_service(self):
        app = self

        class CRMApiHandler(BaseHTTPRequestHandler):
            # Allowed tables for read/write operations
            ALLOWED_TABLES = {
                "rent_requirements", "rent_availability",
                "sale_requirements", "sale_availability",
                "income_transactions", "expense_transactions",
                "clients", "properties", "employees",
            }
            STAFF_TABLES = {
                "rent_requirements", "rent_availability",
                "sale_requirements", "sale_availability",
            }
            # Simple rate limiter per IP
            _rate_limit = {}

            def _allowed_tables(self):
                return self.STAFF_TABLES if app._is_staff_restricted() else self.ALLOWED_TABLES

            def _send(self, payload, status=200):
                body = json.dumps(payload, default=str).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                return

            def _check_rate_limit(self):
                client = self.client_address[0]
                now = datetime.now()
                # Prune stale entries older than 60 seconds to prevent unbounded dict growth
                stale = [ip for ip, (ts, _) in self._rate_limit.items()
                         if (now - ts).total_seconds() > 60]
                for ip in stale:
                    del self._rate_limit[ip]
                if client in self._rate_limit:
                    last, count = self._rate_limit[client]
                    if (now - last).total_seconds() < 1:
                        count += 1
                        if count > 30:  # max 30 requests/sec
                            return False
                    else:
                        count = 1
                    self._rate_limit[client] = (now, count)
                else:
                    self._rate_limit[client] = (now, 1)
                return True

            def _table_columns(self, table):
                cols = Database.execute(f"PRAGMA table_info({table})", fetch=True) or []
                return {c['name'] for c in cols}

            def _clean_payload(self, table, data, add_create_meta=False):
                columns = self._table_columns(table)
                cleaned = {k: v for k, v in data.items() if k in columns and k != "id"}
                unknown = sorted(k for k in data.keys() if k not in columns or k == "id")
                if add_create_meta:
                    if 'created_by' in columns and 'created_by' not in cleaned:
                        cleaned['created_by'] = app.current_user.get('username', 'api')
                    if 'created_at' in columns and 'created_at' not in cleaned:
                        cleaned['created_at'] = str(datetime.now())
                return cleaned, unknown

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
                self.end_headers()

            def do_GET(self):
                if not self._check_rate_limit():
                    self._send({"ok": False, "error": "rate limit exceeded"}, 429)
                    return
                parsed = self.path.split("?", 1)
                path = parsed[0]
                qs = parsed[1] if len(parsed) > 1 else ""
                from urllib.parse import parse_qs
                params = {k: v[-1] for k, v in parse_qs(qs).items()}

                if path in ("/", "/index"):
                    self._send({
                        "ok": True,
                        "service": "realestate-crm-api",
                        "version": "3.1",
                        "message": "Multi-user CRM API is running",
                        "routes": [
                            "/health",
                            "/meta",
                            "/users",
                            "/records/<table>",
                            "/records/<table>?limit=N&offset=N",
                            "/search?q=term",
                            "/stats",
                            "/pipeline?stage=Lead",
                        ],
                    })
                    return
                if path in ("/health", "/healthz"):
                    self._send({"ok": True, "service": "realestate-crm-api", "port": LOCAL_SERVICE_PORT})
                    return
                if path == "/meta":
                    self._send({
                        "company": app.company_name,
                        "user": app.current_user.get("full_name"),
                        "role": app.role,
                        "url": app.local_service_url,
                        "db_size": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
                    })
                    return
                if path == "/users":
                    if not has_permission(app.role, 'users'):
                        self._send({"ok": False, "error": "access denied"}, 403)
                        return
                    rows = Database.execute("SELECT id, username, full_name, email, role, is_active, last_login FROM users ORDER BY id", fetch=True) or []
                    self._send({"ok": True, "users": [dict(r) for r in rows]})
                    return
                if path == "/stats":
                    stats = {}
                    for t in self._allowed_tables():
                        r = Database.execute(f"SELECT COUNT(*) c FROM {t}", fetch=True)
                        stats[t] = r[0]['c'] if r else 0
                    self._send({"ok": True, "stats": stats})
                    return
                if path == "/pipeline":
                    stage = params.get("stage") or None
                    if stage and stage not in DEAL_STAGES:
                        self._send({"ok": False, "error": f"invalid stage. allowed: {DEAL_STAGES}"}, 400)
                        return
                    rows = app._pipeline_rows(stage)
                    self._send({
                        "ok": True,
                        "stage": stage or "All",
                        "count": len(rows),
                        "totals": app._get_pipeline_counts(),
                        "rows": rows,
                    })
                    return
                if path.startswith("/records/"):
                    table = path.replace("/records/", "", 1).strip().lower()
                    if table not in self._allowed_tables():
                        self._send({"ok": False, "error": f"invalid table. allowed: {sorted(self._allowed_tables())}"}, 400)
                        return
                    limit = min(int(params.get("limit", 500)), 2000)
                    offset = int(params.get("offset", 0))
                    total_count = Database.execute(f"SELECT COUNT(*) c FROM {table}", fetch=True)
                    total = total_count[0]['c'] if total_count else 0
                    rows = Database.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset), fetch=True) or []
                    data = [dict(r) for r in rows]
                    self._send({"ok": True, "table": table, "count": len(data), "total": total, "rows": data})
                    return
                if path.startswith("/search"):
                    q = params.get("q", "").strip().lower()
                    if len(q) < 1:
                        self._send({"ok": False, "error": "query param 'q' is required"}, 400)
                        return
                    results = []
                    pattern = f"%{q}%"
                    for table in self._allowed_tables():
                        try:
                            cols = Database.execute(f"PRAGMA table_info({table})", fetch=True) or []
                            col_names = [c['name'] for c in cols[:5]]
                            if not col_names:
                                continue
                            where_clause = " OR ".join(f"LOWER(COALESCE({c},'')) LIKE ?" for c in col_names)
                            label_col = col_names[0]
                            detail_col = col_names[1] if len(col_names) > 1 else "id"
                            sql = f"SELECT id, {label_col} AS label, {detail_col} AS detail FROM {table} WHERE {where_clause} LIMIT 20"
                            rows = Database.execute(sql, tuple([pattern]*len(col_names)), fetch=True) or []
                            for r in rows:
                                results.append({"table": table, "id": r['id'], "label": str(r['label'] or ''), "detail": str(r['detail'] or '')})
                        except Exception:
                            pass
                    self._send({"ok": True, "query": q, "count": len(results), "results": results})
                    return
                self._send({"ok": False, "error": "not found"}, 404)

            def do_POST(self):
                if not self._check_rate_limit():
                    self._send({"ok": False, "error": "rate limit exceeded"}, 429)
                    return
                path = self.path.split("?", 1)[0]
                if not path.startswith("/records/"):
                    self._send({"ok": False, "error": "POST only supported on /records/<table>"}, 400)
                    return
                table = path.replace("/records/", "", 1).strip().lower()
                if table not in self._allowed_tables():
                    self._send({"ok": False, "error": f"invalid table"}, 400)
                    return
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(length).decode('utf-8') if length else "{}"
                    data = json.loads(body)
                except Exception:
                    self._send({"ok": False, "error": "invalid JSON body"}, 400)
                    return
                if not data:
                    self._send({"ok": False, "error": "empty body"}, 400)
                    return
                data, unknown = self._clean_payload(table, data, add_create_meta=True)
                if unknown:
                    self._send({"ok": False, "error": f"unknown fields: {unknown}"}, 400)
                    return
                if not data:
                    self._send({"ok": False, "error": "no valid fields to save"}, 400)
                    return
                cols = ", ".join(data.keys())
                placeholders = ", ".join("?" for _ in data)
                vals = tuple(data.values())
                try:
                    new_id = Database.insert(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", vals)
                    self._send({"ok": True, "table": table, "id": new_id, "message": "record created"}, 201)
                except Exception as ex:
                    self._send({"ok": False, "error": str(ex)}, 500)

            def do_PUT(self):
                if not self._check_rate_limit():
                    self._send({"ok": False, "error": "rate limit exceeded"}, 429)
                    return
                path = self.path.split("?", 1)[0]
                parts = path.strip("/").split("/")
                if len(parts) != 3 or parts[0] != "records":
                    self._send({"ok": False, "error": "PUT requires /records/<table>/<id>"}, 400)
                    return
                table = parts[1].lower()
                if table not in self._allowed_tables():
                    self._send({"ok": False, "error": "invalid table"}, 400)
                    return
                try:
                    row_id = int(parts[2])
                except ValueError:
                    self._send({"ok": False, "error": "invalid id"}, 400)
                    return
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(length).decode('utf-8') if length else "{}"
                    data = json.loads(body)
                except Exception:
                    self._send({"ok": False, "error": "invalid JSON body"}, 400)
                    return
                if not data:
                    self._send({"ok": False, "error": "empty body"}, 400)
                    return
                data, unknown = self._clean_payload(table, data)
                if unknown:
                    self._send({"ok": False, "error": f"unknown fields: {unknown}"}, 400)
                    return
                if not data:
                    self._send({"ok": False, "error": "no valid fields to update"}, 400)
                    return
                set_clause = ", ".join(f"{k}=?" for k in data.keys())
                vals = tuple(data.values()) + (row_id,)
                try:
                    Database.execute(f"UPDATE {table} SET {set_clause} WHERE id=?", vals)
                    self._send({"ok": True, "table": table, "id": row_id, "message": "record updated"})
                except Exception as ex:
                    self._send({"ok": False, "error": str(ex)}, 500)

            def do_DELETE(self):
                if not self._check_rate_limit():
                    self._send({"ok": False, "error": "rate limit exceeded"}, 429)
                    return
                path = self.path.split("?", 1)[0]
                parts = path.strip("/").split("/")
                if len(parts) != 3 or parts[0] != "records":
                    self._send({"ok": False, "error": "DELETE requires /records/<table>/<id>"}, 400)
                    return
                table = parts[1].lower()
                if table not in self._allowed_tables():
                    self._send({"ok": False, "error": "invalid table"}, 400)
                    return
                try:
                    row_id = int(parts[2])
                except ValueError:
                    self._send({"ok": False, "error": "invalid id"}, 400)
                    return
                try:
                    Database.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
                    self._send({"ok": True, "table": table, "id": row_id, "message": "record deleted"})
                except Exception as ex:
                    self._send({"ok": False, "error": str(ex)}, 500)

        def _serve():
            try:
                self._api_server = ThreadingHTTPServer(("0.0.0.0", LOCAL_SERVICE_PORT), CRMApiHandler)
                self._api_server.serve_forever()
            except Exception as ex:
                print(f"Local API Error: {ex}")

        threading.Thread(target=_serve, daemon=True).start()

    def _update_pending_badge(self):
        if self._is_staff_restricted() or not getattr(self, 'pending_lbl', None):
            return
        tables = ['rent_requirements', 'rent_availability', 'sale_requirements', 'sale_availability']
        pending = 0
        for t in tables:
            r = Database.execute(f"SELECT COUNT(*) c FROM {t} WHERE approval_status='Pending'", fetch=True) or []
            pending += (r[0]['c'] if r else 0)
        self.pending_lbl.config(text=f"🛎 Pending Approvals: {pending}")
        self.root.after(10000, self._update_pending_badge)

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            try:
                if self._api_server:
                    self._api_server.shutdown()
                    self._api_server.server_close()
            except Exception:
                pass
            self.root.destroy()
            self._restart_app()

    def _restart_app(self):
        import subprocess, sys
        subprocess.Popen([sys.executable, __file__])

    # ─────────────────────────────────────────────────────────────────────────
    # LEFT SIDEBAR (workflow pipeline + navigation)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_left_sidebar(self, parent):
        """Compact navigation sidebar with workflow pipeline."""
        # Sidebar header
        hdr = tk.Frame(parent, bg=COLORS['sidebar'], height=50)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚡ NAVIGATION", bg=COLORS['sidebar'],
                 fg='white', font=('Segoe UI', 10, 'bold')).pack(pady=14)

        # Quick navigation buttons
        nav_items = [
            (label, compact_label, key)
            for key, label, compact_label, _builder in self._visible_tab_specs()
        ]
        self._nav_buttons = []
        for label, short_text, key in nav_items:
            btn = tk.Button(parent, text=label,
                           bg=COLORS['sidebar'], fg=COLORS['sidebar_txt'],
                           font=('Segoe UI', 10),
                           relief='flat', anchor='w', padx=16, pady=6,
                           cursor='hand2',
                           activebackground='#334155',
                           activeforeground='white',
                           command=lambda k=key: self._switch_tab(k))
            btn.pack(fill='x')
            self._nav_buttons.append((btn, label, short_text))
            # Hover effect
            def on_hover(e, b=btn):
                b.configure(bg='#334155', fg='white')
            def on_leave(e, b=btn):
                b.configure(bg=COLORS['sidebar'], fg=COLORS['sidebar_txt'])
            btn.bind('<Enter>', on_hover)
            btn.bind('<Leave>', on_leave)

        if self._is_staff_restricted():
            footer = tk.Frame(parent, bg=COLORS['sidebar'])
            footer.pack(side='bottom', fill='x', padx=12, pady=12)
            tk.Label(footer, text=f"🔑 {self.role}", bg=COLORS['sidebar'],
                    fg='#fde68a', font=('Segoe UI', 8, 'bold')).pack(anchor='w')
            return

        # Pipeline section separator
        sep = tk.Frame(parent, bg='#334155', height=1)
        sep.pack(fill='x', pady=10, padx=12)

        tk.Label(parent, text="📋 LEAD PIPELINE", bg=COLORS['sidebar'],
                 fg='#94a3b8', font=('Segoe UI', 8, 'bold')).pack(anchor='w', padx=16, pady=(0, 4))

        self.pipeline_buttons = {}
        counts = self._get_pipeline_counts()
        for step in DEAL_STAGES:
            btn = tk.Button(parent, text=f"{step}  ({counts.get(step, 0)})",
                            bg=COLORS['sidebar'], fg=COLORS['sidebar_txt'],
                            font=('Segoe UI', 9), relief='flat',
                            anchor='w', padx=16, pady=3,
                            cursor='hand2',
                            activebackground='#334155',
                            activeforeground='white',
                            command=lambda s=step: self._open_pipeline_board(s))
            btn.pack(fill='x', padx=12, pady=1)
            self.pipeline_buttons[step] = btn

        tk.Button(parent, text="Open Pipeline Board",
                  bg='#334155', fg='white',
                  font=('Segoe UI', 9, 'bold'), relief='flat',
                  anchor='w', padx=16, pady=5, cursor='hand2',
                  activebackground=COLORS['primary'],
                  activeforeground='white',
                  command=lambda: self._open_pipeline_board()).pack(fill='x', padx=12, pady=(6, 1))

        # Stats footer
        footer = tk.Frame(parent, bg=COLORS['sidebar'])
        footer.pack(side='bottom', fill='x', padx=12, pady=12)
        tk.Label(footer, text=f"🔑 {self.role}", bg=COLORS['sidebar'],
                fg='#fde68a', font=('Segoe UI', 8, 'bold')).pack(anchor='w')

    # ─────────────────────────────────────────────────────────────────────────
    # RIGHT PANEL (quick actions + AI)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_right_panel(self, parent):
        """Quick actions and AI suggestions panel."""
        hdr = tk.Frame(parent, bg=COLORS['primary'], height=40)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚡ QUICK ACTIONS", bg=COLORS['primary'],
                 fg='white', font=('Segoe UI', 9, 'bold')).pack(pady=10)

        inner = tk.Frame(parent, bg='white', padx=12, pady=12)
        inner.pack(fill='both', expand=True)

        # Quick action buttons
        actions = [
            ("➕  New Rent Requirement", self._add_rent_req, COLORS['primary']),
            ("🏠  New Rent Available",   self._add_rent_avail, COLORS['success']),
        ]
        if self._is_staff_restricted():
            actions += [
                ("➕  New Sale Requirement", self._add_sale_req, COLORS['primary']),
                ("🏠  New Sale Available",   self._add_sale_avail, COLORS['success']),
            ]
        else:
            actions += [
                ("💰  Add Income",      self._add_income, '#059669'),
                ("💸  Add Expense",     self._add_expense, '#dc2626'),
                ("🧑‍💼  Add Employee",   self._add_employee, '#0891b2'),
            ]
        for label, cmd, color in actions:
            btn = tk.Button(inner, text=label,
                           bg=color, fg='white',
                           font=('Segoe UI', 9, 'bold'),
                           relief='flat', padx=8, pady=6,
                           cursor='hand2',
                           activebackground=color,
                           activeforeground='white',
                           command=cmd)
            btn.pack(fill='x', pady=3)

        if self._is_staff_restricted():
            return

        # AI Assistant section
        sep = tk.Frame(inner, bg=COLORS['border'], height=1)
        sep.pack(fill='x', pady=12)

        tk.Label(inner, text="🤖 AI ASSISTANT",
                 bg='white', fg=COLORS['dark'],
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 6))

        tk.Label(inner, text="Select a record and click AI Match for smart property recommendations.",
                 bg='white', fg=COLORS['secondary'],
                 font=('Segoe UI', 8), wraplength=180, justify='left').pack(anchor='w', pady=(0, 8))

        tk.Button(inner, text="🤖  Run AI Match",
                  bg=COLORS['primary'], fg='white',
                  font=('Segoe UI', 9, 'bold'),
                  relief='flat', padx=8, pady=6,
                  cursor='hand2',
                  command=lambda: self._on_shortcut('ai_match')).pack(fill='x', pady=3)

        tk.Label(inner, text="💡 Keyboard Shortcuts",
                 bg='white', fg=COLORS['dark'],
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(12, 4))

        shortcuts_info = [
            "Ctrl+N  New Record",
            "Ctrl+S  Save",
            "Ctrl+F  Find",
            "Ctrl+E  Edit",
            "Ctrl+R  Refresh",
            "Alt+1-4 Switch Tab",
            "F11     Full Screen",
            "F5      Sync",
            "Esc     Full Screen Off / Close",
        ]
        for s in shortcuts_info:
            tk.Label(inner, text=s, bg='white', fg=COLORS['secondary'],
                    font=('Segoe UI', 8)).pack(anchor='w', pady=1)

    # ─────────────────────────────────────────────────────────────────────────
    # MENU BAR
    # ─────────────────────────────────────────────────────────────────────────

    def _build_menubar(self):
        mb = tk.Menu(self.root, bg=COLORS['light'],
                     activebackground=COLORS['primary'],
                     activeforeground='white', font=('Segoe UI', 9))
        self.root.config(menu=mb)

        fm = tk.Menu(mb, tearoff=0, bg='white', font=('Segoe UI', 9))
        mb.add_cascade(label="📁 File", menu=fm)
        if not self._is_staff_restricted():
            fm.add_command(label="📤 Export to CSV", command=self._export_csv)
            if has_permission(self.role, 'backup'):
                fm.add_command(label="💾 Backup Database", command=self._backup_db)
            fm.add_separator()
        fm.add_command(label="❌ Exit", command=self.root.quit)

        if not self._is_staff_restricted():
            em = tk.Menu(mb, tearoff=0, bg='white', font=('Segoe UI', 9))
            mb.add_cascade(label="✏️ Edit", menu=em)
            em.add_command(label="🔄 Refresh All", command=self._refresh_all)
            em.add_command(label="Find", command=self._quick_search)

        vm = tk.Menu(mb, tearoff=0, bg='white', font=('Segoe UI', 9))
        mb.add_cascade(label="👁️ View", menu=vm)
        for key, label, _compact, _builder in self._visible_tab_specs():
            vm.add_command(label=label, command=lambda k=key: self._switch_tab(k))

        vm.add_separator()
        vm.add_checkbutton(
            label="Full Screen On/Off (F11)",
            variable=self._fullscreen_var,
            command=lambda: self._set_fullscreen(self._fullscreen_var.get())
        )
        vm.add_command(label="Exit Full Screen (Esc)", command=lambda: self._set_fullscreen(False))

        if not self._is_staff_restricted():
            sm = tk.Menu(mb, tearoff=0, bg='white', font=('Segoe UI', 9))
            mb.add_cascade(label="⚙️ Settings", menu=sm)
            sm.add_command(label="🔐 Change My Password",  command=self._change_my_password)
            sm.add_separator()
            if has_permission(self.role, 'settings'):
                sm.add_command(label="🏢 Company Settings",  command=self._company_settings)
                sm.add_command(label="✅ Approval Center",     command=self._approval_center)
                sm.add_command(label="👥 User Management",     command=self._user_management)
                sm.add_command(label="🔑 Roles & Permissions", command=self._roles_info)

            hm = tk.Menu(mb, tearoff=0, bg='white', font=('Segoe UI', 9))
            mb.add_cascade(label="❓ Help", menu=hm)
            hm.add_command(label="📖 User Guide", command=self._user_guide)
            hm.add_command(label="ℹ️ About",      command=self._about)

    # ─────────────────────────────────────────────────────────────────────────
    # GLOBAL KEYBOARD SHORTCUTS
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        """Bind all global keyboard shortcuts (use filter to avoid conflicts in dialogs)."""
        def _bind(seq, cb):
            self.root.bind(seq, cb, add='+')
        _bind('<Control-n>',       lambda e: self._on_shortcut('new'))
        _bind('<Control-s>',       lambda e: self._on_shortcut('save'))
        _bind('<Control-f>',       lambda e: self._quick_search())
        _bind('<Control-e>',       lambda e: self._on_shortcut('edit'))
        _bind('<Control-d>',       lambda e: self._on_shortcut('delete'))
        _bind('<Control-r>',       lambda e: self._refresh_all())
        _bind('<Control-Shift-A>', lambda e: self._on_shortcut('ai_match'))
        _bind('<Control-Shift-R>', lambda e: self._on_shortcut('report'))
        _bind('<F11>',             self._toggle_fullscreen)
        self.root.bind_all('<F11>', self._toggle_fullscreen, add='+')
        self.root.bind_all('<Alt-Return>', self._toggle_fullscreen, add='+')
        _bind('<Alt-1>',           lambda e: self._switch_tab(0))
        _bind('<Alt-2>',           lambda e: self._switch_tab(1))
        _bind('<Alt-3>',           lambda e: self._switch_tab(2))
        _bind('<Alt-4>',           lambda e: self._switch_tab(3))
        _bind('<Escape>',          lambda e: self._on_shortcut('escape'))
        self.root.bind_all('<Escape>', lambda e: self._on_shortcut('escape'), add='+')
        _bind('<F5>',              lambda e: self._refresh_all())

    def _on_shortcut(self, action):
        """Dispatch keyboard shortcuts — figures out which tab/record is active."""
        current = self.nb.index(self.nb.select()) if hasattr(self, 'nb') else -1
        # Map action to the current context
        if action == 'new':
            current_tab_text = self.nb.tab(self.nb.select(), 'text') if current >= 0 else ''
            if 'Rent' in current_tab_text:
                self._add_rent_req() if hasattr(self, '_add_rent_req') else None
            elif 'Sale' in current_tab_text:
                self._add_sale_req() if hasattr(self, '_add_sale_req') else None
            else:
                self._quick_search()
        elif action == 'edit':
            self._quick_search()
        elif action == 'delete':
            messagebox.showinfo("Shortcut", "Select a record, then use Edit > Delete or right-click context menu.")
        elif action == 'ai_match':
            messagebox.showinfo("AI Match", "Select a record from any dealings tab and click the AI Match button.")
        elif action == 'report':
            for i, txt in enumerate(self.nb.tabs()):
                if 'Report' in self.nb.tab(i, 'text'):
                    self.nb.select(i)
                    return
        elif action == 'escape':
            if self._fullscreen:
                self._set_fullscreen(False)
                return
            for w in self.root.winfo_children():
                if isinstance(w, tk.Toplevel):
                    w.destroy()

    def _switch_tab(self, idx):
        """Switch notebook tab programmatically."""
        try:
            if isinstance(idx, str):
                idx = getattr(self, '_tab_index_by_key', {}).get(idx)
            if idx is None:
                return
            if hasattr(self, 'nb') and idx < len(self.nb.tabs()):
                self.nb.select(idx)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # NOTEBOOK TABS
    # ─────────────────────────────────────────────────────────────────────────

    def _staff_restriction_applies(self, user=None):
        user = user or self.current_user
        username = str(user.get('username', '')).strip().lower()
        role = str(user.get('role', '')).strip().lower()
        return role == UserRole.STAFF.value.lower() or username in {'staff', 'staf'}

    def _is_staff_restricted(self):
        return self._staff_restriction_applies(self.current_user)

    def _all_tab_specs(self):
        return [
            ('dashboard', "📊 Dashboard",       "📊 Dash", self._tab_dashboard),
            ('rent',      "🏠 Rent Dealings",   "🏠 Rent", self._tab_rent),
            ('sale',      "💲 Sale Dealings",   "💲 Sale", self._tab_sale),
            ('properties',"🏗️ Properties",     "🏗️ Props", self._tab_properties),
            ('clients',   "👥 Clients",         "👥 Clients", self._tab_clients),
            ('financials',"💰 Financials",      "💰 Finance", self._tab_financials),
            ('employees', "🧑‍💼 Employees",     "🧑‍💼 Staff", self._tab_employees),
            ('reports',   "📈 Reports",         "📈 Reports", self._tab_reports),
        ]

    def _visible_tab_specs(self):
        specs = self._all_tab_specs()
        if self._is_staff_restricted():
            return [spec for spec in specs if spec[0] in ('rent', 'sale')]
        return specs

    def _build_notebook(self, parent=None):
        if parent is None:
            parent = self.root
        self.nb = ttk.Notebook(parent)
        self.nb.pack(fill='both', expand=True, padx=8, pady=6)

        tabs = self._visible_tab_specs()
        self.frames = {}
        self._notebook_labels = []
        self._tab_index_by_key = {}
        self._tab_keys = []
        for key, label, compact_label, builder in tabs:
            f = ttk.Frame(self.nb)
            self.nb.add(f, text=label)
            self.frames[label] = f
            self._notebook_labels.append((label, compact_label))
            self._tab_index_by_key[key] = len(self._tab_keys)
            self._tab_keys.append(key)
            builder(f)

    # =========================================================================
    # TAB: DASHBOARD
    # =========================================================================

    def _tab_dashboard(self, parent):
        canvas = tk.Canvas(parent, bg=COLORS['bg'], highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        canvas.pack(fill='both', expand=True)

        self.dash_inner = tk.Frame(canvas, bg=COLORS['bg'])
        canvas_win = canvas.create_window((0, 0), window=self.dash_inner, anchor='nw')

        def on_config(e):
            canvas.configure(scrollregion=canvas.bbox('all'))
            canvas.itemconfig(canvas_win, width=canvas.winfo_width())
        self.dash_inner.bind('<Configure>', on_config)

        self.dash_frame = self.dash_inner
        self._build_dashboard_content()

    def _build_dashboard_content(self):
        if not hasattr(self, "dash_frame"):
            return
        for w in self.dash_frame.winfo_children():
            w.destroy()

        pad = {'padx': 16, 'pady': 8}

        greet_f = GlassCard(self.dash_frame, accent=COLORS['warning'], hover='#fffbeb')
        greet_f.pack(fill='x', **pad)
        now = datetime.now()
        hour = now.hour
        greet = "Good Morning" if hour < 12 else ("Good Afternoon" if hour < 17 else "Good Evening")
        inner = greet_f.content
        compact_dash = (self.root.winfo_width() or self.root.winfo_screenwidth()) < 980
        tk.Label(inner, text=f"{greet}, {self.current_user['full_name']}! 👋",
                 bg='white', fg=COLORS['dark'],
                 font=('Segoe UI', 14 if compact_dash else 16, 'bold')).pack(
            side='top' if compact_dash else 'left', anchor='w')
        tk.Label(inner, text=now.strftime("%A, %d %B %Y"),
                 bg='white', fg=COLORS['secondary'],
                 font=('Segoe UI', 10)).pack(side='top' if compact_dash else 'right',
                                             anchor='w' if compact_dash else 'e',
                                             pady=(4, 0) if compact_dash else 0)

        self._stat_row(self.dash_frame, [
            ("🏠 Rent Requirements",    self._count('rent_requirements'),  COLORS['primary'], "Open listings"),
            ("📍 Available Properties", self._count('rent_availability'),  COLORS['success'], "On market"),
            ("🏗️ Total Properties",    self._count('properties'),         '#7c3aed',         "Portfolio"),
            ("👥 Total Clients",        self._count('clients'),            COLORS['warning'],  "Registered"),
        ])

        self._stat_row(self.dash_frame, [
            ("💰 Total Income",
             f"{self.currency_symbol} {self._sum('income_transactions','amount'):,.0f}",
             COLORS['success'], "All time"),
            ("💸 Total Expenses",
             f"{self.currency_symbol} {self._sum('expense_transactions','amount'):,.0f}",
             COLORS['danger'], "All time"),
            ("📊 Net Profit",
             f"{self.currency_symbol} {self._sum('income_transactions','amount') - self._sum('expense_transactions','amount'):,.0f}",
             COLORS['primary'], "Income - Expenses"),
            ("🧑‍💼 Employees", self._count('employees'), '#0891b2', "Active staff"),
        ])

        cols = tk.Frame(self.dash_frame, bg=COLORS['bg'])
        cols.pack(fill='both', expand=True, padx=16, pady=8)
        cols.columnconfigure(0, weight=1)
        dashboard_width = self.root.winfo_width() or self.root.winfo_screenwidth()
        two_recent_columns = dashboard_width >= 1100
        cols.columnconfigure(1, weight=1 if two_recent_columns else 0)

        # Recent Rent Requirements — with glassmorphism card
        card1 = GlassCard(cols, accent=COLORS['primary'], hover='#f0f9ff')
        card1.grid(row=0, column=0, sticky='nsew',
                   padx=(0, 6) if two_recent_columns else 0, pady=4)
        inner1 = card1.content
        tk.Label(inner1, text="📝 Recent Rent Requirements",
                 bg='white', fg=COLORS['dark'],
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 6))
        t1 = self._mini_tree(inner1, ('Name', 'Location', 'Budget', 'Property Requires'))
        rows = Database.execute(
            "SELECT client_name, location, budget, property_requires FROM rent_requirements ORDER BY id DESC LIMIT 8",
            fetch=True) or []
        for r in rows:
            t1.insert('', 'end', values=(r['client_name'], r['location'],
                f"{self.currency_symbol}{r['budget']:,.0f}" if r['budget'] else '-',
                r['property_requires'] or '-'))

        # Recent Income Transactions — with glassmorphism card
        card2 = GlassCard(cols, accent=COLORS['success'], hover='#f0fdf4')
        card2.grid(row=0 if two_recent_columns else 1,
                   column=1 if two_recent_columns else 0,
                   sticky='nsew',
                   padx=(6, 0) if two_recent_columns else 0, pady=4)
        inner2 = card2.content
        tk.Label(inner2, text="💰 Recent Income Transactions",
                 bg='white', fg=COLORS['dark'],
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 6))
        t2 = self._mini_tree(inner2, ('Date', 'Type', 'Amount', 'Client'))
        rows2 = Database.execute(
            "SELECT transaction_date, income_type, amount, tenant_name FROM income_transactions ORDER BY id DESC LIMIT 8",
            fetch=True) or []
        for r in rows2:
            t2.insert('', 'end', values=(r['transaction_date'], r['income_type'],
                f"{self.currency_symbol}{r['amount']:,.0f}" if r['amount'] else '-',
                r['tenant_name'] or '-'))

    def _stat_row(self, parent, cards):
        row = tk.Frame(parent, bg=COLORS['bg'])
        row.pack(fill='x', padx=16, pady=4)
        width = self.root.winfo_width() or self.root.winfo_screenwidth()
        cols_per_row = 4 if width >= 1220 else (2 if width >= 820 else 1)
        for c in range(cols_per_row):
            row.columnconfigure(c, weight=1)
        for i, (label, val, color, sub) in enumerate(cards):
            grid_row = i // cols_per_row
            grid_col = i % cols_per_row
            card = GlassCard(row, accent=color, hover='#f8fafc')
            card.grid(row=grid_row, column=grid_col, padx=5, pady=4, sticky='ew')
            inner = card.content
            tk.Label(inner, text=str(label), bg='white', fg=COLORS['secondary'],
                     font=('Segoe UI', 9)).pack(anchor='w')
            tk.Label(inner, text=str(val), bg='white', fg=color,
                     font=('Segoe UI', 15 if width < 820 else 18, 'bold')).pack(anchor='w')
            tk.Label(inner, text=sub, bg='white', fg=COLORS['muted'],
                     font=('Segoe UI', 8)).pack(anchor='w')

    def _mini_tree(self, parent, cols):
        """Create a mini treeview with scrollbars for dashboard widgets."""
        # Main frame for tree + scrollbars
        tree_container = tk.Frame(parent, bg=COLORS['bg'], relief='sunken', bd=1)
        tree_container.pack(fill='both', expand=True, padx=5, pady=5)
        tree_container.grid_propagate(True)
        
        # Grid configuration for tree_container
        tree_container.grid_rowconfigure(0, weight=1)  # Tree row
        tree_container.grid_rowconfigure(1, weight=0)  # H-scrollbar row
        tree_container.grid_columnconfigure(0, weight=1)  # Tree column
        tree_container.grid_columnconfigure(1, weight=0)  # V-scrollbar column
        
        # Create treeview
        t = ttk.Treeview(tree_container, columns=cols, show='headings', height=8)
        for c in cols:
            t.heading(c, text=c)
            t.column(c, width=90)
        
        # Create and configure scrollbars
        vsb = ttk.Scrollbar(tree_container, orient='vertical', command=t.yview)
        hsb = ttk.Scrollbar(tree_container, orient='horizontal', command=t.xview)
        t.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Place tree and scrollbars in grid
        t.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        enable_tree_cell_selection(t, hsb, vsb)
        
        return t

    # =========================================================================
    # DEAL WORKFLOW / PIPELINE
    # =========================================================================

    def _normalize_stage(self, stage):
        stage = (stage or '').strip()
        return stage if stage in DEAL_STAGES else DEAL_STAGES[0]

    def _workflow_defaults(self, vals, value_key):
        stage = self._normalize_stage(vals.get('workflow_stage'))
        priority = vals.get('priority') if vals.get('priority') in DEAL_PRIORITIES else 'Medium'
        probability = safe_float(vals.get('deal_probability'), STAGE_PROBABILITY.get(stage, 10.0))
        if probability < 0:
            probability = STAGE_PROBABILITY.get(stage, 10.0)
        expected_value = safe_float(vals.get('expected_close_value'), 0)
        if expected_value <= 0:
            expected_value = safe_float(vals.get(value_key), 0)
        assigned_to = vals.get('assigned_to') or self.current_user.get('username', '')
        return (
            stage,
            priority,
            vals.get('next_follow_up', ''),
            assigned_to,
            probability,
            expected_value,
        )

    def _get_pipeline_counts(self):
        counts = {stage: 0 for stage in DEAL_STAGES}
        for table in DEAL_TABLES:
            rows = Database.execute(
                f"""SELECT COALESCE(NULLIF(workflow_stage,''), 'Lead') AS stage, COUNT(*) AS c
                    FROM {table}
                    GROUP BY COALESCE(NULLIF(workflow_stage,''), 'Lead')""",
                fetch=True) or []
            for r in rows:
                stage = self._normalize_stage(r['stage'])
                counts[stage] = counts.get(stage, 0) + (r['c'] or 0)
        return counts

    def _update_pipeline_counts(self):
        if not hasattr(self, 'pipeline_buttons'):
            return
        counts = self._get_pipeline_counts()
        for stage, btn in self.pipeline_buttons.items():
            try:
                btn.config(text=f"{stage}  ({counts.get(stage, 0)})")
            except Exception:
                pass

    def _pipeline_rows(self, stage=None):
        datasets = [
            ("Rent Req", "rent_requirements", "client_name", "contact", "property_requires", "budget"),
            ("Rent Av", "rent_availability", "owner_name", "contact", "property_availability", "monthly_rent"),
            ("Sale Req", "sale_requirements", "client_name", "contact", "property_requires", "budget"),
            ("Sale Av", "sale_availability", "owner_name", "contact", "property_availability", "demand"),
        ]
        results = []
        for source, table, name_col, contact_col, type_col, value_col in datasets:
            params = ()
            where = ""
            if stage:
                where = "WHERE COALESCE(NULLIF(workflow_stage,''), 'Lead')=?"
                params = (stage,)
            rows = Database.execute(
                f"""SELECT id, {name_col} AS name, {contact_col} AS contact, location,
                           {type_col} AS property_type, {value_col} AS amount,
                           workflow_stage, priority, next_follow_up, assigned_to,
                           deal_probability, expected_close_value
                    FROM {table}
                    {where}
                    ORDER BY
                        CASE priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END,
                        COALESCE(next_follow_up, '9999-12-31'),
                        id DESC""",
                params, fetch=True) or []
            for r in rows:
                results.append({
                    "source": source,
                    "table": table,
                    "id": r['id'],
                    "name": r['name'] or '',
                    "contact": r['contact'] or '',
                    "location": r['location'] or '',
                    "property_type": r['property_type'] or '',
                    "amount": r['expected_close_value'] or r['amount'] or 0,
                    "stage": self._normalize_stage(r['workflow_stage']),
                    "priority": r['priority'] or 'Medium',
                    "next_follow_up": r['next_follow_up'] or '',
                    "assigned_to": r['assigned_to'] or '',
                    "probability": r['deal_probability'] or STAGE_PROBABILITY.get(self._normalize_stage(r['workflow_stage']), 10.0),
                })
        return results

    def _open_pipeline_board(self, initial_stage=None):
        win = tk.Toplevel(self.root)
        win.title("Deal Pipeline")
        set_app_icon(win)
        fit_window_to_screen(win, 1120, 600, min_w=760, min_h=420)
        win.configure(bg=COLORS['bg'])

        top = tk.Frame(win, bg=COLORS['bg'])
        top.pack(fill='x', padx=10, pady=8)
        tk.Label(top, text="Deal Pipeline", bg=COLORS['bg'], fg=COLORS['dark'],
                 font=('Segoe UI', 14, 'bold')).pack(side='left')

        stage_var = tk.StringVar(value=initial_stage or "All")
        stage_combo = ttk.Combobox(top, values=["All"] + DEAL_STAGES, textvariable=stage_var,
                                   width=20, state='readonly')
        stage_combo.pack(side='right', padx=4)
        tk.Label(top, text="Stage:", bg=COLORS['bg'], fg=COLORS['secondary'],
                 font=('Segoe UI', 9, 'bold')).pack(side='right', padx=(0, 4))

        cols = ('Source', 'ID', 'Stage', 'Priority', 'Name', 'Contact', 'Location',
                'Type', 'Value', 'Probability', 'Next Follow-up', 'Assigned')
        frame = tk.Frame(win, bg=COLORS['bg'])
        frame.pack(fill='both', expand=True, padx=10, pady=(0, 8))
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=cols, show='headings', height=18)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=max(80, len(col) * 9), minwidth=70)
        tree.column('ID', width=60, stretch=False)
        tree.column('Name', width=160)
        tree.column('Value', width=110)
        tree.column('Next Follow-up', width=120)
        vsb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        enable_tree_cell_selection(tree, hsb, vsb)

        status_lbl = tk.Label(win, text="", bg=COLORS['bg'], fg=COLORS['secondary'],
                              font=('Segoe UI', 9))
        status_lbl.pack(fill='x', padx=10, pady=(0, 8))

        def load():
            tree.delete(*tree.get_children())
            stage = None if stage_var.get() == "All" else stage_var.get()
            rows = self._pipeline_rows(stage)
            total_value = 0
            for row in rows:
                total_value += safe_float(row['amount'])
                tree.insert('', 'end', values=(
                    row['source'], row['id'], row['stage'], row['priority'],
                    row['name'], row['contact'], row['location'], row['property_type'],
                    f"{self.currency_symbol}{safe_float(row['amount']):,.0f}",
                    f"{safe_float(row['probability']):.0f}%",
                    row['next_follow_up'], row['assigned_to'],
                ), tags=(row['table'],))
            status_lbl.config(
                text=f"{len(rows)} record(s), expected close value {self.currency_symbol}{total_value:,.0f}"
            )

        def selected_table_row():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a pipeline record first", parent=win)
                return None, None
            table = tree.item(sel[0], 'tags')[0]
            row_id = tree.item(sel[0])['values'][1]
            return table, row_id

        def edit_selected():
            table, row_id = selected_table_row()
            if not table:
                return
            self._workflow_form(table, row_id, on_done=load, parent=win)

        def advance_selected():
            table, row_id = selected_table_row()
            if not table:
                return
            self._advance_workflow_record(table, row_id)
            load()

        ctrl = tk.Frame(win, bg=COLORS['bg'])
        ctrl.pack(fill='x', padx=10, pady=(0, 10))
        tk.Button(ctrl, text="Edit Workflow", command=edit_selected,
                  **self._btn_style('warning')).pack(side='left', padx=3)
        tk.Button(ctrl, text="Next Stage", command=advance_selected,
                  **self._btn_style('success')).pack(side='left', padx=3)
        tk.Button(ctrl, text="Refresh", command=load,
                  **self._btn_style()).pack(side='left', padx=3)

        stage_combo.bind("<<ComboboxSelected>>", lambda _e: load())
        tree.bind('<Double-1>', lambda _e: edit_selected())
        load()

    def _workflow_form(self, table, row_id, on_done=None, parent=None):
        if table not in DEAL_TABLES:
            messagebox.showerror("Workflow", "Workflow is only available for deal records.")
            return
        rows = Database.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,), fetch=True) or []
        if not rows:
            messagebox.showwarning("Workflow", "Record not found.")
            return
        data = dict(rows[0])
        fields = [
            ("Workflow Stage", "workflow_stage", "combo", DEAL_STAGES),
            ("Priority", "priority", "combo", DEAL_PRIORITIES),
            ("Next Follow-up", "next_follow_up", "entry", data.get('next_follow_up') or ''),
            ("Assigned To", "assigned_to", "entry", data.get('assigned_to') or self.current_user.get('username', '')),
            ("Probability %", "deal_probability", "entry", str(data.get('deal_probability') or '')),
            ("Expected Value", "expected_close_value", "entry", str(data.get('expected_close_value') or '')),
        ]
        presets = {
            "workflow_stage": self._normalize_stage(data.get('workflow_stage')),
            "priority": data.get('priority') or 'Medium',
        }

        def save(vals):
            stage, priority, follow_up, assigned_to, probability, expected_value = self._workflow_defaults(
                vals, 'expected_close_value')
            closed_at = datetime.now() if stage == 'Deal Done' else data.get('closed_at')
            Database.execute(
                f"""UPDATE {table}
                    SET workflow_stage=?, priority=?, next_follow_up=?, assigned_to=?,
                        deal_probability=?, expected_close_value=?, closed_at=?
                    WHERE id=?""",
                (stage, priority, follow_up, assigned_to, probability, expected_value, closed_at, row_id))
            self._refresh_all()
            if on_done:
                on_done()

        self._generic_form("Deal Workflow", fields, save, parent=parent, presets=presets)

    def _workflow_selected(self, table, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a record first")
            return
        row_id = tree.item(sel[0])['values'][0]
        self._workflow_form(table, row_id)

    def _advance_workflow_record(self, table, row_id):
        rows = Database.execute(f"SELECT workflow_stage FROM {table} WHERE id=?", (row_id,), fetch=True) or []
        if not rows:
            return
        current = self._normalize_stage(rows[0]['workflow_stage'])
        idx = DEAL_STAGES.index(current)
        next_stage = DEAL_STAGES[min(idx + 1, len(DEAL_STAGES) - 1)]
        closed_at = datetime.now() if next_stage == 'Deal Done' else None
        Database.execute(
            f"""UPDATE {table}
                SET workflow_stage=?, deal_probability=?, last_contacted=?, closed_at=COALESCE(?, closed_at)
                WHERE id=?""",
            (next_stage, STAGE_PROBABILITY.get(next_stage, 10.0), datetime.now().strftime("%Y-%m-%d"), closed_at, row_id))
        self._refresh_all()

    def _advance_selected_workflow(self, table, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a record first")
            return
        row_id = tree.item(sel[0])['values'][0]
        self._advance_workflow_record(table, row_id)
        messagebox.showinfo("Workflow", f"Record #{row_id} moved to the next stage.")

    # =========================================================================
    # TAB: PROPERTY DEALINGS
    # =========================================================================

    # =========================================================================
    # TAB: RENT DEALINGS  (Requirements + Availability)
    # =========================================================================

    def _tab_rent(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        hdr = self._section_header(parent, "🏠 RENT DEALINGS")
        hdr.grid(row=0, column=0, sticky='ew', padx=0, pady=0)
        btn_frame = tk.Frame(hdr, bg=COLORS['primary'])
        btn_frame.pack(side='right', padx=4)
        if has_permission(self.role, 'rent'):
            tk.Button(btn_frame, text="➕ Add Requirement", command=self._add_rent_req,
                      **self._btn_style()).pack(side='left', padx=2)
            tk.Button(btn_frame, text="➕ Add Available Property", command=self._add_rent_avail,
                      **self._btn_style('success')).pack(side='left', padx=2)

        rent_nb = ttk.Notebook(parent)
        rent_nb.grid(row=1, column=0, sticky='nsew', padx=10, pady=6)

        # ── Rent Requirements ──────────────────────────────────────────────
        req_f = ttk.Frame(rent_nb)
        rent_nb.add(req_f, text="📝 Rent Requirements")
        req_f.grid_rowconfigure(0, weight=1)
        req_f.grid_columnconfigure(0, weight=1)
        self.rent_req_tree = self._make_tree(req_f,
            ('ID','Date','Name','Contact','Property Requires','Size','Measurement','Budget','Floor','Location',
             'Option 1','Option 2','Facilities','Client/Broker','Bachelor / Family','Remarks',
             'Stage','Priority','Next Follow-up','Assigned','Probability','Close Value',
             'Approval','Admin Comment'), row=0)
        try:
            self.rent_req_tree.heading('ID', text='')
            self.rent_req_tree.column('ID', width=0, minwidth=0, stretch=False)
        except Exception:
            pass
        self._load_rent_req()

        ctrl1 = tk.Frame(req_f, bg=COLORS['bg'])
        ctrl1.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        if has_permission(self.role, 'rent'):
            tk.Button(ctrl1, text="➕ Add", command=self._add_rent_req,
                      **self._btn_style()).pack(side='left', padx=3)
            tk.Button(ctrl1, text="✏️ Edit", command=self._edit_rent_req,
                      **self._btn_style('warning')).pack(side='left', padx=3)
            tk.Button(ctrl1, text="🗑️ Delete", command=lambda: self._delete_record(
                'rent_requirements', self.rent_req_tree),
                      **self._btn_style('danger')).pack(side='left', padx=3)
        tk.Button(ctrl1, text="🔄 Refresh", command=self._load_rent_req,
                  **self._btn_style()).pack(side='left', padx=3)
        tk.Button(ctrl1, text="🤖 AI Match", command=lambda: self._ai_match_selected('rent_requirements', self.rent_req_tree),
                  **self._btn_style('success')).pack(side='left', padx=3)
        tk.Button(ctrl1, text="Workflow", command=lambda: self._workflow_selected('rent_requirements', self.rent_req_tree),
                  **self._btn_style('warning')).pack(side='left', padx=3)
        tk.Button(ctrl1, text="Next Stage", command=lambda: self._advance_selected_workflow('rent_requirements', self.rent_req_tree),
                  **self._btn_style('success')).pack(side='left', padx=3)
        if self.role in ('Super Admin', 'Admin'):
            tk.Button(ctrl1, text="✅ Approve", command=lambda: self._set_approval_status('rent_requirements', self.rent_req_tree, 'Approved'),
                      **self._btn_style('success')).pack(side='left', padx=3)
            tk.Button(ctrl1, text="↩ Resend", command=lambda: self._set_approval_status('rent_requirements', self.rent_req_tree, 'Resend'),
                      **self._btn_style('warning')).pack(side='left', padx=3)
        tk.Button(ctrl1, text="📤 Export", command=lambda: self._export_tree(self.rent_req_tree, 'rent_requirements'),
                  **self._btn_style()).pack(side='left', padx=3)

        # ── Rent Availability ──────────────────────────────────────────────
        av_f = ttk.Frame(rent_nb)
        rent_nb.add(av_f, text="📍 Rent Availability")
        av_f.grid_rowconfigure(0, weight=1)
        av_f.grid_columnconfigure(0, weight=1)
        self.rent_av_tree = self._make_tree(av_f,
            ('ID','Date','Name','Contact','Property Availability','Size','Measurement','Rent','Floor','Location',
             'Deposit','Maintenance','Facilities','Client/Broker','Bachelor / Family','Remarks',
             'Stage','Priority','Next Follow-up','Assigned','Probability','Close Value',
             'Approval','Admin Comment'), row=0)
        try:
            self.rent_av_tree.heading('ID', text='')
            self.rent_av_tree.column('ID', width=0, minwidth=0, stretch=False)
        except Exception:
            pass
        self._load_rent_avail()

        ctrl2 = tk.Frame(av_f, bg=COLORS['bg'])
        ctrl2.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        if has_permission(self.role, 'rent'):
            tk.Button(ctrl2, text="➕ Add", command=self._add_rent_avail,
                      **self._btn_style()).pack(side='left', padx=3)
            tk.Button(ctrl2, text="✏️ Edit", command=self._edit_rent_avail,
                      **self._btn_style('warning')).pack(side='left', padx=3)
            tk.Button(ctrl2, text="🗑️ Delete", command=lambda: self._delete_record(
                'rent_availability', self.rent_av_tree),
                      **self._btn_style('danger')).pack(side='left', padx=3)
        tk.Button(ctrl2, text="🔄 Refresh", command=self._load_rent_avail,
                  **self._btn_style()).pack(side='left', padx=3)
        tk.Button(ctrl2, text="🤖 AI Match", command=lambda: self._ai_match_selected('rent_availability', self.rent_av_tree),
                  **self._btn_style('success')).pack(side='left', padx=3)
        tk.Button(ctrl2, text="Workflow", command=lambda: self._workflow_selected('rent_availability', self.rent_av_tree),
                  **self._btn_style('warning')).pack(side='left', padx=3)
        tk.Button(ctrl2, text="Next Stage", command=lambda: self._advance_selected_workflow('rent_availability', self.rent_av_tree),
                  **self._btn_style('success')).pack(side='left', padx=3)
        if self.role in ('Super Admin', 'Admin'):
            tk.Button(ctrl2, text="✅ Approve", command=lambda: self._set_approval_status('rent_availability', self.rent_av_tree, 'Approved'),
                      **self._btn_style('success')).pack(side='left', padx=3)
            tk.Button(ctrl2, text="↩ Resend", command=lambda: self._set_approval_status('rent_availability', self.rent_av_tree, 'Resend'),
                      **self._btn_style('warning')).pack(side='left', padx=3)
        tk.Button(ctrl2, text="📤 Export", command=lambda: self._export_tree(self.rent_av_tree, 'rent_availability'),
                  **self._btn_style()).pack(side='left', padx=3)

    # =========================================================================
    # TAB: SALE DEALINGS  (Requirements + Availability)
    # =========================================================================

    def _tab_sale(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        hdr = self._section_header(parent, "💲 SALE DEALINGS")
        hdr.grid(row=0, column=0, sticky='ew', padx=0, pady=0)
        btn_frame = tk.Frame(hdr, bg=COLORS['primary'])
        btn_frame.pack(side='right', padx=4)
        if has_permission(self.role, 'rent'):
            tk.Button(btn_frame, text="➕ Add Requirement", command=self._add_sale_req,
                      **self._btn_style()).pack(side='left', padx=2)
            tk.Button(btn_frame, text="➕ Add Available Property", command=self._add_sale_avail,
                      **self._btn_style('success')).pack(side='left', padx=2)

        sale_nb = ttk.Notebook(parent)
        sale_nb.grid(row=1, column=0, sticky='nsew', padx=10, pady=6)

        # ── Sale Requirements ──────────────────────────────────────────────
        sale_req_f = ttk.Frame(sale_nb)
        sale_nb.add(sale_req_f, text="📝 Sale Requirements")
        sale_req_f.grid_rowconfigure(0, weight=1)
        sale_req_f.grid_columnconfigure(0, weight=1)
        self.sale_req_tree = self._make_tree(sale_req_f,
            ('ID','Date','Name','Contact','Property Requires','Size','Measurement','Budget','Floor','Location',
             'Option 1','Option 2','Facilities','Client/Broker','Bachelor / Family','Remarks',
             'Stage','Priority','Next Follow-up','Assigned','Probability','Close Value',
             'Approval','Admin Comment'), row=0)
        try:
            self.sale_req_tree.heading('ID', text='')
            self.sale_req_tree.column('ID', width=0, minwidth=0, stretch=False)
        except Exception:
            pass
        self._load_sale_req()

        ctrl3 = tk.Frame(sale_req_f, bg=COLORS['bg'])
        ctrl3.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        if has_permission(self.role, 'rent'):
            tk.Button(ctrl3, text="➕ Add", command=self._add_sale_req,
                      **self._btn_style()).pack(side='left', padx=3)
            tk.Button(ctrl3, text="✏️ Edit", command=self._edit_sale_req,
                      **self._btn_style('warning')).pack(side='left', padx=3)
            tk.Button(ctrl3, text="🗑️ Delete", command=lambda: self._delete_record(
                'sale_requirements', self.sale_req_tree),
                      **self._btn_style('danger')).pack(side='left', padx=3)
        tk.Button(ctrl3, text="🔄 Refresh", command=self._load_sale_req,
                  **self._btn_style()).pack(side='left', padx=3)
        tk.Button(ctrl3, text="🤖 AI Match", command=lambda: self._ai_match_selected('sale_requirements', self.sale_req_tree),
                  **self._btn_style('success')).pack(side='left', padx=3)
        tk.Button(ctrl3, text="Workflow", command=lambda: self._workflow_selected('sale_requirements', self.sale_req_tree),
                  **self._btn_style('warning')).pack(side='left', padx=3)
        tk.Button(ctrl3, text="Next Stage", command=lambda: self._advance_selected_workflow('sale_requirements', self.sale_req_tree),
                  **self._btn_style('success')).pack(side='left', padx=3)
        if self.role in ('Super Admin', 'Admin'):
            tk.Button(ctrl3, text="✅ Approve", command=lambda: self._set_approval_status('sale_requirements', self.sale_req_tree, 'Approved'),
                      **self._btn_style('success')).pack(side='left', padx=3)
            tk.Button(ctrl3, text="↩ Resend", command=lambda: self._set_approval_status('sale_requirements', self.sale_req_tree, 'Resend'),
                      **self._btn_style('warning')).pack(side='left', padx=3)
        tk.Button(ctrl3, text="📤 Export", command=lambda: self._export_tree(self.sale_req_tree, 'sale_requirements'),
                  **self._btn_style()).pack(side='left', padx=3)

        # ── Sale Availability ──────────────────────────────────────────────
        sale_av_f = ttk.Frame(sale_nb)
        sale_nb.add(sale_av_f, text="🏷️ Sale Availability")
        sale_av_f.grid_rowconfigure(0, weight=1)
        sale_av_f.grid_columnconfigure(0, weight=1)
        self.sale_av_tree = self._make_tree(sale_av_f,
            ('ID','Date','Name','Contact','Property Availability','Size','Measurement','Demand','Floor','Location',
             'Option 1','Option 2','Facilities','Client/Broker','Bachelor / Family','Remarks',
             'Stage','Priority','Next Follow-up','Assigned','Probability','Close Value',
             'Approval','Admin Comment'), row=0)
        try:
            self.sale_av_tree.heading('ID', text='')
            self.sale_av_tree.column('ID', width=0, minwidth=0, stretch=False)
        except Exception:
            pass
        self._load_sale_avail()

        ctrl4 = tk.Frame(sale_av_f, bg=COLORS['bg'])
        ctrl4.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        if has_permission(self.role, 'rent'):
            tk.Button(ctrl4, text="➕ Add", command=self._add_sale_avail,
                      **self._btn_style()).pack(side='left', padx=3)
            tk.Button(ctrl4, text="✏️ Edit", command=self._edit_sale_avail,
                      **self._btn_style('warning')).pack(side='left', padx=3)
            tk.Button(ctrl4, text="🗑️ Delete", command=lambda: self._delete_record(
                'sale_availability', self.sale_av_tree),
                      **self._btn_style('danger')).pack(side='left', padx=3)
        tk.Button(ctrl4, text="🔄 Refresh", command=self._load_sale_avail,
                  **self._btn_style()).pack(side='left', padx=3)
        tk.Button(ctrl4, text="🤖 AI Match", command=lambda: self._ai_match_selected('sale_availability', self.sale_av_tree),
                  **self._btn_style('success')).pack(side='left', padx=3)
        tk.Button(ctrl4, text="Workflow", command=lambda: self._workflow_selected('sale_availability', self.sale_av_tree),
                  **self._btn_style('warning')).pack(side='left', padx=3)
        tk.Button(ctrl4, text="Next Stage", command=lambda: self._advance_selected_workflow('sale_availability', self.sale_av_tree),
                  **self._btn_style('success')).pack(side='left', padx=3)
        if self.role in ('Super Admin', 'Admin'):
            tk.Button(ctrl4, text="✅ Approve", command=lambda: self._set_approval_status('sale_availability', self.sale_av_tree, 'Approved'),
                      **self._btn_style('success')).pack(side='left', padx=3)
            tk.Button(ctrl4, text="↩ Resend", command=lambda: self._set_approval_status('sale_availability', self.sale_av_tree, 'Resend'),
                      **self._btn_style('warning')).pack(side='left', padx=3)
        tk.Button(ctrl4, text="📤 Export", command=lambda: self._export_tree(self.sale_av_tree, 'sale_availability'),
                  **self._btn_style()).pack(side='left', padx=3)

    def _load_rent_req(self):
        self.rent_req_tree.delete(*self.rent_req_tree.get_children())
        rows = Database.execute(
            """SELECT id,date,client_name,contact,property_requires,size,measurement,budget,floor,location,
                      option1,option2,facilities,client_broker,bachelor_family,remarks,
                      workflow_stage,priority,next_follow_up,assigned_to,deal_probability,expected_close_value,
                      approval_status,approval_comment
               FROM rent_requirements ORDER BY id DESC""",
            fetch=True) or []
        for r in rows:
            budget_val = r['budget']
            budget_txt = f"{self.currency_symbol}{budget_val:,.0f}" if budget_val is not None else '-'
            self.rent_req_tree.insert('', 'end', values=(
                r['id'],
                r['date'] or '',
                r['client_name'] or '',
                r['contact'] or '',
                r['property_requires'] or '',
                r['size'] or '',
                r['measurement'] or '',
                budget_txt,
                r['floor'] or '',
                r['location'] or '',
                r['option1'] or '',
                r['option2'] or '',
                r['facilities'] or '',
                r['client_broker'] or '',
                r['bachelor_family'] or '',
                r['remarks'] or '',
                self._normalize_stage(r['workflow_stage']),
                r['priority'] or 'Medium',
                r['next_follow_up'] or '',
                r['assigned_to'] or '',
                f"{safe_float(r['deal_probability']):.0f}%",
                f"{self.currency_symbol}{safe_float(r['expected_close_value']):,.0f}",
                                r['approval_status'] or 'Pending',
                r['approval_comment'] or '',
            ))
        self._autofit_columns(self.rent_req_tree)

    def _load_rent_avail(self):
        self.rent_av_tree.delete(*self.rent_av_tree.get_children())
        rows = Database.execute(
            """SELECT id,date,owner_name,contact,property_availability,size,measurement,monthly_rent,floor,location,
                      deposit,maintenance_charge,facilities,client_broker,bachelor_family,remarks,
                      workflow_stage,priority,next_follow_up,assigned_to,deal_probability,expected_close_value,
                      approval_status,approval_comment
               FROM rent_availability ORDER BY id DESC""",
            fetch=True) or []
        for r in rows:
            rent_val = r['monthly_rent']
            rent_txt = f"{self.currency_symbol}{rent_val:,.0f}" if rent_val is not None else '-'
            dep_val  = r['deposit']
            dep_txt  = f"{self.currency_symbol}{dep_val:,.0f}" if dep_val is not None else '-'
            m_val    = r['maintenance_charge']
            m_txt    = f"{self.currency_symbol}{m_val:,.0f}" if m_val is not None else '-'
            self.rent_av_tree.insert('', 'end', values=(
                r['id'],
                r['date'] or '',
                r['owner_name'] or '',
                r['contact'] or '',
                r['property_availability'] or '',
                r['size'] or '',
                r['measurement'] or '',
                rent_txt,
                r['floor'] or '',
                r['location'] or '',
                dep_txt,
                m_txt,
                r['facilities'] or '',
                r['client_broker'] or '',
                r['bachelor_family'] or '',
                r['remarks'] or '',
                self._normalize_stage(r['workflow_stage']),
                r['priority'] or 'Medium',
                r['next_follow_up'] or '',
                r['assigned_to'] or '',
                f"{safe_float(r['deal_probability']):.0f}%",
                f"{self.currency_symbol}{safe_float(r['expected_close_value']):,.0f}",
                                r['approval_status'] or 'Pending',
                r['approval_comment'] or '',
            ))
        self._autofit_columns(self.rent_av_tree)

    # ─────────────────────────────────────────────────────────────────────────
    # SALE REQUIREMENTS / AVAILABILITY (Excel-aligned)
    # ─────────────────────────────────────────────────────────────────────────
    def _load_sale_req(self):
        self.sale_req_tree.delete(*self.sale_req_tree.get_children())
        rows = Database.execute(
            """SELECT id,date,client_name,contact,property_requires,size,measurement,budget,floor,location,
                      option1,option2,facilities,client_broker,bachelor_family,remarks,
                      workflow_stage,priority,next_follow_up,assigned_to,deal_probability,expected_close_value,
                      approval_status,approval_comment
               FROM sale_requirements ORDER BY id DESC""",
            fetch=True) or []
        for r in rows:
            b = r['budget']
            btxt = f"{self.currency_symbol}{b:,.0f}" if b is not None else '-'
            self.sale_req_tree.insert('', 'end', values=(
                r['id'], r['date'] or '', r['client_name'] or '', r['contact'] or '',
                r['property_requires'] or '', r['size'] or '', r['measurement'] or '',
                btxt, r['floor'] or '', r['location'] or '',
                r['option1'] or '', r['option2'] or '',
                r['facilities'] or '', r['client_broker'] or '',
                r['bachelor_family'] or '', r['remarks'] or '',
                self._normalize_stage(r['workflow_stage']), r['priority'] or 'Medium',
                r['next_follow_up'] or '', r['assigned_to'] or '',
                f"{safe_float(r['deal_probability']):.0f}%",
                f"{self.currency_symbol}{safe_float(r['expected_close_value']):,.0f}",
                                r['approval_status'] or 'Pending', r['approval_comment'] or '',
            ))
        self._autofit_columns(self.sale_req_tree)

    def _add_sale_req(self):
        fields = [
            ("Date *",               "date",              "entry", datetime.now().strftime("%Y-%m-%d")),
            ("Name *",               "client_name",       "entry", ""),
            ("Contact",              "contact",           "entry", ""),
            ("Property Requires",    "property_requires", "combo_other",
             ['flat','banglow','shop','godam','plot','building','villa','house']),
            ("Size",                 "size",              "combo_other",
             ['single-bed','double-bed','any floor','ground floor','single story','double story','mezzanine','basement']),
            ("Measurement",          "measurement",       "entry", ""),
            ("Budget (Rs.)",         "budget",            "entry", ""),
            ("Floor",                "floor",             "entry", ""),
            ("Location *",           "location",          "autocomplete", COMMON_AREAS),
            ("Option 1",             "option1",           "entry", ""),
            ("Option 2",             "option2",           "entry", ""),
            ("Facilities",           "facilities",        "combo_multi",
             ['lift','car parking','cctv','security','sweet water','salty water','gas','electercity 24/7','electercity with loadshading']),
            ("Client / Broker",      "client_broker",     "entry", ""),
            ("Bachelor / Family",    "bachelor_family",   "entry", ""),
            ("Remarks",              "remarks",           "text",  ""),
        ]
        def save(vals):
            workflow = self._workflow_defaults(vals, 'budget')
            Database.execute(
                """INSERT INTO sale_requirements
                   (date,client_name,contact,property_requires,size,measurement,budget,floor,location,
                    option1,option2,facilities,client_broker,bachelor_family,remarks,
                    workflow_stage,priority,next_follow_up,assigned_to,deal_probability,expected_close_value,
                    approval_status,approval_comment,created_by,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (vals['date'], vals['client_name'], vals['contact'],
                 vals['property_requires'], vals['size'], vals['measurement'],
                 safe_float(vals['budget']),
                 vals['floor'], vals['location'],
                 vals['option1'], vals['option2'],
                 vals['facilities'], vals['client_broker'], vals['bachelor_family'], vals['remarks'],
                 *workflow,
                 'Pending', '',
                 self.current_user['username'], datetime.now()))
            self._load_sale_req()
            self._build_dashboard_content()
        self._generic_form("➕ Add Sale Requirement", fields, save, show_templates=True)

    def _edit_sale_req(self):
        sel = self.sale_req_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a record to edit")
            return
        row_id = self.sale_req_tree.item(sel[0])['values'][0]
        data = Database.execute("SELECT * FROM sale_requirements WHERE id=?", (row_id,), fetch=True)
        if not data:
            return
        d = dict(data[0])
        fields = [
            ("Date *",               "date",              "entry", d['date'] or ''),
            ("Name *",               "client_name",       "entry", d['client_name'] or ''),
            ("Contact",              "contact",           "entry", d['contact'] or ''),
            ("Property Requires",    "property_requires", "combo_other",
             ['flat','banglow','shop','godam','plot','building','villa','house']),
            ("Size",                 "size",              "combo_other",
             ['single-bed','double-bed','any floor','ground floor','single story','double story','mezzanine','basement']),
            ("Measurement",          "measurement",       "entry", d['measurement'] or ''),
            ("Budget (Rs.)",         "budget",            "entry", str(d['budget'] or '')),
            ("Floor",                "floor",                "entry", d['floor'] or ''),
            ("Location *",           "location",             "autocomplete", COMMON_AREAS),
            ("Option 1",             "option1",           "entry", d['option1'] or ''),
            ("Option 2",             "option2",           "entry", d['option2'] or ''),
            ("Facilities",           "facilities",        "combo_multi",
             ['lift','car parking','cctv','security','sweet water','salty water','gas','electercity 24/7','electercity with loadshading']),
            ("Client / Broker",      "client_broker",     "entry", d['client_broker'] or ''),
            ("Bachelor / Family",    "bachelor_family",   "entry", d['bachelor_family'] or ''),
            ("Remarks",              "remarks",           "text",  d['remarks'] or ''),
        ]
        pre = {
            'property_requires': d.get('property_requires'),
            'size': d.get('size'),
            'location': d.get('location'),
            'facilities': d.get('facilities'),
        }
        def save(vals):
            Database.execute(
                """UPDATE sale_requirements
                   SET date=?, client_name=?, contact=?, property_requires=?, size=?, measurement=?, budget=?,
                       floor=?, location=?, option1=?, option2=?, facilities=?, client_broker=?,
                       bachelor_family=?, remarks=?, approval_status='Pending', approval_comment=''
                   WHERE id=?""",
                (vals['date'], vals['client_name'], vals['contact'],
                 vals['property_requires'], vals['size'], vals['measurement'],
                 safe_float(vals['budget']),
                 vals['floor'], vals['location'],
                 vals['option1'], vals['option2'],
                 vals['facilities'], vals['client_broker'], vals['bachelor_family'], vals['remarks'],
                 row_id))
            self._load_sale_req()
        self._generic_form("✏️ Edit Sale Requirement", fields, save, presets=pre, show_templates=True)

    def _load_sale_avail(self):
        self.sale_av_tree.delete(*self.sale_av_tree.get_children())
        rows = Database.execute(
            """SELECT id,date,owner_name,contact,property_availability,size,measurement,demand,floor,location,
                      option1,option2,facilities,client_broker,bachelor_family,remarks,
                      workflow_stage,priority,next_follow_up,assigned_to,deal_probability,expected_close_value,
                      approval_status,approval_comment
               FROM sale_availability ORDER BY id DESC""",
            fetch=True) or []
        for r in rows:
            dmd = r['demand']
            dmdtxt = f"{self.currency_symbol}{dmd:,.0f}" if dmd is not None else '-'
            self.sale_av_tree.insert('', 'end', values=(
                r['id'], r['date'] or '', r['owner_name'] or '', r['contact'] or '',
                r['property_availability'] or '', r['size'] or '', r['measurement'] or '',
                dmdtxt, r['floor'] or '', r['location'] or '',
                r['option1'] or '', r['option2'] or '',
                r['facilities'] or '', r['client_broker'] or '',
                r['bachelor_family'] or '', r['remarks'] or '',
                self._normalize_stage(r['workflow_stage']), r['priority'] or 'Medium',
                r['next_follow_up'] or '', r['assigned_to'] or '',
                f"{safe_float(r['deal_probability']):.0f}%",
                f"{self.currency_symbol}{safe_float(r['expected_close_value']):,.0f}",
                                r['approval_status'] or 'Pending', r['approval_comment'] or '',
            ))
        self._autofit_columns(self.sale_av_tree)

    def _add_sale_avail(self):
        fields = [
            ("Date *",               "date",                 "entry", datetime.now().strftime("%Y-%m-%d")),
            ("Name *",               "owner_name",           "entry", ""),
            ("Contact",              "contact",              "entry", ""),
            ("Property Availability","property_availability","combo_other",
             ['flat','banglow','shop','godam','plot','building','villa','house']),
            ("Size",                 "size",                 "combo_other",
             ['single-bed','double-bed','any floor','ground floor','single story','double story','mezzanine','basement']),
            ("Measurement",          "measurement",          "combo_other",
             ['sqft box','yard box']),
            ("Demand (Rs.)",         "demand",               "entry", ""),
            ("Floor",                "floor",                "entry", ""),
            ("Location *",           "location",             "autocomplete", COMMON_AREAS),
            ("Option 1",             "option1",              "entry", ""),
            ("Option 2",             "option2",              "entry", ""),
            ("Facilities",           "facilities",           "combo_multi",
             ['lift','car parking','cctv','security','sweet water','salty water','gas','electercity 24/7','electercity with loadshading']),
            ("Client / Broker",      "client_broker",        "entry", ""),
            ("Bachelor / Family",    "bachelor_family",      "entry", ""),
            ("Remarks",              "remarks",              "text",  ""),
        ]
        def save(vals):
            workflow = self._workflow_defaults(vals, 'demand')
            Database.execute(
                """INSERT INTO sale_availability
                   (date,owner_name,contact,property_availability,size,measurement,demand,floor,location,
                    option1,option2,facilities,client_broker,bachelor_family,remarks,
                    workflow_stage,priority,next_follow_up,assigned_to,deal_probability,expected_close_value,
                    approval_status,approval_comment,created_by,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (vals['date'], vals['owner_name'], vals['contact'],
                 vals['property_availability'], vals['size'], vals['measurement'],
                 safe_float(vals['demand']),
                 vals['floor'], vals['location'],
                 vals['option1'], vals['option2'],
                 vals['facilities'], vals['client_broker'], vals['bachelor_family'], vals['remarks'],
                 *workflow,
                 'Pending', '',
                 self.current_user['username'], datetime.now()))
            self._load_sale_avail()
            self._build_dashboard_content()
        self._generic_form("➕ Add Sale Availability", fields, save, show_templates=True)

    def _edit_sale_avail(self):
        sel = self.sale_av_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a record to edit")
            return
        row_id = self.sale_av_tree.item(sel[0])['values'][0]
        data = Database.execute("SELECT * FROM sale_availability WHERE id=?", (row_id,), fetch=True)
        if not data:
            return
        d = dict(data[0])
        fields = [
            ("Date *",               "date",                 "entry", d['date'] or ''),
            ("Name *",               "owner_name",           "entry", d['owner_name'] or ''),
            ("Contact",              "contact",              "entry", d['contact'] or ''),
            ("Property Availability","property_availability","combo_other",
             ['flat','banglow','shop','godam','plot','building','villa','house']),
            ("Size",                 "size",                 "combo_other",
             ['single-bed','double-bed','any floor','ground floor','single story','double story','mezzanine','basement']),
            ("Measurement",          "measurement",          "combo_other",
             ['sqft box','yard box']),
            ("Demand (Rs.)",         "demand",               "entry", str(d['demand'] or '')),
            ("Floor",                "floor",                "entry", d['floor'] or ''),
            ("Location *",           "location",             "autocomplete", COMMON_AREAS),
            ("Option 1",             "option1",              "entry", d['option1'] or ''),
            ("Option 2",             "option2",              "entry", d['option2'] or ''),
            ("Facilities",           "facilities",           "combo_multi",
             ['lift','car parking','cctv','security','sweet water','salty water','gas','electercity 24/7','electercity with loadshading']),
            ("Client / Broker",      "client_broker",        "entry", d['client_broker'] or ''),
            ("Bachelor / Family",    "bachelor_family",      "entry", d['bachelor_family'] or ''),
            ("Remarks",              "remarks",              "text",  d['remarks'] or ''),
        ]
        pre = {
            'property_availability': d.get('property_availability'),
            'size': d.get('size'),
            'measurement': d.get('measurement'),
            'location': d.get('location'),
            'facilities': d.get('facilities'),
        }
        def save(vals):
            Database.execute(
                """UPDATE sale_availability
                   SET date=?, owner_name=?, contact=?, property_availability=?, size=?, measurement=?, demand=?,
                       floor=?, location=?, option1=?, option2=?, facilities=?, client_broker=?,
                       bachelor_family=?, remarks=?, approval_status='Pending', approval_comment=''
                   WHERE id=?""",
                (vals['date'], vals['owner_name'], vals['contact'],
                 vals['property_availability'], vals['size'], vals['measurement'],
                 safe_float(vals['demand']),
                 vals['floor'], vals['location'],
                 vals['option1'], vals['option2'],
                 vals['facilities'], vals['client_broker'], vals['bachelor_family'], vals['remarks'],
                 row_id))
            self._load_sale_avail()
        self._generic_form("✏️ Edit Sale Availability", fields, save, presets=pre, show_templates=True)

    # FIX: all _add_* and _edit_* methods now use plain def callbacks (not lambda tuples)

    def _add_rent_req(self):
        fields = [
            ("Date *",               "date",              "entry", datetime.now().strftime("%Y-%m-%d")),
            ("Name *",               "client_name",       "entry", ""),
            ("Contact",              "contact",           "entry", ""),
            ("Property Requires",    "property_requires", "combo_other",
             ['flat','banglow','shop','godam','plot','building','villa','house']),
            ("Size",                 "size",              "combo_other",
             ['single-bed','double-bed','any floor','ground floor','single story','double story','mezzanine','basement']),
            ("Measurement",          "measurement",       "entry", ""),
            ("Budget (Rs.)",         "budget",            "entry", ""),
            ("Floor",                "floor",             "entry", ""),
            ("Location *",           "location",          "autocomplete", COMMON_AREAS),
            ("Option 1",             "option1",           "entry", ""),
            ("Option 2",             "option2",           "entry", ""),
            ("Facilities",           "facilities",        "combo_multi",
             ['lift','car parking','cctv','security','sweet water','salty water','gas','electercity 24/7','electercity with loadshading']),
            ("Client / Broker",      "client_broker",     "entry", ""),
            ("Bachelor / Family",    "bachelor_family",   "entry", ""),
            ("Remarks",              "remarks",           "text",  ""),
        ]
        def save(vals):
            workflow = self._workflow_defaults(vals, 'budget')
            Database.execute(
                """INSERT INTO rent_requirements
                   (date,client_name,contact,property_requires,size,measurement,budget,floor,location,
                    option1,option2,facilities,client_broker,bachelor_family,remarks,
                    workflow_stage,priority,next_follow_up,assigned_to,deal_probability,expected_close_value,
                    approval_status,approval_comment,created_by,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (vals['date'],
                 vals['client_name'], vals['contact'],
                 vals['property_requires'], vals['size'], vals['measurement'],
                 safe_float(vals['budget']),
                 vals['floor'], vals['location'],
                 vals['option1'], vals['option2'],
                 vals['facilities'], vals['client_broker'],
                 vals['bachelor_family'], vals['remarks'],
                 *workflow,
                 'Pending', '',
                 self.current_user['username'], datetime.now()))
            self._load_rent_req()
            self._build_dashboard_content()
        self._generic_form("➕ Add Rent Requirement", fields, save, show_templates=True)

    def _edit_rent_req(self):
        sel = self.rent_req_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a record to edit")
            return
        row_id = self.rent_req_tree.item(sel[0])['values'][0]
        data = Database.execute("SELECT * FROM rent_requirements WHERE id=?", (row_id,), fetch=True)
        if not data:
            return
        d = dict(data[0])
        fields = [
            ("Date *",               "date",              "entry", d['date'] or ''),
            ("Name *",               "client_name",       "entry", d['client_name'] or ''),
            ("Contact",              "contact",           "entry", d['contact'] or ''),
            ("Property Requires",    "property_requires", "combo_other",
             ['flat','banglow','shop','godam','plot','building','villa','house']),
            ("Size",                 "size",              "combo_other",
             ['single-bed','double-bed','any floor','ground floor','single story','double story','mezzanine','basement']),
            ("Measurement",          "measurement",       "entry", d['measurement'] or ''),
            ("Budget (Rs.)",         "budget",            "entry", str(d.get('budget', '') or '')),
            ("Floor",                "floor",             "entry", d['floor'] or ''),
            ("Location *",           "location",          "autocomplete", COMMON_AREAS),
            ("Option 1",             "option1",           "entry", d['option1'] or ''),
            ("Option 2",             "option2",           "entry", d['option2'] or ''),
            ("Facilities",           "facilities",        "combo_multi",
             ['lift','car parking','cctv','security','sweet water','salty water','gas','electercity 24/7','electercity with loadshading']),
            ("Client / Broker",      "client_broker",     "entry", d.get('client_broker', '') or ''),
            ("Bachelor / Family",    "bachelor_family",   "entry", d.get('bachelor_family', '') or ''),
            ("Remarks",              "remarks",           "text",  d.get('remarks', '') or ''),
        ]
        pre = {
            'property_requires': d.get('property_requires'),
            'size': d.get('size'),
            'location': d.get('location'),
            'facilities': d.get('facilities'),
        }
        def save(vals):
            Database.execute(
                """UPDATE rent_requirements
                   SET date=?, client_name=?, contact=?, property_requires=?, size=?, measurement=?, budget=?,
                       floor=?, location=?, option1=?, option2=?, facilities=?, client_broker=?,
                       bachelor_family=?, remarks=?, approval_status='Pending', approval_comment=''
                   WHERE id=?""",
                (vals['date'], vals['client_name'], vals['contact'],
                 vals['property_requires'], vals['size'], vals['measurement'],
                 safe_float(vals['budget']),
                 vals['floor'], vals['location'],
                 vals['option1'], vals['option2'],
                 vals['facilities'], vals['client_broker'],
                 vals['bachelor_family'], vals['remarks'],
                 row_id))
            self._load_rent_req()
        self._generic_form("✏️ Edit Rent Requirement", fields, save, presets=pre, show_templates=True)

    def _add_rent_avail(self):
        fields = [
            ("Date *",               "date",                 "entry", datetime.now().strftime("%Y-%m-%d")),
            ("Name *",               "owner_name",           "entry", ""),
            ("Contact",              "contact",              "entry", ""),
            ("Property Availability","property_availability","combo_other",
             ['flat','banglow','shop','godam','plot','building','villa','house']),
            ("Size",                 "size",                 "combo_other",
             ['single-bed','double-bed','any floor','ground floor','single story','double story','mezzanine','basement']),
            ("Measurement",          "measurement",          "entry", ""),
            ("Rent (Rs.)",           "monthly_rent",         "entry", ""),
            ("Floor",                "floor",                "entry", ""),
            ("Location *",           "location",             "autocomplete", COMMON_AREAS),
            ("Deposit (Rs.)",        "deposit",              "entry", ""),
            ("Maintenance (Rs.)",    "maintenance_charge",   "entry", ""),
            ("Facilities",           "facilities",           "combo_multi",
             ['lift','car parking','cctv','security','sweet water','salty water','gas','electercity 24/7','electercity with loadshading']),
            ("Client / Broker",      "client_broker",        "entry", ""),
            ("Bachelor / Family",    "bachelor_family",      "entry", ""),
            ("Remarks",              "remarks",              "text",  ""),
        ]
        def save(vals):
            workflow = self._workflow_defaults(vals, 'monthly_rent')
            Database.execute(
                """INSERT INTO rent_availability
                   (date,owner_name,contact,property_availability,size,measurement,monthly_rent,floor,location,
                    deposit,maintenance_charge,facilities,client_broker,bachelor_family,remarks,
                    workflow_stage,priority,next_follow_up,assigned_to,deal_probability,expected_close_value,
                    approval_status,approval_comment,created_by,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (vals['date'],
                 vals['owner_name'], vals['contact'],
                 vals['property_availability'], vals['size'], vals['measurement'],
                 safe_float(vals['monthly_rent']),
                 vals['floor'], vals['location'],
                 safe_float(vals['deposit']),
                 safe_float(vals['maintenance_charge']),
                 vals['facilities'], vals['client_broker'],
                 vals['bachelor_family'], vals['remarks'],
                 *workflow,
                 'Pending', '',
                 self.current_user['username'], datetime.now()))
            self._load_rent_avail()
            self._build_dashboard_content()
        self._generic_form("➕ Add Available Property (Rent)", fields, save, show_templates=True)

    def _edit_rent_avail(self):
        sel = self.rent_av_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a record to edit")
            return
        row_id = self.rent_av_tree.item(sel[0])['values'][0]
        data = Database.execute("SELECT * FROM rent_availability WHERE id=?", (row_id,), fetch=True)
        if not data:
            return
        d = dict(data[0])
        fields = [
            ("Date *",               "date",                 "entry", d['date'] or ''),
            ("Name *",               "owner_name",           "entry", d['owner_name'] or ''),
            ("Contact",              "contact",              "entry", d['contact'] or ''),
            ("Property Availability","property_availability","combo_other",
             ['flat','banglow','shop','godam','plot','building','villa','house']),
            ("Size",                 "size",                 "combo_other",
             ['single-bed','double-bed','any floor','ground floor','single story','double story','mezzanine','basement']),
            ("Measurement",          "measurement",          "entry", d['measurement'] or ''),
            ("Rent (Rs.)",           "monthly_rent",         "entry", str(d['monthly_rent'] or '')),
            ("Floor",                "floor",                "entry", d['floor'] or ''),
            ("Location *",           "location",             "autocomplete", COMMON_AREAS),
            ("Deposit (Rs.)",        "deposit",              "entry", str(d.get('deposit') or '')),
            ("Maintenance (Rs.)",    "maintenance_charge",   "entry", str(d['maintenance_charge'] or '')),
            ("Facilities",           "facilities",           "combo_multi",
             ['lift','car parking','cctv','security','sweet water','salty water','gas','electercity 24/7','electercity with loadshading']),
            ("Client / Broker",      "client_broker",        "entry", d.get('client_broker') or ''),
            ("Bachelor / Family",    "bachelor_family",      "entry", d.get('bachelor_family') or ''),
            ("Remarks",              "remarks",              "text",  d.get('remarks') or ''),
        ]
        pre = {
            'property_availability': d.get('property_availability'),
            'size': d.get('size'),
            'location': d.get('location'),
            'facilities': d.get('facilities'),
        }
        def save(vals):
            Database.execute(
                """UPDATE rent_availability
                   SET date=?, owner_name=?, contact=?, property_availability=?, size=?, measurement=?,
                       monthly_rent=?, floor=?, location=?, deposit=?, maintenance_charge=?,
                       facilities=?, client_broker=?, bachelor_family=?, remarks=?, approval_status='Pending', approval_comment=''
                   WHERE id=?""",
                (vals['date'], vals['owner_name'], vals['contact'],
                 vals['property_availability'], vals['size'], vals['measurement'],
                 safe_float(vals['monthly_rent']),
                 vals['floor'], vals['location'],
                 safe_float(vals['deposit']),
                 safe_float(vals['maintenance_charge']),
                 vals['facilities'], vals['client_broker'], vals['bachelor_family'], vals['remarks'],
                 row_id))
            self._load_rent_avail()
        self._generic_form("✏️ Edit Available Property", fields, save, presets=pre, show_templates=True)

    # =========================================================================
    # APPROVALS + AI ASSIST
    # =========================================================================
    def _set_approval_status(self, table, tree, status):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a record first")
            return
        row_id = tree.item(sel[0])['values'][0]
        comment = ""
        if status == "Resend":
            comment = simpledialog.askstring("Resend with Comments",
                                             "Enter comment for user:",
                                             parent=self.root)
            if comment is None:
                return
            comment = comment.strip()
            if not comment:
                messagebox.showwarning("Required", "Comment is required for Resend")
                return
        Database.execute(
            f"""UPDATE {table}
                SET approval_status=?, approval_comment=?, approved_by=?, approved_at=?
                WHERE id=?""",
            (status, comment, self.current_user['username'], datetime.now(), row_id))
        self._refresh_all()
        messagebox.showinfo("Saved", f"Record #{row_id} marked as {status}")

    def _approval_center(self):
        win = tk.Toplevel(self.root)
        win.title("✅ Approval Center")
        set_app_icon(win)
        fit_window_to_screen(win, 980, 560, min_w=700, min_h=420)
        win.grab_set()

        tree = self._make_tree(win, ('Source', 'ID', 'Name', 'Location', 'Status', 'Comment'))

        def _load():
            tree.delete(*tree.get_children())
            datasets = [
                ("Rent Req", "rent_requirements", "client_name", "location"),
                ("Rent Av",  "rent_availability", "owner_name",  "location"),
                ("Sale Req", "sale_requirements", "client_name", "location"),
                ("Sale Av",  "sale_availability", "owner_name",  "location"),
            ]
            for src, table, name_col, loc_col in datasets:
                rows = Database.execute(
                    f"""SELECT id,{name_col} name,{loc_col} location,approval_status,approval_comment
                        FROM {table}
                        WHERE approval_status='Pending' OR approval_status='Resend'
                        ORDER BY id DESC""",
                    fetch=True) or []
                for r in rows:
                    tree.insert('', 'end', values=(src, r['id'], r['name'] or '', r['location'] or '',
                                                   r['approval_status'] or 'Pending', r['approval_comment'] or ''))
        _load()

        ctrl = tk.Frame(win, bg=COLORS['bg'])
        ctrl.pack(fill='x', padx=8, pady=6)

        def _selected_table():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a row")
                return None, None
            src, row_id = tree.item(sel[0])['values'][0], tree.item(sel[0])['values'][1]
            mapping = {'Rent Req': 'rent_requirements', 'Rent Av': 'rent_availability',
                       'Sale Req': 'sale_requirements', 'Sale Av': 'sale_availability'}
            return mapping.get(src), row_id

        def _approve():
            table, row_id = _selected_table()
            if not table:
                return
            Database.execute(
                f"UPDATE {table} SET approval_status='Approved', approval_comment='', approved_by=?, approved_at=? WHERE id=?",
                (self.current_user['username'], datetime.now(), row_id))
            _load()
            self._refresh_all()

        def _resend():
            table, row_id = _selected_table()
            if not table:
                return
            c = simpledialog.askstring("Resend", "Comment for user:", parent=win)
            if c is None:
                return
            c = c.strip()
            if not c:
                messagebox.showwarning("Required", "Comment is required")
                return
            Database.execute(
                f"UPDATE {table} SET approval_status='Resend', approval_comment=?, approved_by=?, approved_at=? WHERE id=?",
                (c, self.current_user['username'], datetime.now(), row_id))
            _load()
            self._refresh_all()

        tk.Button(ctrl, text="✅ Approve", command=_approve, **self._btn_style('success')).pack(side='left', padx=4)
        tk.Button(ctrl, text="↩ Resend w/ Comment", command=_resend, **self._btn_style('warning')).pack(side='left', padx=4)
        tk.Button(ctrl, text="🔄 Refresh", command=_load, **self._btn_style()).pack(side='left', padx=4)

    def _ai_match_selected(self, table, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select one row for AI matching")
            return
        row_id = tree.item(sel[0])['values'][0]
        matches = self._ai_find_matches(table, row_id)
        win = tk.Toplevel(self.root)
        win.title("🤖 AI Smart Match")
        set_app_icon(win)
        fit_window_to_screen(win, 760, 420, min_w=560, min_h=320)
        txt = scrolledtext.ScrolledText(win, font=('Consolas', 10), bg='white')
        txt.pack(fill='both', expand=True, padx=8, pady=8)
        txt.insert('1.0', matches)
        txt.config(state='disabled')

    def _ai_find_matches(self, table, row_id):
        if table == 'rent_requirements':
            q = Database.execute("SELECT * FROM rent_requirements WHERE id=?", (row_id,), fetch=True) or []
            if not q:
                return "No record found."
            r = q[0]
            rows = Database.execute(
                """SELECT id, owner_name, location, monthly_rent, property_availability
                   FROM rent_availability
                   WHERE LOWER(location)=LOWER(?) OR LOWER(property_availability)=LOWER(?)
                   ORDER BY ABS(COALESCE(monthly_rent,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (r['location'] or '', r['property_requires'] or '', r['budget'] or 0), fetch=True) or []
            out = [f"AI Match for Rent Requirement #{row_id} ({r['client_name'] or '-'})", "-"*70]
            for m in rows:
                out.append(f"Property #{m['id']} | {m['owner_name'] or '-'} | {m['location'] or '-'} | "
                           f"Type:{m['property_availability'] or '-'} | Rent:{self.currency_symbol}{(m['monthly_rent'] or 0):,.0f}")
            return "\n".join(out) if len(out) > 2 else "No close matches found."
        if table == 'sale_requirements':
            q = Database.execute("SELECT * FROM sale_requirements WHERE id=?", (row_id,), fetch=True) or []
            if not q:
                return "No record found."
            r = q[0]
            rows = Database.execute(
                """SELECT id, owner_name, location, demand, property_availability
                   FROM sale_availability
                   WHERE LOWER(location)=LOWER(?) OR LOWER(property_availability)=LOWER(?)
                   ORDER BY ABS(COALESCE(demand,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (r['location'] or '', r['property_requires'] or '', r['budget'] or 0), fetch=True) or []
            out = [f"AI Match for Sale Requirement #{row_id} ({r['client_name'] or '-'})", "-"*70]
            for m in rows:
                out.append(f"Listing #{m['id']} | {m['owner_name'] or '-'} | {m['location'] or '-'} | "
                           f"Type:{m['property_availability'] or '-'} | Demand:{self.currency_symbol}{(m['demand'] or 0):,.0f}")
            return "\n".join(out) if len(out) > 2 else "No close matches found."
        # Reverse matches from availability -> requirements
        if table == 'rent_availability':
            q = Database.execute("SELECT * FROM rent_availability WHERE id=?", (row_id,), fetch=True) or []
            if not q:
                return "No record found."
            r = q[0]
            rows = Database.execute(
                """SELECT id, client_name, location, budget, property_requires
                   FROM rent_requirements
                   WHERE LOWER(location)=LOWER(?) OR LOWER(property_requires)=LOWER(?)
                   ORDER BY ABS(COALESCE(budget,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (r['location'] or '', r['property_availability'] or '', r['monthly_rent'] or 0), fetch=True) or []
            out = [f"AI Match for Rent Availability #{row_id} ({r['owner_name'] or '-'})", "-"*70]
            for m in rows:
                out.append(f"Req #{m['id']} | {m['client_name'] or '-'} | {m['location'] or '-'} | "
                           f"Needs:{m['property_requires'] or '-'} | Budget:{self.currency_symbol}{(m['budget'] or 0):,.0f}")
            return "\n".join(out) if len(out) > 2 else "No close matches found."
        if table == 'sale_availability':
            q = Database.execute("SELECT * FROM sale_availability WHERE id=?", (row_id,), fetch=True) or []
            if not q:
                return "No record found."
            r = q[0]
            rows = Database.execute(
                """SELECT id, client_name, location, budget, property_requires
                   FROM sale_requirements
                   WHERE LOWER(location)=LOWER(?) OR LOWER(property_requires)=LOWER(?)
                   ORDER BY ABS(COALESCE(budget,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (r['location'] or '', r['property_availability'] or '', r['demand'] or 0), fetch=True) or []
            out = [f"AI Match for Sale Availability #{row_id} ({r['owner_name'] or '-'})", "-"*70]
            for m in rows:
                out.append(f"Req #{m['id']} | {m['client_name'] or '-'} | {m['location'] or '-'} | "
                           f"Needs:{m['property_requires'] or '-'} | Budget:{self.currency_symbol}{(m['budget'] or 0):,.0f}")
            return "\n".join(out) if len(out) > 2 else "No close matches found."
        return "AI matching is not configured for this dataset."

    # =========================================================================
    # TAB: PROPERTIES
    # =========================================================================

    def _tab_properties(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        hdr = self._section_header(parent, "🏗️ PROPERTY PORTFOLIO")
        hdr.grid(row=0, column=0, sticky='ew', padx=0, pady=0)
        if has_permission(self.role, 'rent'):
            tk.Button(hdr, text="➕ Add Property", command=self._add_property,
                      **self._btn_style()).pack(side='right', padx=4)

        props_frame = tk.Frame(parent, bg=COLORS['bg'])
        props_frame.grid(row=1, column=0, sticky='nsew', padx=8, pady=6)
        props_frame.grid_rowconfigure(0, weight=1)
        props_frame.grid_columnconfigure(0, weight=1)
        
        self.prop_tree = self._make_tree(props_frame,
            ('ID','Code','Title','Type','Status','Owner','Location','Rent/Sale','Maintenance'), row=0)
        self._load_properties()

        ctrl = tk.Frame(props_frame, bg=COLORS['bg'])
        ctrl.grid(row=1, column=0, sticky='ew', padx=0, pady=4)
        if has_permission(self.role, 'rent'):
            tk.Button(ctrl, text="✏️ Edit", command=self._edit_property,
                      **self._btn_style('warning')).pack(side='left', padx=3)
            tk.Button(ctrl, text="🗑️ Delete", command=lambda: self._delete_record(
                'properties', self.prop_tree),
                      **self._btn_style('danger')).pack(side='left', padx=3)
        tk.Button(ctrl, text="🔄 Refresh", command=self._load_properties,
                  **self._btn_style()).pack(side='left', padx=3)

    def _load_properties(self):
        self.prop_tree.delete(*self.prop_tree.get_children())
        rows = Database.execute(
            "SELECT id,property_code,title,property_type,status,owner_name,location,monthly_rent,maintenance_charge FROM properties ORDER BY id DESC",
            fetch=True) or []
        for r in rows:
            self.prop_tree.insert('', 'end', values=(
                r['id'], r['property_code'] or '', r['title'] or '',
                r['property_type'] or '', r['status'] or '',
                r['owner_name'] or '', r['location'] or '',
                                f"{self.currency_symbol}{r['monthly_rent']:,.0f}" if r['monthly_rent'] else '-',
                f"{self.currency_symbol}{r['maintenance_charge']:,.0f}" if r['maintenance_charge'] else '-'))
        self._autofit_columns(self.prop_tree)


    def _add_property(self):
        fields = [
            ("Property Code (Auto)", "property_code",      "entry", gen_id("PROP")),
            ("Title *",              "title",               "entry", ""),
            ("Type",                 "property_type",       "combo",
             ['Apartment','House','Villa','Studio','Shop','Office','Warehouse','Plot']),
            ("Status",               "status",              "combo",
             ['Available','Rented','Sold','Reserved']),
            ("Owner Name",           "owner_name",          "entry", ""),
            ("Owner Contact",        "owner_contact",       "entry", ""),
            ("Location *",           "location",            "autocomplete", COMMON_AREAS),
            ("Area (sqft)",          "area",                "entry", ""),
            ("Floor",                "floor",               "combo",
             ['Ground','1st','2nd','3rd','4th','5th','Top']),
            ("Monthly Rent",         "monthly_rent",        "entry", ""),
            ("Sale Price",           "sale_price",          "entry", ""),
            ("Maintenance",          "maintenance_charge",  "entry", ""),
            ("Facilities",           "facilities",          "entry", ""),
            ("Description",          "description",         "text",  ""),
        ]
        def save(vals):
            Database.execute(
                """INSERT INTO properties
                   (property_code,title,property_type,status,owner_name,owner_contact,
                    location,area,floor,monthly_rent,sale_price,maintenance_charge,
                    facilities,description,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (vals['property_code'], vals['title'], vals['property_type'],
                 vals['status'], vals['owner_name'], vals['owner_contact'],
                 vals['location'], vals['area'], vals['floor'],
                 safe_float(vals['monthly_rent']), safe_float(vals['sale_price']),
                 safe_float(vals['maintenance_charge']), vals['facilities'],
                 vals['description'], datetime.now()))
            self._load_properties()
            self._build_dashboard_content()
        self._generic_form("➕ Add Property", fields, save)

    def _edit_property(self):
        sel = self.prop_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a property to edit")
            return
        row_id = self.prop_tree.item(sel[0])['values'][0]
        data = Database.execute("SELECT * FROM properties WHERE id=?", (row_id,), fetch=True)
        if not data:
            return
        d = data[0]
        fields = [
            ("Property Code",        "property_code",      "entry", d['property_code'] or ''),
            ("Title *",              "title",               "entry", d['title'] or ''),
            ("Type",                 "property_type",       "combo",
             ['Apartment','House','Villa','Studio','Shop','Office','Warehouse','Plot']),
            ("Status",               "status",              "combo",
             ['Available','Rented','Sold','Reserved']),
            ("Owner Name",           "owner_name",          "entry", d['owner_name'] or ''),
            ("Owner Contact",        "owner_contact",       "entry", d['owner_contact'] or ''),
            ("Location *",           "location",            "autocomplete", COMMON_AREAS),
            ("Area (sqft)",          "area",                "entry", d['area'] or ''),
            ("Floor",                "floor",               "combo",
             ['Ground','1st','2nd','3rd','4th','5th','Top']),
            ("Monthly Rent",         "monthly_rent",        "entry", str(d['monthly_rent'] or '')),
            ("Sale Price",           "sale_price",          "entry", str(d['sale_price'] or '')),
            ("Maintenance",          "maintenance_charge",  "entry", str(d['maintenance_charge'] or '')),
            ("Facilities",           "facilities",          "entry", d['facilities'] or ''),
            ("Description",          "description",         "text",  d['description'] or ''),
        ]
        pre = {
            'property_type': d['property_type'],
            'status': d['status'],
            'location': d['location'],
            'floor': d['floor'],
        }
        def save(vals):
            Database.execute(
                """UPDATE properties SET title=?,property_type=?,status=?,owner_name=?,owner_contact=?,
                   location=?,area=?,floor=?,monthly_rent=?,sale_price=?,maintenance_charge=?,
                   facilities=?,description=? WHERE id=?""",
                (vals['title'], vals['property_type'], vals['status'],
                 vals['owner_name'], vals['owner_contact'], vals['location'],
                 vals['area'], vals['floor'],
                 safe_float(vals['monthly_rent']), safe_float(vals['sale_price']),
                 safe_float(vals['maintenance_charge']), vals['facilities'],
                 vals['description'], row_id))
            self._load_properties()
        self._generic_form("✏️ Edit Property", fields, save, presets=pre)

    # =========================================================================
    # TAB: CLIENTS
    # =========================================================================

    def _tab_clients(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        hdr = self._section_header(parent, "👥 CLIENT MANAGEMENT")
        hdr.grid(row=0, column=0, sticky='ew', padx=0, pady=0)
        if has_permission(self.role, 'rent'):
            tk.Button(hdr, text="➕ Add Client", command=self._add_client,
                      **self._btn_style()).pack(side='right', padx=4)

        clients_frame = tk.Frame(parent, bg=COLORS['bg'])
        clients_frame.grid(row=1, column=0, sticky='nsew', padx=8, pady=6)
        clients_frame.grid_rowconfigure(0, weight=1)
        clients_frame.grid_columnconfigure(0, weight=1)
        
        self.client_tree = self._make_tree(clients_frame,
            ('ID','Name','CNIC','Phone','Email','Type','Status'), row=0)
        self._load_clients()

        ctrl = tk.Frame(clients_frame, bg=COLORS['bg'])
        ctrl.grid(row=1, column=0, sticky='ew', padx=0, pady=4)
        if has_permission(self.role, 'rent'):
            tk.Button(ctrl, text="✏️ Edit", command=self._edit_client,
                      **self._btn_style('warning')).pack(side='left', padx=3)
            tk.Button(ctrl, text="🗑️ Delete", command=lambda: self._delete_record(
                'clients', self.client_tree),
                      **self._btn_style('danger')).pack(side='left', padx=3)
        tk.Button(ctrl, text="🔄 Refresh", command=self._load_clients,
                  **self._btn_style()).pack(side='left', padx=3)

    def _load_clients(self):
        self.client_tree.delete(*self.client_tree.get_children())
        rows = Database.execute(
            "SELECT id,client_name,cnic,phone,email,client_type,status FROM clients ORDER BY id DESC",
            fetch=True) or []
        for r in rows:
            self.client_tree.insert('', 'end', values=(
                r['id'], r['client_name'] or '', r['cnic'] or '',
                                r['phone'] or '', r['email'] or '',
                r['client_type'] or '', r['status'] or ''))
        self._autofit_columns(self.client_tree)


    def _add_client(self):
        fields = [
            ("Client Name *", "client_name", "entry", ""),
            ("CNIC",          "cnic",         "entry", ""),
            ("Phone",         "phone",        "entry", ""),
            ("Email",         "email",        "entry", ""),
            ("Address",       "address",      "text",  ""),
            ("Client Type",   "client_type",  "combo",
             ['Tenant','Buyer','Seller','Investor','Other']),
            ("Status",        "status",       "combo", ['Active','Inactive']),
            ("Notes",         "notes",        "text",  ""),
        ]
        def save(vals):
            Database.execute(
                """INSERT INTO clients
                   (client_name,cnic,phone,email,address,client_type,status,notes,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (vals['client_name'], vals['cnic'], vals['phone'], vals['email'],
                 vals['address'], vals['client_type'], vals['status'],
                 vals['notes'], datetime.now()))
            self._load_clients()
            self._build_dashboard_content()
        self._generic_form("➕ Add Client", fields, save)

    def _edit_client(self):
        sel = self.client_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a client to edit")
            return
        row_id = self.client_tree.item(sel[0])['values'][0]
        data = Database.execute("SELECT * FROM clients WHERE id=?", (row_id,), fetch=True)
        if not data:
            return
        d = data[0]
        fields = [
            ("Client Name *", "client_name", "entry", d['client_name'] or ''),
            ("CNIC",          "cnic",         "entry", d['cnic'] or ''),
            ("Phone",         "phone",        "entry", d['phone'] or ''),
            ("Email",         "email",        "entry", d['email'] or ''),
            ("Address",       "address",      "text",  d['address'] or ''),
            ("Client Type",   "client_type",  "combo",
             ['Tenant','Buyer','Seller','Investor','Other']),
            ("Status",        "status",       "combo", ['Active','Inactive']),
            ("Notes",         "notes",        "text",  d['notes'] or ''),
        ]
        pre = {'client_type': d['client_type'], 'status': d['status']}
        def save(vals):
            Database.execute(
                """UPDATE clients SET client_name=?,cnic=?,phone=?,email=?,address=?,
                   client_type=?,status=?,notes=? WHERE id=?""",
                (vals['client_name'], vals['cnic'], vals['phone'], vals['email'],
                 vals['address'], vals['client_type'], vals['status'],
                 vals['notes'], row_id))
            self._load_clients()
        self._generic_form("✏️ Edit Client", fields, save, presets=pre)

    # =========================================================================
    # TAB: FINANCIALS
    # =========================================================================

    def _tab_financials(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        hdr = self._section_header(parent, "💰 FINANCIAL MANAGEMENT")
        hdr.grid(row=0, column=0, sticky='ew', padx=0, pady=0)
        if has_permission(self.role, 'financial'):
            tk.Button(hdr, text="➕ Add Income", command=self._add_income,
                      **self._btn_style('success')).pack(side='right', padx=4)
            tk.Button(hdr, text="➕ Add Expense", command=self._add_expense,
                      **self._btn_style('danger')).pack(side='right', padx=4)

        fin_nb = ttk.Notebook(parent)
        fin_nb.grid(row=1, column=0, sticky='nsew', padx=10, pady=6)

        inc_f = ttk.Frame(fin_nb)
        fin_nb.add(inc_f, text="💰 Income")
        self._build_income_tab(inc_f)

        exp_f = ttk.Frame(fin_nb)
        fin_nb.add(exp_f, text="💸 Expenses")
        self._build_expense_tab(exp_f)

        sum_f = ttk.Frame(fin_nb)
        fin_nb.add(sum_f, text="📊 Summary")
        self._build_fin_summary(sum_f)

    def _build_income_tab(self, parent):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        tree_frame = tk.Frame(parent, bg=COLORS['bg'])
        tree_frame.grid(row=0, column=0, sticky='nsew', padx=8, pady=6)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        self.income_tree = self._make_tree(tree_frame,
            ('ID','Date','Type','Amount','Client','Description','Receipt No','Method'), row=0)
        self._load_income()
        
        ctrl = tk.Frame(parent, bg=COLORS['bg'])
        ctrl.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        if has_permission(self.role, 'financial'):
            tk.Button(ctrl, text="➕ Add",  command=self._add_income,
                      **self._btn_style('success')).pack(side='left', padx=3)
            tk.Button(ctrl, text="✏️ Edit", command=self._edit_income,
                      **self._btn_style('warning')).pack(side='left', padx=3)
            tk.Button(ctrl, text="🗑️ Delete", command=lambda: self._delete_record(
                'income_transactions', self.income_tree),
                      **self._btn_style('danger')).pack(side='left', padx=3)
        tk.Button(ctrl, text="🔄 Refresh", command=self._load_income,
                  **self._btn_style()).pack(side='left', padx=3)
        tk.Button(ctrl, text="📤 Export", command=lambda: self._export_tree(
            self.income_tree, 'income'), **self._btn_style()).pack(side='left', padx=3)

        self.income_total_lbl = tk.Label(parent, text="", bg=COLORS['income_bg'],
                                          fg=COLORS['success'],
                                          font=('Segoe UI', 11, 'bold'), pady=6)
        self.income_total_lbl.grid(row=2, column=0, sticky='ew', padx=8, pady=4)

    def _build_expense_tab(self, parent):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        tree_frame = tk.Frame(parent, bg=COLORS['bg'])
        tree_frame.grid(row=0, column=0, sticky='nsew', padx=8, pady=6)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        self.expense_tree = self._make_tree(tree_frame,
            ('ID','Date','Category','Amount','Vendor','Description','Invoice No','Method'), row=0)
        self._load_expenses()
        
        ctrl = tk.Frame(parent, bg=COLORS['bg'])
        ctrl.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        if has_permission(self.role, 'financial'):
            tk.Button(ctrl, text="➕ Add",  command=self._add_expense,
                      **self._btn_style('danger')).pack(side='left', padx=3)
            tk.Button(ctrl, text="✏️ Edit", command=self._edit_expense,
                      **self._btn_style('warning')).pack(side='left', padx=3)
            tk.Button(ctrl, text="🗑️ Delete", command=lambda: self._delete_record(
                'expense_transactions', self.expense_tree),
                      **self._btn_style('danger')).pack(side='left', padx=3)
        tk.Button(ctrl, text="🔄 Refresh", command=self._load_expenses,
                  **self._btn_style()).pack(side='left', padx=3)
        tk.Button(ctrl, text="📤 Export", command=lambda: self._export_tree(
            self.expense_tree, 'expenses'), **self._btn_style()).pack(side='left', padx=3)

        self.expense_total_lbl = tk.Label(parent, text="", bg=COLORS['expense_bg'],
                                           fg=COLORS['danger'],
                                           font=('Segoe UI', 11, 'bold'), pady=6)
        self.expense_total_lbl.grid(row=2, column=0, sticky='ew', padx=8, pady=4)

    def _build_fin_summary(self, parent):
        self.fin_sum_text = scrolledtext.ScrolledText(parent,
                                                       font=('Courier New', 10),
                                                       bg='white', fg=COLORS['dark'],
                                                       height=30)
        self.fin_sum_text.pack(fill='both', expand=True, padx=10, pady=10)
        ctrl = tk.Frame(parent, bg=COLORS['bg'])
        ctrl.pack(fill='x', padx=10, pady=4)
        tk.Button(ctrl, text="🔄 Refresh Summary", command=self._load_fin_summary,
                  **self._btn_style()).pack(side='left', padx=3)
        tk.Button(ctrl, text="📤 Export", command=self._export_fin_summary,
                  **self._btn_style()).pack(side='left', padx=3)
        self._load_fin_summary()

    def _load_income(self):
        self.income_tree.delete(*self.income_tree.get_children())
        rows = Database.execute(
            "SELECT id,transaction_date,income_type,amount,tenant_name,description,receipt_no,payment_method FROM income_transactions ORDER BY id DESC",
            fetch=True) or []
        total = 0
        for r in rows:
            amt = r['amount'] or 0
            total += amt
            self.income_tree.insert('', 'end', values=(
                r['id'], r['transaction_date'] or '', r['income_type'] or '',
                f"{self.currency_symbol}{amt:,.0f}",
                r['tenant_name'] or '', r['description'] or '',
                r['receipt_no'] or '', r['payment_method'] or ''))
        try:
            self.income_total_lbl.config(
                text=f"  Total Income:  {self.currency_symbol} {total:,.0f}")
        except Exception:
            pass
        self._autofit_columns(self.income_tree)


    def _load_expenses(self):
        self.expense_tree.delete(*self.expense_tree.get_children())
        rows = Database.execute(
            "SELECT id,transaction_date,expense_category,amount,vendor_name,description,invoice_no,payment_method FROM expense_transactions ORDER BY id DESC",
            fetch=True) or []
        total = 0
        for r in rows:
            amt = r['amount'] or 0
            total += amt
            self.expense_tree.insert('', 'end', values=(
                r['id'], r['transaction_date'] or '', r['expense_category'] or '',
                f"{self.currency_symbol}{amt:,.0f}",
                r['vendor_name'] or '', r['description'] or '',
                r['invoice_no'] or '', r['payment_method'] or ''))
        try:
            self.expense_total_lbl.config(
                text=f"  Total Expenses:  {self.currency_symbol} {total:,.0f}")
        except Exception:
            pass
        self._autofit_columns(self.expense_tree)


    def _load_fin_summary(self):
        income   = self._sum('income_transactions', 'amount')
        expenses = self._sum('expense_transactions', 'amount')
        profit   = income - expenses
        margin   = (profit / income * 100) if income > 0 else 0

        lines = [
            f"{'═'*60}",
            f"  FINANCIAL SUMMARY  —  {datetime.now().strftime('%d %B %Y')}",
            f"  Company: {self.company_name}",
            f"{'═'*60}", "",
            "  INCOME BY TYPE", f"  {'─'*55}",
        ]
        rows = Database.execute(
            "SELECT income_type, SUM(amount) as t FROM income_transactions GROUP BY income_type",
            fetch=True) or []
        for r in rows:
            lines.append(f"  {r['income_type']:<35} {self.currency_symbol} {r['t']:>12,.0f}")
        lines += [
            f"  {'─'*55}",
            f"  {'TOTAL INCOME':<35} {self.currency_symbol} {income:>12,.0f}", "",
            "  EXPENSES BY CATEGORY", f"  {'─'*55}",
        ]
        rows2 = Database.execute(
            "SELECT expense_category, SUM(amount) as t FROM expense_transactions GROUP BY expense_category",
            fetch=True) or []
        for r in rows2:
            lines.append(f"  {r['expense_category']:<35} {self.currency_symbol} {r['t']:>12,.0f}")
        lines += [
            f"  {'─'*55}",
            f"  {'TOTAL EXPENSES':<35} {self.currency_symbol} {expenses:>12,.0f}", "",
            f"{'═'*60}",
            f"  {'NET PROFIT':<35} {self.currency_symbol} {profit:>12,.0f}",
            f"  {'PROFIT MARGIN':<35} {margin:>12.1f}%",
            f"{'═'*60}",
        ]
        self.fin_sum_text.delete('1.0', 'end')
        self.fin_sum_text.insert('1.0', "\n".join(lines))

    def _export_fin_summary(self):
        content = self.fin_sum_text.get('1.0', 'end-1c')
        fp = filedialog.asksaveasfilename(defaultextension='.txt',
                                           filetypes=[('Text Files', '*.txt')])
        if fp:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("✅ Exported", f"Financial summary saved to:\n{fp}")

    def _add_income(self):
        fields = [
            ("Date *",           "transaction_date", "entry",
             datetime.now().strftime("%Y-%m-%d")),
            ("Income Type *",    "income_type",      "combo",
             ['Rent','Deposit','Maintenance','Commission','Utility','Advance','Other']),
            ("Amount *",         "amount",           "entry", ""),
            ("Client Name",      "tenant_name",      "entry", ""),
            ("Description",      "description",      "entry", ""),
            ("Receipt No",       "receipt_no",       "entry", gen_id("RCP")),
            ("Payment Method",   "payment_method",   "combo",
             ['Cash','Cheque','Bank Transfer','Online']),
        ]
        def save(vals):
            Database.execute(
                """INSERT INTO income_transactions
                   (transaction_date,income_type,amount,tenant_name,description,receipt_no,payment_method,created_by,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (vals['transaction_date'], vals['income_type'],
                 safe_float(vals['amount']),
                 vals['tenant_name'], vals['description'], vals['receipt_no'],
                 vals['payment_method'], self.current_user['username'], datetime.now()))
            self._load_income()
            self._build_dashboard_content()
        self._generic_form("➕ Add Income", fields, save)

    def _edit_income(self):
        sel = self.income_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a record to edit")
            return
        row_id = self.income_tree.item(sel[0])['values'][0]
        data = Database.execute("SELECT * FROM income_transactions WHERE id=?",
                                 (row_id,), fetch=True)
        if not data:
            return
        d = data[0]
        fields = [
            ("Date *",         "transaction_date", "entry", d['transaction_date'] or ''),
            ("Income Type *",  "income_type",      "combo",
             ['Rent','Deposit','Maintenance','Commission','Utility','Advance','Other']),
            ("Amount *",       "amount",           "entry", str(d['amount'] or '')),
            ("Client Name",    "tenant_name",      "entry", d['tenant_name'] or ''),
            ("Description",    "description",      "entry", d['description'] or ''),
            ("Receipt No",     "receipt_no",       "entry", d['receipt_no'] or ''),
            ("Payment Method", "payment_method",   "combo",
             ['Cash','Cheque','Bank Transfer','Online']),
        ]
        pre = {'income_type': d['income_type'], 'payment_method': d['payment_method']}
        def save(vals):
            Database.execute(
                """UPDATE income_transactions SET transaction_date=?,income_type=?,amount=?,
                   tenant_name=?,description=?,receipt_no=?,payment_method=? WHERE id=?""",
                (vals['transaction_date'], vals['income_type'],
                 safe_float(vals['amount']),
                 vals['tenant_name'], vals['description'], vals['receipt_no'],
                 vals['payment_method'], row_id))
            self._load_income()
        self._generic_form("✏️ Edit Income", fields, save, presets=pre)

    def _add_expense(self):
        fields = [
            ("Date *",         "transaction_date",  "entry",
             datetime.now().strftime("%Y-%m-%d")),
            ("Category *",     "expense_category",  "combo",
             ['Maintenance','Utilities','Repair','Salary','Commission','Tax','Legal','Marketing','Other']),
            ("Amount *",       "amount",             "entry", ""),
            ("Vendor Name",    "vendor_name",        "entry", ""),
            ("Description",    "description",        "entry", ""),
            ("Invoice No",     "invoice_no",         "entry", gen_id("INV")),
            ("Payment Method", "payment_method",     "combo",
             ['Cash','Cheque','Bank Transfer','Online']),
        ]
        def save(vals):
            Database.execute(
                """INSERT INTO expense_transactions
                   (transaction_date,expense_category,amount,vendor_name,description,invoice_no,payment_method,created_by,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (vals['transaction_date'], vals['expense_category'],
                 safe_float(vals['amount']),
                 vals['vendor_name'], vals['description'], vals['invoice_no'],
                 vals['payment_method'], self.current_user['username'], datetime.now()))
            self._load_expenses()
            self._build_dashboard_content()
        self._generic_form("➕ Add Expense", fields, save)

    def _edit_expense(self):
        sel = self.expense_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a record to edit")
            return
        row_id = self.expense_tree.item(sel[0])['values'][0]
        data = Database.execute("SELECT * FROM expense_transactions WHERE id=?",
                                 (row_id,), fetch=True)
        if not data:
            return
        d = data[0]
        fields = [
            ("Date *",         "transaction_date",  "entry", d['transaction_date'] or ''),
            ("Category *",     "expense_category",  "combo",
             ['Maintenance','Utilities','Repair','Salary','Commission','Tax','Legal','Marketing','Other']),
            ("Amount *",       "amount",             "entry", str(d['amount'] or '')),
            ("Vendor Name",    "vendor_name",        "entry", d['vendor_name'] or ''),
            ("Description",    "description",        "entry", d['description'] or ''),
            ("Invoice No",     "invoice_no",         "entry", d['invoice_no'] or ''),
            ("Payment Method", "payment_method",     "combo",
             ['Cash','Cheque','Bank Transfer','Online']),
        ]
        pre = {'expense_category': d['expense_category'], 'payment_method': d['payment_method']}
        def save(vals):
            Database.execute(
                """UPDATE expense_transactions SET transaction_date=?,expense_category=?,amount=?,
                   vendor_name=?,description=?,invoice_no=?,payment_method=? WHERE id=?""",
                (vals['transaction_date'], vals['expense_category'],
                 safe_float(vals['amount']),
                 vals['vendor_name'], vals['description'], vals['invoice_no'],
                 vals['payment_method'], row_id))
            self._load_expenses()
        self._generic_form("✏️ Edit Expense", fields, save, presets=pre)

    # =========================================================================
    # TAB: EMPLOYEES
    # =========================================================================

    def _tab_employees(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        hdr = self._section_header(parent, "🧑‍💼 EMPLOYEE MANAGEMENT")
        hdr.grid(row=0, column=0, sticky='ew', padx=0, pady=0)
        if has_permission(self.role, 'employees'):
            tk.Button(hdr, text="➕ Add Employee", command=self._add_employee,
                      **self._btn_style()).pack(side='right', padx=4)
            tk.Button(hdr, text="💵 Pay Salary", command=self._pay_salary,
                      **self._btn_style('success')).pack(side='right', padx=4)

        emp_nb = ttk.Notebook(parent)
        emp_nb.grid(row=1, column=0, sticky='nsew', padx=10, pady=6)

        emp_f = ttk.Frame(emp_nb)
        emp_nb.add(emp_f, text="👥 Employees")
        emp_f.grid_rowconfigure(0, weight=1)
        emp_f.grid_columnconfigure(0, weight=1)
        
        self.emp_tree = self._make_tree(emp_f,
            ('ID','Emp ID','Name','Position','Department','Phone','Salary','Commission %','Status'), row=0)
        self._load_employees()
        
        ctrl = tk.Frame(emp_f, bg=COLORS['bg'])
        ctrl.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        if has_permission(self.role, 'employees'):
            tk.Button(ctrl, text="✏️ Edit", command=self._edit_employee,
                      **self._btn_style('warning')).pack(side='left', padx=3)
            tk.Button(ctrl, text="🗑️ Delete", command=lambda: self._delete_record(
                'employees', self.emp_tree),
                      **self._btn_style('danger')).pack(side='left', padx=3)
        tk.Button(ctrl, text="🔄 Refresh", command=self._load_employees,
                  **self._btn_style()).pack(side='left', padx=3)

        att_f = ttk.Frame(emp_nb)
        emp_nb.add(att_f, text="📅 Attendance")
        self._build_attendance_tab(att_f)

        sal_f = ttk.Frame(emp_nb)
        emp_nb.add(sal_f, text="💵 Salary History")
        sal_f.grid_rowconfigure(0, weight=1)
        sal_f.grid_columnconfigure(0, weight=1)
        
        self.sal_tree = self._make_tree(sal_f,
            ('ID','Employee','Month','Year','Base Salary','Bonus','Deductions','Net Salary','Method'), row=0)
        self._load_salary_history()
        
        ctrl2 = tk.Frame(sal_f, bg=COLORS['bg'])
        ctrl2.grid(row=1, column=0, sticky='ew', padx=8, pady=4)
        tk.Button(ctrl2, text="🔄 Refresh", command=self._load_salary_history,
                  **self._btn_style()).pack(side='left', padx=3)
        if has_permission(self.role, 'employees'):
            tk.Button(ctrl2, text="💵 Add Payment", command=self._pay_salary,
                      **self._btn_style('success')).pack(side='left', padx=3)

    def _load_employees(self):
        self.emp_tree.delete(*self.emp_tree.get_children())
        rows = Database.execute(
            "SELECT id,employee_id,full_name,position,department,phone,base_salary,commission_rate,status FROM employees ORDER BY id DESC",
            fetch=True) or []
        for r in rows:
            self.emp_tree.insert('', 'end', values=(
                r['id'], r['employee_id'] or '', r['full_name'] or '',
                r['position'] or '', r['department'] or '',
                r['phone'] or '',
                f"{self.currency_symbol}{r['base_salary']:,.0f}" if r['base_salary'] else '-',
                                f"{r['commission_rate']}%" if r['commission_rate'] is not None else '-',
                r['status'] or ''))
        self._autofit_columns(self.emp_tree)


    def _add_employee(self):
        fields = [
            ("Employee ID (Auto)", "employee_id",     "entry", gen_id("EMP")),
            ("Full Name *",        "full_name",        "entry", ""),
            ("CNIC",               "cnic",             "entry", ""),
            ("Phone",              "phone",            "entry", ""),
            ("Email",              "email",            "entry", ""),
            ("Position *",         "position",         "combo",
             ['Agent','Manager','Broker','Admin','Staff','Driver','Security','Cleaner']),
            ("Department",         "department",       "combo",
             ['Sales','Rentals','Administration','Finance','Operations']),
            ("Hire Date",          "hire_date",        "entry",
             datetime.now().strftime("%Y-%m-%d")),
            ("Base Salary *",      "base_salary",      "entry", ""),
            ("Commission %",       "commission_rate",  "entry", "5.0"),
            ("Address",            "address",          "text",  ""),
            ("Notes",              "notes",            "text",  ""),
            ("Status",             "status",           "combo",
             ['Active','Inactive','On Leave','Terminated']),
        ]
        def save(vals):
            Database.execute(
                """INSERT INTO employees
                   (employee_id,full_name,cnic,phone,email,position,department,
                    hire_date,base_salary,commission_rate,address,notes,status,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (vals['employee_id'], vals['full_name'], vals['cnic'],
                 vals['phone'], vals['email'], vals['position'], vals['department'],
                 vals['hire_date'], safe_float(vals['base_salary']),
                 safe_float(vals['commission_rate']), vals['address'],
                 vals['notes'], vals['status'], datetime.now()))
            self._load_employees()
            self._build_dashboard_content()
        self._generic_form("➕ Add Employee", fields, save)

    def _edit_employee(self):
        sel = self.emp_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select an employee to edit")
            return
        row_id = self.emp_tree.item(sel[0])['values'][0]
        data = Database.execute("SELECT * FROM employees WHERE id=?", (row_id,), fetch=True)
        if not data:
            return
        d = data[0]
        fields = [
            ("Employee ID",   "employee_id",    "entry", d['employee_id'] or ''),
            ("Full Name *",   "full_name",       "entry", d['full_name'] or ''),
            ("CNIC",          "cnic",            "entry", d['cnic'] or ''),
            ("Phone",         "phone",           "entry", d['phone'] or ''),
            ("Email",         "email",           "entry", d['email'] or ''),
            ("Position *",    "position",        "combo",
             ['Agent','Manager','Broker','Admin','Staff','Driver','Security','Cleaner']),
            ("Department",    "department",      "combo",
             ['Sales','Rentals','Administration','Finance','Operations']),
            ("Hire Date",     "hire_date",       "entry", d['hire_date'] or ''),
            ("Base Salary *", "base_salary",     "entry", str(d['base_salary'] or '')),
            ("Commission %",  "commission_rate", "entry", str(d['commission_rate'] or '')),
            ("Address",       "address",         "text",  d['address'] or ''),
            ("Notes",         "notes",           "text",  d['notes'] or ''),
            ("Status",        "status",          "combo",
             ['Active','Inactive','On Leave','Terminated']),
        ]
        pre = {'position': d['position'], 'department': d['department'], 'status': d['status']}
        def save(vals):
            Database.execute(
                """UPDATE employees SET full_name=?,cnic=?,phone=?,email=?,position=?,department=?,
                   hire_date=?,base_salary=?,commission_rate=?,address=?,notes=?,status=? WHERE id=?""",
                (vals['full_name'], vals['cnic'], vals['phone'], vals['email'],
                 vals['position'], vals['department'], vals['hire_date'],
                 safe_float(vals['base_salary']), safe_float(vals['commission_rate']),
                 vals['address'], vals['notes'], vals['status'], row_id))
            self._load_employees()
        self._generic_form("✏️ Edit Employee", fields, save, presets=pre)

    def _build_attendance_tab(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        hdr2 = tk.Frame(parent, bg=COLORS['bg'])
        hdr2.grid(row=0, column=0, sticky='ew', padx=8, pady=6)
        tk.Label(hdr2, text="Date:", bg=COLORS['bg'],
                 font=('Segoe UI', 10)).pack(side='left', padx=4)
        self.att_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(hdr2, textvariable=self.att_date_var, width=14,
                  font=('Segoe UI', 10)).pack(side='left', padx=4)
        tk.Button(hdr2, text="📋 Load / Mark Attendance",
                  command=self._load_attendance, **self._btn_style()).pack(side='left', padx=6)

        att_frame = tk.Frame(parent, bg=COLORS['bg'])
        att_frame.grid(row=1, column=0, sticky='nsew', padx=8, pady=6)
        att_frame.grid_rowconfigure(0, weight=1)
        att_frame.grid_columnconfigure(0, weight=1)
        
        self.att_tree = self._make_tree(att_frame, ('ID','Employee','Date','Status','Notes'), row=0)
        
        ctrl = tk.Frame(parent, bg=COLORS['bg'])
        ctrl.grid(row=2, column=0, sticky='ew', padx=8, pady=4)
        if has_permission(self.role, 'employees'):
            tk.Button(ctrl, text="✅ Mark Present",
                      command=lambda: self._mark_attendance('Present'),
                      **self._btn_style('success')).pack(side='left', padx=3)
            tk.Button(ctrl, text="❌ Mark Absent",
                      command=lambda: self._mark_attendance('Absent'),
                      **self._btn_style('danger')).pack(side='left', padx=3)
            tk.Button(ctrl, text="📑 Mark Leave",
                      command=lambda: self._mark_attendance('Leave'),
                      **self._btn_style('warning')).pack(side='left', padx=3)
        self._load_attendance()

    def _load_attendance(self):
        self.att_tree.delete(*self.att_tree.get_children())
        date = self.att_date_var.get()
        rows = Database.execute(
            """SELECT a.id, e.full_name, a.date, a.status, a.notes
               FROM attendance a JOIN employees e ON a.employee_id=e.id
               WHERE a.date=? ORDER BY e.full_name""",
            (date,), fetch=True) or []
        if not rows:
            emps = Database.execute(
                "SELECT id, full_name FROM employees WHERE status='Active'",
                fetch=True) or []
            for e in emps:
                self.att_tree.insert('', 'end', values=(
                    '', e['full_name'], date, 'Not Marked', ''))
        else:
            for r in rows:
                self.att_tree.insert('', 'end', values=(
                    r['id'], r['full_name'], r['date'], r['status'] or '', r['notes'] or ''))
        self._autofit_columns(self.att_tree)


    def _mark_attendance(self, status):
        sel = self.att_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select an employee row")
            return
        date = self.att_date_var.get()
        for s in sel:
            vals = self.att_tree.item(s)['values']
            emp_name = vals[1]
            emp = Database.execute(
                "SELECT id FROM employees WHERE full_name=?", (emp_name,), fetch=True)
            if emp:
                emp_id = emp[0]['id']
                existing = Database.execute(
                    "SELECT id FROM attendance WHERE employee_id=? AND date=?",
                    (emp_id, date), fetch=True)
                if existing:
                    Database.execute(
                        "UPDATE attendance SET status=? WHERE employee_id=? AND date=?",
                        (status, emp_id, date))
                else:
                    Database.execute(
                        "INSERT INTO attendance (employee_id,date,status) VALUES (?,?,?)",
                        (emp_id, date, status))
        self._load_attendance()
        messagebox.showinfo("✅", f"Marked as {status}")

    def _pay_salary(self):
        emps = Database.execute(
            "SELECT id, full_name, base_salary FROM employees WHERE status='Active'",
            fetch=True) or []
        if not emps:
            messagebox.showwarning("No Employees", "No active employees found")
            return
        emp_names = [f"{e['full_name']} (Base: {self.currency_symbol}{e['base_salary']:,.0f})"
                     for e in emps]
        fields = [
            ("Employee *",       "employee",        "combo", emp_names),
            ("Month *",          "month",           "combo",
             ['January','February','March','April','May','June',
              'July','August','September','October','November','December']),
            ("Year *",           "year",            "entry", str(datetime.now().year)),
            ("Base Salary *",    "base_salary",     "entry", ""),
            ("Bonus",            "bonus",           "entry", "0"),
            ("Deductions",       "deductions",      "entry", "0"),
            ("Net Salary",       "net_salary",      "entry", ""),
            ("Payment Method",   "payment_method",  "combo",
             ['Cash','Cheque','Bank Transfer','Online']),
            ("Notes",            "notes",           "entry", ""),
        ]
        def save(vals):
            emp_name = vals['employee'].split(" (Base:")[0]
            emp = Database.execute("SELECT id FROM employees WHERE full_name=?",
                                    (emp_name,), fetch=True)
            if emp:
                base  = safe_float(vals['base_salary'])
                bonus = safe_float(vals['bonus'])
                deduc = safe_float(vals['deductions'])
                net_salary_str = str(vals.get('net_salary', '')).strip()
                net = safe_float(net_salary_str) if net_salary_str else (base + bonus - deduc)
                Database.execute(
                    """INSERT INTO salary_payments
                       (employee_id,payment_date,month,year,base_salary,bonus,deductions,net_salary,payment_method,notes,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (emp[0]['id'], datetime.now().strftime("%Y-%m-%d"),
                     vals['month'], vals['year'],
                     base, bonus, deduc, net, vals['payment_method'],
                     vals['notes'], datetime.now()))
                self._load_salary_history()
        self._generic_form("💵 Pay Salary", fields, save)

    def _load_salary_history(self):
        self.sal_tree.delete(*self.sal_tree.get_children())
        rows = Database.execute(
            """SELECT sp.id, e.full_name, sp.month, sp.year,
                      sp.base_salary, sp.bonus, sp.deductions, sp.net_salary, sp.payment_method
               FROM salary_payments sp JOIN employees e ON sp.employee_id=e.id
               ORDER BY sp.id DESC""",
            fetch=True) or []
        for r in rows:
            self.sal_tree.insert('', 'end', values=(
                r['id'], r['full_name'] or '',
                r['month'] or '', r['year'] or '',
                f"{self.currency_symbol}{r['base_salary']:,.0f}" if r['base_salary'] else '-',
                f"{self.currency_symbol}{r['bonus']:,.0f}"       if r['bonus']       else '-',
                                f"{self.currency_symbol}{r['deductions']:,.0f}"  if r['deductions']  else '-',
                f"{self.currency_symbol}{r['net_salary']:,.0f}"  if r['net_salary']  else '-',
                r['payment_method'] or ''))
        self._autofit_columns(self.sal_tree)


    # =========================================================================
    # TAB: REPORTS
    # =========================================================================

    def _tab_reports(self, parent):
        self._section_header(parent, "📈 REPORTS & ANALYTICS")

        btn_f = tk.Frame(parent, bg=COLORS['bg'])
        btn_f.pack(fill='x', padx=10, pady=6)

        btns = [
            ("💰 Financial Summary", self._report_financial),
            ("🏠 Rent Report",       self._report_rent),
            ("🏗️ Property Report",  self._report_properties),
            ("👥 Client Report",    self._report_clients),
            ("🧑‍💼 Employee Report", self._report_employees),
            ("📅 Attendance Report",self._report_attendance),
        ]
        for i, (lbl, cmd) in enumerate(btns):
            tk.Button(btn_f, text=lbl, command=cmd,
                      **self._btn_style()).grid(row=0, column=i, padx=4, pady=4)

        dr_f = tk.Frame(parent, bg=COLORS['bg'])
        dr_f.pack(fill='x', padx=10, pady=4)
        tk.Label(dr_f, text="From:", bg=COLORS['bg'],
                 font=('Segoe UI', 9)).pack(side='left', padx=4)
        self.rpt_from = tk.StringVar(value=datetime.now().strftime("%Y-%m-01"))
        ttk.Entry(dr_f, textvariable=self.rpt_from, width=14,
                  font=('Segoe UI', 9)).pack(side='left', padx=2)
        tk.Label(dr_f, text="To:", bg=COLORS['bg'],
                 font=('Segoe UI', 9)).pack(side='left', padx=4)
        self.rpt_to = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(dr_f, textvariable=self.rpt_to, width=14,
                  font=('Segoe UI', 9)).pack(side='left', padx=2)

        export_f = tk.Frame(parent, bg=COLORS['bg'])
        export_f.pack(fill='x', padx=10, pady=2)
        tk.Button(export_f, text="📤 Export Report", command=self._export_report,
                  **self._btn_style()).pack(side='left', padx=4)
        if FPDF_AVAILABLE:
            tk.Button(export_f, text="🖨️ Print PDF", command=self._print_pdf,
                      **self._btn_style('danger')).pack(side='left', padx=4)

        self.report_text = scrolledtext.ScrolledText(parent,
                                                      font=('Courier New', 9),
                                                      bg='white', fg=COLORS['dark'],
                                                      height=30)
        self.report_text.pack(fill='both', expand=True, padx=10, pady=6)

    def _report_header(self, title):
        return (f"\n{'═'*65}\n"
                f"  {title}\n"
                f"  Company: {self.company_name}\n"
                f"  Generated: {datetime.now().strftime('%d %B %Y at %H:%M')}\n"
                f"{'═'*65}\n\n")

    def _report_financial(self):
        txt = self._report_header("FINANCIAL SUMMARY REPORT")
        income   = self._sum('income_transactions', 'amount')
        expenses = self._sum('expense_transactions', 'amount')
        profit   = income - expenses

        txt += "  INCOME BY TYPE\n  " + "─"*60 + "\n"
        rows = Database.execute(
            "SELECT income_type, COUNT(*) c, SUM(amount) t FROM income_transactions GROUP BY income_type",
            fetch=True) or []
        for r in rows:
            txt += f"  {r['income_type']:<40} Qty:{r['c']:>4}   {self.currency_symbol} {r['t']:>12,.0f}\n"
        txt += f"\n  {'TOTAL INCOME':<40}       {self.currency_symbol} {income:>12,.0f}\n\n"

        txt += "  EXPENSES BY CATEGORY\n  " + "─"*60 + "\n"
        rows2 = Database.execute(
            "SELECT expense_category, COUNT(*) c, SUM(amount) t FROM expense_transactions GROUP BY expense_category",
            fetch=True) or []
        for r in rows2:
            txt += f"  {r['expense_category']:<40} Qty:{r['c']:>4}   {self.currency_symbol} {r['t']:>12,.0f}\n"
        txt += f"\n  {'TOTAL EXPENSES':<40}       {self.currency_symbol} {expenses:>12,.0f}\n"
        txt += f"\n{'═'*65}\n"
        txt += f"  {'NET PROFIT':<40}       {self.currency_symbol} {profit:>12,.0f}\n"
        txt += f"  {'PROFIT MARGIN':<40}       {(profit/income*100 if income else 0):>12.1f}%\n"
        txt += f"{'═'*65}\n"
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', txt)

    def _report_rent(self):
        txt = self._report_header("PROPERTY DEALINGS REPORT")
        txt += "  RENT REQUIREMENTS\n  " + "─"*60 + "\n"
        rows = Database.execute("SELECT * FROM rent_requirements ORDER BY id DESC", fetch=True) or []
        for r in rows:
            txt += (f"  #{r['id']}  {r['client_name'] or '-':<25}  {r['location'] or '-':<20}"
                    f"  Budget: {self.currency_symbol}{(r['budget'] or 0):,.0f}  "
                    f"  Req: {r['property_requires'] or '-'}\n")
        txt += f"\n  Total Requirements: {len(rows)}\n\n"
        txt += "  AVAILABLE PROPERTIES\n  " + "─"*60 + "\n"
        rows2 = Database.execute("SELECT * FROM rent_availability ORDER BY id DESC", fetch=True) or []
        for r in rows2:
            txt += (f"  #{r['id']}  {r['owner_name'] or '-':<25}  {r['location'] or '-':<20}"
                    f"  Rent: {self.currency_symbol}{(r['monthly_rent'] or 0):,.0f}/mo  Status: {r['status'] or ''}\n")
        txt += f"\n  Total Available: {len(rows2)}\n"

        txt += "\n  SALE REQUIREMENTS\n  " + "─"*60 + "\n"
        rows3 = Database.execute("SELECT * FROM sale_requirements ORDER BY id DESC", fetch=True) or []
        for r in rows3:
            txt += (f"  #{r['id']}  {r['client_name'] or '-':<25}  {r['location'] or '-':<20}"
                    f"  Budget: {self.currency_symbol}{(r['budget'] or 0):,.0f}\n")
        txt += f"\n  Total Sale Requirements: {len(rows3)}\n"

        txt += "\n  SALE AVAILABILITY\n  " + "─"*60 + "\n"
        rows4 = Database.execute("SELECT * FROM sale_availability ORDER BY id DESC", fetch=True) or []
        for r in rows4:
            txt += (f"  #{r['id']}  {r['owner_name'] or '-':<25}  {r['location'] or '-':<20}"
                    f"  Demand: {self.currency_symbol}{(r['demand'] or 0):,.0f}\n")
        txt += f"\n  Total Sale Availability: {len(rows4)}\n"
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', txt)

    def _report_properties(self):
        txt = self._report_header("PROPERTY PORTFOLIO REPORT")
        rows = Database.execute("SELECT * FROM properties ORDER BY id DESC", fetch=True) or []
        by_status = {}
        for r in rows:
            s = r['status'] or 'Unknown'
            by_status[s] = by_status.get(s, 0) + 1
            txt += (f"  [{r['property_code'] or '----'}]  {r['title'] or '-':<30}  "
                    f"{r['property_type'] or '-':<12}  {r['status'] or '-':<12}"
                    f"  {r['location'] or '-'}\n")
        txt += "\n  SUMMARY BY STATUS:\n"
        for k, v in by_status.items():
            txt += f"  {k:<20} {v}\n"
        txt += f"\n  Total Properties: {len(rows)}\n"
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', txt)

    def _report_clients(self):
        txt = self._report_header("CLIENT REPORT")
        rows = Database.execute("SELECT * FROM clients ORDER BY id DESC", fetch=True) or []
        for r in rows:
            txt += (f"  #{r['id']}  {r['client_name'] or '-':<25}  {r['phone'] or '-':<15}"
                    f"  {r['client_type'] or '-':<12}  {r['status'] or ''}\n")
        txt += f"\n  Total Clients: {len(rows)}\n"
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', txt)

    def _report_employees(self):
        txt = self._report_header("EMPLOYEE REPORT")
        rows = Database.execute("SELECT * FROM employees ORDER BY id", fetch=True) or []
        total_salary = 0
        for r in rows:
            sal = r['base_salary'] or 0
            total_salary += sal
            txt += (f"  [{r['employee_id'] or '----'}]  {r['full_name'] or '-':<25}"
                    f"  {r['position'] or '-':<15}  Salary: {self.currency_symbol}{sal:,.0f}"
                    f"  {r['status'] or ''}\n")
        txt += f"\n  Total Employees: {len(rows)}\n"
        txt += f"  Total Monthly Payroll: {self.currency_symbol} {total_salary:,.0f}\n"
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', txt)

    def _report_attendance(self):
        txt = self._report_header("ATTENDANCE REPORT")
        rows = Database.execute(
            """SELECT a.date, e.full_name, a.status FROM attendance a
               JOIN employees e ON a.employee_id=e.id ORDER BY a.date DESC, e.full_name""",
            fetch=True) or []
        present = sum(1 for r in rows if r['status'] == 'Present')
        absent  = sum(1 for r in rows if r['status'] == 'Absent')
        leave   = sum(1 for r in rows if r['status'] == 'Leave')
        for r in rows:
            icon = "✅" if r['status'] == 'Present' else ("❌" if r['status'] == 'Absent' else "📑")
            txt += f"  {r['date']}   {r['full_name'] or '-':<25}  {icon} {r['status'] or ''}\n"
        txt += f"\n  Present: {present}   Absent: {absent}   Leave: {leave}\n"
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', txt)

    def _export_report(self):
        content = self.report_text.get('1.0', 'end-1c')
        if not content.strip():
            messagebox.showwarning("Empty", "Please generate a report first")
            return
        fp = filedialog.asksaveasfilename(defaultextension='.txt',
                                           filetypes=[('Text Files', '*.txt'),
                                                      ('CSV Files', '*.csv')])
        if fp:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("✅ Exported", f"Report saved to:\n{fp}")

    def _print_pdf(self):
        if not FPDF_AVAILABLE:
            messagebox.showerror("Missing", "fpdf2 not installed.\nRun: pip install fpdf2")
            return
        content = self.report_text.get('1.0', 'end-1c')
        if not content.strip():
            messagebox.showwarning("Empty", "Please generate a report first")
            return
        try:
            pdf = FPDF(orientation='L', format='A4')
            pdf.add_page()
            pdf.set_margins(10, 10, 10)
            pdf.set_font("Courier", size=8)
            for line in content.split('\n'):
                clean = ''.join(c if ord(c) < 128 else '' for c in line)
                if len(clean) > 140:
                    for i in range(0, len(clean), 140):
                        pdf.cell(0, 4, clean[i:i+140], ln=True)
                else:
                    pdf.cell(0, 4, clean or " ", ln=True)
            import tempfile, subprocess, platform
            tmp = os.path.join(tempfile.gettempdir(),
                               f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            pdf.output(tmp)
            if platform.system() == 'Windows':
                os.startfile(tmp)
            elif platform.system() == 'Darwin':
                subprocess.Popen(['open', tmp])
            else:
                subprocess.Popen(['xdg-open', tmp])
            messagebox.showinfo("✅ PDF", f"PDF opened: {tmp}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================================
    # SETTINGS WINDOWS
    # =========================================================================

    def _company_settings(self):
        win = tk.Toplevel(self.root)
        win.title("🏢 Company Settings")
        set_app_icon(win)
        fit_window_to_screen(win, 600, 550, min_w=480, min_h=420)
        win.grab_set()

        nb = ttk.Notebook(win)
        nb.pack(fill='both', expand=True, padx=10, pady=10)

        g = ttk.Frame(nb, padding=20)
        nb.add(g, text="📋 General")
        keys = [
            ("Company Name",    "company_name"),
            ("Address",         "company_address"),
            ("Phone",           "company_phone"),
            ("Email",           "company_email"),
        ]
        entries = {}
        for i, (lbl, key) in enumerate(keys):
            ttk.Label(g, text=lbl + ":", font=('Segoe UI', 10)).grid(row=i, column=0, sticky='w', pady=10)
            e = ttk.Entry(g, width=40, font=('Segoe UI', 10))
            e.insert(0, Settings.get(key))
            e.grid(row=i, column=1, padx=10, pady=10)
            entries[key] = e

        f = ttk.Frame(nb, padding=20)
        nb.add(f, text="💰 Financial")
        fkeys = [
            ("Currency Symbol",    "currency_symbol"),
            ("Default Commission %","default_commission"),
            ("Tax Rate %",         "tax_rate"),
            ("Bank Account",       "bank_account"),
        ]
        for i, (lbl, key) in enumerate(fkeys):
            ttk.Label(f, text=lbl + ":", font=('Segoe UI', 10)).grid(row=i, column=0, sticky='w', pady=10)
            e = ttk.Entry(f, width=40, font=('Segoe UI', 10))
            e.insert(0, Settings.get(key))
            e.grid(row=i, column=1, padx=10, pady=10)
            entries[key] = e

        def save():
            try:
                for key, entry in entries.items():
                    validate_form_value(
                        key,
                        key.replace('_', ' ').title(),
                        entry.get(),
                        required=key in ('company_name', 'currency_symbol'),
                        numeric=key in NUMERIC_FORM_KEYS,
                    )
                for key, entry in entries.items():
                    Settings.set(key, entry.get().strip())
            except ValueError as ex:
                messagebox.showwarning("Validation", str(ex), parent=win)
                return
            self.currency_symbol = Settings.get('currency_symbol', 'Rs.')
            self.company_name    = Settings.get('company_name')
            messagebox.showinfo("✅ Saved", "Settings saved successfully!")
            win.destroy()
            self._refresh_all()

        btns = ttk.Frame(win)
        btns.pack(fill='x', padx=10, pady=10)
        ttk.Button(btns, text="💾 Save",   command=save).pack(side='right', padx=5)
        ttk.Button(btns, text="❌ Cancel", command=win.destroy).pack(side='right')

    # ─────────────────────────────────────────────────────────────────────────
    # FIX: User Management — correct toggle logic + use module-level simpledialog
    # ─────────────────────────────────────────────────────────────────────────
    def _user_management(self):
        win = tk.Toplevel(self.root)
        win.title("👥 User Management")
        set_app_icon(win)
        fit_window_to_screen(win, 820, 580, min_w=680, min_h=420)
        win.grab_set()
        win.configure(bg=COLORS['bg'])

        # Tree container — packed
        tree_frame = tk.Frame(win, bg=COLORS['bg'])
        tree_frame.pack(fill='both', expand=True, padx=8, pady=6)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        cols = ('ID','Username','Full Name','Email','Role','Status','Last Login')
        tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=90, minwidth=60)
        tree.column('ID', width=40)
        tree.column('Full Name', width=140)
        tree.column('Email', width=140)
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        enable_tree_cell_selection(tree, hsb, vsb)

        self._load_users_tree(tree)

        ctrl = tk.Frame(win, bg=COLORS['bg'])
        ctrl.pack(fill='x', padx=8, pady=6)

        def add_user():
            fields = [
                ("Username *", "username",  "entry", ""),
                ("Password *", "password",  "entry", ""),
                ("Full Name *","full_name", "entry", ""),
                ("Email",      "email",     "entry", ""),
                ("Role",       "role",      "combo", [r.value for r in UserRole]),
            ]
            def do_create(vals):
                ok, msg = Auth.create_user(
                    vals['username'], vals['password'],
                    vals['full_name'], vals['email'], vals['role'])
                if not ok:
                    raise Exception(msg)
                self._load_users_tree(tree)
            self._generic_form("➕ Add User", fields, do_create, parent=win)

        def edit_user():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Please select a user to edit", parent=win)
                return
            uid      = tree.item(sel[0])['values'][0]
            username = tree.item(sel[0])['values'][1]
            result = Database.execute("SELECT * FROM users WHERE id=?", (uid,), fetch=True)
            if not result:
                return
            d = result[0]
            fields = [
                ("Username *", "username",  "entry", d['username']),
                ("Password (leave blank to keep)", "password", "entry", ""),
                ("Full Name *","full_name", "entry", d['full_name'] or ''),
                ("Email",      "email",     "entry", d['email'] or ''),
                ("Role",       "role",      "combo", [r.value for r in UserRole]),
            ]
            pre = {'role': d['role']}
            def do_save(vals):
                if vals['password'] and len(vals['password']) >= 4:
                    Database.execute("UPDATE users SET username=?, password_hash=?, full_name=?, email=?, role=? WHERE id=?",
                        (vals['username'], Auth.hash_pw(vals['password']), vals['full_name'], vals['email'], vals['role'], uid))
                elif vals['password'] and len(vals['password']) < 4:
                    raise Exception("Password must be at least 4 characters")
                else:
                    Database.execute("UPDATE users SET username=?, full_name=?, email=?, role=? WHERE id=?",
                        (vals['username'], vals['full_name'], vals['email'], vals['role'], uid))
                self._load_users_tree(tree)
            self._generic_form("✏️ Edit User", fields, do_save, parent=win, presets=pre)

        def toggle_status():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Please select a user", parent=win)
                return
            row  = tree.item(sel[0])['values']
            uid  = row[0]
            current_active = 1 if "Active" in str(row[5]) and "Inactive" not in str(row[5]) else 0
            new_active = 0 if current_active else 1
            Database.execute("UPDATE users SET is_active=? WHERE id=?", (new_active, uid))
            self._load_users_tree(tree)

        def reset_pwd():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Please select a user", parent=win)
                return
            uid      = tree.item(sel[0])['values'][0]
            username = tree.item(sel[0])['values'][1]
            new_pw = simpledialog.askstring(
                "Reset Password",
                f"Enter new password for '{username}':",
                show='*', parent=win)
            if new_pw is None:
                return
            if len(new_pw) < 4:
                messagebox.showwarning("Too Short",
                                       "Password must be at least 4 characters", parent=win)
                return
            Database.execute("UPDATE users SET password_hash=? WHERE id=?",
                              (Auth.hash_pw(new_pw), uid))
            messagebox.showinfo("✅ Reset",
                                f"Password for '{username}' reset successfully!", parent=win)

        tk.Button(ctrl, text="➕ Add User",            command=add_user,
                  **self._btn_style()).pack(side='left', padx=3)
        tk.Button(ctrl, text="✏️ Edit User",           command=edit_user,
                  **self._btn_style('warning')).pack(side='left', padx=3)
        tk.Button(ctrl, text="🔄 Toggle Active/Inactive", command=toggle_status,
                  **self._btn_style()).pack(side='left', padx=3)
        tk.Button(ctrl, text="🔐 Reset Password",      command=reset_pwd,
                  **self._btn_style('danger')).pack(side='left', padx=3)
        tk.Button(ctrl, text="🔄 Refresh",             command=lambda: self._load_users_tree(tree),
                  **self._btn_style()).pack(side='left', padx=3)

    def _load_users_tree(self, tree):
        tree.delete(*tree.get_children())
        rows = Database.execute(
            "SELECT id,username,full_name,email,role,is_active,last_login FROM users",
            fetch=True) or []
        for r in rows:
            status = "🟢 Active" if r['is_active'] else "🔴 Inactive"
            tree.insert('', 'end', values=(
                r['id'], r['username'], r['full_name'] or '',
                r['email'] or '', r['role'] or '',
                status, r['last_login'] or 'Never'))

    def _roles_info(self):
        win = tk.Toplevel(self.root)
        win.title("🔑 Roles & Permissions")
        set_app_icon(win)
        fit_window_to_screen(win, 700, 550, min_w=560, min_h=420)
        txt = scrolledtext.ScrolledText(win, font=('Courier', 9), bg='white')
        txt.pack(fill='both', expand=True, padx=10, pady=10)
        info = """
╔══════════════════════════════════════════════════════════════════╗
║              ROLE-BASED ACCESS CONTROL (RBAC)                   ║
╚══════════════════════════════════════════════════════════════════╝

FEATURE            Super Admin  Admin   Manager   Staff   Viewer
─────────────────────────────────────────────────────────────────
Dashboard          ✓            ✓       ✓         ✓       ✓
Property Dealings  ✓ Full       ✓ Full  ✓ Full    ✓ Add   View
Properties         ✓ Full       ✓ Full  ✓ Full    ✓ Add   View
Clients            ✓ Full       ✓ Full  ✓ Full    ✓ Add   View
Financials         ✓ Full       ✓ Full  View only  ✗       ✗
Employees          ✓ Full       ✓ Full  ✓ Full    View    View
Reports            ✓            ✓       ✓         ✗       ✓
Settings           ✓            ✓       ✗         ✗       ✗
User Management    ✓            ✓       ✗         ✗       ✗
Role Management    ✓            ✗       ✗         ✗       ✗
Delete Records     ✓            ✓       ✗         ✗       ✗
Backup/Restore     ✓            ✓       ✗         ✗       ✗
─────────────────────────────────────────────────────────────────
"""
        txt.insert('1.0', info)
        txt.config(state='disabled')

    # ─────────────────────────────────────────────────────────────────────────
    # FIX: Change My Password — field validation improved
    # ─────────────────────────────────────────────────────────────────────────
    def _change_my_password(self):
        win = tk.Toplevel(self.root)
        win.title("🔐 Change My Password")
        set_app_icon(win)
        fit_window_to_screen(win, 400, 320, min_w=360, min_h=300)
        win.grab_set()

        f = ttk.Frame(win, padding=25)
        f.pack(fill='both', expand=True)

        ttk.Label(f, text="Change Password",
                  font=('Segoe UI', 13, 'bold')).pack(pady=(0, 15))

        ttk.Label(f, text="Current Password:").pack(anchor='w', pady=3)
        old = ttk.Entry(f, show='●', width=35)
        old.pack(fill='x', pady=(0, 10))

        ttk.Label(f, text="New Password (min 4 chars):").pack(anchor='w', pady=3)
        new = ttk.Entry(f, show='●', width=35)
        new.pack(fill='x', pady=(0, 10))

        ttk.Label(f, text="Confirm New Password:").pack(anchor='w', pady=3)
        conf = ttk.Entry(f, show='●', width=35)
        conf.pack(fill='x', pady=(0, 15))

        status_lbl = ttk.Label(f, text="", foreground='red')
        status_lbl.pack()

        def save():
            o = old.get()
            n = new.get()
            c = conf.get()
            if not o or not n or not c:
                status_lbl.config(text="⚠ Please fill all fields")
                return
            if n != c:
                status_lbl.config(text="❌ New passwords don't match")
                return
            if len(n) < 4:
                status_lbl.config(text="⚠ Password must be at least 4 characters")
                return
            ok, msg = Auth.change_password(self.current_user['id'], o, n)
            if ok:
                messagebox.showinfo("✅ Success", msg, parent=win)
                win.destroy()
            else:
                status_lbl.config(text=f"❌ {msg}")

        ttk.Button(f, text="✅ Change Password", command=save).pack(fill='x', pady=4)
        ttk.Button(f, text="❌ Cancel", command=win.destroy).pack(fill='x')

    # =========================================================================
    # GENERIC FORM — FIX: removed tuple-expression anti-pattern from on_save
    # =========================================================================

    def _generic_form(self, title, fields, on_save, parent=None, presets=None,
                      show_templates=False):
        """
        fields  : list of (label, key, type, default)
                  type: 'entry' | 'combo' | 'combo_other' | 'combo_multi' | 'autocomplete' | 'text'
        on_save : callable(vals_dict) — raise Exception to show error, return normally to close
        presets : dict {key: initial_value} for combo widgets
        combo_multi stores selected items as comma-separated string
        show_templates : if True, show property template quick-fill buttons
        """
        if presets is None:
            presets = {}

        win = tk.Toplevel(parent or self.root)
        win.title(title)
        set_app_icon(win)
        win.transient(parent or self.root)
        win.grab_set()

        h = min(820, 150 + len(fields) * 58)
        fit_window_to_screen(win, 760, h, min_w=560, min_h=420)

        # Scrollable interior
        canvas = tk.Canvas(win, bg='white', highlightthickness=0)
        vsb    = ttk.Scrollbar(win, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(fill='both', expand=True)

        inner = tk.Frame(canvas, bg='white', padx=30, pady=18)
        cw    = canvas.create_window((0, 0), window=inner, anchor='nw')

        def _on_inner_configure(e):
            canvas.configure(scrollregion=canvas.bbox('all'))
            # NOTE: inner can configure before canvas has a real width (often 1px on Win);
            # keep scrollregion updated here, but size the window via canvas <Configure>.
        inner.bind('<Configure>', _on_inner_configure)

        def _on_canvas_configure(e):
            # Ensure embedded frame always matches visible canvas width
            canvas.itemconfig(cw, width=max(1, e.width))
            canvas.configure(scrollregion=canvas.bbox('all'))
        canvas.bind('<Configure>', _on_canvas_configure)

        # Mouse-wheel scroll support (bind only while this dialog is active)
        def _on_wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        def _on_wheel_linux_up(e):
            canvas.yview_scroll(-1, "units")
        def _on_wheel_linux_down(e):
            canvas.yview_scroll(1, "units")
        def _bind_wheel(_e=None):
            canvas.bind_all('<MouseWheel>', _on_wheel)
            canvas.bind_all('<Button-4>', _on_wheel_linux_up)
            canvas.bind_all('<Button-5>', _on_wheel_linux_down)
        def _unbind_wheel(_e=None):
            canvas.unbind_all('<MouseWheel>')
            canvas.unbind_all('<Button-4>')
            canvas.unbind_all('<Button-5>')
        def _cancel(event=None):
            _unbind_wheel()
            win.destroy()
            return 'break'
        win.bind('<FocusIn>', _bind_wheel)
        win.bind('<FocusOut>', _unbind_wheel)
        win.protocol("WM_DELETE_WINDOW", _cancel)
        _bind_wheel()

        tk.Label(inner, text=title, bg='white', fg=COLORS['primary'],
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 14))

        # Property template quick-fill bar
        template_bar = None
        if show_templates:
            template_bar = PropertyTemplateBar(inner)
            template_bar.pack(fill='x', pady=(0, 8))

        entries = {}
        field_meta = {}
        for label, key, ftype, default in fields:
            clean_label = str(label).replace('*', '').strip()
            option_values = default if isinstance(default, list) else []
            field_meta[key] = {
                'label': clean_label,
                'required': '*' in str(label),
                'numeric': key in NUMERIC_FORM_KEYS,
                'options': option_values,
                'strict_options': ftype == 'combo',
            }
            row = tk.Frame(inner, bg='white')
            row.pack(fill='x', pady=6)
            tk.Label(row, text=label, bg='white', fg=COLORS['dark'],
                     font=('Segoe UI', 10, 'bold'),
                     width=24, anchor='w').pack(side='left', anchor='n')

            if ftype == 'autocomplete':
                options = default if isinstance(default, list) else []
                e = AutocompleteCombobox(row, completion_list=options, width=46, font=('Segoe UI', 10))
                e.set(presets.get(key, options[0] if options else ''))
                entries[key] = (e, ftype, None)
                e.pack(side='left', padx=6, fill='x', expand=True)
            elif ftype == 'combo':
                options = default if isinstance(default, list) else []
                e = ttk.Combobox(row, values=options, width=46, font=('Segoe UI', 10))
                e.set(presets.get(key, options[0] if options else ''))
                entries[key] = (e, ftype, None)
                e.pack(side='left', padx=6, fill='x', expand=True)
            elif ftype == 'combo_other':
                options = default if isinstance(default, list) else []
                # Always include "Other" as a manual KPI entry
                if "Other" not in options:
                    options = options + ["Other"]
                e = ttk.Combobox(row, values=options, width=24, font=('Segoe UI', 10))
                preset = presets.get(key, options[0] if options else '')
                e.set(preset)
                e.pack(side='left', padx=6, fill='x', expand=True)

                other = ttk.Entry(row, width=24, font=('Segoe UI', 10))

                def _toggle_other(_evt=None, _combo=e, _other=other):
                    if _combo.get().strip() == "Other":
                        _other.pack(side='left', padx=(6, 0))
                        _other.focus_set()
                    else:
                        _other.pack_forget()

                e.bind("<<ComboboxSelected>>", _toggle_other)
                if preset and preset not in options:
                    e.set("Other")
                    other.insert(0, str(preset))
                _toggle_other()
                entries[key] = (e, ftype, other)
            elif ftype == 'combo_multi':
                # Multi-select with checkboxes
                options = default if isinstance(default, list) else []
                checkbox_frame = tk.Frame(row, bg='white')
                checkbox_frame.pack(side='left', anchor='nw')
                
                checkbox_vars = {}
                selected_items = []
                if key in presets and presets[key]:
                    selected_items = [x.strip() for x in str(presets[key]).split(',')]
                for idx, opt in enumerate(options):
                    var = tk.BooleanVar()
                    var.set(opt in selected_items)
                    checkbox_vars[opt] = var
                    cb = ttk.Checkbutton(checkbox_frame, text=opt, variable=var)
                    cb.grid(row=idx // 3, column=idx % 3, sticky='w', padx=(0, 12), pady=2)
                
                entries[key] = (checkbox_vars, ftype, options)
            elif ftype == 'text':
                text_frame = tk.Frame(row, bg='white')
                text_frame.pack(side='left', padx=6, fill='x', expand=True)
                e = tk.Text(text_frame, width=52, height=4, font=('Segoe UI', 10),
                            relief='solid', bd=1, wrap='word', undo=True)
                text_scroll = ttk.Scrollbar(text_frame, orient='vertical', command=e.yview)
                e.configure(yscrollcommand=text_scroll.set)
                if default not in (None, "") and not isinstance(default, list):
                    e.insert('1.0', str(default))
                entries[key] = (e, ftype, None)
                e.pack(side='left', fill='x', expand=True)
                text_scroll.pack(side='right', fill='y')
            else:  # 'entry'
                e = ttk.Entry(row, width=52, font=('Segoe UI', 10))
                if default not in (None, "") and not isinstance(default, list):
                    e.insert(0, str(default))
                entries[key] = (e, ftype, None)
                e.pack(side='left', padx=6, fill='x', expand=True)

        # Connect template bar to form entries
        if template_bar:
            template_bar.set_form_entries(entries)

        # Status label inside form (shows errors without closing)
        form_status = tk.Label(inner, text="", bg='white', fg=COLORS['danger'],
                               font=('Segoe UI', 10), anchor='w',
                               justify='left', wraplength=660)
        form_status.pack(fill='x', pady=(8, 0))

        def _save(event=None):
            try:
                vals = {}
                for k, (widget, ftype, other_data) in entries.items():
                    if ftype == 'text':
                        vals[k] = widget.get('1.0', 'end-1c').strip()
                    elif ftype == 'combo_other':
                        v = widget.get().strip()
                        if v == "Other":
                            v2 = (other_data.get().strip() if other_data else "")
                            if not v2:
                                raise Exception(f"Please enter a value for '{k}'")
                            vals[k] = v2
                        else:
                            vals[k] = v
                    elif ftype == 'combo_multi':
                        # Get selected checkboxes and join with comma
                        checkbox_vars = widget
                        selected = [opt for opt, var in checkbox_vars.items() if var.get()]
                        vals[k] = ', '.join(selected)
                    else:
                        vals[k] = widget.get().strip()

                for k, meta in field_meta.items():
                    value = str(vals.get(k, '') or '').strip()
                    validate_form_value(
                        k,
                        meta['label'],
                        value,
                        required=meta['required'],
                        numeric=meta['numeric'],
                        options=meta['options'],
                        strict_options=meta['strict_options'],
                    )

                on_save(vals)           # caller raises Exception on validation failure
                # Unbind wheel before closing to avoid ghost callbacks
                _unbind_wheel()
                win.destroy()
                messagebox.showinfo("Saved", "Record saved successfully!", parent=parent or self.root)
            except Exception as ex:
                form_status.config(text=str(ex))
            return 'break'

        btn_row = ttk.Frame(inner)
        btn_row.pack(fill='x', pady=15)
        ttk.Button(btn_row, text="Save", command=_save).pack(side='left', padx=4, ipadx=14)
        ttk.Button(btn_row, text="Cancel", command=_cancel).pack(side='left', padx=4, ipadx=14)

        def _focus_next(event):
            nxt = event.widget.tk_focusNext()
            if nxt:
                nxt.focus_set()
            return 'break'

        for widget, ftype, _other in entries.values():
            if ftype == 'combo_multi':
                continue
            if ftype != 'text':
                try:
                    widget.bind('<Return>', _focus_next, add='+')
                except Exception:
                    pass
            try:
                win.after_idle(widget.focus_set)
                break
            except Exception:
                pass
        win.bind('<Control-s>', _save)
        win.bind('<Control-S>', _save)
        win.bind('<Escape>', _cancel)

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _section_header(self, parent, title):
        f = tk.Frame(parent, bg=COLORS['primary'], height=42)
        # Don't use pack - caller will handle placement with grid
        f.grid_propagate(False)
        tk.Label(f, text=title, bg=COLORS['primary'], fg='white',
                 font=('Segoe UI', 12, 'bold')).pack(side='left', padx=16, pady=8)
        return f

    def _btn_style(self, kind='primary'):
        c = {
            'primary': COLORS['primary'],
            'success': COLORS['success'],
            'danger':  COLORS['danger'],
            'warning': COLORS['warning'],
        }
        col = c.get(kind, COLORS['primary'])
        return dict(bg=col, fg='white',
                    font=('Segoe UI', 9), relief='flat',
                    padx=10, pady=4, cursor='hand2',
                    activeforeground='white', activebackground=col)

    def _make_tree(self, parent, cols, row=0):
        """Create a treeview with working scrollbars. Returns the tree object.
        The tree frame is placed at the specified row."""
        parent.grid_rowconfigure(row, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        tree_container = ttk.Frame(parent)
        tree_container.grid(row=row, column=0, sticky='nsew', padx=8, pady=6)
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(
            tree_container,
            columns=cols,
            show='headings',
            selectmode='browse'
        )

        for c in cols:
            tree.heading(c, text=c, anchor='w')
            tree.column(c, width=max(110, len(c) * 12), minwidth=90,
                        anchor='w', stretch=False)

        vsb = ttk.Scrollbar(tree_container, orient='vertical', command=tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        enable_tree_cell_selection(tree, hsb, vsb)

        tree.bind('<Double-1>', lambda e, tr=tree: self._open_tree_row_details(tr, e), add='+')
        tree.bind('<Return>', lambda e, tr=tree: self._open_tree_row_details(tr), add='+')
        tree.bind('<Control-c>', lambda e, tr=tree: self._copy_selected_tree_row(tr), add='+')
        tree.bind('<Control-C>', lambda e, tr=tree: self._copy_selected_tree_row(tr), add='+')
        return tree

    def _selected_tree_item(self, tree):
        active = getattr(tree, '_active_cell', None)
        if active and tree.exists(active[0]):
            return active[0]
        selection = tree.selection()
        if selection:
            return selection[0]
        focus = tree.focus()
        return focus if focus else None

    def _open_tree_row_details(self, tree, event=None):
        if event is not None and tree.identify_region(event.x, event.y) not in ('cell', 'tree'):
            return
        item = self._selected_tree_item(tree)
        if not item:
            return

        cols = list(tree['columns'])
        values = list(tree.item(item, 'values'))
        lines = []
        for idx, col in enumerate(cols):
            heading = tree.heading(col).get('text') or col
            if heading == '':
                heading = col
            value = values[idx] if idx < len(values) else ''
            lines.append(f"{heading}\n{value if value not in (None, '') else '-'}")

        win = tk.Toplevel(self.root)
        win.title("Record Details")
        set_app_icon(win)
        fit_window_to_screen(win, 760, 560, min_w=560, min_h=380)
        win.configure(bg=COLORS['bg'])

        txt = scrolledtext.ScrolledText(
            win,
            wrap='word',
            font=('Segoe UI', 10),
            bg='white',
            fg=COLORS['dark'],
            relief='flat',
            padx=14,
            pady=12
        )
        txt.pack(fill='both', expand=True, padx=10, pady=10)
        txt.insert('1.0', "\n\n".join(lines))
        txt.configure(state='disabled')

        btns = ttk.Frame(win)
        btns.pack(fill='x', padx=10, pady=(0, 10))
        ttk.Button(btns, text="Copy", command=lambda: self._copy_text("\n\n".join(lines))).pack(side='left')
        ttk.Button(btns, text="Close", command=win.destroy).pack(side='right')

    def _copy_text(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except Exception:
            pass

    def _copy_selected_tree_row(self, tree):
        active = getattr(tree, '_active_cell', None)
        if active and tree.exists(active[0]):
            heading = getattr(tree, '_active_cell_heading', active[1])
            value = getattr(tree, '_active_cell_value', tree.set(active[0], active[1]))
            self._copy_text(f"{heading}: {value}")
            return 'break'
        item = self._selected_tree_item(tree)
        if not item:
            return 'break'
        cols = list(tree['columns'])
        values = list(tree.item(item, 'values'))
        row = []
        for idx, col in enumerate(cols):
            heading = tree.heading(col).get('text') or col
            value = values[idx] if idx < len(values) else ''
            row.append(f"{heading}: {value}")
        self._copy_text(" | ".join(row))
        return 'break'

    def _delete_record(self, table, tree):
        if not has_permission(self.role, 'delete'):
            messagebox.showerror("🚫 Access Denied",
                                 "You don't have permission to delete records.")
            return
        item = self._selected_tree_item(tree)
        if not item:
            messagebox.showwarning("Select", "Please select a record to delete")
            return
        row_id = tree.item(item)['values'][0]
        if messagebox.askyesno("🗑️ Confirm Delete",
                                f"Delete record #{row_id} from {table}?\nThis cannot be undone."):
            Database.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
            tree.delete(item)
            messagebox.showinfo("✅ Deleted", f"Record #{row_id} deleted.")
            self._build_dashboard_content()

    def _count(self, table):
        r = Database.execute(f"SELECT COUNT(*) c FROM {table}", fetch=True)
        return r[0]['c'] if r else 0

    def _sum(self, table, col):
        r = Database.execute(f"SELECT SUM({col}) s FROM {table}", fetch=True)
        return r[0]['s'] if r and r[0]['s'] else 0

    def _refresh_all(self):
        try:
            self._load_rent_req()
            self._load_rent_avail()
            if hasattr(self, "sale_req_tree"):
                self._load_sale_req()
            if hasattr(self, "sale_av_tree"):
                self._load_sale_avail()
            self._update_pipeline_counts()
            if hasattr(self, "dash_frame"):
                self._build_dashboard_content()
        except Exception:
            pass

    def _quick_search(self):
        win = tk.Toplevel(self.root)
        win.title("Find")
        set_app_icon(win)
        fit_window_to_screen(win, 1180, 620, min_w=800, min_h=420)
        win.grab_set()
        win.configure(bg=COLORS['bg'])

        # Search bar — packed at top
        sf = tk.Frame(win, bg=COLORS['bg'], pady=10)
        sf.pack(fill='x', padx=12)
        tk.Label(sf, text="🔍", bg=COLORS['bg'],
                 font=('Segoe UI', 14)).pack(side='left', padx=(0, 6))
        q = ttk.Entry(sf, font=('Segoe UI', 12))
        q.pack(side='left', fill='x', expand=True, ipady=5)
        q.focus_set()
        tk.Label(sf, text="Sort", bg=COLORS['bg'], fg=COLORS['secondary'],
                 font=('Segoe UI', 10)).pack(side='left', padx=(10, 4))
        category_var = tk.StringVar(value="All")
        category = ttk.Combobox(
            sf, textvariable=category_var, state='readonly', width=20,
            values=("All", "Rent Requirement", "Rent Availability", "Sale Requirement", "Sale Availability")
        )
        category.pack(side='left')

        status_lbl = tk.Label(
            win,
            text="Find by name, contact, property, location, budget, facilities, or remarks.",
            bg=COLORS['bg'], fg=COLORS['secondary'],
            font=('Segoe UI', 9), anchor='w'
        )
        status_lbl.pack(fill='x', padx=16, pady=(0, 6))

        # Results container — packed below search bar
        res_frame = tk.Frame(win, bg=COLORS['bg'])
        res_frame.pack(fill='both', expand=True, padx=12, pady=(0, 8))
        res_frame.grid_rowconfigure(0, weight=1)
        res_frame.grid_columnconfigure(0, weight=1)

        cols = (
            'Type', 'Sr No.', 'Date', 'Name', 'Client Status', 'Broker', 'Contact No.',
            'Property Requirement', 'Property Availability', 'Size', 'Budget/Rent/Demand',
            'Floor', 'Location', 'Facilities', 'Remarks'
        )
        tree = ttk.Treeview(res_frame, columns=cols, show='headings', height=18)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, minwidth=70)
        tree.column('Type', width=130)
        tree.column('Name', width=180)
        tree.column('Contact No.', width=130)
        tree.column('Property Requirement', width=160)
        tree.column('Property Availability', width=160)
        tree.column('Facilities', width=180)
        tree.column('Remarks', width=220)

        vsb = ttk.Scrollbar(res_frame, orient='vertical', command=tree.yview)
        hsb = ttk.Scrollbar(res_frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        enable_tree_cell_selection(tree, hsb, vsb)

        sources = [
            ("Rent Requirement", "rent_requirements"),
            ("Rent Availability", "rent_availability"),
            ("Sale Requirement", "sale_requirements"),
            ("Sale Availability", "sale_availability"),
        ]
        if self._is_staff_restricted():
            allowed_sources = {
                "rent_requirements", "rent_availability",
                "sale_requirements", "sale_availability",
            }
            sources = [src for src in sources if src[1] in allowed_sources]

        def quote_ident(name):
            return '"' + str(name).replace('"', '""') + '"'

        def first_value(row, fields):
            keys = row.keys()
            for field in fields:
                if field in keys and row[field] not in (None, ""):
                    return str(row[field])
            return "-"

        def result_values(src, table, row):
            if table in ("rent_requirements", "sale_requirements"):
                return (
                    src,
                    first_value(row, ("id",)),
                    first_value(row, ("date", "date_created", "created_at")),
                    first_value(row, ("client_name",)),
                    first_value(row, ("client_status",)) if "client_status" in row.keys() else "Client",
                    first_value(row, ("broker", "preferred_broker", "client_broker")),
                    first_value(row, ("contact", "contact_phone")),
                    first_value(row, ("property_requires", "property_type")),
                    "",
                    first_value(row, ("size", "size_beds", "sq_ft", "sq_ft_yards")),
                    first_value(row, ("budget", "budget_max", "budget_min")),
                    first_value(row, ("floor", "floor_no")),
                    first_value(row, ("location",)),
                    first_value(row, ("facilities",)),
                    first_value(row, ("remarks", "description", "notes")),
                )
            amount_fields = ("monthly_rent",) if table == "rent_availability" else ("demand", "asking_price")
            return (
                src,
                first_value(row, ("id",)),
                first_value(row, ("date", "date_posted", "created_at")),
                first_value(row, ("owner_name",)),
                "",
                first_value(row, ("broker", "posted_by_broker", "client_broker", "posted_by")),
                first_value(row, ("contact", "contact_phone")),
                "",
                first_value(row, ("property_availability", "property_type")),
                first_value(row, ("size", "size_beds", "sq_ft", "sq_ft_yards")),
                first_value(row, amount_fields),
                first_value(row, ("floor", "floor_no")),
                first_value(row, ("location",)),
                first_value(row, ("facilities",)),
                first_value(row, ("remarks", "description", "notes")),
            )

        def match_summary(row, searchable_cols, term_lower):
            matches = []
            for col in searchable_cols:
                value = row[col]
                if value is None:
                    continue
                text = str(value).strip()
                if term_lower in text.lower():
                    matches.append(f"{col}: {text[:70]}")
                if len(matches) >= 2:
                    break
            return " | ".join(matches) if matches else "-"

        def do_search(*args):
            tree.delete(*tree.get_children())
            term = q.get().strip()
            if len(term) < 1:
                status_lbl.config(text="Type at least 1 character to search.")
                return
            term_lower = term.lower()
            pattern = f"%{term_lower}%"
            total = 0
            errors = []
            selected = category_var.get()
            active_sources = [src for src in sources if selected == "All" or src[0] == selected]
            status_lbl.config(text=f"Finding \"{term}\"...")
            win.update_idletasks()

            try:
                conn = Database.get_connection()
            except Exception as exc:
                tree.insert('', 'end', values=(
                    "Error", "-", "", "Database unavailable", "", "", "", "", "", "", "", "", "", "", str(exc)
                ))
                status_lbl.config(text=f"Search failed: {exc}")
                return

            try:
                for src, table in active_sources:
                    try:
                        table_info = conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
                        searchable_cols = [col['name'] for col in table_info]
                        if not searchable_cols:
                            errors.append(f"{src}: table has no searchable columns")
                            continue
                        where_sql = " OR ".join(
                            f"LOWER(CAST(COALESCE({quote_ident(col)}, '') AS TEXT)) LIKE ?"
                            for col in searchable_cols
                        )
                        source_text = f"{src} {table.replace('_', ' ')}".lower()
                        if term_lower in source_text:
                            sql = f"SELECT * FROM {quote_ident(table)} ORDER BY id DESC LIMIT 60"
                            params = ()
                        else:
                            sql = (
                                f"SELECT * FROM {quote_ident(table)} "
                                f"WHERE {where_sql} "
                                f"ORDER BY id DESC LIMIT 60"
                            )
                            params = tuple([pattern] * len(searchable_cols))
                        rows = conn.execute(sql, params).fetchall()
                        for r in rows:
                            tree.insert('', 'end', values=result_values(src, table, r))
                            total += 1
                    except Exception as exc:
                        errors.append(f"{src}: {exc}")
            finally:
                conn.close()

            if total == 0:
                tree.insert('', 'end', values=(
                    "No match", "-", "", "No records found", "", "", "", "", "", "", "", "", "", "",
                    f"Try another name, phone, location, amount, facility, or remark for \"{term}\"."
                ))
                message = f"No records matched \"{term}\" in {selected}."
            else:
                message = f"Found {total} result{'s' if total != 1 else ''} for \"{term}\" in {selected}"
            if errors:
                message += f" | Skipped {len(errors)} source{'s' if len(errors) != 1 else ''}: " + "; ".join(errors[:2])
            status_lbl.config(text=message)

        tk.Button(sf, text="Find", command=do_search,
                  bg=COLORS['primary'], fg='white',
                  font=('Segoe UI', 10, 'bold'),
                  relief='flat', padx=16, pady=4, cursor='hand2').pack(side='left', padx=(6, 0))

        q.bind('<Return>', do_search)
        q.bind('<KeyRelease>', lambda e: do_search() if len(q.get().strip()) >= 2 else None)
        category.bind('<<ComboboxSelected>>', lambda e: do_search() if q.get().strip() else None)
        # Allow double-click to close and show record detail
        def on_double_click(e):
            sel = tree.selection()
            if sel:
                src = tree.item(sel[0])['values'][0]
                rid = tree.item(sel[0])['values'][1]
                win.destroy()
                messagebox.showinfo("📍 Navigate", f"Navigate to {src} #{rid}?\n(Select the relevant tab manually to view/edit)")
        tree.bind('<Double-1>', on_double_click)

    def _export_tree(self, tree, name):
        fp = filedialog.asksaveasfilename(
            defaultextension='.csv',
            initialfile=f"{name}_{datetime.now().strftime('%Y%m%d')}.csv",
            filetypes=[('CSV Files', '*.csv')])
        if not fp:
            return
        try:
            with open(fp, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow([tree.heading(c)['text'] for c in tree['columns']])
                for child in tree.get_children():
                    w.writerow(tree.item(child)['values'])
            messagebox.showinfo("✅ Exported", f"Data exported to:\n{fp}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _export_csv(self):
        tables = ['rent_requirements','rent_availability','income_transactions',
                  'sale_requirements','sale_availability',
                  'expense_transactions','employees','clients','properties']
        fp = filedialog.asksaveasfilename(defaultextension='.csv',
                                           filetypes=[('CSV Files', '*.csv')])
        if not fp:
            return
        base, ext = os.path.splitext(fp)
        for table in tables:
            rows = Database.execute(f"SELECT * FROM {table}", fetch=True) or []
            if rows:
                with open(f"{base}_{table}{ext}", 'w', newline='', encoding='utf-8') as f:
                    w = csv.writer(f)
                    w.writerow(rows[0].keys())
                    for r in rows:
                        w.writerow(list(r))
        messagebox.showinfo("✅ Exported", f"All tables exported with prefix:\n{base}")

    def _backup_db(self):
        fp = filedialog.asksaveasfilename(
            defaultextension='.db',
            initialfile=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            filetypes=[('SQLite DB', '*.db')])
        if not fp:
            return
        if not os.path.exists(DB_PATH):
            messagebox.showerror("Error", f"Database file not found:\n{DB_PATH}")
            return
        shutil.copy(DB_PATH, fp)
        messagebox.showinfo("✅ Backup", f"Database backed up to:\n{fp}")

    def _user_guide(self):
        win = tk.Toplevel(self.root)
        win.title("📖 User Guide")
        set_app_icon(win)
        fit_window_to_screen(win, 600, 500, min_w=480, min_h=380)
        txt = scrolledtext.ScrolledText(win, font=('Segoe UI', 10), bg='white', wrap='word')
        txt.pack(fill='both', expand=True, padx=10, pady=10)
        guide = """
🏢 PROFESSIONAL REAL ESTATE CRM — USER GUIDE
════════════════════════════════════════════

📊 DASHBOARD
  • Overview of all key metrics and recent activity
  • Cards show counts and totals at a glance

🏢 PROPERTY DEALINGS
  • Requirements: Track what clients are looking for
  • Available: List properties available for rent
  • Add, Edit, Delete records (role-dependent)

🏗️ PROPERTIES
  • Full portfolio management
  • Track status: Available / Rented / Sold / Reserved

👥 CLIENTS
  • Manage tenants, buyers, sellers, investors
  • Track contact info and status

💰 FINANCIALS
  • Income: Record all income transactions
  • Expenses: Track all outgoing payments
  • Summary: View P&L at a glance

🧑‍💼 EMPLOYEES
  • Add and manage staff records
  • Mark daily attendance
  • Process and view salary payments

📈 REPORTS
  • Generate financial, property, employee reports
  • Export to TXT or PDF

⚙️ SETTINGS (Admin only)
  • Company info, currency, financials
  • User Management: Add users, set roles
  • Change password anytime from Settings menu

🔐 SECURITY
  • Roles: Super Admin > Admin > Manager > Staff > Viewer
  • Each role has specific permissions

🔄 TIPS
  • Use Edit > Refresh to reload data
  • Use Find (Edit menu) to find records fast
  • Backup database regularly from File menu
"""
        txt.insert('1.0', guide)
        txt.config(state='disabled')

    def _about(self):
        messagebox.showinfo("ℹ️ About", f"""Professional Real Estate CRM
Version 3.1 — Bug-Fix Edition

Built with Python & Tkinter
Database: SQLite
DB File: {DB_PATH}

Fixes in this version:
✓ Add records now works correctly
✓ Float conversion is robust (safe_float)
✓ Edit forms pre-populate correctly
✓ User management: toggle active/inactive fixed
✓ Password reset uses correct simpledialog import
✓ Change password inline error feedback

Company: {self.company_name}
User: {self.current_user['full_name']} ({self.role})
© {datetime.now().year} — All Rights Reserved""")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    Database.init_all()

    login_root = tk.Tk()
    login = LoginWindow(login_root)
    login_root.mainloop()

    if login.current_user is None:
        return

    main_root = tk.Tk()
    app = RealEstateCRM(main_root, login.current_user)
    main_root.mainloop()


if __name__ == "__main__":
    main()
