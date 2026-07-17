"""Migration 003: Add Foreign Key Constraints

This migration adds foreign key constraints to the RealEstate_CRM database.
SQLite doesn't support ALTER TABLE to add foreign keys, so this migration
recreates tables with the proper constraints and migrates data.

Based on backend/models.py, the following foreign key relationships are needed:
- login_logs.user_id -> users.id
- attendance.employee_id -> employees.id
- salary_payments.employee_id -> employees.id
- sf_performance_goals.employee_id -> sf_employees.id
- sf_learning.employee_id -> sf_employees.id
- sf_compensation.employee_id -> sf_employees.id
- sf_onboarding.employee_id -> sf_employees.id
- wf_workflow_steps.workflow_id -> wf_workflows.id
- wf_instances.workflow_id -> wf_workflows.id
- wf_tasks.instance_id -> wf_instances.id
- wf_approvals.task_id -> wf_tasks.id
- wf_sla_log.instance_id -> wf_instances.id
- wf_sla_log.task_id -> wf_tasks.id
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


def check_foreign_keys_enabled(conn: sqlite3.Connection) -> bool:
    """Check if foreign keys are enabled."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    return cursor.fetchone()[0] == 1


def get_existing_foreign_keys(conn: sqlite3.Connection, table: str) -> set[str]:
    """Get existing foreign key references for a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA foreign_key_list({table})")
    return {row[2] for row in cursor.fetchall()}  # Returns referenced table names


def get_table_indexes(conn: sqlite3.Connection, table_name: str) -> list[str]:
    """Get CREATE INDEX statements for a table."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",
        (table_name,)
    )
    return [row[0] for row in cursor.fetchall()]


def clean_orphaned_records(conn: sqlite3.Connection, table_name: str, foreign_keys: list[str]) -> int:
    """Clean orphaned records that would violate foreign key constraints.
    
    Returns count of records cleaned.
    """
    cursor = conn.cursor()
    total_cleaned = 0
    
    for fk in foreign_keys:
        parts = fk.split("REFERENCES")
        if len(parts) != 2:
            continue
        
        column = parts[0].strip()
        reference = parts[1].strip()
        ref_parts = reference.split("(")
        if len(ref_parts) != 2:
            continue
        
        ref_table = ref_parts[0]
        ref_column = ref_parts[1].rstrip(")")
        
        # Find orphaned records
        cursor.execute(f"""
            SELECT COUNT(*) FROM {table_name} t
            WHERE t.{column} IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM {ref_table} r WHERE r.{ref_column} = t.{column}
            )
        """)
        orphaned_count = cursor.fetchone()[0]
        
        if orphaned_count > 0:
            print(f"    Found {orphaned_count} orphaned records in {table_name}.{column}")
            # Set orphaned foreign keys to NULL
            cursor.execute(f"""
                UPDATE {table_name}
                SET {column} = NULL
                WHERE {column} IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM {ref_table} r WHERE r.{ref_column} = {table_name}.{column}
                )
            """)
            total_cleaned += orphaned_count
    
    return total_cleaned


def recreate_table_with_foreign_keys(
    conn: sqlite3.Connection,
    table_name: str,
    columns_def: str,
    foreign_keys: list[str]
) -> bool:
    """Recreate a table with foreign key constraints.
    
    Returns True if table was recreated, False if skipped.
    """
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    if not cursor.fetchone():
        print(f"  Table {table_name} does not exist, skipping")
        return False
    
    # Get existing data count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    
    # Check if foreign keys already exist
    existing_fks = get_existing_foreign_keys(conn, table_name)
    
    # Build new table definition
    fk_clauses = []
    for fk in foreign_keys:
        # Parse foreign key definition
        # Format: "column_name REFERENCES target_table(target_column)"
        parts = fk.split("REFERENCES")
        if len(parts) == 2:
            column = parts[0].strip()
            reference = parts[1].strip()
            # Check if this FK already exists
            ref_table = reference.split("(")[0]
            if ref_table not in existing_fks:
                # Add ON DELETE SET NULL for soft references
                fk_clauses.append(f"FOREIGN KEY ({column}) REFERENCES {reference} ON DELETE SET NULL")
    
    if not fk_clauses:
        print(f"  Table {table_name} already has all foreign keys, skipping")
        return False
    
    # Get existing indexes before dropping table
    existing_indexes = get_table_indexes(conn, table_name)
    
    # Clean orphaned records first
    cleaned = clean_orphaned_records(conn, table_name, foreign_keys)
    if cleaned > 0:
        print(f"    Cleaned {cleaned} orphaned records")
    
    # Create temporary table with foreign keys
    temp_table = f"{table_name}_new"
    fk_def = ", ".join(fk_clauses)
    
    create_sql = f"""
        CREATE TABLE {temp_table} (
            {columns_def},
            {fk_def}
        )
    """
    
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
        cursor.execute(create_sql)
        
        # Copy data from old table
        cursor.execute(f"INSERT INTO {temp_table} SELECT * FROM {table_name}")
        
        # Drop old table and rename new
        cursor.execute(f"DROP TABLE {table_name}")
        cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
        
        # Recreate indexes
        for index_sql in existing_indexes:
            # Replace old table name with new table name in index SQL
            new_index_sql = index_sql.replace(temp_table, table_name)
            try:
                cursor.execute(new_index_sql)
            except sqlite3.Error as e:
                print(f"    Warning: Could not recreate index: {e}")
        
        print(f"  ✓ Recreated {table_name} with foreign keys ({count} rows migrated, {len(existing_indexes)} indexes restored)")
        return True
        
    except Exception as e:
        print(f"  ✗ Error recreating {table_name}: {e}")
        # Rollback on error
        conn.rollback()
        raise


