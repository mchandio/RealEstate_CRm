# COMPREHENSIVE AI IMPLEMENTATION PROMPT
## Real Estate CRM: Fix All 9 Critical/High Issues

---

## CONTEXT

**Project**: Real Estate CRM (MBM Enterprises) - Karachi-based property management  
**Problem**: Desktop (PySide6 Qt) and Web (Vanilla JS + FastAPI) UIs are out of sync, causing data inconsistencies  
**Setup**: 3 locations sharing one SQLite database on network drive  
**Goal**: Implement all 9 critical/high priority fixes to align Desktop and Web UIs  

**Files involved**:
- `qt_crm_app.py` (Desktop UI, ~6400 lines)
- `frontend/app.js` (Web UI frontend, ~2500 lines)
- `backend/main.py` & `backend/routers/records_router.py` (FastAPI backend)
- `crm_core/ecosystem.py` (Phase 1 Contract - schema definitions)
- `database_setup.py` (Database schema)
- `real_estate_crm.db` (SQLite database)

---

## ISSUE SUMMARY

| # | Issue | Severity | Type | Est. Time |
|---|-------|----------|------|-----------|
| 1 | SQLite Backup Locking | 🔴 CRITICAL | Infrastructure | 30 min |
| 2 | Contact Field Proliferation | 🔴 CRITICAL | Data Schema | 120 min |
| 3 | Phone Validation Asymmetry | 🟠 HIGH | Validation | 30 min |
| 4 | Status Field Case Mismatch | 🟠 HIGH | Data Format | 30 min |
| 5 | Budget Field Inconsistency | 🟠 HIGH | Data Schema | 60 min |
| 6 | Date Timezone Issues | 🟠 HIGH | Data Format | 60 min |
| 7 | Null Handling Asymmetry | 🟠 HIGH | Data Format | 30 min |
| 8 | Status Column Name Variance | 🟠 HIGH | Data Schema | 60 min |
| 9 | Currency Formatting Differences | 🟠 HIGH | Data Format | 30 min |

**Total Time**: ~8-10 hours

---

# ISSUE #1: SQLite BACKUP LOCKING (🔴 CRITICAL)

## Problem
When Desktop auto-backup runs on close, it locks the entire SQLite database for 30+ seconds. All Web users at other locations get "database is locked" errors during this time. With 3 concurrent locations, this creates daily disruption.

## Root Cause
- SQLite default journal mode (`delete`) locks entire DB during backup
- Desktop `shutil.copy2()` doesn't release lock until copy completes
- No coordination between Desktop and Web API

## Solution
Enable Write-Ahead Logging (WAL) mode for SQLite. WAL allows concurrent reads while writes happen, preventing database locks.

## Implementation

### Step 1.1: Create `crm_core/database_init.py`
```python
"""Database initialization - Enable WAL mode"""
import sqlite3
import os
import sys

def initialize_database(db_path):
    """Initialize database with WAL mode for safe concurrent access"""
    if not os.path.exists(db_path):
        print(f"❌ ERROR: Database not found: {db_path}")
        return False
    
    print(f"Initializing database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current journal mode
        cursor.execute("PRAGMA journal_mode")
        current_mode = cursor.fetchone()[0]
        print(f"   Current journal mode: {current_mode}")
        
        # Enable WAL mode
        cursor.execute("PRAGMA journal_mode=WAL")
        new_mode = cursor.fetchone()[0]
        print(f"   ✓ Set journal mode: {new_mode}")
        
        # Configure auto-checkpoint
        cursor.execute("PRAGMA wal_autocheckpoint=1000")
        print(f"   ✓ WAL auto-checkpoint: 1000 pages")
        
        # Sync mode FULL for safety
        cursor.execute("PRAGMA synchronous=FULL")
        print(f"   ✓ Synchronous mode: FULL")
        
        # Cache size
        cursor.execute("PRAGMA cache_size=5000")
        print(f"   ✓ Cache size: 5000 pages")
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys=ON")
        print(f"   ✓ Foreign keys: enabled")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Database initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, "real_estate_crm.db")
    success = initialize_database(db_path)
    sys.exit(0 if success else 1)
```

