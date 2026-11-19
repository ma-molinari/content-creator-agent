"""Forward worker callbacks and drop one response after the API commits."""
import http.client
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()
STATS = {"completion_attempts": 0, "responses_dropped": 0}


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
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        connection = http.client.HTTPConnection("api", 8081, timeout=30)
        try:
            connection.request("POST", self.path, body=body, headers={
                "Content-Type": self.headers.get("Content-Type", "application/json"),
                "X-Worker-API-Key": self.headers.get("X-Worker-API-Key", ""),
            })
            response = connection.getresponse()
            content = response.read()
            drop = False
            if self.path.endswith("/complete"):
                with LOCK:
                    STATS["completion_attempts"] += 1
                    if response.status == 204 and STATS["responses_dropped"] == 0:
                        STATS["responses_dropped"] += 1
                        drop = True
            if drop:
                self.close_connection = True
                self.connection.shutdown(socket.SHUT_RDWR)
                return
            self.send_response(response.status)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        finally:
            connection.close()


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8081), Handler).serve_forever()
