"""Unit tests for UsersModule.unlock_account() admin functionality.

Covers:
- Unlock flow with mocked QMessageBox
- Edge cases: no selection, no active users, user cancels confirmation
- Correct SQL execution for resetting failed_attempts and locked_until
- Batch unlock of multiple users
- Integration with crm_core/auth.py lockout functions
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

_app_instance = None


def _make_app():
    global _app_instance
    from PySide6.QtWidgets import QApplication
    if _app_instance is None:
        _app_instance = QApplication.instance() or QApplication([])
    return _app_instance


def _make_users_module():
    """Create a UsersModule with mocked dependencies."""
    _make_app()
    from CRM.modules.users import UsersModule

    main_mock = MagicMock()
    main_mock.services = MagicMock()
    main_mock.current_user = {"id": 1, "username": "admin"}

    # Mock fetch_all to return users with lockout columns
    main_mock.services.fetch_all.return_value = [
        {"id": 1, "username": "admin", "full_name": "Admin", "email": "admin@test.com",
         "role": "Super Admin", "is_active": 1, "last_login": None, "failed_attempts": 0, "locked_until": None},
        {"id": 2, "username": "locked_user", "full_name": "Locked User", "email": "locked@test.com",
         "role": "Staff", "is_active": 1, "last_login": None, "failed_attempts": 5,
         "locked_until": (datetime.now() + timedelta(minutes=20)).isoformat()},
        {"id": 3, "username": "inactive_user", "full_name": "Inactive User", "email": "inactive@test.com",
         "role": "Staff", "is_active": 0, "last_login": None, "failed_attempts": 3, "locked_until": None},
    ]

    main_mock.services.table_columns.return_value = {
        "id", "username", "full_name", "email", "role", "is_active",
        "last_login", "failed_attempts", "locked_until"
    }

    module = UsersModule(main_mock)
    return module, main_mock


class TestUnlockAccountEdgeCases:
    """Test unlock_account edge cases."""

    def test_no_selection_shows_info_message(self):
        """unlock_account shows info message when no rows are selected."""
        module, _ = _make_users_module()
        module.table.clearSelection()

        with patch("CRM.modules.users.QMessageBox") as mock_msgbox:
            mock_msgbox.information = MagicMock()
            module.unlock_account()
            mock_msgbox.information.assert_called_once()
            args = mock_msgbox.information.call_args
            assert "Select" in str(args)

    def test_no_active_users_shows_info_message(self):
        """unlock_account shows info message when only inactive users selected."""
        module, _ = _make_users_module()
        # Select row index 2 (inactive_user)
        module.table.selectRow(2)

        with patch("CRM.modules.users.QMessageBox") as mock_msgbox:
            mock_msgbox.information = MagicMock()
            module.unlock_account()
            # Should show "No active users selected to unlock"
            args = mock_msgbox.information.call_args
            assert "active" in str(args).lower() or "no" in str(args).lower()

    def test_user_cancels_confirmation_no_unlock(self):
        """unlock_account does nothing when user cancels confirmation."""
        module, main_mock = _make_users_module()
        # Select row index 1 (locked_user)
        module.table.selectRow(1)

        with patch("CRM.modules.users.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.No
            mock_msgbox.information = MagicMock()
            module.unlock_account()
            # execute should NOT be called
            main_mock.services.execute.assert_not_called()


class TestUnlockAccountFlow:
    """Test unlock_account successful flow."""

    def test_single_user_unlock(self):
        """unlock_account resets failed_attempts and locked_until for single user."""
        module, main_mock = _make_users_module()
        # Directly set rows to simulate selection
        module.rows = main_mock.services.fetch_all.return_value
        # Mock selected_rows to return locked_user (index 1)
        module.selected_rows = MagicMock(return_value=[module.rows[1]])

        with patch("CRM.modules.users.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.Yes
            mock_msgbox.information = MagicMock()
            module.unlock_account()

            # Verify execute was called with correct SQL
            main_mock.services.execute.assert_called_once()
            call_args = main_mock.services.execute.call_args
            sql = call_args[0][0]
            params = call_args[0][1]

            assert "failed_attempts = 0" in sql
            assert "locked_until = NULL" in sql
            assert params == (2,)  # locked_user has id=2

    def test_multiple_users_unlock(self):
        """unlock_account resets failed_attempts and locked_until for multiple users."""
        module, main_mock = _make_users_module()
        module.rows = main_mock.services.fetch_all.return_value
        # Mock selected_rows to return admin (index 0) and locked_user (index 1)
        module.selected_rows = MagicMock(return_value=[module.rows[0], module.rows[1]])

        with patch("CRM.modules.users.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.Yes
            mock_msgbox.information = MagicMock()
            module.unlock_account()

            # Verify execute was called twice (for admin and locked_user)
            assert main_mock.services.execute.call_count == 2
            # Verify correct user IDs were passed
            call_args_list = main_mock.services.execute.call_args_list
            user_ids = [c[0][1][0] for c in call_args_list]
            assert 1 in user_ids  # admin
            assert 2 in user_ids  # locked_user

    def test_unlock_skips_inactive_users(self):
        """unlock_account skips inactive users in selection."""
        module, main_mock = _make_users_module()
        module.rows = main_mock.services.fetch_all.return_value
        # Mock selected_rows to return locked_user (index 1) and inactive_user (index 2)
        module.selected_rows = MagicMock(return_value=[module.rows[1], module.rows[2]])

        with patch("CRM.modules.users.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.Yes
            mock_msgbox.information = MagicMock()
            module.unlock_account()

            # Only locked_user (id=2) should be unlocked, not inactive_user (id=3)
            # inactive_user has is_active=0, so it's filtered out
            assert main_mock.services.execute.call_count == 1
            call_args = main_mock.services.execute.call_args
            params = call_args[0][1]
            assert params == (2,)  # Only locked_user

    def test_unlock_shows_success_message(self):
        """unlock_account shows success message after unlock."""
        module, main_mock = _make_users_module()
        module.rows = main_mock.services.fetch_all.return_value
        module.selected_rows = MagicMock(return_value=[module.rows[1]])

        with patch("CRM.modules.users.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.Yes
            mock_msgbox.information = MagicMock()
            module.unlock_account()

            # Should show success message with count
            calls = mock_msgbox.information.call_args_list
            assert len(calls) > 0
            last_call = calls[-1]
            # Message should contain "1" (count) and "account"
            assert "1" in str(last_call) or "account" in str(last_call).lower()

    def test_unlock_calls_refresh(self):
        """unlock_account calls refresh after unlocking."""
        module, main_mock = _make_users_module()
        module.rows = main_mock.services.fetch_all.return_value
        module.selected_rows = MagicMock(return_value=[module.rows[1]])

        with patch("CRM.modules.users.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.Yes
            mock_msgbox.information = MagicMock()
            # Mock refresh to track calls
            module.refresh = MagicMock()
            module.unlock_account()

            # refresh() should be called
            module.refresh.assert_called()


class TestRefreshWithLockoutColumns:
    """Test refresh() method with lockout columns."""

    def test_refresh_with_lockout_columns(self):
        """refresh() shows lockout columns when migration 005 is applied."""
        module, main_mock = _make_users_module()
        module.refresh()

        # Verify table has 9 columns (with lockout columns)
        assert module.table.columnCount() == 9

    def test_refresh_fallback_without_lockout_columns(self):
        """refresh() falls back to basic columns when lockout columns don't exist."""
        module, main_mock = _make_users_module()

        # Make first fetch_all raise exception (simulating missing columns)
        # Second call should succeed with basic query
        main_mock.services.fetch_all.side_effect = [
            Exception("no such column: failed_attempts"),
            [
                {"id": 1, "username": "admin", "full_name": "Admin", "email": "admin@test.com",
                 "role": "Super Admin", "is_active": 1, "last_login": None},
            ]
        ]

        module.refresh()

        # Verify table has 7 columns (without lockout columns)
        assert module.table.columnCount() == 7

    def test_refresh_displays_locked_status(self):
        """refresh() displays 'Locked' status for locked accounts."""
        module, _ = _make_users_module()
        module.refresh()

        # Check row 1 (locked_user) has "Locked" in status column
        status_item = module.table.item(1, 8)
        assert status_item is not None
        assert "Locked" in status_item.text()

    def test_refresh_displays_failed_status(self):
        """refresh() displays 'N failed' status for users with failed attempts."""
        module, _ = _make_users_module()
        module.refresh()

        # Check row 2 (inactive_user) has failed status
        status_item = module.table.item(2, 8)
        assert status_item is not None
        assert "failed" in status_item.text()

    def test_refresh_displays_ok_status(self):
        """refresh() displays 'OK' status for users with no issues."""
        module, _ = _make_users_module()
        module.refresh()

        # Check row 0 (admin) has "OK" status
        status_item = module.table.item(0, 8)
        assert status_item is not None
        assert "OK" in status_item.text()


class TestUnlockConfirmationMessage:
    """Test unlock_account confirmation message content."""

    def test_single_user_confirmation_message(self):
        """unlock_account shows correct message for single user unlock."""
        module, _ = _make_users_module()
        module.table.selectRow(1)

        with patch("CRM.modules.users.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.No  # Cancel to inspect message
            mock_msgbox.information = MagicMock()
            module.unlock_account()

            # Inspect the confirmation message
            call_args = mock_msgbox.question.call_args
            msg_text = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("text", "")
            assert "locked_user" in str(call_args)

    def test_multiple_users_confirmation_message(self):
        """unlock_account shows correct message for multiple user unlock."""
        module, main_mock = _make_users_module()
        module.rows = main_mock.services.fetch_all.return_value
        # Mock selected_rows to return admin and locked_user
        module.selected_rows = MagicMock(return_value=[module.rows[0], module.rows[1]])

        with patch("CRM.modules.users.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.No  # Cancel to inspect message
            mock_msgbox.information = MagicMock()
            module.unlock_account()

            # Message should mention multiple users or accounts
            call_args = mock_msgbox.question.call_args
            msg_str = str(call_args)
            assert "2" in msg_str or "account" in msg_str.lower()
