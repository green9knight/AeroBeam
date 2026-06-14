"""Wing load calculations for preliminary spar sizing."""

from __future__ import annotations

from dataclasses import dataclass
from math import pi

GRAVITY_M_S2 = 9.80665


@dataclass(frozen=True)
class LoadCase:
    """Root loads for a symmetric wing under a limit maneuver load factor."""

    gross_weight_n: float
    span_m: float
    limit_load_factor: float
    safety_factor: float = 1.5
    distribution: str = "elliptical"

    def __post_init__(self) -> None:
        if self.gross_weight_n <= 0:
            raise ValueError("gross_weight_n must be positive")
        if self.span_m <= 0:
            raise ValueError("span_m must be positive")
        if self.limit_load_factor <= 0:
            raise ValueError("limit_load_factor must be positive")
        if self.safety_factor <= 0:
            raise ValueError("safety_factor must be positive")
        if self.distribution not in {"elliptical", "uniform"}:
            raise ValueError("distribution must be 'elliptical' or 'uniform'")

    @classmethod
    def from_aircraft_mass(
        cls,
        *,
        mass_kg: float,
        span_m: float,
        limit_load_factor: float,
        safety_factor: float = 1.5,
        distribution: str = "elliptical",
    ) -> "LoadCase":
        """Create a load case from aircraft mass and wing span."""

        if mass_kg <= 0:
            raise ValueError("mass_kg must be positive")
        return cls(
            gross_weight_n=mass_kg * GRAVITY_M_S2,
            span_m=span_m,
            limit_load_factor=limit_load_factor,
            safety_factor=safety_factor,
            distribution=distribution,
        )

    @property
    def ultimate_lift_n(self) -> float:
        """Total ultimate lift carried by the complete wing."""

        return self.gross_weight_n * self.limit_load_factor * self.safety_factor

    @property
    def root_shear_n(self) -> float:
        """Root shear force for one wing half."""

        return self.ultimate_lift_n / 2.0

    @property
    def root_bending_moment_nm(self) -> float:
        """Root bending moment for one wing half.

        Elliptical lift uses ``M = L b / (3 pi)``. Uniform lift uses
        ``M = L b / 8``. In both equations ``L`` is total wing lift and ``b``
        is full wing span.
        """

        if self.distribution == "elliptical":
            return self.ultimate_lift_n * self.span_m / (3.0 * pi)
        return self.ultimate_lift_n * self.span_m / 8.0