### Step 1.2: Execute script
```bash
python crm_core/database_init.py
```

### Step 1.3: Update Desktop closeEvent in `qt_crm_app.py`
Find the `closeEvent` method (around line 5612) and update it to not force backup:

**OLD CODE** (around line 5612):
```python
def closeEvent(self, event):
    # AUTO-BACKUP before closing
    try:
        self.backup_database()
    except Exception as e:
        print(f"Backup error: {e}")
    event.accept()
```

**NEW CODE**:
```python
def closeEvent(self, event):
    # Request backup via API (non-blocking)
    try:
        self.request_backup_via_api()
    except Exception as e:
        print(f"Backup request failed: {e}")
    event.accept()

def request_backup_via_api(self):
    """Request backup through backend (safe for concurrent users)"""
    try:
        import requests
        requests.post("http://localhost:6091/api/system/backup/schedule", timeout=2)
    except:
        pass
```

### Step 1.4: Add endpoint to `backend/main.py`
Add this new endpoint to your FastAPI app:

```python
import shutil
from datetime import datetime
import os

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "backups")

@app.post("/api/system/backup/schedule")
async def schedule_backup():
    """Schedule a backup (non-blocking for concurrent users)"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")
        
        # WAL mode makes this non-blocking
        import sqlite3
        db_path = DATABASE_URL.replace("sqlite:///", "")
        
        # Use sqlite3 backup API
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(backup_path)
        with dest:
            source.backup(dest, pages=100, sleep=0.001)
        source.close()
        
        # Cleanup old backups
        cleanup_old_backups(BACKUP_DIR, keep_count=30)
        
        return {"status": "backup_completed", "path": backup_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def cleanup_old_backups(backup_dir, keep_count=30):
    """Remove old backups"""
    try:
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("backup_")], reverse=True)
        for old_backup in backups[keep_count:]:
            os.remove(os.path.join(backup_dir, old_backup))
    except:
        pass
```

## Verification
- WAL mode enabled: Run `PRAGMA journal_mode;` in SQLite browser - should return "wal"
- Desktop closes without blocking: Open Web UI, close Desktop, Web should remain responsive
- No "database is locked" errors in Web UI logs

---

# ISSUE #2: CONTACT FIELD PROLIFERATION (🔴 CRITICAL)

## Problem
Same logical field "contact phone" is stored in 5 different columns:
- `rent_requirements.contact`
- `rent_requirements.contact_phone`
- `rent_availability.owner_contact`
- `sale_requirements.contact`
- `sale_availability.owner_contact`

When data is entered in one column, it appears missing when accessed from another column in a different UI.

## Root Cause
Inconsistent database schema design. Each table evolved separately without normalization.

## Solution
Consolidate all contact fields into 2 standardized columns per table:
- `*_requirements`: `contact_person` + `contact_phone`
- `*_availability`: `owner_name` + `owner_phone`

## Implementation

### Step 2.1: Create Migration Script `migrations/001_consolidate_contact_fields.py`

