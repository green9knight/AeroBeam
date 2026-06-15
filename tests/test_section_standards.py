import math
import unittest

from spar_sections import IBeam, MATERIAL_DB, PlainRect, RoundTube


class SectionStandardsTest(unittest.TestCase):
    def test_round_tube_area_and_inertia_match_annulus_formula(self):
        tube = RoundTube(OD=3.0, wall=0.065, mat_name="6061-T6")
        props = tube.get_props()
        inner = 3.0 - 2.0 * 0.065
        expected_area = math.pi / 4.0 * (3.0**2 - inner**2)
        expected_i = math.pi / 64.0 * (3.0**4 - inner**4)

        self.assertAlmostEqual(props.area, expected_area)
        self.assertAlmostEqual(props.I_tr, expected_i)
        self.assertAlmostEqual(props.EI, MATERIAL_DB["6061-T6"]["E"] * expected_i)
        self.assertAlmostEqual(props.y_top, 1.5)
        self.assertAlmostEqual(props.y_bot, 1.5)

    def test_plain_rectangle_matches_bh3_over_12(self):
        rect = PlainRect(width=2.0, height=6.0, mat_name="Sitka Spruce")
        props = rect.get_props()
        expected_i = 2.0 * 6.0**3 / 12.0

        self.assertAlmostEqual(props.area, 12.0)
        self.assertAlmostEqual(props.I_tr, expected_i)
        self.assertAlmostEqual(props.NA, 3.0)
        self.assertAlmostEqual(props.y_top, 3.0)
        self.assertAlmostEqual(props.y_bot, 3.0)

    def test_symmetric_same_material_i_beam_neutral_axis_and_inertia(self):
        spar = IBeam(
            b_top=2.0,
            t_top=0.5,
            b_bot=2.0,
            t_bot=0.5,
            h_web=5.0,
            t_web=0.25,
            cap_mat="6061-T6",
            web_mat="6061-T6",
        )
        props = spar.get_props()
        total_height = 6.0
        expected_na = total_height / 2.0

        # Hand calculation by rectangular elements about the section NA.
        cap_area = 2.0 * 0.5
        cap_i_self = 2.0 * 0.5**3 / 12.0
        cap_offset = 2.75
        web_i = 0.25 * 5.0**3 / 12.0
        expected_i = 2.0 * (cap_i_self + cap_area * cap_offset**2) + web_i

        self.assertAlmostEqual(props.NA, expected_na)
        self.assertAlmostEqual(props.I_tr, expected_i)
        self.assertAlmostEqual(props.y_top, 3.0)
        self.assertAlmostEqual(props.y_bot, 3.0)


if __name__ == "__main__":
    unittest.main()
