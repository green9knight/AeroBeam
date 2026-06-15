import unittest

from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


class FittingDemandTest(unittest.TestCase):
    def test_fitting_demands_report_root_and_strut_loads(self):
        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "num_points": 101,
                "config": "strut_braced",
                "front_spar_load_share": 0.6,
                "jury_strut": True,
                "jury_spar_bl": 60.0,
            }
        )
        analyzer = WingStressAnalyzer(inputs)
        analyzer.analyze()

        demands = analyzer.fitting_loads
        self.assertAlmostEqual(demands["front_root_vertical"], abs(analyzer.pos["V_root"] * analyzer.lsf))
        self.assertAlmostEqual(demands["rear_root_vertical"], abs(analyzer.pos["V_root"] * analyzer.rsf))
        self.assertAlmostEqual(demands["main_strut_vertical"], abs(analyzer.pos["Fv_strut_attach"]))
        self.assertAlmostEqual(demands["jury_vertical"], abs(analyzer.pos["Fv_jury"]))
        self.assertAlmostEqual(demands["main_strut_axial"], abs(analyzer.pos["F_axial"]))

    def test_summary_states_local_reinforcement_scope(self):
        analyzer = WingStressAnalyzer({**DEFAULT_INPUTS, "config": "strut_braced"})
        analyzer.analyze()
        summary = analyzer.summary_text()

        self.assertIn("LOCAL FITTING / BEARING LOAD DEMANDS", summary)
        self.assertIn("Reinforce/check tube bearing", summary)
        self.assertNotIn("bearing MS", summary)


if __name__ == "__main__":
    unittest.main()
