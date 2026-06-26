from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.auth import hash_password
from backend.database import Base
from backend.models import User
from backend.routers.auth_router import LOGIN_FAILURE_LIMIT, _login_failures, login
from backend.schemas import LoginRequest


class FakeRequest:
    def __init__(self, host: str = "127.0.0.1", headers: dict[str, str] | None = None):
        self.client = SimpleNamespace(host=host)
        self.headers = headers or {}


@pytest.fixture
def auth_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(
        User(
            username="RemoteUser",
            password_hash=hash_password("secret123"),
            full_name="Remote User",
            role="Staff",
            is_active=True,
        )
    )
    db.commit()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()
        _login_failures.clear()


def test_remote_login_accepts_trimmed_case_insensitive_username(auth_db):
    response = login(
        LoginRequest(username=" remoteuser ", password="secret123"),
        FakeRequest(headers={"x-forwarded-for": "203.0.113.25, 127.0.0.1"}),
        auth_db,
    )

    assert response.user["username"] == "RemoteUser"
    assert response.access_token


def test_correct_remote_password_bypasses_previous_failed_attempt_lockout(auth_db):
    request = FakeRequest(headers={"CF-Connecting-IP": "203.0.113.50"})
    for _ in range(LOGIN_FAILURE_LIMIT):
        with pytest.raises(HTTPException) as exc:
            login(LoginRequest(username="remoteuser", password="wrong"), request, auth_db)
        assert exc.value.status_code == 401

    response = login(LoginRequest(username="REMOTEUSER", password="secret123"), request, auth_db)

    assert response.user["username"] == "RemoteUser"
    assert response.access_token


def test_forwarded_for_spoofing_does_not_bypass_throttle_by_default(auth_db, monkeypatch):
    monkeypatch.delenv("CRM_TRUST_PROXY_HEADERS", raising=False)

    for index in range(LOGIN_FAILURE_LIMIT):
        request = FakeRequest(
            host="198.51.100.10",
            headers={"x-forwarded-for": f"203.0.113.{index}"},
        )
        with pytest.raises(HTTPException) as exc:
            login(LoginRequest(username="remoteuser", password="wrong"), request, auth_db)
        assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        login(
            LoginRequest(username="remoteuser", password="wrong"),
            FakeRequest(host="198.51.100.10", headers={"x-forwarded-for": "203.0.113.250"}),
            auth_db,
        )

    assert exc.value.status_code == 429


def test_forwarded_for_is_trusted_only_when_proxy_headers_enabled(auth_db, monkeypatch):
    monkeypatch.setenv("CRM_TRUST_PROXY_HEADERS", "1")

    for _ in range(LOGIN_FAILURE_LIMIT):
        with pytest.raises(HTTPException) as exc:
            login(
                LoginRequest(username="remoteuser", password="wrong"),
                FakeRequest(host="198.51.100.10", headers={"x-forwarded-for": "203.0.113.1"}),
                auth_db,
            )
        assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        login(
            LoginRequest(username="remoteuser", password="wrong"),
            FakeRequest(host="198.51.100.10", headers={"x-forwarded-for": "203.0.113.2"}),
            auth_db,
        )

    assert exc.value.status_code == 401
