#!/usr/bin/env python3
"""
AeroBeam Web Backend - Robust Version with Strong Error Handling
Run with: python3 web_app_robust.py
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
from spar_sections import (
    MATERIAL_DB, STRUT_MATERIALS, ALUMINUM_ANGLES, ANGLE_DESCRIPTIONS,
    spar_type_names, aluminum_mat_names, wood_mat_names, all_mat_names, strut_mat_names,
)
from airfoil_database import AIRFOIL_DB

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
BETA_PASSWORD = os.environ.get("AEROBEAM_BETA_PASSWORD", "").strip()


def _jsonable(value):
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def safe_run_analysis(inputs: dict) -> dict:
    """Run analysis with full error protection. Never crashes the server."""
    try:
        # Merge with defaults for safety
        full_inputs = dict(DEFAULT_INPUTS)
        if inputs:
            full_inputs.update(inputs)

        analyzer = WingStressAnalyzer(full_inputs)
        analyzer.analyze()

        # Build response
        summary = analyzer.summary_text() if hasattr(analyzer, "summary_text") else "Analysis complete."

        result = {
            "ok": True,
            "summary": summary,
            "metrics": {
                "sigma_max_front": getattr(analyzer, "max_sigma_front", None),
                "sigma_max_rear": getattr(analyzer, "max_sigma_rear", None),
                "spar_weight_total": getattr(analyzer, "spar_weight_total", None),
                "z_delta_max": getattr(analyzer, "max_z_delta", None),
            },
        }
        return result

    except Exception as e:
        tb = traceback.format_exc()
        print("=== ANALYSIS CRASH ===", file=sys.stderr)
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/defaults":
            self._send_json({
                "ok": True,
                "defaults": DEFAULT_INPUTS,
                "sparTypes": spar_type_names(),
                "materials": all_mat_names(),
                "strutMaterials": strut_mat_names(),
            })
            return

        # Serve static files from web/ folder
        if path == "/" or path == "/index.html":
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

        # Beta password check (simple)
        if BETA_PASSWORD:
            provided = data.get("betaPassword", "")
            if provided != BETA_PASSWORD:
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
        elif filename.endswith(".json"):
            content_type = "application/json"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        with open(filepath, "rb") as f:
            self.wfile.write(f.read())

    def log_message(self, format, *args):
        # Reduce noise
        pass


def run_server():
    server = ThreadingHTTPServer((HOST, PORT), AeroBeamHandler)
    print(f"AeroBeam Web Server running on http://{HOST}:{PORT}")
    print(f"Beta password required: {'YES' if BETA_PASSWORD else 'NO'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    run_server()
