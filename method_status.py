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
        "status": "PRELIMINARY",
        "label": "Jury strut column brace",
        "note": "Bruhn: a jury strut braces the lift strut. Pin-ended Euler length is the longer segment. Brace demand is 2.5% of lift-strut compression. It does not relieve spar bending.",
    },
    "pdelta": {
        "status": "PRELIMINARY",
        "label": "P-delta amplification",
        "note": "Timoshenko beam-column factor 1/(1-P/Pe) applied only between the root and the lift strut, where the spar carries the strut compression.",
    },
    "torsion": {
        "status": "EXPERIMENTAL",
        "label": "D-cell/geodetic/rib/skin torsion sharing",
        "note": "Nose area and skin length come from the thickness curve. Bredt-Batho is the torsion cell. Torque about the shear center is the signed pitching moment plus lift times the aerodynamic-center offset. Cantilever and single-strut ribs are stiff in their plane, so bending is shared by EI and the rib torque includes the spar-to-spar couple. Reported spar positions add that twist: nose-up lowers a point aft of the shear center. A plywood or formed-aluminum rib is a shear panel. A Dow-foam rib with spruce caps is a sandwich beam and is soft in core shear. Dual-strut bending stays on the entered load share. Strip force is demand only.",
    },
    "buckling": {
        "status": "PRELIMINARY",
        "label": "Web, skin, cap, and tube buckling warnings",
        "note": "Metal plates use Timoshenko. Wood and plywood use an orthotropic long-plate formula. Boundary conditions remain simply supported screening checks.",
    },
    "fittings": {
        "status": "DISPLAY",
        "label": "Local fitting and bearing load demands",
        "note": "Reports loads to be reacted at fittings only; bearing, lugs, bushings, bolts, doublers, and local crush sizing are outside AeroBeam.",
    },
    "divergence": {
        "status": "EXPERIMENTAL",
        "label": "Divergence speed screening",
        "note": "Uniform-wing torsional divergence, q = (pi/(2L))^2 * GJ / (e c^2 Cl_alpha). Shear center is the thin-wall shear flow of the closed contour, or the spar axis if the wing is an open tube. Screening only, not flutter.",
    },
}


def method_status_lines() -> list[str]:
    """Return compact lines for reports and UI diagnostics."""

    lines = ["METHOD STATUS: BETA / PRELIMINARY"]
    for key in ("loads", "sections", "strut", "jury", "pdelta", "torsion", "buckling", "fittings", "divergence"):
        item = METHOD_STATUS[key]
        lines.append(f"  {item['status']}: {item['label']}")
    return lines
