from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, LoginLog
from backend.schemas import LoginRequest, UserCreate, UserUpdate, ChangePassword, TokenResponse
from backend.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_permission, ROLE_PERMISSIONS, normalize_role,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
LOGIN_FAILURE_WINDOW = timedelta(minutes=10)
LOGIN_FAILURE_LIMIT = 8
_login_failures: dict[str, list[datetime]] = {}


def _login_key(request: Request, username: str) -> str:
    ip_address = request.client.host if request.client else "unknown"
    return f"{ip_address}:{username.strip().lower()}"


def _recent_login_failures(key: str) -> list[datetime]:
    now = datetime.now()
    recent = [stamp for stamp in _login_failures.get(key, []) if now - stamp <= LOGIN_FAILURE_WINDOW]
    _login_failures[key] = recent
    return recent


def _check_login_throttle(request: Request, username: str) -> str:
    key = _login_key(request, username)
    if len(_recent_login_failures(key)) >= LOGIN_FAILURE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.")
    return key


def _record_login_failure(key: str) -> None:
    recent = _recent_login_failures(key)
    recent.append(datetime.now())
    _login_failures[key] = recent


def _record_login_success(key: str) -> None:
    _login_failures.pop(key, None)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    throttle_key = _check_login_throttle(request, req.username)
    ip_address = request.client.host if request.client else None
    user = db.query(User).filter(User.username == req.username, User.is_active == True).first()
    if not user or not verify_password(req.password, user.password_hash):
        _record_login_failure(throttle_key)
        db.add(LoginLog(user_id=None, login_time=datetime.now(), status="Failed", ip_address=ip_address))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    _record_login_success(throttle_key)
    user.last_login = datetime.now()
    user.role = normalize_role(user.role)
    db.add(LoginLog(user_id=user.id, login_time=datetime.now(), status="Success", ip_address=ip_address))
    db.commit()
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        user={
            "id": user.id, "username": user.username,
            "full_name": user.full_name, "email": user.email,
            "role": normalize_role(user.role), "is_active": user.is_active,
        }
    )


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id, "username": user.username,
        "full_name": user.full_name, "email": user.email,
        "role": normalize_role(user.role), "is_active": user.is_active,
    }


@router.post("/change-password")
def change_password(
    req: ChangePassword,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"ok": True, "message": "Password changed"}


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users")),
):
    users = db.query(User).order_by(User.id).all()
    return [
        {
            "id": u.id, "username": u.username,
            "full_name": u.full_name, "email": u.email,
            "role": normalize_role(u.role), "is_active": u.is_active,
            "last_login": str(u.last_login) if u.last_login else None,
        }
        for u in users
    ]


@router.post("/users")
def create_user(
    req: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users")),
):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    role = normalize_role(req.role)
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail="Invalid role")
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        email=req.email,
        role=role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"ok": True, "id": new_user.id, "message": "User created"}


@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users")),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": u.id, "username": u.username,
        "full_name": u.full_name, "email": u.email,
        "role": normalize_role(u.role), "is_active": u.is_active,
        "last_login": str(u.last_login) if u.last_login else None,
    }


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    req: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users")),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if req.username is not None:
        u.username = req.username
    if req.full_name is not None:
        u.full_name = req.full_name
    if req.email is not None:
        u.email = req.email
    if req.role is not None:
        role = normalize_role(req.role)
        if role not in ROLE_PERMISSIONS:
            raise HTTPException(status_code=400, detail="Invalid role")
        u.role = role
    if req.is_active is not None:
        u.is_active = req.is_active
    if req.password is not None and len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if req.password is not None:
        u.password_hash = hash_password(req.password)
    db.commit()
    return {"ok": True, "message": "User updated"}


@router.delete("/users/{user_id}")
def remove_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users")),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot remove your own user while logged in")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.role in ("Super Admin", "Admin") and u.is_active:
        active_admins = (
            db.query(User)
            .filter(User.id != user_id, User.is_active == True, User.role.in_(["Super Admin", "Admin"]))
            .count()
        )
        if active_admins == 0:
            raise HTTPException(status_code=400, detail="At least one active admin user is required")
    u.is_active = False
    db.commit()
    return {"ok": True, "message": "User removed. Login is disabled for this user."}
