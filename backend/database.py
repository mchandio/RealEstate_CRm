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
        cursor.execute("PRAGMA wal_autocheckpoint=1000")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.execute("PRAGMA cache_size=5000")
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
            _backfill_phase1_canonical_columns(conn, table, existing)
        _archive_existing_closed_availability(conn)


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


def _backfill_phase1_canonical_columns(conn, table: str, columns: set[str]) -> None:
    """Keep legacy and canonical Phase 1 aliases synchronized.

    Older deployments populated contact while newer Web/Desktop code can read
    contact_phone, owner_phone, and contact_person. We keep all aliases present
    so old screens, imports, reports, and the new UI do not lose records.
    """
    if table in {"rent_requirements", "sale_requirements"}:
        if {"client_name", "contact_person"} <= columns:
            conn.exec_driver_sql(
                f"UPDATE {table} SET contact_person=client_name "
                "WHERE (contact_person IS NULL OR contact_person='') AND client_name IS NOT NULL"
            )
        if {"contact", "contact_phone"} <= columns:
            conn.exec_driver_sql(
                f"UPDATE {table} SET contact_phone=contact "
                "WHERE (contact_phone IS NULL OR contact_phone='') AND contact IS NOT NULL AND contact<>''"
            )
            conn.exec_driver_sql(
                f"UPDATE {table} SET contact=contact_phone "
                "WHERE (contact IS NULL OR contact='') AND contact_phone IS NOT NULL AND contact_phone<>''"
            )
        if "client_status" in columns:
            conn.exec_driver_sql(
                f"""UPDATE {table}
                    SET client_status=CASE
                        WHEN LOWER(client_status) IN ('o', 'owner') THEN 'Owner'
                        WHEN LOWER(client_status) IN ('b', 'broker', 'agent') THEN 'Broker'
                        WHEN client_status IS NULL OR client_status='' THEN 'Client'
                        WHEN LOWER(client_status)='client' THEN 'Client'
                        ELSE client_status
                    END"""
            )
        if {"budget", "budget_max"} <= columns:
            conn.exec_driver_sql(
                f"UPDATE {table} SET budget=budget_max "
                "WHERE (budget IS NULL OR budget=0) AND budget_max IS NOT NULL AND budget_max<>0"
            )
        if {"budget", "budget_min"} <= columns:
            conn.exec_driver_sql(
                f"UPDATE {table} SET budget=budget_min "
                "WHERE (budget IS NULL OR budget=0) AND budget_min IS NOT NULL AND budget_min<>0"
            )
        if {"property_requires", "property_type"} <= columns:
            conn.exec_driver_sql(
                f"UPDATE {table} SET property_requires=property_type "
                "WHERE (property_requires IS NULL OR property_requires='') AND property_type IS NOT NULL AND property_type<>''"
            )
        if {"property_requires", "property_requirement"} <= columns:
            conn.exec_driver_sql(
                f"UPDATE {table} SET property_requires=property_requirement "
                "WHERE (property_requires IS NULL OR property_requires='') AND property_requirement IS NOT NULL AND property_requirement<>''"
            )

    if table in {"rent_availability", "sale_availability"}:
        if {"contact", "owner_phone"} <= columns:
            conn.exec_driver_sql(
                f"UPDATE {table} SET owner_phone=contact "
                "WHERE (owner_phone IS NULL OR owner_phone='') AND contact IS NOT NULL AND contact<>''"
            )
            conn.exec_driver_sql(
                f"UPDATE {table} SET contact=owner_phone "
                "WHERE (contact IS NULL OR contact='') AND owner_phone IS NOT NULL AND owner_phone<>''"
            )
        if {"contact_phone", "owner_phone"} <= columns:
            conn.exec_driver_sql(
                f"UPDATE {table} SET contact_phone=owner_phone "
                "WHERE (contact_phone IS NULL OR contact_phone='') AND owner_phone IS NOT NULL AND owner_phone<>''"
            )
            conn.exec_driver_sql(
                f"UPDATE {table} SET owner_phone=contact_phone "
                "WHERE (owner_phone IS NULL OR owner_phone='') AND contact_phone IS NOT NULL AND contact_phone<>''"
            )
        if "client_broker" in columns:
            conn.exec_driver_sql(
                f"""UPDATE {table}
                    SET client_broker=CASE
                        WHEN LOWER(client_broker) IN ('c', 'client') THEN 'Client'
                        WHEN LOWER(client_broker) IN ('b', 'broker', 'agent') THEN 'Broker'
                        WHEN client_broker IS NULL OR client_broker='' THEN 'Owner'
                        WHEN LOWER(client_broker) IN ('o', 'owner', 'seller') THEN 'Owner'
                        ELSE client_broker
                    END"""
            )
        if "status" in columns:
            conn.exec_driver_sql(
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
                conn.exec_driver_sql(
                    f"UPDATE {table} SET status='Available' WHERE status='Sold'"
                )
            elif table == "sale_availability":
                conn.exec_driver_sql(
                    f"UPDATE {table} SET status='Available' WHERE status='Rented'"
                )
            conn.exec_driver_sql(
                f"UPDATE {table} SET status=? WHERE status IS NULL OR status=''",
                ("Available",),
            )
        if {"property_availability", "property_type"} <= columns:
            conn.exec_driver_sql(
                f"UPDATE {table} SET property_availability=property_type "
                "WHERE (property_availability IS NULL OR property_availability='') AND property_type IS NOT NULL AND property_type<>''"
            )

    if {"size", "size_beds"} <= columns:
        conn.exec_driver_sql(
            f"UPDATE {table} SET size=size_beds "
            "WHERE (size IS NULL OR size='') AND size_beds IS NOT NULL AND size_beds<>''"
        )
    if {"measurement", "sq_ft"} <= columns:
        conn.exec_driver_sql(
            f"UPDATE {table} SET measurement=sq_ft "
            "WHERE (measurement IS NULL OR measurement='') AND sq_ft IS NOT NULL AND sq_ft<>''"
        )
    if {"measurement", "sq_ft_yards"} <= columns:
        conn.exec_driver_sql(
            f"UPDATE {table} SET measurement=sq_ft_yards "
            "WHERE (measurement IS NULL OR measurement='') AND sq_ft_yards IS NOT NULL AND sq_ft_yards<>''"
        )
    if {"measurement_unit", "sq_ft_yards"} <= columns:
        conn.exec_driver_sql(
            f"""UPDATE {table}
                SET measurement_unit=CASE
                    WHEN LOWER(sq_ft_yards) LIKE '%yard%' OR LOWER(sq_ft_yards) LIKE '%yd%' THEN 'Yards'
                    ELSE 'Sq Ft'
                END
                WHERE (measurement_unit IS NULL OR measurement_unit='')
                  AND sq_ft_yards IS NOT NULL AND sq_ft_yards<>''"""
        )
    if {"measurement_unit", "sq_ft"} <= columns:
        conn.exec_driver_sql(
            f"UPDATE {table} SET measurement_unit='Sq Ft' "
            "WHERE (measurement_unit IS NULL OR measurement_unit='') AND sq_ft IS NOT NULL AND sq_ft<>''"
            )


def _archive_existing_closed_availability(conn) -> None:
    archive_rules = {
        "rent_availability": ("Rented", "rented_properties", "rent"),
        "sale_availability": ("Sold", "sold_properties", "sale"),
    }
    copy_candidates = (
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
    for source_table, (closed_status, archive_table, deal_type) in archive_rules.items():
        source_columns = {
            row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({source_table})").fetchall()
        }
        archive_columns = {
            row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({archive_table})").fetchall()
        }
        if not source_columns or not archive_columns or "status" not in source_columns:
            continue
        conn.exec_driver_sql(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{archive_table}_source "
            f"ON {archive_table}(source_table, source_id)"
        )
        copy_columns = [
            column for column in copy_candidates
            if column in source_columns and column in archive_columns
        ]
        insert_columns = [
            "source_table", "source_id", "deal_type", "closed_status",
            "closed_at", "archived_at", "archived_by", *copy_columns,
        ]
        closed_expr = "COALESCE(CAST(closed_at AS TEXT), datetime('now'))" if "closed_at" in source_columns else "datetime('now')"
        select_values = [
            "?",
            "id",
            "?",
            "?",
            closed_expr,
            "datetime('now')",
            "'migration'",
            *[f'"{column}"' for column in copy_columns],
        ]
        conn.exec_driver_sql(
            f"""INSERT OR IGNORE INTO {archive_table}
                ({', '.join(f'"{column}"' for column in insert_columns)})
                SELECT {', '.join(select_values)}
                FROM {source_table}
                WHERE LOWER(COALESCE(status,''))=LOWER(?)
                  AND COALESCE(is_deleted,0)=0""",
            (source_table, deal_type, closed_status, closed_status),
        )
        updates = ["is_deleted=1"] if "is_deleted" in source_columns else []
        params = []
        if "deleted_by" in source_columns:
            updates.append("deleted_by=COALESCE(NULLIF(deleted_by,''), ?)")
            params.append("deal_archive")
        if "deleted_at" in source_columns:
            updates.append("deleted_at=COALESCE(deleted_at, datetime('now'))")
        if "workflow_stage" in source_columns:
            updates.append("workflow_stage='Deal Done'")
        if "deal_probability" in source_columns:
            updates.append("deal_probability=100")
        if "closed_at" in source_columns:
            updates.append("closed_at=COALESCE(closed_at, datetime('now'))")
        if not updates:
            continue
        params.append(closed_status)
        conn.exec_driver_sql(
            f"""UPDATE {source_table}
                SET {', '.join(updates)}
                WHERE LOWER(COALESCE(status,''))=LOWER(?)
                  AND COALESCE(is_deleted,0)=0""",
            tuple(params),
        )


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
