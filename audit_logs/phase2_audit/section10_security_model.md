# SECTION 10: SECURITY MODEL
## Engineering Audit - Real Estate CRM System

**Date:** 2026-07-15  
**Evidence source:** `backend/auth.py`, `backend/config.py`, `backend/main.py`, `backend/models.py`, `professional_crm.py`, `app.py`, `qt_crm_app_bak.py`, `farmflow_python_app/app.py`

---

## 10.1 Analysis

### Authentication Mechanisms

| Layer | Method | Implementation |
|-------|--------|----------------|
| Backend API | JWT Bearer tokens | `jose.jwt` with HS256, 24h expiry |
| Desktop Qt | Direct SQLite query | SHA-256 password hash comparison |
| FarmFlow | Flask session + CSRF | Session-based with CSRF tokens |

### Password Storage

| Location | Algorithm | Notes |
|----------|-----------|-------|
| `backend/auth.py` | SHA-256 (primary) | Maintains compatibility with Qt desktop |
| `backend/auth.py` | bcrypt (fallback) | Via passlib CryptContext |
| `professional_crm.py` | SHA-256 | Desktop app password hashing |
| `app.py` | SHA-256 | Legacy monolithic app |
| `qt_crm_app_bak.py` | SHA-256 | Backup Qt app |

### Session & Token Management

- **JWT Secret**: Auto-generated persistent file (`.crm_jwt_secret`) or environment variable
- **Token Expiry**: 24 hours (configurable via `JWT_EXPIRY_HOURS`)
- **Token Claims**: User ID (`sub`), expiration (`exp`)
- **Token Transport**: HTTP Bearer header via FastAPI HTTPBearer

### Authorization Model

| Role | Permissions |
|------|------------|
| Super Admin | Full access (dashboard, rent, sale, properties, clients, financial, employees, reports, settings, users, backup, delete, successfactors, workflow) |
| Admin | Full access (same as Super Admin) |
| Manager | Most access (excludes settings, users, backup, delete) |
| Staff | Limited (dashboard, rent, sale, reports, workflow view) |
| Viewer | Read-only (dashboard, rent_view, sale_view, reports) |

### Network Security

**CORS Configuration (`backend/config.py`):**
```python
# Default: localhost only
CORS_ORIGINS = [
    f"http://127.0.0.1:{API_PORT}",
    f"http://localhost:{API_PORT}",
]

# Wide open if CRM_ALLOW_WIDE_CORS=1
if os.getenv("CRM_ALLOW_WIDE_CORS") == "1":
    return ["*"]
```

**Rate Limiting (`backend/main.py`):**
```python
limiter = Limiter(key_func=get_remote_address, default_limits=["30/second"])
```

### Input Validation

- **Pydantic Schemas**: Request/response validation via `backend/schemas.py`
- **Form Validation**: `validate_form_value()` in `app.py` for desktop forms
- **SQL Injection**: Mitigated by SQLAlchemy ORM parameterized queries
- **CSS Validation**: `validate_css_fragment()` in `frontend/styles.py`

### CSRF Protection

| Application | Protected? | Method |
|-------------|-----------|--------|
| FastAPI Backend | No | Stateless JWT (not cookie-based) |
| FarmFlow | Yes | Flask session-based CSRF tokens |
| Desktop Qt | N/A | Not web-based |

### Audit Logging

- **Login Logs**: `login_logs` table tracks login attempts, IP, status
- **Audit Trail**: `audit_logs` table tracks CRUD operations
- **Workflow Audit**: `wf_audit_log` for workflow state changes

---

## 10.2 Findings (ranked)

### Critical

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| S-C1 | **SHA-256 password hashing** is not a proper KDF - lacks salting and key stretching | Offline brute-force attacks if DB compromised | Critical | Migrate to bcrypt/argon2 with automatic rehash on login | Medium | Medium |
| S-C2 | **Default admin credentials** (`admin`/`admin`) created on startup with no forced change | Unauthorized access in production | Critical | Force password change on first login or require env vars | Low | Low |
| S-C3 | **No CSRF protection on FastAPI** state-changing endpoints (uses JWT in headers, not cookies) | Lower risk than cookie-based but still vulnerable to XSS token theft | High | Acceptable for JWT-in-header pattern; ensure XSS prevention | Low | Low |

### High

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| S-H1 | **JWT secret stored on disk** (`.crm_jwt_secret`) without encryption | Secret readable by any local process | High | Use OS keyring or encrypted storage; restrict file permissions | Medium | Low |
| S-H2 | **No password policy enforcement** - no strength requirements, no rotation, no history | Weak passwords persist indefinitely | High | Add password complexity rules, optional rotation policy | Low | Low |
| S-H3 | **No account lockout** mechanism after failed attempts | Unlimited brute-force attempts | High | Add progressive delay or lockout after N failures | Medium | Low |
| S-H4 | **No token revocation** - JWTs valid until expiry even after password change/logout | Stolen tokens remain valid | High | Implement token blacklist or short-lived refresh tokens | High | Medium |
| S-H5 | **CORS wildcard available** via `CRM_ALLOW_WIDE_CORS=1` | Cross-origin requests from any domain | High | Remove wildcard option; use explicit origins only | Low | None |

