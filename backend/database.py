from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, TIMESTAMP, create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    # FastAPI serves several LAN users on worker threads. SQLite is fine for this
    # office-size workload as long as each connection may be used outside the
    # thread that created it.
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
else:
    engine_kwargs.update({"pool_size": 10, "max_overflow": 20})

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Enable WAL mode for SQLite (better concurrency)
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    import backend.models  # noqa: F401 - ensures every model is loaded
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def _ensure_sqlite_columns():
    """Apply lightweight SQLite migrations for columns added after create_all."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    workflow_columns = {
        "workflow_stage": "TEXT DEFAULT 'Lead'",
        "priority": "TEXT DEFAULT 'Medium'",
        "next_follow_up": "TEXT",
        "assigned_to": "TEXT",
        "last_contacted": "TEXT",
        "deal_probability": "REAL DEFAULT 10.0",
        "expected_close_value": "REAL DEFAULT 0",
        "closed_at": "TIMESTAMP",
        "lost_reason": "TEXT",
    }
    requirement_columns = {
        "client_status": "TEXT DEFAULT 'Client'",
        "broker": "TEXT",
    }
    deal_tables = (
        "rent_requirements",
        "rent_availability",
        "sale_requirements",
        "sale_availability",
    )
    availability_status_columns = {
        "rent_availability": "TEXT DEFAULT 'Available'",
        "sale_availability": "TEXT DEFAULT 'Available'",
    }
    with engine.begin() as conn:
        _ensure_model_columns(conn)

        login_log_columns = {
            row[1] for row in conn.exec_driver_sql("PRAGMA table_info(login_logs)").fetchall()
        }
        if login_log_columns and "ip_address" not in login_log_columns:
            conn.exec_driver_sql("ALTER TABLE login_logs ADD COLUMN ip_address TEXT")

        for table in deal_tables:
            existing = {
                row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            }
            for column, ddl in workflow_columns.items():
                if column not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                    existing.add(column)
            if table in availability_status_columns and "status" not in existing:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN status {availability_status_columns[table]}")
                existing.add("status")
            if table in {"rent_requirements", "sale_requirements"}:
                for column, ddl in requirement_columns.items():
                    if column not in existing:
                        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                        existing.add(column)
                conn.exec_driver_sql(
                    f"UPDATE {table} SET client_status='Client' WHERE client_status IS NULL OR client_status=''"
                )
                if "client_broker" in existing:
                    conn.exec_driver_sql(
                        f"UPDATE {table} SET broker=NULLIF(client_broker, '') "
                        "WHERE broker IS NULL OR broker=''"
                    )
            conn.exec_driver_sql(
                f"UPDATE {table} SET workflow_stage='Lead' WHERE workflow_stage IS NULL OR workflow_stage=''"
            )
            conn.exec_driver_sql(
                f"UPDATE {table} SET priority='Medium' WHERE priority IS NULL OR priority=''"
            )


def _ensure_model_columns(conn) -> None:
    """Add missing SQLite columns declared by SQLAlchemy models.

    The desktop app has carried older SQLite schemas forward for years. The
    browser API queries ORM models, so every model column must exist even when
    the legacy desktop UI uses an alias such as sq_ft_yards instead.
    """
    for table in Base.metadata.sorted_tables:
        existing = {
            row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table.name})").fetchall()
        }
        if not existing:
            continue
        for column in table.columns:
            if column.name in existing or column.primary_key:
                continue
            conn.exec_driver_sql(
                f"ALTER TABLE {table.name} ADD COLUMN {column.name} {_sqlite_column_type(column.type)}"
            )
            existing.add(column.name)


def _sqlite_column_type(column_type) -> str:
    if isinstance(column_type, Integer):
        return "INTEGER"
    if isinstance(column_type, Float):
        return "REAL"
    if isinstance(column_type, Boolean):
        return "INTEGER"
    if isinstance(column_type, (DateTime, TIMESTAMP)):
        return "TIMESTAMP"
    if isinstance(column_type, (String, Text)):
        return "TEXT"
    return "TEXT"
