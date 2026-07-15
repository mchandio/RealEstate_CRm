import socket
import threading
from http.server import ThreadingHTTPServer
from typing import Type


def _is_port_free(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.close()
        return True
    except OSError:
        return False


def start_threaded_server(address: tuple[str, int], handler: Type) -> ThreadingHTTPServer:
    host, port = address
    if not _is_port_free(host, port):
        raise OSError(f"Port {port} on {host} is already in use")
    server = ThreadingHTTPServer((host, port), handler)

    def serve():
        try:
            server.serve_forever()
        except Exception:
            pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return server
