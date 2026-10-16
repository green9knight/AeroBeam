"""Spar tip position includes twist about the shear center."""

import unittest

import numpy as np

from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


def wing(**overrides):
    data = {
        **DEFAULT_INPUTS,
        "b": 200.0,
        "num_points": 21,
        "config": "cantilever",
        "num_spars": 2,
        "root_chord": 60.0,
        "tip_chord": 60.0,
        "taper_start_bl": 100.0,
        "front_spar_percent": 0.15,
        "rear_spar_percent": 0.70,
        "x_ac_c": 0.30,
        "Cm_ac": 0.0,
        "Vd_mph": 120.0,
        "altitude_ft": 0.0,
        "dcell_enabled": True,
        "dcell_skin_thick": 0.04,
        "dcell_skin_mat": "2024-T3",
        "wing_structure_type": "fabric_buildup",
        "ng_lift": 1500.0,
        "distribute_wing_weight": False,
        "jury_strut": False,
        "secondary_bending": False,
    }
    data.update(overrides)
    model = WingStressAnalyzer(data)
    model.analyze()
    return model


class TwistDeflectionTests(unittest.TestCase):
    def test_rear_spar_position_adds_the_shear_center_twist(self):
        model = wing()
        y_sc = model._shear_center_y()
        phi = model.pos["phi"]
        expected_rear = model.pos["z_bend_rear"] - phi * (model.y_rear - y_sc)
        expected_front = model.pos["z_bend_front"] - phi * (model.y_front - y_sc)
        self.assertGreater(phi[-1], 0.0)
        self.assertTrue(np.allclose(model.pos["z_rear"], expected_rear))
        self.assertTrue(np.allclose(model.pos["z_front"], expected_front))
        self.assertLess(model.pos["z_rear"][-1], model.pos["z_bend_rear"][-1])
        self.assertAlmostEqual(model.pos["phi"][0], 0.0)

    def test_bending_stress_does_not_use_the_twist_offset(self):
        twisted = wing()
        sc_frac = float(twisted._shear_center_y()[0] - twisted.y_le[0]) / twisted.root_chord
        straight = wing(Vd_mph=0.0, Cm_ac=0.0, x_ac_c=sc_frac)
        self.assertAlmostEqual(straight.pos["phi"][-1], 0.0, places=6)
        self.assertTrue(np.allclose(straight.pos["z_rear"], straight.pos["z_bend_rear"]))
        self.assertAlmostEqual(
            float(np.max(np.abs(twisted.pos["sigma_rear"]))),
            float(np.max(np.abs(straight.pos["sigma_rear"]))),
            places=3,
        )

    def test_negative_g_reverses_the_twist_offset(self):
        model = wing()
        self.assertLess(model.neg["phi"][-1], 0.0)
        self.assertGreater(model.neg["z_rear"][-1], model.neg["z_bend_rear"][-1])

    def test_ribs_lock_the_spars_to_one_bending_curve(self):
        model = wing()
        self.assertTrue(np.allclose(model.pos["z_bend_front"], model.pos["z_bend_rear"]))
        gap = model.y_rear - model.y_front
        tied = model.pos["z_front"] - model.pos["phi"] * gap
        self.assertTrue(np.allclose(model.pos["z_rear"], tied))

    def test_a_moving_shear_center_uses_the_local_offset(self):
        model = wing(
            torsion_box_enabled=True,
            torsion_box_bays=2,
            torsion_box_top_mat="2024-T3",
            torsion_box_top_thick=0.04,
            torsion_box_bot_mat="2024-T3",
            torsion_box_bot_thick=0.04,
            rib_spacing=12.0,
            num_points=101,
            b=240.0,
            root_chord=60.0,
            tip_chord=36.0,
            taper_start_bl=24.0,
        )
        y_sc = model._shear_center_y()
        jump = int(np.argmax(np.abs(np.diff(y_sc))))
        self.assertGreater(abs(float(y_sc[jump + 1] - y_sc[jump])), 5.0)
        phi = model.pos["phi"]
        dphi = float(phi[jump + 1] - phi[jump])
        bend = float(model.pos["z_bend_rear"][jump + 1] - model.pos["z_bend_rear"][jump])
        lever = float(model.y_rear[jump + 1] - y_sc[jump + 1])
        dz = float(model.pos["z_rear"][jump + 1] - model.pos["z_rear"][jump])
        # Virtual work at this station uses only the twist increment.
        self.assertAlmostEqual(dz, bend - lever * dphi, places=9)


if __name__ == "__main__":
    unittest.main()
