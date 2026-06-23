"""
Common 6061-T6 Aluminum Round Tube Spar Sizes
For use in ultralight / experimental aircraft wing spars.

Data based on common aircraft supply sizes (Aircraft Spruce, Wicks, etc.)
"""

from dataclasses import dataclass
from typing import List
import numpy as np

E_6061_T6 = 10_000_000  # psi (Young's Modulus for 6061-T6)


@dataclass
class TubeSpar:
    od: float          # Outer Diameter (inches)
    wall: float        # Wall thickness (inches)
    description: str   # Human readable description (internal use)

    @property
    def id(self) -> float:
        return self.od - 2 * self.wall

    @property
    def I(self) -> float:
        """Moment of Inertia (in^4)"""
        do = self.od
        di = self.id
        return (np.pi / 64) * (do**4 - di**4)

    @property
    def EI(self) -> float:
        """Bending stiffness (lb-in²)"""
        return self.I * E_6061_T6

    def __str__(self):
        """String shown in the GUI dropdown"""
        return f'{self.od:.1f}" OD x {self.wall:.3f}" wall  |  I = {self.I:.3f} in⁴'


# Common aircraft-grade 6061-T6 round tubes
COMMON_TUBE_SIZES: List[TubeSpar] = [
    # 2.0" OD
    TubeSpar(2.0, 0.049, "2.0in x 0.049in (light)"),
    TubeSpar(2.0, 0.058, "2.0in x 0.058in"),
    TubeSpar(2.0, 0.065, "2.0in x 0.065in (common)"),
    TubeSpar(2.0, 0.083, "2.0in x 0.083in"),

    # 2.5" OD
    TubeSpar(2.5, 0.049, "2.5in x 0.049in"),
    TubeSpar(2.5, 0.058, "2.5in x 0.058in"),
    TubeSpar(2.5, 0.065, "2.5in x 0.065in"),
    TubeSpar(2.5, 0.083, "2.5in x 0.083in"),

    # 3.0" OD (very common)
    TubeSpar(3.0, 0.049, "3.0in x 0.049in"),
    TubeSpar(3.0, 0.058, "3.0in x 0.058in"),
    TubeSpar(3.0, 0.065, "3.0in x 0.065in (very common)"),
    TubeSpar(3.0, 0.083, "3.0in x 0.083in"),
    TubeSpar(3.0, 0.095, "3.0in x 0.095in"),
    TubeSpar(3.0, 0.120, "3.0in x 0.120in (heavy)"),

    # 3.5" OD
    TubeSpar(3.5, 0.058, "3.5in x 0.058in"),
    TubeSpar(3.5, 0.065, "3.5in x 0.065in"),
    TubeSpar(3.5, 0.083, "3.5in x 0.083in"),

    # 4.0" OD
    TubeSpar(4.0, 0.058, "4.0in x 0.058in"),
    TubeSpar(4.0, 0.065, "4.0in x 0.065in"),
    TubeSpar(4.0, 0.083, "4.0in x 0.083in"),
    TubeSpar(4.0, 0.095, "4.0in x 0.095in"),

    # 5.0" OD
    TubeSpar(5.0, 0.065, "5.0in x 0.065in"),
    TubeSpar(5.0, 0.083, "5.0in x 0.083in"),
]


def get_tube_by_description(description: str) -> TubeSpar:
    """Find a tube by the exact string shown in the GUI dropdown"""
    for tube in COMMON_TUBE_SIZES:
        if str(tube) == description:
            return tube
    raise ValueError(f"Tube size not found: {description}")


def list_tube_descriptions() -> List[str]:
    """Return list of all available tube descriptions for GUI dropdown"""
    return [str(tube) for tube in COMMON_TUBE_SIZES]