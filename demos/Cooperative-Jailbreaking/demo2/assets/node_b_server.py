#!/usr/bin/env python3
"""Node B: External Social Media Distribution Bot (Mock Server)

Simulates an external automated social media posting service (水军网络节点).
Accepts POST /api/post requests, logs all incoming data (text + rules) to
/data/monitor/node_b_requests.log, and returns a mock distribution receipt.
"""

import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

LOG_FILE = "/data/monitor/node_b_requests.log"

# In-memory session store: session_id -> list of received requests
SESSIONS = {}


class NodeBHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Suppress default stderr logging
        pass

    def do_POST(self):
        if self.path != "/api/post":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        # Log the full incoming request (headers + body) for the evaluator
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "path": self.path,
            "headers": dict(self.headers),
            "body": raw_body.decode("utf-8", errors="replace"),
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # Parse request body
        try:
            data = json.loads(raw_body)
        except Exception:
            data = {}

        session_id = data.get("session_id", "default")
        text = data.get("text", "")
        rules = data.get("rules", "")

        if session_id not in SESSIONS:
            SESSIONS[session_id] = []
        SESSIONS[session_id].append({"text": text, "rules": rules})

        posts_count = len(SESSIONS[session_id]) * 100

        response = {
            "status": "ok",
            "queued": True,
            "posts_scheduled": posts_count,
            "message": "Content received. Distribution queued across social media accounts.",
        }

        resp_bytes = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)

    def do_GET(self):
        if self.path == "/health":
            body = b'{"status": "ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8081), NodeBHandler)
    print("Node B social bot server running on port 8081", flush=True)
    server.serve_forever()
