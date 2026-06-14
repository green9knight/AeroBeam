# AeroBeam

AeroBeam is a small Python toolkit for preliminary wing spar sizing. It estimates
root bending and shear loads, sizes a rectangular hollow box spar, and reports
basic margins and mass per unit span.

The calculations are intended for early trade studies and sanity checks, not for
certification or final structural release. Always validate final designs with
appropriate structural analysis, material allowables, manufacturing constraints,
and test evidence.

## Features

- Elliptical or uniform wing load distributions.
- Limit-load plus safety-factor sizing.
- Built-in materials for common aluminum and composite spar concepts.
- Dependency-free Python API and command line interface.
- Unit tests covering load calculations, spar sizing, and CLI behavior.

## Quick start

Run the example from the repository root:

```bash
python -m aerobeam examples/trainer_wing.json
```

JSON output is also available:

```bash
python -m aerobeam examples/trainer_wing.json --format json
```

## Input format

```json
{
  "aircraft": {
    "mass_kg": 12.5,
    "span_m": 2.4,
    "limit_load_factor": 4.4,
    "safety_factor": 1.5,
    "load_distribution": "elliptical"
  },
  "spar": {
    "width_m": 0.04,
    "height_m": 0.12,
    "min_wall_thickness_m": 0.0008,
    "manufacturing_increment_m": 0.0002
  },
  "material": "6061-T6"
}
```

## Python API

```python
from aerobeam import LoadCase, get_material, size_box_spar

load_case = LoadCase.from_aircraft_mass(
    mass_kg=12.5,
    span_m=2.4,
    limit_load_factor=4.4,
    safety_factor=1.5,
)

result = size_box_spar(
    load_case=load_case,
    material=get_material("6061-T6"),
    width_m=0.04,
    height_m=0.12,
)

print(result.geometry.wall_thickness_m)
print(result.controlling_margin)
```

## Development

Run the test suite with the standard library test runner:

```bash
python -m unittest
```
