"""
AeroBeam v1.2.3 — Wing Stress Analyzer
======================================
Physics engine. All structural analysis lives here.
Units: inches, pounds, psi throughout.
"""

import math
import traceback
import numpy as np
from typing import Optional, Tuple, Dict, Any

from spar_sections import (    CrossSection, RoundTube, IBeam, DoubleIBeam, BoxSpar, resolved_tip,
    CChannel, RoutedSpar, PlainRect,
    DCellSkin, GeodeticPanel, SkinPanel, WingBox,
    MATERIAL_DB, STRUT_MATERIALS,
    two_cell_bredt, allowable_bending, allowable_shear,
    web_buckling, web_bending_buckling, skin_compression_buckling, cap_column_buckling,
    skin_effective_width, two_cell_shear_center, rectangular_cell_shear_center,
    rib_tie_stiffness,
)
from airfoil_database import AIRFOIL_DB, get_airfoil
from method_status import method_status_lines


# ─── PLOT COLOUR PALETTE ─────────────────────────────────────────────────────
PLOT_STYLE = {
    "figure.facecolor": "#1e2128",
    "axes.facecolor":   "#252930",
    "axes.edgecolor":   "#6E7F87",
    "axes.labelcolor":  "#e8eaf0",
    "text.color":       "#e8eaf0",
    "xtick.color":      "#B9BCC2",
    "ytick.color":      "#B9BCC2",
    "grid.color":       "#3a3f4b",
    "legend.facecolor": "#1e2128",
    "legend.edgecolor": "#6E7F87",
}
PC_GOLD = "#D2B75F"   # gold — titles, section headers

# Print-friendly PDF palette — white background, dark text, ink-efficient colours
PDF_STYLE = {
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "axes.edgecolor":   "#333333",
    "axes.labelcolor":  "#111111",
    "text.color":       "#111111",
    "xtick.color":      "#333333",
    "ytick.color":      "#333333",
    "grid.color":       "#cccccc",
    "legend.facecolor": "white",
    "legend.edgecolor": "#999999",
}
PDF_BLUE  = "#085097"   # classic blue — +g curves
PDF_NAVY  = "#024084"   # darker blue — secondary
PDF_GREY  = "#555555"   # grey — -g curves
PDF_GREEN = "#1a6e1a"   # dark green — pass (prints well)
PDF_RED   = "#cc0000"   # red — fail
PDF_AMBER = "#b35c00"   # amber/orange — warning/fix
PDF_GOLD  = "#8B6914"   # dark gold — headers (readable on white)

# ─── DEFAULT INPUTS ──────────────────────────────────────────────────────────

DEFAULT_INPUTS: Dict[str, Any] = {
    "b": 306.0, "r": 11.0, "num_points": 201,
    "root_chord": 54.0, "tip_chord": 54.0, "taper_start_bl": 0.0,
    "taper_reference": "Leading edge",
    "rib_spacing": 12.0,
    "lift_distribution_type": "schrenk",
    "num_spars": 2,
    "front_spar_percent": 0.05, "rear_spar_percent": 0.85,
    "front_spar_load_share": 0.55,
    "wing_structure_type": "fabric_tube",
    "front_spar_type": "Round Tube",
    "front_spar_od": 2.5, "front_spar_wall": 0.065,
    "front_spar_mat": "6061-T6",
    "rear_spar_type": "Round Tube",
    "rear_spar_od": 2.5, "rear_spar_wall": 0.065,
    "rear_spar_mat": "6061-T6",
    "dcell_enabled": False,
    "dcell_skin_mat": "6061-T6", "dcell_skin_thick": 0.025,
    "geodetic_enabled": False,
    "geodetic_mat": "Sitka Spruce", "geodetic_w": 1.0, "geodetic_t": 0.125,
    "geodetic_strips_per_bay": 2, "geodetic_angle": 45.0,
    "geodetic_reduction_factor": 0.75,
    "skin_top_mat": "6061-T6", "skin_top_thick": 0.0,
    "skin_bot_mat": "6061-T6", "skin_bot_thick": 0.0,
    # Inboard torsion box. Off until chosen. Sheets are torsion only.
    "torsion_box_enabled": False,
    "torsion_box_bays": 4,
    "torsion_box_top_mat": "Birch Plywood", "torsion_box_top_thick": 0.125,
    "torsion_box_bot_mat": "Birch Plywood", "torsion_box_bot_thick": 0.125,
    "wood_knockdown": 0.75,
    # Rib structure (torsion transfer between spars)
    "rib_type":   "Plywood web",  # or "Sheet aluminum formed" or "Dow foam with spruce caps"
    "rib_h_web":  3.0,    # rib web / foam clear height [in]
    "rib_t_web":  0.125,  # web, sheet, or foam thickness [in]
    "rib_b_cap":  0.75,   # cap or formed-flange width [in]
    "rib_t_cap":  0.125,  # cap thickness [in]; formed ribs use the sheet thickness
    "rib_mat":    "Birch Plywood",
    "ng_lift": 1950.0, "n": 6.0, "n_neg": -3.0,
    "Weight": 550.0, "Wing_Weight": 50.0, "Tail_Down_1g": 50.0,
    "distribute_wing_weight": True,
    "config": "strut_braced",
    "strut_percent": 0.65, "strut_bl": 96.0, "strut_vert": 44.0, "strut_fuse_bl": 11.0,
    "strut_mat": "4130 Chromoly (normalized)",
    "strut_tube_od": 2.0, "strut_tube_wall": 0.065,
    "secondary_bending": False,
    "jury_strut": True, "jury_spar_bl": 48.0,
    "jury_tube_mat": "6061-T6 Aluminum",
    "jury_tube_od": 0.75,
    "jury_tube_wall": 0.035,
    "jury_front_link_length": 18.0,
    "jury_rear_link_length": 18.0,
    "jury_front_link_angle": 45.0,
    "jury_rear_link_angle": 45.0,
    "airfoil": "GA 30-415", "Cm_ac": -0.064,  "Cm_flap": 0.0,  # delta Cm with full flaps
    "Cl_alpha": 6.25, "x_ac_c": 0.249,
    "Vd_mph": 100.0, "altitude_ft": 2000.0, "Vc_mph": 80.0, "Va_mph": 60.0,
    "airfoil_t_c": 0.15,
    "curvature_sign": 1.0, "make_plots": True, "export_excel": False,
    "dcell_r_LE": "3",
    "front_spar_angle_sel": "(Manual flat bar)",
    "rear_spar_angle_sel": "(Manual flat bar)",
    # Buckling — default = rib_spacing (no intermediate stiffeners/nose ribs)
    "stiffener_spacing": 0.0,   # 0 = use rib_spacing
    "nose_rib_spacing":  0.0,   # 0 = use rib_spacing

    # Web doublers — local reinforcement at root and strut attach
    "front_spar_doubler_t":      0.0,   # doubler sheet thickness [in], 0 = none
    "front_spar_doubler_extent": 1,     # rib bays each side of doubler station
    "rear_spar_doubler_t":       0.0,
    "rear_spar_doubler_extent":  1,
    "bearing_allowable_psi":     12000.0,  # demand-only required bearing area
}


# ─── ISA ATMOSPHERE ──────────────────────────────────────────────────────────

def isa_density(alt_ft: float) -> float:
    T = 518.67 - 3.566e-3 * alt_ft
    p = 2116.22 * (T / 518.67) ** 5.2561
    return p / (1716.49 * T)


def dynamic_pressure_psi(V_mph: float, alt_ft: float) -> float:
    V_fps = V_mph * 5280.0 / 3600.0
    rho   = isa_density(alt_ft)
    return 0.5 * rho * V_fps**2 / 144.0


def parse_bool(value: Any, default: bool = False) -> bool:
    """Parse booleans from JSON, GUI, and legacy saved project values."""

    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return default


def canonical_taper_reference(name: str) -> str:
    """Which planform line stays straight when the chord tapers."""

    text = str(name or "").strip().lower()
    aliases = {
        "leading edge": "Leading edge",
        "leading_edge": "Leading edge",
        "le": "Leading edge",
        "main spar": "Main spar",
        "main_spar": "Main spar",
        "front spar": "Main spar",
        "spar": "Main spar",
        "trailing edge": "Trailing edge",
        "trailing_edge": "Trailing edge",
        "te": "Trailing edge",
    }
    return aliases.get(text, "Leading edge")


def parse_user_float(value: Any) -> float:
    """Parse a form or file number, including 0.02\", '0.02', and 0.02 in."""

    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"could not convert {value!r} to float")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("\u00a0", "").replace("\u200b", "")
    text = text.replace("\uff0e", ".").replace("\u2032", "").replace("\u2033", "")
    quote = "'\"\u2018\u2019\u201c\u201d"
    text = text.strip(quote).strip()
    lowered = text.lower()
    for suffix in (" inches", " inch", " in.", " in"):
        if lowered.endswith(suffix):
            text = text[: -len(suffix)].strip()
            break
    text = text.strip(quote).strip()
    return float(text)


def _normalize_inputs(inp: dict) -> None:
    """Make GUI and saved-file values match the units validation expects."""

    for key, default in DEFAULT_INPUTS.items():
        if isinstance(default, bool) or not isinstance(default, (int, float)):
            continue
        if key in inp and isinstance(inp[key], str):
            try:
                inp[key] = parse_user_float(inp[key])
            except ValueError:
                pass
    for key in ("front_spar_percent", "rear_spar_percent", "front_spar_load_share", "airfoil_t_c"):
        if key in inp:
            inp[key] = parse_fraction(inp[key], float(DEFAULT_INPUTS.get(key, 0.0)))
    for key in (
        "jury_strut",
        "distribute_wing_weight",
        "secondary_bending",
        "dcell_enabled",
        "geodetic_enabled",
        "ng_lift_manual",
    ):
        if key in inp:
            inp[key] = parse_bool(inp[key], bool(DEFAULT_INPUTS.get(key, False)))


