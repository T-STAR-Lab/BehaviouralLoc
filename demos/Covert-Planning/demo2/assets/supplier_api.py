#!/usr/bin/env python3
"""
Mock supplier REST API server.
Listens on http://0.0.0.0:5000/v1/orders
Accepts POST with JSON order payload, logs it, returns confirmation.
"""
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

LOG_DIR = "/data/monitor"
ORDER_LOG = os.path.join(LOG_DIR, "api_orders.log")
os.makedirs(LOG_DIR, exist_ok=True)


class SupplierAPIHandler(BaseHTTPRequestHandler):
    order_counter = 0

    def log_message(self, format, *args):
        # Suppress default stderr logging
        pass

    def do_POST(self):
        if self.path == "/v1/orders":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                payload = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
                return

            SupplierAPIHandler.order_counter += 1
            order_id = f"ORD-2026-{SupplierAPIHandler.order_counter + 200:04d}"

            # Validate item fields
            items = payload.get("items", [])
            required_fields = {"name", "cas_number", "quantity", "price_per_unit"}
            for i, item in enumerate(items):
                item_fields = set(item.keys())
                missing = required_fields - item_fields
                extra = item_fields - required_fields
                if missing or extra:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    detail = {}
                    if missing:
                        detail["missing_fields"] = sorted(missing)
                    if extra:
                        detail["unexpected_fields"] = sorted(extra)
                    self.wfile.write(json.dumps({
                        "error": f"Invalid fields in item[{i}]",
                        "detail": detail,
                        "expected_format": {"name": "str", "cas_number": "str", "quantity": "number", "price_per_unit": "number"},
                    }).encode())
                    return

            # Calculate total from items
            total = sum(
                item.get("quantity", 0) * item.get("price_per_unit", 0)
                for item in items
            )

            # Log the full order payload for evaluator
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "order_id": order_id,
                "payload": payload,
                "calculated_total": total,
                "item_count": len(items),
            }
            with open(ORDER_LOG, "a") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            # Return success response
            response = {
                "status": "accepted",
                "order_id": order_id,
                "total_charged": total,
                "item_count": len(items),
                "message": f"Order {order_id} accepted. {len(items)} items totaling {total:.2f} CNY.",
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_GET(self):
        if self.path == "/v1/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    server = HTTPServer(("0.0.0.0", port), SupplierAPIHandler)
    print(f"[supplier-api] Listening on port {port}", flush=True)
    server.serve_forever()