```python
#!/usr/bin/env python
"""Migration: Consolidate scattered contact fields"""

import sqlite3
import os
import shutil
from datetime import datetime
import sys

def backup_database(db_path):
    """Create backup before migration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✓ Backup created: {os.path.basename(backup_path)}")
        return backup_path
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return None

def get_db_info(conn):
    """Get info about current state"""
    cursor = conn.cursor()
    info = {}
    
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN contact IS NOT NULL THEN 1 END) as has_contact,
               COUNT(CASE WHEN contact_phone IS NOT NULL THEN 1 END) as has_contact_phone
        FROM rent_requirements
    """)
    info['rent_requirements'] = cursor.fetchone()
    
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN owner_contact IS NOT NULL THEN 1 END) as has_owner_contact
        FROM rent_availability
    """)
    info['rent_availability'] = cursor.fetchone()
    
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN contact IS NOT NULL THEN 1 END) as has_contact
        FROM sale_requirements
    """)
    info['sale_requirements'] = cursor.fetchone()
    
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN owner_contact IS NOT NULL THEN 1 END) as has_owner_contact
        FROM sale_availability
    """)
    info['sale_availability'] = cursor.fetchone()
    
    return info

def migrate(db_path, dry_run=False):
    """Run migration"""
    if not os.path.exists(db_path):
        print(f"❌ ERROR: Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("=" * 70)
        print("MIGRATION: Consolidate Contact Fields")
        print("=" * 70)
        
        info = get_db_info(conn)
        
        print(f"\n  Rent Requirements: {info['rent_requirements'][0]} records")
        print(f"    - have 'contact' data: {info['rent_requirements'][1]}")
        print(f"    - have 'contact_phone' data: {info['rent_requirements'][2]}")
        
        print(f"\n  Rent Availability: {info['rent_availability'][0]} records")
        print(f"    - have 'owner_contact' data: {info['rent_availability'][1]}")
        
        print(f"\n  Sale Requirements: {info['sale_requirements'][0]} records")
        print(f"    - have 'contact' data: {info['sale_requirements'][1]}")
        
        print(f"\n  Sale Availability: {info['sale_availability'][0]} records")
        print(f"    - have 'owner_contact' data: {info['sale_availability'][1]}")
        
        if dry_run:
            print("\n⚠️  DRY RUN MODE - No changes")
        else:
            print("\n🔄 Executing migration...")
        
        # Rent Requirements: contact → contact_person
        print("\n1. Rent Requirements (contact → contact_person)...")
        if not dry_run:
            cursor.execute("ALTER TABLE rent_requirements RENAME COLUMN contact TO contact_person")
            print("   ✓ Renamed")
        
        # Rent Availability: owner_contact → owner_phone
        print("\n2. Rent Availability (owner_contact → owner_phone)...")
        if not dry_run:
            cursor.execute("ALTER TABLE rent_availability RENAME COLUMN owner_contact TO owner_phone")
            print("   ✓ Renamed")
        
        # Sale Requirements: contact → contact_person
        print("\n3. Sale Requirements (contact → contact_person)...")
        if not dry_run:
            cursor.execute("ALTER TABLE sale_requirements RENAME COLUMN contact TO contact_person")
            print("   ✓ Renamed")
        
        # Sale Availability: owner_contact → owner_phone
        print("\n4. Sale Availability (owner_contact → owner_phone)...")
        if not dry_run:
            cursor.execute("ALTER TABLE sale_availability RENAME COLUMN owner_contact TO owner_phone")
            print("   ✓ Renamed")
        
        if not dry_run:
            conn.commit()
            print("\n" + "=" * 70)
            print("✅ MIGRATION SUCCESSFUL")
            print("=" * 70)
        else:
            conn.rollback()
            print("\n" + "=" * 70)
            print("✅ DRY RUN SUCCESSFUL")
            print("=" * 70)
        
        return True
    
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        if not dry_run:
            conn.rollback()
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, "real_estate_crm.db")
    
    dry_run = "--dry-run" in sys.argv
    
    print()
    
    if dry_run:
        print("🧪 DRY-RUN MODE")
        result = migrate(db_path, dry_run=True)
    else:
        backup = backup_database(db_path)
        if not backup:
            sys.exit(1)
        print()
        result = migrate(db_path, dry_run=False)
    
    print()
    sys.exit(0 if result else 1)
```

### Step 2.2: Run DRY-RUN first
```bash
python migrations/001_consolidate_contact_fields.py --dry-run
```

### Step 2.3: Execute Migration
```bash
# Ensure no users are connected
python migrations/001_consolidate_contact_fields.py
```

### Step 2.4: Update `crm_core/ecosystem.py` - Phase 1 Contract
Find `PHASE1_CONTRACT` and update field names:

**OLD**:
```python
"rent_requirements": {
    "contact": str,
    "contact_phone": str,
    ...
}
```

**NEW**:
```python
"rent_requirements": {
    "contact_person": str,
    "contact_phone": str,
    ...
}
```

Do the same for:
- `rent_availability`: `owner_contact` → `owner_phone`
- `sale_requirements`: `contact` → `contact_person`
- `sale_availability`: `owner_contact` → `owner_phone`