### Medium

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| S-M1 | **No HTTP security headers** (HSTS, CSP, X-Frame-Options) | Vulnerable to clickjacking, MIME sniffing | Medium | Add security headers middleware | Low | None |
| S-M2 | **No API key authentication** for service-to-service calls | All API access requires user credentials | Medium | Consider API keys for internal services | Low | Low |
| S-M3 | **Role-based only, no field-level permissions** | Users see all data within their role scope | Medium | Add attribute-based access control if needed | High | High |
| S-M4 | **Login logs not indexed** for efficient querying | Slow security investigations | Medium | Add indexes on user_id, login_time, status | Low | None |
| S-M5 | **No password hashing for legacy tables** - direct SHA-256 comparison | Cannot upgrade existing hashes | Medium | Implement hash migration on successful login | Medium | Medium |

### Low

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| S-L1 | **JWT expiry not configurable per-role** | All users get same token lifetime | Low | Allow shorter tokens for elevated roles | Low | Low |
| S-L2 | **No login attempt logging for desktop app** | Incomplete security audit trail | Low | Add login logging to Qt authentication | Low | Low |
| S-L3 | **No HTTPS enforcement** in code | Tokens transmitted in plaintext if not terminated at proxy | Low | Document TLS requirement; add HSTS header | Low | None |

---

## 10.3 Recommendations

### Immediate (Phase 8 - Security)

1. **Password Hashing Migration:**
   ```python
   # In backend/auth.py
   def verify_password(password: str, hashed: str) -> bool:
       # Check if legacy SHA-256 hash
       if re.fullmatch(r"[0-9a-fA-F]{64}", hashed):
           if hashlib.sha256(password.encode()).hexdigest().lower() == hashed.lower():
               # Rehash with bcrypt on successful login
               new_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
               # Update in DB
               return True
           return False
       # Verify bcrypt
       return bcrypt.checkpw(password.encode(), hashed.encode())
   ```

2. **Admin Password Enforcement:**
   - Require `ADMIN_PASSWORD` environment variable in production
   - Or force password change on first login via flag

3. **Security Headers Middleware:**
   ```python
   @app.middleware("http")
   async def add_security_headers(request, call_next):
       response = await call_next(request)
       response.headers["X-Content-Type-Options"] = "nosniff"
       response.headers["X-Frame-Options"] = "DENY"
       response.headers["X-XSS-Protection"] = "1; mode=block"
       response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
       return response
   ```

### Medium-term

4. **Token Revocation:** Implement Redis-backed token blacklist or use short-lived access tokens with refresh token rotation.

5. **Rate Limiting Enhancement:** Add per-endpoint rate limits, especially for `/api/auth/login` (e.g., 5/minute).

6. **Audit Log Enhancement:** Add structured security events (login failures, permission denials, data exports).

---

## 10.4 Security Controls Summary

| Control | Status | Notes |
|---------|--------|-------|
| Authentication | ✅ Implemented | JWT + password |
| Authorization | ✅ Implemented | Role-based permissions |
| Password Hashing | ⚠️ Partial | SHA-256 primary, bcrypt fallback |
| CSRF Protection | ❌ Not needed | JWT in headers, not cookies |
| Rate Limiting | ✅ Implemented | 30/second global |
| Input Validation | ✅ Implemented | Pydantic + form validation |
| SQL Injection Prevention | ✅ Implemented | SQLAlchemy ORM |
| Audit Logging | ✅ Implemented | Login + CRUD + workflow |
| HTTPS Enforcement | ❌ Not implemented | Document requirement |
| Security Headers | ❌ Not implemented | Add middleware |
| Account Lockout | ❌ Not implemented | Add in Phase 8 |
| Password Policy | ❌ Not implemented | Add in Phase 8 |
| Token Revocation | ❌ Not implemented | Consider in Phase 8 |

---

## 10.5 Validation Results

| Check | Result |
|-------|--------|
| Password storage algorithm | SHA-256 (primary), bcrypt (fallback) |
| JWT implementation | HS256, 24h expiry, persistent secret |
| CORS configuration | localhost only (default), wildcard option exists |
| Rate limiting | 30/second global via slowapi |
| CSRF protection | Not applicable (JWT in headers) |
| Audit logging | login_logs, audit_logs, wf_audit_log tables |
| Input validation | Pydantic schemas, form validators |

---

## 10.6 Code Changes

**None.** Prompt Phase 2 is audit-only for this section.

---

## 10.7 Next Proposed Phase Step

**Section 11: Performance Bottlenecks** (depends on this section) — query analysis, N+1 detection, memory profiling, caching opportunities.
