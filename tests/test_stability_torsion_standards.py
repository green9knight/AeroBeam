import math
import unittest

from spar_sections import (
    DCellSkin,
    GeodeticPanel,
    MATERIAL_DB,
    STRUT_MATERIALS,
    cap_column_buckling,
    skin_compression_buckling,
    skin_effective_width,
    web_buckling,
    two_cell_bredt,
)
from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


class StabilityTorsionStandardsTest(unittest.TestCase):
    def test_strut_euler_buckling_matches_pin_ended_column_formula(self):
        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "config": "strut_braced",
                "strut_fuse_bl": 11.0,
                "strut_bl": 96.0,
                "strut_vert": 44.0,
                "strut_tube_od": 3.0,
                "strut_tube_wall": 0.065,
                "strut_mat": "4130 Chromoly (normalized)",
                "jury_strut": False,
            }
        )
        analyzer = WingStressAnalyzer(inputs)
        analyzer.analyze()

        od = 3.0
        wall = 0.065
        inner = od - 2.0 * wall
        inertia = math.pi / 64.0 * (od**4 - inner**4)
        length = math.hypot(96.0 - 11.0, 44.0)
        expected = math.pi**2 * STRUT_MATERIALS["4130 Chromoly (normalized)"]["E"] * inertia / length**2

        self.assertAlmostEqual(analyzer.strut_summary["length"], length)
        self.assertAlmostEqual(analyzer.strut_summary["P_euler"], expected)

    def test_skin_buckling_matches_plate_formula(self):
        result = skin_compression_buckling(t_skin=0.025, b_panel=12.0, mat_name="6061-T6", k=4.0)
        E = MATERIAL_DB["6061-T6"]["E"]
        nu = 0.33
        expected = 4.0 * math.pi**2 * E * (0.025 / 12.0) ** 2 / (12.0 * (1.0 - nu**2))
        self.assertAlmostEqual(result["sigma_cr_skin"], expected)

    def test_skin_effective_width_matches_von_karman_winter_screening_formula(self):
        result = skin_effective_width(
            t_skin=0.025,
            b_panel=12.0,
            sigma_edge=20_000.0,
            mat_name="6061-T6",
        )
        expected = min(12.0, 1.9 * 0.025 * math.sqrt(MATERIAL_DB["6061-T6"]["E"] / 20_000.0))
        self.assertAlmostEqual(result["b_eff"], expected)
        self.assertAlmostEqual(result["load_per_length"], 20_000.0 * expected * 0.025)

    def test_web_shear_buckling_matches_plate_formula(self):
        result = web_buckling(t_web=0.032, h_web=6.0, stiffener_spacing=12.0, mat_name="6061-T6")
        E = MATERIAL_DB["6061-T6"]["E"]
        nu = 0.33
        aspect = 12.0 / 6.0
        ks = 5.34 + 4.0 / aspect**2
        expected = ks * math.pi**2 * E * (0.032 / 6.0) ** 2 / (12.0 * (1.0 - nu**2))
        self.assertAlmostEqual(result["k_s"], ks)
        self.assertAlmostEqual(result["tau_cr"], expected)

    def test_cap_column_buckling_matches_euler_formula(self):
        result = cap_column_buckling(b_cap=1.5, t_cap=0.125, rib_spacing=12.0, mat_name="6061-T6")
        E = MATERIAL_DB["6061-T6"]["E"]
        area = 1.5 * 0.125
        inertia = 0.125 * 1.5**3 / 12.0
        p_cr = math.pi**2 * E * inertia / 12.0**2
        self.assertAlmostEqual(result["P_cr"], p_cr)
        self.assertAlmostEqual(result["sigma_cr_cap"], p_cr / area)

    def test_dcell_single_cell_gj_matches_bredt_batho_formula(self):
        dcell = DCellSkin(
            t_skin=0.125,
            skin_mat="Birch Plywood",
            chord_to_spar=16.0,
            t_web=0.125,
        )
        h_spar = 6.0
        area = 16.0 * h_spar
        ds_over_t = 2.0 * 16.0 / 0.125 + h_spar / 0.125
        expected = 4.0 * MATERIAL_DB["Birch Plywood"]["G"] * area**2 / ds_over_t
        self.assertAlmostEqual(dcell.GJ(h_spar), expected)

    def test_two_cell_bredt_satisfies_equilibrium_and_compatibility(self):
        A1 = 35.0
        A2 = 120.0
        ds1 = 250.0
        ds2 = 410.0
        shared = 60.0
        G1 = 80_000.0
        G2 = 145_000.0
        torque = 25_000.0

        q1, q2, gj = two_cell_bredt(A1, A2, ds1, ds2, shared, G1, G2, torque)
        d11 = ds1 + shared
        d22 = ds2 + shared
        d12 = shared
        phi_1 = (q1 * d11 - q2 * d12) / (2.0 * A1 * G1)
        phi_2 = (q2 * d22 - q1 * d12) / (2.0 * A2 * G2)
        torque_check = 2.0 * q1 * A1 + 2.0 * q2 * A2

        self.assertAlmostEqual(torque_check, torque)
        self.assertAlmostEqual(phi_1, phi_2)
        self.assertAlmostEqual(gj, torque / phi_1)

    def test_geodetic_strip_force_is_consistent_with_equivalent_shear_thickness(self):
        panel = GeodeticPanel(
            rib_spacing=10.0,
            strips_per_bay=2,
            strip_width=1.0,
            strip_thick=0.125,
            angle_deg=45.0,
            mat_name="Sitka Spruce",
        )
        q = 75.0
        stress_from_t_eff = q / panel.t_eff()
        stress_from_force = panel.strip_force(q) / panel.A_strip
        self.assertAlmostEqual(stress_from_force, stress_from_t_eff)


if __name__ == "__main__":
    unittest.main()