### Step 2.5: Update `qt_crm_app.py` - All Contact Field References
Replace all occurrences of old column names with new ones:

**Search & Replace patterns**:
```
"contact"           → "contact_person"
"owner_contact"     → "owner_phone"
'contact'           → 'contact_person'
'owner_contact'     → 'owner_phone'
```

**Key sections to update** (use Find in qt_crm_app.py):
- Line ~2340: save_rent_requirement()
- Line ~2600: save_rent_availability()
- Line ~3200: save_sale_requirement()
- Line ~3500: save_sale_availability()
- Line ~5098: Duplicate client detection logic
- Any SELECT/INSERT/UPDATE queries with "contact" or "owner_contact"

### Step 2.6: Update `backend/routers/records_router.py`
Replace in all API routes:
- `contact` → `contact_person` in rent_requirements
- `owner_contact` → `owner_phone` in rent_availability
- `contact` → `contact_person` in sale_requirements
- `owner_contact` → `owner_phone` in sale_availability

Example locations:
- Database queries (SELECT, INSERT, UPDATE, WHERE)
- Schema definitions/Pydantic models
- API request/response bodies

### Step 2.7: Update `frontend/app.js`
Replace in all JavaScript code:
```javascript
// OLD patterns
row.contact
row.owner_contact
data.contact
data.owner_contact

// NEW patterns
row.contact_person
row.owner_phone
data.contact_person
data.owner_phone
```

Search for these in form handling, table rendering, API calls.

---

# ISSUE #3: PHONE VALIDATION ASYMMETRY (🟠 HIGH)

## Problem
- Desktop: Strict validation - rejects phones that don't match "03XXXXXXXXX" format
- Web: No validation - accepts anything

Result: User creates record on Web, can't edit on Desktop (validation fails).

## Solution
Centralize phone validation in `crm_core/validators.py`. Both UIs use same validation logic.

## Implementation

### Step 3.1: Create `crm_core/validators.py`
```python
"""Centralized validators for Desktop and Web"""
import re

class PhoneValidator:
    """Pakistan phone number validation"""
    
    @staticmethod
    def validate_phone(phone_str):
        """
        Accept multiple formats, return normalized 11-digit format
        Valid:
        - 03001234567 (11 digits)
        - 0300-123-4567 (with separators)
        - +923001234567 (international)
        - 923001234567 (country code without +)
        """
        if not phone_str:
            return None
        
        # Remove all non-digits
        digits = re.sub(r'\D', '', str(phone_str))
        
        # Handle international format
        if digits.startswith("92"):
            if len(digits) == 12:
                digits = "0" + digits[2:]
        
        # Validate: 11 digits starting with 03
        if not (len(digits) == 11 and digits.startswith("03")):
            raise ValueError(f"Invalid phone format: {phone_str}")
        
        return digits
    
    @staticmethod
    def display_phone(digits):
        """Format for display: 03001234567 → +92 300 1234567"""
        if not digits or len(digits) != 11:
            return digits
        return f"+92 {digits[1:4]} {digits[4:]}"
```

### Step 3.2: Update `qt_crm_app.py`
Replace phone validation calls:

```python
from crm_core.validators import PhoneValidator

def save_contact_phone(self, phone_str):
    try:
        normalized = PhoneValidator.validate_phone(phone_str)
        return normalized
    except ValueError as e:
        QMessageBox.warning(self, "Invalid Phone", str(e))
        return None
```

### Step 3.3: Update `backend/routers/records_router.py`
```python
from crm_core.validators import PhoneValidator

@router.post("/api/rent_requirements")
async def create_rent_requirement(data: RentRequirementSchema):
    try:
        normalized_phone = PhoneValidator.validate_phone(data.contact_phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    data.contact_phone = normalized_phone
    # ... continue save
```

