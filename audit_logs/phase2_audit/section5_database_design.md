# SECTION 5: DATABASE DESIGN
## Engineering Audit - Real Estate CRM System

**Date:** 2026-07-15  
**Evidence source:** Live DB `real_estate_crm.db` (47 tables, ~1.8 MB), `professional_crm.py`, `CRM/database.py`, `backend/models.py`, `backend/database.py`, `crm_core/db.py`, `libreoffice_base_export/schema_complete.sql`

---

## 5.1 Analysis

### Access layers (single physical SQLite file)

| Layer | Mechanism | Schema authority |
|-------|-----------|------------------|
| Desktop / Qt | Raw `sqlite3` via `crm_core.db.SQLiteRepository` + `CRMServices` | `professional_crm.Database.init_all()` then `CRM.database.ensure_qt_schema()` |
| FastAPI backend | SQLAlchemy ORM (`backend/models.py`) | `Base.metadata.create_all` + `_ensure_sqlite_columns()` / `_ensure_model_columns()` |
| Exports / LibreOffice | Static SQL scripts | Partial / older subset of tables |

Production path: `crm_core.DB_PATH` → `real_estate_crm.db`. WAL is enabled on connections that set pragmas; bare `sqlite3.connect` without the repository helper may leave `foreign_keys` off (observed `PRAGMA foreign_keys=0` on an unadorned connect).

### Live inventory (47 user tables)

**Core CRM:** `users`, `login_logs`, `app_settings`, `clients`, `properties`, `broker_contacts`, `rent_requirements`, `rent_availability`, `sale_requirements`, `sale_availability`, `rented_properties`, `sold_properties`, `pending_approvals`

**Financial / HR:** `income_transactions`, `expense_transactions`, `employees`, `attendance`, `salary_payments`, `employee_attendance`, `employee_commissions`, `employee_payroll`, `employee_performance`, `financial_summary`

**Matching / import:** `rent_matches`, `data_imports`, `property_verification`

**Audit (triplicate):** `audit_logs`, `audit_log`, `AuditLog`

**SuccessFactors:** `sf_employees`, `sf_positions`, `sf_performance_goals`, `sf_must_win_battles`, `sf_kpis`, `sf_learning`, `sf_recruiting`, `sf_compensation`, `sf_onboarding`

**Workflow engine:** `wf_workflows`, `wf_workflow_steps`, `wf_instances`, `wf_tasks`, `wf_approvals`, `wf_notifications`, `wf_sla_log`, `wf_audit_log`

### Notable row volumes (live)

| Table | Rows | Implication |
|-------|------|-------------|
| `wf_audit_log` | 1228 | Hot write path |
| `login_logs` | 633 | Unindexed growth |
| `audit_logs` | 607 | Indexed (ORM) |
| `rent_requirements` | 541 | Primary deal search surface |
| `clients` | 518 | Directory / search |
| `expense_transactions` | 175 | Reporting |

### Indexes that actually exist (15 non-auto)

- `audit_logs`: action, created_at, id, record_id, table_name, username  
- `broker_contacts`: area, office_address, home_address  
- `rented_properties` / `sold_properties`: closed_at, location, unique `(source_table, source_id)`

**Missing from live DB despite SQL export scripts claiming them:** location/status/`is_deleted` indexes on deal tables; `attendance(employee_id, date)` composite.

### Soft delete

Present on Phase-1 deal tables (`is_deleted`, `deleted_by`, `deleted_at`). Close-to-archive soft-deletes availability rows and copies into `rented_properties` / `sold_properties`. Soft delete is **not** uniform on `clients`, `properties`, `employees`, financial tables.

### Migration strategy

Additive only: `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ... ADD COLUMN` + backfill UPDATEs that sync legacy aliases (`contact` ↔ `contact_phone` ↔ `owner_phone`, `budget` ↔ `budget_min`/`budget_max`, `measurement` ↔ `sq_ft`/`sq_ft_yards`). No versioned migration table, no down migrations, no Alembic.

### Normalization snapshot

- Deal rows store people as free text (`client_name`, `owner_name`, phones) rather than FKs to `clients` / `broker_contacts` → **denormalized operational model** (fast data entry, weak integrity).
- `properties` inventory is largely **disconnected** from rent/sale availability rows (parallel models).
- Archive tables **copy** many source columns (`UNIQUE(source_table, source_id)` prevents dup archives) → intentional snapshot denormalization for closed deals.
- `employee_name` duplicated beside optional `employee_id` on several SF tables.

---

## 5.2 Findings (ranked)

### Critical

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| D-C1 | **Column alias proliferation** on deal tables (e.g. `rent_requirements` has 59 columns: `contact`/`contact_phone`, `budget`/`budget_min`/`budget_max`, `size`/`size_beds`, `measurement`/`sq_ft`/`sq_ft_yards`) | Conflicting reads/writes across desktop, API, exports | Data loss / wrong search results | Freeze a **canonical column map**; write-through helpers only; stop teaching new aliases; Phase 4 cleanup after app adapters | High | High |
| D-C2 | **Deal-table indexes almost absent** in live DB (541 rent requirements, no location / workflow / `is_deleted` indexes) | Full table scans on list/filter/match | Latency under multi-user LAN | Add indexes in Phase 4: `(is_deleted, location)`, `(is_deleted, workflow_stage)`, `(is_deleted, status)`, `(assigned_to)`, follow-up date | Low–Med | Low |
| D-C3 | **Financial model is cash-book lite**, not ledger: only `income_transactions` / `expense_transactions`; no installments, journal, AR/AP, bank book, or transfer/registry tables | Cannot support agency closing / commission / receipt workflows | Wrong P&L / unreconcilable money | Domain tables in Phase 5 (installments, commissions, receipts) without ripping existing tables | High | Med |
| D-C4 | **Triplicate audit stores** (`audit_logs`, `audit_log`, `AuditLog`) with different shapes | Incomplete / inconsistent compliance trail | Audit gaps under investigation | Designate `audit_logs` as canonical; deprecate others; dual-write then migrate | Med | Med |

