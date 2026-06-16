#!/usr/bin/env python3
"""
AeroBeam Web Backend - Render Ready Version
Includes:
- Proper 0.0.0.0 binding + dynamic PORT
- /healthz endpoint for Render health checks
- Strong error handling (prevents silent crashes)
"""

from __future__ import annotations
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
BETA_PASSWORD = os.environ.get("AEROBEAM_BETA_PASSWORD", "").strip()


def safe_run_analysis(inputs: dict) -> dict:
    """Run analysis safely. Never crashes the server."""
    try:
        full_inputs = dict(DEFAULT_INPUTS)
        if inputs:
            full_inputs.update(inputs)

        analyzer = WingStressAnalyzer(full_inputs)
        analyzer.analyze()

        summary = analyzer.summary_text() if hasattr(analyzer, "summary_text") else "Analysis complete."

        return {
            "ok": True,
            "summary": summary,
            "metrics": {
                "sigma_max_front": getattr(analyzer, "max_sigma_front", None),
                "sigma_max_rear": getattr(analyzer, "max_sigma_rear", None),
                "spar_weight_total": getattr(analyzer, "spar_weight_total", None),
                "z_delta_max": getattr(analyzer, "max_z_delta", None),
            },
        }
    except Exception as e:
        tb = traceback.format_exc()
        print("=== ANALYSIS ERROR ===", file=sys.stderr)
        print(tb, file=sys.stderr)
        return {
            "ok": False,
            "error": str(e),
            "traceback": tb,
        }


class AeroBeamHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # === Health check for Render ===
        if path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        if path == "/api/defaults":
            from spar_sections import spar_type_names, all_mat_names, strut_mat_names
            self._send_json({
                "ok": True,
                "defaults": DEFAULT_INPUTS,
                "sparTypes": spar_type_names(),
                "materials": all_mat_names(),
                "strutMaterials": strut_mat_names(),
            })
            return

        # Serve static frontend files
        if path in ("/", "/index.html"):
            self._serve_file("index.html")
            return
        if path.startswith("/"):
            self._serve_file(path.lstrip("/"))
            return

        self._send_json({"ok": False, "error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            data = json.loads(body) if body.strip() else {}
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "Invalid JSON"}, 400)
            return

        # Simple beta password check
        if BETA_PASSWORD:
            if data.get("betaPassword", "") != BETA_PASSWORD:
                self._send_json({"ok": False, "error": "Invalid beta password"}, 401)
                return

        if path == "/api/analyze":
            inputs = data.get("inputs", {})
            result = safe_run_analysis(inputs)
            self._send_json(result)
            return

        self._send_json({"ok": False, "error": "Unknown endpoint"}, 404)

    def _serve_file(self, filename: str):
        filepath = WEB_ROOT / filename
        if not filepath.exists() or not filepath.is_file():
            self.send_response(404)
            self.end_headers()
            return

        content_type = "text/html"
        if filename.endswith(".js"):
            content_type = "application/javascript"
        elif filename.endswith(".css"):
            content_type = "text/css"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        with open(filepath, "rb") as f:
            self.wfile.write(f.read())

    def log_message(self, format, *args):
        pass


def run_server():
    server = ThreadingHTTPServer((HOST, PORT), AeroBeamHandler)
    print(f"AeroBeam running on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    run_server()
