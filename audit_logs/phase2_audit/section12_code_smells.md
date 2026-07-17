# SECTION 12: CODE SMELLS
## Engineering Audit - Real Estate CRM System

**Date:** 2026-07-15  
**Evidence source:** `CRM/app_window.py`, `CRM/services.py`, `backend/auth.py`, `crm_core/reports.py`, code searches

---

## 12.1 Analysis

### Code Smell Categories Identified

| Category | Count | Severity | Location |
|----------|-------|----------|----------|
| God Class | 1 | Critical | `CRM/app_window.py` - `ModernCRMWindow` |
| Duplicate Logic | 12+ | High | `crm_core/reports.py`, `CRM/app_window.py` |
| Dead Code | 5+ | Medium | Legacy files, unused imports |
| Tight Coupling | 8+ | High | `CRM/app_window.py` ↔ modules |
| Long Methods | 6+ | High | `CRM/app_window.py`, `crm_core/reports.py` |
| Magic Numbers/Strings | 15+ | Medium | Throughout codebase |
| TODO/FIXME/HACK | 20+ | Low-Medium | Scattered across files |

---

## 12.2 Findings (ranked)

### Critical

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| S-C1 | **God Class: `ModernCRMWindow`** - 2000+ lines handling UI, business logic, API, dashboard, navigation, menus, and status bar | Impossible to test, maintain, or extend | High coupling, fragile changes | Extract into focused classes: `NavigationManager`, `MenuBuilder`, `DashboardController`, `APIManager` | High | Medium |
| S-C2 | **`_build_specs()` method** - 150+ lines of repetitive TableSpec creation for rent/sale requirements/availability | DRY violation, error-prone updates | Wrong specs if one table changed but not others | Create factory methods: `deal_requirement_spec()`, `deal_availability_spec()` with table-specific params | Medium | Low |

### High

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| S-H1 | **Duplicate `_normalize_location()` logic** - exists in both `crm_core/reports.py` and `CRM/app_window.py` | Inconsistent location normalization | Different results in reports vs dashboard | Extract to `crm_core/utils.py` as shared utility | Low | Low |
| S-H2 | **Duplicate dashboard calculation methods** - `_dashboard_count()`, `_dashboard_active_where()`, `_dashboard_location_buckets()` in `app_window.py` duplicate `ReportService` logic | Double maintenance, potential divergence | Reports and dashboard show different numbers | Delegate to `ReportService` or create shared `DashboardService` | Medium | Medium |
| S-H3 | **`_property_match()` method** - 80+ lines of nested if-else with repeated query patterns | Hard to understand, test, and extend | Wrong property matching | Refactor into strategy pattern or chain of responsibility | Medium | Medium |
| S-H4 | **Wildcard imports** - `from module import *` found in several files | Namespace pollution, unclear dependencies | Name collisions, hard to trace origins | Replace with explicit imports | Low | Low |
| S-H5 | **Unused imports in `app_window.py`** - many PySide6 widgets imported but not used in visible code | Cluttered imports, unclear dependencies | Confusion about actual usage | Remove unused imports, use IDE analysis | Low | None |

### Medium

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| S-M1 | **Magic strings for workflow stages** - `"Lead"`, `"Contacted"`, `"Pending"`, `"Deal Done"` scattered throughout | Typos cause silent failures | Inconsistent state transitions | Create `WorkflowStage` enum or constants module | Low | Low |
| S-M2 | **Hardcoded UI constants** - colors, sizes, margins in `app_window.py` | Inconsistent styling, hard to theme | UI changes require code changes | Move to CSS/stylesheet constants or theme system | Low | Low |
| S-M3 | **Repetitive permission checks** - `has_permission(self.role, "rent")` pattern repeated 20+ times | DRY violation | Missed permission check | Create `@requires_permission` decorator or permission helper | Low | Low |
| S-M4 | **Legacy backup files** - `qt_crm_premium_style.py`, `pyinstaller_qt_runtime_hook.py`, `professional_crm_old.py` | Confusion about which files are active | Editing wrong file | Delete or move to `archive/` directory | Low | None |
| S-M5 | **TODO/FIXME/HACK comments** - 20+ items indicating known technical debt | Incomplete implementations | Features may not work as expected | Create tracking issues, address in Phase 3-10 | Low | None |

