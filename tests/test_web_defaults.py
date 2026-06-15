from spar_sections import ANGLE_DESCRIPTIONS
from web_app import analyze_payload, report_payload
import unittest


class WebDefaultsTest(unittest.TestCase):
    def test_large_angle_is_available_to_web_defaults(self):
        # The web defaults endpoint builds directly from ANGLE_DESCRIPTIONS.
        # This guards against accidentally removing the large cap angles from
        # the browser quick-select data source.
        self.assertIn("2-1/2 x 2-1/2 x 3/8", ANGLE_DESCRIPTIONS)

    def test_web_report_accepts_percent_style_spar_locations(self):
        payload = {
            "inputs": {
                "front_spar_percent": 30,
                "rear_spar_percent": 80,
                "front_spar_load_share": 75,
            }
        }
        analysis = analyze_payload(payload)
        self.assertTrue(analysis["ok"])
        self.assertAlmostEqual(analysis["series"]["geometry"]["front_spar_percent"], 0.30)
        self.assertAlmostEqual(analysis["series"]["geometry"]["rear_spar_percent"], 0.80)
        pdf = report_payload(payload)
        self.assertEqual(pdf[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
