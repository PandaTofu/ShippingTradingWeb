"""Bond website and enquiry API using only the Python standard library."""

from __future__ import annotations

import csv
import json
import mimetypes
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = PROJECT_ROOT / "dist"
DATA_ROOT = Path(os.environ.get("BOND_INQUIRY_DIR", PROJECT_ROOT / "data")).resolve()
CSV_PATH = DATA_ROOT / "inquiries.csv"
HOST = os.environ.get("BOND_INQUIRY_HOST", "127.0.0.1")
PORT = int(os.environ.get("BOND_INQUIRY_PORT", "8011"))
MAX_BODY_BYTES = 32 * 1024
RATE_WINDOW_SECONDS = 10 * 60
RATE_LIMIT = 5
ALLOWED_FUELS = {"VLSFO", "ULSFO", "MGO / MDO", "HSFO", "Biofuel blend", "Other"}
FIELDS = (
    "reference",
    "submitted_at_utc",
    "source_ip",
    "vessel_name",
    "bunker_port",
    "fuel_type",
    "quantity_mt",
    "required_date",
    "company",
    "contact",
    "remarks",
)

csv_lock = threading.Lock()
rate_lock = threading.Lock()
request_times: dict[str, deque[float]] = defaultdict(deque)


def clean_text(value: object, field: str, max_length: int, required: bool = True) -> str:
    text = " ".join(str(value or "").strip().split())
    if required and not text:
        raise ValueError(f"{field} is required.")
    if len(text) > max_length:
        raise ValueError(f"{field} is too long.")
    if text.startswith(("=", "+", "-", "@")):
        text = "'" + text
    return text


def validate_payload(payload: dict[str, object]) -> dict[str, str]:
    if clean_text(payload.get("website"), "Website", 200, required=False):
        raise ValueError("Invalid submission.")

    fuel_type = clean_text(payload.get("fuelType"), "Fuel type", 40)
    if fuel_type not in ALLOWED_FUELS:
        raise ValueError("Please select a valid fuel type.")

    quantity_raw = clean_text(payload.get("quantity"), "Quantity", 20)
    try:
        quantity = float(quantity_raw)
    except ValueError as exc:
        raise ValueError("Quantity must be a number.") from exc
    if quantity <= 0 or quantity > 1_000_000:
        raise ValueError("Quantity is outside the accepted range.")

    required_date = clean_text(payload.get("requiredDate"), "Required date", 10)
    try:
        date.fromisoformat(required_date)
    except ValueError as exc:
        raise ValueError("Required date is invalid.") from exc

    return {
        "vessel_name": clean_text(payload.get("vesselName"), "Vessel name", 160),
        "bunker_port": clean_text(payload.get("bunkerPort"), "Bunker port", 160),
        "fuel_type": fuel_type,
        "quantity_mt": f"{quantity:g}",
        "required_date": required_date,
        "company": clean_text(payload.get("company"), "Company", 200),
        "contact": clean_text(payload.get("contact"), "Contact", 240),
        "remarks": clean_text(payload.get("remarks"), "Remarks", 2000, required=False),
    }


def save_inquiry(values: dict[str, str], source_ip: str) -> str:
    reference = "BOND-" + datetime.now(timezone.utc).strftime("%Y%m%d-") + uuid.uuid4().hex[:8].upper()
    row = {
        "reference": reference,
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_ip": source_ip,
        **values,
    }
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    with csv_lock:
        is_new = not CSV_PATH.exists()
        with CSV_PATH.open("a", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            if is_new:
                writer.writeheader()
            writer.writerow(row)
    return reference


class BondRequestHandler(SimpleHTTPRequestHandler):
    server_version = "BondEnquiry/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_ROOT), **kwargs)

    def _json_response(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _source_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        return forwarded or self.client_address[0]

    def _within_rate_limit(self, source_ip: str) -> bool:
        now = time.monotonic()
        with rate_lock:
            events = request_times[source_ip]
            while events and now - events[0] > RATE_WINDOW_SECONDS:
                events.popleft()
            if len(events) >= RATE_LIMIT:
                return False
            events.append(now)
            return True

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._json_response(HTTPStatus.OK, {"status": "ok"})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/inquiries":
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return

        source_ip = self._source_ip()
        if not self._within_rate_limit(source_ip):
            self._json_response(HTTPStatus.TOO_MANY_REQUESTS, {"error": "Too many requests. Please try again later."})
            return

        if self.headers.get_content_type() != "application/json":
            self._json_response(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "JSON is required."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            self._json_response(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "Invalid request size."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
            if not isinstance(payload, dict):
                raise ValueError("Invalid request.")
            values = validate_payload(payload)
            reference = save_inquiry(values, source_ip)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON."})
            return
        except ValueError as error:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except OSError:
            self._json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "The enquiry could not be recorded."})
            return

        self._json_response(HTTPStatus.CREATED, {"ok": True, "reference": reference})


if __name__ == "__main__":
    mimetypes.add_type("application/wasm", ".wasm")
    server = ThreadingHTTPServer((HOST, PORT), BondRequestHandler)
    print(f"Bond website available at http://{HOST}:{PORT}")
    print(f"Enquiries will be saved to {CSV_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