### Low

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| S-L1 | **Inconsistent naming** - `camelCase` vs `snake_case` in some utility functions | Python convention violation | Reduced readability | Standardize to `snake_case` per PEP 8 | Low | Low |
| S-L2 | **Missing type hints** in some older functions | Reduced IDE support, unclear contracts | Runtime type errors | Add type hints gradually | Low | None |
| S-L3 | **No docstrings** on some private methods | Reduced maintainability | Hard to understand purpose | Add docstrings to public and complex private methods | Low | None |

---

## 12.3 Recommendations

### Immediate (Phase 3 - Architecture)

1. **Extract God Class Responsibilities:**
   ```python
   # Create focused managers
   class NavigationManager:
       """Handles sidebar navigation and page switching."""
       
   class MenuBuilder:
       """Constructs application menus based on permissions."""
       
   class DashboardController:
       """Manages dashboard data and refresh logic."""
       
   class APIManager:
       """Handles desktop and LAN server lifecycle."""
   ```

2. **Create Table Spec Factories:**
   ```python
   def create_deal_requirement_spec(
       title: str, table: str, permission: str, option_sets: dict
   ) -> TableSpec:
       """Factory for rent/sale requirement table specs."""
       return TableSpec(
           title, table,
           [
               ColumnSpec("id", "Sr No.", width=70),
               ColumnSpec("date", "Date", format_date_display, 96),
               ColumnSpec("client_name", "Name", width=150),
               # ... common columns
           ],
           deal_fields("client_name", "property_requires", "budget", option_sets),
           deal_insert_columns("client_name", "property_requires", "budget"),
           deal_update_columns("client_name", "property_requires", "budget"),
           permission=permission,
           deal_table=True,
       )
   ```

3. **Extract Shared Utilities:**
   ```python
   # crm_core/utils.py
   def normalize_location(value: Any) -> str:
       """Normalize location string to canonical form."""
       # Single implementation used by reports and dashboard
       
   def build_active_where_clause(table: str, columns: set[str]) -> str:
       """Build WHERE clause for active (non-deleted) records."""
       # Shared between dashboard and reports
   ```

### Medium-term

4. **Create Workflow Stage Constants:**
   ```python
   # crm_core/constants.py
   class WorkflowStage:
       LEAD = "Lead"
       CONTACTED = "Contacted"
       PENDING = "Pending"
       DEAL_DONE = "Deal Done"
       CLOSED = "Closed"
   ```

5. **Implement Permission Decorator:**
   ```python
   def requires_permission(permission: str):
       """Decorator to check user permission before method execution."""
       def decorator(method):
           @functools.wraps(method)
           def wrapper(self, *args, **kwargs):
               if not has_permission(self.role, permission):
                   raise PermissionError(f"Permission '{permission}' required")
               return method(self, *args, **kwargs)
           return wrapper
       return decorator
   ```

6. **Clean Up Legacy Files:**
   ```bash
   # Move to archive directory
   mkdir -p RealEstate_CRM/archive/legacy
   mv RealEstate_CRM/qt_crm_premium_style.py RealEstate_CRM/archive/legacy/
   mv RealEstate_CRM/professional_crm_old.py RealEstate_CRM/archive/legacy/
   mv RealEstate_CRM/pyinstaller_qt_runtime_hook.py RealEstate_CRM/archive/legacy/
   ```

---

## 12.4 Code Smells Summary

| Smell Type | Location | Severity | Fix Effort |
|------------|----------|----------|------------|
| God Class | `ModernCRMWindow` | Critical | High (Phase 3) |
| Duplicate Logic | reports.py, app_window.py | High | Medium (Phase 3) |
| Dead Code | Legacy files | Medium | Low (immediate) |
| Tight Coupling | app_window.py ↔ modules | High | High (Phase 3) |
| Long Methods | _build_specs(), _property_match() | High | Medium (Phase 3) |
| Magic Strings | Workflow stages, permissions | Medium | Low (Phase 3) |
| TODO/FIXME | Throughout codebase | Low-Medium | Incremental |

---

## 12.5 Validation Results

| Check | Result |
|-------|--------|
| God Class identified | `ModernCRMWindow` (2000+ lines) |
| Duplicate logic locations | 12+ instances found |
| Dead/legacy files | 5+ files identified |
| TODO/FIXME comments | 20+ items |
| Unused imports | Multiple in app_window.py |
| Wildcard imports | Found in several files |

---

## 12.6 Code Changes

**None.** Prompt Phase 2 is audit-only for this section.

---

## 12.7 Next Proposed Phase Step

**Section 13: Duplicate Logic** (depends on this section) — detailed analysis of code duplication patterns and refactoring opportunities.
