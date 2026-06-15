import unittest

from spar_sections import aluminum_mat_names, all_mat_names
from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


class RibReactionRequirementTest(unittest.TestCase):
    def test_aluminum_materials_remain_available_for_other_components(self):
        self.assertIn("6061-T6", all_mat_names())
        self.assertIn("6061-T6", aluminum_mat_names())

    def test_torsion_reports_required_rib_reactions_not_rib_margins(self):
        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "num_points": 81,
                "dcell_enabled": True,
                "wing_structure_type": "aluminum_skin",
                "skin_top_thick": 0.025,
                "skin_bot_thick": 0.025,
            }
        )

        analyzer = WingStressAnalyzer(inputs)
        analyzer.analyze()

        self.assertIsNotNone(analyzer.torsion)
        self.assertIn("rib_bay_torque", analyzer.torsion)
        self.assertIn("rib_reaction_required", analyzer.torsion)
        self.assertNotIn("MS_rib_shear", analyzer.torsion)
        self.assertNotIn("MS_rib_bend", analyzer.torsion)


if __name__ == "__main__":
    unittest.main()
