import unittest

from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


def analyze_with(**overrides):
    inputs = dict(DEFAULT_INPUTS)
    inputs.update(
        {
            "num_points": 81,
            "config": "strut_braced",
            "strut_fuse_bl": 11.0,
            "strut_bl": 96.0,
            "strut_vert": 44.0,
            "jury_spar_bl": 48.0,
            "jury_strut": False,
        }
    )
    inputs.update(overrides)
    analyzer = WingStressAnalyzer(inputs)
    analyzer.analyze()
    return analyzer


class JuryStrutTest(unittest.TestCase):
    def test_jury_strut_reduces_euler_length_and_increases_pe(self):
        without_jury = analyze_with(jury_strut=False)
        with_jury = analyze_with(jury_strut=True)

        self.assertLess(
            with_jury.strut_summary["effective_length"],
            without_jury.strut_summary["effective_length"],
        )
        self.assertGreater(
            with_jury.strut_summary["P_euler"],
            without_jury.strut_summary["P_euler"],
        )
        self.assertAlmostEqual(
            with_jury.strut_summary["F_axial"],
            without_jury.strut_summary["F_axial"],
        )

    def test_out_of_range_jury_bl_does_not_change_euler_length(self):
        without_jury = analyze_with(jury_strut=False)
        bad_jury = analyze_with(jury_strut=True, jury_spar_bl=120.0)

        self.assertAlmostEqual(
            bad_jury.strut_summary["effective_length"],
            without_jury.strut_summary["effective_length"],
        )
        self.assertAlmostEqual(
            bad_jury.strut_summary["P_euler"],
            without_jury.strut_summary["P_euler"],
        )


if __name__ == "__main__":
    unittest.main()
