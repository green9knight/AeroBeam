"""AeroBeam browser front end.

Run with:
    python3 web_app.py

The server intentionally uses only the Python standard library so the web UI can
ship beside the desktop app without adding Flask/FastAPI packaging overhead.
"""

from __future__ import annotations

import json
import mimetypes
import os
import tempfile
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Web/PDF rendering must be headless on Render and thread-safe in the HTTP server.
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

from airfoil_database import AIRFOIL_DB
from method_status import METHOD_STATUS
from spar_sections import (
    MATERIAL_DB,
    ANGLE_DESCRIPTIONS,
    STRUT_MATERIALS,
    all_mat_names,
    spar_type_names,
    strut_mat_names,
)
from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
BETA_PASSWORD = os.environ.get("AEROBEAM_BETA_PASSWORD", "").strip()


def _jsonable(value: Any) -> Any:
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


def _series(analyzer: WingStressAnalyzer) -> dict[str, Any]:
    x = analyzer.x
    pos = analyzer.pos
    neg = analyzer.neg
    return _jsonable(
        {
            "x": x,
            "chord": analyzer.chord_x,
            "positive": {
                "w": pos["w"],
                "V": pos["V"],
                "M": pos["M"],
                "M_front": pos["M_front"],
                "M_rear": pos["M_rear"],
                "z_front": pos["z_front"],
                "z_rear": pos["z_rear"],
                "z_delta": pos["z_delta"],
                "sigma_front": pos["sigma_front"],
                "sigma_rear": pos["sigma_rear"],
            },
            "negative": {
                "w": neg["w"],
                "V": neg["V"],
                "M": neg["M"],
                "M_front": neg["M_front"],
                "M_rear": neg["M_rear"],
                "z_front": neg["z_front"],
                "z_rear": neg["z_rear"],
                "z_delta": neg["z_delta"],
                "sigma_front": neg["sigma_front"],
                "sigma_rear": neg["sigma_rear"],
            },
            "torsion": {
                "T_total": analyzer.torsion["T_total"] if analyzer.torsion else [],
                "T_running": analyzer.torsion["T_running"] if analyzer.torsion else [],
                "phi_deg": np.degrees(analyzer.torsion["phi"]) if analyzer.torsion else [],
            },
            "geometry": {
                "b_half": analyzer.b_half,
                "root_bl": analyzer.r,
                "x": x,
                "chord": analyzer.chord_x,
                "front_spar": analyzer.front_pct * analyzer.chord_x,
                "rear_spar": analyzer.rear_pct * analyzer.chord_x,
                "front_spar_percent": analyzer.front_pct,
                "rear_spar_percent": analyzer.rear_pct,
                "strut_bl": analyzer.strut_bl,
                "strut_fuse_bl": analyzer.strut_fuse_bl,
                "strut_vert": analyzer.strut_vert,
                "jury_enabled": analyzer.jury,
                "jury_bl": analyzer.jury_bl,
                "config": analyzer.config,
                "dcell_enabled": analyzer.dcell_enabled,
                "taper_start_bl": analyzer.taper_start_bl,
            },
        }
    )


def analyze_payload(payload: dict[str, Any]) -> dict[str, Any]:
    inputs = dict(DEFAULT_INPUTS)
    inputs.update(payload.get("inputs", payload))

    analyzer = WingStressAnalyzer(inputs)
    analyzer.analyze()

    return {
        "ok": True,
        "summary": analyzer.summary_text(),
        "metrics": _jsonable(
            {
                "sigma_max_front": analyzer.sigma_max_front,
                "sigma_max_rear": analyzer.sigma_max_rear,
                "ms_front": analyzer.ms_front,
                "ms_rear": analyzer.ms_rear,
                "spar_weight_total": getattr(analyzer, "spar_weight_total", 0.0),
                "z_max_front": analyzer.pos["z_max_front"],
                "z_max_rear": analyzer.pos["z_max_rear"],
                "z_delta_max": analyzer.pos["z_delta_max"],
                "coupling_kappa": getattr(analyzer, "_geodetic_kappa", 0.0),
                "torsion": {
                    "phi_root_deg": analyzer.torsion["phi_root_deg"] if analyzer.torsion else 0.0,
                    "f_rib": analyzer.torsion.get("f_rib", 0.0) if analyzer.torsion else 0.0,
                    "f_geo": analyzer.torsion.get("f_geo", 0.0) if analyzer.torsion else 0.0,
                    "f_skin": analyzer.torsion.get("f_skin", 0.0) if analyzer.torsion else 0.0,
                },
            }
        ),
        "series": _series(analyzer),
    }


def report_payload(payload: dict[str, Any]) -> bytes:
    inputs = dict(DEFAULT_INPUTS)
    inputs.update(payload.get("inputs", payload))

    analyzer = WingStressAnalyzer(inputs)
    analyzer.analyze()

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "aerobeam-report.pdf"
        analyzer.export_pdf(path)
        return path.read_bytes()


class AeroBeamHandler(BaseHTTPRequestHandler):
    server_version = "AeroBeamWeb/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._send_json({"ok": True, "service": "aerobeam-web"})
            return
        if parsed.path == "/api/defaults":
            self._send_json(
                {
                    "defaults": DEFAULT_INPUTS,
                    "sparTypes": spar_type_names(),
                    "materials": all_mat_names(),
                    "strutMaterials": strut_mat_names(),
                    "angles": ANGLE_DESCRIPTIONS,
                    "airfoils": sorted(AIRFOIL_DB.keys()),
                    "materialData": MATERIAL_DB,
                    "strutMaterialData": STRUT_MATERIALS,
                    "methodStatus": METHOD_STATUS,
                }
            )
            return

        path = parsed.path if parsed.path != "/" else "/index.html"
        self._send_static(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/analyze", "/api/report"}:
            self._send_json({"ok": False, "error": "unknown endpoint"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not self._authorized(payload):
                return
            if parsed.path == "/api/report":
                self._send_pdf(report_payload(payload), "aerobeam-report.pdf")
            else:
                self._send_json(analyze_payload(payload))
        except Exception as exc:  # pragma: no cover - returned to browser
            self._send_json(
                {
                    "ok": False,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
                status=400,
            )

    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), fmt % args))

    def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        body = json.dumps(_jsonable(payload), indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_pdf(self, body: bytes, filename: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self, payload: dict[str, Any] | None = None) -> bool:
        if not BETA_PASSWORD:
            return True
        payload = payload or {}
        supplied = (
            self.headers.get("X-AeroBeam-Password")
            or payload.get("betaPassword")
            or payload.get("password")
            or ""
        ).strip()
        if supplied == BETA_PASSWORD:
            return True
        self._send_json({"ok": False, "error": "invalid or missing beta password"}, status=401)
        return False

    def _send_static(self, request_path: str) -> None:
        rel = request_path.lstrip("/")
        target = (WEB_ROOT / rel).resolve()
        if WEB_ROOT not in target.parents and target != WEB_ROOT:
            self._send_json({"ok": False, "error": "invalid path"}, status=403)
            return
        if not target.is_file():
            self._send_json({"ok": False, "error": "not found"}, status=404)
            return

        body = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), AeroBeamHandler)
    print(f"AeroBeam web UI running at http://{HOST}:{PORT}")
    if BETA_PASSWORD:
        print("Beta password protection enabled.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping AeroBeam web UI.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
