import unittest

import numpy as np

from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


def base_inputs(**overrides):
    inputs = dict(DEFAULT_INPUTS)
    inputs.update(
        {
            "num_points": 81,
            "config": "single_strut",
            "num_spars": 2,
            "b": 240.0,
            "root_chord": 54.0,
            "tip_chord": 54.0,
            "front_spar_percent": 0.30,
            "rear_spar_percent": 0.80,
            "front_spar_load_share": 0.90,
            "strut_bl": 80.0,
            "strut_vert": 44.0,
            "strut_fuse_bl": 11.0,
            "ng_lift": 1800.0,
            "n": 4.0,
            "n_neg": -2.0,
            "front_spar_type": "Round Tube",
            "front_spar_od": 3.0,
            "front_spar_wall": 0.065,
            "rear_spar_type": "Round Tube",
            "rear_spar_od": 1.5,
            "rear_spar_wall": 0.049,
            "dcell_enabled": False,
            "geodetic_enabled": False,
            "wing_structure_type": "fabric_buildup",
            "rib_t_web": 0.0,
            "Vd_mph": 0.0,
            "Cm_ac": 0.0,
        }
    )
    inputs.update(overrides)
    return inputs


class TorsionCouplingTest(unittest.TestCase):
    def test_single_strut_rear_spar_uses_structural_torsion(self):
        analyzer = WingStressAnalyzer(base_inputs())
        analyzer.analyze()

        rear_sigma = np.max(np.abs(analyzer.pos["sigma_rear"]))
        rear_deflection = np.max(np.abs(analyzer.pos["z_rear"]))

        self.assertGreater(rear_sigma, 1.0)
        self.assertGreater(rear_deflection, 1e-6)
        self.assertIn("M_front", analyzer.pos)
        self.assertIn("M_rear", analyzer.pos)
        self.assertIn("z_delta", analyzer.pos)
        self.assertGreater(np.max(np.abs(analyzer.pos["M_rear"])), 1.0)
        self.assertFalse(np.allclose(analyzer.pos["M_front"], analyzer.pos["M_rear"]))
        self.assertTrue(np.allclose(analyzer.pos["z_delta"], analyzer.pos["z_rear"] - analyzer.pos["z_front"]))

    def test_geodetic_transfer_stiffness_is_available_for_case_solution(self):
        analyzer = WingStressAnalyzer(
            base_inputs(
                dcell_enabled=True,
                geodetic_enabled=True,
                rib_t_web=0.125,
                geodetic_w=1.0,
                geodetic_t=0.125,
                geodetic_strips_per_bay=2,
            )
        )
        analyzer.analyze()

        self.assertGreater(analyzer._torsion_stiffness, 0.0)
        self.assertEqual(analyzer._torsion_stiffness, analyzer._torsion_transfer["k_total"])
        self.assertGreater(analyzer._geodetic_kappa, 0.0)
        self.assertLessEqual(analyzer._geodetic_kappa, 1.0)


if __name__ == "__main__":
    unittest.main()