### High

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| D-H1 | **Sparse FK enforcement**: only a few tables have FKs; `attendance` and `salary_payments` lack FK on live DB despite ORM `ForeignKey`; ad-hoc connect has `foreign_keys=0` | Orphan attendance/pay rows | Integrity | Always open via repository (already sets `foreign_keys=ON`); add FK DDL after orphan cleanup; CASCADE/RESTRICT policy documented | Med | Med |
| D-H2 | **No FK from deals → clients/properties/users** | Same person duplicated inconsistently across 500+ requirement rows | Matching / reporting errors | Optional FK columns + gradual linkage (null-allowed), not big-bang rewrite | High | High |
| D-H3 | **Dual schema authors** (`professional_crm` + Qt ensure + SQLAlchemy ensure) can diverge | Browser API vs desktop field mismatch | Subtle bugs | Single schema module / one init entrypoint calling shared ensure list | Med | Med |
| D-H4 | **Archive migration UPDATE/INSERT** in `ensure_qt_schema` / `_archive_existing_closed_availability` spans many statements without an app-level savepoint API on all paths | Partial archive on crash mid-migrate | Closed deals half-soft-deleted | Wrap close+archive in one SQLAlchemy session / one sqlite transaction (backend already sessions; desktop archive paths must match) | Med | Med |
| D-H5 | **Legacy employee_* tables** coexist with `attendance` / `salary_payments` | Confusion which is source of truth | Double payroll logic | Inventory usage; mark dead tables; document active path | Low | Low |

### Medium

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| D-M1 | Dates as `TEXT` inconsistently (`date`, `created_at` TEXT vs TIMESTAMP) | Sort/filter bugs | Wrong period reports | ISO-8601 write convention + helpers; long-term typed columns | Med | Med |
| D-M2 | Soft delete not applied to `clients` / `properties` / money tables | Accidental hard deletes or permanent clutter | Data loss | Soft-delete policy per entity type | Med | Med |
| D-M3 | `income`/`expense` have `property_id` without FK to `properties` | Orphans; weak financial→asset link | Bad property P&L | Add FK after cleanup | Low | Low |
| D-M4 | Migration is **imperative backfill on every startup** | Longer boot; repeated UPDATEs | Lock contention on LAN | Migration version table; run once per version | Med | Low |
| D-M5 | Export schemas (`schema_complete.sql`) lag production (missing SF/WF/archive source columns) | Wrong docs / bad restores | Ops mistakes | Generate schema dump from live DB as source of truth | Low | Low |

### Low

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| D-L1 | Table name `AuditLog` (PascalCase) vs snake_case convention | Confusing tooling | Mistaken queries | Rename after dual-write deprecation | Low | Low |
| D-L2 | Multiple leftover `.db` copies under `dist/`, `installer_test/`, `outputs/backups/` | Ops ambiguity | Wrong DB edited | Document which file is production; keep backups read-only | Low | None |

---

## 5.3 Recommendations

1. **Phase 4 first wave (safe):** indexes on deal + finance filter columns; composite attendance index; ensure all writers use `foreign_keys=ON`.
2. **Phase 4 second wave:** single schema ensure module; migration version table; deprecate duplicate audit tables.
3. **Do not** normalize people/properties into FKs until Phase 5 workflows define how dealers enter data (preserve business value).
4. **Do not** collapse rent/sale requirement and availability tables — they mirror agency practice (demand vs supply boards).
5. Treat `rented_properties` / `sold_properties` as **immutable closed snapshots**; keep UNIQUE on source.

---

## 5.4 Engineering rationale

- Incremental, additive schema changes match “never destroy user data” and months of alias evolution.
- Missing indexes are higher ROI than rewriting table shapes (measurable filter performance).
- Domain gaps (installments, ledger) are **feature** gaps with schema implications — schedule Phase 5, not a greenfield schema rewrite.
- Dual desktop/API schema ensure is technical debt with proven adaptive backfills; consolidate carefully.

---

## 5.5 Implementation plan (for Phase 4 — not executed in this iteration)

1. Script: `CREATE INDEX IF NOT EXISTS` for critical filters; verify with `EXPLAIN QUERY PLAN`.
2. Orphan report for `attendance.employee_id`, `salary_payments.employee_id`, `income_transactions.property_id`.
3. Introduce `schema_migrations(version, applied_at)` and gate backfills.
4. Document canonical column map in `audit_logs/phase2_audit/` companion note.
5. No destructive DROP until Phase 9 test coverage exists for deals/finance/archive.

---

## 5.6 Code changes

**None.** Prompt Phase 2 is audit-only for this section.

---

## 5.7 Validation results

| Check | Result |
|-------|--------|
| Live table count | 47 user tables |
| Live index count (named) | 15 |
| FK count (PRAGMA) | Present on SF/WF/employee_* / rent_matches; absent on attendance/salary_payments/login_logs |
| Soft delete on deals | Confirmed columns + filter usage in `crm_core/reports.py` |
| Dual init paths | Confirmed `ensure_database()` → `professional_crm` + `ensure_qt_schema()`; backend `init_db()` |

---

## 5.8 Next proposed phase step

**Section 6: Entity Relationships** (depends on this section) — ER map, cardinality, cascade/orphan risks, missing domain entities.
