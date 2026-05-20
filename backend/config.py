import os
import secrets
from pathlib import Path

from crm_core.paths import DB_PATH, OUTPUT_DIR

# Database: set DATABASE_URL=postgresql://user:pass@host/db for PostgreSQL.
# Default uses the same SQLite database as the Qt desktop app so LAN users and
# desktop users see one shared CRM.
CRM_DB_PATH = Path(os.getenv("CRM_DB_PATH", str(DB_PATH)))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{CRM_DB_PATH.as_posix()}")

def _persistent_secret(name: str) -> str:
    """Create one stable local secret so LAN logins survive app restarts."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    secret_path = OUTPUT_DIR / name
    try:
        existing = secret_path.read_text(encoding="utf-8").strip()
        if len(existing) >= 32:
            return existing
    except FileNotFoundError:
        pass
    secret = secrets.token_urlsafe(48)
    secret_path.write_text(secret, encoding="utf-8")
    return secret


JWT_SECRET = os.getenv("JWT_SECRET") or _persistent_secret(".crm_jwt_secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

API_PORT = int(os.getenv("API_PORT", "6090"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    if os.getenv("CRM_ALLOW_WIDE_CORS") == "1":
        return ["*"]
    # The web UI is normally served from the same FastAPI origin, so broad CORS
    # is unnecessary. These localhost entries keep local development convenient.
    return [
        f"http://127.0.0.1:{API_PORT}",
        f"http://localhost:{API_PORT}",
    ]


CORS_ORIGINS = _cors_origins()
CORS_ORIGIN_REGEX = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?",
)

# Admin seed
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@company.com")
