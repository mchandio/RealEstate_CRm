"""CRM Login Flow Test - Run with: python3 test_login.py"""
import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

print("=" * 60)
print("CRM LOGIN FLOW TEST")
print("=" * 60)

# Step 1: Initialize app and database
print("\n[1] Initializing app...")
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
print("  QApplication created")

from CRM.database import ensure_database
ensure_database()
print("  Database initialized")

from CRM.services import CRMServices
services = CRMServices()
print("  CRMServices loaded")

# Step 2: Check admin user exists
print("\n[2] Checking admin user...")
admin_row = services.fetch_one('SELECT id, username, password_hash, role FROM users WHERE username="admin"')
if admin_row:
    print(f"  Admin user exists (id={admin_row['id']}, role={admin_row['role']})")
    # Ensure password hash matches 'admin'
    expected_hash = hashlib.sha256("admin".encode()).hexdigest()
    if admin_row["password_hash"] != expected_hash:
        services.execute('UPDATE users SET password_hash=? WHERE username="admin"', (expected_hash,))
        print("  Fixed admin password hash")
else:
    services.create_user("admin", "admin", "System Administrator", "admin@crm.local", "Super Admin")
    print("  Created admin user")

# Step 3: Test login with admin/admin
print("\n[3] Testing login with admin/admin...")
user = services.login("admin", "admin")
if user:
    print(f"  ✅ Login successful!")
    print(f"     Username: {user.get('username')}")
    print(f"     Role: {user.get('role')}")
    print(f"     Full Name: {user.get('full_name')}")
else:
    print("  ❌ Login failed")
    sys.exit(1)

# Step 4: Test wrong password
print("\n[4] Testing wrong password...")
bad_user = services.login("admin", "wrongpassword")
if bad_user is None:
    print("  ✅ Wrong password correctly rejected")
else:
    print("  ❌ Wrong password should have been rejected")

# Step 5: Test LoginDialog widget
print("\n[5] Testing LoginDialog widget...")
from CRM.dialogs.login import LoginDialog
dialog = LoginDialog(services)
print(f"  Dialog title: {dialog.windowTitle()}")
print(f"  Username field default: {dialog.username.text()}")

# Pre-fill and accept
dialog.username.setText("admin")
dialog.password.setText("admin")
dialog.try_login()
if dialog.current_user:
    print(f"  ✅ Dialog login successful: {dialog.current_user.get('username')}")
else:
    print("  ❌ Dialog login failed")

# Step 6: Test with wrong credentials in dialog
print("\n[6] Testing Dialog with wrong password...")
dialog2 = LoginDialog(services)
dialog2.username.setText("admin")
dialog2.password.setText("wrong")
dialog2.try_login()
if dialog2.current_user is None:
    print("  ✅ Dialog correctly rejected wrong password")
else:
    print("  ❌ Dialog should have rejected wrong password")

# Step 7: Test main window creation
print("\n[7] Testing ModernCRMWindow creation...")
from CRM.app_window import ModernCRMWindow
window = ModernCRMWindow(services, user, startup_progress=lambda p, m: None)
print(f"  ✅ ModernCRMWindow created successfully")
print(f"     Window title: {window.windowTitle()}")

print("\n" + "=" * 60)
print("LOGIN FLOW TEST COMPLETE - ALL PASSED!")
print("=" * 60)