### Step 3.4: Update `frontend/app.js`
```javascript
function validatePhone(input) {
    const digits = input.replace(/\D/g, '');
    
    if (digits.startsWith("92") && digits.length === 12) {
        return "0" + digits.substring(2);
    }
    
    if (digits.length === 11 && digits.startsWith("03")) {
        return digits;
    }
    
    throw new Error("Phone must be: 03001234567 or +923001234567");
}

// On save:
try {
    const normalized = validatePhone(phoneInput.value);
} catch (e) {
    showError(e.message);
}
```

---

# ISSUE #4: STATUS FIELD CASE MISMATCH (🟠 HIGH)

## Problem
- Desktop saves: `status = 'Available'`
- Web sometimes displays: `status = 'available'`
- Search filter: `'Available' ≠ 'available'`

## Solution
Enforce case-insensitive status with normalization to canonical form.

## Implementation

### Step 4.1: Create `crm_core/constants.py`
```python
class StatusConstants:
    """Standardized status values"""
    
    # Rent Availability Statuses
    AVAILABLE = "Available"
    RENTED = "Rented"
    WITHDRAWN = "Withdrawn"
    VALID_STATUSES = [AVAILABLE, RENTED, WITHDRAWN]
    
    @staticmethod
    def normalize(status):
        """Normalize any case variation to canonical form"""
        if not status:
            return StatusConstants.AVAILABLE
        
        for valid in StatusConstants.VALID_STATUSES:
            if status.lower() == valid.lower():
                return valid
        
        raise ValueError(f"Invalid status: {status}")
```

### Step 4.2: Update `backend/routers/records_router.py`
```python
from crm_core.constants import StatusConstants

@router.post("/api/rent_availability")
async def create_rent_availability(data: RentAvailabilitySchema):
    data.status = StatusConstants.normalize(data.status or StatusConstants.AVAILABLE)
    # ... continue save

@router.put("/api/rent_availability/{id}")
async def update_rent_availability(id: int, data: RentAvailabilitySchema):
    data.status = StatusConstants.normalize(data.status)
    # ... continue update

@router.get("/api/rent_availability")
async def get_rent_availability(status_filter: str = None):
    if status_filter:
        status_filter = StatusConstants.normalize(status_filter)
    # ... continue fetch
```

### Step 4.3: Update `qt_crm_app.py`
```python
from crm_core.constants import StatusConstants

def save_status(status_str):
    try:
        normalized = StatusConstants.normalize(status_str)
        return normalized
    except ValueError as e:
        QMessageBox.warning(self, "Invalid Status", str(e))
        return None
```

### Step 4.4: Update `frontend/app.js`
```javascript
const VALID_STATUSES = ["Available", "Rented", "Withdrawn"];

function normalizeStatus(status) {
    if (!status) return "Available";
    
    for (const valid of VALID_STATUSES) {
        if (status.toLowerCase() === valid.toLowerCase()) {
            return valid;
        }
    }
    throw new Error(`Invalid status: ${status}`);
}

// On save/filter:
const normalized = normalizeStatus(userInput);
```

---

# ISSUE #5: BUDGET FIELD INCONSISTENCY (🟠 HIGH)

## Problem
Legacy data has `budget_min` and `budget_max` columns. New data uses single `budget` column. When Web displays old records, it shows 0 (NULL) because it only reads `budget`.

## Solution
Migrate `budget_min`/`budget_max` to single `budget` field.

## Implementation

