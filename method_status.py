"""Method status registry for AeroBeam outputs.

These tags are deliberately conservative. A method can only move from
EXPERIMENTAL/PRELIMINARY to STANDARD after benchmark coverage is added and the
methods audit is updated.
"""

from __future__ import annotations

METHOD_STATUS = {
    "loads": {
        "status": "PRELIMINARY",
        "label": "Lift, shear, and moment integration",
        "note": "Standard beam equilibrium with preliminary lift distributions; benchmark required for each load distribution.",
    },
    "sections": {
        "status": "PRELIMINARY",
        "label": "Cross-section EI, neutral axis, and basic bending stress",
        "note": "Parallel-axis/transformed-section approach; section benchmark suite required.",
    },
    "strut": {
        "status": "PRELIMINARY",
        "label": "Main strut statics and Euler buckling",
        "note": "Assumes ideal pin-ended column and equivalent vertical reaction.",
    },
    "jury": {
        "status": "EXPERIMENTAL",
        "label": "Load-bearing jury strut support",
        "note": "Compatibility approximation; validate against independent indeterminate beam/frame model.",
    },
    "pdelta": {
        "status": "PRELIMINARY",
        "label": "P-delta amplification",
        "note": "Scalar beam-column amplification; benchmark for strut-braced wing segment required.",
    },
    "torsion": {
        "status": "EXPERIMENTAL",
        "label": "D-cell/geodetic/rib/skin torsion sharing",
        "note": "Bredt-Batho portions are standard; geodetic/rear-spar coupling is unvalidated. Rib outputs are required reactions only, not rib sizing.",
    },
    "buckling": {
        "status": "PRELIMINARY",
        "label": "Web, skin, cap, and tube buckling warnings",
        "note": "Plate/column screening checks; boundary-condition benchmarks required.",
    },
    "divergence": {
        "status": "EXPERIMENTAL",
        "label": "Divergence speed screening",
        "note": "Simplified closed-form estimate with approximate shear center; not flutter analysis.",
    },
}


def method_status_lines() -> list[str]:
    """Return compact lines for reports and UI diagnostics."""

    lines = ["METHOD STATUS: BETA / PRELIMINARY"]
    for key in ("loads", "sections", "strut", "jury", "pdelta", "torsion", "buckling", "divergence"):
        item = METHOD_STATUS[key]
        lines.append(f"  {item['status']}: {item['label']}")
    return lines
