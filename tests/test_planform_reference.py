"""Tapered planform can hold the leading edge, main spar, or trailing edge straight."""

import unittest

import numpy as np

from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


def wing(reference="Leading edge"):
    return WingStressAnalyzer({
        **DEFAULT_INPUTS,
        "b": 200.0,
        "num_points": 11,
        "root_chord": 60.0,
        "tip_chord": 30.0,
        "taper_start_bl": 40.0,
        "front_spar_percent": 0.25,
        "rear_spar_percent": 0.70,
        "taper_reference": reference,
        "Vd_mph": 0.0,
    })


class PlanformReferenceTests(unittest.TestCase):
    def test_leading_edge_is_the_straight_line(self):
        shape = wing("Leading edge")
        self.assertTrue(np.allclose(shape.y_le, 0.0))
        self.assertAlmostEqual(shape.y_te[-1], 30.0)
        self.assertAlmostEqual(shape.y_front[-1], 0.25 * 30.0)
        self.assertGreater(shape.y_front[0], shape.y_front[-1])

    def test_main_spar_stays_at_the_root_spar_station(self):
        shape = wing("Main spar")
        self.assertTrue(np.allclose(shape.y_front, 0.25 * 60.0))
        self.assertAlmostEqual(shape.y_le[-1], 0.25 * (60.0 - 30.0))
        self.assertAlmostEqual(shape.y_te[-1] - shape.y_le[-1], 30.0)
        self.assertAlmostEqual(shape.y_rear[-1] - shape.y_le[-1], 0.70 * 30.0)

    def test_trailing_edge_stays_at_the_root_chord(self):
        shape = wing("Trailing edge")
        self.assertTrue(np.allclose(shape.y_te, 60.0))
        self.assertAlmostEqual(shape.y_le[-1], 30.0)
        self.assertAlmostEqual(shape.y_front[-1], 30.0 + 0.25 * 30.0)

    def test_constant_inboard_chord_matches_for_every_reference(self):
        shapes = [wing(name) for name in ("Leading edge", "Main spar", "Trailing edge")]
        inboard = shapes[0].x <= 40.0
        for shape in shapes:
            self.assertTrue(np.allclose(shape.y_le[inboard], 0.0))
            self.assertTrue(np.allclose(shape.y_front[inboard], 15.0))
            self.assertTrue(np.allclose(shape.chord_x, shapes[0].chord_x))

    def test_a_missing_choice_keeps_the_leading_edge_straight(self):
        omitted = WingStressAnalyzer({**DEFAULT_INPUTS, "root_chord": 60.0, "tip_chord": 30.0, "num_points": 5})
        self.assertEqual(omitted.taper_reference, "Leading edge")
        self.assertTrue(np.allclose(omitted.y_le, 0.0))


if __name__ == "__main__":
    unittest.main()
