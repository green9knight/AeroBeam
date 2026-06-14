"""Material allowables used by AeroBeam sizing calculations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    """Basic material properties for preliminary spar sizing."""

    name: str
    density_kg_m3: float
    bending_strength_pa: float
    shear_strength_pa: float

    def __post_init__(self) -> None:
        if self.density_kg_m3 <= 0:
            raise ValueError("density_kg_m3 must be positive")
        if self.bending_strength_pa <= 0:
            raise ValueError("bending_strength_pa must be positive")
        if self.shear_strength_pa <= 0:
            raise ValueError("shear_strength_pa must be positive")


_MATERIALS = {
    "6061-t6": Material(
        name="6061-T6 aluminum",
        density_kg_m3=2700.0,
        bending_strength_pa=276e6,
        shear_strength_pa=207e6,
    ),
    "7075-t6": Material(
        name="7075-T6 aluminum",
        density_kg_m3=2810.0,
        bending_strength_pa=503e6,
        shear_strength_pa=331e6,
    ),
    "carbon-epoxy": Material(
        name="carbon-epoxy laminate",
        density_kg_m3=1600.0,
        bending_strength_pa=600e6,
        shear_strength_pa=80e6,
    ),
}


def get_material(name: str) -> Material:
    """Return a built-in material by name.

    Names are matched case-insensitively. Supported values are ``6061-T6``,
    ``7075-T6``, and ``carbon-epoxy``.
    """

    key = name.strip().lower()
    try:
        return _MATERIALS[key]
    except KeyError as exc:
        supported = ", ".join(sorted(_MATERIALS))
        raise ValueError(f"unknown material {name!r}; supported materials: {supported}") from exc
