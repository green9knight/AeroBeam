"""Rectangular box spar sizing routines."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from aerobeam.loads import LoadCase
from aerobeam.materials import Material


@dataclass(frozen=True)
class BoxSparGeometry:
    """A rectangular hollow box spar cross section."""

    width_m: float
    height_m: float
    wall_thickness_m: float

    def __post_init__(self) -> None:
        if self.width_m <= 0:
            raise ValueError("width_m must be positive")
        if self.height_m <= 0:
            raise ValueError("height_m must be positive")
        if self.wall_thickness_m <= 0:
            raise ValueError("wall_thickness_m must be positive")
        if 2.0 * self.wall_thickness_m >= min(self.width_m, self.height_m):
            raise ValueError("wall_thickness_m is too large for the spar dimensions")

    @property
    def inner_width_m(self) -> float:
        return self.width_m - 2.0 * self.wall_thickness_m

    @property
    def inner_height_m(self) -> float:
        return self.height_m - 2.0 * self.wall_thickness_m

    @property
    def area_m2(self) -> float:
        return self.width_m * self.height_m - self.inner_width_m * self.inner_height_m

    @property
    def second_moment_area_m4(self) -> float:
        outer = self.width_m * self.height_m**3
        inner = self.inner_width_m * self.inner_height_m**3
        return (outer - inner) / 12.0

    @property
    def section_modulus_m3(self) -> float:
        return self.second_moment_area_m4 / (self.height_m / 2.0)

    def mass_per_meter_kg_m(self, material: Material) -> float:
        return self.area_m2 * material.density_kg_m3

    def bending_stress_pa(self, root_moment_nm: float) -> float:
        return root_moment_nm / self.section_modulus_m3

    def shear_stress_pa(self, root_shear_n: float) -> float:
        # For a thin box spar, root shear is primarily carried by the two webs.
        web_area_m2 = 2.0 * self.wall_thickness_m * self.height_m
        return root_shear_n / web_area_m2


@dataclass(frozen=True)
class SparDesignResult:
    """Sizing output for a rectangular box spar."""

    geometry: BoxSparGeometry
    material: Material
    load_case: LoadCase
    bending_stress_pa: float
    shear_stress_pa: float

    @property
    def bending_margin(self) -> float:
        return self.material.bending_strength_pa / self.bending_stress_pa - 1.0

    @property
    def shear_margin(self) -> float:
        return self.material.shear_strength_pa / self.shear_stress_pa - 1.0

    @property
    def controlling_margin(self) -> float:
        return min(self.bending_margin, self.shear_margin)

    @property
    def mass_per_meter_kg_m(self) -> float:
        return self.geometry.mass_per_meter_kg_m(self.material)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the design."""

        return {
            "material": self.material.name,
            "load_case": {
                "distribution": self.load_case.distribution,
                "ultimate_lift_n": self.load_case.ultimate_lift_n,
                "root_shear_n": self.load_case.root_shear_n,
                "root_bending_moment_nm": self.load_case.root_bending_moment_nm,
            },
            "geometry": {
                "width_m": self.geometry.width_m,
                "height_m": self.geometry.height_m,
                "wall_thickness_m": self.geometry.wall_thickness_m,
                "area_m2": self.geometry.area_m2,
                "second_moment_area_m4": self.geometry.second_moment_area_m4,
                "section_modulus_m3": self.geometry.section_modulus_m3,
            },
            "stresses": {
                "bending_pa": self.bending_stress_pa,
                "shear_pa": self.shear_stress_pa,
            },
            "margins": {
                "bending": self.bending_margin,
                "shear": self.shear_margin,
                "controlling": self.controlling_margin,
            },
            "mass_per_meter_kg_m": self.mass_per_meter_kg_m,
        }


def size_box_spar(
    *,
    load_case: LoadCase,
    material: Material,
    width_m: float,
    height_m: float,
    min_wall_thickness_m: float = 0.0005,
    manufacturing_increment_m: float = 0.0001,
) -> SparDesignResult:
    """Size the thinnest rectangular box spar that satisfies stress margins."""

    if min_wall_thickness_m <= 0:
        raise ValueError("min_wall_thickness_m must be positive")
    if manufacturing_increment_m < 0:
        raise ValueError("manufacturing_increment_m cannot be negative")

    max_wall_thickness_m = min(width_m, height_m) * 0.49
    low = min_wall_thickness_m
    high = max_wall_thickness_m

    if low >= high:
        raise ValueError("min_wall_thickness_m is too large for the spar dimensions")
    if not _passes(load_case, material, width_m, height_m, high):
        raise ValueError("spar dimensions cannot satisfy the load case with this material")

    if _passes(load_case, material, width_m, height_m, low):
        wall_thickness_m = low
    else:
        for _ in range(80):
            mid = (low + high) / 2.0
            if _passes(load_case, material, width_m, height_m, mid):
                high = mid
            else:
                low = mid
        wall_thickness_m = high

    if manufacturing_increment_m:
        wall_thickness_m = _round_up(wall_thickness_m, manufacturing_increment_m)
        if wall_thickness_m >= max_wall_thickness_m:
            raise ValueError("manufacturing increment rounds thickness beyond valid geometry")

    return _evaluate(load_case, material, width_m, height_m, wall_thickness_m)


def _round_up(value: float, increment: float) -> float:
    return ceil(value / increment) * increment


def _passes(
    load_case: LoadCase,
    material: Material,
    width_m: float,
    height_m: float,
    wall_thickness_m: float,
) -> bool:
    result = _evaluate(load_case, material, width_m, height_m, wall_thickness_m)
    return result.bending_margin >= 0.0 and result.shear_margin >= 0.0


def _evaluate(
    load_case: LoadCase,
    material: Material,
    width_m: float,
    height_m: float,
    wall_thickness_m: float,
) -> SparDesignResult:
    geometry = BoxSparGeometry(width_m, height_m, wall_thickness_m)
    bending_stress_pa = geometry.bending_stress_pa(load_case.root_bending_moment_nm)
    shear_stress_pa = geometry.shear_stress_pa(load_case.root_shear_n)
    return SparDesignResult(
        geometry=geometry,
        material=material,
        load_case=load_case,
        bending_stress_pa=bending_stress_pa,
        shear_stress_pa=shear_stress_pa,
    )
