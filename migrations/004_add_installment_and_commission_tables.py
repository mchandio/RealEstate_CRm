"""Migration 004: Add Installment Tracking and Commission Calculation Tables

This migration adds tables for:
1. Installment Tracking - Track installment schedules and payments for property deals
2. Commission Calculation - Calculate and track agent commissions for deals

Based on Phase 2 audit findings (Section 26: Feature Gaps), these are critical
missing features for a real estate CRM.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def get_db_path() -> str:
    """Get the database path."""
    try:
        from crm_core import DB_PATH
        return str(DB_PATH)
    except ImportError:
        return "real_estate_crm.db"


def create_tables(conn: sqlite3.Connection) -> dict[str, int]:
    """Create installment and commission tables. Returns counts."""
    counts = {
        "installment_schedules": 0,
        "installment_payments": 0,
        "commissions": 0,
        "commission_splits": 0,
    }
    
    cursor = conn.cursor()
    
    # =========================================================================
    # Installment Schedule Table
    # =========================================================================
    # Note: deal_id does not have a hardcoded FK constraint because it can reference
    # either rent_availability or sale_availability depending on deal_type.
    # Referential integrity is handled in application code.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS installment_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id INTEGER NOT NULL,
            deal_type TEXT NOT NULL,  -- 'rent_availability' or 'sale_availability'
            deal_table TEXT NOT NULL,  -- Source table name
            total_amount REAL DEFAULT 0,
            installment_count INTEGER DEFAULT 0,
            installment_amount REAL DEFAULT 0,
            frequency TEXT DEFAULT 'monthly',  -- monthly, quarterly, yearly
            start_date TEXT NOT NULL,
            end_date TEXT,
            status TEXT DEFAULT 'Active',  -- Active, Completed, Cancelled, Defaulted
            notes TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            last_edited_by TEXT,
            last_edited_at TEXT
        )
    """)
    counts["installment_schedules"] = 1
    
    # =========================================================================
    # Installment Payments Table
    # =========================================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS installment_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            installment_number INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            amount REAL DEFAULT 0,
            paid_amount REAL DEFAULT 0,
            paid_date TEXT,
            status TEXT DEFAULT 'Pending',  -- Pending, Paid, Late, Partial, Waived
            penalty REAL DEFAULT 0,
            late_days INTEGER DEFAULT 0,
            payment_method TEXT,
            receipt_no TEXT,
            notes TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (schedule_id) REFERENCES installment_schedules(id) ON DELETE RESTRICT
        )
    """)
    counts["installment_payments"] = 1
    
    # =========================================================================
    # Commissions Table
    # =========================================================================
    # Note: deal_id does not have a hardcoded FK constraint because it can reference
    # either rent_availability or sale_availability depending on deal_type.
    # Referential integrity is handled in application code.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id INTEGER NOT NULL,
            deal_type TEXT NOT NULL,  -- 'rent_availability' or 'sale_availability'
            deal_table TEXT NOT NULL,  -- Source table name
            deal_amount REAL DEFAULT 0,
            commission_rate REAL DEFAULT 5.0,
            total_commission REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',  -- Pending, Approved, Paid, Cancelled
            approved_by TEXT,
            approved_at TEXT,
            paid_at TEXT,
            payment_method TEXT,
            notes TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            last_edited_by TEXT,
            last_edited_at TEXT
        )
    """)
    counts["commissions"] = 1
    
    # =========================================================================
    # Commission Splits Table (for multiple agents)
    # =========================================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commission_splits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commission_id INTEGER NOT NULL,
            agent_id INTEGER,
            agent_name TEXT NOT NULL,
            split_percentage REAL DEFAULT 100.0,
            split_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',  -- Pending, Paid
            paid_at TEXT,
            payment_method TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (commission_id) REFERENCES commissions(id) ON DELETE RESTRICT,
            FOREIGN KEY (agent_id) REFERENCES employees(id) ON DELETE SET NULL
        )
    """)
    counts["commission_splits"] = 1
    
    # =========================================================================
    # Create Indexes
    # =========================================================================
    indexes = [
        ("idx_inst_sched_deal", "installment_schedules", "deal_id"),
        ("idx_inst_sched_status", "installment_schedules", "status"),
        ("idx_inst_pay_schedule", "installment_payments", "schedule_id"),
        ("idx_inst_pay_status", "installment_payments", "status"),
        ("idx_inst_pay_due", "installment_payments", "due_date"),
        ("idx_comm_deal", "commissions", "deal_id"),
        ("idx_comm_status", "commissions", "status"),
        ("idx_comm_agent", "commission_splits", "agent_id"),
        ("idx_comm_split_comm", "commission_splits", "commission_id"),
    ]
    
    for idx_name, table, column in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    conn.commit()
    return counts


def run_migration(db_path: str | None = None) -> dict[str, int]:
    """Run the migration. Returns counts of tables created."""
    if db_path is None:
        db_path = get_db_path()
    
    print(f"Running migration 004: Add Installment and Commission Tables")
    print(f"Database: {db_path}")
    print("-" * 60)
    
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        
        counts = create_tables(conn)
        conn.close()
        
        total = sum(counts.values())
        print("-" * 60)
        print(f"Migration complete! Created {total} rows across tables:")
        print(f"  - Installment Schedules: {counts['installment_schedules']}")
        print(f"  - Installment Payments: {counts['installment_payments']}")
        print(f"  - Commissions: {counts['commissions']}")
        print(f"  - Commission Splits: {counts['commission_splits']}")
        
        return counts
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
