# 🏗️ Architecture Documentation
## Real Estate CRM - System Architecture

---

## 📋 Overview

The Real Estate CRM is a desktop application built with PySide6 (Qt) for property management, deal tracking, and agent commission management. It follows a layered architecture with clear separation of concerns.

**Last Updated:** 2026-07-16

---

## 🏛️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  PySide6 Widgets (CRM/modules/*.py)                │    │
│  │  - DataTablePage, DealModule, FinancialModule      │    │
│  │  - UsersModule, CommissionModule, InstallmentModule │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  CRMServices (CRM/services.py)                     │    │
│  │  - Business logic, authentication, data access      │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    Data Access Layer                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Repository Pattern (crm_core/repositories.py)     │    │
│  │  - SQLiteBaseRepository, DealRepository            │    │
│  │  - ClientRepository, PropertyRepository            │    │
│  │  - UserRepository, AuditRepository                 │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    Data Layer                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  SQLite Database (real_estate_crm.db)              │    │
│  │  - 20+ tables with foreign keys and indexes        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
RealEstate_CRM/
├── CRM/                        # Desktop Application (PySide6)
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── app_window.py           # Main window (ModernCRMWindow)
│   ├── services.py             # Service layer
│   ├── models.py               # Data models (TableSpec, ColumnSpec, FieldSpec)
│   ├── constants.py            # Application constants
│   ├── database.py             # Database initialization
│   ├── protocols.py            # Protocol definitions
│   ├── modules/                # Feature modules
│   │   ├── data_table.py       # Generic data table with pagination
│   │   ├── deals.py            # Deal management
│   │   ├── financial.py        # Financial tracking
│   │   ├── employees.py        # Employee management
│   │   ├── users.py            # User management with lockout
│   │   ├── installments.py     # Installment tracking
│   │   ├── commissions.py      # Commission tracking
│   │   ├── reports.py          # Report generation
│   │   └── ...
│   ├── dialogs/                # Dialog windows
│   │   ├── login.py            # Login dialog
│   │   ├── record.py           # Record add/edit dialog
│   │   └── ...
│   ├── widgets/                # Reusable widgets
│   │   ├── table.py            # ExcelTableWidget
│   │   ├── charts.py           # Chart widgets
│   │   └── ...
│   └── utils/                  # Utility functions
│       ├── formatting.py       # Date/money formatting
│       ├── validation.py       # Input validation
│       └── parsing.py          # Data parsing
│
├── crm_core/                   # Core Business Logic
│   ├── __init__.py
│   ├── auth.py                 # Authentication (password, lockout)
│   ├── db.py                   # Database repository base
│   ├── repositories.py         # Repository implementations
│   ├── service_interfaces.py   # Service interfaces
│   ├── constants.py            # Core constants
│   ├── validators.py           # Validation logic
│   └── ...
│
├── backend/                    # REST API (FastAPI)
│   ├── main.py                 # FastAPI app
│   ├── auth.py                 # API authentication
│   ├── routers/                # API routers
│   │   ├── auth_router.py      # Authentication endpoints
│   │   ├── records_router.py   # CRUD endpoints
│   │   └── ...
│   └── ...
│
├── migrations/                 # Database migrations
│   ├── 001_consolidate_contact_fields.py
│   ├── 002_add_missing_indexes.py
│   ├── 003_add_foreign_keys.py
│   ├── 004_add_installment_and_commission_tables.py
│   └── 005_add_account_lockout_columns.py
│
├── tests/                      # Test suite
│   ├── test_auth_core.py       # 32 tests
│   ├── test_data_table_query.py # 35 tests
│   ├── test_commission_edge_cases.py # 33 tests
│   └── ...
│
├── pytest.ini                  # Pytest configuration
├── .coveragerc                 # Coverage configuration
└── requirements.txt            # Python dependencies
```

---

## 🔑 Key Design Patterns

### 1. Repository Pattern
All database access is abstracted through repositories in `crm_core/repositories.py`:

```python
# Factory pattern for repository creation
factory = RepositoryFactory(db_path)
user_repo = factory.users
deal_repo = factory.get_repository("rent_availability")

# CRUD operations
user = user_repo.get_by_username("admin")
deals = deal_repo.get_active_deals()
new_id = user_repo.create(user_data)
user_repo.update(user_id, update_data)
user_repo.soft_delete(user_id, username)
```

### 2. Service Layer
Business logic is centralized in `CRM/services.py`:

```python
services = CRMServices()

# Authentication
user = services.login(username, password)
ok, msg = services.create_user(username, password, full_name, email, role)

# Deal operations
deal = services.get_deal(table, id)
deals = services.get_active_deals(table)
new_deal = services.create_deal(table, data, username)