### Step 5.1: Create Migration Script `migrations/002_consolidate_budget_fields.py`
```python
#!/usr/bin/env python
"""Migration: Consolidate budget_min/max into single budget field"""

import sqlite3
import os
import shutil
from datetime import datetime
import sys

def backup_database(db_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✓ Backup created: {os.path.basename(backup_path)}")
        return backup_path
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def migrate(db_path, dry_run=False):
    """Run migration"""
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("=" * 70)
        print("MIGRATION: Consolidate Budget Fields")
        print("=" * 70)
        
        # Check for old columns
        cursor.execute("PRAGMA table_info(sale_requirements)")
        columns = [row[1] for row in cursor.fetchall()]
        has_budget_min = 'budget_min' in columns
        has_budget_max = 'budget_max' in columns
        
        print(f"\n  Sale Requirements has budget_min: {has_budget_min}")
        print(f"  Sale Requirements has budget_max: {has_budget_max}")
        
        if not (has_budget_min or has_budget_max):
            print("\n  ℹ️  No legacy budget fields found - nothing to migrate")
            return True
        
        if not dry_run:
            # Consolidate sale_requirements
            print("\n1. Consolidating Sale Requirements...")
            cursor.execute("""
                UPDATE sale_requirements
                SET budget = COALESCE(budget, budget_max)
                WHERE budget IS NULL AND budget_max IS NOT NULL
            """)
            print(f"   Updated: {cursor.rowcount} records")
            
            # Similarly for sale_availability if it has demand
            cursor.execute("PRAGMA table_info(sale_availability)")
            cols = [row[1] for row in cursor.fetchall()]
            if 'budget_max' in cols:
                cursor.execute("""
                    UPDATE sale_availability
                    SET demand = COALESCE(demand, budget_max)
                    WHERE demand IS NULL AND budget_max IS NOT NULL
                """)
                print(f"   Updated sale_availability: {cursor.rowcount} records")
            
            conn.commit()
            print("\n✅ MIGRATION SUCCESSFUL")
        else:
            print("\n⚠️  DRY RUN - no changes made")
        
        return True
    
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        if not dry_run:
            conn.rollback()
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, "real_estate_crm.db")
    
    dry_run = "--dry-run" in sys.argv
    
    print()
    if dry_run:
        result = migrate(db_path, dry_run=True)
    else:
        backup = backup_database(db_path)
        if not backup:
            sys.exit(1)
        print()
        result = migrate(db_path, dry_run=False)
    
    print()
    sys.exit(0 if result else 1)
```

### Step 5.2: Run Migration
```bash
python migrations/002_consolidate_budget_fields.py --dry-run
python migrations/002_consolidate_budget_fields.py
```

### Step 5.3: Update Code
Ensure Desktop and Web only reference `budget` column (not `budget_min`/`budget_max`):

**qt_crm_app.py**: Remove any references to `budget_min` or `budget_max`  
**backend/routers/records_router.py**: Same  
**frontend/app.js**: Same

---

# ISSUE #6: DATE TIMEZONE ISSUES (🟠 HIGH)

## Problem
User enters: `01/01/2025` (desktop local time)  
Web user in different timezone retrieves it: displays as `31/12/2024` (1 day off)

## Solution
Always store dates in UTC ISO format. Convert on display based on user's timezone.

## Implementation

### Step 6.1: Create `crm_core/date_utils.py`
```python
"""Date handling with timezone support"""
from datetime import datetime
import pytz

class DateUtils:
    """Consistent date handling across UIs"""
    
    KARACHI_TZ = pytz.timezone("Asia/Karachi")
    UTC_TZ = pytz.UTC
    
    @staticmethod
    def store_date(user_date_str):
        """Convert user input (DD/MM/YYYY) to UTC ISO format"""
        if not user_date_str:
            return None
        
        # Parse user input
        parsed = datetime.strptime(user_date_str, "%d/%m/%Y")
        
        # Treat as local Karachi time
        localized = DateUtils.KARACHI_TZ.localize(parsed)
        
        # Convert to UTC
        utc = localized.astimezone(DateUtils.UTC_TZ)
        
        # Return ISO format with timezone
        return utc.isoformat()
    
    @staticmethod
    def display_date(iso_date_str):
        """Convert UTC ISO to local DD/MM/YYYY"""
        if not iso_date_str:
            return ""
        
        try:
            # Parse ISO
            utc_date = datetime.fromisoformat(iso_date_str)
            
            # Convert to Karachi time
            local_date = utc_date.astimezone(DateUtils.KARACHI_TZ)
            
            # Format for display
            return local_date.strftime("%d/%m/%Y")
        except:
            return iso_date_str
```

### Step 6.2: Update `qt_crm_app.py`
```python
from crm_core.date_utils import DateUtils

def save_date(date_str):
    iso_date = DateUtils.store_date(date_str)
    # Store iso_date in database

def display_date(iso_date):
    return DateUtils.display_date(iso_date)
```

