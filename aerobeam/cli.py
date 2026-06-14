"""Command line interface for AeroBeam."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aerobeam.loads import LoadCase
from aerobeam.materials import get_material
from aerobeam.spar import SparDesignResult, size_box_spar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Size a rectangular wing box spar")
    parser.add_argument("input", type=Path, help="Path to an AeroBeam JSON input file")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format",
    )
    args = parser.parse_args(argv)

    try:
        result = design_from_file(args.input)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")

    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_text_report(result))
    return 0


def design_from_file(path: Path) -> SparDesignResult:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return design_from_mapping(data)


def design_from_mapping(data: dict[str, Any]) -> SparDesignResult:
    aircraft = _required_mapping(data, "aircraft")
    spar = _required_mapping(data, "spar")
    material_name = _required(data, "material")

    load_case = LoadCase.from_aircraft_mass(
        mass_kg=float(_required(aircraft, "mass_kg")),
        span_m=float(_required(aircraft, "span_m")),
        limit_load_factor=float(_required(aircraft, "limit_load_factor")),
        safety_factor=float(aircraft.get("safety_factor", 1.5)),
        distribution=str(aircraft.get("load_distribution", "elliptical")).lower(),
    )

    return size_box_spar(
        load_case=load_case,
        material=get_material(str(material_name)),
        width_m=float(_required(spar, "width_m")),
        height_m=float(_required(spar, "height_m")),
        min_wall_thickness_m=float(spar.get("min_wall_thickness_m", 0.0005)),
        manufacturing_increment_m=float(spar.get("manufacturing_increment_m", 0.0001)),
    )


def format_text_report(result: SparDesignResult) -> str:
    return "\n".join(
        [
            "AeroBeam spar sizing result",
            "===========================",
            f"Material: {result.material.name}",
            f"Load distribution: {result.load_case.distribution}",
            f"Ultimate lift: {_fmt(result.load_case.ultimate_lift_n, 'N')}",
            f"Root shear: {_fmt(result.load_case.root_shear_n, 'N')}",
            f"Root bending moment: {_fmt(result.load_case.root_bending_moment_nm, 'N*m')}",
            "",
            "Geometry",
            "--------",
            f"Width: {_fmt(result.geometry.width_m, 'm')}",
            f"Height: {_fmt(result.geometry.height_m, 'm')}",
            f"Wall thickness: {_fmt(result.geometry.wall_thickness_m, 'm')}",
            f"Section modulus: {_fmt(result.geometry.section_modulus_m3, 'm^3')}",
            f"Mass per meter: {_fmt(result.mass_per_meter_kg_m, 'kg/m')}",
            "",
            "Margins",
            "-------",
            f"Bending stress: {_fmt(result.bending_stress_pa / 1e6, 'MPa')}",
            f"Shear stress: {_fmt(result.shear_stress_pa / 1e6, 'MPa')}",
            f"Bending margin: {result.bending_margin:.3f}",
            f"Shear margin: {result.shear_margin:.3f}",
            f"Controlling margin: {result.controlling_margin:.3f}",
        ]
    )


def _required_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = _required(data, key)
    if not isinstance(value, dict):
        raise TypeError(f"{key!r} must be an object")
    return value


def _required(data: dict[str, Any], key: str) -> Any:
    try:
        return data[key]
    except KeyError as exc:
        raise KeyError(f"missing required field {key!r}") from exc


def _fmt(value: float, unit: str) -> str:
    return f"{value:.6g} {unit}"


if __name__ == "__main__":
    sys.exit(main())
