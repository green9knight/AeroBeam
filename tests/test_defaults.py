import os
import tempfile
import unittest

from input_validation import ValidationError, validate_inputs
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
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.pdf")
            analyzer.export_pdf(path)
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(4), b"%PDF")

    def test_impossible_span_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_inputs({**DEFAULT_INPUTS, "b": -10})

    def test_full_front_spar_share_and_zero_dive_speed_are_accepted(self):
        sanitized, warnings = validate_inputs(
            {**DEFAULT_INPUTS, "front_spar_load_share": 1.0, "Vd_mph": 0.0}
        )
        self.assertEqual(sanitized["front_spar_load_share"], 1.0)
        self.assertTrue(any(item.field == "Vd_mph" for item in warnings))


if __name__ == "__main__":
    unittest.main()
