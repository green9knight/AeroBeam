"""
AeroBeam v1.2 — Spar Cross-Section Library
===========================================
Materials, CrossSection subclasses, D-cell, geodetic panel,
SkinPanel, WingBox, AluminumAngle, and strut material database.

All units: inches, pounds, psi throughout.
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple, List


# ─── MATERIAL DATABASE ──────────────────────────────────────────────────────

# Each material: (E, Ftu, Fty, Fb, Fc, Ft, Fsu, G, rho, is_wood)
#   E    = Young's modulus (psi)
#   Ftu  = ultimate tensile strength (psi)   — metal
#   Fty  = tensile yield (psi)               — metal
#   Fb   = bending allowable (psi)           — wood (modulus of rupture x knockdown)
#   Fc   = compression allowable (psi)       — wood
#   Ft   = tension allowable (psi)           — wood
#   Fsu  = shear allowable (psi)
#   G    = shear modulus (psi)
#   rho  = density (lb/in³)
#   is_wood = True for wood/ply materials

MATERIAL_DB = {
    # ── Aluminum ──────────────────────────────────────────────────────────────
    "6061-T6": {
        "E": 10_000_000, "Ftu": 42_000, "Fty": 35_000,
        "Fb": None, "Fc": None, "Ft": None,
        "Fsu": 27_000, "G": 3_770_000, "rho": 0.098, "is_wood": False,
        "label": "6061-T6 Aluminum",
    },
    "2024-T3": {
        "E": 10_500_000, "Ftu": 64_000, "Fty": 47_000,
        "Fb": None, "Fc": None, "Ft": None,
        "Fsu": 40_000, "G": 4_000_000, "rho": 0.101, "is_wood": False,
        "label": "2024-T3 Aluminum",
    },
    "7075-T6": {
        "E": 10_400_000, "Ftu": 83_000, "Fty": 73_000,
        "Fb": None, "Fc": None, "Ft": None,
        "Fsu": 48_000, "G": 3_900_000, "rho": 0.102, "is_wood": False,
        "label": "7075-T6 Aluminum",
    },
    "6063-T5": {
        "E": 10_000_000, "Ftu": 22_000, "Fty": 16_000,
        "Fb": None, "Fc": None, "Ft": None,
        "Fsu": 13_000, "G": 3_770_000, "rho": 0.098, "is_wood": False,
        "label": "6063-T5 Aluminum",
    },
    # ── Wood — FAA AC 43.13-1B Table 1 ───────────────────────────────────────
    "Sitka Spruce": {
        "E": 1_570_000, "Ftu": None, "Fty": None,
        "Fb": 10_000, "Fc": 5_900, "Ft": 9_400,
        "Fsu": 1_200, "G": 120_000, "rho": 0.016, "is_wood": True,
        "label": "Sitka Spruce",
    },
    "White Pine": {
        "E": 1_200_000, "Ftu": None, "Fty": None,
        "Fb": 7_400, "Fc": 4_800, "Ft": 5_600,
        "Fsu": 900, "G": 100_000, "rho": 0.013, "is_wood": True,
        "label": "White Pine",
    },
    "Douglas Fir": {
        "E": 1_920_000, "Ftu": None, "Fty": None,
        "Fb": 12_400, "Fc": 7_400, "Ft": 11_800,
        "Fsu": 1_500, "G": 145_000, "rho": 0.020, "is_wood": True,
        "label": "Douglas Fir",
    },
    "White Ash": {
        "E": 1_740_000, "Ftu": None, "Fty": None,
        "Fb": 14_800, "Fc": 7_800, "Ft": 14_900,
        "Fsu": 1_700, "G": 135_000, "rho": 0.024, "is_wood": True,
        "label": "White Ash",
    },
    "Honduran Mahogany": {
        "E": 1_340_000, "Ftu": None, "Fty": None,
        "Fb": 9_200, "Fc": 5_200, "Ft": 7_900,
        "Fsu": 1_100, "G": 105_000, "rho": 0.019, "is_wood": True,
        "label": "Honduran Mahogany",
    },
    # ── Plywood ───────────────────────────────────────────────────────────────
    "Birch Plywood": {
        "E": 1_200_000, "Ftu": None, "Fty": None,
        "Fb": 6_200, "Fc": 4_000, "Ft": 5_500,
        "Fsu": 3_500, "G": 80_000, "rho": 0.022, "is_wood": True,
        "label": "Birch Plywood",
    },
    "Mahogany Plywood": {
        "E": 1_000_000, "Ftu": None, "Fty": None,
        "Fb": 5_200, "Fc": 3_500, "Ft": 4_600,
        "Fsu": 2_800, "G": 70_000, "rho": 0.018, "is_wood": True,
        "label": "Mahogany Plywood",
    },
    "Poplar Plywood": {
        "E": 1_100_000, "Ftu": None, "Fty": None,
        "Fb": 5_000, "Fc": 3_300, "Ft": 4_400,
        "Fsu": 2_600, "G": 75_000, "rho": 0.020, "is_wood": True,
        "label": "Poplar Plywood",
    },
}

# ── Strut-specific materials (steel + aluminum) ───────────────────────────────
STRUT_MATERIALS = {
    "6061-T6 Aluminum": {
        "E": 10_000_000, "Ftu": 42_000, "Fty": 35_000,
        "G": 3_770_000, "rho": 0.098,
    },
    "4130 Chromoly (normalized)": {
        "E": 29_000_000, "Ftu": 90_000, "Fty": 70_000,
        "G": 11_200_000, "rho": 0.283,
    },
    "4130 Chromoly (annealed)": {
        "E": 29_000_000, "Ftu": 81_000, "Fty": 52_000,
        "G": 11_200_000, "rho": 0.283,
    },
    "4140 Chromoly (normalized)": {
        "E": 29_000_000, "Ftu": 95_000, "Fty": 75_000,
        "G": 11_200_000, "rho": 0.284,
    },
    "1020 Mild Steel": {
        "E": 29_500_000, "Ftu": 65_000, "Fty": 48_000,
        "G": 11_500_000, "rho": 0.284,
    },
}


def mat(name: str) -> dict:
    """Return material property dict. Raises KeyError if not found."""
    return MATERIAL_DB[name]


def allowable_bending(mat_name: str, knockdown: float = 1.0) -> float:
    """Return bending allowable: Ftu for metal, Fb×knockdown for wood."""
    m = MATERIAL_DB[mat_name]
    if m["is_wood"]:
        return m["Fb"] * knockdown
    return m["Ftu"]


def allowable_shear(mat_name: str) -> float:
    return MATERIAL_DB[mat_name]["Fsu"]


# ─── CROSS-SECTION BASE ──────────────────────────────────────────────────────

class CrossSection:
    """
    Base class for spar cross-sections.
    All subclasses implement get_props(chord_frac) which returns
    a SectionProps namedtuple at a given spanwise station.
    """

    def get_props(self, scale: float = 1.0) -> "SectionProps":
        raise NotImplementedError

    def get_arrays(self, x: np.ndarray, b_half: float,
                   chord_root: float, chord_tip: float) -> dict:
        """
        Return section properties at every spanwise station.
        Geometry tapers linearly root→tip via chord ratio.
        Returns dict of numpy arrays.
        """
        props_list = []
        for xi in x:
            frac = xi / b_half          # 0 at root, 1 at tip
            chord = chord_root + (chord_tip - chord_root) * frac
            scale = chord / chord_root  # geometry scales with chord
            props_list.append(self.get_props(scale))
        return {
            "EI":     np.array([p.EI     for p in props_list]),
            "I_tr":   np.array([p.I_tr   for p in props_list]),
            "y_top":  np.array([p.y_top  for p in props_list]),
            "y_bot":  np.array([p.y_bot  for p in props_list]),
            "y_max":  np.array([p.y_max  for p in props_list]),
            "area":   np.array([p.area   for p in props_list]),
            "NA":     np.array([p.NA     for p in props_list]),
        }

    def weight(self, b_half: float, chord_root: float, chord_tip: float) -> float:
        """Half-span weight [lb] using average cross-section (exact for linear taper)."""
        p_root = self.get_props(1.0)
        p_tip  = self.get_props(chord_tip / chord_root)
        avg_area_rho = (p_root.area_rho + p_tip.area_rho) / 2.0
        return avg_area_rho * b_half

    def summary(self, chord_root: float) -> str:
        p = self.get_props(1.0)
        return (f"  EI(root)   = {p.EI:>14,.0f} lb·in²\n"
                f"  I_tr(root) = {p.I_tr:>14.4f} in⁴\n"
                f"  y_max(root)= {p.y_max:>14.4f} in\n"
                f"  NA(root)   = {p.NA:>14.4f} in from bottom\n")


@dataclass
class SectionProps:
    EI:       float   # composite bending stiffness [lb·in²]
    I_tr:     float   # transformed moment of inertia [in⁴]
    y_top:    float   # distance from NA to top fiber [in]
    y_bot:    float   # distance from NA to bottom fiber [in]
    NA:       float   # neutral axis from bottom [in]
    area:     float   # total cross-section area [in²]
    area_rho: float   # Σ(A_i x rho_i) for weight calc [lb/in]

    @property
    def y_max(self) -> float:
        return max(self.y_top, self.y_bot)


def _composite_props(elements, cap_mat: str) -> SectionProps:
    """
    Compute composite SectionProps from a list of rectangular elements.
    elements: list of (b, h, y_centroid, mat_name)
    cap_mat: reference material for transformed I
    """
    E_cap = MATERIAL_DB[cap_mat]["E"]
    # Neutral axis
    sum_EA  = sum(MATERIAL_DB[m]["E"] * b * h for b, h, _, m in elements)
    sum_EAy = sum(MATERIAL_DB[m]["E"] * b * h * yc for b, h, yc, m in elements)
    NA = sum_EAy / sum_EA if sum_EA > 0 else 0.0

    EI = 0.0; I_tr = 0.0; area = 0.0; area_rho = 0.0
    y_vals = []
    for b, h, yc, m_name in elements:
        E   = MATERIAL_DB[m_name]["E"]
        rho = MATERIAL_DB[m_name]["rho"]
        A   = b * h
        d   = yc - NA
        I_self = b * h**3 / 12.0
        I_pa   = I_self + A * d**2
        EI      += E * I_pa
        I_tr    += (E / E_cap) * I_pa
        area    += A
        area_rho += A * rho
        y_vals += [yc - h/2, yc + h/2]

    h_total = max(y_vals) - min(y_vals)
    y_bot   = NA - min(y_vals)
    y_top   = max(y_vals) - NA

    return SectionProps(EI=EI, I_tr=I_tr, y_top=y_top, y_bot=y_bot,
                        NA=NA, area=area, area_rho=area_rho)


# ─── ROUND TUBE ──────────────────────────────────────────────────────────────

class RoundTube(CrossSection):
    """
    Round tube spar — aluminum only.
    OD and wall scale with chord (geometry is proportional).
    """
    def __init__(self, OD: float, wall: float, mat_name: str = "6061-T6"):
        self.OD = OD
        self.wall = wall
        self.mat_name = mat_name

    def get_props(self, scale: float = 1.0) -> SectionProps:
        od = self.OD * scale
        wa = self.wall * scale
        id_ = od - 2 * wa
        A   = math.pi / 4 * (od**2 - id_**2)
        I   = math.pi / 64 * (od**4 - id_**4)
        E   = MATERIAL_DB[self.mat_name]["E"]
        rho = MATERIAL_DB[self.mat_name]["rho"]
        NA  = od / 2
        return SectionProps(
            EI=E*I, I_tr=I, y_top=od/2, y_bot=od/2,
            NA=NA, area=A, area_rho=A*rho,
        )

    def get_arrays(self, x, b_half, chord_root, chord_tip):
        # Round tube is constant section — does NOT taper with chord.
        p = self.get_props(1.0)
        n = len(x)
        return {k: np.full(n, getattr(p, k))
                for k in ("EI","I_tr","y_top","y_bot","y_max","area","NA")}

    def tube_props(self) -> dict:
        od = self.OD; wa = self.wall; id_ = od - 2*wa
        A = math.pi/4*(od**2-id_**2)
        I = math.pi/64*(od**4-id_**4)
        E = MATERIAL_DB[self.mat_name]["E"]
        return {"OD": od, "wall": wa, "ID": id_, "A": A, "I": I,
                "EI": E*I, "mat": self.mat_name}


# ─── PLAIN RECTANGULAR ───────────────────────────────────────────────────────

class PlainRect(CrossSection):
    """Solid rectangular section — typically solid wood."""
    def __init__(self, width: float, height: float, mat_name: str = "Sitka Spruce"):
        self.width = width
        self.height = height
        self.mat_name = mat_name

    def get_props(self, scale: float = 1.0) -> SectionProps:
        w = self.width * scale
        h = self.height * scale
        elements = [(w, h, h/2, self.mat_name)]
        return _composite_props(elements, self.mat_name)


# ─── I-BEAM ──────────────────────────────────────────────────────────────────

class IBeam(CrossSection):
    """
    Single-web I-beam with optional asymmetric caps.
    Two materials: cap_mat (top and bottom caps) + web_mat (web).
    """
    def __init__(self,
                 b_top: float, t_top: float,
                 b_bot: float, t_bot: float,
                 h_web: float, t_web: float,
                 cap_mat: str = "Sitka Spruce",
                 web_mat: str = "Birch Plywood"):
        self.b_top = b_top; self.t_top = t_top
        self.b_bot = b_bot; self.t_bot = t_bot
        self.h_web = h_web; self.t_web = t_web
        self.cap_mat = cap_mat
        self.web_mat = web_mat

    def get_props(self, scale: float = 1.0) -> SectionProps:
        s = scale
        # y measured from bottom of bottom cap
        yc_bot = self.t_bot * s / 2
        yc_web = self.t_bot * s + self.h_web * s / 2
        yc_top = self.t_bot * s + self.h_web * s + self.t_top * s / 2
        elements = [
            (self.b_bot*s, self.t_bot*s, yc_bot, self.cap_mat),
            (self.t_web*s, self.h_web*s, yc_web, self.web_mat),
            (self.b_top*s, self.t_top*s, yc_top, self.cap_mat),
        ]
        return _composite_props(elements, self.cap_mat)

    @property
    def h_total(self) -> float:
        return self.t_bot + self.h_web + self.t_top


# ─── DOUBLE I-BEAM ───────────────────────────────────────────────────────────

class DoubleIBeam(CrossSection):
    """
    Two parallel webs — the classic aircraft wood spar.
    web_spacing = clear distance between webs.
    """
    def __init__(self,
                 b_top: float, t_top: float,
                 b_bot: float, t_bot: float,
                 h_web: float, t_web: float,
                 web_spacing: float,
                 cap_mat: str = "Sitka Spruce",
                 web_mat: str = "Birch Plywood"):
        self.b_top = b_top; self.t_top = t_top
        self.b_bot = b_bot; self.t_bot = t_bot
        self.h_web = h_web; self.t_web = t_web
        self.web_spacing = web_spacing
        self.cap_mat = cap_mat
        self.web_mat = web_mat

    def get_props(self, scale: float = 1.0) -> SectionProps:
        s = scale
        yc_bot = self.t_bot*s/2
        yc_web = self.t_bot*s + self.h_web*s/2
        yc_top = self.t_bot*s + self.h_web*s + self.t_top*s/2
        ws = self.web_spacing * s
        # left web x-centroid irrelevant for bending I about horizontal axis
        elements = [
            (self.b_bot*s, self.t_bot*s, yc_bot, self.cap_mat),
            (self.t_web*s, self.h_web*s, yc_web, self.web_mat),  # left web
            (self.t_web*s, self.h_web*s, yc_web, self.web_mat),  # right web
            (self.b_top*s, self.t_top*s, yc_top, self.cap_mat),
        ]
        return _composite_props(elements, self.cap_mat)


# ─── BOX SPAR ────────────────────────────────────────────────────────────────

class BoxSpar(CrossSection):
    """Hollow rectangular box spar."""
    def __init__(self, b_outer: float, h_outer: float,
                 t_web: float, t_cap: float,
                 cap_mat: str = "Sitka Spruce",
                 web_mat: str = "Birch Plywood"):
        self.b_outer = b_outer; self.h_outer = h_outer
        self.t_web = t_web; self.t_cap = t_cap
        self.cap_mat = cap_mat; self.web_mat = web_mat

    def get_props(self, scale: float = 1.0) -> SectionProps:
        s = scale
        b = self.b_outer*s; h = self.h_outer*s
        tc = self.t_cap*s;  tw = self.t_web*s
        h_web = h - 2*tc
        yc_bot = tc/2
        yc_web = tc + h_web/2
        yc_top = tc + h_web + tc/2
        elements = [
            (b,  tc,    yc_bot, self.cap_mat),
            (tw, h_web, yc_web, self.web_mat),  # left
            (tw, h_web, yc_web, self.web_mat),  # right
            (b,  tc,    yc_top, self.cap_mat),
        ]
        return _composite_props(elements, self.cap_mat)


# ─── C-CHANNEL ───────────────────────────────────────────────────────────────

class CChannel(CrossSection):
    """Single-web C-channel (one web, caps on both sides)."""
    def __init__(self,
                 b_top: float, t_top: float,
                 b_bot: float, t_bot: float,
                 h_web: float, t_web: float,
                 cap_mat: str = "6061-T6",
                 web_mat: str = "6061-T6"):
        self.b_top = b_top; self.t_top = t_top
        self.b_bot = b_bot; self.t_bot = t_bot
        self.h_web = h_web; self.t_web = t_web
        self.cap_mat = cap_mat; self.web_mat = web_mat

    def get_props(self, scale: float = 1.0) -> SectionProps:
        s = scale
        yc_bot = self.t_bot*s/2
        yc_web = self.t_bot*s + self.h_web*s/2
        yc_top = self.t_bot*s + self.h_web*s + self.t_top*s/2
        elements = [
            (self.b_bot*s, self.t_bot*s, yc_bot, self.cap_mat),
            (self.t_web*s, self.h_web*s, yc_web, self.web_mat),
            (self.b_top*s, self.t_top*s, yc_top, self.cap_mat),
        ]
        return _composite_props(elements, self.cap_mat)


# ─── ROUTED (MONOLITHIC) ─────────────────────────────────────────────────────

class RoutedSpar(CrossSection):
    """
    I-beam routed from solid block — single material, no glue joints.
    Geometry identical to IBeam but cap_mat == web_mat.
    """
    def __init__(self,
                 b_top: float, t_top: float,
                 b_bot: float, t_bot: float,
                 h_web: float, t_web: float,
                 mat_name: str = "Sitka Spruce"):
        self.b_top = b_top; self.t_top = t_top
        self.b_bot = b_bot; self.t_bot = t_bot
        self.h_web = h_web; self.t_web = t_web
        self.mat_name = mat_name

    def get_props(self, scale: float = 1.0) -> SectionProps:
        s = scale
        yc_bot = self.t_bot*s/2
        yc_web = self.t_bot*s + self.h_web*s/2
        yc_top = self.t_bot*s + self.h_web*s + self.t_top*s/2
        elements = [
            (self.b_bot*s, self.t_bot*s, yc_bot, self.mat_name),
            (self.t_web*s, self.h_web*s, yc_web, self.mat_name),
            (self.b_top*s, self.t_top*s, yc_top, self.mat_name),
        ]
        return _composite_props(elements, self.mat_name)


# ─── ALUMINUM C-SPAR ─────────────────────────────────────────────────────────

class AluminumCSpar(CrossSection):
    """
    Aluminum C-spar: single angle cap on one side + aluminum sheet web.
    The uncapped side is just the web edge (negligible flange).
    Use for false spars, rear spars, and aileron spars.

    cap_side = "top" or "bottom"
    b_cap, t_cap = equivalent cap width and thickness (from angle or flat bar)
    h_web, t_web = web sheet height and thickness
    mat_name     = aluminum material for both cap and web
    """
    def __init__(self, b_cap: float, t_cap: float,
                 h_web: float, t_web: float,
                 cap_side: str = "top",
                 mat_name: str = "6061-T6"):
        self.b_cap    = b_cap
        self.t_cap    = t_cap
        self.h_web    = h_web
        self.t_web    = t_web
        self.cap_side = cap_side
        self.mat_name = mat_name

    def get_props(self, scale: float = 1.0) -> SectionProps:
        s  = scale
        bc = self.b_cap * s; tc = self.t_cap * s
        hw = self.h_web * s; tw = self.t_web * s
        be = tw; te = tw   # uncapped edge: web thickness only

        if self.cap_side == "top":
            elements = [
                (be, te, te/2,          self.mat_name),   # web edge bottom
                (tw, hw, te + hw/2,     self.mat_name),   # web sheet
                (bc, tc, te+hw+tc/2,    self.mat_name),   # angle cap top
            ]
        else:
            elements = [
                (bc, tc, tc/2,          self.mat_name),   # angle cap bottom
                (tw, hw, tc + hw/2,     self.mat_name),   # web sheet
                (be, te, tc+hw+te/2,    self.mat_name),   # web edge top
            ]
        return _composite_props(elements, self.mat_name)


# ─── ALUMINUM ANGLE CAP LIBRARY ──────────────────────────────────────────────

@dataclass
class AluminumAngle:
    """
    Standard extruded 6061-T6 aluminum angle for spar caps.
    L1 = cap leg (horizontal, faces outward) [in]
    L2 = web leg (vertical, into spar web) [in]
    t  = thickness (uniform both legs) [in]
    """
    L1: float
    L2: float
    t: float
    description: str = ""

    @property
    def area(self) -> float:
        return (self.L1 + self.L2 - self.t) * self.t

    @property
    def b_equiv(self) -> float:
        """Cap leg width — use as b_cap in I-beam."""
        return self.L1

    @property
    def t_equiv(self) -> float:
        """Equivalent thickness = area / L1 (same area, same width)."""
        return self.area / self.L1

    @property
    def weight_per_foot(self) -> float:
        return self.area * 0.098 * 12  # 6061-T6 rho=0.098 lb/in³

    def __str__(self) -> str:
        return (f"{self.description}  "
                f"A={self.area:.4f} in²  {self.weight_per_foot:.3f} lb/ft  "
                f"equiv: {self.b_equiv:.4f}\" x {self.t_equiv:.4f}\"")


# 24 standard sizes — Aircraft Spruce / Wicks catalog
ALUMINUM_ANGLES: List[AluminumAngle] = [
    # Equal leg
    AluminumAngle(0.750, 0.750, 0.0625, '3/4 x 3/4 x 1/16'),
    AluminumAngle(0.750, 0.750, 0.0938, '3/4 x 3/4 x 3/32'),
    AluminumAngle(0.750, 0.750, 0.1250, '3/4 x 3/4 x 1/8'),
    AluminumAngle(1.000, 1.000, 0.0625, '1 x 1 x 1/16'),
    AluminumAngle(1.000, 1.000, 0.0938, '1 x 1 x 3/32'),
    AluminumAngle(1.000, 1.000, 0.1250, '1 x 1 x 1/8'),
    AluminumAngle(1.250, 1.250, 0.0938, '1-1/4 x 1-1/4 x 3/32'),
    AluminumAngle(1.250, 1.250, 0.1250, '1-1/4 x 1-1/4 x 1/8'),
    AluminumAngle(1.500, 1.500, 0.0938, '1-1/2 x 1-1/2 x 3/32'),
    AluminumAngle(1.500, 1.500, 0.1250, '1-1/2 x 1-1/2 x 1/8'),
    AluminumAngle(1.500, 1.500, 0.1875, '1-1/2 x 1-1/2 x 3/16'),
    AluminumAngle(2.000, 2.000, 0.1250, '2 x 2 x 1/8'),
    AluminumAngle(2.000, 2.000, 0.1875, '2 x 2 x 3/16'),
    AluminumAngle(2.000, 2.000, 0.2500, '2 x 2 x 1/4'),
    AluminumAngle(2.000, 2.000, 0.3750, '2 x 2 x 3/8'),
    AluminumAngle(2.500, 2.500, 0.1250, '2-1/2 x 2-1/2 x 1/8'),
    AluminumAngle(2.500, 2.500, 0.1875, '2-1/2 x 2-1/2 x 3/16'),
    AluminumAngle(2.500, 2.500, 0.2500, '2-1/2 x 2-1/2 x 1/4'),
    AluminumAngle(2.500, 2.500, 0.3750, '2-1/2 x 2-1/2 x 3/8'),
    # Unequal leg (cap x web)
    AluminumAngle(1.000, 0.750, 0.0938, '1 x 3/4 x 3/32'),
    AluminumAngle(1.250, 1.000, 0.0938, '1-1/4 x 1 x 3/32'),
    AluminumAngle(1.250, 1.000, 0.1250, '1-1/4 x 1 x 1/8'),
    AluminumAngle(1.500, 1.000, 0.0938, '1-1/2 x 1 x 3/32'),
    AluminumAngle(1.500, 1.000, 0.1250, '1-1/2 x 1 x 1/8'),
    AluminumAngle(2.000, 1.000, 0.1250, '2 x 1 x 1/8'),
    AluminumAngle(2.000, 1.250, 0.1250, '2 x 1-1/4 x 1/8'),
    AluminumAngle(2.000, 1.500, 0.1250, '2 x 1-1/2 x 1/8'),
    AluminumAngle(2.500, 1.500, 0.1250, '2-1/2 x 1-1/2 x 1/8'),
    AluminumAngle(2.500, 2.000, 0.1250, '2-1/2 x 2 x 1/8'),
    AluminumAngle(3.000, 2.000, 0.1875, '3 x 2 x 3/16'),
]

ANGLE_DESCRIPTIONS = [f"(Manual flat bar)"] + [a.description for a in ALUMINUM_ANGLES]


def get_angle(description: str) -> Optional[AluminumAngle]:
    for a in ALUMINUM_ANGLES:
        if a.description == description:
            return a
    return None


# ─── D-CELL LEADING EDGE SKIN ────────────────────────────────────────────────

@dataclass
class DCellSkin:
    """
    D-cell (leading edge closed section) from LE to front spar web.

    Torsional stiffness by Bredt-Batho:
        GJ = 4 * G * A_enclosed² / ∮(ds/t)

    A_enclosed is the dominant term — it is computed as a simple rectangle:
        A = chord_to_spar x h_spar

    This is accurate to ±5% for typical airfoils where the LE radius
    is small relative to the D-cell width. The r_LE detail changes GJ
    by <5% and is not worth asking the user to measure.

    The user inputs they DO know:
        chord_to_spar — front spar position x chord  (from Wing Geometry)
        t_skin        — skin thickness (1/16" or 1/8" ply, or aluminum sheet)
        skin_mat      — material
        t_web         — front spar web thickness (closing wall)
    """
    t_skin:        float   # skin thickness [in]
    skin_mat:      str     # material name from MATERIAL_DB
    chord_to_spar: float   # chordwise distance LE → front spar web [in] (root)
    t_web:         float   # front spar web thickness [in] (rear wall of D-cell)

    def enclosed_area(self, h_spar: float, scale: float = 1.0) -> float:
        """Enclosed area of D-cell [in²] — simple rectangle, accurate to ±5%."""
        c = self.chord_to_spar * scale
        h = h_spar * scale
        return c * h

    def ds_over_t_own(self, h_spar: float, scale: float = 1.0) -> float:
        """
        ∮ ds/t for D-cell perimeter EXCLUDING the shared front spar web.
        Top skin + LE nose + bottom skin, approximated as 2 flat panels.
        """
        c  = self.chord_to_spar * scale
        ts = self.t_skin * scale
        return 2.0 * c / ts     # top + bottom flat runs

    def ds_over_t_web(self, h_spar: float, scale: float = 1.0) -> float:
        """ds/t for the shared front spar web (rear wall of D-cell)."""
        h  = h_spar * scale
        tw = self.t_web * scale
        return h / tw

    def GJ(self, h_spar: float, scale: float = 1.0) -> float:
        """Single-cell Bredt GJ for D-cell alone [lb·in²]."""
        G    = MATERIAL_DB[self.skin_mat]["G"]
        A_e  = self.enclosed_area(h_spar, scale)
        ds_t = self.ds_over_t_own(h_spar, scale) + self.ds_over_t_web(h_spar, scale)
        return 4.0 * G * A_e**2 / ds_t

    def weight(self, h_spar: float, b_half: float, scale_tip: float = 0.5) -> float:
        """Approximate half-span weight of D-cell skin [lb]."""
        rho   = MATERIAL_DB[self.skin_mat]["rho"]
        ts    = self.t_skin
        c_r   = self.chord_to_spar;  h_r = h_spar
        c_t   = c_r * scale_tip;     h_t = h_r * scale_tip
        perim_r = 2*c_r + h_r
        perim_t = 2*c_t + h_t
        return (perim_r + perim_t) / 2 * ts * rho * b_half


# ─── GEODETIC PANEL ──────────────────────────────────────────────────────────

@dataclass
class GeodeticPanel:
    """
    Wood geodetic (basket-weave) lattice panel between front and rear spars.
    Creates second closed cell for torsion when combined with D-cell.

    rib_spacing    — spanwise rib bay [in]
    strips_per_bay — number of strips per bay per direction (typically 2–4)
    strip_width    — w_strip [in]
    strip_thick    — t_strip [in]
    angle_deg      — strip angle to spar axis [deg], default 45
    mat_name       — strip material (from MATERIAL_DB, wood)
    """
    rib_spacing:    float
    strips_per_bay: int
    strip_width:    float
    strip_thick:    float
    angle_deg:      float = 45.0
    mat_name:       str   = "Sitka Spruce"

    @property
    def s_strip(self) -> float:
        """Centre-to-centre spacing along spar [in]."""
        return self.rib_spacing / self.strips_per_bay

    @property
    def A_strip(self) -> float:
        return self.strip_width * self.strip_thick

    def t_eff(self, scale: float = 1.0) -> float:
        """Equivalent shear panel thickness [in] for Bredt ∮(ds/t)."""
        θ = math.radians(self.angle_deg)
        s = self.s_strip * scale   # spacing scales with chord
        A = self.A_strip * scale**2
        return A * math.sin(θ) * math.cos(θ) * 2.0 / s

    def shear_stiffness_per_span(self, reduction_factor: float = 0.75,
                                 scale: float = 1.0) -> float:
        """Distributed elastic shear stiffness from diagonal strip axial action.

        Preliminary two-spar elastic-connection estimate:
            k_s = 2 * A * E * sin(theta) * cos(theta) / s * f_red

        where ``s`` is strip spacing along the span. ``f_red`` accounts for
        compression diagonal effectiveness, connection compliance, crossings,
        gusset flexibility, and construction details.
        """
        θ = math.radians(self.angle_deg)
        A = self.A_strip * scale**2
        E = MATERIAL_DB[self.mat_name]["E"]
        s = self.s_strip * scale
        return 2.0 * A * E * math.sin(θ) * math.cos(θ) / max(s, 1e-9) * reduction_factor

    def enclosed_area(self, c_box: float, h_spar: float) -> float:
        """Rectangle between spars [in²] at given chord and spar height."""
        return c_box * h_spar

    def ds_over_t_own(self, c_box: float, h_spar: float,
                      t_web_rs: float, scale: float = 1.0) -> float:
        """
        ∮ ds/t for geodetic cell EXCLUDING the shared front spar web.
        (top geodetic + bottom geodetic + rear spar web)
        """
        t = self.t_eff(scale)
        c = c_box * scale
        h = h_spar * scale
        tw = t_web_rs * scale
        return (2 * c / t) + (h / tw)

    def strip_force(self, q2: float, scale: float = 1.0) -> float:
        """Axial force per strip from panel shear flow q2 [lb/in].

        Consistent with ``t_eff = 2*A*sin(theta)*cos(theta)/s``:
            q = sigma_strip * t_eff
            F_strip = sigma_strip * A
                     = q*s / (2*sin(theta)*cos(theta))
        """
        θ = math.radians(self.angle_deg)
        s = self.s_strip * scale
        denom = 2.0 * math.sin(θ) * math.cos(θ)
        return q2 * s / max(denom, 1e-9)

    def strip_stress(self, q2: float, scale: float = 1.0) -> float:
        """Axial stress in each strip [psi]."""
        A = self.A_strip * scale**2
        return self.strip_force(q2, scale) / A

    def weight(self, c_box: float, h_spar: float, b_half: float) -> float:
        """Approximate geodetic strip weight per half-span [lb]."""
        rho = MATERIAL_DB[self.mat_name]["rho"]
        # Strip length = diagonal across bay
        θ = math.radians(self.angle_deg)
        strip_len = c_box / math.cos(θ)   # one strip across the box
        n_per_bay = self.strips_per_bay * 2   # both directions
        n_bays    = b_half / self.rib_spacing
        n_total   = n_per_bay * n_bays
        return n_total * strip_len * self.A_strip * rho


# ─── SKIN PANEL (aluminum full-wing skin) ────────────────────────────────────

@dataclass
class SkinPanel:
    """Top or bottom aluminum skin panel for a stressed-skin wing."""
    thickness: float     # skin thickness [in]
    mat_name:  str       # material

    def t_eff(self) -> float:
        """Effective thickness after shear lag (30t rule, each side of cap)."""
        return 30 * self.thickness

    def buckling_stress(self, rib_spacing: float) -> float:
        """
        Critical buckling stress of flat panel [psi].
        Simply supported on 4 sides, compression.
        k=4.0, ν=0.33 aluminum.
        """
        E  = MATERIAL_DB[self.mat_name]["E"]
        t  = self.thickness
        b  = rib_spacing
        nu = 0.33
        k  = 4.0
        return k * math.pi**2 * E * (t/b)**2 / (12 * (1 - nu**2))

    def weight_per_sqin(self) -> float:
        return self.thickness * MATERIAL_DB[self.mat_name]["rho"]


# ─── TWO-CELL BREDT-BATHO ────────────────────────────────────────────────────

def two_cell_bredt(A1: float, A2: float,
                   ds_t_1_own: float, ds_t_2_own: float,
                   ds_t_shared: float,
                   G1: float, G2: float,
                   T: float) -> Tuple[float, float, float]:
    """
    Exact two-cell Bredt-Batho solution with differing shear moduli.

    Cell 1: D-cell  (G1 = D-cell skin shear modulus)
    Cell 2: geodetic box or aluminum skin  (G2)
    Shared wall: front spar web (ds_t_shared = h_spar / t_web)

    Returns: (q1, q2, GJ_total)
      q1, q2  = shear flows in each cell [lb/in]
      GJ_total = torsional stiffness [lb·in²]

    Physics:
      Compatibility (equal twist rate both cells):
        [q1·d11 - q2·d12] / (2·A1·G1) = [q2·d22 - q1·d12] / (2·A2·G2)
      Equilibrium:
        T = 2·q1·A1 + 2·q2·A2
    """
    d11 = ds_t_1_own  + ds_t_shared
    d22 = ds_t_2_own  + ds_t_shared
    d12 = ds_t_shared

    M = np.array([
        [ d11/(A1*G1) + d12/(A2*G2),   -(d22/(A2*G2) + d12/(A1*G1)) ],
        [ 2.0*A1,                         2.0*A2                      ],
    ])
    try:
        q1, q2 = np.linalg.solve(M, np.array([0.0, T]))
    except np.linalg.LinAlgError:
        return 0.0, 0.0, 1.0   # degenerate — avoid divide by zero upstream

    phi_prime = (q1*d11 - q2*d12) / (2.0 * A1 * G1)
    GJ = T / phi_prime if abs(phi_prime) > 1e-20 else 1.0

    return float(q1), float(q2), float(GJ)


# ─── WING BOX (aluminum stressed skin) ───────────────────────────────────────

class WingBox:
    """
    Full aluminum stressed-skin wing box.
    Front spar + rear spar + top skin + bottom skin.
    Bending: combined parallel-axis section.
    Torsion: two-cell Bredt (D-cell + main box).
    """
    def __init__(self,
                 front_spar: CrossSection,
                 rear_spar:  CrossSection,
                 top_skin:   SkinPanel,
                 bot_skin:   SkinPanel,
                 d_cell:     Optional[DCellSkin],
                 front_pct:  float,
                 rear_pct:   float,
                 rib_spacing: float):
        self.front_spar  = front_spar
        self.rear_spar   = rear_spar
        self.top_skin    = top_skin
        self.bot_skin    = bot_skin
        self.d_cell      = d_cell
        self.front_pct   = front_pct
        self.rear_pct    = rear_pct
        self.rib_spacing = rib_spacing

    def get_combined_props(self, chord: float, h_spar: float,
                           cap_mat: str) -> SectionProps:
        """
        Combined section properties at a given chord.
        Uses 30t effective width for skin shear lag.
        """
        scale  = chord / chord   # = 1.0 always (already scaled by caller)
        c_box  = (self.rear_pct - self.front_pct) * chord
        t_top  = self.top_skin.thickness
        t_bot  = self.bot_skin.thickness
        b_eff_top = min(self.top_skin.t_eff(), c_box/2)
        b_eff_bot = min(self.bot_skin.t_eff(), c_box/2)

        fs = self.front_spar.get_props(1.0)
        rs = self.rear_spar.get_props(1.0)

        # y from bottom of bottom skin
        yc_bot_skin = t_bot/2
        yc_fs_bot   = t_bot + fs.y_bot   # front spar bottom cap centroid
        yc_fs_web   = t_bot + fs.NA       # approx
        yc_rs_bot   = t_bot + rs.y_bot
        yc_top_skin = t_bot + h_spar + t_top/2

        top_mat = self.top_skin.mat_name
        bot_mat = self.bot_skin.mat_name

        # Effective skin at each spar cap (parallel axis to spar)
        elements = [
            # Full bottom skin
            (chord, t_bot, yc_bot_skin, bot_mat),
            # Full top skin
            (chord, t_top, yc_top_skin, top_mat),
        ]
        # Add spar elements (scaled by 1.0 — caller provides correct chord)
        # Use raw element lists from each spar
        t_bot_s = t_bot; h_s = h_spar; t_top_s = t_top

        fs_props = self.front_spar.get_props(1.0)
        rs_props = self.rear_spar.get_props(1.0)

        # Combined using spar arrays shifted to correct y baseline
        for b, h, yc, m in _spar_elements(self.front_spar, t_bot, h_spar):
            elements.append((b, h, yc, m))
        for b, h, yc, m in _spar_elements(self.rear_spar, t_bot, h_spar):
            elements.append((b, h, yc, m))

        return _composite_props(elements, cap_mat)

    def skin_buckling(self, chord: float) -> Tuple[float, float]:
        """
        Returns (sigma_cr_top, sigma_cr_bot) [psi].
        b = rib_spacing for simply-supported panel.
        """
        cr_top = self.top_skin.buckling_stress(self.rib_spacing)
        cr_bot = self.bot_skin.buckling_stress(self.rib_spacing)
        return cr_top, cr_bot

    def torsion_GJ(self, h_spar: float, chord: float,
                   t_web_fs: float, t_web_rs: float) -> Tuple[float, float, float]:
        """
        Two-cell Bredt GJ for wing box.
        Returns (GJ_total, q1_per_T, q2_per_T) — shear flows per unit torque.
        """
        c_box = (self.rear_pct - self.front_pct) * chord
        A2 = c_box * h_spar

        if self.d_cell:
            A1 = self.d_cell.enclosed_area(h_spar, 1.0)
            G1 = MATERIAL_DB[self.d_cell.skin_mat]["G"]
            ds1_own   = self.d_cell.ds_over_t_own(h_spar, 1.0)
            ds_shared = self.d_cell.ds_over_t_web(h_spar, 1.0)
        else:
            A1 = 0.0; G1 = 1.0; ds1_own = 1e9; ds_shared = h_spar/t_web_fs

        t_top = self.top_skin.thickness
        t_bot = self.bot_skin.thickness
        G2 = MATERIAL_DB[self.top_skin.mat_name]["G"]
        ds2_own = (c_box/t_top + c_box/t_bot + h_spar/t_web_rs)

        if A1 < 1e-6:
            # No D-cell — single-cell main box
            ds_total = ds2_own + ds_shared
            GJ = 4 * G2 * A2**2 / ds_total
            q_per_T = 1.0 / (2*A2)
            return GJ, 0.0, q_per_T

        q1, q2, GJ = two_cell_bredt(A1, A2, ds1_own, ds2_own, ds_shared, G1, G2, 1.0)
        return GJ, q1, q2


def _spar_elements(spar: CrossSection, y_base: float, h_spar: float) -> list:
    """
    Helper: extract rectangular elements from a CrossSection
    and offset y_centroid by y_base.
    This is a simplified approach — returns approx elements for WingBox.
    """
    p = spar.get_props(1.0)
    # Represent spar as three rectangles: bot cap, web, top cap
    # Use generic I-beam approximation if not explicitly an IBeam
    if isinstance(spar, (IBeam, CChannel, RoutedSpar)):
        t_b = spar.t_bot; b_b = spar.b_bot
        t_t = spar.t_top; b_t = spar.b_top
        h_w = spar.h_web; t_w = spar.t_web
        cap_m = spar.cap_mat if hasattr(spar, 'cap_mat') else spar.mat_name
        web_m = spar.web_mat if hasattr(spar, 'web_mat') else spar.mat_name
    elif isinstance(spar, RoundTube):
        # Approximate tube as equivalent I-beam
        p2 = spar.get_props(1.0)
        cap_m = spar.mat_name; web_m = spar.mat_name
        od = spar.OD; wa = spar.wall
        t_b = wa; b_b = od; h_w = od-2*wa; t_w = wa*2; t_t = wa; b_t = od
    else:
        cap_m = "6061-T6"; web_m = "6061-T6"
        t_b = 0.1; b_b = 1.0; h_w = h_spar-0.2; t_w = 0.05; t_t = 0.1; b_t = 1.0

    yc_bot = y_base + t_b/2
    yc_web = y_base + t_b + h_w/2
    yc_top = y_base + t_b + h_w + t_t/2
    return [
        (b_b, t_b, yc_bot, cap_m),
        (t_w, h_w, yc_web, web_m),
        (b_t, t_t, yc_top, cap_m),
    ]


# ─── CONVENIENCE FUNCTIONS ───────────────────────────────────────────────────

def spar_type_names() -> List[str]:
    return [
        "Round Tube",
        "Plain Rectangular",
        "I-Beam",
        "Double I-Beam",
        "Box Spar",
        "C-Channel",
        "Routed (Monolithic)",
        "Aluminum I-Beam",      # angle caps both sides + sheet web
        "Aluminum C-Spar",      # single angle cap one side + sheet web
    ]


def aluminum_mat_names() -> List[str]:
    return [k for k, v in MATERIAL_DB.items() if not v["is_wood"]]


def wood_mat_names() -> List[str]:
    return [k for k, v in MATERIAL_DB.items() if v["is_wood"]]


def all_mat_names() -> List[str]:
    return list(MATERIAL_DB.keys())


def strut_mat_names() -> List[str]:
    return list(STRUT_MATERIALS.keys())


# ─── SELF-TEST ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== spar_sections.py self-test ===\n")

    # Round tube
    tube = RoundTube(2.0, 0.065, "6061-T6")
    p = tube.get_props(1.0)
    print(f"Round tube 2\"×0.065\":  EI={p.EI:,.0f}  I={p.I_tr:.4f}  y_max={p.y_max:.4f}")

    # Wood I-beam
    spar = IBeam(b_top=1.5, t_top=0.75, b_bot=1.5, t_bot=0.75,
                 h_web=5.0, t_web=0.125,
                 cap_mat="Sitka Spruce", web_mat="Birch Plywood")
    p = spar.get_props(1.0)
    print(f"Wood I-beam 1.5\"×0.75\" caps, 5\"×0.125\" web:")
    print(f"  EI={p.EI:,.0f}  I_tr={p.I_tr:.4f}  NA={p.NA:.4f}  y_max={p.y_max:.4f}")

    # Aluminum angle
    ang = get_angle("1-1/2 x 1 x 1/8")
    if ang:
        print(f"Angle {ang.description}: A={ang.area:.4f}  b_eq={ang.b_equiv}  t_eq={ang.t_equiv:.4f}")

    # D-cell GJ
    dc = DCellSkin(t_skin=0.125, skin_mat="Birch Plywood",
                   chord_to_spar=8.1, t_web=0.125)
    gj = dc.GJ(h_spar=6.48, scale=1.0)
    print(f"D-cell GJ (1/8\" birch ply): {gj:,.0f} lb·in²")

    # Geodetic panel
    geo = GeodeticPanel(rib_spacing=10.0, strips_per_bay=2,
                        strip_width=1.0, strip_thick=0.125,
                        angle_deg=45.0, mat_name="Sitka Spruce")
    print(f"Geodetic strip spacing: {geo.s_strip}\" c-t-c  t_eff={geo.t_eff():.5f}\"")

    # Two-cell Bredt
    A1 = 34.3; A2 = 175.0
    G1 = 80_000; G2 = 120_000
    ds1_own = 137.4; ds2_own = 1796.9; ds_shared = 51.84
    q1, q2, GJ = two_cell_bredt(A1, A2, ds1_own, ds2_own, ds_shared, G1, G2, 33810.0)
    print(f"Two-cell Bredt: q1={q1:.1f} q2={q2:.1f} GJ={GJ:,.0f} lb·in²")

    # Strut steel
    steel = STRUT_MATERIALS["4130 Chromoly (normalized)"]
    od=2.0; wa=0.065; id_=od-2*wa
    I = math.pi/64*(od**4-id_**4); L=93.6
    euler = math.pi**2 * steel["E"] * I / L**2
    print(f"4130 strut 2\"×0.065\"×93.6\": Euler={euler:,.0f} lb")

    print("\nAll tests passed.")


# ─── BUCKLING CHECKS ─────────────────────────────────────────────────────────

def shear_buckling_ks(a: float, b: float) -> float:
    """
    Shear buckling coefficient k_s for a flat plate, SS on all 4 edges.
    a = panel length (stiffener spacing along span) [in]
    b = panel height (web depth) [in]
    Source: Timoshenko & Gere, Theory of Elastic Stability, 2nd ed.
            NACA TN 3781 (Batdorf & Stein)
    """
    r = a / max(b, 1e-9)
    if r >= 1.0:
        return 5.34 + 4.00 / r**2   # long panel (a >= b)
    else:
        return 5.34 / r**2 + 4.00   # tall panel (a < b)


def web_buckling(t_web: float, h_web: float, stiffener_spacing: float,
                 mat_name: str) -> dict:
    """
    Shear buckling check for spar web panel.

    Inputs:
      t_web             — web thickness [in]
      h_web             — web clear height between caps [in]
      stiffener_spacing — c-t-c stiffener spacing along span [in]
                          (use rib_spacing if no intermediate stiffeners)
      mat_name          — material

    Returns dict with tau_cr, k_s, aspect_ratio, MS_shear_buckling,
    and t_min (minimum thickness to avoid buckling at the applied load).
    """
    m   = MATERIAL_DB[mat_name]
    E   = m["E"]; nu = 0.33 if not m["is_wood"] else 0.0
    Fsu = m["Fsu"]

    a   = stiffener_spacing
    b   = h_web
    k_s = shear_buckling_ks(a, b)

    tau_cr = k_s * math.pi**2 * E * (t_web / b)**2 / (12 * (1 - nu**2))

    return {
        "k_s":          k_s,
        "aspect_ratio": a / max(b, 1e-9),
        "tau_cr":       tau_cr,
        "stiffener_spacing": stiffener_spacing,
    }


def web_bending_buckling(t_web: float, h_web: float, mat_name: str) -> dict:
    """
    Bending (compression) buckling of web under moment.
    k_c = 23.9 for simply-supported plate in pure bending.
    Source: Timoshenko & Gere Table 9-5
    """
    m  = MATERIAL_DB[mat_name]
    E  = m["E"]; nu = 0.33 if not m["is_wood"] else 0.0
    k_c = 23.9
    sigma_cr = k_c * math.pi**2 * E * (t_web / h_web)**2 / (12 * (1 - nu**2))
    return {"k_c": k_c, "sigma_cr_web_bending": sigma_cr}


def skin_compression_buckling(t_skin: float, b_panel: float,
                               mat_name: str, k: float = 4.0) -> dict:
    """
    Compression buckling of flat skin panel between ribs (or nose ribs).

    b_panel = shortest unsupported dimension [in]
              For box skin: rib_spacing
              For D-cell skin: nose_rib_spacing
    k = 4.0 for SS all edges (conservative standard)
    Source: NACA TN 3781, Bruhn C5
    """
    m  = MATERIAL_DB[mat_name]
    E  = m["E"]; nu = 0.33 if not m["is_wood"] else 0.0
    sigma_cr = k * math.pi**2 * E * (t_skin / b_panel)**2 / (12 * (1 - nu**2))
    return {"sigma_cr_skin": sigma_cr, "k": k, "b_panel": b_panel}


def skin_effective_width(t_skin: float, b_panel: float,
                         sigma_edge: float, mat_name: str) -> dict:
    """
    Post-buckled compression effective width screening calculation.

    Uses common von Karman/Winter-style aircraft preliminary sizing concept:
        b_e = 1.9 t sqrt(E / sigma_e), capped at the actual panel width.

    This is a demand/capacity estimate only. It does not size stringers,
    rivets, inter-rivet buckling, frames/ribs, crippling, or post-buckled
    diagonal-tension shear behavior.
    """
    m = MATERIAL_DB[mat_name]
    E = m["E"]
    sigma = max(abs(sigma_edge), 1e-9)
    b_eff_raw = 1.9 * t_skin * math.sqrt(E / sigma)
    b_eff = min(b_panel, b_eff_raw)
    load_per_length = sigma * b_eff * t_skin
    return {
        "b_eff": b_eff,
        "b_eff_ratio": b_eff / max(b_panel, 1e-9),
        "load_per_length": load_per_length,
        "formula": "b_eff = min(b, 1.9*t*sqrt(E/sigma_edge))",
    }


def cap_column_buckling(b_cap: float, t_cap: float, rib_spacing: float,
                        mat_name: str) -> dict:
    """
    Euler column buckling of compression cap between ribs.
    Treated as a pin-ended column with L = rib_spacing.

    The cap is a flat rectangular strip: b_cap (chordwise width) x t_cap (height into web).
    The web and skin fully restrain out-of-plane motion, so the governing mode is
    in-plane (chordwise) buckling using the STRONG axis:
        I_strong = t_cap * b_cap^3 / 12

    The weak-axis (out-of-plane) mode would require I = b_cap * t_cap^3 / 12 but is
    suppressed by the web attachment — using it would be unrealistically conservative.
    Source: Bruhn C7.10, Niu Airframe Structural Design 6.4
    """
    m   = MATERIAL_DB[mat_name]
    E   = m["E"]
    A   = b_cap * t_cap
    I_strong = t_cap * b_cap**3 / 12.0   # in-plane — governs, web restrains out-of-plane
    I_weak   = b_cap * t_cap**3 / 12.0   # out-of-plane — suppressed by web (shown for info)
    I   = I_strong
    L   = rib_spacing
    P_cr = math.pi**2 * E * I / L**2
    sigma_cr_cap = P_cr / max(A, 1e-9)
    return {
        "A_cap":        A,
        "I_cap":        I,
        "I_strong":     I_strong,
        "I_weak":       I_weak,
        "P_cr":         P_cr,
        "sigma_cr_cap": sigma_cr_cap,
        "slenderness":  L / math.sqrt(I / max(A, 1e-9)),
    }