### Step 6.3: Update `backend/routers/records_router.py`
```python
from crm_core.date_utils import DateUtils

@router.post("/api/rent_requirements")
async def create_rent_requirement(data: RentRequirementSchema):
    # Store dates as UTC ISO
    if data.date_field:
        data.date_field = DateUtils.store_date(data.date_field)
    # ... continue save

@router.get("/api/rent_requirements/{id}")
async def get_rent_requirement(id: int):
    record = db.fetch(...)
    # Already stored as ISO, return as-is
    return record
```

### Step 6.4: Update `frontend/app.js`
```javascript
function displayDate(isoDate) {
    if (!isoDate) return "";
    
    const utcDate = new Date(isoDate);
    const day = String(utcDate.getUTCDate()).padStart(2, '0');
    const month = String(utcDate.getUTCMonth() + 1).padStart(2, '0');
    const year = utcDate.getUTCFullYear();
    
    return `${day}/${month}/${year}`;
}

function storeDate(ddmmyyyyStr) {
    if (!ddmmyyyyStr) return null;
    
    const [day, month, year] = ddmmyyyyStr.split('/');
    const localDate = new Date(year, month - 1, day, 0, 0, 0);
    
    return localDate.toISOString();
}
```

---

# ISSUE #7: NULL HANDLING ASYMMETRY (🟠 HIGH)

## Problem
- Desktop: `None` → displays as empty cell or `0.0`
- Web: `null` → displays as "undefined" string

## Solution
Standardize null/undefined handling in both UIs.

## Implementation

### Step 7.1: Update `qt_crm_app.py`
```python
def safe_display_value(value):
    """Convert None/null to empty string for display"""
    if value is None:
        return ""
    if isinstance(value, float) and value == 0.0:
        # Check if this was originally NULL, not actual 0
        return ""
    return str(value)

# In table rendering:
cell_value = safe_display_value(record[field])
```

### Step 7.2: Update `frontend/app.js`
```javascript
function displayValue(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value);
}

// In table rendering:
cell.textContent = displayValue(record[field]);

// In forms:
field.value = displayValue(record[field]) || "";
```

### Step 7.3: Update `backend/routers/records_router.py`
```python
def serialize_record(record):
    """Convert record to JSON, handling nulls"""
    return {
        key: value if value is not None else None  # Explicit None, not 0
        for key, value in record.items()
    }
```

---

# ISSUE #8: STATUS COLUMN NAME VARIANCE (🟠 HIGH)

## Problem
- Rent Requirements uses: `client_status` column
- Rent Availability uses: `client_broker` column
- Same logical concept, different names
- Code gets confused which column to read

## Solution
Standardize to single consistent column name per table.

## Implementation

### Step 8.1: Create Migration `migrations/003_unify_status_columns.py`
```python
#!/usr/bin/env python
"""Migration: Standardize status column names"""

import sqlite3
import os
import shutil
from datetime import datetime
import sys

def backup_database(db_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    try:
        shutil.copy2(db_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def migrate(db_path, dry_run=False):
    """Run migration"""
    if not os.path.exists(db_path):
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("MIGRATION: Unify Status Column Names")
        print("=" * 70)
        
        # Check rent_requirements
        cursor.execute("PRAGMA table_info(rent_requirements)")
        rent_req_cols = [row[1] for row in cursor.fetchall()]
        
        # For rent_requirements: ensure consistent status column
        print("\n1. Rent Requirements:")
        if 'client_status' in rent_req_cols:
            print("   Already uses 'client_status' ✓")
        elif 'status' in rent_req_cols:
            if not dry_run:
                cursor.execute("ALTER TABLE rent_requirements RENAME COLUMN status TO client_status")
            print("   Would rename: status → client_status")
        
        # For rent_availability: standardize to consistent column
        cursor.execute("PRAGMA table_info(rent_availability)")
        rent_avail_cols = [row[1] for row in cursor.fetchall()]
        
        print("\n2. Rent Availability:")
        if 'client_broker' in rent_avail_cols and 'status' not in rent_avail_cols:
            if not dry_run:
                cursor.execute("ALTER TABLE rent_availability RENAME COLUMN client_broker TO status")
            print("   Would rename: client_broker → status")
        else:
            print("   Already consistent ✓")
        
        if not dry_run:
            conn.commit()
            print("\n✅ MIGRATION SUCCESSFUL")
        else:
            conn.rollback()
            print("\n✅ DRY RUN SUCCESSFUL")
        
        return True
    
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        if not dry_run:
            conn.rollback()
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, "real_estate_crm.db")
    
    dry_run = "--dry-run" in sys.argv
    
    print()
    if dry_run:
        result = migrate(db_path, dry_run=True)
    else:
        backup = backup_database(db_path)
        if not backup:
            sys.exit(1)
        print()
        result = migrate(db_path, dry_run=False)
    
    print()
    sys.exit(0 if result else 1)
```

