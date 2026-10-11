import math
import unittest

from spar_sections import (
    DCellSkin,
    GeodeticPanel,
    MATERIAL_DB,
    STRUT_MATERIALS,
    cap_column_buckling,
    half_thickness_over_chord,
    orthotropic_long_plate_compression,
    single_cell_shear_center,
    skin_compression_buckling,
    skin_effective_width,
    two_cell_shear_center,
    web_buckling,
    web_bending_buckling,
    wood_plate_constants,
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

    def test_aluminum_skin_reports_remaining_cap_stringer_load_demand(self):
        from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer

        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "wing_structure_type": "aluminum_skin",
                "skin_top_thick": 0.025,
                "skin_bot_thick": 0.025,
                "rib_spacing": 12.0,
            }
        )
        analyzer = WingStressAnalyzer(inputs)
        analyzer.analyze()
        front = analyzer.buckling["front"]

        total = front["skin_total_load_per_in"]
        effective = front["skin_eff_load_per_in"]
        demand = front["cap_stringer_load_per_in"]

        self.assertAlmostEqual(demand, max(total - effective, 0.0))
        self.assertAlmostEqual(front["cap_stringer_load_per_bay"], demand * analyzer.rib_spacing)

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

    def test_dcell_area_comes_from_the_thickness_curve(self):
        dcell = DCellSkin(
            t_skin=0.125,
            skin_mat="Birch Plywood",
            chord_to_spar=16.0,
            t_web=0.125,
            t_c=0.12,
            x_t_c=0.30,
        )
        h_max = 0.12 * 80.0
        geo = dcell.nose_geometry(h_max, 1.0, n=80)
        # Independent integral of the same thickness law, cut at the spar.
        import numpy as np
        xs = np.linspace(0.0, geo["x_spar"], 80)
        chord = h_max / 0.12
        ys = np.array([
            0.0 if x == 0.0 else half_thickness_over_chord(x / chord, 0.12, 0.30) * chord
            for x in xs
        ])
        area = 2.0 * float(np.sum((ys[1:] + ys[:-1]) * 0.5 * np.diff(xs)))
        self.assertAlmostEqual(geo["area"], area, delta=area * 0.02)
        self.assertLess(geo["area"], 16.0 * h_max)
        self.assertGreater(geo["skin_length"], 2.0 * 16.0)
        self.assertLess(geo["h_web"], h_max)
        ds_over_t = geo["skin_length"] / 0.125 + geo["h_web"] / 0.125
        expected = 4.0 * MATERIAL_DB["Birch Plywood"]["G"] * geo["area"] ** 2 / ds_over_t
        self.assertAlmostEqual(dcell.GJ(h_max), expected, delta=expected * 0.01)

    def test_closed_section_shear_center_follows_the_thin_wall_flow(self):
        radius = 5.0
        count = 120
        circle = [
            (radius * math.cos(2.0 * math.pi * i / count) + 3.0,
             radius * math.sin(2.0 * math.pi * i / count))
            for i in range(count + 1)
        ]
        tube = single_cell_shear_center(circle, 0.05)
        self.assertAlmostEqual(tube["x"], 3.0, delta=0.05)
        self.assertAlmostEqual(tube["Fy"], 1.0, delta=0.02)

        dcell = DCellSkin(
            t_skin=0.05, skin_mat="Birch Plywood",
            chord_to_spar=12.0, t_web=0.08, t_c=0.12, x_t_c=0.30,
        )
        geo = dcell.nose_geometry(7.2, 1.0)
        nose_x = dcell.shear_center_x(7.2, 1.0)
        self.assertGreater(nose_x, 1.0)
        self.assertLess(nose_x, geo["x_spar"])
        self.assertNotAlmostEqual(nose_x / 60.0, 0.22, delta=0.02)
        outer = two_cell_shear_center(
            geo["points"], 0.05, geo["x_spar"], 36.0, geo["h_web"], 0.05, 0.05)
        self.assertAlmostEqual(outer["Fy"], 1.0, delta=0.05)
        self.assertGreater(outer["x"], nose_x)
        self.assertLess(outer["x"], 36.0)

    def test_wood_shear_buckling_uses_orthotropic_plate(self):
        plywood = web_buckling(0.10, 6.0, 12.0, "Birch Plywood")
        spruce = web_buckling(0.10, 6.0, 12.0, "Sitka Spruce")
        self.assertEqual(plywood["plate"], "orthotropic")
        constants = wood_plate_constants("Birch Plywood")
        sigma_4 = orthotropic_long_plate_compression(
            constants["E1"], constants["E2"], constants["nu12"], constants["nu21"],
            constants["G"], 0.10, 6.0)
        # Seydel shear stiffness is not the compression formula. It must differ
        # from the metal plate with nu forced to 0, which was the old wood path.
        metal_nu0 = plywood["k_s"] * math.pi ** 2 * MATERIAL_DB["Birch Plywood"]["E"] * (0.10 / 6.0) ** 2 / 12.0
        self.assertNotAlmostEqual(plywood["tau_cr"], metal_nu0, delta=metal_nu0 * 0.05)
        self.assertGreater(plywood["tau_cr"], spruce["tau_cr"])
        bend = web_bending_buckling(0.10, 6.0, "Birch Plywood")
        self.assertAlmostEqual(bend["sigma_cr_web_bending"], (23.9 / 4.0) * sigma_4, delta=sigma_4 * 0.01)
        # Isotropic reduction of the long-plate formula is Timoshenko k = 4.
        e = 10_000_000.0
        nu = 0.33
        g = e / (2.0 * (1.0 + nu))
        iso = orthotropic_long_plate_compression(e, e, nu, nu, g, 0.10, 6.0)
        timoshenko = 4.0 * math.pi ** 2 * e * (0.10 / 6.0) ** 2 / (12.0 * (1.0 - nu ** 2))
        self.assertAlmostEqual(iso, timoshenko, delta=timoshenko * 0.001)

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

    def test_geodetic_shear_stiffness_uses_axial_strip_formula_and_reduction(self):
        panel = GeodeticPanel(
            rib_spacing=10.0,
            strips_per_bay=2,
            strip_width=1.0,
            strip_thick=0.125,
            angle_deg=45.0,
            mat_name="Sitka Spruce",
        )
        theta = math.radians(45.0)
        expected_full = (
            2.0
            * panel.A_strip
            * MATERIAL_DB["Sitka Spruce"]["E"]
            * math.sin(theta)
            * math.cos(theta)
            / panel.s_strip
        )
        self.assertAlmostEqual(panel.shear_stiffness_per_span(1.0), expected_full)
        self.assertAlmostEqual(panel.shear_stiffness_per_span(0.75), expected_full * 0.75)


if __name__ == "__main__":
    unittest.main()
