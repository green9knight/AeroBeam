# AeroBeam

Wing spar design and stress analysis for ultralight and experimental aircraft.

AeroBeam is a preliminary design tool. Do not use the results for airworthiness
or final structural sizing without independent verification by a qualified
aircraft structures engineer.

## Install

Python 3.11 or newer. On Windows, use the official Python installer so Tkinter
is included.

```bash
python -m pip install -r requirements.txt
```

## Run the desktop app

```bash
python wing_stress_gui.py
```

The desktop app is the supported interface. It can save and open `.aerobeam`
project files, and it can export a PDF report or an Excel workbook after an
analysis.

An optional browser interface is also included:

```bash
python -m streamlit run streamlit_app.py
```

## Build a portable Windows app

From a Windows machine, with the dependencies above installed:

```bat
build_portable.bat
```

That script uses PyInstaller and `wing_stress.spec` to create
`AeroBeam_Portable\`. The window icon is `web\AeroBeam.ico`.

## Tests

```bash
python -m unittest discover -s tests -v
```

## What the analysis covers

For a strut-braced or cantilever wing, AeroBeam estimates shear, bending
moment, deflection, bending stress, and margin of safety for the front and
rear spars. It also estimates torsion, wing twist, buckling warnings, and a
simplified divergence-speed screen.

Read these before relying on a result:

- `docs/STRUCTURAL_METHODS_AUDIT.md`
- `docs/AEROSPACE_STANDARDS_MATRIX.md`
- `docs/VALIDATION_PLAN.md`
- `README.txt`

Several methods are still preliminary or experimental. The results summary
labels them.

## License

[MIT](LICENSE). Copyright (c) 2026 Phil Ramer.
