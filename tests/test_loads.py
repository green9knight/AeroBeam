import math
import unittest

from aerobeam.loads import GRAVITY_M_S2, LoadCase


class LoadCaseTest(unittest.TestCase):
    def test_elliptical_root_loads(self) -> None:
        load_case = LoadCase.from_aircraft_mass(
            mass_kg=10.0,
            span_m=2.0,
            limit_load_factor=4.0,
            safety_factor=1.5,
        )

        ultimate_lift = 10.0 * GRAVITY_M_S2 * 4.0 * 1.5

        self.assertAlmostEqual(load_case.ultimate_lift_n, ultimate_lift)
        self.assertAlmostEqual(load_case.root_shear_n, ultimate_lift / 2.0)
        self.assertAlmostEqual(
            load_case.root_bending_moment_nm,
            ultimate_lift * 2.0 / (3.0 * math.pi),
        )

    def test_uniform_root_bending_is_supported(self) -> None:
        load_case = LoadCase(
            gross_weight_n=100.0,
            span_m=4.0,
            limit_load_factor=2.0,
            safety_factor=1.0,
            distribution="uniform",
        )

        self.assertAlmostEqual(load_case.root_bending_moment_nm, 100.0)

    def test_invalid_distribution_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "distribution"):
            LoadCase(
                gross_weight_n=100.0,
                span_m=4.0,
                limit_load_factor=2.0,
                distribution="triangular",
            )


if __name__ == "__main__":
    unittest.main()
