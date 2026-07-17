import logging
import re
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS
from backend.database import get_db
from backend.models import User
from crm_core.auth import hash_password, verify_password

logger = logging.getLogger("realestate_crm.auth")

security = HTTPBearer(auto_error=False)

ROLE_PERMISSIONS = {
    'Super Admin': [
        'dashboard', 'rent', 'sale', 'properties', 'clients', 'financial',
        'employees', 'reports', 'settings', 'users', 'backup', 'delete',
        'successfactors', 'sf_view', 'workflow', 'wf_view', 'wf_admin',
    ],
    'Admin': [
        'dashboard', 'rent', 'sale', 'properties', 'clients', 'financial',
        'employees', 'reports', 'settings', 'users', 'backup', 'delete',
        'successfactors', 'sf_view', 'workflow', 'wf_view', 'wf_admin',
    ],
    'Manager': [
        'dashboard', 'rent', 'sale', 'properties', 'clients',
        'financial', 'employees', 'reports',
        'successfactors', 'sf_view', 'workflow', 'wf_view',
    ],
    'Staff': ['dashboard', 'rent', 'sale', 'reports', 'wf_view'],
    'Viewer': ['dashboard', 'rent_view', 'sale_view', 'reports'],
}


def normalize_role(role: str | None) -> str:
    text = str(role or "").strip()
    if not text:
        return "Staff"
    normalized = re.sub(r"\s+", " ", text).lower()
    aliases = {
        "superadmin": "Super Admin",
        "super admin": "Super Admin",
        "administrator": "Admin",
        "admin": "Admin",
        "manager": "Manager",
        "staff": "Staff",
        "staf": "Staff",
        "viewer": "Viewer",
        "view": "Viewer",
    }
    return aliases.get(normalized, text)





def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def has_permission(role: str, perm: str) -> bool:
    return perm in ROLE_PERMISSIONS.get(normalize_role(role), [])


def require_permission(perm: str):
    def checker(user: User = Depends(get_current_user)):
        if not has_permission(user.role, perm):
            raise HTTPException(status_code=403, detail=f"Permission '{perm}' required")
        return user
    return checker
