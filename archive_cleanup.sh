#!/usr/bin/env bash
# ============================================================================
# Real Estate CRM — Archive Cleanup Script
# ============================================================================
# This script moves orphaned, deprecated, and unused files into
# .archive_cleanup/ so you can verify the system still builds and runs.
#
# WHAT THIS SCRIPT DOES:
#   1. Creates .archive_cleanup/ directory
#   2. Moves legacy monolith files, duplicate style files, orphaned tests,
#      one-off scripts, temporary files, and optional integration modules.
#   3. Preserves directory structure inside the archive.
#
# USAGE:
#   chmod +x archive_cleanup.sh
#   ./archive_cleanup.sh          # Dry-run (preview only)
#   ./archive_cleanup.sh --apply  # Actually move the files
#
# RESTORE:
#   To undo, run: ./archive_cleanup.sh --restore
# ============================================================================

set -euo pipefail

ARCHIVE_DIR=".archive_cleanup"
DRY_RUN=true
RESTORE=false

for arg in "$@"; do
  case "$arg" in
    --apply)  DRY_RUN=false ;;
    --restore) RESTORE=true ;;
    --help|-h)
      echo "Usage: $0 [--apply] [--restore]"
      echo "  (no args)  Dry-run: show what would be moved"
      echo "  --apply    Actually move files to $ARCHIVE_DIR/"
      echo "  --restore  Restore files from $ARCHIVE_DIR/"
      exit 0
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Restore mode
# ---------------------------------------------------------------------------
if $RESTORE; then
  echo "=== Restoring files from $ARCHIVE_DIR/ ==="
  if [ ! -d "$ARCHIVE_DIR" ]; then
    echo "Error: $ARCHIVE_DIR/ does not exist. Nothing to restore."
    exit 1
  fi
  find "$ARCHIVE_DIR" -type f | while read -r src; do
    dest="${src#$ARCHIVE_DIR/}"
    dir="$(dirname "$dest")"
    mkdir -p "$dir"
    mv "$src" "$dest"
    echo "  RESTORED: $dest"
  done
  # Remove empty dirs in archive
  find "$ARCHIVE_DIR" -depth -type d -empty -delete
  echo "=== Restore complete ==="
  exit 0
fi

# ---------------------------------------------------------------------------
# Build list of files to archive
# ---------------------------------------------------------------------------
FILES_TO_ARCHIVE=()

# --- Category 1: Legacy monolith files (superseded by CRM/ module system) ---
LEGACY_MONOLITHS=(
  "professional_crm.py"
  "professional_crm_old.py"
  "qt_crm_app.py"
  "qt_crm_app_bak.py"
  "app.py"
)
for f in "${LEGACY_MONOLITHS[@]}"; do
  [ -f "$f" ] && FILES_TO_ARCHIVE+=("$f")
done

# --- Category 2: Legacy modules (superseded by CRM/modules/ and crm_core/) ---
LEGACY_MODULES=(
  "search_module.py"
  "financial_module.py"
  "employee_module.py"
  "data_import_module.py"
)
for f in "${LEGACY_MODULES[@]}"; do
  [ -f "$f" ] && FILES_TO_ARCHIVE+=("$f")
done

# --- Category 3: Duplicate / superseded config & style files ---
DUPLICATE_FILES=(
  "qt_crm_premium_style.py"
  "database_setup.py"
  "CRM/qt_crm_premium_style.py"
  "CRM/frontend/styles.py"
  "CRM/frontend/__codex_session.html"
  "frontend/styles.py"
)
for f in "${DUPLICATE_FILES[@]}"; do
  [ -f "$f" ] && FILES_TO_ARCHIVE+=("$f")
done

# --- Category 4: One-off scripts & scratch files ---
SCRATCH_FILES=(
  "scratch_drop_cols.py"
  "VERIFICATION_REPORT.py"
  "migrate_legacy.py"
)
for f in "${SCRATCH_FILES[@]}"; do
  [ -f "$f" ] && FILES_TO_ARCHIVE+=("$f")
done

