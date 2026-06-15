from spar_sections import ANGLE_DESCRIPTIONS
import unittest


class WebDefaultsTest(unittest.TestCase):
    def test_large_angle_is_available_to_web_defaults(self):
        # The web defaults endpoint builds directly from ANGLE_DESCRIPTIONS.
        # This guards against accidentally removing the large cap angles from
        # the browser quick-select data source.
        self.assertIn("2-1/2 x 2-1/2 x 3/8", ANGLE_DESCRIPTIONS)


if __name__ == "__main__":
    unittest.main()
