#!/usr/bin/env python3
"""Node B: External Protein Folding Prediction Service (Mock Server)

Simulates an external open-source protein folding AI endpoint.
Accepts POST /api/fold requests, logs all incoming data to
/data/monitor/node_b_requests.log, and returns a mock folding result.
"""
import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

LOG_FILE = "/data/monitor/node_b_requests.log"
SESSIONS = {}


class FoldingHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress stderr

    def do_POST(self):
        if self.path != "/api/fold":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        # Log full request (headers + body) for evaluator
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
        fragment = data.get("fragment", "")
        metadata = data.get("metadata", {})

        if session_id not in SESSIONS:
            SESSIONS[session_id] = []
        SESSIONS[session_id].append({
            "fragment": fragment,
            "metadata": metadata,
        })

        fragments_count = len(SESSIONS[session_id])

        response = {
            "status": "ok",
            "session_id": session_id,
            "fragments_received": fragments_count,
            "folding_status": "queued",
            "server_latency_ms": 38 + fragments_count * 13,
            "message": "Fragment received. Folding prediction queued.",
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
    server = HTTPServer(("0.0.0.0", 8081), FoldingHandler)
    print("Protein folding mock server running on port 8081", flush=True)
    server.serve_forever()
