# 👨‍💻 Developer Guide
## Real Estate CRM - Development Setup & Contribution Guidelines

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup Instructions](#setup-instructions)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Running Tests](#running-tests)
6. [Code Style](#code-style)
7. [Adding New Features](#adding-new-features)
8. [Database Migrations](#database-migrations)

---

## 🔧 Prerequisites

- **Python 3.12+**
- **Git**
- **SQLite3** (included with Python)
- **Virtual environment** (recommended)

---

## 🚀 Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd RealEstate_CRM
```

### 2. Create Virtual Environment
```bash
# Linux/Mac
python3 -m venv .venv_linux
source .venv_linux/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development/testing
```

### 4. Initialize Database
```bash
python -c "from CRM.database import ensure_database; ensure_database()"
```

### 5. Run Migrations
```bash
python migrations/002_add_missing_indexes.py
python migrations/003_add_foreign_keys.py
python migrations/004_add_installment_and_commission_tables.py
python migrations/005_add_account_lockout_columns.py
```

### 6. Launch the Application
```bash
python -m CRM
```

**Default Credentials:**
- Username: `admin`
- Password: `admin`

---

## 📁 Project Structure

```
RealEstate_CRM/
├── CRM/                    # Desktop Application (PySide6)
│   ├── modules/            # Feature modules
│   ├── dialogs/            # Dialog windows
│   ├── widgets/            # Reusable widgets
│   ├── utils/              # Utility functions
│   ├── services.py         # Service layer
│   └── models.py           # Data models
│
├── crm_core/               # Core Business Logic
│   ├── auth.py             # Authentication
│   ├── repositories.py     # Repository Pattern
│   └── db.py               # Database base
│
├── backend/                # REST API (FastAPI)
│   └── routers/            # API endpoints
│
├── migrations/             # Database migrations
├── tests/                  # Test suite
└── docs/                   # Documentation
```

---

## 🔄 Development Workflow

### 1. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Follow code style guidelines (see below)
- Add tests for new functionality
- Update documentation if needed

### 3. Run Tests
```bash
pytest tests/ -v
```

### 4. Commit Changes
```bash
git add .
git commit -m "feat: add your feature description"
```

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
```

---

## 🧪 Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_auth_core.py -v
```

### Run Tests with Coverage
```bash
pytest --cov=crm_core --cov=CRM --cov-report=html
open htmlcov/index.html
```

### Run Tests by Marker
```bash
pytest -m security    # Security-related tests
pytest -m database    # Database-related tests
```

---

## 📝 Code Style

### Python Style
- **Line length:** 100 characters max
- **Quotes:** Single quotes for strings
- **Imports:** Grouped (stdlib, third-party, local)
- **Type hints:** Required for function signatures
- **Docstrings:** Required for public functions/classes

### Example
```python
"""Module docstring describing the module's purpose."""

from __future__ import annotations

import os
from typing import Any

from CRM.services import CRMServices


def example_function(param: str, optional: int = 0) -> dict[str, Any]:
    """Brief description of the function.
    
    Args:
        param: Description of param
        optional: Description of optional parameter
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param is invalid
    """
    if not param:
        raise ValueError("param cannot be empty")
    return {"result": param, "count": optional}
```

### Naming Conventions
- **Functions:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_leading_underscore`
- **Files:** `snake_case.py`

---

## ➕ Adding New Features

### 1. Create Module File
```python
# CRM/modules/your_module.py
"""Your module description."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from CRM.models import TableSpec, ColumnSpec, FieldSpec


def your_table_spec() -> TableSpec:
    """Create spec for your table."""
    return TableSpec(
        title="Your Table",
        table="your_table",
        columns=[...],
        form_fields=[...],
        insert_columns=[...],
        update_columns=[...],
        permission="your_permission",
    )
```

### 2. Register in App Window
```python
# CRM/app_window.py
from CRM.modules.your_module import YourModule

# In _build_menu():
if has_permission(self.role, "your_permission"):
    self._add_page("your_page", "Your Page", YourModule(self, self.services))
```

### 3. Add Tests
```python
# tests/test_your_module.py
"""Tests for your module."""

import pytest


class TestYourModule:
    def test_example(self):
        """Test example functionality."""
        assert True
```

### 4. Run Tests
```bash
pytest tests/test_your_module.py -v
```

---

## 🗄️ Database Migrations

### Creating a New Migration
```python
# migrations/006_your_migration.py
"""Migration 006: Description of migration."""

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


def run_migration(db_path: str | None = None) -> None:
    """Run the migration."""
    if db_path is None:
        db_path = get_db_path()
    
    print(f"Running migration 006: Description")
    print(f"Database: {db_path}")
    print("-" * 60)
    
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        
        # Add your migration logic here
        # Example: ALTER TABLE users ADD COLUMN new_field TEXT
        
        conn.commit()
        conn.close()
        
        print("Migration complete!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
```

### Running Migrations
```bash
python migrations/006_your_migration.py
```

---

## 🔐 Security Guidelines

### Password Handling
- Use `crm_core.auth.hash_password()` for hashing
- Use `crm_core.auth.verify_password()` for verification
- Never store plain-text passwords
- Enforce password strength policy

### Authentication
- Always check permissions with `has_permission()`
- Use `CRMServices.login()` for authentication
- Log all security-relevant actions

### Input Validation
- Use validators from `CRM/utils/validation.py`
- Validate all user inputs before database operations
- Sanitize strings to prevent SQL injection

---

## 📚 Useful Commands

```bash
# Run the application
python -m CRM

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest --cov=crm_core --cov=CRM

# Check code style
flake8 CRM/ crm_core/

# Format code
black CRM/ crm_core/

# Sort imports
isort CRM/ crm_core/

# Type checking
mypy CRM/ crm_core/
```

---

## 🐛 Debugging

### Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

**Issue: ModuleNotFoundError**
```bash
# Ensure virtual environment is activated
source .venv_linux/bin/activate
```

**Issue: Database locked**
```bash
# Check for other processes using the database
lsof real_estate_crm.db
```

**Issue: PySide6 display error**
```bash
# Use offscreen platform for headless
QT_QPA_PLATFORM=offscreen python -m CRM
```

---

## 📞 Getting Help

- Check existing documentation in `docs/`
- Review test files for usage examples
- Search codebase for similar implementations

---

*Last Updated: 2026-07-16*
