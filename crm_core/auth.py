"""Shared authentication utilities for RealEstate_CRM.

Consolidates password hashing, verification, and rehashing logic used by both
the FastAPI backend (backend/auth.py) and the Qt desktop app (CRM/services.py).

This module is the single source of truth for password operations, fixing the
DRY violation identified in Section 18 of the engineering audit.

Supports:
- bcrypt (preferred, secure, salted, key-stretched)
- SHA-256 (legacy fallback for backward compatibility)
- Automatic rehash from SHA-256 to bcrypt on successful login
- Password strength policy enforcement
- Account lockout after failed attempts
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger("realestate_crm.auth")

# =============================================================================
# Password Strength Policy (Section 8 - Engineering Audit)
# =============================================================================

# Configuration constants
MIN_PASSWORD_LENGTH = 8
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength against security policy.
    
    Returns:
        (is_valid, error_message) tuple
        
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&*()_+-=[]{}|;':",./<>?)
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:",./<>?]', password):
        return False, "Password must contain at least one special character."
    return True, ""


# =============================================================================
# Account Lockout (Section 8 - Engineering Audit)
# =============================================================================

def is_account_locked(db_fetch_one, db_execute, username: str) -> tuple[bool, str]:
    """Check if an account is locked due to failed login attempts.
    
    Args:
        db_fetch_one: Function to fetch a single database row
        db_execute: Function to execute a database query
        username: The username to check
    
    Returns:
        (is_locked, lockout_message) tuple
    """
    try:
        user = db_fetch_one(
            "SELECT id, locked_until, failed_attempts FROM users WHERE LOWER(username) = LOWER(?)",
            (username,)
        )
        if not user:
            return False, ""
        
        locked_until = user.get("locked_until")
        if locked_until:
            try:
                lock_time = datetime.fromisoformat(str(locked_until))
                if datetime.now() < lock_time:
                    remaining = (lock_time - datetime.now()).seconds // 60
                    return True, f"Account is locked. Try again in {remaining + 1} minutes."
                # Lockout expired, reset the counter in database
                db_execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
                    (user["id"],)
                )
                return False, ""
            except (ValueError, TypeError):
                pass
        return False, ""
    except Exception as e:
        logger.debug("Error checking account lockout: %s", e)
        return False, ""


def record_failed_login(db_execute, db_fetch_one, username: str) -> int:
    """Record a failed login attempt and lock account if threshold exceeded.
    
    Args:
        db_execute: Function to execute a database query
        db_fetch_one: Function to fetch a single database row
        username: The username that failed login
    
    Returns:
        Number of consecutive failed attempts
    """
    try:
        user = db_fetch_one(
            "SELECT id, failed_attempts FROM users WHERE LOWER(username) = LOWER(?)",
            (username,)
        )
        if not user:
            return 0
        
        current_attempts = (user.get("failed_attempts") or 0) + 1
        
        if current_attempts >= MAX_FAILED_ATTEMPTS:
            # Lock the account
            lock_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            db_execute(
                "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                (current_attempts, lock_until.isoformat(), user["id"])
            )
            logger.warning("Account locked for user %s after %d failed attempts", username, current_attempts)
        else:
            db_execute(
                "UPDATE users SET failed_attempts = ? WHERE id = ?",
                (current_attempts, user["id"])
            )
        
        return current_attempts
    except Exception as e:
        logger.debug("Error recording failed login: %s", e)
        return 0


def reset_failed_attempts(db_execute, username: str) -> None:
    """Reset failed login attempts on successful login.
    
    Args:
        db_execute: Function to execute a database query
        username: The username that successfully logged in
    """
    try:
        db_execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE LOWER(username) = LOWER(?)",
            (username,)
        )
    except Exception as e:
        logger.debug("Error resetting failed attempts: %s", e)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with automatic fallback to SHA-256.

    Priority: bcrypt (secure, salted, key-stretched)
    Fallback: SHA-256 (for backward compatibility with legacy desktop users)

    New passwords are always hashed with bcrypt. On successful login with
    SHA-256, the hash is automatically rehashed to bcrypt.
    """
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except ImportError:
        logger.debug("bcrypt not available, falling back to SHA-256 password hashing")
        return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash.

    Supports both bcrypt and legacy SHA-256 hashes.
    SHA-256 hashes are detected by pattern (64 hex chars).

    Returns True if the password matches, False otherwise.
    """
    hashed = str(hashed or "")
    if not hashed:
        return False

    # Try bcrypt first (new standard)
    if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except ImportError:
            return False

    # Fallback: Legacy SHA-256 hash detection (64 hex characters)
    if re.fullmatch(r"[0-9a-fA-F]{64}", hashed):
        expected = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(expected.lower(), hashed.lower())

    return False


def needs_rehash(hashed: str) -> bool:
    """Check if a password hash needs to be rehashed to bcrypt.

    Returns True if the hash is a legacy SHA-256 hash that should be
    migrated to bcrypt on next successful login.
    """
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", str(hashed or "")))


def rehash_to_bcrypt(password: str) -> str | None:
    """Generate a new bcrypt hash for rehashing.

    Returns the new bcrypt hash string, or None if bcrypt is not available.
    """
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except ImportError:
        return None
