import unittest

import numpy as np

from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


def wing(**overrides):
    inputs = dict(DEFAULT_INPUTS)
    inputs.update(
        {
            "num_points": 81,
            "b": 300.0,
            "root_chord": 60.0,
            "tip_chord": 60.0,
            "taper_start_bl": 0.0,
            "rib_spacing": 20.0,
            "config": "cantilever",
            "num_spars": 2,
            "front_spar_percent": 0.25,
            "rear_spar_percent": 0.70,
            "dcell_enabled": True,
            "dcell_skin_mat": "6061-T6",
            "dcell_skin_thick": 0.020,
            "wing_structure_type": "fabric_buildup",
            "geodetic_enabled": False,
            "airfoil_t_c": 0.12,
            "x_ac_c": 0.25,
            "Cl_alpha": 6.0,
            "Vd_mph": 100.0,
            "altitude_ft": 0.0,
            "torsion_box_enabled": False,
        }
    )
    inputs.update(overrides)
    analyzer = WingStressAnalyzer(inputs)
    analyzer.analyze()
    return analyzer


class TorsionBoxTest(unittest.TestCase):
    def test_box_is_off_unless_chosen(self):
        plain = wing()
        stored = wing(
            torsion_box_enabled=False,
            torsion_box_bays=6,
            torsion_box_top_thick=0.25,
            torsion_box_bot_thick=0.25,
        )
        zero_bays = wing(
            torsion_box_enabled=True,
            torsion_box_bays=0,
            torsion_box_top_thick=0.25,
            torsion_box_bot_thick=0.25,
        )

        self.assertTrue(np.allclose(stored.GJ, plain.GJ))
        self.assertTrue(np.allclose(zero_bays.GJ, plain.GJ))
        self.assertEqual(stored._torsion_box_end(), 0.0)
        self.assertNotIn("spanwise", plain.divergence)

    def test_inboard_bays_stiffen_only_the_sheeted_span(self):
        plain = wing()
        boxed = wing(
            torsion_box_enabled=True,
            torsion_box_bays=2,
            torsion_box_top_mat="6061-T6",
            torsion_box_bot_mat="6061-T6",
            torsion_box_top_thick=0.040,
            torsion_box_bot_thick=0.032,
        )

        self.assertAlmostEqual(boxed._torsion_box_end(), 40.0)
        self.assertGreater(boxed.GJ[0], plain.GJ[0] * 1.5)
        outboard = np.where(boxed.x > 40.0)[0][0]
        self.assertAlmostEqual(boxed.GJ[outboard], plain.GJ[outboard], places=3)
        self.assertGreater(boxed.divergence["x_sc"], plain.divergence["x_sc"])
        self.assertIn("torsion-box", boxed.divergence["sc_method"])
        self.assertTrue(np.allclose(boxed._EI_f, plain._EI_f))
        self.assertTrue(np.allclose(boxed._EI_r, plain._EI_r))

    def test_sheet_material_and_each_thickness_change_gj(self):
        plywood = wing(
            torsion_box_enabled=True,
            torsion_box_bays=2,
            torsion_box_top_mat="Birch Plywood",
            torsion_box_bot_mat="Birch Plywood",
            torsion_box_top_thick=0.125,
            torsion_box_bot_thick=0.125,
        )
        aluminum = wing(
            torsion_box_enabled=True,
            torsion_box_bays=2,
            torsion_box_top_mat="2024-T3",
            torsion_box_bot_mat="2024-T3",
            torsion_box_top_thick=0.125,
            torsion_box_bot_thick=0.125,
        )
        thin_top = wing(
            torsion_box_enabled=True,
            torsion_box_bays=2,
            torsion_box_top_mat="2024-T3",
            torsion_box_bot_mat="Birch Plywood",
            torsion_box_top_thick=0.020,
            torsion_box_bot_thick=0.125,
        )
        thick_top = wing(
            torsion_box_enabled=True,
            torsion_box_bays=2,
            torsion_box_top_mat="2024-T3",
            torsion_box_bot_mat="Birch Plywood",
            torsion_box_top_thick=0.080,
            torsion_box_bot_thick=0.125,
        )
        thin_bot = wing(
            torsion_box_enabled=True,
            torsion_box_bays=2,
            torsion_box_top_mat="Birch Plywood",
            torsion_box_bot_mat="2024-T3",
            torsion_box_top_thick=0.125,
            torsion_box_bot_thick=0.020,
        )
        thick_bot = wing(
            torsion_box_enabled=True,
            torsion_box_bays=2,
            torsion_box_top_mat="Birch Plywood",
            torsion_box_bot_mat="2024-T3",
            torsion_box_top_thick=0.125,
            torsion_box_bot_thick=0.080,
        )

        self.assertGreater(aluminum.GJ[0], plywood.GJ[0])
        self.assertGreater(thick_top.GJ[0], thin_top.GJ[0])
        self.assertGreater(thick_bot.GJ[0], thin_bot.GJ[0])
        text = plywood.summary_text()
        self.assertIn("Birch Plywood", text)
        self.assertIn("Top sheet: 0.125 in", text)
        self.assertIn("Bottom sheet: 0.125 in", text)

    def test_full_span_box_matches_the_uniform_divergence_formula(self):
        boxed = wing(
            torsion_box_enabled=True,
            torsion_box_bays=20,
            torsion_box_top_mat="6061-T6",
            torsion_box_bot_mat="6061-T6",
            torsion_box_top_thick=0.032,
            torsion_box_bot_thick=0.032,
        )
        plain = wing()
        closed = boxed._divergence(float(boxed.GJ[0]))

        self.assertAlmostEqual(boxed._torsion_box_end(), boxed.b_half)
        self.assertTrue(boxed.divergence["spanwise"])
        self.assertAlmostEqual(
            boxed.divergence["V_div"], closed["V_div"], delta=closed["V_div"] * 0.02
        )
        self.assertGreater(boxed.divergence["V_div"], plain.divergence["V_div"])


if __name__ == "__main__":
    unittest.main()
