"""Migrate data from legacy real_estate_crm.db to the new SQLAlchemy database."""
import sqlite3
import sys
from datetime import datetime
from backend.database import SessionLocal, init_db
from backend.models import (
    RentRequirement, RentAvailability,
    SaleRequirement, SaleAvailability,
    IncomeTransaction, ExpenseTransaction,
    Employee, Client, Property,
)

LEGACY_DB = "real_estate_crm.db"
TABLE_MAP = {
    "rent_requirements": (RentRequirement, "date", "client_name", "contact", "property_requires", "size", "measurement", "budget", "floor", "location", "option1", "option2", "facilities", "client_broker", "bachelor_family", "remarks", "workflow_stage", "priority", "next_follow_up", "assigned_to", "deal_probability", "expected_close_value"),
    "rent_availability": (RentAvailability, "date", "owner_name", "contact", "property_availability", "size", "measurement", "monthly_rent", "floor", "location", "deposit", "maintenance_charge", "facilities", "client_broker", "bachelor_family", "remarks", "workflow_stage", "priority", "next_follow_up", "assigned_to", "deal_probability", "expected_close_value"),
    "sale_requirements": (SaleRequirement, "date", "client_name", "contact", "property_requires", "size", "measurement", "budget", "floor", "location", "option1", "option2", "facilities", "client_broker", "bachelor_family", "remarks", "workflow_stage", "priority", "next_follow_up", "assigned_to", "deal_probability", "expected_close_value"),
    "sale_availability": (SaleAvailability, "date", "owner_name", "contact", "property_availability", "size", "measurement", "demand", "floor", "location", "option1", "option2", "facilities", "client_broker", "bachelor_family", "remarks", "workflow_stage", "priority", "next_follow_up", "assigned_to", "deal_probability", "expected_close_value"),
    "income": (IncomeTransaction, "transaction_date", "income_type", "amount", "tenant_name", "description", "receipt_no", "payment_method"),
    "expenses": (ExpenseTransaction, "transaction_date", "expense_category", "amount", "vendor_name", "description", "invoice_no", "payment_method"),
    "employees": (Employee, "employee_id", "full_name", "cnic", "phone", "email", "position", "department", "hire_date", "base_salary", "commission_rate", "status", "address", "notes"),
    "clients": (Client, "client_name", "cnic", "phone", "email", "address", "client_type", "notes", "status"),
    "properties": (Property, "property_code", "title", "property_type", "status", "owner_name", "owner_contact", "location", "area", "floor", "monthly_rent", "sale_price", "maintenance_charge", "facilities", "description"),
}


def get_legacy_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def migrate():
    init_db()
    db = SessionLocal()
    legacy = sqlite3.connect(LEGACY_DB)
    legacy.row_factory = sqlite3.Row
    cursor = legacy.cursor()

    total = 0
    for legacy_table, (model_class, *field_names) in TABLE_MAP.items():
        try:
            legacy_cols = get_legacy_columns(cursor, legacy_table)
        except Exception:
            print(f"  Table '{legacy_table}' not found in legacy DB, skipping.")
            continue

        cursor.execute(f"SELECT * FROM {legacy_table}")
        rows = cursor.fetchall()
        count = 0
        for row in rows:
            data = {}
            for col in legacy_cols:
                if col in field_names:
                    val = row[col]
                    if isinstance(val, str):
                        val = val.strip()
                    data[col] = val
            if not data:
                continue
            # Map legacy column names to new model
            col_map = {}
            for f in field_names:
                if f in legacy_cols:
                    col_map[f] = f
            instance = model_class(**{k: data[k] for k in col_map.values() if k in data})
            db.add(instance)
            count += 1
        db.commit()
        print(f"  Migrated {count} rows from '{legacy_table}'")
        total += count

    legacy.close()
    db.close()
    print(f"\nMigration complete. {total} total records migrated.")


if __name__ == "__main__":
    migrate()
