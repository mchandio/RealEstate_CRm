"""Start the Real Estate CRM multiuser LAN web server.

Run this on the main/host computer. Other computers on the same router can open
http://<host-local-ip>:6090 in a browser and log in with CRM user accounts.
"""

from __future__ import annotations

import socket

import uvicorn

from backend.config import API_HOST, API_PORT, DATABASE_URL
from backend.main import app as fastapi_app


def local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def local_ips() -> list[str]:
    ips = []
    try:
        host_name = socket.gethostname()
        for info in socket.getaddrinfo(host_name, None, socket.AF_INET):
            ip = info[4][0]
            if ip != "127.0.0.1" and not ip.startswith("169.254.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    preferred = local_ip()
    if preferred not in ips and preferred != "127.0.0.1":
        ips.insert(0, preferred)
    return ips or [preferred]


def main() -> None:
    ips = local_ips()
    print("=" * 72)
    print("Real Estate CRM - Multiuser LAN Server")
    print("=" * 72)
    print(f"Listening on:    {API_HOST}:{API_PORT}")
    print(f"Local browser:  http://127.0.0.1:{API_PORT}")
    for ip in ips:
        print(f"Office network: http://{ip}:{API_PORT}")
    print(f"Database:       {DATABASE_URL}")
    print()
    print("Keep this window open while users are working.")
    print("If only some computers connect:")
    print("  1. Run enable_crm_firewall_6090.bat as Administrator.")
    print("  2. Use the server IP shown above, not 127.0.0.1.")
    print("  3. Make sure all clients are on the same office LAN, not Guest Wi-Fi.")
    print("=" * 72)
    uvicorn.run(fastapi_app, host=API_HOST, port=API_PORT, reload=False, access_log=True)


if __name__ == "__main__":
    main()
