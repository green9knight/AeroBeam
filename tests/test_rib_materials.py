import unittest

from spar_sections import aluminum_mat_names, all_mat_names
from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


class RibMaterialTest(unittest.TestCase):
    def test_aluminum_materials_are_available_for_ribs(self):
        self.assertIn("6061-T6", all_mat_names())
        self.assertIn("6061-T6", aluminum_mat_names())

    def test_aluminum_rib_material_analyzes(self):
        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "num_points": 81,
                "rib_mat": "6061-T6",
                "rib_h_web": 3.0,
                "rib_t_web": 0.025,
                "rib_b_cap": 0.75,
                "rib_t_cap": 0.025,
                "dcell_enabled": True,
                "wing_structure_type": "aluminum_skin",
                "skin_top_thick": 0.025,
                "skin_bot_thick": 0.025,
            }
        )

        analyzer = WingStressAnalyzer(inputs)
        analyzer.analyze()

        self.assertIsNotNone(analyzer.torsion)
        self.assertIn("MS_rib_shear", analyzer.torsion)
        self.assertIn("MS_rib_bend", analyzer.torsion)


if __name__ == "__main__":
    unittest.main()
