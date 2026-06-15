import unittest

from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer, parse_bool, parse_fraction


def analyze_with(**overrides):
    inputs = dict(DEFAULT_INPUTS)
    inputs.update(
        {
            "num_points": 101,
            "config": "strut_braced",
            "Wing_Weight": 300.0,
            "secondary_bending": False,
            "jury_strut": False,
            "distribute_wing_weight": False,
        }
    )
    inputs.update(overrides)
    analyzer = WingStressAnalyzer(inputs)
    analyzer.analyze()
    return analyzer


class ConfigToggleTest(unittest.TestCase):
    def test_string_false_values_are_false(self):
        self.assertFalse(parse_bool("False"))
        self.assertFalse(parse_bool("0"))
        self.assertFalse(parse_bool("off"))
        self.assertFalse(parse_bool(""))
        self.assertTrue(parse_bool("True"))
        self.assertTrue(parse_bool("1"))

        analyzer = analyze_with(
            distribute_wing_weight="False",
            secondary_bending="False",
            jury_strut="False",
        )

        self.assertFalse(analyzer.dist_relief)
        self.assertFalse(analyzer.secondary)
        self.assertFalse(analyzer.jury)

    def test_percent_style_values_are_normalized(self):
        self.assertAlmostEqual(parse_fraction(30), 0.30)
        self.assertAlmostEqual(parse_fraction("80"), 0.80)
        self.assertAlmostEqual(parse_fraction(0.55), 0.55)

        analyzer = WingStressAnalyzer(
            {
                **DEFAULT_INPUTS,
                "front_spar_percent": 30,
                "rear_spar_percent": 80,
                "front_spar_load_share": 75,
            }
        )
        self.assertAlmostEqual(analyzer.front_pct, 0.30)
        self.assertAlmostEqual(analyzer.rear_pct, 0.80)
        self.assertAlmostEqual(analyzer.lsf, 0.75)

    def test_distributed_wing_weight_changes_root_shear(self):
        base = analyze_with(distribute_wing_weight=False)
        relief = analyze_with(distribute_wing_weight=True)

        self.assertLess(relief.pos["V_root"], base.pos["V_root"])
        self.assertLess(relief.sigma_max_front, base.sigma_max_front)

    def test_pdelta_changes_front_spar_stress_when_enabled(self):
        base = analyze_with(secondary_bending=False)
        pdelta = analyze_with(secondary_bending=True)

        self.assertGreater(pdelta.sigma_max_front, base.sigma_max_front)
        self.assertEqual(base.pos["pdelta_amp"], 1.0)
        self.assertGreater(pdelta.pos["pdelta_amp"], 1.0)

    def test_jury_changes_euler_capacity_when_enabled(self):
        base = analyze_with(jury_strut=False, jury_spar_bl=60.0)
        jury = analyze_with(jury_strut=True, jury_spar_bl=60.0)

        self.assertGreater(jury.strut_summary["P_euler"], base.strut_summary["P_euler"])
        self.assertGreater(jury.strut_summary["Fv_jury"], 0.0)
        station = 20
        self.assertLess(abs(jury.pos["M_front"][station]), abs(base.pos["M_front"][station]))


if __name__ == "__main__":
    unittest.main()
