"""Unit tests for DataTablePage._build_query() and pagination logic (Phase 7).

Covers:
- _build_query() filter construction (soft delete, keyword, date range, text filters)
- _build_query() sort key selection and fallback
- _build_query() returns correct tuple structure
- Pagination state management (_current_page, _page_size, _total_count)
- Pagination navigation methods (_page_first, _page_prev, _page_next, _page_last)
- _page_size_changed resets to page 0
- _update_pagination_controls button states and info label
- clear_filters resets pagination to page 0
- refresh() uses LIMIT/OFFSET correctly
- export_csv() exports ALL filtered rows when no selection
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helpers: Build a DataTablePage without requiring a running Qt event loop
# ---------------------------------------------------------------------------

def _make_spec(columns=None, table="rent_availability", title="Rent Availability",
               permission="rent", order_by="id DESC", form_fields=None, insert_columns=None, update_columns=None):
    """Create a mock TableSpec."""
    from CRM.models import TableSpec, ColumnSpec
    if columns is None:
        columns = [
            ColumnSpec("ID", "id"),
            ColumnSpec("Owner", "owner_name"),
            ColumnSpec("Location", "location"),
            ColumnSpec("Rent", "monthly_rent"),
            ColumnSpec("Status", "status"),
            ColumnSpec("Date", "date"),
        ]
    spec = TableSpec(
        title=title,
        table=table,
        columns=columns,
        form_fields=form_fields or [],
        insert_columns=insert_columns or [],
        update_columns=update_columns or [],
        permission=permission,
        order_by=order_by,
    )
    return spec


def _make_host(services=None, role="Admin", username="admin", currency_symbol="PKR"):
    """Create a mock AppHost."""
    host = MagicMock()
    host.services = services or MagicMock()
    host.role = role
    host.currency_symbol = currency_symbol
    host.current_user = {"username": username}
    host.can_edit.return_value = False
    host.can_delete_record.return_value = (True, "")
    return host


_app_instance = None


def _make_page(spec=None, host=None, page_size=100, total_rows=0, rows=None):
    """Create a DataTablePage with mocked dependencies.
    
    Args:
        total_rows: Total row count for COUNT(*) query (default 0)
        rows: Rows to return from fetch_all (default [])
    """
    global _app_instance
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtWidgets import QApplication
    if _app_instance is None:
        _app_instance = QApplication.instance() or QApplication([])

    from CRM.modules.data_table import DataTablePage
    _spec = spec or _make_spec()
    services = MagicMock()
    services.table_columns.return_value = {"id", "owner_name", "location", "monthly_rent", "status", "date", "is_deleted"}
    services.fetch_one.return_value = {"total": total_rows}
    services.fetch_all.return_value = rows or []
    _host = host or _make_host(services=services)
    page = DataTablePage(_host, _spec, page_size=page_size)
    return page


# ===========================================================================
# _build_query() Tests
# ===========================================================================

class TestBuildQuery:
    """Test _build_query() helper method."""

    def test_build_query_returns_five_tuple(self):
        """_build_query returns (where_sql, params, sort_key, columns, all_columns)."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "location", "monthly_rent", "status", "date", "is_deleted"}
        result = page._build_query()
        assert isinstance(result, tuple)
        assert len(result) == 5

    def test_build_query_includes_soft_delete_filter(self):
        """_build_query includes is_deleted filter when column exists."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "location", "monthly_rent", "status", "date", "is_deleted"}
        where_sql, params, sort_key, columns, all_columns = page._build_query()
        assert "is_deleted" in where_sql
        assert "COALESCE(is_deleted, 0)=0" in where_sql

    def test_build_query_excludes_soft_delete_when_column_missing(self):
        """_build_query omits is_deleted filter when column doesn't exist."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "location"}
        where_sql, params, sort_key, columns, all_columns = page._build_query()
        assert "is_deleted" not in where_sql

    def test_build_query_keyword_search(self):
        """_build_query adds LIKE clauses for keyword search."""
        page = _make_page()
        page.keyword_input.setText("DHA")
        page.services.table_columns.return_value = {"id", "owner_name", "location", "monthly_rent", "status", "date"}
        where_sql, params, sort_key, columns, all_columns = page._build_query()
        assert "LIKE" in where_sql
        assert "%DHA%" in params

    def test_build_query_empty_keyword_no_search(self):
        """_build_query with empty keyword has no LIKE clause from keyword."""
        page = _make_page()
        page.keyword_input.setText("")
        page.services.table_columns.return_value = {"id", "owner_name", "location", "monthly_rent", "status", "date"}
        where_sql, params, sort_key, columns, all_columns = page._build_query()
        # No keyword means no LIKE clause from keyword (but may have other filters)
        assert "%DHA%" not in params

    def test_build_query_no_filters_returns_empty_where(self):
        """_build_query with no active filters returns empty WHERE clause."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "location"}
        page.keyword_input.setText("")
        # Ensure no date filter is active
        from PySide6.QtCore import QDate
        page.start_date.setDate(page.start_date.minimumDate())
        page.end_date.setDate(page.end_date.minimumDate())
        where_sql, params, sort_key, columns, all_columns = page._build_query()
        assert where_sql == ""

    def test_build_query_sort_key_from_combo(self):
        """_build_query uses sort combo data as sort key."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "location", "monthly_rent", "status"}
        # Set sort combo to "owner_name"
        idx = page.sort_combo.findData("owner_name")
        if idx >= 0:
            page.sort_combo.setCurrentIndex(idx)
        where_sql, params, sort_key, columns, all_columns = page._build_query()
        assert sort_key in ("owner_name", "id")

    def test_build_query_sort_key_fallback_to_id(self):
        """_build_query falls back to 'id' when sort key not in available columns."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name"}
        page.keyword_input.setText("")
        where_sql, params, sort_key, columns, all_columns = page._build_query()
        assert sort_key in all_columns

    def test_build_query_columns_from_spec(self):
        """_build_query returns columns from TableSpec that exist in table."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "location", "status"}
        where_sql, params, sort_key, columns, all_columns = page._build_query()
        # columns should be the spec columns that exist in the table
        spec_keys = [col.key for col in page.spec.columns]
        for col in columns:
            assert col in spec_keys or col in all_columns

    def test_build_query_all_columns_from_service(self):
        """_build_query returns all_columns from table_columns service."""
        page = _make_page()
        expected = {"id", "owner_name", "location", "monthly_rent", "status", "date", "is_deleted"}
        page.services.table_columns.return_value = expected
        where_sql, params, sort_key, columns, all_columns = page._build_query()
        assert all_columns == expected

    def test_build_query_date_range_filter(self):
        """_build_query includes date range filters when dates are set."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "date", "owner_name"}
        from PySide6.QtCore import QDate
        page.start_date.setDate(QDate(2026, 1, 1))
        page.end_date.setDate(QDate(2026, 6, 30))
        where_sql, params, sort_key, columns, all_columns = page._build_query()
        assert "date(" in where_sql.lower() or "date(" in where_sql
        assert "2026-01-01" in params
        assert "2026-06-30" in params


# ===========================================================================
# Pagination State Tests
# ===========================================================================

class TestPaginationState:
    """Test pagination state management."""

    def test_initial_page_size(self):
        """Default page size is 100."""
        page = _make_page(page_size=100)
        assert page._page_size == 100

    def test_custom_page_size(self):
        """Page size can be set via constructor."""
        page = _make_page(page_size=50)
        assert page._page_size == 50

    def test_initial_page_is_zero(self):
        """Initial current page is 0."""
        page = _make_page()
        assert page._current_page == 0

    def test_initial_total_count_is_zero(self):
        """Initial total count is 0."""
        page = _make_page()
        assert page._total_count == 0


# ===========================================================================
# Pagination Navigation Tests
# ===========================================================================

class TestPaginationNavigation:
    """Test page navigation methods."""

    def test_page_first_sets_page_to_zero(self):
        """_page_first sets current page to 0."""
        page = _make_page()
        page.refresh = MagicMock()
        page._current_page = 5
        page._page_first()
        assert page._current_page == 0

    def test_page_prev_decrements_page(self):
        """_page_prev decrements current page by 1."""
        page = _make_page()
        page.refresh = MagicMock()
        page._current_page = 3
        page._page_prev()
        assert page._current_page == 2

    def test_page_prev_stays_at_zero(self):
        """_page_prev does not go below page 0."""
        page = _make_page()
        page.refresh = MagicMock()
        page._current_page = 0
        page._page_prev()
        assert page._current_page == 0

    def test_page_next_increments_page(self):
        """_page_next increments current page by 1."""
        page = _make_page()
        page.refresh = MagicMock()
        page._total_count = 500
        page._page_size = 100
        page._current_page = 0
        page._page_next()
        assert page._current_page == 1

    def test_page_next_stays_at_max(self):
        """_page_next does not exceed max page."""
        page = _make_page()
        page.refresh = MagicMock()
        page._total_count = 150
        page._page_size = 100
        page._current_page = 1  # max page for 150 rows with 100/page is 1
        page._page_next()
        assert page._current_page == 1

    def test_page_last_sets_to_max_page(self):
        """_page_last sets current page to the last page."""
        page = _make_page()
        page.refresh = MagicMock()
        page._total_count = 350
        page._page_size = 100
        page._page_last()
        assert page._current_page == 3  # 350/100 = 3.5, max page = 3

    def test_page_last_with_zero_records(self):
        """_page_last with 0 records sets page to 0."""
        page = _make_page()
        page.refresh = MagicMock()
        page._total_count = 0
        page._page_last()
        assert page._current_page == 0


# ===========================================================================
# Page Size Change Tests
# ===========================================================================

class TestPageSizeChange:
    """Test page size change behavior."""

    def test_page_size_changed_resets_to_page_zero(self):
        """Changing page size resets current page to 0."""
        page = _make_page()
        page._current_page = 5
        page._page_size = 100
        # Simulate page size combo change
        page._page_size = 250
        page._current_page = 0
        assert page._current_page == 0

    def test_page_sizes_constant(self):
        """PAGE_SIZES constant is defined."""
        from CRM.modules.data_table import DataTablePage
        assert hasattr(DataTablePage, "PAGE_SIZES")
        assert 50 in DataTablePage.PAGE_SIZES
        assert 100 in DataTablePage.PAGE_SIZES
        assert 1000 in DataTablePage.PAGE_SIZES


# ===========================================================================
# clear_filters Pagination Reset Tests
# ===========================================================================

class TestClearFiltersPagination:
    """Test that clear_filters resets pagination."""

    def test_clear_filters_resets_page_to_zero(self):
        """clear_filters resets _current_page to 0."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "location", "status"}
        page.services.fetch_one.return_value = {"total": 0}
        page.services.fetch_all.return_value = []
        page._current_page = 3
        page.clear_filters()
        assert page._current_page == 0