# Settings
value = services.settings_get("key", "default")
services.settings_set("key", "value")
```

### 3. Table Specification Pattern
UI tables are defined declaratively using `TableSpec`:

```python
spec = TableSpec(
    title="Rent Availability",
    table="rent_availability",
    columns=[
        ColumnSpec("id", "ID", width=64),
        ColumnSpec("owner_name", "Owner", width=150),
        ColumnSpec("monthly_rent", "Rent", money_formatter, 130),
    ],
    form_fields=[
        FieldSpec("Owner Name", "owner_name", required=True),
        FieldSpec("Monthly Rent", "monthly_rent", numeric=True),
    ],
    insert_columns=["owner_name", "monthly_rent", ...],
    update_columns=["owner_name", "monthly_rent", ...],
    permission="rent",
    order_by="created_at DESC",
)
```

---

## 🔐 Security Architecture

### Authentication Flow
1. User enters credentials in LoginDialog
2. `CRMServices.login()` checks account lockout via `crm_core.auth.is_account_locked()`
3. Password verified against stored hash (bcrypt or SHA-256 fallback)
4. Failed attempts recorded via `record_failed_login()`
5. Account locked after `MAX_FAILED_ATTEMPTS` (5) failed attempts
6. Lockout duration: `LOCKOUT_DURATION_MINUTES` (30 minutes)
7. Successful login resets failed attempts via `reset_failed_attempts()`

### Security Constants (`crm_core/auth.py`)
```python
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30
MIN_PASSWORD_LENGTH = 8
```

### Password Policy
- Minimum 8 characters (`MIN_PASSWORD_LENGTH`)
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character (!@#$%^&*()_+-=[]{}|;':",./<>?)

### Authorization
- Role-based access control (Super Admin, Admin, Staff, etc.)
- Permission checks via `has_permission(role, permission)`
- Phase 1 tables require approval for edits/deletes

---

## 📊 Database Schema

### Core Tables
- `users` - User accounts with lockout fields (failed_attempts, locked_until)
- `rent_availability` - Available rental properties
- `rent_requirements` - Client rental requirements
- `sale_availability` - Properties for sale
- `sale_requirements` - Buyer requirements
- `employees` - Employee records
- `income_transactions` - Income tracking
- `expense_transactions` - Expense tracking

### Workflow Tables
- `pending_approvals` - Edit/delete approval queue
- `audit_logs` - Change audit trail
- `app_settings` - Application configuration

### Financial Tables
- `installment_schedules` - Payment schedules
- `installment_payments` - Individual payments
- `commissions` - Commission records
- `commission_splits` - Agent commission splits

### Database Migrations
| Migration | Description |
|-----------|-------------|
| 001 | Consolidate contact fields |
| 002 | Add missing indexes for performance |
| 003 | Add foreign key constraints |
| 004 | Add installment and commission tables |
| 005 | Add account lockout columns (failed_attempts, locked_until) |

---

## 🔄 Data Flow

### Record Creation Flow
```
User clicks "Add" → RecordDialog opens → User fills form
→ validate_form_value() checks inputs → services.insert() executes SQL
→ after_record_saved() refreshes table → log_audit() records change
```

### Pagination Flow
```
Page loads → refresh() called → _build_query() constructs SQL
→ COUNT(*) gets total → LIMIT/OFFSET fetches page
→ _update_pagination_controls() updates UI
```

---

## 🧪 Testing Architecture

### Test Files (122 tests total)
| File | Tests | Coverage Area |
|------|-------|---------------|
| test_auth_core.py | 32 | Password hashing, strength validation, lockout |
| test_data_table_query.py | 35 | Pagination, _build_query() DRY fix |
| test_commission_edge_cases.py | 33 | Split percentages, rate validation |
| test_users_unlock.py | 15 | Admin unlock functionality |
| test_installments_commissions.py | 4 | Installment/commission tracking |
| test_migrations.py | 3 | Database migrations |
| **Total** | **122** | |

### Test Infrastructure
- pytest with pytest-cov for coverage
- Mock-based testing for Qt widgets
- SQLite in-memory databases for isolation
- `pytest.importorskip()` for optional dependencies
- pytest.ini and .coveragerc configuration

---

## 📈 Performance Considerations

### Pagination
- Default page size: 100 rows
- Configurable: 50, 100, 250, 500, 1000
- COUNT(*) query for total rows
- LIMIT/OFFSET for page fetching

### Query Optimization
- `_build_query()` centralizes filter construction
- Indexes on frequently queried columns
- Soft delete via `is_deleted` flag

---

## 🚀 Deployment

### Desktop Application
```bash
# Using virtual environment
.venv_linux/bin/python -m CRM

# Or system Python
python3 -m CRM
```

### Requirements
- Python 3.12+
- PySide6 6.x
- SQLite3 (included with Python)
- bcrypt (optional, for secure password hashing)

---

*This architecture supports the enterprise requirements of reliability, maintainability, scalability, and security.*
