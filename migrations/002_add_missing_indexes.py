"""Migration 002: Add Missing Indexes

This migration adds all missing database indexes identified in the Phase 2
Engineering Audit (Section 21: Missing Indexes). These indexes will significantly
improve query performance for the RealEstate_CRM application.

Priority Levels:
- CRITICAL: Location, status/workflow, and contact indexes (affects search/filter)
- HIGH: Financial, employee, and composite indexes (affects reporting)
- MEDIUM: Workflow and additional composite indexes (affects specific modules)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def get_db_path() -> str:
    """Get the database path."""
    # Try to import from crm_core, fallback to default
    try:
        from crm_core import DB_PATH
        return str(DB_PATH)
    except ImportError:
        return "real_estate_crm.db"


def create_indexes(conn: sqlite3.Connection) -> dict[str, int]:
    """Create all missing indexes. Returns dict of index counts by category."""
    counts = {
        "location": 0,
        "status_workflow": 0,
        "contact": 0,
        "financial": 0,
        "employee": 0,
        "workflow": 0,
        "composite": 0,
        "date": 0,
        "budget": 0,
        "property_type": 0,
    }
    
    cursor = conn.cursor()
    
    # =========================================================================
    # CRITICAL: Location Indexes (Deal Tables)
    # =========================================================================
    location_indexes = [
        # Rent Requirements
        ("idx_rr_location", "rent_requirements", "location"),
        # Rent Availability
        ("idx_ra_location", "rent_availability", "location"),
        # Sale Requirements
        ("idx_sr_location", "sale_requirements", "location"),
        # Sale Availability
        ("idx_sa_location", "sale_availability", "location"),
    ]
    
    for idx_name, table, column in location_indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            counts["location"] += 1
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    # =========================================================================
    # HIGH: Date Indexes (Deal Tables)
    # =========================================================================
    date_indexes = [
        ("idx_rr_date", "rent_requirements", "date"),
        ("idx_ra_date", "rent_availability", "date"),
        ("idx_sr_date", "sale_requirements", "date"),
        ("idx_sa_date", "sale_availability", "date"),
    ]
    
    for idx_name, table, column in date_indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            counts["date"] += 1
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    # =========================================================================
    # HIGH: Budget/Price Indexes (Deal Tables)
    # =========================================================================
    budget_indexes = [
        ("idx_rr_budget", "rent_requirements", "budget"),
        ("idx_ra_rent", "rent_availability", "monthly_rent"),
        ("idx_sr_budget", "sale_requirements", "budget"),
        ("idx_sa_demand", "sale_availability", "demand"),
    ]
    
    for idx_name, table, column in budget_indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            counts["budget"] += 1
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    # =========================================================================
    # MEDIUM: Property Type Indexes (Deal Tables)
    # =========================================================================
    property_type_indexes = [
        ("idx_rr_property", "rent_requirements", "property_requires"),
        ("idx_ra_property", "rent_availability", "property_availability"),
        ("idx_sr_property", "sale_requirements", "property_requires"),
        ("idx_sa_property", "sale_availability", "property_availability"),
    ]
    
    for idx_name, table, column in property_type_indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            counts["property_type"] += 1
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    # =========================================================================
    # CRITICAL: Status/Workflow Indexes (Deal Tables)
    # =========================================================================
    status_workflow_indexes = [
        # Rent Requirements
        ("idx_rr_workflow", "rent_requirements", "workflow_stage"),
        ("idx_rr_priority", "rent_requirements", "priority"),
        # Rent Availability
        ("idx_ra_workflow", "rent_availability", "workflow_stage"),
        ("idx_ra_priority", "rent_availability", "priority"),
        # Sale Requirements
        ("idx_sr_workflow", "sale_requirements", "workflow_stage"),
        ("idx_sr_priority", "sale_requirements", "priority"),
        # Sale Availability
        ("idx_sa_workflow", "sale_availability", "workflow_stage"),
        ("idx_sa_priority", "sale_availability", "priority"),
    ]
    
    for idx_name, table, column in status_workflow_indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            counts["status_workflow"] += 1
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    # =========================================================================
    # CRITICAL: Contact Indexes (Deal Tables + Clients)
    # =========================================================================
    contact_indexes = [
        # Rent Requirements
        ("idx_rr_client_name", "rent_requirements", "client_name"),
        ("idx_rr_contact_phone", "rent_requirements", "contact_phone"),
        # Rent Availability
        ("idx_ra_owner_name", "rent_availability", "owner_name"),
        ("idx_ra_owner_phone", "rent_availability", "owner_phone"),
        # Sale Requirements
        ("idx_sr_client_name", "sale_requirements", "client_name"),
        ("idx_sr_contact_phone", "sale_requirements", "contact_phone"),
        # Sale Availability
        ("idx_sa_owner_name", "sale_availability", "owner_name"),
        ("idx_sa_owner_phone", "sale_availability", "owner_phone"),
        # Clients
        ("idx_client_name", "clients", "client_name"),
        ("idx_client_phone", "clients", "phone"),
        ("idx_client_type", "clients", "client_type"),
        ("idx_client_status", "clients", "status"),
        # Properties
        ("idx_prop_location", "properties", "location"),
        ("idx_prop_type", "properties", "property_type"),
        ("idx_prop_status", "properties", "status"),
        ("idx_prop_owner", "properties", "owner_name"),
        ("idx_prop_owner_contact", "properties", "owner_contact"),
    ]
    
    for idx_name, table, column in contact_indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            counts["contact"] += 1
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    # =========================================================================
    # HIGH: Financial Indexes
    # =========================================================================
    financial_indexes = [
        # Income Transactions
        ("idx_income_date", "income_transactions", "transaction_date"),
        ("idx_income_type", "income_transactions", "income_type"),
        # Expense Transactions
        ("idx_expense_date", "expense_transactions", "transaction_date"),
        ("idx_expense_category", "expense_transactions", "expense_category"),
    ]
    
    for idx_name, table, column in financial_indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            counts["financial"] += 1
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    # =========================================================================
    # HIGH: Employee/HR Indexes
    # =========================================================================
    employee_indexes = [
        # Employees
        ("idx_emp_name", "employees", "full_name"),
        ("idx_emp_dept", "employees", "department"),
        ("idx_emp_status", "employees", "status"),
        ("idx_emp_phone", "employees", "phone"),
        # Attendance
        ("idx_att_status", "attendance", "status"),
        ("idx_att_date", "attendance", "date"),
        # Salary Payments
        ("idx_sal_emp", "salary_payments", "employee_id"),
        ("idx_sal_date", "salary_payments", "payment_date"),
    ]
    
    for idx_name, table, column in employee_indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            counts["employee"] += 1
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    # =========================================================================
    # MEDIUM: Workflow Table Indexes
    # =========================================================================
    workflow_indexes = [
        # Workflow Instances
        ("idx_wf_inst_status", "wf_instances", "status"),
        ("idx_wf_inst_assignee", "wf_instances", "current_assignee"),
        # Workflow Tasks
        ("idx_wf_task_status", "wf_tasks", "status"),
        ("idx_wf_task_assignee", "wf_tasks", "assigned_to"),
        # Workflow Approvals
        ("idx_wf_approval_status", "wf_approvals", "status"),
        # Workflow Audit Log
        ("idx_wf_audit_action", "wf_audit_log", "action"),
        ("idx_wf_audit_performer", "wf_audit_log", "performed_by"),
        ("idx_wf_audit_reference", "wf_audit_log", "reference_table", "reference_id"),
    ]
    
    for idx_info in workflow_indexes:
        idx_name = idx_info[0]
        table = idx_info[1]
        columns = idx_info[2:]
        try:
            cols_str = ", ".join(columns)
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({cols_str})")
            counts["workflow"] += 1
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    # =========================================================================
    # HIGH: Composite Indexes (Common Query Patterns)
    # =========================================================================
    composite_indexes = [
        # Soft delete + location (most common query pattern)
        ("idx_rr_active_location", "rent_requirements", "is_deleted", "location"),
        ("idx_ra_active_location", "rent_availability", "is_deleted", "location", "status"),
        ("idx_sr_active_location", "sale_requirements", "is_deleted", "location"),
        ("idx_sa_active_location", "sale_availability", "is_deleted", "location", "status"),
        # Soft delete + status/workflow
        ("idx_rr_active_workflow", "rent_requirements", "is_deleted", "workflow_stage"),
        ("idx_ra_active_status", "rent_availability", "is_deleted", "status"),
        ("idx_sr_active_workflow", "sale_requirements", "is_deleted", "workflow_stage"),
        ("idx_sa_active_status", "sale_availability", "is_deleted", "status"),
        # Employee attendance lookup
        ("idx_att_emp_date_status", "attendance", "employee_id", "date", "status"),
        # Financial date + category
        ("idx_income_date_type", "income_transactions", "transaction_date", "income_type"),
        ("idx_expense_date_cat", "expense_transactions", "transaction_date", "expense_category"),
        # Salary month lookup
        ("idx_sal_month_year", "salary_payments", "month", "year"),
    ]
    
    for idx_info in composite_indexes:
        idx_name = idx_info[0]
        table = idx_info[1]
        columns = idx_info[2:]
        try:
            cols_str = ", ".join(columns)
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({cols_str})")
            counts["composite"] += 1
        except sqlite3.Error as e:
            print(f"Warning: Could not create index {idx_name}: {e}")
    
    conn.commit()
    return counts


def run_migration(db_path: str | None = None) -> dict[str, int]:
    """Run the migration. Returns counts of indexes created by category."""
    if db_path is None:
        db_path = get_db_path()
    
    print(f"Running migration 002: Add Missing Indexes")
    print(f"Database: {db_path}")
    print("-" * 60)
    
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        
        counts = create_indexes(conn)
        conn.close()
        
        total = sum(counts.values())
        print("-" * 60)
        print(f"Migration complete! Created {total} indexes:")
        print(f"  - Location indexes: {counts['location']}")
        print(f"  - Date indexes: {counts['date']}")
        print(f"  - Budget/Price indexes: {counts['budget']}")
        print(f"  - Property Type indexes: {counts['property_type']}")
        print(f"  - Status/Workflow indexes: {counts['status_workflow']}")
        print(f"  - Contact indexes: {counts['contact']}")
        print(f"  - Financial indexes: {counts['financial']}")
        print(f"  - Employee/HR indexes: {counts['employee']}")
        print(f"  - Workflow indexes: {counts['workflow']}")
        print(f"  - Composite indexes: {counts['composite']}")
        
        return counts
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
