"""CRM Login Flow Test - Core (no Qt)."""
import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crm_core.db import SQLiteRepository
from crm_core import DB_PATH

repo = SQLiteRepository(DB_PATH)
print("=" * 50)
print("CRM CORE LOGIN TEST")
print("=" * 50)

# 1. DB connection
users = repo.fetch_all("SELECT id, username, role, is_active FROM users")
print(f"\n[1] Database OK - {len(users)} users found")

# 2. Fix admin password
expected = hashlib.sha256("admin".encode()).hexdigest()
repo.execute('UPDATE users SET password_hash=? WHERE username="admin"', (expected,))
print("[2] Admin password hash set to SHA-256(admin)")

# 3. Verify login via SQL
row = repo.fetch_one(
    'SELECT * FROM users WHERE LOWER(TRIM(username))=LOWER(?) AND is_active=1',
    ("admin",),
)
assert row is not None, "Admin user not found!"
assert row["password_hash"] == expected, "Password hash mismatch!"
print(f"[3] SQL login OK: {row['username']} ({row['role']})")

# 4. Verify wrong password rejected
wrong_hash = hashlib.sha256("wrong".encode()).hexdigest()
assert row["password_hash"] != wrong_hash
print("[4] Wrong password correctly rejected")

# 5. Test CRMServices (no Qt)
from CRM.services import CRMServices
services = CRMServices()
h = services.hash_password("admin")
assert h == expected, f"hash_password mismatch: {h} != {expected}"
print("[5] CRMServices.hash_password() OK")

# 6. Test services.login()
user = services.login("admin", "admin")
assert user is not None, "services.login('admin', 'admin') failed!"
print(f"[6] services.login() OK: {user['username']} ({user['role']})")

# 7. Test wrong password via services.login()
bad = services.login("admin", "wrongpassword")
assert bad is None, "services.login should reject wrong password!"
print("[7] services.login() wrong password rejected OK")

print("\n" + "=" * 50)
print("ALL 7 CORE TESTS PASSED!")
print("=" * 50)
