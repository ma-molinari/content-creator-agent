"""Minimal S3 protocol stub for the isolated Docker rehearsal only."""
import hashlib
import json
import os
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OBJECTS = {}
AGE_SECONDS = int(os.getenv("REHEARSAL_AGE_SECONDS", "0"))
LOCK = threading.Lock()
NAMESPACE = "http://s3.amazonaws.com/doc/2006-03-01/"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def parsed(self):
        url = urllib.parse.urlsplit(self.path)
        return urllib.parse.unquote(url.path).lstrip("/").split("/", 1), urllib.parse.parse_qs(url.query, keep_blank_values=True)

    def respond(self, status, body=b"", headers=None):
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_PUT(self):
        parts, _ = self.parsed()
        if len(parts) == 1:
            return self.respond(200)
        data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        key = parts[1]
        with LOCK:
            if self.headers.get("If-None-Match") == "*" and key in OBJECTS:
                return self.respond(412, b"<Error><Code>PreconditionFailed</Code></Error>")
            OBJECTS[key] = (data, self.headers.get("Content-Type", "application/octet-stream"), time.time() - AGE_SECONDS)
        self.respond(200, headers={"ETag": '"' + hashlib.md5(data).hexdigest() + '"'})

    def do_GET(self):
        if self.path == "/__rehearsal/count":
            with LOCK:
                count = len(OBJECTS)
            return self.respond(200, json.dumps({"count": count}).encode(), {"Content-Type": "application/json"})
        parts, query = self.parsed()
        if len(parts) == 1:
            prefix = query.get("prefix", [""])[0]
            root = ET.Element("ListBucketResult", xmlns=NAMESPACE)
            ET.SubElement(root, "Name").text = parts[0]
            ET.SubElement(root, "Prefix").text = prefix
            ET.SubElement(root, "IsTruncated").text = "false"
            with LOCK:
                for key, (data, _, modified) in sorted(OBJECTS.items()):
                    if not key.startswith(prefix):
                        continue
                    item = ET.SubElement(root, "Contents")
                    ET.SubElement(item, "Key").text = key
                    ET.SubElement(item, "LastModified").text = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(modified))
                    ET.SubElement(item, "ETag").text = '"' + hashlib.md5(data).hexdigest() + '"'
                    ET.SubElement(item, "Size").text = str(len(data))
            return self.respond(200, ET.tostring(root), {"Content-Type": "application/xml"})
        with LOCK:
            obj = OBJECTS.get(parts[1])
        if obj is None:
            return self.respond(404, b"<Error><Code>NoSuchKey</Code></Error>", {"Content-Type": "application/xml"})
        data, content_type, _ = obj
        return self.respond(200, data, {"Content-Type": content_type, "ETag": '"' + hashlib.md5(data).hexdigest() + '"'})

    def do_HEAD(self):
        self.do_GET()

    def do_DELETE(self):
        parts, _ = self.parsed()
        with LOCK:
            OBJECTS.pop(parts[1], None)
        return self.respond(204)

    def do_POST(self):
        if self.path == "/__rehearsal/remove-attachments":
            with LOCK:
                keys = [key for key in OBJECTS if "/chat-attachments/" in key]
                for key in keys:
                    del OBJECTS[key]
            return self.respond(200, json.dumps({"removed": len(keys)}).encode(), {"Content-Type": "application/json"})
        _, query = self.parsed()
        if "delete" not in query:
            return self.respond(400)
        data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        root = ET.fromstring(data)
        result = ET.Element("DeleteResult", xmlns=NAMESPACE)
        with LOCK:
            for item in root.iter():
                if item.tag.endswith("Key") and item.text:
                    OBJECTS.pop(item.text, None)
                    deleted = ET.SubElement(result, "Deleted")
                    ET.SubElement(deleted, "Key").text = item.text
        return self.respond(200, ET.tostring(result), {"Content-Type": "application/xml"})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
