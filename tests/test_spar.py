import unittest

from aerobeam.loads import LoadCase
from aerobeam.materials import Material, get_material
from aerobeam.spar import BoxSparGeometry, size_box_spar


class BoxSparGeometryTest(unittest.TestCase):
    def test_cross_section_properties_are_positive(self) -> None:
        geometry = BoxSparGeometry(width_m=0.04, height_m=0.12, wall_thickness_m=0.001)

        self.assertGreater(geometry.area_m2, 0.0)
        self.assertGreater(geometry.second_moment_area_m4, 0.0)
        self.assertGreater(geometry.section_modulus_m3, 0.0)

    def test_rejects_wall_that_closes_section(self) -> None:
        with self.assertRaisesRegex(ValueError, "too large"):
            BoxSparGeometry(width_m=0.04, height_m=0.12, wall_thickness_m=0.02)


class SizeBoxSparTest(unittest.TestCase):
    def test_sizes_to_non_negative_margins(self) -> None:
        load_case = LoadCase.from_aircraft_mass(
            mass_kg=12.5,
            span_m=2.4,
            limit_load_factor=4.4,
            safety_factor=1.5,
        )

        result = size_box_spar(
            load_case=load_case,
            material=get_material("6061-t6"),
            width_m=0.04,
            height_m=0.12,
            min_wall_thickness_m=0.0008,
            manufacturing_increment_m=0.0002,
        )

        self.assertGreaterEqual(result.bending_margin, 0.0)
        self.assertGreaterEqual(result.shear_margin, 0.0)
        self.assertAlmostEqual(result.geometry.wall_thickness_m % 0.0002, 0.0, places=12)

    def test_rejects_insufficient_geometry(self) -> None:
        weak_material = Material(
            name="weak",
            density_kg_m3=1000.0,
            bending_strength_pa=1.0,
            shear_strength_pa=1.0,
        )
        load_case = LoadCase(
            gross_weight_n=1000.0,
            span_m=10.0,
            limit_load_factor=5.0,
        )

        with self.assertRaisesRegex(ValueError, "cannot satisfy"):
            size_box_spar(
                load_case=load_case,
                material=weak_material,
                width_m=0.02,
                height_m=0.04,
            )


if __name__ == "__main__":
    unittest.main()
