import unittest

import math
import numpy as np

from spar_sections import STRUT_MATERIALS
from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


def two_spar_spring_fe(x, w_front, w_rear, ei_front, ei_rear, k_connection):
    """Independent two-beam FE model with distributed vertical coupling springs.

    This is a validation scaffold for rear-spar coupling trends. It is not the
    production solver. Both spars are cantilevered at the root. Springs connect
    front and rear vertical displacement DOFs at each span station.
    """

    n = len(x)
    ndof = 4 * n  # front v/th, rear v/th per station
    K = np.zeros((ndof, ndof))
    F = np.zeros(ndof)

    def dofs(spar, node):
        base = 0 if spar == 0 else 2 * n
        return [base + 2 * node, base + 2 * node + 1]

    def assemble_beam(spar, w, ei):
        for i in range(n - 1):
            L = x[i + 1] - x[i]
            EI = 0.5 * (ei[i] + ei[i + 1])
            k = EI / L**3 * np.array(
                [
                    [12, 6 * L, -12, 6 * L],
                    [6 * L, 4 * L**2, -6 * L, 2 * L**2],
                    [-12, -6 * L, 12, -6 * L],
                    [6 * L, 2 * L**2, -6 * L, 4 * L**2],
                ]
            )
            q = 0.5 * (w[i] + w[i + 1])
            f = q * L / 2.0 * np.array([1, L / 6.0, 1, -L / 6.0])
            edofs = dofs(spar, i) + dofs(spar, i + 1)
            for a in range(4):
                F[edofs[a]] += f[a]
                for b in range(4):
                    K[edofs[a], edofs[b]] += k[a, b]

    assemble_beam(0, w_front, ei_front)
    assemble_beam(1, w_rear, ei_rear)

    # Convert distributed connection stiffness [lb/in span per in deflection]
    # to nodal springs using tributary span length.
    for i in range(n):
        tributary = (x[1] - x[0]) if 0 < i < n - 1 else (x[1] - x[0]) / 2.0
        k_node = k_connection * tributary
        vf = dofs(0, i)[0]
        vr = dofs(1, i)[0]
        K[vf, vf] += k_node
        K[vr, vr] += k_node
        K[vf, vr] -= k_node
        K[vr, vf] -= k_node

    constrained = [dofs(0, 0)[0], dofs(0, 0)[1], dofs(1, 0)[0], dofs(1, 0)[1]]
    free = [idx for idx in range(ndof) if idx not in constrained]
    U = np.zeros(ndof)
    U[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
    z_front = U[0 : 2 * n : 2]
    z_rear = U[2 * n : 4 * n : 2]
    return z_front, z_rear


class TwoSparCouplingTest(unittest.TestCase):
    def make_analyzer(self):
        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "b": 200.0,
                "num_points": 61,
                "config": "cantilever",
                "front_spar_load_share": 0.7,
                "lift_distribution_type": "uniform",
                "ng_lift": 1000.0,
                "front_spar_type": "Round Tube",
                "front_spar_od": 3.0,
                "front_spar_wall": 0.065,
                "rear_spar_type": "Round Tube",
                "rear_spar_od": 1.5,
                "rear_spar_wall": 0.049,
                "dcell_enabled": False,
                "geodetic_enabled": False,
            }
        )
        analyzer = WingStressAnalyzer(inputs)
        analyzer._spar_arrays()
        return analyzer

    def test_zero_coupling_matches_independent_cantilever_beams(self):
        analyzer = self.make_analyzer()
        w_total = analyzer._lift_dist(1000.0)
        w_front = w_total * 0.7
        w_rear = w_total * 0.3
        zf, zr = two_spar_spring_fe(analyzer.x, w_front, w_rear, analyzer._EI_f, analyzer._EI_r, 0.0)
        _, zf_ind = analyzer._deflect_cantilever(analyzer._shear_moment(w_front)[1], analyzer._EI_f)
        _, zr_ind = analyzer._deflect_cantilever(analyzer._shear_moment(w_rear)[1], analyzer._EI_r)

        self.assertAlmostEqual(zf[-1], zf_ind[-1], delta=abs(zf_ind[-1]) * 0.03)
        self.assertAlmostEqual(zr[-1], zr_ind[-1], delta=abs(zr_ind[-1]) * 0.03)

    def test_high_coupling_drives_relative_deflection_toward_zero(self):
        analyzer = self.make_analyzer()
        w_total = analyzer._lift_dist(1000.0)
        w_front = w_total * 0.7
        w_rear = w_total * 0.3
        zf_free, zr_free = two_spar_spring_fe(analyzer.x, w_front, w_rear, analyzer._EI_f, analyzer._EI_r, 0.0)
        zf_c, zr_c = two_spar_spring_fe(analyzer.x, w_front, w_rear, analyzer._EI_f, analyzer._EI_r, 1e6)

        free_delta = np.max(np.abs(zr_free - zf_free))
        coupled_delta = np.max(np.abs(zr_c - zf_c))
        self.assertLess(coupled_delta, free_delta * 0.02)

    def test_aerobeam_kappa_increases_with_geodetic_stiffness(self):
        base = {
            **DEFAULT_INPUTS,
            "b": 200.0,
            "num_points": 61,
            "config": "cantilever",
            "front_spar_load_share": 0.7,
            "wing_structure_type": "fabric_buildup",
            "dcell_enabled": True,
            "geodetic_enabled": True,
        }
        low = WingStressAnalyzer({**base, "geodetic_reduction_factor": 0.25})
        high = WingStressAnalyzer({**base, "geodetic_reduction_factor": 1.0})
        low.analyze()
        high.analyze()

        self.assertGreater(high._geodetic_kappa, low._geodetic_kappa)
        self.assertLessEqual(high._geodetic_kappa, 1.0)

    def test_aerobeam_rear_response_uses_elastic_coupling_solver(self):
        base = {
            **DEFAULT_INPUTS,
            "b": 200.0,
            "num_points": 61,
            "config": "cantilever",
            "front_spar_load_share": 0.7,
            "wing_structure_type": "fabric_buildup",
            "dcell_enabled": True,
            "geodetic_enabled": True,
            "Vd_mph": 0.0,
            "Cm_ac": 0.0,
        }
        weak = WingStressAnalyzer({**base, "geodetic_reduction_factor": 0.0})
        strong = WingStressAnalyzer({**base, "geodetic_reduction_factor": 1.0})
        weak.analyze()
        strong.analyze()

        self.assertGreater(weak.pos["z_delta_max"], strong.pos["z_delta_max"])
        self.assertGreater(strong._geodetic_kappa, weak._geodetic_kappa)

    def test_jury_tube_links_reduce_relative_deflection(self):
        base = {
            **DEFAULT_INPUTS,
            "b": 200.0,
            "num_points": 61,
            "config": "cantilever",
            "front_spar_load_share": 0.7,
            "wing_structure_type": "fabric_buildup",
            "dcell_enabled": False,
            "geodetic_enabled": False,
            "Vd_mph": 0.0,
            "Cm_ac": 0.0,
            "jury_strut": True,
            "jury_spar_bl": 50.0,
            "jury_tube_mat": "6061-T6 Aluminum",
            "jury_tube_od": 0.75,
            "jury_tube_wall": 0.035,
            "jury_front_link_length": 18.0,
            "jury_rear_link_length": 18.0,
            "jury_front_link_angle": 45.0,
            "jury_rear_link_angle": 45.0,
        }
        loose = WingStressAnalyzer({**base, "jury_tube_wall": 0.0})
        tied = WingStressAnalyzer(base)
        loose.analyze()
        tied.analyze()

        self.assertGreater(loose.pos["z_delta_max"], tied.pos["z_delta_max"])
        idx = int(np.argmin(np.abs(tied.x - 50.0)))
        self.assertLess(abs(tied.pos["z_delta"][idx]), abs(loose.pos["z_delta"][idx]))
        self.assertGreater(tied._jury_coupling_stiffness(), 0.0)

    def test_jury_tube_coupling_stiffness_matches_series_spring_projection(self):
        inputs = {
            **DEFAULT_INPUTS,
            "jury_strut": True,
            "jury_tube_mat": "6061-T6 Aluminum",
            "jury_tube_od": 0.75,
            "jury_tube_wall": 0.035,
            "jury_front_link_length": 18.0,
            "jury_rear_link_length": 24.0,
            "jury_front_link_angle": 45.0,
            "jury_rear_link_angle": 30.0,
        }
        analyzer = WingStressAnalyzer(inputs)
        area = analyzer._jury_tube_area()
        E = STRUT_MATERIALS["6061-T6 Aluminum"]["E"]
        kf = E * area / 18.0 * math.sin(math.radians(45.0)) ** 2
        kr = E * area / 24.0 * math.sin(math.radians(30.0)) ** 2
        expected = 1.0 / (1.0 / kf + 1.0 / kr)
        self.assertAlmostEqual(analyzer._jury_coupling_stiffness(), expected)


if __name__ == "__main__":
    unittest.main()