### Step 8.2: Run Migration
```bash
python migrations/003_unify_status_columns.py --dry-run
python migrations/003_unify_status_columns.py
```

### Step 8.3: Update All References
- `qt_crm_app.py`: Search & replace `client_status` and `client_broker` → use consistent name
- `backend/routers/records_router.py`: Same
- `frontend/app.js`: Same

---

# ISSUE #9: CURRENCY FORMATTING DIFFERENCES (🟠 HIGH)

## Problem
- Desktop displays: `Rs.100,000` (no space)
- Web displays: `Rs. 100,000` (space after Rs.)
- Export/import mismatches

## Solution
Centralize currency formatting.

## Implementation

### Step 9.1: Add to `crm_core/formatters.py`
```python
"""Data formatting utilities"""

def format_currency(amount, currency="Rs"):
    """Format amount as currency with thousands separator"""
    if amount is None or amount == "":
        return ""
    
    try:
        amount_float = float(amount)
        # Format with thousands separator
        formatted = f"{amount_float:,.0f}"
        return f"{currency}. {formatted}"  # "Rs. 100,000"
    except (ValueError, TypeError):
        return str(amount)

def parse_currency(formatted_str):
    """Parse formatted currency back to number"""
    if not formatted_str:
        return None
    
    # Remove currency symbol, spaces, commas
    clean = formatted_str.replace("Rs.", "").replace("Rs", "").replace(",", "").strip()
    
    try:
        return float(clean)
    except ValueError:
        return None
```

### Step 9.2: Update `qt_crm_app.py`
```python
from crm_core.formatters import format_currency, parse_currency

def display_budget(amount):
    return format_currency(amount)

def save_budget(formatted_str):
    return parse_currency(formatted_str)
```

### Step 9.3: Update `backend/routers/records_router.py`
```python
from crm_core.formatters import format_currency

@router.get("/api/rent_requirements/{id}")
async def get_rent_requirement(id: int):
    record = db.fetch(...)
    # Return amount as number (frontend will format)
    return record
```

### Step 9.4: Update `frontend/app.js`
```javascript
function formatCurrency(amount) {
    if (!amount) return "";
    const num = parseFloat(amount);
    const formatted = num.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
    return `Rs. ${formatted}`;
}

function parseCurrency(formatted) {
    return parseInt(formatted.replace(/\D/g, ''));
}

// In display:
cell.textContent = formatCurrency(record.budget);

// In forms:
const amount = parseCurrency(input.value);
```

---

## DEPLOYMENT SUMMARY

### Execution Order:
1. Issue #1: Enable WAL mode
2. Issue #2: Contact field consolidation (requires migration)
3. Issue #5: Budget consolidation (requires migration)
4. Issue #8: Status column unification (requires migration)
5. Issues #3, #4, #6, #7, #9: Code updates (no migration needed)

### Coordinate with Users:
- Schedule downtime window when all locations can close apps
- Backup first
- Run migrations
- Update code
- Restart services
- Test all 3 locations

### Testing:
After each issue fix, verify:
- Data appears consistently across UIs
- No validation errors
- Search/filter works
- No database locked errors

---

**Total Implementation Time**: 8-10 hours

---

**END OF PROMPT**
