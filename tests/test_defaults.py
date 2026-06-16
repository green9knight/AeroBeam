import unittest

from web_app import report_payload
from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


class DefaultInputsTest(unittest.TestCase):
    def test_default_inputs_match_current_beta_baseline(self):
        self.assertEqual(DEFAULT_INPUTS["b"], 306.0)
        self.assertEqual(DEFAULT_INPUTS["r"], 11.0)
        self.assertEqual(DEFAULT_INPUTS["front_spar_percent"], 0.05)
        self.assertEqual(DEFAULT_INPUTS["rear_spar_percent"], 0.85)
        self.assertEqual(DEFAULT_INPUTS["front_spar_od"], 2.5)
        self.assertEqual(DEFAULT_INPUTS["rear_spar_od"], 2.5)
        self.assertEqual(DEFAULT_INPUTS["strut_bl"], 96.0)
        self.assertEqual(DEFAULT_INPUTS["strut_fuse_bl"], 11.0)
        self.assertTrue(DEFAULT_INPUTS["distribute_wing_weight"])
        self.assertTrue(DEFAULT_INPUTS["jury_strut"])
        self.assertEqual(DEFAULT_INPUTS["jury_spar_bl"], 48.0)
        self.assertEqual(DEFAULT_INPUTS["airfoil"], "GA 30-415")
        self.assertAlmostEqual(DEFAULT_INPUTS["Cm_ac"], -0.064)
        self.assertAlmostEqual(DEFAULT_INPUTS["airfoil_t_c"], 0.15)

    def test_default_analysis_and_report_run(self):
        analyzer = WingStressAnalyzer(dict(DEFAULT_INPUTS))
        analyzer.analyze()
        self.assertGreater(analyzer.sigma_max_front, 0.0)
        self.assertGreater(analyzer.strut_summary["P_euler"], 0.0)
        pdf = report_payload({})
        self.assertEqual(pdf[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
