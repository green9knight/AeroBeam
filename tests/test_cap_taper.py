"""Built-up spar caps are a root size and a tip size."""

import unittest

import numpy as np

from spar_sections import BoxSpar, IBeam, RoundTube, resolved_tip
from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


def ibeam(**tips):
    return IBeam(
        b_top=2.0, t_top=1.0, b_bot=2.0, t_bot=1.0,
        h_web=4.0, t_web=0.125, **tips,
    )


def wing(**overrides):
    data = {
        **DEFAULT_INPUTS,
        "b": 200.0,
        "num_points": 5,
        "root_chord": 60.0,
        "tip_chord": 30.0,
        "taper_start_bl": 40.0,
        "front_spar_type": "I-Beam",
        "rear_spar_type": "Round Tube",
        "front_spar_b_top": 2.0,
        "front_spar_t_top": 1.0,
        "front_spar_b_bot": 2.0,
        "front_spar_t_bot": 1.0,
        "front_spar_h_web": 4.0,
        "front_spar_t_web": 0.125,
        "Vd_mph": 0.0,
    }
    data.update(overrides)
    model = WingStressAnalyzer(data)
    model._spar_arrays()
    return model


class CapTaperTests(unittest.TestCase):
    def test_a_blank_or_zero_tip_matches_the_root(self):
        spar = ibeam()
        self.assertEqual(resolved_tip(None, 2.0), 2.0)
        self.assertEqual(resolved_tip(0, 2.0), 2.0)
        self.assertEqual(resolved_tip("nope", 2.0), 2.0)
        self.assertEqual(spar.caps_at(1.0), (2.0, 1.0, 2.0, 1.0))

    def test_halfway_is_the_average_of_root_and_tip(self):
        spar = ibeam(b_top_tip=1.0, t_top_tip=0.5, b_bot_tip=1.0, t_bot_tip=0.5)
        self.assertEqual(spar.caps_at(0.0), (2.0, 1.0, 2.0, 1.0))
        self.assertEqual(spar.caps_at(0.5), (1.5, 0.75, 1.5, 0.75))
        self.assertEqual(spar.caps_at(1.0), (1.0, 0.5, 1.0, 0.5))

    def test_station_caps_keep_the_web_gauge(self):
        spar = ibeam(b_top_tip=1.0, t_top_tip=0.5, b_bot_tip=1.0, t_bot_tip=0.5)
        at_tip = spar.get_props(0.5, caps=spar.caps_at(1.0))
        scaled_everything = spar.get_props(0.5)
        self.assertAlmostEqual(at_tip.area, 1.0 * 0.5 * 2 + 0.125 * 2.0)
        self.assertNotAlmostEqual(at_tip.EI, scaled_everything.EI)

    def test_inboard_of_taper_start_keeps_the_root_caps(self):
        model = wing(
            front_spar_b_top_tip=1.0, front_spar_t_top_tip=0.5,
            front_spar_b_bot_tip=1.0, front_spar_t_bot_tip=0.5,
        )
        root = model.front_spar.get_props(1.0, caps=model.front_spar.caps_at(0.0))
        self.assertTrue(np.allclose(model._EI_f[model.x <= 40.0], root.EI))
        tip = model.front_spar.get_props(0.5, caps=model.front_spar.caps_at(1.0))
        self.assertAlmostEqual(model._EI_f[-1], tip.EI)

    def test_omitted_tip_does_not_shrink_the_caps_with_the_chord(self):
        model = wing()
        tip = model.front_spar.get_props(0.5, caps=model.front_spar.caps_at(0.0))
        self.assertAlmostEqual(model._EI_f[-1], tip.EI)
        self.assertEqual(model.front_spar.caps_at(1.0), model.front_spar.caps_at(0.0))

    def test_equal_caps_on_a_constant_chord_keep_one_stiffness(self):
        model = wing(tip_chord=60.0, taper_start_bl=0.0, front_spar_b_top_tip=2.0, front_spar_t_top_tip=1.0,
                     front_spar_b_bot_tip=2.0, front_spar_t_bot_tip=1.0)
        self.assertTrue(np.allclose(model._EI_f, model._EI_f[0]))

    def test_a_round_tube_stays_constant(self):
        model = wing(front_spar_type="Round Tube", rear_spar_type="Round Tube")
        tube = RoundTube(model.front_spar.OD, model.front_spar.wall, model.front_spar.mat_name)
        self.assertTrue(np.allclose(model._EI_f, tube.get_props(1.0).EI))

    def test_box_width_and_cap_thickness_have_their_own_tip(self):
        box = BoxSpar(2.0, 5.0, 0.125, 0.75, b_outer_tip=1.0, t_cap_tip=0.25)
        self.assertEqual(box.caps_at(1.0), (1.0, 0.25))
        self.assertEqual(box.caps_at(0.0), (2.0, 0.75))


if __name__ == "__main__":
    unittest.main()
