"""Rib construction stiffness: plywood, formed aluminum, and foam with spruce caps."""

import unittest

from spar_sections import MATERIAL_DB, rib_tie_stiffness
from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer, parse_user_float


class RibTieStiffnessTests(unittest.TestCase):
    def test_plywood_matches_shear_panel(self):
        gap, pitch, h, t = 20.0, 12.0, 3.0, 0.125
        G = MATERIAL_DB["Birch Plywood"]["G"]
        rib = rib_tie_stiffness("Plywood web", gap, pitch, h, t, 0.75, 0.125, "Birch Plywood")
        self.assertEqual(rib["type"], "Plywood web")
        self.assertAlmostEqual(rib["k_per_span"], G * t * h / (gap * pitch))
        self.assertEqual(rib["cap_sigma_per_lb"], 0.0)

    def test_formed_aluminum_uses_sheet_shear_only(self):
        gap, pitch, h, t = 20.0, 12.0, 4.0, 0.025
        G = MATERIAL_DB["2024-T3"]["G"]
        rib = rib_tie_stiffness(
            "Sheet aluminum formed", gap, pitch, h, t, 0.50, 0.032, "2024-T3")
        self.assertAlmostEqual(rib["k_one"], G * t * h / gap)
        self.assertAlmostEqual(rib["shear_area"], t * h)
        self.assertGreater(rib["k_per_span"], rib_tie_stiffness(
            "Plywood web", gap, pitch, h, 0.125, 0.75, 0.125, "Birch Plywood")["k_per_span"])

    def test_foam_is_core_shear_in_series_with_spruce_caps(self):
        gap, pitch = 24.0, 12.0
        h, t = 4.0, 0.5
        b_cap, t_cap = 0.25, 0.25
        rib = rib_tie_stiffness(
            "Dow foam with spruce caps", gap, pitch, h, t, b_cap, t_cap, "Birch Plywood", 0.75)
        G = 300.0
        shear_only = G * t * h / gap
        d = h + t_cap
        cap_area = b_cap * t_cap
        I_caps = 2.0 * cap_area * (d / 2.0) ** 2 + 2.0 * b_cap * t_cap ** 3 / 12.0
        E = MATERIAL_DB["Sitka Spruce"]["E"]
        k_one = 1.0 / (gap / (G * t * h) + gap ** 3 / (12.0 * E * I_caps))
        self.assertAlmostEqual(rib["k_one"], k_one)
        self.assertLess(rib["k_one"], shear_only)
        self.assertAlmostEqual(rib["G"], 300.0)
        self.assertAlmostEqual(rib["Fsu"], 25.0)
        self.assertAlmostEqual(rib["cap_sigma_per_lb"], (gap / 2.0) / (d * cap_area))
        self.assertAlmostEqual(rib["cap_allow"], MATERIAL_DB["Sitka Spruce"]["Fc"] * 0.75)
        self.assertLess(rib["k_per_span"], 10.0)

    def test_sheet_thickness_accepts_quotes_and_an_inch_mark(self):
        for raw in ("0.02", "'0.02'", '"0.02"', '0.02"', "0.020 in", " .02"):
            self.assertAlmostEqual(parse_user_float(raw), 0.02)
            wing = WingStressAnalyzer({**DEFAULT_INPUTS, "rib_t_web": raw, "num_points": 5})
            self.assertAlmostEqual(wing.rib_t_web, 0.02)

    def test_missing_type_stays_on_the_plywood_panel(self):
        rib = rib_tie_stiffness("", 18.0, 10.0, 3.0, 0.125, 0.5, 0.125, "Birch Plywood")
        plywood = rib_tie_stiffness("Plywood web", 18.0, 10.0, 3.0, 0.125, 0.5, 0.125, "Birch Plywood")
        self.assertEqual(rib["k_per_span"], plywood["k_per_span"])

    def test_analyzer_keeps_the_bending_path_and_reports_the_rib(self):
        common = {
            **DEFAULT_INPUTS,
            "b": 200.0,
            "num_points": 21,
            "config": "cantilever",
            "front_spar_load_share": 0.7,
            "lift_distribution_type": "uniform",
            "ng_lift": 1000.0,
            "distribute_wing_weight": False,
            "Vd_mph": 0.0,
            "Cm_ac": 0.0,
            "dcell_enabled": False,
            "geodetic_enabled": False,
            "num_spars": 2,
        }
        plywood = WingStressAnalyzer(common)
        foam = WingStressAnalyzer({
            **common,
            "rib_type": "Dow foam with spruce caps",
            "rib_h_web": 4.0,
            "rib_t_web": 0.5,
            "rib_b_cap": 0.25,
            "rib_t_cap": 0.25,
        })
        plywood.analyze()
        foam.analyze()
        self.assertEqual(plywood._rear_spar_path, "rib-tied cantilever")
        self.assertEqual(foam._rear_spar_path, "rib-tied cantilever")
        self.assertGreater(plywood._torsion_transfer["k_rib"], foam._torsion_transfer["k_rib"] * 10.0)
        self.assertAlmostEqual(foam.torsion["rib_model"]["Fsu"], 25.0)
        self.assertGreater(foam.torsion["rib_tau"], 0.0)
        self.assertGreater(foam.torsion["rib_cap_sigma"], 0.0)
        self.assertIn("Foam core shear is soft", foam.summary_text())


if __name__ == "__main__":
    unittest.main()
