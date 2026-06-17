#!/usr/bin/env python3
"""
AeroBeam Web Backend - Render Ready (Complete)
Fixes: binding, health check, and missing plot data for frontend
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

# Cache for /api/defaults response
_defaults_cache = None


def _build_defaults_response():
    """Build the defaults API response once and cache it."""
    from spar_sections import (
        spar_type_names, all_mat_names, strut_mat_names,
        ALUMINUM_ANGLES, ANGLE_DESCRIPTIONS
    )
    from common_tube_spars import COMMON_TUBE_SIZES
    from airfoil_database import airfoil_names, AIRFOIL_DB
    from method_status import METHOD_STATUS
    
    # Build angle data
    angle_data = {
        angle.description: {
            "L1": angle.L1,
            "L2": angle.L2,
            "t": angle.t,
            "area": angle.area,
            "b_equiv": angle.b_equiv,
            "t_equiv": angle.t_equiv,
        }
        for angle in ALUMINUM_ANGLES
    }
    
    # Build tube spar data
    tube_spars = [str(tube) for tube in COMMON_TUBE_SIZES]
    
    # Build airfoil data
    airfoil_data = {
        name: {
            "family": data.get("family", ""),
            "t_c": data.get("t_c", 0),
            "Cm_ac": data.get("Cm_ac", 0),
        }
        for name, data in AIRFOIL_DB.items()
    }
    
    return {
        "ok": True,
        "defaults": DEFAULT_INPUTS,
        "sparTypes": spar_type_names(),
        "materials": all_mat_names(),
        "strutMaterials": strut_mat_names(),
        "angles": ANGLE_DESCRIPTIONS,
        "angleData": angle_data,
        "tubeSpars": tube_spars,
        "airfoils": airfoil_names(),
        "airfoilData": airfoil_data,
        "methodStatus": METHOD_STATUS,
    }


def _get_defaults_response():
    """Get cached defaults response, building it if necessary."""
    global _defaults_cache
    if _defaults_cache is None:
        _defaults_cache = _build_defaults_response()
    return _defaults_cache


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


def _series(analyzer):
    x = analyzer.x
    pos = analyzer.pos
    neg = analyzer.neg
    torsion = analyzer.torsion or {}
    return _jsonable({
        "x": x,
        "chord": analyzer.chord_x,
        "positive": {
            "w": pos.get("w", []),
            "V": pos.get("V", []),
            "M": pos.get("M", []),
            "M_front": pos.get("M_front", []),
            "M_rear": pos.get("M_rear", []),
            "z_front": pos.get("z_front", []),
            "z_rear": pos.get("z_rear", []),
            "z_delta": pos.get("z_delta", []),
            "sigma_front": pos.get("sigma_front", []),
            "sigma_rear": pos.get("sigma_rear", []),
        },
        "negative": {
            "w": neg.get("w", []),
            "V": neg.get("V", []),
            "M": neg.get("M", []),
            "M_front": neg.get("M_front", []),
            "M_rear": neg.get("M_rear", []),
            "z_front": neg.get("z_front", []),
            "z_rear": neg.get("z_rear", []),
            "z_delta": neg.get("z_delta", []),
            "sigma_front": neg.get("sigma_front", []),
            "sigma_rear": neg.get("sigma_rear", []),
        },
        "torsion": {
            "T_total": torsion.get("T_total", []),
            "T_running": torsion.get("T_running", []),
            "phi_deg": np.degrees(torsion.get("phi", [])) if torsion.get("phi") is not None else [],
        },
        "geometry": {
            "b_half": getattr(analyzer, "b_half", 0),
            "root_bl": getattr(analyzer, "r", 0),
            "x": x,
            "chord": analyzer.chord_x,
            "front_spar": getattr(analyzer, "front_pct", 0) * analyzer.chord_x,
            "rear_spar": getattr(analyzer, "rear_pct", 0) * analyzer.chord_x,
            "front_spar_percent": getattr(analyzer, "front_pct", 0),
            "rear_spar_percent": getattr(analyzer, "rear_pct", 0),
        }
    })


def safe_run_analysis(inputs: dict) -> dict:
    try:
        print(f"=== STARTING ANALYSIS ===", file=sys.stderr)
        print(f"Input keys: {list(inputs.keys()) if inputs else 'None'}", file=sys.stderr)
        
        full_inputs = dict(DEFAULT_INPUTS)
        if inputs:
            full_inputs.update(inputs)
        
        # Log critical configuration
        print(f"Spar type: {full_inputs.get('front_spar_type', 'unknown')}", file=sys.stderr)
        print(f"Material: {full_inputs.get('front_spar_mat', 'unknown')}", file=sys.stderr)
        print(f"Jury strut: {full_inputs.get('jury_strut', False)}", file=sys.stderr)
        
        print("Creating analyzer...", file=sys.stderr)
        analyzer = WingStressAnalyzer(full_inputs)
        
        print("Running analysis...", file=sys.stderr)
        analyzer.analyze()
        
        print("Analysis complete, generating summary...", file=sys.stderr)
        summary = analyzer.summary_text() if hasattr(analyzer, "summary_text") else "Analysis complete."

        print("Building response...", file=sys.stderr)
        result = {
            "ok": True,
            "summary": summary,
            "metrics": {
                "sigma_max_front": getattr(analyzer, "max_sigma_front", None),
                "sigma_max_rear": getattr(analyzer, "max_sigma_rear", None),
                "spar_weight_total": getattr(analyzer, "spar_weight_total", None),
                "z_delta_max": getattr(analyzer, "max_z_delta", None),
            },
            "series": _series(analyzer),
        }
        print("=== ANALYSIS SUCCESS ===", file=sys.stderr)
        return result
        
    except Exception as e:
        tb = traceback.format_exc()
        print("=== ANALYSIS ERROR ===", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        print(f"Error message: {str(e)}", file=sys.stderr)
        print("Full traceback:", file=sys.stderr)
        print(tb, file=sys.stderr)
        print("=== END ERROR ===", file=sys.stderr)
        return {
            "ok": False,
            "error": str(e),
            "error_type": type(e).__name__,
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

    def _handle_healthz(self):
        """Handle /healthz endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def _handle_defaults(self):
        """Handle /api/defaults endpoint."""
        self._send_json(_get_defaults_response())

    def _handle_index(self):
        """Handle index page."""
        self._serve_file("index.html")

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path

            # Route dispatch table
            routes = {
                "/healthz": self._handle_healthz,
                "/api/defaults": self._handle_defaults,
                "/": self._handle_index,
                "/index.html": self._handle_index,
            }

            # Try exact match first
            handler = routes.get(path)
            if handler:
                handler()
                return

            # Fall back to static file serving
            if path.startswith("/"):
                self._serve_file(path.lstrip("/"))
                return

            # 404 for anything else
            self._send_json({"ok": False, "error": "Not found"}, 404)
            
        except Exception as e:
            print(f"=== UNHANDLED EXCEPTION IN do_GET ===", file=sys.stderr)
            print(f"Path: {self.path}", file=sys.stderr)
            print(f"Error: {e}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            print(f"=== END UNHANDLED EXCEPTION ===", file=sys.stderr)
            try:
                self.send_response(500)
                self.end_headers()
            except:
                pass  # Connection might be broken

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

            try:
                data = json.loads(body) if body.strip() else {}
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}", file=sys.stderr)
                self._send_json({"ok": False, "error": "Invalid JSON"}, 400)
                return

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
            
        except Exception as e:
            print(f"=== UNHANDLED EXCEPTION IN do_POST ===", file=sys.stderr)
            print(f"Error: {e}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            print(f"=== END UNHANDLED EXCEPTION ===", file=sys.stderr)
            try:
                self._send_json({"ok": False, "error": f"Server error: {str(e)}"}, 500)
            except:
                pass  # Connection might be broken

    def _serve_file(self, filename: str):
        """Serve a static file from the web directory."""
        filepath = WEB_ROOT / filename
        if not filepath.exists() or not filepath.is_file():
            self.send_response(404)
            self.end_headers()
            return

        # MIME type mapping
        mime_types = {
            ".html": "text/html",
            ".js": "application/javascript",
            ".css": "text/css",
            ".ico": "image/x-icon",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".json": "application/json",
            ".txt": "text/plain",
        }

        suffix = filepath.suffix.lower()
        content_type = mime_types.get(suffix, "application/octet-stream")

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        with open(filepath, "rb") as f:
            self.wfile.write(f.read())

    def log_message(self, format, *args):
        """Log HTTP requests to stderr."""
        sys.stderr.write("%s - - [%s] %s\n" %
                        (self.address_string(),
                         self.log_date_time_string(),
                         format % args))
    
    def log_error(self, format, *args):
        """Log errors to stderr."""
        sys.stderr.write("ERROR: %s - - [%s] %s\n" %
                        (self.address_string(),
                         self.log_date_time_string(),
                         format % args))


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
