"""Forward to isolated LocalStack and age only ListObjectsV2 response metadata."""
import http.client
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

LOCK = threading.Lock()
STATS = {"aged_timestamps": 0, "forwarded_requests": 0}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def forward(self):
        if self.command == "GET" and self.path == "/__rehearsal/stats":
            with LOCK:
                payload = json.dumps(STATS).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        with LOCK:
            STATS["forwarded_requests"] += 1
        connection = http.client.HTTPConnection("s3", 4566, timeout=30)
        try:
            headers = {key: value for key, value in self.headers.items() if key.lower() != "connection"}
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            content = response.read()
            query = parse_qs(urlsplit(self.path).query)
            if self.command == "GET" and query.get("list-type") == ["2"] and response.status == 200:
                content, count = re.subn(rb"(<LastModified>)[^<]+(</LastModified>)", rb"\g<1>2000-01-01T00:00:00.000Z\g<2>", content)
                with LOCK:
                    STATS["aged_timestamps"] += count
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in {"content-length", "transfer-encoding", "connection", "server", "date"}:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(content)
        finally:
            connection.close()

    do_GET = forward
    do_HEAD = forward
    do_PUT = forward
    do_POST = forward
    do_DELETE = forward


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
