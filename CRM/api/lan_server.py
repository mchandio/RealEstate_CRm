"""LAN Server - Uvicorn/Browser Portal Server.

Extracts the uvicorn/LAN browser server logic from ModernCRMWindow.
Runs the FastAPI backend as a daemon thread for browser access.
"""
from __future__ import annotations

import socket
import threading
from typing import Any, TYPE_CHECKING

from CRM.constants import LAN_WEB_HOST, LAN_WEB_PORT, LAN_WEB_ENABLED

if TYPE_CHECKING:
    pass


class LanServer:
    """LAN browser portal server using uvicorn/FastAPI.

    Runs the backend FastAPI application as a daemon thread,
    allowing browser-based access to CRM data from client computers.
    """

    def __init__(self) -> None:
        self._server: Any | None = None
        self._thread: threading.Thread | None = None
        self._owns_server: bool = False
        self._status: str = "Starting"
        self._url: str = ""

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running."""
        return self._owns_server and self._server is not None

    @property
    def status(self) -> str:
        """Return current server status message."""
        return self._status

    @property
    def url(self) -> str:
        """Return the server URL."""
        return self._url

    def start(self, status_callback: Any = None) -> None:
        """Start the LAN browser server.

        Args:
            status_callback: Optional callable(status: str, url: str | None) for status updates.
        """
        def set_status(status: str, url: str | None = None) -> None:
            self._status = status
            if url is not None:
                self._url = url
            if status_callback:
                status_callback(status, url)

        if not LAN_WEB_ENABLED:
            set_status("Browser server disabled", "Set CRM_LAN_WEB_ENABLED=1 to enable")
            return

        if _is_port_open("127.0.0.1", LAN_WEB_PORT):
            self._owns_server = False
            set_status("Browser server already running", f"http://{_get_local_ip()}:{LAN_WEB_PORT}")
            return

        try:
            import uvicorn
            from backend.main import app as fastapi_app
        except Exception as exc:
            set_status("Browser server unavailable", str(exc))
            print(f"LAN web server import error: {exc}")
            return

        try:
            config = uvicorn.Config(
                fastapi_app,
                host=LAN_WEB_HOST,
                port=LAN_WEB_PORT,
                reload=False,
                access_log=False,
                log_level="warning",
                log_config=None,
            )
            server = uvicorn.Server(config)
        except Exception as exc:
            set_status("Browser server unavailable", str(exc))
            print(f"LAN web server startup error: {exc}")
            return

        self._server = server
        self._owns_server = True

        def serve() -> None:
            try:
                server.run()
            except BaseException as exc:
                self._status = f"Browser server stopped: {exc}"
                if status_callback:
                    status_callback(self._status, None)
                print(f"LAN web server error: {exc}")

        self._thread = threading.Thread(target=serve, name="CRM-LAN-Web-Server", daemon=True)
        self._thread.start()
        set_status("Browser login online", self._url or f"http://{_get_local_ip()}:{LAN_WEB_PORT}")

    def stop(self) -> None:
        """Stop the LAN browser server if we own it."""
        if not self._owns_server:
            self._server = None
            self._thread = None
            return
        try:
            if self._server:
                self._server.should_exit = True
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2)
        except Exception:
            pass
        self._server = None
        self._thread = None
        self._owns_server = False


def _get_local_ip() -> str:
    """Get the local IP address for network access."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _is_port_open(host: str, port: int) -> bool:
    """Check if a port is already in use."""
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False