def create_backup(db_path: str) -> str:
    """Create a backup of the database before migration."""
    import shutil
    from datetime import datetime
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path


def run_migration(db_path: str | None = None) -> dict[str, int]:
    """Run the migration. Returns counts of tables modified."""
    if db_path is None:
        db_path = get_db_path()
    
    print(f"Running migration 003: Add Foreign Key Constraints")
    print(f"Database: {db_path}")
    print("-" * 60)
    
    # Create backup before destructive operation
    create_backup(db_path)
    
    counts = {
        "tables_modified": 0,
        "tables_skipped": 0,
        "tables_error": 0,
    }
    
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys=ON")
        
        if not check_foreign_keys_enabled(conn):
            print("Warning: Foreign keys could not be enabled")
        
        # Define tables that need foreign keys
        # Format: (table_name, columns_definition, foreign_keys)
        
        tables_to_update = [
            # Login Logs - FK to users
            (
                "login_logs",
                """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                login_time TEXT,
                status TEXT,
                ip_address TEXT
                """,
                ["user_id REFERENCES users(id)"]
            ),
            
            # Attendance - FK to employees
            (
                "attendance",
                """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                date TEXT,
                check_in TEXT,
                check_out TEXT,
                shift_name TEXT DEFAULT 'Office',
                scheduled_start TEXT DEFAULT '09:30',
                scheduled_end TEXT DEFAULT '18:00',
                status TEXT DEFAULT 'Present',
                leave_type TEXT,
                worked_minutes INTEGER DEFAULT 0,
                late_minutes INTEGER DEFAULT 0,
                early_leave_minutes INTEGER DEFAULT 0,
                overtime_minutes INTEGER DEFAULT 0,
                approved_by TEXT,
                last_edited_at TEXT,
                notes TEXT
                """,
                ["employee_id REFERENCES employees(id)"]
            ),
            
            # Salary Payments - FK to employees
            (
                "salary_payments",
                """
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
                """,
                ["employee_id REFERENCES employees(id)"]
            ),
            
            # SF Performance Goals - FK to sf_employees
            (
                "sf_performance_goals",
                """
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
                created_at TEXT
                """,
                ["employee_id REFERENCES sf_employees(id)"]
            ),
            
            # SF Learning - FK to sf_employees
            (
                "sf_learning",
                """
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
                """,
                ["employee_id REFERENCES sf_employees(id)"]
            ),
            
            # SF Compensation - FK to sf_employees
            (
                "sf_compensation",
                """
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
                """,
                ["employee_id REFERENCES sf_employees(id)"]
            ),
            
            # SF Onboarding - FK to sf_employees
            (
                "sf_onboarding",
                """
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
                """,
                ["employee_id REFERENCES sf_employees(id)"]
            ),
            
            # WF Workflow Steps - FK to wf_workflows
            (
                "wf_workflow_steps",
                """
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
                created_at TEXT
                """,
                ["workflow_id REFERENCES wf_workflows(id)"]
            ),
            
            # WF Instances - FK to wf_workflows
            (
                "wf_instances",
                """
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
                notes TEXT
                """,
                ["workflow_id REFERENCES wf_workflows(id)"]
            ),
            
            # WF Tasks - FK to wf_instances
            (
                "wf_tasks",
                """
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
                reference_id INTEGER
                """,
                ["instance_id REFERENCES wf_instances(id)"]
            ),
            
            # WF Approvals - FK to wf_tasks
            (
                "wf_approvals",
                """
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
                """,
                ["task_id REFERENCES wf_tasks(id)"]
            ),
            
            # WF SLA Log - FK to wf_instances and wf_tasks
            (
                "wf_sla_log",
                """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_id INTEGER,
                task_id INTEGER,
                sla_target_hours INTEGER,
                actual_hours REAL,
                breached INTEGER DEFAULT 0,
                logged_at TEXT
                """,
                [
                    "instance_id REFERENCES wf_instances(id)",
                    "task_id REFERENCES wf_tasks(id)"
                ]
            ),
        ]
        
        print("\nAdding foreign key constraints...")
        print("(SQLite requires table recreation to add foreign keys)\n")
        
        for table_name, columns_def, foreign_keys in tables_to_update:
            try:
                result = recreate_table_with_foreign_keys(
                    conn, table_name, columns_def, foreign_keys
                )
                if result:
                    counts["tables_modified"] += 1
                else:
                    counts["tables_skipped"] += 1
            except Exception as e:
                print(f"  ✗ Failed to process {table_name}: {e}")
                counts["tables_error"] += 1
        
        conn.commit()
        conn.close()
        
        print("-" * 60)
        print(f"Migration complete!")
        print(f"  - Tables modified: {counts['tables_modified']}")
        print(f"  - Tables skipped: {counts['tables_skipped']}")
        print(f"  - Tables with errors: {counts['tables_error']}")
        
        if counts['tables_error'] > 0:
            print("\nWarning: Some tables had errors. Check the output above.")
        
        return counts
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
