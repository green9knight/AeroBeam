import unittest

import numpy as np

from wing_stress_analyzer import DEFAULT_INPUTS, WingStressAnalyzer


def beam_fe_support_reactions(x, w, ei, support_positions):
    """Independent Euler-Bernoulli beam FE reaction solver.

    Vertical displacement is positive downward. Rotations are free at supports.
    Supports constrain vertical displacement only, matching AeroBeam's pinned
    support idealization for root/jury/main strut reactions.
    """

    n = len(x)
    ndof = 2 * n
    K = np.zeros((ndof, ndof))
    F = np.zeros(ndof)

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
        dofs = [2 * i, 2 * i + 1, 2 * (i + 1), 2 * (i + 1) + 1]
        for a in range(4):
            F[dofs[a]] += f[a]
            for b in range(4):
                K[dofs[a], dofs[b]] += k[a, b]

    constrained_nodes = [int(np.argmin(np.abs(x - pos))) for pos in support_positions]
    constrained = [2 * node for node in constrained_nodes]
    free = [idx for idx in range(ndof) if idx not in constrained]

    U = np.zeros(ndof)
    U[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
    residual = K @ U - F

    # Residual at a constrained vertical DOF is opposite the upward support load.
    return {
        pos: -float(residual[2 * node])
        for pos, node in zip(support_positions, constrained_nodes)
    }


def beam_fe_displacements(x, w, ei, support_positions, fixed_rotations=()):
    """Return vertical displacements from an independent Euler-Bernoulli FE solve."""

    n = len(x)
    ndof = 2 * n
    K = np.zeros((ndof, ndof))
    F = np.zeros(ndof)

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
        dofs = [2 * i, 2 * i + 1, 2 * (i + 1), 2 * (i + 1) + 1]
        for a in range(4):
            F[dofs[a]] += f[a]
            for b in range(4):
                K[dofs[a], dofs[b]] += k[a, b]

    constrained_nodes = [int(np.argmin(np.abs(x - pos))) for pos in support_positions]
    constrained = [2 * node for node in constrained_nodes]
    constrained += [2 * int(np.argmin(np.abs(x - pos))) + 1 for pos in fixed_rotations]
    free = [idx for idx in range(ndof) if idx not in constrained]
    U = np.zeros(ndof)
    U[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
    return U[0::2]


class JuryIndependentBeamTest(unittest.TestCase):
    def test_cantilever_deflection_matches_independent_fe_model(self):
        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "b": 200.0,
                "num_points": 101,
                "lift_distribution_type": "uniform",
                "ng_lift": 1000.0,
                "config": "cantilever",
                "front_spar_load_share": 1.0,
                "secondary_bending": False,
                "distribute_wing_weight": False,
            }
        )
        analyzer = WingStressAnalyzer(inputs)
        analyzer.analyze()
        fe_z = beam_fe_displacements(
            analyzer.x,
            analyzer._lift_dist(inputs["ng_lift"]),
            analyzer._EI_f,
            [0.0],
            fixed_rotations=[0.0],
        )

        self.assertAlmostEqual(analyzer.pos["z_front"][-1], fe_z[-1], delta=abs(fe_z[-1]) * 0.03)

    def test_main_strut_reaction_matches_root_moment_static_relation(self):
        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "b": 200.0,
                "num_points": 101,
                "lift_distribution_type": "uniform",
                "ng_lift": 1000.0,
                "config": "strut_braced",
                "front_spar_load_share": 1.0,
                "strut_bl": 80.0,
                "jury_strut": False,
                "secondary_bending": False,
                "distribute_wing_weight": False,
            }
        )
        analyzer = WingStressAnalyzer(inputs)
        analyzer.analyze()

        # Uniform cantilever root moment is L * b_half / 2. A single ideal
        # strut support at BL s supplies R = M_root / s.
        expected = (1000.0 * 100.0 / 2.0) / 80.0
        self.assertAlmostEqual(analyzer.strut_summary["Fv_strut_attach"], expected, delta=expected * 0.01)

    def test_strut_braced_uniform_deflection_matches_independent_fe_model(self):
        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "b": 200.0,
                "num_points": 101,
                "root_chord": 48.0,
                "tip_chord": 48.0,
                "lift_distribution_type": "uniform",
                "ng_lift": 1000.0,
                "config": "strut_braced",
                "front_spar_load_share": 1.0,
                "front_spar_type": "Round Tube",
                "front_spar_od": 3.0,
                "front_spar_wall": 0.065,
                "strut_fuse_bl": 0.0,
                "strut_bl": 80.0,
                "jury_strut": False,
                "secondary_bending": False,
                "distribute_wing_weight": False,
                "dcell_enabled": False,
                "geodetic_enabled": False,
            }
        )
        analyzer = WingStressAnalyzer(inputs)
        analyzer.analyze()
        w = analyzer._lift_dist(inputs["ng_lift"])
        reactions = beam_fe_support_reactions(analyzer.x, w, analyzer._EI_f, [0.0, inputs["strut_bl"]])
        fe_z = beam_fe_displacements(analyzer.x, w, analyzer._EI_f, [0.0, inputs["strut_bl"]])

        self.assertAlmostEqual(
            analyzer.strut_summary["Fv_strut_attach"],
            reactions[inputs["strut_bl"]],
            delta=abs(reactions[inputs["strut_bl"]]) * 0.02,
        )
        self.assertAlmostEqual(analyzer.pos["z_front"][-1], fe_z[-1], delta=abs(fe_z[-1]) * 0.06)

    def test_strut_braced_elliptical_deflection_matches_independent_fe_model(self):
        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "b": 200.0,
                "num_points": 101,
                "root_chord": 48.0,
                "tip_chord": 48.0,
                "lift_distribution_type": "elliptical",
                "ng_lift": 1000.0,
                "config": "strut_braced",
                "front_spar_load_share": 1.0,
                "front_spar_type": "Round Tube",
                "front_spar_od": 3.0,
                "front_spar_wall": 0.065,
                "strut_fuse_bl": 0.0,
                "strut_bl": 80.0,
                "jury_strut": False,
                "secondary_bending": False,
                "distribute_wing_weight": False,
                "dcell_enabled": False,
                "geodetic_enabled": False,
            }
        )
        analyzer = WingStressAnalyzer(inputs)
        analyzer.analyze()
        w = analyzer._lift_dist(inputs["ng_lift"])
        reactions = beam_fe_support_reactions(analyzer.x, w, analyzer._EI_f, [0.0, inputs["strut_bl"]])
        fe_z = beam_fe_displacements(analyzer.x, w, analyzer._EI_f, [0.0, inputs["strut_bl"]])

        self.assertAlmostEqual(
            analyzer.strut_summary["Fv_strut_attach"],
            reactions[inputs["strut_bl"]],
            delta=abs(reactions[inputs["strut_bl"]]) * 0.03,
        )
        self.assertAlmostEqual(analyzer.pos["z_front"][-1], fe_z[-1], delta=abs(fe_z[-1]) * 0.06)

    def test_jury_brace_does_not_change_spar_support_reaction(self):
        inputs = dict(DEFAULT_INPUTS)
        inputs.update(
            {
                "b": 200.0,
                "num_points": 101,
                "root_chord": 48.0,
                "tip_chord": 48.0,
                "lift_distribution_type": "uniform",
                "ng_lift": 1000.0,
                "config": "strut_braced",
                "front_spar_load_share": 1.0,
                "strut_fuse_bl": 0.0,
                "strut_bl": 80.0,
                "jury_strut": False,
                "secondary_bending": False,
                "distribute_wing_weight": False,
                "dcell_enabled": False,
                "geodetic_enabled": False,
            }
        )
        plain = WingStressAnalyzer(inputs)
        plain.analyze()
        braced = WingStressAnalyzer({**inputs, "jury_strut": True, "jury_spar_bl": 40.0})
        braced.analyze()

        self.assertEqual(braced.strut_summary["Fv_jury"], 0.0)
        self.assertAlmostEqual(
            braced.strut_summary["Fv_strut_attach"],
            plain.strut_summary["Fv_strut_attach"],
        )
        self.assertAlmostEqual(braced.pos["M_front"][10], plain.pos["M_front"][10])
        self.assertAlmostEqual(
            braced.strut_summary["jury_brace_load"],
            0.025 * abs(braced.neg["F_axial"]),
        )
        self.assertLess(
            braced.strut_summary["effective_length"],
            plain.strut_summary["effective_length"],
        )


if __name__ == "__main__":
    unittest.main()
