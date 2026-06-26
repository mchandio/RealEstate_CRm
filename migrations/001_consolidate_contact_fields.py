#!/usr/bin/env python
"""Safe Phase 1 data repair.

This migration does not rename or drop legacy columns. It adds canonical
columns and backfills them so old Desktop data and new Web data stay visible in
both UIs.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime


PHASE1_TABLES = ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability")


def backup_database(db_path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    with sqlite3.connect(db_path, timeout=30) as source, sqlite3.connect(backup_path) as dest:
        source.execute("PRAGMA busy_timeout=30000")
        source.backup(dest, pages=100, sleep=0.001)
    return backup_path


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def add_column(conn: sqlite3.Connection, table: str, existing: set[str], name: str, ddl: str) -> None:
    if name not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        existing.add(name)


def backfill_table(conn: sqlite3.Connection, table: str) -> None:
    existing = columns(conn, table)
    if table in {"rent_requirements", "sale_requirements"}:
        add_column(conn, table, existing, "contact_person", "TEXT")
        add_column(conn, table, existing, "contact_phone", "TEXT")
        if {"client_name", "contact_person"} <= existing:
            conn.execute(
                f"UPDATE {table} SET contact_person=client_name "
                "WHERE (contact_person IS NULL OR contact_person='') AND client_name IS NOT NULL"
            )
        if {"contact", "contact_phone"} <= existing:
            conn.execute(
                f"UPDATE {table} SET contact_phone=contact "
                "WHERE (contact_phone IS NULL OR contact_phone='') AND contact IS NOT NULL AND contact<>''"
            )
            conn.execute(
                f"UPDATE {table} SET contact=contact_phone "
                "WHERE (contact IS NULL OR contact='') AND contact_phone IS NOT NULL AND contact_phone<>''"
            )
        if "client_status" in existing:
            conn.execute(
                f"""UPDATE {table}
                    SET client_status=CASE
                        WHEN LOWER(client_status) IN ('o','owner') THEN 'Owner'
                        WHEN LOWER(client_status) IN ('b','broker','agent') THEN 'Broker'
                        WHEN client_status IS NULL OR client_status='' THEN 'Client'
                        WHEN LOWER(client_status)='client' THEN 'Client'
                        ELSE client_status
                    END"""
            )
        if {"budget", "budget_max"} <= existing:
            conn.execute(
                f"UPDATE {table} SET budget=budget_max "
                "WHERE (budget IS NULL OR budget=0) AND budget_max IS NOT NULL AND budget_max<>0"
            )
        if {"budget", "budget_min"} <= existing:
            conn.execute(
                f"UPDATE {table} SET budget=budget_min "
                "WHERE (budget IS NULL OR budget=0) AND budget_min IS NOT NULL AND budget_min<>0"
            )
    else:
        add_column(conn, table, existing, "owner_phone", "TEXT")
        add_column(conn, table, existing, "contact_phone", "TEXT")
        if {"contact", "owner_phone"} <= existing:
            conn.execute(
                f"UPDATE {table} SET owner_phone=contact "
                "WHERE (owner_phone IS NULL OR owner_phone='') AND contact IS NOT NULL AND contact<>''"
            )
            conn.execute(
                f"UPDATE {table} SET contact=owner_phone "
                "WHERE (contact IS NULL OR contact='') AND owner_phone IS NOT NULL AND owner_phone<>''"
            )
        if {"owner_phone", "contact_phone"} <= existing:
            conn.execute(
                f"UPDATE {table} SET contact_phone=owner_phone "
                "WHERE (contact_phone IS NULL OR contact_phone='') AND owner_phone IS NOT NULL AND owner_phone<>''"
            )
        if "client_broker" in existing:
            conn.execute(
                f"""UPDATE {table}
                    SET client_broker=CASE
                        WHEN LOWER(client_broker) IN ('c','client') THEN 'Client'
                        WHEN LOWER(client_broker) IN ('b','broker','agent') THEN 'Broker'
                        WHEN client_broker IS NULL OR client_broker='' THEN 'Owner'
                        WHEN LOWER(client_broker) IN ('o','owner','seller') THEN 'Owner'
                        ELSE client_broker
                    END"""
            )
        if "status" in existing:
            conn.execute(
                f"""UPDATE {table}
                    SET status=CASE
                        WHEN status IS NULL OR status='' THEN 'Available'
                        WHEN LOWER(status)='available' THEN 'Available'
                        WHEN LOWER(status)='reserved' THEN 'Reserved'
                        WHEN LOWER(status)='hold' THEN 'Reserved'
                        WHEN LOWER(status)='withdrawn' THEN 'Withdrawn'
                        WHEN LOWER(status)='inactive' THEN 'Inactive'
                        WHEN LOWER(status) IN ('sold','sale') THEN 'Sold'
                        WHEN LOWER(status) IN ('rented','rent') THEN 'Rented'
                        ELSE status
                    END"""
            )
            if table == "rent_availability":
                conn.execute(f"UPDATE {table} SET status='Available' WHERE status='Sold'")
            if table == "sale_availability":
                conn.execute(f"UPDATE {table} SET status='Available' WHERE status='Rented'")


def migrate(db_path: str, dry_run: bool = False) -> bool:
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found: {db_path}")
        return False
    with sqlite3.connect(db_path, timeout=30) as conn:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_autocheckpoint=1000")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA cache_size=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            for table in PHASE1_TABLES:
                if not columns(conn, table):
                    print(f"Skipping missing table: {table}")
                    continue
                backfill_table(conn, table)
            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
    return True


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    database_path = os.path.join(root, "real_estate_crm.db")
    dry = "--dry-run" in sys.argv
    if not dry:
        backup_path = backup_database(database_path)
        print(f"Backup created: {backup_path}")
    ok = migrate(database_path, dry_run=dry)
    print("Dry run complete." if dry else "Migration complete.")
    sys.exit(0 if ok else 1)
