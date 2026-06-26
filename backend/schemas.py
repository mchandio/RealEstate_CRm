from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str = ""
    email: str = ""
    role: str = "Staff"


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


class RecordCreate(BaseModel):
    data: dict[str, Any]


class RecordUpdate(BaseModel):
    data: dict[str, Any]


class ApprovalAction(BaseModel):
    status: str  # Approved, Resend
    comment: str = ""


class WorkflowAction(BaseModel):
    stage: str
    priority: str = "Medium"
    status: Optional[str] = None
    next_follow_up: Optional[str] = None
    assigned_to: Optional[str] = None
    deal_probability: Optional[float] = None
    expected_close_value: Optional[float] = None
    lost_reason: Optional[str] = None


class MatchRequest(BaseModel):
    record_id: int
    table: str


class ReportRequest(BaseModel):
    report_type: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
