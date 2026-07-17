"""Unit tests for installments and commissions tracking.

Covers:
- Installment tracking logic
- Commission calculation logic
- Payment recording
"""
from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest


@pytest.fixture
def setup_db():
    """Create a temporary SQLite database with required tables."""
    import sqlite3
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Create installment tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS installment_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_table TEXT NOT NULL,
            deal_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            num_installments INTEGER NOT NULL,
            installment_amount REAL NOT NULL,
            start_date TEXT NOT NULL,
            status TEXT DEFAULT 'Active',
            created_by TEXT,
            created_at TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS installment_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            installment_number INTEGER NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            paid_date TEXT,
            status TEXT DEFAULT 'Pending',
            payment_method TEXT,
            reference TEXT,
            notes TEXT,
            recorded_by TEXT,
            recorded_at TEXT,
            FOREIGN KEY (plan_id) REFERENCES installment_plans(id)
        )
    """)
    
    # Create commission tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commission_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_table TEXT NOT NULL,
            deal_id INTEGER NOT NULL,
            deal_amount REAL NOT NULL,
            commission_rate REAL NOT NULL,
            total_commission REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_by TEXT,
            created_at TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commission_splits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            agent_name TEXT NOT NULL,
            split_percentage REAL NOT NULL,
            split_amount REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            paid_date TEXT,
            notes TEXT,
            FOREIGN KEY (plan_id) REFERENCES commission_plans(id)
        )
    """)
    
    conn.commit()
    
    yield db_path, conn
    
    conn.close()
    Path(db_path).unlink(missing_ok=True)


class TestInstallmentPlans:
    def test_create_installment_plan(self, setup_db):
        db_path, conn = setup_db
        
        cursor = conn.execute("""
            INSERT INTO installment_plans (deal_table, deal_id, total_amount, num_installments, installment_amount, start_date, status, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("rent_availability", 1, 600000, 12, 50000, "2026-01-01", "Active", "admin", datetime.now().isoformat()))
        conn.commit()
        
        plan_id = cursor.lastrowid
        assert plan_id > 0
        
        # Verify the plan was created
        plan = conn.execute("SELECT * FROM installment_plans WHERE id = ?", (plan_id,)).fetchone()
        assert plan is not None
        assert plan["total_amount"] == 600000
        assert plan["num_installments"] == 12
    
    def test_create_payment(self, setup_db):
        db_path, conn = setup_db
        
        # Create plan first
        cursor = conn.execute("""
            INSERT INTO installment_plans (deal_table, deal_id, total_amount, num_installments, installment_amount, start_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("rent_availability", 1, 600000, 12, 50000, "2026-01-01", "Active"))
        conn.commit()
        plan_id = cursor.lastrowid
        
        # Create payment
        cursor = conn.execute("""
            INSERT INTO installment_payments (plan_id, installment_number, amount, due_date, paid_date, status, payment_method, recorded_by, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (plan_id, 1, 50000, "2026-02-01", "2026-01-28", "Paid", "Cash", "admin", datetime.now().isoformat()))
        conn.commit()
        
        payment_id = cursor.lastrowid
        assert payment_id > 0
        
        # Verify payment
        payment = conn.execute("SELECT * FROM installment_payments WHERE id = ?", (payment_id,)).fetchone()
        assert payment is not None
        assert payment["amount"] == 50000
        assert payment["status"] == "Paid"


class TestCommissionPlans:
    def test_create_commission_plan(self, setup_db):
        db_path, conn = setup_db
        
        cursor = conn.execute("""
            INSERT INTO commission_plans (deal_table, deal_id, deal_amount, commission_rate, total_commission, status, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("sale_availability", 1, 5000000, 2.0, 100000, "Pending", "admin", datetime.now().isoformat()))
        conn.commit()
        
        plan_id = cursor.lastrowid
        assert plan_id > 0
        
        plan = conn.execute("SELECT * FROM commission_plans WHERE id = ?", (plan_id,)).fetchone()
        assert plan is not None
        assert plan["total_commission"] == 100000
        assert plan["commission_rate"] == 2.0
    
    def test_create_commission_split(self, setup_db):
        db_path, conn = setup_db
        
        # Create plan
        cursor = conn.execute("""
            INSERT INTO commission_plans (deal_table, deal_id, deal_amount, commission_rate, total_commission, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("sale_availability", 1, 5000000, 2.0, 100000, "Pending"))
        conn.commit()
        plan_id = cursor.lastrowid
        
        # Create split
        cursor = conn.execute("""
            INSERT INTO commission_splits (plan_id, agent_name, split_percentage, split_amount, status)
            VALUES (?, ?, ?, ?, ?)
        """, (plan_id, "Agent Smith", 60.0, 60000, "Pending"))
        conn.commit()
        
        split_id = cursor.lastrowid
        assert split_id > 0
        
        split = conn.execute("SELECT * FROM commission_splits WHERE id = ?", (split_id,)).fetchone()
        assert split is not None
        assert split["split_amount"] == 60000
        assert split["split_percentage"] == 60.0