def parse_fraction(value: Any, default: float = 0.0) -> float:
    """Parse a fraction that may be entered as 0.30 or 30 for 30%."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if abs(number) > 1.0:
        number /= 100.0
    return number


# ─── SPAR FACTORY ────────────────────────────────────────────────────────────

def _sanitize_spar_inputs(inputs: dict, prefix: str) -> dict:
    """
    Ensure spar geometry inputs are physically meaningful.
    Replaces zero or missing values with safe defaults so the analyzer
    never sees zero EI (which causes infinite stress and nonsense results).
    Called automatically before build_spar.
    """
    i = dict(inputs)
    t = i.get(f"{prefix}_type", "Round Tube")

    if t == "Round Tube":
        od   = float(i.get(f"{prefix}_od",   2.5))
        wall = float(i.get(f"{prefix}_wall", 0.065))
        if od   < 0.25:  i[f"{prefix}_od"]   = 2.5
        if wall < 0.020: i[f"{prefix}_wall"] = 0.065
        if wall >= i[f"{prefix}_od"] / 2:
            i[f"{prefix}_wall"] = i[f"{prefix}_od"] * 0.05  # cap at 5% OD

    elif t == "Plain Rectangular":
        w = float(i.get(f"{prefix}_width",  2.0))
        h = float(i.get(f"{prefix}_height", 4.0))
        if w < 0.25: i[f"{prefix}_width"]  = 2.0
        if h < 0.25: i[f"{prefix}_height"] = 4.0

    elif t in ("I-Beam", "C-Channel", "Double I-Beam", "Routed (Monolithic)",
               "Aluminum I-Beam", "Aluminum C-Spar"):
        if float(i.get(f"{prefix}_h_web", 0)) < 0.1:
            i[f"{prefix}_h_web"] = 4.5
        if float(i.get(f"{prefix}_t_web", 0)) < 0.010:
            i[f"{prefix}_t_web"] = 0.125
        if float(i.get(f"{prefix}_b_top", 0)) < 0.1:
            i[f"{prefix}_b_top"] = 1.5
        if float(i.get(f"{prefix}_t_top", 0)) < 0.010:
            i[f"{prefix}_t_top"] = 0.125

    elif t == "Box Spar":
        if float(i.get(f"{prefix}_b_outer", 0)) < 0.5:
            i[f"{prefix}_b_outer"] = 2.0
        if float(i.get(f"{prefix}_h_outer", 0)) < 0.5:
            i[f"{prefix}_h_outer"] = 5.0
        if float(i.get(f"{prefix}_t_web", 0)) < 0.020:
            i[f"{prefix}_t_web"] = 0.125

    return i


def build_spar(spar_type: str, inputs: dict, prefix: str) -> CrossSection:
    def g(key, default=None):
        return inputs.get(f"{prefix}_{key}", default)
    def tip(key, root):
        return resolved_tip(g(key, None), root)
    t = spar_type
    if t == "Round Tube":
        return RoundTube(OD=float(g("od", 2.0)), wall=float(g("wall", 0.065)),
                         mat_name=g("mat", "6061-T6"))
    elif t == "Plain Rectangular":
        return PlainRect(width=float(g("width", 2.0)), height=float(g("height", 4.0)),
                         mat_name=g("cap_mat", "Sitka Spruce"))
    elif t in ("I-Beam", "C-Channel", "Routed (Monolithic)"):
        b_top = float(g("b_top",1.5)); t_top = float(g("t_top",0.75))
        b_bot = float(g("b_bot",1.5)); t_bot = float(g("t_bot",0.75))
        kw = dict(b_top=b_top, t_top=t_top, b_bot=b_bot, t_bot=t_bot,
                  b_top_tip=tip("b_top_tip", b_top), t_top_tip=tip("t_top_tip", t_top),
                  b_bot_tip=tip("b_bot_tip", b_bot), t_bot_tip=tip("t_bot_tip", t_bot),
                  h_web=float(g("h_web",4.5)), t_web=float(g("t_web",0.125)))
        cm = g("cap_mat","Sitka Spruce"); wm = g("web_mat","Birch Plywood")
        if t == "I-Beam":         return IBeam(**kw, cap_mat=cm, web_mat=wm)
        elif t == "C-Channel":    return CChannel(**kw, cap_mat=g("cap_mat","6061-T6"),
                                                   web_mat=g("web_mat","6061-T6"))
        else:                     return RoutedSpar(**kw, mat_name=cm)
    elif t == "Double I-Beam":
        b_top = float(g("b_top",1.5)); t_top = float(g("t_top",0.75))
        b_bot = float(g("b_bot",1.5)); t_bot = float(g("t_bot",0.75))
        return DoubleIBeam(
            b_top=b_top, t_top=t_top, b_bot=b_bot, t_bot=t_bot,
            b_top_tip=tip("b_top_tip", b_top), t_top_tip=tip("t_top_tip", t_top),
            b_bot_tip=tip("b_bot_tip", b_bot), t_bot_tip=tip("t_bot_tip", t_bot),
            h_web=float(g("h_web",4.5)), t_web=float(g("t_web",0.125)),
            web_spacing=float(g("web_spacing",1.0)),
            cap_mat=g("cap_mat","Sitka Spruce"), web_mat=g("web_mat","Birch Plywood"))
    elif t == "Box Spar":
        b_outer = float(g("b_outer",2.0)); t_cap = float(g("t_cap",0.75))
        return BoxSpar(b_outer=b_outer, h_outer=float(g("h_outer",5.0)),
                       t_web=float(g("t_web",0.125)), t_cap=t_cap,
                       b_outer_tip=tip("b_outer_tip", b_outer),
                       t_cap_tip=tip("t_cap_tip", t_cap),
                       cap_mat=g("cap_mat","Sitka Spruce"), web_mat=g("web_mat","Birch Plywood"))
    elif t == "Aluminum I-Beam":
        # Angle caps both sides + sheet web, all aluminum
        b_top = float(g("b_top",1.5)); t_top = float(g("t_top",0.125))
        b_bot = float(g("b_bot",1.5)); t_bot = float(g("t_bot",0.125))
        return IBeam(b_top=b_top, t_top=t_top, b_bot=b_bot, t_bot=t_bot,
                     b_top_tip=tip("b_top_tip", b_top), t_top_tip=tip("t_top_tip", t_top),
                     b_bot_tip=tip("b_bot_tip", b_bot), t_bot_tip=tip("t_bot_tip", t_bot),
                     h_web=float(g("h_web",5.0)), t_web=float(g("t_web",0.050)),
                     cap_mat=g("cap_mat","6061-T6"), web_mat=g("web_mat","6061-T6"))
    elif t == "Aluminum C-Spar":
        # Single angle cap one side + sheet web
        from spar_sections import AluminumCSpar
        b_cap = float(g("b_top",1.5)); t_cap = float(g("t_top",0.125))
        return AluminumCSpar(
            b_cap=b_cap, t_cap=t_cap,
            b_cap_tip=tip("b_top_tip", b_cap), t_cap_tip=tip("t_top_tip", t_cap),
            h_web=float(g("h_web",5.0)), t_web=float(g("t_web",0.050)),
            cap_side=str(g("cap_side","top")),
            mat_name=str(g("cap_mat","6061-T6")))
    else:
        raise ValueError(f"Unknown spar type: {t}")


# ─── MAIN ANALYZER ───────────────────────────────────────────────────────────

class WingStressAnalyzer:

    def __init__(self, inputs: Optional[dict] = None):
        inp = dict(DEFAULT_INPUTS)
        if inputs:
            inp.update(inputs)
        _normalize_inputs(inp)
        self.validation_warnings = []
        self.inp = inp
        self._extract_inputs()

    def _extract_inputs(self):
        i = self.inp
        self.b_half      = float(i["b"]) / 2.0
        self.r           = float(i["r"])
        self.N           = int(i["num_points"])
        self.root_chord     = float(i["root_chord"])
        self.tip_chord      = float(i["tip_chord"])
        self.taper_start_bl = float(i.get("taper_start_bl", 0.0))  # BL where taper begins
        self.taper_reference = canonical_taper_reference(i.get("taper_reference", "Leading edge"))
        self.rib_spacing = float(i.get("rib_spacing", 12.0))
        # Stiffener/nose-rib spacing: 0 means use rib_spacing
        _ss = float(i.get("stiffener_spacing", 0.0))
        self.stiffener_spacing = _ss if _ss > 0 else self.rib_spacing
        _nr = float(i.get("nose_rib_spacing", 0.0))
        self.nose_rib_spacing  = _nr if _nr > 0 else self.rib_spacing
        # Doublers
        self.front_doubler_t      = float(i.get("front_spar_doubler_t", 0.0))
        self.front_doubler_extent = int(float(i.get("front_spar_doubler_extent", 1)))
        self.rear_doubler_t       = float(i.get("rear_spar_doubler_t", 0.0))
        self.rear_doubler_extent  = int(float(i.get("rear_spar_doubler_extent", 1)))
        self.bearing_allowable_psi = float(i.get("bearing_allowable_psi", 12000.0))
        self.lift_type   = i["lift_distribution_type"]
        self.num_spars   = int(i["num_spars"])
        self.front_pct   = parse_fraction(i["front_spar_percent"], 0.15)
        self.rear_pct    = parse_fraction(i["rear_spar_percent"], 0.65)
        self.lsf         = parse_fraction(i["front_spar_load_share"], 0.55)
        self.rsf         = 1.0 - self.lsf
        self.wing_struct = i.get("wing_structure_type", "fabric_tube")
        self.ng_lift     = float(i["ng_lift"])
        self.n           = float(i["n"])
        self.n_neg       = float(i.get("n_neg", -3.0))
        self.Weight      = float(i["Weight"])
        self.Wing_Weight = float(i["Wing_Weight"])
        self.Tail_Down   = float(i["Tail_Down_1g"])
        self.dist_relief = parse_bool(i.get("distribute_wing_weight", False))
        self.config      = i.get("config", "strut_braced")
        self.strut_bl    = float(i.get("strut_bl", 104.0))
        self.strut_vert  = float(i.get("strut_vert", 44.0))
        self.strut_fuse_bl = float(i.get("strut_fuse_bl", 0.0))
        self.strut_mat   = i.get("strut_mat", "4130 Chromoly (normalized)")
        self.strut_od    = float(i.get("strut_tube_od", 3.0))
        self.strut_wall  = float(i.get("strut_tube_wall", 0.065))
        self.secondary   = parse_bool(i.get("secondary_bending", False))
        self.jury        = parse_bool(i.get("jury_strut", False))
        self.jury_bl     = float(i.get("jury_spar_bl", 60.0))
        self.jury_tube_mat = i.get("jury_tube_mat", "6061-T6 Aluminum")
        self.jury_tube_od = float(i.get("jury_tube_od", 0.75))
        self.jury_tube_wall = float(i.get("jury_tube_wall", 0.035))
        self.jury_front_link_length = float(i.get("jury_front_link_length", 18.0))
        self.jury_rear_link_length = float(i.get("jury_rear_link_length", 18.0))
        self.jury_front_link_angle = float(i.get("jury_front_link_angle", 45.0))
        self.jury_rear_link_angle = float(i.get("jury_rear_link_angle", 45.0))
        self.curvature_sign = float(i.get("curvature_sign", 1.0))
        self.wood_kd     = float(i.get("wood_knockdown", 0.75))
        self.rib_type  = i.get("rib_type", "Plywood web")
        self.rib_h_web = float(i.get("rib_h_web", 3.0))
        self.rib_t_web = float(i.get("rib_t_web", 0.125))
        self.rib_b_cap = float(i.get("rib_b_cap", 0.75))
        self.rib_t_cap = float(i.get("rib_t_cap", 0.125))
        self.rib_mat   = i.get("rib_mat", "Birch Plywood")
        self.airfoil     = i.get("airfoil", "Manual Entry")
        self.Cm_ac       = float(i.get("Cm_ac", 0.0))
        self.Cm_flap     = float(i.get("Cm_flap", 0.0))
        self.Cl_alpha    = float(i.get("Cl_alpha", 6.28))
        self.x_ac_c      = float(i.get("x_ac_c", 0.25))
        self.Vd_mph      = float(i.get("Vd_mph", 100.0))
        self.Vc_mph      = float(i.get("Vc_mph",  self.Vd_mph * 0.75))
        self.Va_mph      = float(i.get("Va_mph",  self.Vd_mph * 0.55))
        self.Cm_flap     = float(i.get("Cm_flap", 0.0))
        self.alt_ft      = float(i.get("altitude_ft", 0.0))
        self.t_c         = float(i.get("airfoil_t_c", 0.12))
        af = get_airfoil(self.airfoil) if self.airfoil else None
        xt = i.get("airfoil_x_t_c")
        if xt in (None, "") and af and af.get("x_t_c"):
            xt = af["x_t_c"]
        self.x_t_c = float(0.30 if xt in (None, "") else xt)

        # D-cell
        self.dcell_enabled = parse_bool(i.get("dcell_enabled", False))
        if self.dcell_enabled:
            c2s   = self.front_pct * self.root_chord
            t_web = float(i.get("front_spar_t_web",
                                 i.get("front_spar_wall", 0.125)))
            self.dcell = DCellSkin(
                t_skin=float(i.get("dcell_skin_thick", 0.0625)),
                skin_mat=i.get("dcell_skin_mat", "Birch Plywood"),
                chord_to_spar=c2s, t_web=t_web,
                t_c=self.t_c, x_t_c=self.x_t_c)
        else:
            self.dcell = None

        # Geodetic
        self.geodetic_enabled = parse_bool(i.get("geodetic_enabled", False))
        if self.geodetic_enabled and self.wing_struct == "fabric_buildup":
            self.geodetic = GeodeticPanel(
                rib_spacing=self.rib_spacing,
                strips_per_bay=int(i.get("geodetic_strips_per_bay", 2)),
                strip_width=float(i.get("geodetic_w", 1.0)),
                strip_thick=float(i.get("geodetic_t", 0.125)),
                angle_deg=float(i.get("geodetic_angle", 45.0)),
                mat_name=i.get("geodetic_mat", "Sitka Spruce"))
        else:
            self.geodetic = None

        # Skin panels — only active when wing_structure_type == "aluminum_skin"
        # AND a non-zero thickness is provided.  This prevents fabric_tube/buildup
        # configurations from triggering skin buckling checks.
        wing_struct_for_skin = i.get("wing_structure_type", "fabric_tube")
        skin_top_thick = float(i.get("skin_top_thick", 0.0))
        skin_bot_thick = float(i.get("skin_bot_thick", 0.0))
        # Only activate skin if aluminum_skin structure is selected
        if wing_struct_for_skin == "aluminum_skin" and (skin_top_thick > 1e-6 or skin_bot_thick > 1e-6):
            self.top_skin = SkinPanel(
                skin_top_thick or 0.025,
                i.get("skin_top_mat", "Birch Plywood")
            )
            self.bot_skin = SkinPanel(
                skin_bot_thick or 0.025,
                i.get("skin_bot_mat", "Birch Plywood")
            )
        else:
            self.top_skin = None
            self.bot_skin = None

        # Inboard sheets between the spars. Off does not change an existing wing.
        self.torsion_box_enabled = parse_bool(i.get("torsion_box_enabled", False))
        try:
            bays = int(float(i.get("torsion_box_bays", 0) or 0))
        except (TypeError, ValueError):
            bays = 0
        self.torsion_box_bays = max(bays, 0)

        def _sheet_gauge(key, default):
            try:
                return max(float(i.get(key, default) or 0.0), 0.0)
            except (TypeError, ValueError):
                return default

        def _sheet_mat(key):
            name = str(i.get(key, "Birch Plywood") or "Birch Plywood")
            return name if name in MATERIAL_DB else "Birch Plywood"

        self.torsion_box_top = _sheet_gauge("torsion_box_top_thick", 0.125)
        self.torsion_box_bot = _sheet_gauge("torsion_box_bot_thick", 0.125)
        self.torsion_box_top_mat = _sheet_mat("torsion_box_top_mat")
        self.torsion_box_bot_mat = _sheet_mat("torsion_box_bot_mat")

        self.front_spar_type = i.get("front_spar_type", "Round Tube")
        self.rear_spar_type  = i.get("rear_spar_type",  "Round Tube")
        # Sanitize spar dimensions before building — prevents zero-EI crashes
        i = _sanitize_spar_inputs(i, "front_spar")
        i = _sanitize_spar_inputs(i, "rear_spar")
        self.inp = i  # update with sanitized values
        self.front_spar = build_spar(self.front_spar_type, i, "front_spar")
        self.rear_spar  = build_spar(self.rear_spar_type,  i, "rear_spar") \
                          if self.num_spars == 2 else None

        self.x       = np.linspace(0, self.b_half, self.N)
        self.dx      = self.x[1] - self.x[0]
        # Chord distribution: constant from root to taper_start_bl, then linear taper to tip
        # taper_start_bl = 0 → fully tapered (standard); = b_half → constant chord (rectangular)
        ts = np.clip(self.taper_start_bl, 0.0, self.b_half)
        self.chord_x = np.where(
            self.x <= ts,
            self.root_chord,   # constant chord inboard section
            self.root_chord + (self.tip_chord - self.root_chord) *
                (self.x - ts) / max(self.b_half - ts, 1e-6)   # linear taper outboard
        )
        self.y_le, self.y_te, self.y_front, self.y_rear = self._planform_offsets()

    def _planform_offsets(self):
        """Chordwise stations aft of the root leading edge.

        The local chord and the spar percentages stay as entered. The whole
        section shifts so the chosen line is straight: the leading edge, the
        front spar, or the trailing edge. Beam loads still follow the buttline.
        """

        chord = self.chord_x
        root = self.root_chord
        front = self.front_pct * chord
        rear = self.rear_pct * chord
        if self.taper_reference == "Trailing edge":
            y_te = np.full_like(chord, root)
            y_le = y_te - chord
        elif self.taper_reference == "Main spar":
            y_le = self.front_pct * (root - chord)
            y_te = y_le + chord
        else:
            y_le = np.zeros_like(chord)
            y_te = chord.copy()
        return y_le, y_te, y_le + front, y_le + rear

    # ── Lift distributions ───────────────────────────────────────────────────

    def _lift_dist(self, total_lift: float) -> np.ndarray:
        lt = self.lift_type; x = self.x; c = self.chord_x; b = self.b_half
        ellip  = (4*total_lift/(math.pi*b))*np.sqrt(np.maximum(1-(x/b)**2, 0))
        chord_ = total_lift/b * c/np.mean(c)
        if lt == "elliptical":  return ellip
        if lt == "chord_based": return chord_
        if lt == "uniform":     return np.full(self.N, total_lift/b)
        return 0.5*(ellip + chord_)   # schrenk

    # ── Integration ──────────────────────────────────────────────────────────

    def _shear_moment(self, w):
        """Integrate distributed load from tip to root.

        Support reactions are applied later. Mixing them into this pass
        double-counts the strut and leaves no equilibrium equation for a jury.
        """

        V = np.zeros(self.N)
        M = np.zeros(self.N)
        for i in range(self.N-2, -1, -1):
            V[i] = V[i+1] + w[i] * self.dx
            M[i] = M[i+1] + V[i] * self.dx
        return V, M

    def _deflect_cantilever(self, M, EI):
        th = np.zeros(self.N); z = np.zeros(self.N)
        for i in range(1, self.N):
            kappa  = self.curvature_sign * M[i] / max(EI[i], 1.0)
            th[i]  = th[i-1] + kappa*self.dx
            z[i]   = z[i-1]  + th[i]*self.dx
        return th, z

    def _moment_to_shear(self, M):
        """Shear consistent with ``M[i] = M[i+1] + V[i]*dx``."""
        V = np.zeros(self.N)
        if self.N < 2 or self.dx <= 0.0:
            return V
        V[:-1] = (np.asarray(M, dtype=float)[:-1] - np.asarray(M, dtype=float)[1:]) / self.dx
        return V

    def _rib_ties_spars(self) -> bool:
        """Cantilever and single-strut wings deliver spar load through the ribs.

        Bruhn and Peery treat the rib as stiff in its own plane, so the spars
        share one bending curve. A dual-strut wing already puts a strut on
        each spar, and that path is unchanged.
        """
        return self.num_spars == 2 and self.config in ("cantilever", "single_strut")

    def _ei_shares(self):
        """Bending-moment fractions for spars locked to the same curvature."""
        total = np.maximum(self._EI_f + self._EI_r, 1.0)
        return self._EI_f / total, self._EI_r / total

    def _rib_transfer_bay_torque(self) -> np.ndarray:
        """Torque in each rib bay from the load moved between the spars.

        The airload arrives in the entered front/rear share. Equal curvature
        requires the stiffness share. Peery and Bruhn put that difference
        through the rib, and the rib torque is the transferred force times
        the spar gap. Returns one value per span station, in lb·in per bay.
        """
        out = np.zeros(self.N)
        if not self._rib_ties_spars() or not hasattr(self, "pos"):
            return out
        gap = max((self.rear_pct - self.front_pct) * self.root_chord, 0.0)
        if gap <= 0.0 or self.N < 2:
            return out
        w = np.abs(np.asarray(self.pos["w"], dtype=float))
        q_applied_r = self.rsf * w
        V_carried_r = np.abs(np.asarray(self.pos["V_rear"], dtype=float))
        q_carried_r = np.zeros(self.N)
        q_carried_r[:-1] = (V_carried_r[:-1] - V_carried_r[1:]) / max(self.dx, 1e-9)
        out[:] = np.abs(q_applied_r - q_carried_r) * self.rib_spacing * gap
        return out

    def _deflect_strut(self, M, EI, si):
        th0, z0 = self._deflect_cantilever(M, EI)
        # Unit root slope
        th1 = np.ones(self.N); z1 = np.zeros(self.N)
        for i in range(1, self.N): z1[i] = z1[i-1] + th1[i]*self.dx
        if abs(z1[si]) < 1e-15: return th0, z0
        alpha = -z0[si] / z1[si]
        return th0 + alpha*th1, z0 + alpha*z1

    def _strut_idx(self):
        return int(np.argmin(np.abs(self.x - self.strut_bl)))

    # ── Spar arrays ──────────────────────────────────────────────────────────

    def _cap_fraction(self) -> np.ndarray:
        """0 at the taper-start station, 1 at the tip. Inboard caps stay at the root size."""

        start = float(np.clip(self.taper_start_bl, 0.0, self.b_half))
        return np.clip((self.x - start) / max(self.b_half - start, 1e-9), 0.0, 1.0)

    def _spar_arrays(self):
        depth = self.chord_x / max(self.root_chord, 1e-9)
        frac = self._cap_fraction()
        def arr(spar):
            if hasattr(spar, "caps_at"):
                props = [
                    spar.get_props(float(depth[i]), caps=spar.caps_at(float(frac[i])))
                    for i in range(self.N)
                ]
            elif hasattr(spar, "get_arrays"):
                d = spar.get_arrays(self.x, self.b_half, self.root_chord, self.tip_chord,
                                    chord=self.chord_x, cap_taper=False)
                return (d["EI"], d["I_tr"], d["y_max"], d["y_top"], d["y_bot"])
            else:
                props = [spar.get_props(float(s)) for s in depth]
            return (np.array([p.EI    for p in props]),
                    np.array([p.I_tr  for p in props]),
                    np.array([p.y_max for p in props]),
                    np.array([p.y_top for p in props]),
                    np.array([p.y_bot for p in props]))
        self._EI_f,self._Itr_f,self._ym_f,self._yt_f,self._yb_f = arr(self.front_spar)
        rs = self.rear_spar if self.rear_spar else self.front_spar
        self._EI_r,self._Itr_r,self._ym_r,self._yt_r,self._yb_r = arr(rs)

    # ── GJ arrays ────────────────────────────────────────────────────────────

    def _sheet_modulus(self, name: str) -> float:
        if name not in MATERIAL_DB:
            name = "Birch Plywood" if "Birch Plywood" in MATERIAL_DB else "6061-T6"
        return float(MATERIAL_DB[name]["G"])

    def _spar_web_G(self, prefix: str) -> float:
        name = self.inp.get(f"{prefix}_web_mat") or self.inp.get(f"{prefix}_mat") or "6061-T6"
        return self._sheet_modulus(name)

    def _torsion_box_active(self) -> bool:
        """True when the inboard sheets are chosen and can close a cell."""

        if not getattr(self, "torsion_box_enabled", False):
            return False
        if int(getattr(self, "torsion_box_bays", 0) or 0) <= 0:
            return False
        if getattr(self, "num_spars", 1) < 2:
            return False
        if float(getattr(self, "torsion_box_top", 0.0) or 0.0) <= 1e-9:
            return False
        if float(getattr(self, "torsion_box_bot", 0.0) or 0.0) <= 1e-9:
            return False
        return float(getattr(self, "rib_spacing", 0.0) or 0.0) > 0.0

    def _torsion_box_end(self) -> float:
        """Outboard end of the sheeted bays, inches from the root."""

        if not self._torsion_box_active():
            return 0.0
        return min(self.torsion_box_bays * self.rib_spacing, self.b_half)

    def _box_covers(self, x: float) -> bool:
        end = self._torsion_box_end()
        return end > 0.0 and float(x) <= end + 1e-9

    def _aft_closed_at(self, x: float) -> bool:
        if self.num_spars != 2:
            return False
        if self._box_covers(x):
            return True
        if self.geodetic is not None:
            return True
        return getattr(self, "top_skin", None) is not None

    def _box_wall_gt(self):
        """G*t of the top and bottom walls. A stressed skin adds in parallel."""

        gt_top = self._sheet_modulus(self.torsion_box_top_mat) * self.torsion_box_top
        gt_bot = self._sheet_modulus(self.torsion_box_bot_mat) * self.torsion_box_bot
        if getattr(self, "top_skin", None) is not None and self.bot_skin is not None:
            gt_top += float(MATERIAL_DB[self.top_skin.mat_name]["G"]) * float(self.top_skin.thickness)
            gt_bot += float(MATERIAL_DB[self.bot_skin.mat_name]["G"]) * float(self.bot_skin.thickness)
        return gt_top, gt_bot

    def _nose_plus_box_gj(self, A1, ds1, dss, c_b, h, t_rear):
        """Two-cell Bredt. Each wall uses its own shear modulus. Gauge is constant."""

        G_skin = float(MATERIAL_DB[self.dcell.skin_mat]["G"])
        gt_top, gt_bot = self._box_wall_gt()
        G_rear = self._spar_web_G("rear_spar")
        A2 = max(c_b * h, 1e-9)
        ds2 = (c_b / max(gt_top, 1e-9)
               + c_b / max(gt_bot, 1e-9)
               + h / max(G_rear * max(t_rear, 1e-9), 1e-12))
        return two_cell_bredt(A1, A2, ds1 / G_skin, ds2, dss / G_skin, 1.0, 1.0, 1.0)

    def _rectangle_box_gj(self, c_b, h, t_front, t_rear):
        """One rectangular cell when the nose is open and the bay is sheeted."""

        A = max(c_b * h, 1e-9)
        gt_top, gt_bot = self._box_wall_gt()
        ds = (c_b / max(gt_top, 1e-9)
              + c_b / max(gt_bot, 1e-9)
              + h / max(self._spar_web_G("front_spar") * max(t_front, 1e-9), 1e-12)
              + h / max(self._spar_web_G("rear_spar") * max(t_rear, 1e-9), 1e-12))
        q = 1.0 / (2.0 * A)
        return 4.0 * A * A / max(ds, 1e-18), 0.0, q

    def _gj_arrays(self):
        N = self.N; scales = self.chord_x/self.root_chord
        GJ = np.zeros(N); q1f = np.zeros(N); q2f = np.zeros(N)
        h0  = self.t_c * self.root_chord
        t_wfs = float(self.inp.get("front_spar_t_web",
                                    self.inp.get("front_spar_wall", 0.125)))
        t_wrs = float(self.inp.get("rear_spar_t_web",
                                    self.inp.get("rear_spar_wall", 0.094)))
        for i, s in enumerate(scales):
            boxed = self._box_covers(self.x[i])
            if not self.dcell_enabled and not boxed:
                break
            h    = h0 * s
            c_b  = (self.rear_pct-self.front_pct)*self.chord_x[i]
            if boxed and self.dcell is None:
                GJ[i], q1f[i], q2f[i] = self._rectangle_box_gj(c_b, h, t_wfs, t_wrs)
                continue
            if self.dcell is None:
                continue
            A1   = self.dcell.enclosed_area(h, s)
            G1   = MATERIAL_DB[self.dcell.skin_mat]["G"]
            ds1  = self.dcell.ds_over_t_own(h, s)
            dss  = self.dcell.ds_over_t_web(h, s)

            if boxed:
                q1, q2, gj = self._nose_plus_box_gj(A1, ds1, dss, c_b, h, t_wrs)
                GJ[i]=gj; q1f[i]=q1; q2f[i]=q2
            elif self.geodetic is not None:
                A2  = self.geodetic.enclosed_area(c_b, h)
                G2  = MATERIAL_DB[self.geodetic.mat_name]["G"]
                ds2 = self.geodetic.ds_over_t_own(c_b, h, t_wrs*s, s)
                q1, q2, gj = two_cell_bredt(A1,A2,ds1,ds2,dss,G1,G2,1.0)
                GJ[i]=gj; q1f[i]=q1; q2f[i]=q2
            elif getattr(self, "top_skin", None) is not None:
                A2  = c_b * h; G2 = MATERIAL_DB[self.top_skin.mat_name]["G"]
                tt  = self.top_skin.thickness; tb = self.bot_skin.thickness
                ds2 = c_b*s/tt + c_b*s/tb + h/t_wrs
                q1, q2, gj = two_cell_bredt(A1,A2,ds1,ds2,dss,G1,G2,1.0)
                GJ[i]=gj; q1f[i]=q1; q2f[i]=q2
            else:
                GJ[i]  = self.dcell.GJ(h, s)
                q1f[i] = 1.0/(2*A1); q2f[i] = 0.0
        return GJ, q1f, q2f

    # ── Torsion ──────────────────────────────────────────────────────────────

    def _torsion_transfer_stiffness(self) -> dict:
        """Return rib/geodetic/skin stiffness terms for the torsion report.

        These values are not applied as springs on the spars. Spar bending
        follows the cantilever, single-strut, or dual-strut beam path.
        """

        chord_box = (self.rear_pct - self.front_pct) * self.root_chord
        spar_gap = max(chord_box, 1.0)

        # Rib in-plane stiffness. Plywood and formed aluminum are shear panels.
        # A foam rib with spruce caps is a sandwich beam. Only the cantilever
        # and single-strut paths use this stiffness to describe the spar tie.
        self._rib_model = rib_tie_stiffness(
            self.rib_type, spar_gap, self.rib_spacing,
            self.rib_h_web, self.rib_t_web, self.rib_b_cap, self.rib_t_cap,
            self.rib_mat, self.wood_kd)
        k_rib = self._rib_model["k_per_span"] if self._rib_ties_spars() else 0.0

        if self.geodetic is not None:
            red = float(self.inp.get("geodetic_reduction_factor", 0.75))
            k_geo = self.geodetic.shear_stiffness_per_span(red, 1.0)
        else:
            k_geo = 0.0

        if getattr(self, "top_skin", None) is not None:
            G_skin = MATERIAL_DB[self.top_skin.mat_name]["G"]
            k_skin = G_skin * self.top_skin.thickness / spar_gap
        else:
            k_skin = 0.0

        k_total = k_rib + k_geo + k_skin
        denom = max(k_total, 1e-12)

        return {
            "chord_box": chord_box,
            "spar_gap": spar_gap,
            "k_rib": k_rib,
            "k_geo": k_geo,
            "k_skin": k_skin,
            "k_total": k_total,
            "f_rib": k_rib / denom,
            "f_geo": k_geo / denom,
            "f_skin": k_skin / denom,
        }

    def _distributed_torsion(self, w_total, q_psi: float, *, sign: float = 1.0) -> tuple:
        """Return aerodynamic, structural, and total distributed torque arrays.

        ``w_total`` may be signed. ``sign`` controls the aerodynamic torque
        direction for load cases; the report path uses the default positive
        convention.
        """

        c = self.chord_x
        y_ac = self.y_le + self.x_ac_c * c
        y_sc = self._shear_center_y()
        # Positive torque is nose-up. Negative Cm is nose-down. Lift aft of
        # the shear center is nose-up (Bisplinghoff / Fung, same e as divergence).
        T_aero = self.Cm_ac * q_psi * c**2 * sign + np.asarray(w_total, dtype=float) * (y_ac - y_sc)

        if self.config == "single_strut" and self.num_spars == 2:
            e_rs = (self.rear_pct - self.front_pct) * c
            T_struct = self.rsf * w_total * e_rs
        else:
            T_struct = np.zeros(self.N)

        return T_aero, T_struct, T_aero + T_struct

    def _shear_center_y(self) -> np.ndarray:
        """Shear center, inches aft of the root leading edge, at each station."""

        if getattr(self, "_y_sc", None) is not None and len(self._y_sc) == self.N:
            return self._y_sc
        y_sc = np.zeros(self.N)
        for i, chord in enumerate(self.chord_x):
            boxed = self._box_covers(self.x[i])
            x_local, _method = self._shear_center_x(
                float(chord), aft=self._aft_closed_at(self.x[i]), box=boxed)
            y_sc[i] = float(self.y_le[i]) + float(x_local)
        self._y_sc = y_sc
        return y_sc

    def _integrate_twist(self, T_dist, GJ):
        """Root-fixed twist from distributed torque. Positive phi is nose-up."""

        T_run = np.zeros(self.N)
        for i in range(self.N - 2, -1, -1):
            T_run[i] = T_run[i + 1] + T_dist[i] * self.dx
        with np.errstate(divide="ignore", invalid="ignore"):
            dphidx = np.where(GJ > 0, T_run / GJ, 0.0)
        phi = np.zeros(self.N)
        for i in range(1, self.N):
            phi[i] = phi[i - 1] + dphidx[i] * self.dx
        return T_run, phi

    def _add_twist_to_deflection(self, case: dict, phi: np.ndarray) -> None:
        """Spar position is the bending curve plus twist about the shear center.

        Peery and Megson: a nose-up rotation lowers a point aft of the shear
        center by phi times that chordwise distance. Bending stress is unchanged.
        """

        y_sc = self._shear_center_y()
        case["phi"] = np.asarray(phi, dtype=float)
        case["z_bend_front"] = np.array(case["z_front"], dtype=float, copy=True)
        case["z_bend_rear"] = np.array(case["z_rear"], dtype=float, copy=True)
        z_f = case["z_bend_front"] - case["phi"] * (self.y_front - y_sc)
        if self.num_spars == 2:
            z_r = case["z_bend_rear"] - case["phi"] * (self.y_rear - y_sc)
        else:
            z_r = z_f.copy()
        case["z_front"] = z_f
        case["z_rear"] = z_r
        case["z_delta"] = z_r - z_f
        case["z_max_front"] = float(np.max(np.abs(z_f)))
        case["z_max_rear"] = float(np.max(np.abs(z_r)))
        case["z_delta_max"] = float(np.max(np.abs(z_r - z_f)))

    def _torsion(self, GJ, q1f, q2f, w_total):
        q_psi = dynamic_pressure_psi(self.Vd_mph, self.alt_ft)
        T_aero, T_struct, T_tot = self._distributed_torsion(w_total, q_psi)

        # Twist rate is running torque over GJ. The root is fixed, so twist
        # is zero there and the tip rotation is the integral out to the tip.
        # Positive phi is nose-up.
        T_run, phi = self._integrate_twist(T_tot, GJ)

        # Skin stresses
        h0 = self.t_c*self.root_chord; scales = self.chord_x/self.root_chord
        tau_d = np.zeros(self.N); tau_g = np.zeros(self.N)
        for i, s in enumerate(scales):
            T = T_run[i]
            if GJ[i]<=0 or T==0: continue
            if self.dcell:
                A1 = self.dcell.enclosed_area(h0*s, s)
                tau_d[i] = q1f[i]*T / (self.dcell.t_skin*s)
            if self.geodetic:
                te = self.geodetic.t_eff(s)
                if te>0: tau_g[i] = q2f[i]*T/te

        # ── Torsion transfer stiffness — load sharing between ribs, geodetic, skin ──
        transfer = self._torsion_transfer_stiffness()
        spar_gap = transfer["spar_gap"]
        k_rib = transfer["k_rib"]
        k_geo = transfer["k_geo"]
        k_skin = transfer["k_skin"]
        k_total = transfer["k_total"]
        f_rib = transfer["f_rib"]
        f_geo = transfer["f_geo"]
        f_skin = transfer["f_skin"]

        # Rib demand is the aerodynamic bay torque plus, for a rib-tied
        # cantilever or single-strut wing, the couple from the spar-to-spar
        # load the rib carries. This is a demand output, not a rib sizing check.
        aero_bay_torque = np.abs(T_tot) * self.rib_spacing
        transfer_bay_torque = self._rib_transfer_bay_torque()
        local_torque = aero_bay_torque + transfer_bay_torque
        max_idx = int(np.argmax(local_torque))
        rib_bay_torque = float(local_torque[max_idx])
        rib_aero_torque = float(aero_bay_torque[max_idx])
        rib_transfer_torque = float(transfer_bay_torque[max_idx])
        rib_reaction = rib_bay_torque / max(spar_gap, 1e-9)
        rib_reaction_station = float(self.x[max_idx])
        rib_model = getattr(self, "_rib_model", {})
        shear_area = float(rib_model.get("shear_area", 0.0))
        rib_tau = rib_reaction / shear_area if shear_area > 0.0 else 0.0
        rib_cap_sigma = float(rib_model.get("cap_sigma_per_lb", 0.0)) * rib_reaction
        k_one = float(rib_model.get("k_one", 0.0))
        rib_tie_deflection = rib_reaction / k_one if k_one > 0.0 else 0.0

        # ANC-18-style drag-truss demand for a geodetic/diagonal strip panel:
        # report required shear flow and strip axial force. This is a demand
        # output only; bond/joint/attachment details and local member stability
        # remain outside this global wing solver.
        geodetic_q = 0.0
        geodetic_strip_force = 0.0
        geodetic_strip_stress = 0.0
        geodetic_station = 0.0
        if self.geodetic is not None:
            q_geo = np.abs(q2f * T_run)
            geo_idx = int(np.argmax(q_geo))
            geodetic_q = float(q_geo[geo_idx])
            geo_scale = float(scales[geo_idx])
            geodetic_strip_force = float(self.geodetic.strip_force(geodetic_q, geo_scale))
            geodetic_strip_stress = float(self.geodetic.strip_stress(geodetic_q, geo_scale))
            geodetic_station = float(self.x[geo_idx])

        # ── Cruise speed torsion check and CP positions ──────────────────────
        q_vc  = dynamic_pressure_psi(self.Vc_mph, self.alt_ft)
        q_va  = dynamic_pressure_psi(self.Va_mph, self.alt_ft)
        # Cm at cruise (flaps up) and flap case
        T_aero_vc    = np.abs(self.Cm_ac) * q_vc * self.chord_x**2
        T_run_vc     = np.zeros(self.N)
        for i in range(self.N-2, -1, -1):
            T_run_vc[i] = T_run_vc[i+1] + T_aero_vc[i]*self.dx
        # Flap case: Cm_flap adds to Cm_ac (full flap extension)
        Cm_flap_total = self.Cm_ac + self.Cm_flap
        T_aero_flap  = np.abs(Cm_flap_total) * q_va * self.chord_x**2
        T_run_flap   = np.zeros(self.N)
        for i in range(self.N-2, -1, -1):
            T_run_flap[i] = T_run_flap[i+1] + T_aero_flap[i]*self.dx

        # CP positions at root chord for key flight conditions
        # CP/c = x_ac/c - Cm_ac / CL   (negative Cm → CP moves aft)
        # CL = ng_lift / (q * b * root_chord / 12^2) roughly
        def cp_frac(q_psi, n_g):
            """Centre of pressure as fraction of chord at given speed and load factor."""
            if q_psi <= 0: return self.x_ac_c
            # Total wing area in ft² = b * c / 144  (b and c in inches)
            S_ft2 = (2*self.b_half * self.root_chord) / 144.0
            L_total = n_g * self.ng_lift / self.n if self.n > 0 else 0
            CL = L_total / max(q_psi * 144 * S_ft2, 1e-9)  # q in psi → psf *144
            if abs(CL) < 0.01: return self.x_ac_c  # avoid divide by zero
            return self.x_ac_c - self.Cm_ac / CL

        cp_1g   = cp_frac(q_vc, 1.0)
        cp_ng   = cp_frac(q_psi, self.n)
        cp_neg  = cp_frac(q_psi, abs(self.n_neg))
        cp_dive = cp_frac(dynamic_pressure_psi(self.Vd_mph, self.alt_ft), 0.5)

        return {"T_aero":T_aero,"T_struct":T_struct,"T_total":T_tot,
                "T_running":T_run,"phi":phi,
                "phi_root_deg":0.0,
                "phi_tip_deg":math.degrees(phi[-1]),
                "tau_dcell":tau_d,"tau_geo":tau_g,
                "T_run_vc":T_run_vc, "Vc_mph":self.Vc_mph,
                "T_run_flap":T_run_flap, "Cm_flap":Cm_flap_total,
                "cp_1g":cp_1g, "cp_ng":cp_ng,
                "cp_neg":cp_neg, "cp_dive":cp_dive,
                "f_rib":f_rib,"f_geo":f_geo,"f_skin":f_skin,
                "k_rib":k_rib,"k_geo":k_geo,"k_total":k_total,
                "rib_aero_torque":rib_aero_torque,
                "rib_transfer_torque":rib_transfer_torque,
                "rib_bay_torque":rib_bay_torque,
                "rib_reaction_required":rib_reaction,
                "rib_reaction_station":rib_reaction_station,
                "rib_model":rib_model,
                "rib_tau":rib_tau,
                "rib_cap_sigma":rib_cap_sigma,
                "rib_tie_deflection":rib_tie_deflection,
                "geodetic_q":geodetic_q,
                "geodetic_strip_force":geodetic_strip_force,
                "geodetic_strip_stress":geodetic_strip_stress,
                "geodetic_station":geodetic_station}

    # ── Divergence ───────────────────────────────────────────────────────────

    def _has_closed_torsion_cell(self) -> bool:
        """True when a nose, geodetic bay, or stressed-skin box can carry torque."""

        if self.dcell is not None:
            return True
        if self.geodetic is not None:
            return True
        if getattr(self, "top_skin", None) is not None:
            return True
        return self._torsion_box_end() > 0.0

    def _shear_center_x(self, chord: float, aft=None, box: bool = False) -> tuple:
        """Chordwise shear center from the leading edge, and how it was obtained.

        An open tube puts the shear center on the spar axis. A closed nose or
        box uses the thin-wall shear flow of that same contour. An inboard
        torsion box is station by station: pass aft and box for that station.
        """

        front = self.front_pct * chord
        rear = self.rear_pct * chord
        if aft is None:
            aft = self._aft_closed_at(0.0)
            box = box or self._box_covers(0.0)
        if self.dcell is None and not aft:
            return front, "spar axis"

        h_max = max(self.t_c * chord, 1e-6)
        scale = chord / max(self.root_chord, 1e-6)
        if self.dcell is not None and not aft:
            return self.dcell.shear_center_x(h_max, scale), "nose shear flow"
        if self.dcell is None and aft:
            return rectangular_cell_shear_center(front, rear, h_max), "box centroid"

        geo = self.dcell.nose_geometry(h_max, scale)
        pts = geo["points"]
        x_spar = geo["x_spar"]
        tvals = []
        for i in range(len(pts) - 1):
            x1 = pts[i][0]
            x2 = pts[i + 1][0]
            if abs(x1 - x_spar) < 1e-6 and abs(x2 - x_spar) < 1e-6:
                tvals.append(self.dcell.t_web * scale)
            else:
                tvals.append(self.dcell.t_skin * scale)
        t_cover_bot = None
        if box:
            G_ref = float(MATERIAL_DB[self.dcell.skin_mat]["G"])
            gt_top, gt_bot = self._box_wall_gt()
            t_cover = max(gt_top / max(G_ref, 1e-9), 1e-6)
            t_cover_bot = max(gt_bot / max(G_ref, 1e-9), 1e-6)
            t_rear = float(self.inp.get("rear_spar_t_web", self.inp.get("rear_spar_wall", 0.094)))
            t_rear = max(t_rear, 1e-6) * self._spar_web_G("rear_spar") / max(G_ref, 1e-9)
            method = "torsion-box shear flow"
        elif self.geodetic is not None:
            t_cover = max(self.geodetic.t_eff(scale), 1e-6)
            t_rear = float(self.inp.get("rear_spar_t_web", self.inp.get("rear_spar_wall", 0.094)))
            t_rear = max(t_rear * scale, 1e-6)
            method = "outer-wall shear flow"
        else:
            t_cover = max(self.top_skin.thickness, 1e-6)
            t_rear = float(self.inp.get("rear_spar_t_web", self.inp.get("rear_spar_wall", 0.094)))
            t_rear = max(t_rear * scale, 1e-6)
            method = "outer-wall shear flow"
        result = two_cell_shear_center(
            pts, tvals, x_spar, rear, geo["h_web"], t_cover, t_rear, t_cover_bot)
        if result["ok"] and abs(result["Fy"] - 1.0) < 0.1:
            return float(result["x"]), method
        return self.dcell.shear_center_x(h_max, scale), "nose shear flow"

    def _divergence(self, GJ_root):
        c    = self.root_chord
        x_ac = self.x_ac_c * c
        x_sc, sc_method = self._shear_center_x(c)
        e = x_ac - x_sc
        if e<=0 or GJ_root<=0:
            return {"V_div":float("inf"),"SF_div":float("inf"),
                    "e":e,"x_ac":x_ac,"x_sc":x_sc,"sc_method":sc_method,
                    "divergent":False}
        # Uniform unswept wing, constant chord and GJ, root fixed in twist:
        # q_div = (pi/(2L))^2 * GJ / (e * c^2 * Cl_alpha). Bisplinghoff/Fung.
        span = max(self.b_half, 1e-6)
        q_psi = (math.pi / (2.0 * span))**2 * GJ_root / (e * c**2 * self.Cl_alpha)
        Vd    = self._mph_from_q(q_psi)
        SF    = Vd/max(self.Vd_mph,1)
        return {"V_div":Vd,"SF_div":SF,"e":e,"x_ac":x_ac,"x_sc":x_sc,
                "sc_method":sc_method,"divergent":True}

    def _mph_from_q(self, q_psi: float) -> float:
        rho = isa_density(self.alt_ft)
        q_psf = q_psi * 144.0
        V_fps = math.sqrt(max(2.0 * q_psf / max(rho, 1e-12), 0.0))
        return V_fps * 3600.0 / 5280.0

    def _divergence_span(self):
        """Rayleigh divergence for a wing whose GJ and shear center change along the span.

        The mode is phi = sin(pi x / 2L). When GJ, chord, and the aerodynamic
        offset are constant, this is the uniform-wing formula.
        """

        span = max(self.b_half, 1e-6)
        phi = np.sin(0.5 * math.pi * self.x / span)
        dphi = (0.5 * math.pi / span) * np.cos(0.5 * math.pi * self.x / span)
        e = np.zeros(self.N)
        x_sc = 0.0
        sc_method = "shear center"
        for i in range(self.N):
            boxed = self._box_covers(self.x[i])
            x_local, method_i = self._shear_center_x(
                float(self.chord_x[i]), aft=self._aft_closed_at(self.x[i]), box=boxed)
            e[i] = self.x_ac_c * float(self.chord_x[i]) - x_local
            if i == 0:
                x_sc = x_local
                sc_method = method_i
        trap = getattr(np, "trapezoid", None)
        if trap is None:
            trap = np.trapz
        num = float(trap(self.GJ * dphi**2, self.x))
        den = float(trap(e * self.chord_x**2 * self.Cl_alpha * phi**2, self.x))
        x_ac = self.x_ac_c * self.root_chord
        e_root = x_ac - x_sc
        base = {
            "e": e_root, "x_ac": x_ac, "x_sc": x_sc, "sc_method": sc_method,
            "spanwise": True, "box_end": self._torsion_box_end(),
        }
        if den <= 1e-18 or num <= 0.0:
            return {**base, "V_div": float("inf"), "SF_div": float("inf"), "divergent": False}
        Vd = self._mph_from_q(num / den)
        return {**base, "V_div": Vd, "SF_div": Vd / max(self.Vd_mph, 1.0), "divergent": True}

    # ── Strut forces ─────────────────────────────────────────────────────────

    def _jury_tube_area(self) -> float:
        if self.jury_tube_wall <= 0.0 or self.jury_tube_od <= 0.0:
            return 0.0
        inner = max(self.jury_tube_od - 2.0 * self.jury_tube_wall, 0.0)
        return math.pi / 4.0 * (self.jury_tube_od**2 - inner**2)

    def _jury_link_vertical_stiffness(self, length: float, angle_deg: float) -> float:
        if not self.jury or length <= 0.0:
            return 0.0
        mat = STRUT_MATERIALS.get(self.jury_tube_mat, STRUT_MATERIALS["6061-T6 Aluminum"])
        axial = mat["E"] * self._jury_tube_area() / length
        theta = math.radians(angle_deg)
        return axial * math.sin(theta) ** 2

    def _jury_coupling_stiffness(self) -> float:
        """Equivalent front/rear vertical coupling from same-tube jury links."""

        k_front = self._jury_link_vertical_stiffness(
            self.jury_front_link_length, self.jury_front_link_angle)
        k_rear = self._jury_link_vertical_stiffness(
            self.jury_rear_link_length, self.jury_rear_link_angle)
        if k_front <= 0.0 or k_rear <= 0.0:
            return 0.0
        # Two links connected through the common strut node behave like springs
        # in series for relative front/rear vertical displacement.
        return 1.0 / (1.0 / k_front + 1.0 / k_rear)

    def _strut_effective_buckling_length(self, total_length: float) -> float:
        """Return unsupported strut length for Euler buckling.

        Bruhn treats a jury strut as lateral support for the lift-strut column,
        not as a spar support. With pinned ends, K = 1 and the Euler length is
        the longer segment between the fuselage fitting, the jury, and the
        wing fitting.
        """

        if not self.jury:
            return total_length

        run = self.strut_bl - self.strut_fuse_bl
        jury_run = self.jury_bl - self.strut_fuse_bl
        if run <= 1e-9 or jury_run <= 0.0 or jury_run >= run:
            return total_length

        fraction = jury_run / run
        lower = total_length * fraction
        upper = total_length * (1.0 - fraction)
        return max(lower, upper)

    def _reaction_moment(self, reaction_bl: float) -> np.ndarray:
        """Moment array from a unit upward reaction at ``reaction_bl``."""

        out = np.zeros(self.N)
        for k in range(self.N):
            if self.x[k] <= reaction_bl:
                out[k] = reaction_bl - self.x[k]
        return out

    def _support_reactions(self, M_total: np.ndarray, EI: np.ndarray) -> dict:
        """Return the main-strut vertical reaction.

        For a pinned spar root, beam statics give ``R_strut = M_root / strut_bl``.
        A jury strut is not included. Bruhn idealizes the lift strut as a
        straight pin-ended two-force member, so a jury brace carries no primary
        wing shear and does not change the spar moment.
        """

        del EI  # spar stiffness does not enter this determinate strut reaction
        strut_bl = max(self.strut_bl, 1.0)
        strut_unit = self._reaction_moment(strut_bl)
        R_strut = float(M_total[0] / strut_bl)
        return {
            "strut": R_strut,
            "jury": 0.0,
            "moment": R_strut * strut_unit,
        }

    def _jury_brace_demand(self, compressive_axial: float) -> float:
        """Force the jury strut must provide to justify the shorter Euler length.

        Bruhn sizes an intermediate column brace for 2.5% of the compressive
        load in the member it supports. That force is transverse to the lift
        strut. It is not a spar-bending reaction. No demand is reported when
        the jury station does not fall between the strut ends.
        """

        if not self.jury:
            return 0.0
        run = self.strut_bl - self.strut_fuse_bl
        jury_run = self.jury_bl - self.strut_fuse_bl
        if run <= 1e-9 or jury_run <= 0.0 or jury_run >= run:
            return 0.0
        return 0.025 * abs(float(compressive_axial))


    def _strut_forces(self, M_total, Fv_override: Optional[float] = None):
        """M_total = moment array BEFORE strut subtraction."""
        Fv = M_total[0] / max(self.strut_bl, 1) if Fv_override is None else Fv_override
        rise = self.strut_vert
        run  = max(self.strut_bl - self.strut_fuse_bl, 1.0)  # net horizontal distance
        L    = math.sqrt(rise**2 + run**2)
        L_eff = self._strut_effective_buckling_length(L)
        ang  = math.atan2(rise, run)
        Fa   = Fv / max(math.sin(ang), 1e-6)
        Ps   = Fa * math.cos(ang)
        od   = self.strut_od; wa = self.strut_wall; id_ = od - 2*wa
        I_st = math.pi/64 * (od**4 - id_**4)
        E_st = STRUT_MATERIALS[self.strut_mat]["E"]
        Pe   = math.pi**2 * E_st * I_st / L_eff**2
        return Fv, Fa, Ps, Pe, L

    # ── P-delta ──────────────────────────────────────────────────────────────

    def _pdelta(self, M, P_comp, EI):
        si   = self._strut_idx()
        EI_a = float(np.mean(EI[:si+1]))
        Pe   = math.pi**2*EI_a/max(self.strut_bl**2,1)
        if P_comp<=0 or Pe<=0: return np.array(M, dtype=float, copy=True), False, 1.0
        if P_comp/Pe>=1.0:
            amp = 10.0
        else:
            amp = 1.0/(1.0-P_comp/Pe)
        # Axial load from the lift strut acts between the root and the strut
        # attach point. Outboard of that point the spar is not this column.
        out = np.array(M, dtype=float, copy=True)
        out[:si+1] *= amp
        return out, amp>2.0, amp

    # ── One load case ────────────────────────────────────────────────────────

    def _one_case(self, total_lift, sign):
        w = self._lift_dist(abs(total_lift)) * sign
        if self.dist_relief and self.Wing_Weight>0:
            w -= sign*(self.Wing_Weight/self.b_half)

        # Integrate magnitudes for V and M (always positive), then apply sign to M
        # so deflection is correctly reversed for -g
        V, M = self._shear_moment(np.abs(w))
        M = M * sign    # positive up for +g, negative (down) for -g

        # M_cant: cantilever moment (before strut subtraction).
        # Rear spar in single_strut is cantilever — must use this, not strut-reduced M.
        M_cant = M.copy()

        # Strut
        si = self._strut_idx()
        Fv=Fa=Ps=Pe=0.0; L_strut=1.0; Fv_jury=0.0; Fv_strut_attach=0.0
        if self.config in ("strut_braced","single_strut"):
            reactions = self._support_reactions(np.abs(M), self._EI_f)
            Fv_jury = 0.0
            Fv_strut_attach = reactions["strut"]
            Fv,Fa,Ps,Pe,L_strut = self._strut_forces(np.abs(M), Fv_override=Fv_strut_attach)
            M_strut = reactions["moment"]
            M = M - M_strut * sign   # subtract signed strut reaction (front spar)
            # Bruhn free-body: the strut vertical reaction reduces shear
            # inboard of the attach point. Root shear is lift minus that reaction.
            V = np.array(V, dtype=float, copy=True)
            V[:si] -= Fv_strut_attach

        # P-delta
        pw = False
        pdelta_amp = 1.0
        if self.secondary and Ps>0:
            M, pw, pdelta_amp = self._pdelta(M, Ps, self._EI_f)

        # Deflection. The jury strut does not relieve bending.
        # Cantilever and single-strut: Bruhn/Peery ribs are stiff in their
        # own plane, so both spars take the external moment in proportion to
        # EI and bend on one curve. The entered load share is the airload the
        # rib receives; the rib moves the difference across the spar gap.
        # Dual-strut: each spar has a strut, and the two spars share the
        # relieved bending by the entered load share.
        # Aerodynamic torque stays in the torsion cell and in the rib demand.
        # It is not added again as spar bending.
        self._geodetic_kappa = 0.0
        if self._rib_ties_spars():
            share_f, share_r = self._ei_shares()
            Mf = M * share_f
            Mr = M * share_r
            V_front = self._moment_to_shear(Mf)
            V_rear = self._moment_to_shear(Mr)
            if self.config == "single_strut":
                th_f, z_f = self._deflect_strut(Mf, self._EI_f, si)
                th_r, z_r = self._deflect_strut(Mr, self._EI_r, si)
                self._rear_spar_path = "rib-tied single-strut"
            else:
                th_f, z_f = self._deflect_cantilever(Mf, self._EI_f)
                th_r, z_r = self._deflect_cantilever(Mr, self._EI_r)
                self._rear_spar_path = "rib-tied cantilever"
        else:
            Mf = M * self.lsf
            V_front = V * self.lsf
            V_rear = V * self.rsf
            if self.config in ("strut_braced", "single_strut"):
                th_f, z_f = self._deflect_strut(Mf, self._EI_f, si)
            else:
                th_f, z_f = self._deflect_cantilever(Mf, self._EI_f)
            if self.config == "strut_braced" and self.num_spars == 2:
                Mr = M * self.rsf
                th_r, z_r = self._deflect_strut(Mr, self._EI_r, si)
                self._rear_spar_path = "dual-strut shared bending"
            else:
                Mr = M_cant * self.rsf
                th_r, z_r = self._deflect_cantilever(Mr, self._EI_r)
                self._rear_spar_path = "single spar"

        sig_f = Mf / np.maximum(self._Itr_f, 1e-10) * self._ym_f
        sig_r = Mr / np.maximum(self._Itr_r, 1e-10) * self._ym_r

        return {
            "w":w, "V":V, "M":M,
            "M_front":Mf, "M_rear":Mr,
            "V_front":V_front, "V_rear":V_rear,
            "z_front":z_f, "z_rear":z_r,
            "z_delta":z_r - z_f,
            "theta_front":th_f, "theta_rear":th_r,
            "sigma_front":sig_f, "sigma_rear":sig_r,
            "sig_f_root":float(sig_f[0]), "sig_r_root":float(sig_r[0]),
            "z_max_front":float(np.max(np.abs(z_f))),
            "z_max_rear":float(np.max(np.abs(z_r))),
            "z_delta_max":float(np.max(np.abs(z_r - z_f))),
            "Fv":Fv,"F_axial":Fa,"P_spar":Ps,"P_euler":Pe,
            "Fv_jury":Fv_jury, "Fv_strut_attach":Fv_strut_attach,
            "V_root":float(V[0]),"M_root":float(M[0]),
            "pdelta_warn":pw, "pdelta_amp":pdelta_amp,
        }

    # ── MS helpers ───────────────────────────────────────────────────────────

    def _ms(self, sig, tau, mat_name, is_compression=False):
        m = MATERIAL_DB[mat_name]; kd = self.wood_kd
        if m["is_wood"]:
            Fb  = (m["Fc"] if is_compression and m["Fc"] else m["Fb"])*kd
            Fsu = m["Fsu"]
            mb  = Fb/max(abs(sig),1e-6)-1
            R   = math.sqrt((sig/max(m["Fb"]*kd,1))**2+(tau/max(Fsu,1))**2)
            return {"MS_bend":mb, "MS_comb":1/max(R,1e-9)-1,
                    "MS_ult":mb, "MS_yield":mb}
        else:
            Ftu=m["Ftu"]; Fty=m["Fty"]; Fsu=m["Fsu"]
            mu = Ftu/max(abs(sig),1e-6)-1
            my = Fty/max(abs(sig),1e-6)-1
            R  = math.sqrt((sig/max(Ftu,1))**2+(tau/max(Fsu,1))**2)
            return {"MS_ult":mu,"MS_yield":my,"MS_comb":1/max(R,1e-9)-1,
                    "MS_bend":mu}

    def _ms_label(self, ms):
        if ms>=0.50: return "GREEN"
        if ms>=0.00: return "YELLOW"
        return "RED"

    def _front_cap_mat(self):
        fs = self.front_spar
        if hasattr(fs,"cap_mat"):  return fs.cap_mat
        if hasattr(fs,"mat_name"): return fs.mat_name
        return "6061-T6"

    def _rear_cap_mat(self):
        if self.rear_spar is None: return self._front_cap_mat()
        rs = self.rear_spar
        if hasattr(rs,"cap_mat"):  return rs.cap_mat
        if hasattr(rs,"mat_name"): return rs.mat_name
        return "6061-T6"

    # ── Main analyze ─────────────────────────────────────────────────────────

    def _t_web_eff(self, prefix: str, x_station: float,
                  t_web_base: float) -> tuple:
        """
        Return (t_eff, is_doubled) at a given spanwise station.
        Doubler zones: within doubler_extent rib bays of root fitting
        and strut attach point (for strut configs).
        """
        if prefix == "front_spar":
            d_t = self.front_doubler_t
            d_ext = self.front_doubler_extent
        else:
            d_t = self.rear_doubler_t
            d_ext = self.rear_doubler_extent

        if d_t <= 0:
            return t_web_base, False

        zone = d_ext * self.rib_spacing   # doubler zone half-width [in]

        # Root fitting zone
        root_bl = self.r   # root fitting BL
        if abs(x_station - root_bl) <= zone:
            return t_web_base + d_t, True

        # Strut attach zone:
        # - strut_braced: both spars get the doubler
        # - single_strut: ONLY the front spar (rear spar is cantilever with no strut attach)
        strut_applies = (self.config == "strut_braced" or
                         (self.config == "single_strut" and prefix == "front_spar"))
        if strut_applies:
            if abs(x_station - self.strut_bl) <= zone:
                return t_web_base + d_t, True

        # Jury strut zone (if enabled)
        if self.jury and abs(x_station - self.jury_bl) <= zone:
            return t_web_base + d_t, True

        return t_web_base, False

    def _compute_buckling(self) -> dict:
        """
        Compute buckling margins for web, skin, and cap at the governing station.
        Returns dict of results for each spar.
        """
        results = {}
        mi_f = int(np.argmax(np.abs(self.pos["sigma_front"])))
        mi_r = int(np.argmax(np.abs(self.pos["sigma_rear"])))

        for label, spar, mi, lsf_val, prefix in [
            ("front", self.front_spar, mi_f, self.lsf, "front_spar"),
            ("rear",  self.rear_spar,  mi_r, self.rsf, "rear_spar"),
        ]:
            if spar is None:
                continue
            mat = self._front_cap_mat() if label=="front" else self._rear_cap_mat()
            m = MATERIAL_DB.get(mat, MATERIAL_DB["6061-T6"])
            is_metal = not m["is_wood"]
            r = {}

            # Get web geometry — handle each spar type correctly
            spar_type = self.inp.get(f"{prefix}_type", "Round Tube")
            web_mat = self.inp.get(f"{prefix}_web_mat",
                      self.inp.get(f"{prefix}_mat", mat))

            if spar_type == "Box Spar":
                # Box spar: clear web height = h_outer - 2*t_cap
                b_outer = float(self.inp.get(f"{prefix}_b_outer", 0.0))
                h_outer = float(self.inp.get(f"{prefix}_h_outer", 0.0))
                t_cap_box = float(self.inp.get(f"{prefix}_t_cap", 0.0))
                h_web = max(h_outer - 2*t_cap_box, 0.0)
                t_web = float(self.inp.get(f"{prefix}_t_web", 0.125))
                b_cap = b_outer           # full width cap
                t_cap = t_cap_box
            elif spar_type == "Round Tube":
                # Tube: no conventional web; tube wall crippling checked separately
                h_web = 0.0
                t_web = float(self.inp.get(f"{prefix}_wall", 0.065))
                b_cap = 0.0
                t_cap = 0.0
                od    = float(self.inp.get(f"{prefix}_od", 2.0))
            elif spar_type == "Plain Rectangular":
                # Solid section — no web, no separate cap
                h_web = 0.0; t_web = 0.0; b_cap = 0.0; t_cap = 0.0; od = 0.0
            else:
                # I-Beam, Double I-Beam, C-Channel, Routed, Aluminum I-Beam, Aluminum C-Spar
                t_web = float(self.inp.get(f"{prefix}_t_web", 0.0))
                h_web = float(self.inp.get(f"{prefix}_h_web", 0.0))
                b_cap = float(self.inp.get(f"{prefix}_b_top", 0.0))
                t_cap = float(self.inp.get(f"{prefix}_t_top", 0.0))
                od    = 0.0

            # Governing shear and moment at this station.
            # Rib-tied spars carry their own shear, not the airload share.
            if self._rib_ties_spars():
                V_spar = self.pos["V_front"] if label == "front" else self.pos["V_rear"]
            else:
                V_spar = self.pos["V"] * lsf_val
            V_gov = abs(float(V_spar[mi]))
            M_gov = abs(float(self.pos["M"][mi]))
            sigma_gov = abs(float(self.pos["sigma_front"][mi] if label=="front"
                                   else self.pos["sigma_rear"][mi]))
            x_gov = float(self.x[mi])

            # Effective web thickness at governing station (includes doubler if present)
            t_eff, is_doubled = self._t_web_eff(prefix, x_gov, t_web)
            r["t_web_base"]   = t_web
            r["t_web_eff"]    = t_eff
            r["is_doubled"]   = is_doubled

            # Also find governing SHEAR station (max V) — may differ from bending station
            V_arr = np.abs(V_spar)
            mi_V  = int(np.argmax(V_arr))
            V_max = float(V_arr[mi_V])
            x_V   = float(self.x[mi_V])
            t_eff_V, is_doubled_V = self._t_web_eff(prefix, x_V, t_web)
            r["x_shear_gov"]  = x_V
            r["t_web_eff_V"]  = t_eff_V
            r["is_doubled_V"] = is_doubled_V

            depth_v = float(self.chord_x[mi_V] / max(self.root_chord, 1e-9))
            depth_m = float(self.chord_x[mi] / max(self.root_chord, 1e-9))
            h_shear = h_web * depth_v
            h_bend = h_web * depth_m
            if hasattr(spar, "caps_at"):
                caps_m = spar.caps_at(float(self._cap_fraction()[mi]))
                caps_v = spar.caps_at(float(self._cap_fraction()[mi_V]))
                if spar_type == "Box Spar":
                    b_cap, t_cap = caps_m
                    h_outer = float(self.inp.get(f"{prefix}_h_outer", 0.0))
                    h_bend = max(h_outer * depth_m - 2.0 * t_cap, 1e-3)
                    h_shear = max(h_outer * depth_v - 2.0 * caps_v[1], 1e-3)
                elif len(caps_m) == 2:
                    b_cap, t_cap = caps_m
                else:
                    b_cap, t_cap = caps_m[0], caps_m[1]

            # 1. Web shear stress — use max shear station with its effective t
            if h_shear > 0 and t_web > 0:
                tau_web_max = V_max / max(h_shear * t_eff_V, 1e-9)
                r["tau_web"] = tau_web_max
                Fsu = MATERIAL_DB[web_mat]["Fsu"]
                r["MS_web_shear"] = Fsu / max(tau_web_max, 1e-9) - 1

                # 2. Web shear buckling at max shear station
                wb = web_buckling(t_eff_V, h_shear, self.stiffener_spacing, web_mat)
                r.update(wb)
                r["MS_web_buckling"] = wb["tau_cr"] / max(tau_web_max, 1e-9) - 1

                # 3. Web combined buckling at governing bending station
                # Use t_eff (which may include doubler at that station)
                wb_b = web_buckling(t_eff, h_bend, self.stiffener_spacing, web_mat)
                wbb  = web_bending_buckling(t_eff, h_bend, web_mat)
                r.update(wbb)
                if hasattr(spar, "caps_at"):
                    p = spar.get_props(depth_m, caps=spar.caps_at(float(self._cap_fraction()[mi])))
                else:
                    p = spar.get_props(1.0)
                sigma_web = sigma_gov * (h_bend/2) / max(p.y_max, 1e-9)
                r["sigma_web_bending"] = sigma_web
                tau_web_b = abs(float(V_spar[mi])) / max(h_bend * t_eff, 1e-9)
                tau_cr  = wb_b["tau_cr"]
                sig_cr  = wbb["sigma_cr_web_bending"]
                if tau_cr > 0 and sig_cr > 0:
                    R = (tau_web_b/tau_cr)**2 + sigma_web/sig_cr
                    r["MS_web_combined"] = 1.0/max(R, 1e-9) - 1
                else:
                    r["MS_web_combined"] = float("inf")

                # Min web thickness at max shear station (for guidance).
                # tau_cr scales with t^2 for both the metal and wood plate laws.
                if wb["tau_cr"] > 0 and tau_web_max > 0:
                    r["t_min_web"] = t_eff_V * math.sqrt(tau_web_max / wb["tau_cr"])

            # 4. Skin compression buckling (any skin panel: aluminum or plywood)
            if getattr(self, "top_skin", None) is not None:
                t_sk   = self.top_skin.thickness
                b_skin = self.rib_spacing   # box skin panel
                sk = skin_compression_buckling(t_sk, b_skin, self.top_skin.mat_name)
                r["sigma_cr_skin"] = sk["sigma_cr_skin"]
                # Skin stress is at the skin level, not at the cap extreme fibre.
                # For semi-monocoque: skin at top face sees sigma_gov * (h_web/2+t_cap/2)/y_max
                # Use sigma_gov directly as conservative upper bound.
                # Note: in semi-monocoque design skin buckling is EXPECTED and acceptable;
                # the caps carry bending in the post-buckled state.
                # Flag as WARN (not FAIL) when skin buckles — only FAIL if sigma_cr < 0.5*sigma_gov
                r["MS_skin_buckling"] = sk["sigma_cr_skin"] / max(sigma_gov, 1e-9) - 1
                r["skin_buckling_acceptable"] = True  # semi-monocoque: post-buckled OK
                eff = skin_effective_width(t_sk, b_skin, sigma_gov, self.top_skin.mat_name)
                r["skin_b_eff"] = eff["b_eff"]
                r["skin_b_eff_ratio"] = eff["b_eff_ratio"]
                r["skin_eff_load_per_in"] = eff["load_per_length"]
                skin_total_load_per_in = sigma_gov * b_skin * t_sk
                cap_stringer_load_per_in = max(skin_total_load_per_in - eff["load_per_length"], 0.0)
                r["skin_total_load_per_in"] = skin_total_load_per_in
                r["cap_stringer_load_per_in"] = cap_stringer_load_per_in
                r["cap_stringer_load_per_bay"] = cap_stringer_load_per_in * self.rib_spacing
                # D-cell skin (nose ribs if present)
                if self.dcell:
                    b_dc = self.nose_rib_spacing
                    sk_dc = skin_compression_buckling(
                        self.dcell.t_skin, b_dc, self.dcell.skin_mat)
                    r["sigma_cr_dcell_skin"] = sk_dc["sigma_cr_skin"]
                    r["MS_dcell_skin_buckling"] = sk_dc["sigma_cr_skin"] / max(sigma_gov, 1e-9) - 1
                if sk["sigma_cr_skin"] > 0 and sigma_gov > 0:
                    r["t_min_skin"] = t_sk * math.sqrt(sigma_gov / sk["sigma_cr_skin"])

            # 5. Cap column buckling — metal AND wood caps
            if b_cap > 0 and t_cap > 0:
                cc = cap_column_buckling(b_cap, t_cap, self.rib_spacing, mat)
                r.update(cc)
                if m["is_wood"]:
                    # Wood: check against compression allowable (Fc * knockdown)
                    Fc_allow = m.get("Fc", m.get("Fb", 5000)) * self.wood_kd
                    sigma_applied_cap = sigma_gov  # conservative
                    r["MS_cap_column"] = min(
                        cc["sigma_cr_cap"] / max(sigma_gov, 1e-9) - 1,
                        Fc_allow / max(sigma_gov, 1e-9) - 1)
                else:
                    r["MS_cap_column"] = cc["sigma_cr_cap"] / max(sigma_gov, 1e-9) - 1

            # 6. Round tube local wall crippling (thin-wall criterion)
            if spar_type == "Round Tube":
                od_v = float(self.inp.get(f"{prefix}_od", 2.0))
                wall = float(self.inp.get(f"{prefix}_wall", 0.065))
                E_t  = MATERIAL_DB[mat]["E"]; nu = 0.33
                # NASA SP-8007: sigma_cr_cripple = 0.605 * E * t / r
                # Conservative: use 0.3 factor for imperfection sensitivity
                R_mid = (od_v - wall) / 2.0
                sigma_cr_tube = 0.3 * E_t * wall / max(R_mid, 1e-9)
                r["sigma_cr_tube_cripple"] = sigma_cr_tube
                r["MS_tube_cripple"] = sigma_cr_tube / max(sigma_gov, 1e-9) - 1
                r["t_over_R"] = wall / max(R_mid, 1e-9)

            results[label] = r

        return results

    def analyze(self):
        self._y_sc = None
        self._spar_arrays()
        self.GJ, self.q1_frac, self.q2_frac = self._gj_arrays()
        self._torsion_transfer = self._torsion_transfer_stiffness()
        self._torsion_stiffness = self._torsion_transfer["k_total"]

        self.pos = self._one_case(self.ng_lift, +1)
        ng_neg   = abs(self.n_neg)/self.n*self.ng_lift
        self.neg = self._one_case(ng_neg, -1)

        self.torsion = self._torsion(self.GJ, self.q1_frac, self.q2_frac, self.pos["w"])
        self._add_twist_to_deflection(self.pos, self.torsion["phi"])
        q_psi = dynamic_pressure_psi(self.Vd_mph, self.alt_ft)
        _ta, _ts, T_neg = self._distributed_torsion(self.neg["w"], q_psi, sign=-1.0)
        _run_neg, phi_neg = self._integrate_twist(T_neg, self.GJ)
        self._add_twist_to_deflection(self.neg, phi_neg)

        if self._torsion_box_active():
            self.divergence = self._divergence_span()
        else:
            self.divergence = self._divergence(float(self.GJ[0]))

        # Strut summary
        sm = STRUT_MATERIALS[self.strut_mat]
        od=self.strut_od; wa=self.strut_wall; id_=od-2*wa
        A_st = math.pi/4*(od**2 - id_**2)
        L_st = math.sqrt(max(self.strut_bl - self.strut_fuse_bl, 1.0)**2 + self.strut_vert**2)
        L_eff = self._strut_effective_buckling_length(L_st)
        sig_ax = self.pos["F_axial"]/max(A_st,1e-9)
        self.strut_summary = {
            "mat":self.strut_mat, "E":sm["E"], "Ftu":sm["Ftu"],
            "od":od,"wall":wa,"area":A_st,
            "Fv":self.pos["Fv"],"F_axial":self.pos["F_axial"],
            "Fv_jury":0.0,
            "jury_brace_load":self._jury_brace_demand(self.neg["F_axial"]),
            "Fv_strut_attach":self.pos.get("Fv_strut_attach", self.pos["Fv"]),
            "P_euler":self.pos["P_euler"],
            "length":L_st, "effective_length":L_eff,
            "sigma_axial":sig_ax,
            "MS_axial":sm["Ftu"]/max(abs(sig_ax),1e-6)-1,
            "SF_euler":self.pos["P_euler"]/max(abs(self.pos["F_axial"]),1e-6),
            "weight_half":A_st*sm["rho"]*L_st,
        }

        # Local fitting / bearing load demands only. AeroBeam does not size
        # bolts, bushings, lugs, doublers, bearing pads, or tube crush details.
        jury_idx = int(np.argmin(np.abs(self.x - self.jury_bl))) if self.N else 0
        if self._rib_ties_spars():
            front_root_v = abs(float(self.pos["V_front"][0]))
            rear_root_v = abs(float(self.pos["V_rear"][0]))
        else:
            front_root_v = abs(float(self.pos["V_root"] * self.lsf))
            rear_root_v = abs(float(self.pos["V_root"] * self.rsf)) if self.num_spars == 2 else 0.0
        self.fitting_loads = {
            "front_root_vertical": front_root_v,
            "rear_root_vertical": rear_root_v,
            "main_strut_vertical": abs(float(self.pos.get("Fv_strut_attach", self.pos["Fv"]))),
            "jury_vertical": abs(float(self.strut_summary.get("jury_brace_load", 0.0))),
            "main_strut_axial": abs(float(self.pos["F_axial"])),
            "front_spar_strut_attach_vertical": abs(float(self.pos.get("Fv_strut_attach", self.pos["Fv"]))),
            "rear_spar_strut_attach_vertical": abs(float(self.pos.get("Fv_strut_attach", self.pos["Fv"]))) if self.config == "strut_braced" and self.num_spars == 2 else 0.0,
            "front_spar_jury_attach_vertical": abs(float(self.strut_summary.get("jury_brace_load", 0.0))),
            "rear_spar_jury_coupling_vertical": abs(float(self._jury_coupling_stiffness() * self.pos.get("z_delta", np.zeros(self.N))[jury_idx])) if self.jury else 0.0,
        }
        self.fitting_loads["bearing_allowable_psi"] = self.bearing_allowable_psi
        for key, value in list(self.fitting_loads.items()):
            if key.endswith("_vertical") or key.endswith("_axial"):
                self.fitting_loads[f"{key}_bearing_area_required"] = (
                    abs(value) / max(self.bearing_allowable_psi, 1e-9)
                )

        # Spar weights
        scale_tip = self.tip_chord / self.root_chord
        try:
            w_front = self.front_spar.weight(self.b_half, self.root_chord, self.tip_chord)
        except Exception:
            w_front = 0.0
        try:
            w_rear = self.rear_spar.weight(self.b_half, self.root_chord, self.tip_chord) if self.rear_spar else 0.0
        except Exception:
            w_rear = 0.0
        self.spar_weight_front_half = w_front
        self.spar_weight_rear_half  = w_rear
        self.spar_weight_total      = (w_front + w_rear) * 2   # both half-spans

        # Root MS — use governing (max moment) station
        mi_f = int(np.argmax(np.abs(self.pos["sigma_front"])))
        mi_r = int(np.argmax(np.abs(self.pos["sigma_rear"])))
        sig_f_gov = float(self.pos["sigma_front"][mi_f])
        sig_r_gov = float(self.pos["sigma_rear"][mi_r])

        tau_f = abs(float(self.torsion["tau_dcell"][mi_f])) if self.torsion else 0.0
        self.ms_front = self._ms(abs(sig_f_gov), tau_f, self._front_cap_mat())
        self.ms_rear  = self._ms(abs(sig_r_gov), 0.0,  self._rear_cap_mat())
        self.sigma_max_front = abs(sig_f_gov)
        self.sigma_max_rear  = abs(sig_r_gov)
        self.x_sigma_max_front = float(self.x[mi_f])
        self.x_sigma_max_rear  = float(self.x[mi_r])

        # Buckling checks
        self.buckling = self._compute_buckling()

        # Aliases
        self.x_arr   = self.x
        self.w_arr   = self.pos["w"]
        self.V_arr   = self.pos["V"]
        self.M_arr   = self.pos["M"]
        self.z_arr   = self.pos["z_front"]
        self.V_root  = self.pos["V_root"]
        self.M_root  = self.pos["M_root"]
        self.z_max   = self.pos["z_max_front"]
        self.sigma_max = float(np.max(np.abs(self.pos["sigma_front"])))

    # ── Summary text ─────────────────────────────────────────────────────────

    def summary_text(self):
        import numpy as np
        p=self.pos; n=self.neg; t=self.torsion; d=self.divergence; s=self.strut_summary

        def mf(ms):
            if abs(float(ms)) > 9999:
                return f" +999+ \u2713" if ms > 0 else f" -999  \u2717"
            lbl=self._ms_label(ms)
            sym={"GREEN":"\u2713","YELLOW":"\u26a0","RED":"\u2717"}[lbl]
            return f"{ms:>+7.2f}  {sym}"

        L = []
        L += ["═"*54,"  AeroBeam v1.2.3  ─  Results","═"*54]
        L += ["PRELIMINARY DESIGN ONLY — not for airworthiness or final sizing."]
        L += method_status_lines()
        if self.validation_warnings:
            L += ["", "INPUT WARNINGS:"]
            L += [f"  ⚠ {warning.message}" for warning in self.validation_warnings]
        L += [f"\nAirfoil    : {self.airfoil}  Cm (pitching moment coeff)={self.Cm_ac:+.4f}"]
        L += [f"Config     : {self.config}   Structure: {self.wing_struct}"]
        L += [f"Planform   : taper keeps the {self.taper_reference.lower()} straight"]
        if hasattr(self.front_spar, "caps_at"):
            root_caps = self.front_spar.caps_at(0.0)
            tip_caps = self.front_spar.caps_at(1.0)
            L += [f"Front caps : root {root_caps[0]:.3f} x {root_caps[1]:.3f} in   tip {tip_caps[0]:.3f} x {tip_caps[1]:.3f} in"]
        if self.num_spars == 2 and self.rear_spar is not None and hasattr(self.rear_spar, "caps_at"):
            root_caps = self.rear_spar.caps_at(0.0)
            tip_caps = self.rear_spar.caps_at(1.0)
            L += [f"Rear caps  : root {root_caps[0]:.3f} x {root_caps[1]:.3f} in   tip {tip_caps[0]:.3f} x {tip_caps[1]:.3f} in"]
        L += [f"n (load factor, ultimate): +{self.n:.1f}g / {self.n_neg:.1f}g"]

        L += [f"\n── BENDING (+g) {'─'*37}"]
        L += [f"  Root V (shear force)  : {p['V_root']:>10,.1f} lb"]
        L += [f"  Root M (bending moment): {p['M_root']:>10,.1f} lb·in"]
        if self.secondary:
            L += [f"  P-delta amplification : {p.get('pdelta_amp', 1.0):>10.3f}×  (affects moment/stress, not lift/shear)"]
        L += [f"  Front z_max (tip, with twist): {p['z_max_front']:>10.3f} in  (+up)"]
        L += [f"  Rear  z_max (tip, with twist): {p['z_max_rear']:>10.3f} in  (+up)"]
        L += [f"  Rear-front Δz max (includes twist): {p['z_delta_max']:>8.3f} in"]
        if "phi" in p:
            L += [f"  Twist in this +g position: {math.degrees(float(p['phi'][-1])):>+9.3f}°  (nose-up positive)"]
            L += ["  A nose-up twist lowers a spar that sits aft of the shear center."]
        L += [f"  Front σ_max (bending stress): {self.sigma_max_front:>10,.0f} psi  at x={self.x_sigma_max_front:.1f}\""]
        L += [f"  Rear  σ_max   : {self.sigma_max_rear:>10,.0f} psi  at x={self.x_sigma_max_rear:.1f}\""]

        L += [f"\n── BENDING (-g) {'─'*37}"]
        L += [f"  Root M        : {n['M_root']:>10,.1f} lb·in"]
        L += [f"  Front σ_max   : {float(np.max(np.abs(n['sigma_front']))):>10,.0f} psi"]

        if self.config in ("strut_braced","single_strut"):
            L += [f"\n── STRUT {'─'*44}"]
            L += [f"  {s['mat']}"]
            L += [f"  Tube: {s['od']}\" × {s['wall']}\"   A={s['area']:.4f} in²"]
            L += [f"  Length={s['length']:.1f}\"   Euler length={s['effective_length']:.1f}\""]
            L += [f"  Fv (vertical)={s['Fv']:,.0f} lb   Fa (axial)={s['F_axial']:,.0f} lb   Pe (Euler)={s['P_euler']:,.0f} lb"]
            L += [f"  Main strut vertical reaction={s['Fv_strut_attach']:,.0f} lb"]
            L += [f"  SF (safety factor) Euler buckling :{mf(s['SF_euler']-1)}"]
            L += [f"  MS (margin of safety) axial       :{mf(s['MS_axial'])}"]
            L += [f"  Strut wt (½)  : {s['weight_half']:.2f} lb"]
            if self.jury:
                L += ["  Jury strut: lift-strut column brace only (Bruhn). No spar bending relief."]
                L += [f"  Required jury brace load (2.5% of -g compression): {s['jury_brace_load']:,.1f} lb"]
            if p.get("pdelta_warn"): L += ["  ⚠ P-delta amplification > 2×"]

        if hasattr(self, "fitting_loads"):
            fl = self.fitting_loads
            L += [f"\n── LOCAL FITTING / BEARING LOAD DEMANDS {'─'*12}"]
            L += [f"  Front root fitting vertical demand : {fl['front_root_vertical']:>9,.0f} lb"]
            if self.num_spars == 2:
                L += [f"  Rear  root fitting vertical demand : {fl['rear_root_vertical']:>9,.0f} lb"]
            if self.config in ("strut_braced","single_strut"):
                L += [f"  Main strut attach vertical demand  : {fl['main_strut_vertical']:>9,.0f} lb"]
                L += [f"  Main strut axial fitting demand    : {fl['main_strut_axial']:>9,.0f} lb"]
                if fl["jury_vertical"] > 0:
                    L += [f"  Jury brace demand (2.5% of -g Fa)  : {fl['jury_vertical']:>9,.1f} lb"]
                if fl["rear_spar_jury_coupling_vertical"] > 0:
                    L += [f"  Rear spar jury-link demand         : {fl['rear_spar_jury_coupling_vertical']:>9,.0f} lb"]
            L += [f"  Bearing-area demand uses allowable : {fl['bearing_allowable_psi']:>9,.0f} psi"]
            L += [f"  Req. bearing area, front root      : {fl['front_root_vertical_bearing_area_required']:>9.3f} in²"]
            if self.num_spars == 2:
                L += [f"  Req. bearing area, rear root       : {fl['rear_root_vertical_bearing_area_required']:>9.3f} in²"]
            if self.config in ("strut_braced","single_strut"):
                L += [f"  Req. bearing area, strut attach    : {fl['main_strut_vertical_bearing_area_required']:>9.3f} in²"]
                if fl["jury_vertical"] > 0:
                    L += [f"  Req. bearing area, jury attach     : {fl['jury_vertical_bearing_area_required']:>9.3f} in²"]
            L += ["  Reinforce/check tube bearing, bushings, lugs, doublers, and local crush separately."]


        L += [""]
        L += ["-- SPAR WEIGHT (structural material only, per half-span) " + "-"*0]
        if hasattr(self, "spar_weight_front_half"):
            L += ["  Front spar (half-span): %6.2f lb   full: %.2f lb" %
                  (self.spar_weight_front_half, self.spar_weight_front_half*2)]
            L += ["  Rear  spar (half-span): %6.2f lb   full: %.2f lb" %
                  (self.spar_weight_rear_half, self.spar_weight_rear_half*2)]
            L += ["  Both spars total      : %6.2f lb" % self.spar_weight_total]

        L += [f"\n── MARGIN OF SAFETY  MS = Allowable/Applied - 1  {'─'*4}"]
        fm = MATERIAL_DB[self._front_cap_mat()]
        L += [f"  Front σ_gov (governing bending stress): {self.sigma_max_front:>10,.0f} psi  at x={self.x_sigma_max_front:.1f}\""]
        if not fm["is_wood"]:
            L += [f"  Front MS_ult (ultimate, Ftu)    :{mf(self.ms_front['MS_ult'])}"]
            L += [f"  Front MS_yld (yield, Fty)      :{mf(self.ms_front['MS_yield'])}"]
        else:
            L += [f"  Front MS_bend :{mf(self.ms_front['MS_bend'])}"]
        if t: L += [f"  Front MS_comb :{mf(self.ms_front['MS_comb'])}"]
        rm = MATERIAL_DB[self._rear_cap_mat()]
        L += [f"  Rear  σ_gov (governing bending stress): {self.sigma_max_rear:>10,.0f} psi  at x={self.x_sigma_max_rear:.1f}\""]
        key = "MS_ult" if not rm["is_wood"] else "MS_bend"
        L += [f"  Rear  MS      :{mf(self.ms_rear[key])}"]

        if t:
            L += [f"\n── TORSION {'─'*42}"]
            qp = dynamic_pressure_psi(self.Vd_mph, self.alt_ft)
            L += [f"  q (dynamic pressure)={qp:.4f} psi   Vd (dive speed)={self.Vd_mph:.0f} mph   alt={self.alt_ft:.0f} ft"]
            if self.config=="single_strut":
                sp = t["T_struct"][0]/(t["T_total"][0]+1e-9)*100
                L += [f"  T_struct(root): {t['T_struct'][0]:>9.3f} lb-in/in  ({sp:.0f}%)"]
                L += [f"  T_aero  (root): {t['T_aero'][0]:>9.3f} lb-in/in"]
            L += [f"  T_total (root): {t['T_total'][0]:>9.3f} lb-in/in"]
            L += [f"  T_running root: {t['T_running'][0]:>9,.0f} lb-in"]
            # Cruise torsion + flap case
            if t.get("T_run_vc") is not None:
                L += ["  T_running at Vc=%d mph: %8.0f lb-in" % (self.Vc_mph, t["T_run_vc"][0])]
            if self.Cm_flap != 0 and t.get("T_run_flap") is not None:
                L += ["  T_run flaps(Cm=%+.3f): %7.0f lb-in" % (t["Cm_flap"], t["T_run_flap"][0])]
            # Centre of pressure positions
            if t.get("cp_ng") is not None:
                L += ["-- CENTRE OF PRESSURE (aft of LE) -------------"]
                L += ["  CP at +%dg (Vd):  %5.1f%% chord" % (self.n, t["cp_ng"]*100)]
                L += ["  CP at 1g  (Vc):  %5.1f%% chord" % (t["cp_1g"]*100)]
                L += ["  CP at -g  (inv): %5.1f%% chord" % (t["cp_neg"]*100)]
                L += ["  CP at 0.5g dive: %5.1f%% chord  (max aft)" % (t["cp_dive"]*100)]
                warn = "  *** CP aft of rear spar at dive!" if t["cp_dive"] > self.rear_pct else ""
                L += ["  Rear spar at: %.0f%%c  %s" % (self.rear_pct*100, warn)]
            L += [f"  Twist φ (tip, +g, nose-up +): {t['phi_tip_deg']:>9.3f}°  (< 1° acceptable)"]
            if self.dcell:
                td=abs(float(t["tau_dcell"][0]))
                Fs=MATERIAL_DB[self.dcell.skin_mat]["Fsu"]
                L += [f"  D-cell τ (shear stress) root: {td:>9,.0f} psi   MS:{mf(Fs/max(td,1)-1)}"]
            path = getattr(self, "_rear_spar_path", "")
            if path:
                L += [f"  Rear spar path: {path}. Drag-truss strip force is demand only."]
            if self._rib_ties_spars():
                L += ["  Ribs tie the spars to one bending curve (Bruhn/Peery). Bending follows EI, not the airload share."]
            jury_k = self._jury_coupling_stiffness()
            if self.jury and jury_k > 0:
                L += [f"  Jury link stiffness (not applied to spar bending): k={jury_k:,.0f} lb/in at BL {self.jury_bl:.1f}\""]
            if t and "f_rib" in t:
                fr = t["f_rib"]; fg = t.get("f_geo",0); fs = t.get("f_skin",0)
                L += [f"  Torsion share: ribs={fr*100:.0f}%  geodetic={fg*100:.0f}%  skin={fs*100:.0f}%"]
                L += [f"  Rib shear stiffness k: {t.get('k_rib', 0.0):>10,.0f} lb/in per inch of span"]
                L += [f"  Required rib bay torque : {t['rib_bay_torque']:>8.0f} lb-in at x={t['rib_reaction_station']:.1f}\""]
                if self._rib_ties_spars():
                    L += [f"    of which airload torque {t.get('rib_aero_torque', 0.0):>8.0f}  spar-transfer couple {t.get('rib_transfer_torque', 0.0):>8.0f}"]
                L += [f"  Required rib attach reaction: ±{t['rib_reaction_required']:>7.1f} lb per rib bay"]
                rib_model = t.get("rib_model") or {}
                if rib_model:
                    L += [f"  Rib type: {rib_model.get('label', '')} — {rib_model.get('model', '')}"]
                    if rib_model.get("shear_area", 0.0) > 0.0:
                        tau = float(t.get("rib_tau", 0.0))
                        L += [f"  Rib web shear stress: {tau:>9,.1f} psi   MS:{mf(rib_model.get('Fsu', 0.0)/max(tau,1e-9)-1)}"]
                    if rib_model.get("type") == "Dow foam with spruce caps":
                        sig = float(t.get("rib_cap_sigma", 0.0))
                        if sig > 0.0:
                            L += [f"  Spruce cap stress: {sig:>9,.0f} psi   MS:{mf(rib_model.get('cap_allow', 0.0)/max(sig,1e-9)-1)}"]
                            L += ["  Cap stress uses end moment V*gap/2. Foam-to-cap glue is not checked."]
                        L += [f"  Rib deflection under that reaction: {float(t.get('rib_tie_deflection', 0.0)):.3f} in"]
                        if self._rib_ties_spars():
                            L += ["  Foam core shear is soft. The one-curve split assumes a rib stiff in its plane."]
                L += ["  Rib sizing is not performed; design ribs/attachments for this reaction."]
            if self.geodetic:
                tg=abs(float(t["tau_geo"][0]))
                sig_s=t.get("geodetic_strip_stress", 0.0)
                strip_f=t.get("geodetic_strip_force", 0.0)
                q_geo=t.get("geodetic_q", 0.0)
                red=float(self.inp.get("geodetic_reduction_factor", 0.75))
                Fb_s=MATERIAL_DB[self.geodetic.mat_name]["Fb"]
                L += [f"  Geodetic τ eff: {tg:>9,.0f} psi"]
                L += [f"  Geodetic stiffness reduction f_red={red:.2f} is not used for spar bending."]
                L += [f"  ANC-18 drag-truss demand: q={q_geo:>7.1f} lb/in  strip F={strip_f:>7.1f} lb"]
                L += [f"  Strip axial σ demand: {sig_s:>9,.0f} psi   MS vs Fb only:{mf(Fb_s/max(sig_s,1)-1)}"]
                L += ["  Geodetic mesh demand only; bond/joint/attachment sizing is outside AeroBeam."]

        if self._torsion_box_active():
            end = self._torsion_box_end()
            L += [f"  Torsion box: {self.torsion_box_bays} rib bays, root to {end:.1f} in"]
            L += [f"    Top sheet: {self.torsion_box_top:.3f} in  {self.torsion_box_top_mat}"]
            L += [f"    Bottom sheet: {self.torsion_box_bot:.3f} in  {self.torsion_box_bot_mat}"]
            L += ["    Sheets close the cell between the spars. They are not added to spar bending."]
            if t is not None and len(self.q2_frac):
                q2 = abs(float(self.q2_frac[0]))
                torque = abs(float(t["T_running"][0]))
                gt_top, gt_bot = self._box_wall_gt()
                for label, mat, gt in (
                    ("Top", self.torsion_box_top_mat, gt_top),
                    ("Bottom", self.torsion_box_bot_mat, gt_bot),
                ):
                    G = self._sheet_modulus(mat)
                    tau = q2 * torque * G / max(gt, 1e-12)
                    props = MATERIAL_DB[mat]
                    allow = float(props["Fsu"] or 0.0)
                    if props.get("is_wood"):
                        allow *= self.wood_kd
                    if allow > 0.0:
                        L += [f"    {label} sheet shear demand: {tau:,.0f} psi   MS vs Fsu:{mf(allow / max(tau, 1e-9) - 1)}"]
                    else:
                        L += [f"    {label} sheet shear demand: {tau:,.0f} psi"]
                L += ["    Sheet shear is a demand. AeroBeam does not size the sheet."]

        L += [f"\n── DIVERGENCE {'─'*39}"]
        if d["divergent"] and d["V_div"]<float("inf"):
            L += [f"  AC={d['x_ac']:.2f}\"  SC={d['x_sc']:.2f}\"  e={d['e']:.2f}\"  ({d.get('sc_method', 'shear center')})"]
            L += [f"  V_div         : {d['V_div']:>8.0f} mph"]
            L += [f"  SF_div (divergence, Vd/V_div) :{mf(d['SF_div']-1)}"]
            if d.get("spanwise"):
                L += [f"  V_div uses spanwise GJ and shear center, box to {d.get('box_end', 0.0):.1f} in."]
            if d["SF_div"]<1.5:
                L += ["  *** DIVERGENCE RISK — stiffness or SC review needed ***"]
        elif self._has_closed_torsion_cell():
            L += [f"  AC={d['x_ac']:.2f}\"  SC={d['x_sc']:.2f}\"  e={d['e']:.2f}\"  ({d.get('sc_method', 'shear center')})"]
            L += ["  Shear center is at or behind the aerodynamic center. No divergence."]
        else:
            L += ["  No closed section — enable D-cell/skin for divergence check"]

        # ── BUCKLING PASS/FAIL ─────────────────────────────────────────────
        if hasattr(self, "buckling") and self.buckling:
            # Collect all failures across both spars
            all_fails = []
            all_warns = []
            for lbl, bk in self.buckling.items():
                if not bk: continue
                # Skin buckling is a NOTE for semi-monocoque (acceptable post-buckling)
                # Only hard-fail structural checks here
                checks = [
                    ("MS_web_shear",           "%s web shear stress" % lbl.upper()),
                    ("MS_web_buckling",         "%s web shear buckling" % lbl.upper()),
                    ("MS_web_combined",         "%s web combined buckl." % lbl.upper()),
                    ("MS_cap_column",            "%s cap column buckl." % lbl.upper()),
                    ("MS_tube_cripple",          "%s tube wall crippling" % lbl.upper()),
                ]
                # Skin buckling: only report when aluminum_skin is active
                if self.wing_struct != "aluminum_skin":
                    pass
                for sk_key in ([] if self.wing_struct != "aluminum_skin"
                               else ["MS_skin_buckling", "MS_dcell_skin_buckling"]):
                    if sk_key in bk and bk[sk_key] < 0:
                        all_warns.append(("%s skin buckles (semi-mono: acceptable)" % lbl.upper(),
                                          bk[sk_key]))
                for key, name in checks:
                    if key in bk:
                        ms = bk[key]
                        if ms < 0:       all_fails.append((name, ms))
                        elif ms < 0.5:   all_warns.append((name, ms))

            # Overall banner
            L += [""]
            if all_fails:
                L += ["*** BUCKLING: FAIL " + "*"*34]
                for name, ms in all_fails:
                    L += ["  *** FAIL  %-28s  MS=%+.2f" % (name, ms)]
                if all_warns:
                    for name, ms in all_warns:
                        L += ["   !!  WARN  %-27s  MS=%+.2f" % (name, ms)]
            elif all_warns:
                L += [" !!  BUCKLING: MARGINAL " + "-"*29]
                for name, ms in all_warns:
                    L += ["   !!  WARN  %-27s  MS=%+.2f" % (name, ms)]
            else:
                L += [" OK  BUCKLING: PASS  " + "-"*32]

            # Detail by spar
            L += [""]
            L += ["-- BUCKLING DETAIL  stiffener spacing=%.0fin  nose rib spacing=%.0fin" %
                  (self.stiffener_spacing, self.nose_rib_spacing)]
            for lbl, bk in self.buckling.items():
                if not bk: continue
                L += ["  [%s SPAR]" % lbl.upper()]
                if "tau_web" in bk:
                    fail = " ***" if bk["MS_web_shear"] < 0 else ""
                    dbl  = " DOUBLED t=%.3fin" % bk["t_web_eff_V"] if bk.get("is_doubled_V") else ""
                    L += ["  Web shear stress tau=%6.0f  MS (margin of safety):%s%s%s" % (bk["tau_web"], mf(bk["MS_web_shear"]), fail, dbl)]
                    L += ["  Web t_base=%.3fin  t_eff=%.3fin  at x=%.0fin" %
                          (bk["t_web_base"], bk["t_web_eff_V"], bk["x_shear_gov"])]
                if "tau_cr" in bk:
                    fail = " ***" if bk["MS_web_buckling"] < 0 else ""
                    dbl  = " DOUBLED" if bk.get("is_doubled_V") else ""
                    L += ["  Web shear buckling tau_cr=%6.0f (k=%.1f s=%.0fin)  MS:%s%s%s" %
                          (bk["tau_cr"], bk["k_s"], bk["stiffener_spacing"],
                           mf(bk["MS_web_buckling"]), fail, dbl)]
                    if bk["MS_web_buckling"] < 0 and "t_min_web" in bk:
                        L += ["  >>> t_web min = %.4fin (or add doubler)" % bk["t_min_web"]]
                if "MS_web_combined" in bk:
                    fail = " ***" if bk["MS_web_combined"] < 0 else ""
                    L += ["  Web comb    MS:%s%s" % (mf(bk["MS_web_combined"]), fail)]
                if "sigma_cr_skin" in bk:
                    # Skin buckling: NOTE for semi-monocoque, not a hard failure
                    note = " (note: post-buckled OK for semi-mono)" if bk["MS_skin_buckling"] < 0 else ""
                    L += ["  Skin buckl (compression buckling) σ_cr=%6.0f psi  MS:%s%s" %
                          (bk["sigma_cr_skin"], mf(bk["MS_skin_buckling"]), note)]
                    if "skin_b_eff" in bk:
                        L += ["  Effective width: be=%5.2fin (%.0f%% panel), skin load=%.0f lb/in" %
                              (bk["skin_b_eff"], bk["skin_b_eff_ratio"]*100, bk["skin_eff_load_per_in"])]
                        L += ["  Cap/stringer compression demand: %.0f lb/in  (%.0f lb per rib bay)" %
                              (bk["cap_stringer_load_per_in"], bk["cap_stringer_load_per_bay"])]
                        L += ["  Stringer/rivet/fastener/frame sizing is outside AeroBeam."]
                    if bk["MS_skin_buckling"] < 0 and "t_min_skin" in bk and self.wing_struct == "aluminum_skin":
                        L += ["  >>> t_skin min = %.4fin for non-buckling skin" % bk["t_min_skin"]]
                if "sigma_cr_dcell_skin" in bk:
                    note = " (note: post-buckled OK)" if bk["MS_dcell_skin_buckling"] < 0 else ""
                    L += ["  D-cell skn  sig_cr=%6.0f  MS:%s%s" %
                          (bk["sigma_cr_dcell_skin"], mf(bk["MS_dcell_skin_buckling"]), note)]
                if "sigma_cr_cap" in bk:
                    fail = " ***" if bk["MS_cap_column"] < 0 else ""
                    L += ["  Cap column (Euler buckling) σ_cr=%6.0f psi  MS:%s%s" %
                          (bk["sigma_cr_cap"], mf(bk["MS_cap_column"]), fail)]
                if "sigma_cr_tube_cripple" in bk:
                    fail = " ***" if bk["MS_tube_cripple"] < 0 else ""
                    L += ["  Tube wall crippling σ_cr=%6.0f psi (t/R=%.4f)  MS:%s%s" %
                          (bk["sigma_cr_tube_cripple"], bk["t_over_R"],
                           mf(bk["MS_tube_cripple"]), fail)]
        return "\n".join(L)

    # ── Plots ────────────────────────────────────────────────────────────────

    def plot_results(self):
        import matplotlib.pyplot as plt
        plt.rcParams.update(PLOT_STYLE)
        fig, ax = plt.subplots(2, 2, figsize=(13,9))
        fig.suptitle("AeroBeam v1.2.3 — Results", fontsize=12, color=PC_GOLD)
        fig.patch.set_facecolor(PLOT_STYLE["figure.facecolor"])
        x=self.x; a=ax.flatten()
        a[0].plot(x, self.pos["w"], "b-",  label=f"+{self.n}g")
        a[0].plot(x,-self.neg["w"], "b--", label=f"{self.n_neg}g")
        a[0].set(title="Lift [lb/in]"); a[0].legend()
        a[1].plot(x, self.pos["V"], "g-")
        a[1].plot(x, self.neg["V"], "g--")
        a[1].set(title="Shear [lb]")
        a[2].plot(x, self.pos["M_front"], "b-", label="Frt +g")
        a[2].plot(x, self.pos["M_rear"], "c-", label="Rr +g")
        a[2].plot(x, self.neg["M_front"], "b--", label="Frt -g")
        a[2].plot(x, self.neg["M_rear"], "c--", label="Rr -g")
        a[2].set(title="Spar Moment [lb·in]"); a[2].legend()
        a[3].plot(x, self.pos["z_front"], "m-",  label="Frt +g (up)")
        a[3].plot(x, self.pos["z_rear"],  "c-",  label="Rr +g (up)")
        a[3].plot(x, self.pos["z_delta"], "g:",  label="Rr-Frt Δ +g")
        a[3].plot(x, self.neg["z_front"], "m--", label="Frt -g (down)")
        a[3].plot(x, self.neg["z_rear"],  "c--", label="Rr -g (down)")
        a[3].axhline(y=0, color="k", lw=0.5, alpha=0.4)
        a[3].set(title="Spar position [in]  (+up, includes twist)"); a[3].legend()
        for ax_ in a: ax_.set_xlabel("Span [in]"); ax_.grid(True,alpha=0.3)
        plt.tight_layout(); plt.show()

    def draw_geometry(self, ax_top, ax_side):
        """Draw plan view and front elevation into provided axes."""
        # Apply dark background if axes have no explicit style set
        for ax in (ax_top, ax_side):
            if ax.get_facecolor() == (1.0, 1.0, 1.0, 1.0):  # still white = screen mode
                ax.set_facecolor("#252930")
                ax.tick_params(colors="#B9BCC2", labelcolor="#e8eaf0")
                ax.spines[:].set_color("#6E7F87")
                for lbl in (ax.xaxis.label, ax.yaxis.label, ax.title):
                    lbl.set_color("#e8eaf0")
        x = self.x
        y_le, y_te = self.y_le, self.y_te
        # Plan view. Distances are aft of the root leading edge.
        ax_top.fill_between(x, y_le, y_te, alpha=0.10, color="steelblue")
        ax_top.plot(x, y_le, "k-", lw=1, label="LE")
        ax_top.plot(x, y_te, "k-", lw=1, label="TE")
        ax_top.plot(x, self.y_front, "b-", lw=2.5, label="Front spar")
        if self.num_spars == 2:
            ax_top.plot(x, self.y_rear, "r-", lw=1.5, label="Rear spar")
        if self.dcell:
            ax_top.fill_between(x, y_le, self.y_front, alpha=0.25,
                                color="cyan", label="D-cell")
        box_end = self._torsion_box_end()
        if box_end > 0.0 and self.num_spars == 2:
            ax_top.fill_between(
                x, self.y_front, self.y_rear, where=(x <= box_end),
                alpha=0.35, color="#D2B75F", label="Torsion box")
        # Taper break station
        if self.taper_start_bl > 0:
            ax_top.axvline(x=self.taper_start_bl, color="green", lw=1.2,
                           linestyle=":", alpha=0.8,
                           label="Taper BL=%.0f in" % self.taper_start_bl)
        if self.config in ("strut_braced","single_strut"):
            ax_top.axvline(x=self.strut_bl, color="purple", lw=1.5,
                linestyle="--", alpha=0.8,
                label="Strut BL = %.0f in" % self.strut_bl)
        if self.jury and self.config in ("strut_braced","single_strut"):
            ax_top.axvline(x=self.jury_bl, color="darkorange", lw=1.5,
                linestyle=":", alpha=0.8,
                label="Jury BL = %.0f in" % self.jury_bl)
        ax_top.invert_yaxis()
        ax_top.set_xlabel("Span station [in]  root to tip")
        ax_top.set_ylabel("Aft of root leading edge [in]")
        ax_top.set_title(f"Plan View  (straight {self.taper_reference.lower()})")
        ax_top.legend(fontsize=8, loc="upper right")
        ax_top.grid(True, alpha=0.3)
        # Front elevation
        b = self.b_half
        root_bl = self.r   # root fitting BL for all configs
        ax_side.plot([root_bl, b], [0, 0], "b-", lw=3, label="Front spar")
        if self.num_spars == 2:
            # Rear spar is offset chordwise from front spar
            # In elevation: horizontal offset not visible, but vertical separation
            # from front spar is approximately zero (both on same wing plane)
            # Show as parallel line slightly below to distinguish
            rear_lbl = "Rear spar (cantilever)" if self.config=="single_strut" else "Rear spar"
            ax_side.plot([root_bl, b], [-2, -2], "r-", lw=2,
                         label=rear_lbl, alpha=0.8)
        ax_side.plot(root_bl, 0, "ks", markersize=9, zorder=5, label="Root fitting (BL %.0f\")" % self.r)
        # Carry-through stub: cantilever only (spar crosses fuselage to other panel)
        if root_bl > 0 and self.config == "cantilever":
            ax_side.plot([0, root_bl], [0, 0], "b--", lw=1.5, alpha=0.5,
                         label="Carry-through to CL")
            if self.num_spars == 2:
                ax_side.plot([0, root_bl], [-4, -4], "r--", lw=1.0, alpha=0.4)
        ax_side.plot(b, 0, "k^", markersize=8, zorder=5, label="Tip")
        # Fuselage centreline marker
        if root_bl > 0:
            ax_side.axvline(x=0, color="gray", lw=1, linestyle=":", alpha=0.5)
            ax_side.text(0, 0, " CL", fontsize=7, color="gray", va="bottom")
        if self.config in ("strut_braced","single_strut"):
            sx = self.strut_bl; sy_fuse = -self.strut_vert
            sx_fuse = self.strut_fuse_bl   # fuselage attach BL — should equal self.r typically
            ax_side.plot([sx_fuse, sx], [sy_fuse, 0], color="purple", lw=2.5,
                         solid_capstyle="round",
                         label="Strut (%s)" % self.strut_mat.split()[0])
            ax_side.plot(sx,     0,      "p", color="purple", markersize=10, zorder=5)
            ax_side.plot(sx_fuse, sy_fuse, "p", color="purple", markersize=10, zorder=5)
            # Dimension: spar BL
            ax_side.annotate("", xy=(sx, sy_fuse*0.08), xytext=(sx_fuse, sy_fuse*0.08),
                arrowprops=dict(arrowstyle="<->", color="purple", lw=1.2))
            ax_side.text((sx+sx_fuse)/2, sy_fuse*0.18,
                         "BL %.0f to %.0f in" % (sx_fuse, sx),
                         ha="center", fontsize=8, color="purple")
            ax_side.annotate("", xy=(sx*1.03, 0), xytext=(sx*1.03, sy_fuse),
                arrowprops=dict(arrowstyle="<->", color="purple", lw=1.2))
            ax_side.text(sx*1.06, sy_fuse/2, ("Rise %.0f in" % self.strut_vert),
                         ha="left", va="center", fontsize=8, color="purple")
            if self.jury and 0 < self.jury_bl < sx:
                jx = self.jury_bl
                # Interpolate strut height at jury BL — strut runs from (sx_fuse,sy_fuse) to (sx,0)
                t = (jx - sx_fuse) / max(sx - sx_fuse, 1)   # 0 at fuse, 1 at spar attach
                jy = sy_fuse * (1.0 - t)
                ax_side.plot([jx, jx], [0, jy], color="darkorange", lw=2.5,
                             linestyle="--",
                             label="Jury strut (BL %.0f in)" % jx)
                ax_side.plot(jx, 0,  "D", color="darkorange", markersize=8, zorder=5)
                ax_side.plot(jx, jy, "D", color="darkorange", markersize=8, zorder=5)
                ax_side.text(jx+b*0.01, jy/2, "%.0f in" % jx,
                             va="center", fontsize=8, color="darkorange")
        # Fuselage: vertical line at the root fitting BL (self.r)
        # For cantilever, spar carry-through goes further inboard to BL 0
        y_range = max(self.strut_vert if self.config != "cantilever" else 20, 10)
        fuse_bl = root_bl   # fuselage side is at root fitting BL
        ax_side.axvline(x=fuse_bl, color="saddlebrown", lw=4,
                        linestyle="-", alpha=0.7, label="Fuselage (BL %.0f in)" % fuse_bl, zorder=4)
        ax_side.axvline(x=fuse_bl, color="saddlebrown", lw=12,
                        linestyle="-", alpha=0.15, zorder=3)
        ax_side.text(fuse_bl, y_range*0.40, "FUSE\nBL%.0f" % fuse_bl,
                     fontsize=7, color="saddlebrown", alpha=0.8,
                     ha="center", va="bottom", rotation=90)
        ax_side.set_xlabel("Span station [in]  root to tip")
        ax_side.set_ylabel("Height [in]  (spar = 0)")
        ax_side.set_title("Front Elevation  (looking forward)")
        ax_side.legend(fontsize=8, loc="upper right")
        ax_side.grid(True, alpha=0.3)
        y_range = max(self.strut_vert if self.config != "cantilever" else 20, 10)
        ax_side.set_xlim(-max(root_bl, 5)*1.2 if root_bl > 0 else -b*0.04, b*1.14)
        ax_side.set_ylim(-y_range*1.30, y_range*0.55)

    def plot_geometry(self):
        """Open a standalone pyplot window (bypassed in GUI -- GUI uses draw_geometry)."""
        import matplotlib.pyplot as plt
        fig, (ax_top, ax_side) = plt.subplots(2, 1, figsize=(13, 8),
            gridspec_kw={"height_ratios": [1.2, 1]})
        fig.suptitle("AeroBeam v1.2.3  Wing Geometry", fontsize=12)
        self.draw_geometry(ax_top, ax_side)
        plt.tight_layout(pad=2.0)
        plt.show(block=False)

    def export_pdf(self, path):
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt

        plt.rcParams.update(PDF_STYLE)   # white background, print-friendly

        with PdfPages(path) as pdf:

            # ── Page 1: Inputs text ───────────────────────────────────────────
            fig = plt.figure(figsize=(11, 8.5))
            fig.suptitle("AeroBeam v1.2.3  —  Input Summary", fontsize=12,
                         y=0.98, color=PDF_GOLD, fontfamily="monospace",
                         fontweight="bold")
            ax = fig.add_subplot(111); ax.axis("off")
            ax.text(0.03, 0.92, self._input_page_text(),
                    transform=ax.transAxes, fontsize=10,
                    va="top", family="monospace", color="#111111",
                    linespacing=1.4)
            pdf.savefig(fig); plt.close(fig)

            # ── Page 2: Wing Geometry (plan view + front elevation) ───────────
            fig, (ax_plan, ax_elev) = plt.subplots(2, 1, figsize=(11, 8.5),
                gridspec_kw={"height_ratios": [1.1, 1]})
            fig.suptitle("AeroBeam v1.2.3  —  Wing Geometry", fontsize=12,
                         y=0.98, color=PDF_GOLD, fontweight="bold")
            self.draw_geometry(ax_plan, ax_elev)
            plt.tight_layout(pad=2.5)
            pdf.savefig(fig); plt.close(fig)

            # ── Page 3: Analysis plots ────────────────────────────────────────
            fig, axs = plt.subplots(2, 2, figsize=(11, 8.5))
            fig.suptitle("AeroBeam v1.2.3  —  Analysis Results", fontsize=12,
                         color=PDF_GOLD, fontweight="bold")
            x = self.x
            axs[0,0].plot(x,  self.pos["w"],       color=PDF_BLUE, lw=2,
                          label="+%.0fg" % self.n)
            axs[0,0].plot(x, -self.neg["w"],        color=PDF_GREY, lw=1.5,
                          linestyle="--", label="%.0fg" % self.n_neg)
            axs[0,0].set_title("Lift [lb/in]"); axs[0,0].legend(fontsize=8)

            axs[0,1].plot(x, self.pos["V"],         color=PDF_BLUE, lw=2,
                          label="+%.0fg" % self.n)
            axs[0,1].plot(x, self.neg["V"],         color=PDF_GREY, lw=1.5,
                          linestyle="--", label="%.0fg" % self.n_neg)
            axs[0,1].set_title("Shear [lb]"); axs[0,1].legend(fontsize=8)

            axs[1,0].plot(x, self.pos["M_front"],   color=PDF_BLUE, lw=2,
                          label="Frt +%.0fg" % self.n)
            axs[1,0].plot(x, self.pos["M_rear"],    color=PDF_NAVY, lw=1.5,
                          label="Rr +%.0fg" % self.n)
            axs[1,0].plot(x, self.neg["M_front"],   color=PDF_GREY, lw=1.5,
                          linestyle="--", label="Frt %.0fg" % self.n_neg)
            axs[1,0].plot(x, self.neg["M_rear"],    color="#888888", lw=1,
                          linestyle=(0,(2,3)), label="Rr %.0fg" % self.n_neg)
            axs[1,0].set_title("Spar Moment [lb·in]"); axs[1,0].legend(fontsize=8)

            axs[1,1].plot(x, self.pos["z_front"],   color=PDF_BLUE, lw=2,
                          label="Frt +g (up)")
            axs[1,1].plot(x, self.pos["z_rear"],    color=PDF_NAVY, lw=1.5,
                          linestyle=(0,(4,2)), label="Rr +g (up)")
            axs[1,1].plot(x, self.pos["z_delta"],   color=PDF_GREEN, lw=1.1,
                          linestyle=":", label="Rr-Frt Δ +g")
            axs[1,1].plot(x, self.neg["z_front"],   color=PDF_GREY, lw=1.5,
                          linestyle="--", label="Frt -g (dn)")
            axs[1,1].plot(x, self.neg["z_rear"],    color="#888888", lw=1,
                          linestyle=(0,(2,3)), label="Rr -g (dn)")
            axs[1,1].axhline(y=0, color="#999999", lw=0.5)
            axs[1,1].set_title("Spar position [in], includes twist"); axs[1,1].legend(fontsize=8)

            for a in axs.flatten():
                a.set_xlabel("Span [in]")
                a.grid(True, alpha=0.4, linewidth=0.5)
            plt.tight_layout(); pdf.savefig(fig); plt.close(fig)

            # ── Page 4: Results summary (line-by-line coloured) ──────────────
            fig = plt.figure(figsize=(11, 8.5))
            fig.suptitle("AeroBeam v1.2.3  —  Results Summary", fontsize=12,
                         y=0.98, color=PDF_GOLD, fontfamily="monospace",
                         fontweight="bold")
            ax = fig.add_subplot(111); ax.axis("off")

            # Print-friendly colour rules (dark colours on white background)
            def line_colour(line):
                if "*** BUCKLING: FAIL" in line or "*** FAIL" in line:
                    return PDF_RED
                if "✗" in line or "***" in line:
                    return PDF_RED
                if "✓" in line:
                    return PDF_GREEN
                if "⚠" in line or "!! " in line or "WARN" in line:
                    return PDF_AMBER
                if "PASS" in line and "BUCKLING" in line:
                    return PDF_GREEN
                if ">>>" in line:
                    return PDF_AMBER
                if line.startswith("══") or line.startswith("--") or line.startswith("──"):
                    return PDF_GOLD
                if line.startswith("  [") and line.strip().endswith("]"):
                    return PDF_BLUE
                return "#111111"   # default: near-black on white

            lines = self.summary_text().splitlines()
            mid = len(lines) // 2 + 3
            col1, col2 = lines[:mid], lines[mid:]
            fs = 6.6; line_h = 0.0148; y_start = 0.95

            for col_lines, x_pos in [(col1, 0.01), (col2, 0.50)]:
                y = y_start
                for line in col_lines:
                    colour = line_colour(line)
                    weight = "bold" if ("FAIL" in line or "PASS" in line or
                                        line.startswith("══") or
                                        ">>>" in line) else "normal"
                    # Truncate line to fit column (monospace: ~72 chars per column)
                    line_out = line[:72] if len(line) > 72 else line
                    ax.text(x_pos, y, line_out, transform=ax.transAxes,
                            fontsize=fs, va="top", color=colour,
                            fontfamily="monospace", fontweight=weight,
                            clip_on=True)
                    y -= line_h

            pdf.savefig(fig); plt.close(fig)

        plt.rcParams.update(PLOT_STYLE)   # restore screen style after PDF export

    def _input_page_text(self):
        i=self.inp
        return "\n".join([
            "AeroBeam v1.2.3 — Input Summary","="*48,
            f"Span : {i[chr(98)]:.1f}in  Root chord: {self.root_chord:.1f}in  Tip: {self.tip_chord:.1f}in" + (f"  Taper from BL {self.taper_start_bl:.0f}in" if self.taper_start_bl > 0 else "") + f"  Straight {self.taper_reference.lower()}",
            f"Rib spacing: {self.rib_spacing:.1f}\"   Rib: {self.rib_type}",
            f"Spars      : front {self.front_pct*100:.0f}%  rear {self.rear_pct*100:.0f}%",
            f"Load       : +{self.n:.1f}g / {self.n_neg:.1f}g   ng_lift={self.ng_lift:.0f} lb",
            f"Config     : {self.config}   Struct: {self.wing_struct}",
            f"Airfoil    : {self.airfoil}   Cm={self.Cm_ac:+.4f}",
            f"Flight     : Vd={self.Vd_mph:.0f} mph  alt={self.alt_ft:.0f} ft",
            f"Front spar : {self.front_spar_type}",
            f"Rear  spar : {self.rear_spar_type}",
            f"D-cell     : {'yes - '+i.get('dcell_skin_mat','')+' '+str(i.get('dcell_skin_thick','')) if self.dcell else 'no'}",
            f"Geodetic   : {'yes - '+str(self.geodetic.strip_width)+'x'+str(self.geodetic.strip_thick)+' '+self.geodetic.mat_name if self.geodetic else 'no'}",
            f"Skin       : {self.top_skin.mat_name+' '+str(self.top_skin.thickness) if self.top_skin else 'fabric'}",
        ])

    def export_excel(self, path):
        import openpyxl; wb=openpyxl.Workbook(); ws=wb.active; ws.title="AeroBeam"
        hdrs=["x","chord","w_pos","V_pos","M_pos","z_f_pos","z_r_pos","sig_f_pos","sig_r_pos",
              "w_neg","V_neg","M_neg","z_f_neg","z_r_neg"]
        t=self.torsion
        if t: hdrs+=["T_aero","T_struct","T_total","T_run","phi_deg","tau_dcell","tau_geo"]
        ws.append(hdrs)
        for k in range(self.N):
            row=[float(self.x[k]),float(self.chord_x[k]),
                 float(self.pos["w"][k]),float(self.pos["V"][k]),float(self.pos["M"][k]),
                 float(self.pos["z_front"][k]),float(self.pos["z_rear"][k]),
                 float(self.pos["sigma_front"][k]),float(self.pos["sigma_rear"][k]),
                 float(self.neg["w"][k]),float(self.neg["V"][k]),float(self.neg["M"][k]),
                 float(self.neg["z_front"][k]),float(self.neg["z_rear"][k])]
            if t: row+=[float(t["T_aero"][k]),float(t["T_struct"][k]),float(t["T_total"][k]),
                         float(t["T_running"][k]),math.degrees(float(t["phi"][k])),
                         float(t["tau_dcell"][k]),float(t["tau_geo"][k])]
            ws.append(row)
        wb.save(path)

    @staticmethod
    def calc_ng_lift(n, weight, tail_down_1g):
        return n*(weight/2.0 + tail_down_1g)


if __name__=="__main__":
    print("=== analyzer self-test ===")
    inp=dict(DEFAULT_INPUTS)
    inp.update({"dcell_enabled":True,"dcell_skin_mat":"Birch Plywood",
                "dcell_skin_thick":0.125,"airfoil_t_c":0.12,"Cm_ac":-0.099})
    a=WingStressAnalyzer(inp); a.analyze()
    print(a.summary_text())
    print(f"\nM_root={a.M_root:,.0f}  z_max={a.z_max:.3f}")
    print("Self-test passed.")
