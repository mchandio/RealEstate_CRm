"""
Real Estate CRM - Database Schema & Setup
Handles: Rent, Sale, Financial, Employee, and Transaction Records
"""

import sqlite3
import os
import logging
from datetime import datetime

# Configuration
DB_NAME = "real_estate_crm.db"
LOG_FILE = "crm.log"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                   format="%(asctime)s - %(levelname)s - %(message)s")

class DatabaseSetup:
    """Initialize and manage CRM database"""
    
    def __init__(self, db_path=DB_NAME):
        self.db_path = db_path
    
    def init_database(self):
        """Create all tables for the CRM system"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # ═════════════════════════════════════════════════════════════════
        # RENT MANAGEMENT TABLES
        # ═════════════════════════════════════════════════════════════════
        c.execute('''
        CREATE TABLE IF NOT EXISTS rent_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_created TEXT,
            client_name TEXT NOT NULL,
            client_status TEXT DEFAULT 'Client',
            broker TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            property_type TEXT,
            size_beds INTEGER,
            size_bath INTEGER,
            sq_ft REAL,
            floor_no INTEGER,
            location TEXT NOT NULL,
            budget_min REAL,
            budget_max REAL,
            maintenance_budget REAL,
            facilities TEXT,
            description TEXT,
            preferred_broker TEXT,
            workflow_stage TEXT DEFAULT 'Lead',
            priority TEXT DEFAULT 'Medium',
            next_follow_up TEXT,
            assigned_to TEXT,
            last_contacted TEXT,
            deal_probability REAL DEFAULT 10.0,
            expected_close_value REAL DEFAULT 0,
            closed_at TIMESTAMP,
            lost_reason TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS rent_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_posted TEXT,
            owner_name TEXT NOT NULL,
            contact_phone TEXT,
            contact_email TEXT,
            property_type TEXT,
            size_beds INTEGER,
            size_bath INTEGER,
            sq_ft REAL,
            floor_no INTEGER,
            location TEXT NOT NULL,
            monthly_rent REAL,
            maintenance_charge REAL,
            facilities TEXT,
            description TEXT,
            posted_by_broker TEXT,
            workflow_stage TEXT DEFAULT 'Lead',
            priority TEXT DEFAULT 'Medium',
            next_follow_up TEXT,
            assigned_to TEXT,
            last_contacted TEXT,
            deal_probability REAL DEFAULT 10.0,
            expected_close_value REAL DEFAULT 0,
            closed_at TIMESTAMP,
            lost_reason TEXT,
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS rent_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requirement_id INTEGER NOT NULL,
            availability_id INTEGER NOT NULL,
            match_score REAL,
            match_reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(requirement_id) REFERENCES rent_requirements(id),
            FOREIGN KEY(availability_id) REFERENCES rent_availability(id)
        )
        ''')
        
        # ═════════════════════════════════════════════════════════════════
        # SALE MANAGEMENT TABLES
        # ═════════════════════════════════════════════════════════════════
        c.execute('''
        CREATE TABLE IF NOT EXISTS sale_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_created TEXT,
            client_name TEXT NOT NULL,
            client_status TEXT DEFAULT 'Client',
            broker TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            property_type TEXT,
            size_beds INTEGER,
            size_bath INTEGER,
            sq_ft REAL,
            location TEXT NOT NULL,
            budget_min REAL,
            budget_max REAL,
            facilities TEXT,
            description TEXT,
            preferred_broker TEXT,
            workflow_stage TEXT DEFAULT 'Lead',
            priority TEXT DEFAULT 'Medium',
            next_follow_up TEXT,
            assigned_to TEXT,
            last_contacted TEXT,
            deal_probability REAL DEFAULT 10.0,
            expected_close_value REAL DEFAULT 0,
            closed_at TIMESTAMP,
            lost_reason TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS sale_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_posted TEXT,
            owner_name TEXT NOT NULL,
            contact_phone TEXT,
            contact_email TEXT,
            property_type TEXT,
            size_beds INTEGER,
            size_bath INTEGER,
            sq_ft REAL,
            location TEXT NOT NULL,
            asking_price REAL,
            facilities TEXT,
            description TEXT,
            posted_by_broker TEXT,
            workflow_stage TEXT DEFAULT 'Lead',
            priority TEXT DEFAULT 'Medium',
            next_follow_up TEXT,
            assigned_to TEXT,
            last_contacted TEXT,
            deal_probability REAL DEFAULT 10.0,
            expected_close_value REAL DEFAULT 0,
            closed_at TIMESTAMP,
            lost_reason TEXT,
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # ═════════════════════════════════════════════════════════════════
        # FINANCIAL MANAGEMENT TABLES
        # ═════════════════════════════════════════════════════════════════
        c.execute('''
        CREATE TABLE IF NOT EXISTS income_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date TEXT NOT NULL,
            property_id INTEGER,
            income_type TEXT NOT NULL,
            amount REAL NOT NULL,
            tenant_name TEXT,
            description TEXT,
            receipt_no TEXT,
            recorded_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS expense_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date TEXT NOT NULL,
            property_id INTEGER,
            expense_category TEXT NOT NULL,
            amount REAL NOT NULL,
            vendor_name TEXT,
            description TEXT,
            invoice_no TEXT,
            approved_by TEXT,
            recorded_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS financial_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            year INTEGER NOT NULL,
            total_income REAL DEFAULT 0,
            total_expense REAL DEFAULT 0,
            net_profit REAL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(month, year)
        )
        ''')
        
        # ═════════════════════════════════════════════════════════════════
        # EMPLOYEE MANAGEMENT TABLES
        # ═════════════════════════════════════════════════════════════════
        c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            contact_phone TEXT,
            phone TEXT,
            email TEXT,
            position TEXT NOT NULL,
            hire_date TEXT NOT NULL,
            base_salary REAL NOT NULL,
            commission_rate REAL DEFAULT 5.0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS employee_commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            deal_type TEXT,
            deal_id INTEGER,
            commission_amount REAL NOT NULL,
            deal_value REAL,
            commission_date TEXT NOT NULL,
            status TEXT DEFAULT 'earned',
            paid_on TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS employee_payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            payroll_month TEXT NOT NULL,
            payroll_year INTEGER NOT NULL,
            base_salary REAL,
            commissions_earned REAL DEFAULT 0,
            bonuses REAL DEFAULT 0,
            deductions REAL DEFAULT 0,
            net_salary REAL,
            paid_date TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id),
            UNIQUE(employee_id, payroll_month, payroll_year)
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS employee_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT,
            hours_worked REAL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS employee_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            review_date TEXT NOT NULL,
            rating REAL,
            deals_closed INTEGER,
            revenue_generated REAL,
            notes TEXT,
            reviewed_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
        ''')
        
        # ═════════════════════════════════════════════════════════════════
        # DATA IMPORT & AUDIT TABLES
        # ═════════════════════════════════════════════════════════════════
        c.execute('''
        CREATE TABLE IF NOT EXISTS data_imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_type TEXT NOT NULL,
            file_name TEXT,
            total_records INTEGER,
            successful_records INTEGER,
            failed_records INTEGER,
            import_date TEXT NOT NULL,
            imported_by TEXT,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            table_name TEXT,
            record_id INTEGER,
            old_value TEXT,
            new_value TEXT,
            user TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        workflow_columns = [
            ("workflow_stage", "TEXT DEFAULT 'Lead'"),
            ("priority", "TEXT DEFAULT 'Medium'"),
            ("next_follow_up", "TEXT"),
            ("assigned_to", "TEXT"),
            ("last_contacted", "TEXT"),
            ("deal_probability", "REAL DEFAULT 10.0"),
            ("expected_close_value", "REAL DEFAULT 0"),
            ("closed_at", "TIMESTAMP"),
            ("lost_reason", "TEXT"),
        ]
        phase1_common_columns = [
            ("size", "TEXT"),
            ("measurement", "TEXT"),
            ("measurement_unit", "TEXT"),
            ("contact", "TEXT"),
            ("facilities", "TEXT"),
            ("location", "TEXT"),
        ]
        requirement_columns = [
            ("client_status", "TEXT DEFAULT 'Client'"),
            ("broker", "TEXT"),
            ("property_requires", "TEXT"),
            ("budget", "REAL DEFAULT 0"),
        ]
        availability_columns = [
            ("client_broker", "TEXT DEFAULT 'Owner'"),
            ("property_availability", "TEXT"),
            ("owner_phone", "TEXT"),
            ("building_name", "TEXT"),
        ]
        for table in ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability"):
            c.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in c.fetchall()}
            for column, ddl in phase1_common_columns:
                if column not in existing:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                    existing.add(column)
            for column, ddl in workflow_columns:
                if column not in existing:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                    existing.add(column)
            if table in {"rent_requirements", "sale_requirements"}:
                for column, ddl in requirement_columns:
                    if column not in existing:
                        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                        existing.add(column)
                c.execute(f"UPDATE {table} SET client_status='Client' WHERE client_status IS NULL OR client_status=''")
                if "preferred_broker" in existing:
                    c.execute(f"""UPDATE {table}
                                  SET broker=preferred_broker
                                  WHERE (broker IS NULL OR broker='')
                                    AND preferred_broker IS NOT NULL AND preferred_broker<>''""")
            else:
                for column, ddl in availability_columns:
                    if column not in existing:
                        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                        existing.add(column)
                c.execute(f"UPDATE {table} SET client_broker='Owner' WHERE client_broker IS NULL OR client_broker=''")
            c.execute(f"UPDATE {table} SET workflow_stage='Lead' WHERE workflow_stage IS NULL OR workflow_stage=''")
            c.execute(f"UPDATE {table} SET priority='Medium' WHERE priority IS NULL OR priority=''")

        c.execute("PRAGMA table_info(employees)")
        employee_cols = {row[1] for row in c.fetchall()}
        if "phone" not in employee_cols:
            c.execute("ALTER TABLE employees ADD COLUMN phone TEXT")
        if "contact_phone" in employee_cols:
            c.execute("UPDATE employees SET phone=contact_phone WHERE (phone IS NULL OR phone='') AND contact_phone IS NOT NULL")
        
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully")
        print("✅ Database schema created successfully!")
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def drop_all_tables(self):
        """Drop all tables (use with caution - for development only)"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        for table in tables:
            c.execute(f"DROP TABLE IF EXISTS {table[0]}")
        conn.commit()
        conn.close()
        logging.warning("All tables dropped")
        print("⚠️ All tables have been dropped!")


if __name__ == "__main__":
    db = DatabaseSetup()
    db.init_database()
