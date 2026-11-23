"""Test-only CONNECT proxy that can pause S3 traffic before forwarding TLS."""
import json
import select
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RELEASED = threading.Event()
LOCK = threading.Lock()
STATS = {"connections": 0}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path != "/__rehearsal/stats":
            self.send_error(404)
            return
        with LOCK:
            body = json.dumps(STATS).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/__rehearsal/release":
            self.send_error(404)
            return
        RELEASED.set()
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_CONNECT(self):
        host, separator, port = self.path.rpartition(":")
        if not separator or port != "443" or not host.endswith(".amazonaws.com"):
            self.send_error(403)
            return
        with LOCK:
            STATS["connections"] += 1
        self.send_response(200, "Connection established")
        self.end_headers()
        self.close_connection = True
        if not RELEASED.wait(120):
            return
        try:
            with socket.create_connection((host, 443), timeout=10) as target:
                self.connection.settimeout(30)
                while True:
                    ready, _, _ = select.select([self.connection, target], [], [], 30)
                    if not ready:
                        return
                    for source in ready:
                        data = source.recv(65536)
                        if not data:
                            return
                        destination = target if source is self.connection else self.connection
                        destination.sendall(data)
        except (OSError, ValueError):
            return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 3128), Handler).serve_forever()
