import math
import unittest

import numpy as np

from spar_sections import STRUT_MATERIALS
from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer, dynamic_pressure_psi, isa_density


def analyzer_with(**overrides):
    inputs = dict(DEFAULT_INPUTS)
    inputs.update(
        {
            "num_points": 801,
            "b": 200.0,
            "root_chord": 48.0,
            "tip_chord": 24.0,
            "taper_start_bl": 0.0,
            "ng_lift": 1000.0,
            "config": "cantilever",
            "num_spars": 1,
            "Vd_mph": 100.0,
            "altitude_ft": 0.0,
        }
    )
    inputs.update(overrides)
    return WingStressAnalyzer(inputs)


class LoadsAeroStandardsTest(unittest.TestCase):
    def test_dynamic_pressure_matches_q_equals_half_rho_v_squared(self):
        speed_mph = 100.0
        speed_fps = speed_mph * 5280.0 / 3600.0
        expected = 0.5 * isa_density(0.0) * speed_fps**2 / 144.0
        self.assertAlmostEqual(dynamic_pressure_psi(speed_mph, 0.0), expected)

    def test_lift_distributions_integrate_to_total_lift(self):
        total = 1000.0
        for lift_type in ("uniform", "elliptical", "chord_based", "schrenk"):
            with self.subTest(lift_type=lift_type):
                analyzer = analyzer_with(lift_distribution_type=lift_type)
                w = analyzer._lift_dist(total)
                integrated = np.trapezoid(w, analyzer.x)
                self.assertAlmostEqual(integrated, total, delta=total * 0.01)

    def test_chord_based_load_tracks_chord_ratio(self):
        analyzer = analyzer_with(lift_distribution_type="chord_based")
        w = analyzer._lift_dist(1000.0)
        root_to_tip_load_ratio = w[0] / w[-1]
        root_to_tip_chord_ratio = analyzer.chord_x[0] / analyzer.chord_x[-1]
        self.assertAlmostEqual(root_to_tip_load_ratio, root_to_tip_chord_ratio)

    def test_distributed_wing_weight_relief_matches_uniform_down_load(self):
        base_inputs = {
            "b": 200.0,
            "num_points": 401,
            "lift_distribution_type": "uniform",
            "ng_lift": 1000.0,
            "Wing_Weight": 200.0,
            "config": "cantilever",
            "num_spars": 1,
            "front_spar_load_share": 1.0,
            "secondary_bending": False,
            "jury_strut": False,
        }
        base = analyzer_with(**base_inputs, distribute_wing_weight=False)
        relief = analyzer_with(**base_inputs, distribute_wing_weight=True)
        base.analyze()
        relief.analyze()

        b_half = base.b_half
        self.assertAlmostEqual(base.pos["V_root"] - relief.pos["V_root"], 200.0, delta=1.0)
        self.assertAlmostEqual(
            base.pos["M_root"] - relief.pos["M_root"],
            200.0 * b_half / 2.0,
            delta=200.0 * b_half / 2.0 * 0.01,
        )

    def test_strut_axial_load_matches_vertical_reaction_trigonometry(self):
        analyzer = WingStressAnalyzer(
            {
                **DEFAULT_INPUTS,
                "num_points": 101,
                "config": "strut_braced",
                "strut_fuse_bl": 11.0,
                "strut_bl": 96.0,
                "strut_vert": 44.0,
                "strut_mat": "4130 Chromoly (normalized)",
                "jury_strut": False,
            }
        )
        analyzer.analyze()
        summary = analyzer.strut_summary
        run = 96.0 - 11.0
        angle = math.atan2(44.0, run)
        expected_axial = summary["Fv"] / math.sin(angle)
        expected_compression = expected_axial * math.cos(angle)

        self.assertAlmostEqual(summary["F_axial"], expected_axial)
        self.assertAlmostEqual(analyzer.pos["P_spar"], expected_compression)

    def test_pdelta_amplification_matches_beam_column_scalar_formula(self):
        analyzer = WingStressAnalyzer(
            {
                **DEFAULT_INPUTS,
                "num_points": 101,
                "b": 200.0,
                "strut_bl": 100.0,
                "config": "strut_braced",
            }
        )
        analyzer._spar_arrays()
        moment = np.ones(analyzer.N) * 100.0
        ei_mean = float(np.mean(analyzer._EI_f[: analyzer._strut_idx() + 1]))
        pe = math.pi**2 * ei_mean / analyzer.strut_bl**2
        amplified, warning, amp = analyzer._pdelta(moment, 0.25 * pe, analyzer._EI_f)

        self.assertFalse(warning)
        self.assertAlmostEqual(amp, 1.0 / (1.0 - 0.25))
        self.assertAlmostEqual(amplified[0], moment[0] * amp)

    def test_divergence_formula_matches_current_closed_form_screening_calculation(self):
        analyzer = WingStressAnalyzer(
            {
                **DEFAULT_INPUTS,
                "root_chord": 60.0,
                "x_ac_c": 0.30,
                "front_spar_percent": 0.20,
                "Cl_alpha": 6.0,
                "Vd_mph": 100.0,
                "altitude_ft": 0.0,
                "dcell_enabled": False,
                "wing_structure_type": "fabric_tube",
            }
        )
        gj = 2_000_000.0
        result = analyzer._divergence(gj)
        rho = isa_density(0.0)
        c_ft = 60.0 / 12.0
        x_ac = 0.30 * 60.0
        x_sc = 0.20 * 60.0
        e_ft = (x_ac - x_sc) / 12.0
        gj_ft = gj / 144.0
        expected_fps = math.sqrt(2.0 * gj_ft / (rho * 6.0 * e_ft * c_ft**2))
        expected_mph = expected_fps * 3600.0 / 5280.0

        self.assertAlmostEqual(result["V_div"], expected_mph)
        self.assertAlmostEqual(result["SF_div"], expected_mph / 100.0)


if __name__ == "__main__":
    unittest.main()
