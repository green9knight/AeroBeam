"""
AeroBeam v1.2 — Wing Stress Analyzer
======================================
Physics engine. All structural analysis lives here.
Units: inches, pounds, psi throughout.
"""

import math
import traceback
import numpy as np
from typing import Optional, Tuple, Dict, Any

from spar_sections import (
    CrossSection, RoundTube, IBeam, DoubleIBeam, BoxSpar,
    CChannel, RoutedSpar, PlainRect,
    DCellSkin, GeodeticPanel, SkinPanel, WingBox,
    MATERIAL_DB, STRUT_MATERIALS,
    two_cell_bredt, allowable_bending, allowable_shear,
    web_buckling, web_bending_buckling, skin_compression_buckling, cap_column_buckling,
    skin_effective_width,
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
    "root_chord": 54.0, "tip_chord": 54.0, "taper_start_bl": 0.0, "rib_spacing": 12.0,
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
    "skin_top_mat": "6061-T6", "skin_top_thick": 0.025,
    "skin_bot_mat": "6061-T6", "skin_bot_thick": 0.025,
    "wood_knockdown": 0.75,
    # Rib structure (torsion transfer between spars)
    "rib_h_web":  3.0,    # rib web clear height [in]
    "rib_t_web":  0.125,  # rib web thickness [in]
    "rib_b_cap":  0.75,   # rib cap width [in]
    "rib_t_cap":  0.125,  # rib cap thickness [in]
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

def build_spar(spar_type: str, inputs: dict, prefix: str) -> CrossSection:
    def g(key, default=None):
        return inputs.get(f"{prefix}_{key}", default)
    t = spar_type
    if t == "Round Tube":
        return RoundTube(OD=float(g("od", 2.0)), wall=float(g("wall", 0.065)),
                         mat_name=g("mat", "6061-T6"))
    elif t == "Plain Rectangular":
        return PlainRect(width=float(g("width", 2.0)), height=float(g("height", 4.0)),
                         mat_name=g("cap_mat", "Sitka Spruce"))
    elif t in ("I-Beam", "C-Channel", "Routed (Monolithic)"):
        kw = dict(b_top=float(g("b_top",1.5)), t_top=float(g("t_top",0.75)),
                  b_bot=float(g("b_bot",1.5)), t_bot=float(g("t_bot",0.75)),
                  h_web=float(g("h_web",4.5)), t_web=float(g("t_web",0.125)))
        cm = g("cap_mat","Sitka Spruce"); wm = g("web_mat","Birch Plywood")
        if t == "I-Beam":         return IBeam(**kw, cap_mat=cm, web_mat=wm)
        elif t == "C-Channel":    return CChannel(**kw, cap_mat=g("cap_mat","6061-T6"),
                                                   web_mat=g("web_mat","6061-T6"))
        else:                     return RoutedSpar(**kw, mat_name=cm)
    elif t == "Double I-Beam":
        return DoubleIBeam(
            b_top=float(g("b_top",1.5)), t_top=float(g("t_top",0.75)),
            b_bot=float(g("b_bot",1.5)), t_bot=float(g("t_bot",0.75)),
            h_web=float(g("h_web",4.5)), t_web=float(g("t_web",0.125)),
            web_spacing=float(g("web_spacing",1.0)),
            cap_mat=g("cap_mat","Sitka Spruce"), web_mat=g("web_mat","Birch Plywood"))
    elif t == "Box Spar":
        return BoxSpar(b_outer=float(g("b_outer",2.0)), h_outer=float(g("h_outer",5.0)),
                       t_web=float(g("t_web",0.125)), t_cap=float(g("t_cap",0.75)),
                       cap_mat=g("cap_mat","Sitka Spruce"), web_mat=g("web_mat","Birch Plywood"))
    elif t == "Aluminum I-Beam":
        # Angle caps both sides + sheet web, all aluminum
        return IBeam(b_top=float(g("b_top",1.5)), t_top=float(g("t_top",0.125)),
                     b_bot=float(g("b_bot",1.5)), t_bot=float(g("t_bot",0.125)),
                     h_web=float(g("h_web",5.0)), t_web=float(g("t_web",0.050)),
                     cap_mat=g("cap_mat","6061-T6"), web_mat=g("web_mat","6061-T6"))
    elif t == "Aluminum C-Spar":
        # Single angle cap one side + sheet web
        from spar_sections import AluminumCSpar
        return AluminumCSpar(
            b_cap=float(g("b_top",1.5)), t_cap=float(g("t_top",0.125)),
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

        # D-cell
        self.dcell_enabled = parse_bool(i.get("dcell_enabled", False))
        if self.dcell_enabled:
            c2s   = self.front_pct * self.root_chord
            t_web = float(i.get("front_spar_t_web",
                                 i.get("front_spar_wall", 0.125)))
            self.dcell = DCellSkin(
                t_skin=float(i.get("dcell_skin_thick", 0.0625)),
                skin_mat=i.get("dcell_skin_mat", "Birch Plywood"),
                chord_to_spar=c2s, t_web=t_web)
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

        # Skin panels (aluminum or plywood/wood)
        # Create if skin thickness is provided, regardless of wing_structure_type.
        # This allows plywood skin to contribute to torsional transfer stiffness.
        skin_top_thick = float(i.get("skin_top_thick", 0.0))
        skin_bot_thick = float(i.get("skin_bot_thick", 0.0))
        if skin_top_thick > 1e-6 or skin_bot_thick > 1e-6:
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

        self.front_spar_type = i.get("front_spar_type", "Round Tube")
        self.rear_spar_type  = i.get("rear_spar_type",  "Round Tube")
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
        V = np.zeros(self.N)
        M = np.zeros(self.N)

        # Basic integration from tip to root
        for i in range(self.N-2, -1, -1):
            V[i] = V[i+1] + w[i] * self.dx
            M[i] = M[i+1] + V[i] * self.dx

        # === Strut reaction handling (strut-braced only, no jury effect) ===
        config = getattr(self, "config", "cantilever")
        if config in ("strut_braced", "single_strut"):
            strut_bl = getattr(self, "strut_bl", self.b_half * 0.65)
            strut_reaction = getattr(self, "strut_reaction", 0.0)

            if strut_reaction <= 0:
                # Calculate strut reaction from statics
                moment_root = np.sum(w * self.x * self.dx)
                arm = max(strut_bl - getattr(self, "r", 0.0), 1e-6)
                strut_reaction = moment_root / arm
                self.strut_reaction = strut_reaction

            # Apply concentrated reaction at strut location
            strut_idx = np.argmin(np.abs(self.x - strut_bl))
            V[:strut_idx] += strut_reaction

            # Re-integrate moment after the force application
            for i in range(strut_idx - 1, -1, -1):
                M[i] = M[i + 1] + V[i] * self.dx

        return V, M

    def _deflect_cantilever(self, M, EI):
        th = np.zeros(self.N); z = np.zeros(self.N)
        for i in range(1, self.N):
            kappa  = self.curvature_sign * M[i] / max(EI[i], 1.0)
            th[i]  = th[i-1] + kappa*self.dx
            z[i]   = z[i-1]  + th[i]*self.dx
        return th, z

    def _deflect_strut(self, M, EI, si):
        th0, z0 = self._deflect_cantilever(M, EI)
        # Unit root slope
        th1 = np.ones(self.N); z1 = np.zeros(self.N)
        for i in range(1, self.N): z1[i] = z1[i-1] + th1[i]*self.dx
        if abs(z1[si]) < 1e-15: return th0, z0
        alpha = -z0[si] / z1[si]
        return th0 + alpha*th1, z0 + alpha*z1

    def _elastic_coupled_rear_response(self, w_rear, z_front, k_connection,
                                       point_couplings: Optional[list] = None):
        """Solve rear spar as a beam elastically connected to front spar.

        The front spar response is already solved with the appropriate root and
        strut supports. The rear spar is a root-fixed beam carrying the torsion
        couple load and connected to the front spar by distributed springs.
        This replaces the older scalar kappa blend with an actual elastic
        compatibility solve for the rear spar.
        """

        n = self.N
        ndof = 2 * n
        K = np.zeros((ndof, ndof))
        F = np.zeros(ndof)
        element_data = []

        for i in range(n - 1):
            L = self.x[i + 1] - self.x[i]
            EI = 0.5 * (self._EI_r[i] + self._EI_r[i + 1])
            k = EI / L**3 * np.array([
                [12, 6 * L, -12, 6 * L],
                [6 * L, 4 * L**2, -6 * L, 2 * L**2],
                [-12, -6 * L, 12, -6 * L],
                [6 * L, 2 * L**2, -6 * L, 4 * L**2],
            ])
            q = 0.5 * (w_rear[i] + w_rear[i + 1])
            f = q * L / 2.0 * np.array([1, L / 6.0, 1, -L / 6.0])
            dofs = [2 * i, 2 * i + 1, 2 * (i + 1), 2 * (i + 1) + 1]
            for a in range(4):
                F[dofs[a]] += f[a]
                for b in range(4):
                    K[dofs[a], dofs[b]] += k[a, b]
            element_data.append((dofs, k, f))

        # Distributed elastic connection: force = k * (z_front - z_rear).
        for i in range(n):
            tributary = self.dx if 0 < i < n - 1 else self.dx / 2.0
            k_node = max(k_connection, 0.0) * tributary
            dof = 2 * i
            K[dof, dof] += k_node
            F[dof] += k_node * z_front[i]

        # Optional discrete soft connections such as jury struts tying front
        # and rear spars together at the jury station.
        for station, stiffness in point_couplings or []:
            if stiffness <= 0:
                continue
            idx = int(np.argmin(np.abs(self.x - station)))
            dof = 2 * idx
            K[dof, dof] += stiffness
            F[dof] += stiffness * z_front[idx]

        # Rear spar root fitting: fixed vertical displacement and rotation.
        constrained = [0, 1]
        free = [idx for idx in range(ndof) if idx not in constrained]
        U = np.zeros(ndof)
        U[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])

        z = U[0::2]
        th = U[1::2]
        M = np.zeros(n)
        counts = np.zeros(n)
        for i, (dofs, k, f) in enumerate(element_data):
            end_forces = k @ U[dofs] - f
            # Internal element end moments are the rotational DOF forces.
            M[i] += end_forces[1]
            M[i + 1] += -end_forces[3]
            counts[i] += 1
            counts[i + 1] += 1
        M = np.divide(M, np.maximum(counts, 1.0))
        return th, z, M

    def _strut_idx(self):
        return int(np.argmin(np.abs(self.x - self.strut_bl)))

    # ── Spar arrays ──────────────────────────────────────────────────────────

    def _spar_arrays(self):
        scales = self.chord_x / self.root_chord
        def arr(spar):
            # Use get_arrays if available (handles constant vs tapered correctly)
            if hasattr(spar, 'get_arrays'):
                d = spar.get_arrays(self.x, self.b_half, self.root_chord, self.tip_chord)
                return (d["EI"], d["I_tr"], d["y_max"], d["y_top"], d["y_bot"])
            props = [spar.get_props(s) for s in scales]
            return (np.array([p.EI    for p in props]),
                    np.array([p.I_tr  for p in props]),
                    np.array([p.y_max for p in props]),
                    np.array([p.y_top for p in props]),
                    np.array([p.y_bot for p in props]))
        self._EI_f,self._Itr_f,self._ym_f,self._yt_f,self._yb_f = arr(self.front_spar)
        rs = self.rear_spar if self.rear_spar else self.front_spar
        self._EI_r,self._Itr_r,self._ym_r,self._yt_r,self._yb_r = arr(rs)

    # ── GJ arrays ────────────────────────────────────────────────────────────

    def _gj_arrays(self):
        N = self.N; scales = self.chord_x/self.root_chord
        GJ = np.zeros(N); q1f = np.zeros(N); q2f = np.zeros(N)
        h0  = self.t_c * self.root_chord
        t_wfs = float(self.inp.get("front_spar_t_web",
                                    self.inp.get("front_spar_wall", 0.125)))
        t_wrs = float(self.inp.get("rear_spar_t_web",
                                    self.inp.get("rear_spar_wall", 0.094)))
        for i, s in enumerate(scales):
            if not self.dcell_enabled: break
            h    = h0 * s
            c_b  = (self.rear_pct-self.front_pct)*self.chord_x[i]
            A1   = self.dcell.enclosed_area(h, s)
            G1   = MATERIAL_DB[self.dcell.skin_mat]["G"]
            ds1  = self.dcell.ds_over_t_own(h, s)
            dss  = self.dcell.ds_over_t_web(h, s)

            if self.geodetic is not None:
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
        """Return rib/geodetic/skin torsion-transfer stiffness terms.

        This model is used by both the case solver and the reported torsion
        results. Keeping it in one place avoids the recurring bug where rear
        spar coupling was based on stale or approximate stiffness values.
        """

        chord_box = (self.rear_pct - self.front_pct) * self.root_chord
        spar_gap = max(chord_box, 1.0)

        # Ribs are no longer treated as a defined structural member in the
        # global torsion/coupling model. AeroBeam reports required rib bay
        # reactions separately so designers can size ribs with their own
        # construction details and standards.
        k_rib = 0.0

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
        T_aero = np.abs(self.Cm_ac) * q_psi * c**2 * sign

        if self.config == "single_strut" and self.num_spars == 2:
            e_rs = (self.rear_pct - self.front_pct) * c
            T_struct = self.rsf * w_total * e_rs
        else:
            T_struct = np.zeros(self.N)

        return T_aero, T_struct, T_aero + T_struct

    def _torsion(self, GJ, q1f, q2f, w_total):
        q_psi = dynamic_pressure_psi(self.Vd_mph, self.alt_ft)
        T_aero, T_struct, T_tot = self._distributed_torsion(w_total, q_psi)

        # Running torque (cumulative from tip)
        T_run = np.zeros(self.N)
        for i in range(self.N-2, -1, -1):
            T_run[i] = T_run[i+1] + T_tot[i]*self.dx

        # Twist
        with np.errstate(divide="ignore", invalid="ignore"):
            dphidx = np.where(GJ>0, T_tot/GJ, 0.0)
        phi = np.zeros(self.N)
        for i in range(self.N-2, -1, -1):
            phi[i] = phi[i+1] + dphidx[i]*self.dx

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

        # Required rib reactions if ribs are used as the transfer path. This is
        # a demand output, not a rib sizing check.
        local_torque = np.abs(T_tot) * self.rib_spacing
        max_idx = int(np.argmax(local_torque))
        rib_bay_torque = float(local_torque[max_idx])
        rib_reaction = rib_bay_torque / max(spar_gap, 1e-9)
        rib_reaction_station = float(self.x[max_idx])

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
                "phi_root_deg":math.degrees(phi[0]),
                "tau_dcell":tau_d,"tau_geo":tau_g,
                "T_run_vc":T_run_vc, "Vc_mph":self.Vc_mph,
                "T_run_flap":T_run_flap, "Cm_flap":Cm_flap_total,
                "cp_1g":cp_1g, "cp_ng":cp_ng,
                "cp_neg":cp_neg, "cp_dive":cp_dive,
                "f_rib":f_rib,"f_geo":f_geo,"f_skin":f_skin,
                "k_rib":k_rib,"k_geo":k_geo,"k_total":k_total,
                "rib_bay_torque":rib_bay_torque,
                "rib_reaction_required":rib_reaction,
                "rib_reaction_station":rib_reaction_station,
                "geodetic_q":geodetic_q,
                "geodetic_strip_force":geodetic_strip_force,
                "geodetic_strip_stress":geodetic_strip_stress,
                "geodetic_station":geodetic_station}

    # ── Divergence ───────────────────────────────────────────────────────────

    def _divergence(self, GJ_root):
        c    = self.root_chord
        x_ac = self.x_ac_c * c
        x_sc = (0.22*c if (self.dcell or getattr(self, "top_skin", None) is not None or
                            self.wing_struct in ("fabric_buildup","aluminum_skin"))
                 else self.front_pct*c)
        e = x_ac - x_sc
        if e<=0 or GJ_root<=0:
            return {"V_div":float("inf"),"SF_div":float("inf"),
                    "e":e,"x_ac":x_ac,"x_sc":x_sc,"divergent":False}
        rho   = isa_density(self.alt_ft)
        c_ft  = c/12.0; e_ft = e/12.0
        GJ_ft = GJ_root/144.0
        Vsq   = 2.0*GJ_ft/(rho*self.Cl_alpha*e_ft*c_ft**2)
        Vd    = math.sqrt(max(Vsq,0))*3600/5280
        SF    = Vd/max(self.Vd_mph,1)
        return {"V_div":Vd,"SF_div":SF,"e":e,"x_ac":x_ac,"x_sc":x_sc,"divergent":True}

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

        A jury strut braces the lift strut laterally at ``jury_bl``. It should
        not change the axial load or wing reactions; it only reduces the
        unsupported column length to the longer of the two strut segments.
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
        """Return vertical reactions for main strut and optional load-bearing jury.

        Without a valid jury BL, this reduces to the existing statics relation
        ``R_strut = M_root / strut_bl``. With a valid jury station between the
        fuselage and main strut attach, the jury and main strut reactions are
        solved with:

        1. root moment relief: R_j*j + R_s*s = M_root
        2. compatibility: after root-slope adjustment, z(jury) and z(strut)
           are both zero.
        """

        strut_bl = max(self.strut_bl, 1.0)
        strut_unit = self._reaction_moment(strut_bl)

        if not self.jury or not (self.strut_fuse_bl < self.jury_bl < self.strut_bl):
            R_strut = M_total[0] / strut_bl
            return {
                "strut": R_strut,
                "jury": 0.0,
                "moment": R_strut * strut_unit,
            }

        jury_bl = self.jury_bl
        jury_unit = self._reaction_moment(jury_bl)
        ji = int(np.argmin(np.abs(self.x - jury_bl)))
        si = self._strut_idx()

        def compatibility(moment: np.ndarray) -> float:
            _, z = self._deflect_cantilever(moment, EI)
            return z[ji] - z[si] * (self.x[ji] / max(self.x[si], 1e-9))

        rhs = np.array([M_total[0], compatibility(M_total)])
        matrix = np.array([
            [jury_bl, strut_bl],
            [compatibility(jury_unit), compatibility(strut_unit)],
        ])

        try:
            R_jury, R_strut = np.linalg.solve(matrix, rhs)
        except np.linalg.LinAlgError:
            R_jury = 0.0
            R_strut = M_total[0] / strut_bl

        # A reversed reaction would mean this geometry/stiffness does not make
        # the jury act as an upward support. Fall back to buckling-only behavior.
        if R_jury < 0.0 or R_strut < 0.0:
            R_jury = 0.0
            R_strut = M_total[0] / strut_bl

        return {
            "strut": float(R_strut),
            "jury": float(R_jury),
            "moment": R_jury * jury_unit + R_strut * strut_unit,
        }

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
        if P_comp<=0 or Pe<=0: return M, False, 1.0
        if P_comp/Pe>=1.0:     return M*10, True, 10.0
        amp = 1.0/(1.0-P_comp/Pe)
        return M*amp, amp>2.0, amp

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
            Fv_jury = reactions["jury"]
            Fv_strut_attach = reactions["strut"]
            Fv_total = Fv_jury + Fv_strut_attach
            Fv,Fa,Ps,Pe,L_strut = self._strut_forces(np.abs(M), Fv_override=Fv_total)
            M_strut = reactions["moment"]
            M = M - M_strut * sign   # subtract signed strut reaction (front spar)

        # P-delta
        pw = False
        pdelta_amp = 1.0
        if self.secondary and Ps>0:
            M, pw, pdelta_amp = self._pdelta(M, Ps, self._EI_f)

        # Deflection — front spar (uses strut-corrected M)
        Mf = M*self.lsf

        # Force cantilever deflection if we want to ignore jury strut effect on plots
        ignore_jury_for_deflection = getattr(self, "jury", False)

        if self.config in ("strut_braced","single_strut") and not ignore_jury_for_deflection:
            th_f, z_f = self._deflect_strut(Mf, self._EI_f, si)
        else:
            th_f, z_f = self._deflect_cantilever(Mf, self._EI_f)

        # ── REAR SPAR LOAD PATH ──────────────────────────────────────────────
        # For cantilever and single_strut: the rear spar root fitting transfers
        # the TORSION COUPLE to the fuselage, not independent lift bending.
        # Load = T(x) / spar_spacing(x) acting as a vertical distributed force.
        # For strut_braced: both spars share lift bending via rsf (parallel beams).
        #
        # Geodetic/fabric coupling partially transfers bending from front to rear,
        # but the rear spar deflects together with front (κ coupling factor).

        spar_spacing = max((self.rear_pct - self.front_pct) * self.root_chord, 1.0)
        chord_box    = spar_spacing

        # Torsion-based rear spar distributed load (correct for cantilever/single_strut)
        # V_rear(x) = T_total(x) / spar_spacing [lb/in]. Use the same signed
        # torsion model as the report path so altitude, single-strut structural
        # torsion, and airfoil moment stay consistent.
        q_dyn = dynamic_pressure_psi(self.Vd_mph, self.alt_ft)
        _, _, T_total_case = self._distributed_torsion(w, q_dyn, sign=sign)
        w_rear = T_total_case / spar_spacing

        # Combined transfer stiffness from geodetic/skin elastic connection.
        transfer = getattr(self, "_torsion_transfer", None)
        if transfer is None:
            transfer = self._torsion_transfer_stiffness()
        k_transfer = transfer["k_total"]

        if self.config == "strut_braced" and self.num_spars == 2:
            # Both spars strutted: parallel beam model is correct
            Mr = M * self.rsf
            th_r, z_r = self._deflect_strut(Mr, self._EI_r, si)
            self._geodetic_kappa = 0.0

        elif self.config in ("cantilever", "single_strut") and self.num_spars == 2:
            point_couplings = []
            # Only add jury coupling if we are NOT ignoring jury for deflection plots
            if getattr(self, "jury", False) and not getattr(self, "_ignore_jury_for_deflection", True):
                jury_k = self._jury_coupling_stiffness()
                if jury_k > 0.0:
                    point_couplings.append((self.jury_bl, jury_k))
            th_r, z_r, Mr = self._elastic_coupled_rear_response(w_rear, z_f, k_transfer, point_couplings)
            _, z_r_free, _ = self._elastic_coupled_rear_response(w_rear, z_f, 0.0, [])
            free_delta = float(np.max(np.abs(z_r_free - z_f)))
            coupled_delta = float(np.max(np.abs(z_r - z_f)))
            if free_delta > 1e-9:
                self._geodetic_kappa = float(np.clip(1.0 - coupled_delta / free_delta, 0.0, 1.0))
            else:
                self._geodetic_kappa = 1.0 if coupled_delta < 1e-9 else 0.0

        else:
            # Single spar or fallback
            Mr = M_cant * self.rsf
            th_r, z_r = self._deflect_cantilever(Mr, self._EI_r)
            self._geodetic_kappa = 0.0

        sig_f = Mf / np.maximum(self._Itr_f, 1e-10) * self._ym_f
        sig_r = Mr / np.maximum(self._Itr_r, 1e-10) * self._ym_r

        return {
            "w":w, "V":V, "M":M,
            "M_front":Mf, "M_rear":Mr,
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

            # Governing shear and moment at this station
            V_gov = abs(float(self.pos["V"][mi])) * lsf_val
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
            V_arr = np.abs(self.pos["V"]) * lsf_val
            mi_V  = int(np.argmax(V_arr))
            V_max = float(V_arr[mi_V])
            x_V   = float(self.x[mi_V])
            t_eff_V, is_doubled_V = self._t_web_eff(prefix, x_V, t_web)
            r["x_shear_gov"]  = x_V
            r["t_web_eff_V"]  = t_eff_V
            r["is_doubled_V"] = is_doubled_V

            # 1. Web shear stress — use max shear station with its effective t
            if h_web > 0 and t_web > 0:
                tau_web_max = V_max / max(h_web * t_eff_V, 1e-9)
                r["tau_web"] = tau_web_max
                Fsu = MATERIAL_DB[web_mat]["Fsu"]
                r["MS_web_shear"] = Fsu / max(tau_web_max, 1e-9) - 1

                # 2. Web shear buckling at max shear station
                wb = web_buckling(t_eff_V, h_web, self.stiffener_spacing, web_mat)
                r.update(wb)
                r["MS_web_buckling"] = wb["tau_cr"] / max(tau_web_max, 1e-9) - 1

                # 3. Web combined buckling at governing bending station
                # Use t_eff (which may include doubler at that station)
                wb_b = web_buckling(t_eff, h_web, self.stiffener_spacing, web_mat)
                wbb  = web_bending_buckling(t_eff, h_web, web_mat)
                r.update(wbb)
                p = spar.get_props(1.0)
                sigma_web = sigma_gov * (h_web/2) / max(p.y_max, 1e-9)
                r["sigma_web_bending"] = sigma_web
                tau_web_b = abs(float(self.pos["V"][mi])) * lsf_val / max(h_web * t_eff, 1e-9)
                tau_cr  = wb_b["tau_cr"]
                sig_cr  = wbb["sigma_cr_web_bending"]
                if tau_cr > 0 and sig_cr > 0:
                    R = (tau_web_b/tau_cr)**2 + sigma_web/sig_cr
                    r["MS_web_combined"] = 1.0/max(R, 1e-9) - 1
                else:
                    r["MS_web_combined"] = float("inf")

                # Min web thickness at max shear station (for guidance)
                Emw = MATERIAL_DB[web_mat]["E"]; nu = 0.33
                k_s = wb["k_s"]
                if k_s > 0 and Emw > 0 and tau_web_max > 0:
                    t_min_web = h_web * math.sqrt(tau_web_max * 12*(1-nu**2) / (k_s * math.pi**2 * Emw))
                    r["t_min_web"] = t_min_web

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
                # Minimum skin thickness guidance
                Esk = MATERIAL_DB[self.top_skin.mat_name]["E"]; nu = 0.33
                k_sk = 4.0
                if sigma_gov > 0:
                    t_min_skin = b_skin * math.sqrt(sigma_gov * 12*(1-nu**2) / (k_sk * math.pi**2 * Esk))
                    r["t_min_skin"] = t_min_skin

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
        self._spar_arrays()
        self.GJ, self.q1_frac, self.q2_frac = self._gj_arrays()
        self._torsion_transfer = self._torsion_transfer_stiffness()
        self._torsion_stiffness = self._torsion_transfer["k_total"]

        self.pos = self._one_case(self.ng_lift, +1)
        ng_neg   = abs(self.n_neg)/self.n*self.ng_lift
        self.neg = self._one_case(ng_neg, -1)

        self.torsion = self._torsion(self.GJ, self.q1_frac, self.q2_frac, self.pos["w"])

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
            "Fv_jury":self.pos.get("Fv_jury", 0.0),
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
        self.fitting_loads = {
            "front_root_vertical": abs(float(self.pos["V_root"] * self.lsf)),
            "rear_root_vertical": abs(float(self.pos["V_root"] * self.rsf)) if self.num_spars == 2 else 0.0,
            "main_strut_vertical": abs(float(self.pos.get("Fv_strut_attach", self.pos["Fv"]))),
            "jury_vertical": abs(float(self.pos.get("Fv_jury", 0.0))),
            "main_strut_axial": abs(float(self.pos["F_axial"])),
            "front_spar_strut_attach_vertical": abs(float(self.pos.get("Fv_strut_attach", self.pos["Fv"]))),
            "rear_spar_strut_attach_vertical": abs(float(self.pos.get("Fv_strut_attach", self.pos["Fv"]))) if self.config == "strut_braced" and self.num_spars == 2 else 0.0,
            "front_spar_jury_attach_vertical": abs(float(self.pos.get("Fv_jury", 0.0))),
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
        L += ["═"*54,"  AeroBeam v1.2  ─  Results","═"*54]
        L += method_status_lines()
        L += [f"\nAirfoil    : {self.airfoil}  Cm (pitching moment coeff)={self.Cm_ac:+.4f}"]
        L += [f"Config     : {self.config}   Structure: {self.wing_struct}"]
        L += [f"n (load factor, ultimate): +{self.n:.1f}g / {self.n_neg:.1f}g"]

        L += [f"\n── BENDING (+g) {'─'*37}"]
        L += [f"  Root V (shear force)  : {p['V_root']:>10,.1f} lb"]
        L += [f"  Root M (bending moment): {p['M_root']:>10,.1f} lb·in"]
        if self.secondary:
            L += [f"  P-delta amplification : {p.get('pdelta_amp', 1.0):>10.3f}×  (affects moment/stress, not lift/shear)"]
        L += [f"  Front z_max (tip deflection): {p['z_max_front']:>10.3f} in  (+up)"]
        L += [f"  Rear  z_max (tip deflection): {p['z_max_rear']:>10.3f} in  (+up)"]
        L += [f"  Rear-front Δz max (relative flex): {p['z_delta_max']:>8.3f} in"]
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
            if self.jury:
                L += [f"  Vertical reactions: jury={s['Fv_jury']:,.0f} lb   main strut attach={s['Fv_strut_attach']:,.0f} lb"]
            L += [f"  SF (safety factor) Euler buckling :{mf(s['SF_euler']-1)}"]
            L += [f"  MS (margin of safety) axial       :{mf(s['MS_axial'])}"]
            L += [f"  Strut wt (½)  : {s['weight_half']:.2f} lb"]
            if self.jury:
                L += ["  Jury strut modeled as load-bearing support plus Euler brace."]
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
                    L += [f"  Jury attach vertical demand        : {fl['jury_vertical']:>9,.0f} lb"]
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
            L += [f"  Twist φ (aeroelastic, root): {t['phi_root_deg']:>9.3f}°  (< 1° acceptable)"]
            if self.dcell:
                td=abs(float(t["tau_dcell"][0]))
                Fs=MATERIAL_DB[self.dcell.skin_mat]["Fsu"]
                L += [f"  D-cell τ (shear stress) root: {td:>9,.0f} psi   MS:{mf(Fs/max(td,1)-1)}"]
            if hasattr(self, "_geodetic_kappa"):
                kap = self._geodetic_kappa
                L += [f"  Geodetic coupling k : {kap:.4f}  (1.0=fully coupled, 0=cantilever)"]
                jury_k = self._jury_coupling_stiffness()
                if self.jury and jury_k > 0:
                    L += [f"  Jury tube front/rear coupling: k={jury_k:,.0f} lb/in at BL {self.jury_bl:.1f}\""]
                    L += [f"  Jury links: {self.jury_tube_od:.3f}x{self.jury_tube_wall:.3f} {self.jury_tube_mat}, "
                          f"Lf={self.jury_front_link_length:.1f}\" @ {self.jury_front_link_angle:.0f}°, "
                          f"Lr={self.jury_rear_link_length:.1f}\" @ {self.jury_rear_link_angle:.0f}°"]
                if kap < 0.5:
                    L += ["  ⚠ Weak coupling — rear spar closer to free cantilever"]
                elif kap > 0.95:
                    L += ["  Rear spar effectively constrained by rib/geodetic structure"]
            if t and "f_rib" in t:
                fr = t["f_rib"]; fg = t.get("f_geo",0); fs = t.get("f_skin",0)
                L += [f"  Torsion share: ribs={fr*100:.0f}%  geodetic={fg*100:.0f}%  skin={fs*100:.0f}%"]
                L += [f"  Required rib bay torque : {t['rib_bay_torque']:>8.0f} lb-in at x={t['rib_reaction_station']:.1f}\""]
                L += [f"  Required rib attach reaction: ±{t['rib_reaction_required']:>7.1f} lb per rib bay"]
                L += ["  Rib sizing is not performed; design ribs/attachments for this reaction."]
            if self.geodetic:
                tg=abs(float(t["tau_geo"][0]))
                sig_s=t.get("geodetic_strip_stress", 0.0)
                strip_f=t.get("geodetic_strip_force", 0.0)
                q_geo=t.get("geodetic_q", 0.0)
                red=float(self.inp.get("geodetic_reduction_factor", 0.75))
                Fb_s=MATERIAL_DB[self.geodetic.mat_name]["Fb"]
                L += [f"  Geodetic τ eff: {tg:>9,.0f} psi"]
                L += [f"  Geodetic stiffness reduction f_red={red:.2f} (connection/detail allowance)"]
                L += [f"  ANC-18 drag-truss demand: q={q_geo:>7.1f} lb/in  strip F={strip_f:>7.1f} lb"]
                L += [f"  Strip axial σ demand: {sig_s:>9,.0f} psi   MS vs Fb only:{mf(Fb_s/max(sig_s,1)-1)}"]
                L += ["  Geodetic mesh demand only; bond/joint/attachment sizing is outside AeroBeam."]

        L += [f"\n── DIVERGENCE {'─'*39}"]
        if d["divergent"] and d["V_div"]<float("inf"):
            L += [f"  AC={d['x_ac']:.2f}\"  SC={d['x_sc']:.2f}\"  e={d['e']:.2f}\""]
            L += [f"  V_div         : {d['V_div']:>8.0f} mph"]
            L += [f"  SF_div (divergence, Vd/V_div) :{mf(d['SF_div']-1)}"]
            if d["SF_div"]<1.5:
                L += ["  *** DIVERGENCE RISK — stiffness or SC review needed ***"]
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
                # Skin buckling: warn separately (expected in semi-monocoque)
                for sk_key in ("MS_skin_buckling", "MS_dcell_skin_buckling"):
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
                    if bk["MS_skin_buckling"] < 0 and "t_min_skin" in bk:
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
        fig.suptitle("AeroBeam v1.2 — Results", fontsize=12, color=PC_GOLD)
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
        a[3].set(title="Deflection [in]  (+up / -down)"); a[3].legend()
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
        x = self.x; c = self.chord_x
        # Plan view
        ax_top.fill_between(x, 0, c, alpha=0.10, color="steelblue")
        ax_top.plot(x, np.zeros_like(x), "k-", lw=1, label="LE")
        ax_top.plot(x, c, "k-", lw=1, label="TE")
        ax_top.plot(x, self.front_pct*c, "b-", lw=2.5, label="Front spar")
        if self.num_spars == 2:
            ax_top.plot(x, self.rear_pct*c, "r-", lw=1.5, label="Rear spar")
        if self.dcell:
            ax_top.fill_between(x, 0, self.front_pct*c, alpha=0.25,
                                color="cyan", label="D-cell")
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
        ax_top.set_ylabel("Chord [in]  LE to TE")
        ax_top.set_title("Plan View  (root at left, LE at top)")
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
        fig.suptitle("AeroBeam v1.2  Wing Geometry", fontsize=12)
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
            fig.suptitle("AeroBeam v1.2  —  Input Summary", fontsize=12,
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
            fig.suptitle("AeroBeam v1.2  —  Wing Geometry", fontsize=12,
                         y=0.98, color=PDF_GOLD, fontweight="bold")
            self.draw_geometry(ax_plan, ax_elev)
            plt.tight_layout(pad=2.5)
            pdf.savefig(fig); plt.close(fig)

            # ── Page 3: Analysis plots ────────────────────────────────────────
            fig, axs = plt.subplots(2, 2, figsize=(11, 8.5))
            fig.suptitle("AeroBeam v1.2  —  Analysis Results", fontsize=12,
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
            axs[1,1].set_title("Deflection [in]"); axs[1,1].legend(fontsize=8)

            for a in axs.flatten():
                a.set_xlabel("Span [in]")
                a.grid(True, alpha=0.4, linewidth=0.5)
            plt.tight_layout(); pdf.savefig(fig); plt.close(fig)

            # ── Page 4: Results summary (line-by-line coloured) ──────────────
            fig = plt.figure(figsize=(11, 8.5))
            fig.suptitle("AeroBeam v1.2  —  Results Summary", fontsize=12,
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
            "AeroBeam v1.2 — Input Summary","="*48,
            f"Span : {i[chr(98)]:.1f}in  Root chord: {self.root_chord:.1f}in  Tip: {self.tip_chord:.1f}in" + (f"  Taper from BL {self.taper_start_bl:.0f}in" if self.taper_start_bl > 0 else ""),
            f"Rib spacing: {self.rib_spacing:.1f}\"",
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