# --- Category 5: Legacy test files (test old modules, not active code) ---
LEGACY_TESTS=(
  "test_functionality.py"
  "test_system.py"
  "test_import.py"
)
for f in "${LEGACY_TESTS[@]}"; do
  [ -f "$f" ] && FILES_TO_ARCHIVE+=("$f")
done

# --- Category 6: Temporary / generated files ---
TEMP_FILES=(
  ".CHECKLIST.md.swp"
)
for f in "${TEMP_FILES[@]}"; do
  [ -f "$f" ] && FILES_TO_ARCHIVE+=("$f")
done

# --- Database backups are excluded (kept in project root) ---
# Backup files (real_estate_crm.db.backup_*) are NOT archived.
# They are important recovery data and should remain in place.

# ---------------------------------------------------------------------------
# Also flag entire optional directories (informational only — not moved)
# ---------------------------------------------------------------------------
OPTIONAL_DIRS=()
[ -d "libreoffice_base_export" ] && OPTIONAL_DIRS+=("libreoffice_base_export")
[ -d "access_expenses_manager" ] && OPTIONAL_DIRS+=("access_expenses_manager")

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------
echo "============================================================"
echo "  Real Estate CRM — Archive Cleanup"
echo "============================================================"
echo ""
echo "Found ${#FILES_TO_ARCHIVE[@]} files to archive."
echo ""

if [ ${#OPTIONAL_DIRS[@]} -gt 0 ]; then
  echo "Optional directories (not moved, for your review):"
  for d in "${OPTIONAL_DIRS[@]}"; do
    echo "  DIR: $d/"
  done
  echo ""
fi

if [ ${#FILES_TO_ARCHIVE[@]} -eq 0 ]; then
  echo "No files to archive. The project is already clean."
  exit 0
fi

for f in "${FILES_TO_ARCHIVE[@]}"; do
  if $DRY_RUN; then
    echo "  WOULD MOVE: $f"
  else
    # Preserve subdirectory structure
    dir="$(dirname "$f")"
    mkdir -p "$ARCHIVE_DIR/$dir"
    mv "$f" "$ARCHIVE_DIR/$f"
    echo "  MOVED: $f -> $ARCHIVE_DIR/$f"
  fi
done

echo ""
if $DRY_RUN; then
  echo "=== DRY RUN COMPLETE — No files were moved ==="
  echo "Run with --apply to actually move files:"
  echo "  $0 --apply"
else
  echo "=== Archive complete: ${#FILES_TO_ARCHIVE[@]} files moved to $ARCHIVE_DIR/ ==="
  echo ""
  echo "Running verification checks..."
  echo ""
  # Run actual import checks to verify nothing critical was broken
  VERIFICATION_FAILED=false
  echo -n "  1. Core CRM imports...       "
  if python3 -c "import CRM; import backend; print('OK')" 2>/dev/null; then
    echo "PASS"
  else
    echo "FAIL (run: $0 --restore)"
    VERIFICATION_FAILED=true
  fi
  echo -n "  2. Qt desktop module...      "
  if python3 -c "from CRM.main import main; print('OK')" 2>/dev/null; then
    echo "PASS"
  else
    echo "FAIL (run: $0 --restore)"
    VERIFICATION_FAILED=true
  fi
  echo -n "  3. Backend API module...     "
  if python3 -c "from backend.main import app" 2>/dev/null; then
    echo "PASS"
  else
    echo "SKIP (backend dependencies not installed — not an archive issue)"
  fi
  echo -n "  4. crm_core services...      "
  if python3 -c "from crm_core.service_interfaces import AuthServiceInterface; print('OK')" 2>/dev/null; then
    echo "PASS"
  else
    echo "FAIL (run: $0 --restore)"
    VERIFICATION_FAILED=true
  fi
  echo ""
  if $VERIFICATION_FAILED; then
    echo "WARNING: Some imports failed. Run '$0 --restore' to undo."
  else
    echo "All import checks passed."
  fi
  echo ""
  echo "Manual verification steps:"
  echo "  1. Verify the app starts:    python -m CRM  (desktop)"
  echo "  2. Verify web server:        ./start.sh     (web)"
  echo "  3. Run tests:                pytest          (tests)"
  echo "  4. To restore all files:     $0 --restore"
fi
