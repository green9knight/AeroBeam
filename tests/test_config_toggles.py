import unittest

from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer, parse_bool


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

    def test_distributed_wing_weight_changes_root_shear(self):
        base = analyze_with(distribute_wing_weight=False)
        relief = analyze_with(distribute_wing_weight=True)

        self.assertLess(relief.pos["V_root"], base.pos["V_root"])
        self.assertLess(relief.sigma_max_front, base.sigma_max_front)

    def test_pdelta_changes_front_spar_stress_when_enabled(self):
        base = analyze_with(secondary_bending=False)
        pdelta = analyze_with(secondary_bending=True)

        self.assertGreater(pdelta.sigma_max_front, base.sigma_max_front)

    def test_jury_changes_euler_capacity_when_enabled(self):
        base = analyze_with(jury_strut=False, jury_spar_bl=60.0)
        jury = analyze_with(jury_strut=True, jury_spar_bl=60.0)

        self.assertGreater(jury.strut_summary["P_euler"], base.strut_summary["P_euler"])
        self.assertAlmostEqual(jury.strut_summary["F_axial"], base.strut_summary["F_axial"])


if __name__ == "__main__":
    unittest.main()
