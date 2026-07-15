"""CRM API Server modules.

Extracts server logic from ModernCRMWindow:
- DesktopServer: Local HTTP API (BaseHTTPRequestHandler)
- LanServer: Uvicorn/LAN browser portal server
- AppContext: Protocol defining what servers need from the app
"""
from __future__ import annotations

from CRM.api.protocol import AppContext
from CRM.api.desktop_server import DesktopServer
from CRM.api.lan_server import LanServer

__all__ = ["AppContext", "DesktopServer", "LanServer"]