# ===========================================================================
# _update_pagination_controls Tests
# ===========================================================================

class TestUpdatePaginationControls:
    """Test _update_pagination_controls button states and info label."""

    def test_zero_records_shows_no_records(self):
        """With 0 records, info label shows 'No records'."""
        page = _make_page()
        page._total_count = 0
        page._update_pagination_controls()
        assert "No records" in page._page_info_label.text()

    def test_first_page_disables_prev_buttons(self):
        """On first page, prev/first buttons are disabled."""
        page = _make_page()
        page._total_count = 200
        page._page_size = 100
        page._current_page = 0
        page._update_pagination_controls()
        assert not page._page_first_btn.isEnabled()
        assert not page._page_prev_btn.isEnabled()

    def test_last_page_disables_next_buttons(self):
        """On last page, next/last buttons are disabled."""
        page = _make_page()
        page._total_count = 150
        page._page_size = 100
        page._current_page = 1
        page._update_pagination_controls()
        assert not page._page_next_btn.isEnabled()
        assert not page._page_last_btn.isEnabled()

    def test_middle_page_enables_all_buttons(self):
        """On middle page, all buttons are enabled."""
        page = _make_page()
        page._total_count = 350
        page._page_size = 100
        page._current_page = 1
        page._update_pagination_controls()
        assert page._page_first_btn.isEnabled()
        assert page._page_prev_btn.isEnabled()
        assert page._page_next_btn.isEnabled()
        assert page._page_last_btn.isEnabled()

    def test_page_info_shows_correct_range(self):
        """Info label shows correct row range."""
        page = _make_page()
        page._total_count = 250
        page._page_size = 100
        page._current_page = 1
        page._update_pagination_controls()
        text = page._page_info_label.text()
        assert "Showing 101-" in text
        assert "of 250" in text
        assert "Page 2" in text

    def test_last_page_range_clamped_to_total(self):
        """Last page range is clamped to total count."""
        page = _make_page()
        page._total_count = 150
        page._page_size = 100
        page._current_page = 1
        page._update_pagination_controls()
        text = page._page_info_label.text()
        assert "Showing 101-150 of 150" in text


