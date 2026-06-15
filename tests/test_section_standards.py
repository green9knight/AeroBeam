import math
import unittest

from spar_sections import AluminumCSpar, BoxSpar, IBeam, MATERIAL_DB, PlainRect, RoundTube


def transformed_props(elements, reference_material):
    """Independent transformed-section calculation for rectangular elements."""

    sum_ea = sum(MATERIAL_DB[mat]["E"] * b * h for b, h, _, mat in elements)
    sum_eay = sum(MATERIAL_DB[mat]["E"] * b * h * y for b, h, y, mat in elements)
    neutral_axis = sum_eay / sum_ea
    ref_e = MATERIAL_DB[reference_material]["E"]
    inertia = 0.0
    y_min = min(y - h / 2.0 for b, h, y, mat in elements)
    y_max = max(y + h / 2.0 for b, h, y, mat in elements)
    area = 0.0
    for b, h, y, mat in elements:
        area += b * h
        i_self = b * h**3 / 12.0
        i_pa = i_self + b * h * (y - neutral_axis) ** 2
        inertia += MATERIAL_DB[mat]["E"] / ref_e * i_pa
    return {
        "NA": neutral_axis,
        "I_tr": inertia,
        "area": area,
        "y_top": y_max - neutral_axis,
        "y_bot": neutral_axis - y_min,
    }


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

    def test_asymmetric_transformed_i_beam_matches_independent_element_calculation(self):
        spar = IBeam(
            b_top=1.5,
            t_top=0.5,
            b_bot=2.5,
            t_bot=0.75,
            h_web=5.0,
            t_web=0.25,
            cap_mat="Sitka Spruce",
            web_mat="Birch Plywood",
        )
        props = spar.get_props()
        elements = [
            (2.5, 0.75, 0.75 / 2.0, "Sitka Spruce"),
            (0.25, 5.0, 0.75 + 5.0 / 2.0, "Birch Plywood"),
            (1.5, 0.5, 0.75 + 5.0 + 0.5 / 2.0, "Sitka Spruce"),
        ]
        expected = transformed_props(elements, "Sitka Spruce")

        self.assertAlmostEqual(props.NA, expected["NA"])
        self.assertAlmostEqual(props.I_tr, expected["I_tr"])
        self.assertAlmostEqual(props.y_top, expected["y_top"])
        self.assertAlmostEqual(props.y_bot, expected["y_bot"])
        self.assertAlmostEqual(props.area, expected["area"])

    def test_box_spar_matches_independent_element_calculation(self):
        spar = BoxSpar(
            b_outer=3.0,
            h_outer=6.0,
            t_web=0.125,
            t_cap=0.5,
            cap_mat="6061-T6",
            web_mat="6061-T6",
        )
        props = spar.get_props()
        h_web = 6.0 - 2.0 * 0.5
        elements = [
            (3.0, 0.5, 0.25, "6061-T6"),
            (2.0 * 0.125, h_web, 0.5 + h_web / 2.0, "6061-T6"),
            (3.0, 0.5, 6.0 - 0.25, "6061-T6"),
        ]
        expected = transformed_props(elements, "6061-T6")

        self.assertAlmostEqual(props.NA, expected["NA"])
        self.assertAlmostEqual(props.I_tr, expected["I_tr"])
        self.assertAlmostEqual(props.area, expected["area"])

    def test_aluminum_c_spar_single_cap_matches_independent_element_calculation(self):
        spar = AluminumCSpar(
            b_cap=1.5,
            t_cap=0.125,
            h_web=5.0,
            t_web=0.050,
            cap_side="top",
            mat_name="6061-T6",
        )
        props = spar.get_props()
        elements = [
            (0.050, 0.050, 0.050 / 2.0, "6061-T6"),
            (0.050, 5.0, 0.050 + 5.0 / 2.0, "6061-T6"),
            (1.5, 0.125, 0.050 + 5.0 + 0.125 / 2.0, "6061-T6"),
        ]
        expected = transformed_props(elements, "6061-T6")

        self.assertAlmostEqual(props.NA, expected["NA"])
        self.assertAlmostEqual(props.I_tr, expected["I_tr"])
        self.assertAlmostEqual(props.y_top, expected["y_top"])
        self.assertAlmostEqual(props.y_bot, expected["y_bot"])


if __name__ == "__main__":
    unittest.main()