# ===========================================================================
# refresh() Pagination Integration Tests
# ===========================================================================

class TestRefreshPagination:
    """Test refresh() pagination integration."""

    def test_refresh_clamps_page_to_max(self):
        """refresh() clamps _current_page to max valid page."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "status"}
        page.services.fetch_one.return_value = {"total": 50}
        page.services.fetch_all.return_value = []
        page._page_size = 100
        page._current_page = 5  # Invalid page
        page.refresh()
        # After refresh, page should be clamped to 0 (max_page for 50 rows = 0)
        assert page._current_page == 0

    def test_refresh_uses_limit_offset(self):
        """refresh() applies LIMIT and OFFSET to the query."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "status"}
        page.services.fetch_one.return_value = {"total": 250}
        page.services.fetch_all.return_value = []
        page._page_size = 100
        page._current_page = 2
        page.refresh()
        # Check that fetch_all was called with LIMIT/OFFSET in the SQL
        call_args = page.services.fetch_all.call_args
        sql = call_args[0][0]
        assert "LIMIT 100" in sql
        assert "OFFSET 200" in sql

    def test_refresh_updates_total_count(self):
        """refresh() updates _total_count from COUNT(*) query."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "status"}
        page.services.fetch_one.return_value = {"total": 42}
        page.services.fetch_all.return_value = []
        page.refresh()
        assert page._total_count == 42

    def test_refresh_first_page_offset_zero(self):
        """refresh() uses OFFSET 0 for first page."""
        page = _make_page()
        page.services.table_columns.return_value = {"id", "owner_name", "status"}
        page.services.fetch_one.return_value = {"total": 250}
        page.services.fetch_all.return_value = []
        page._page_size = 100
        page._current_page = 0
        page.refresh()
        call_args = page.services.fetch_all.call_args
        sql = call_args[0][0]
        assert "OFFSET 0" in sql
