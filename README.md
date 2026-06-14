# AeroBeam
Wing spar design and stress analysis.

## Run the GUI

Install the Python runtime dependencies:

```bash
python3 -m pip install -r requirements.txt
```

On Linux, install Tkinter if your Python distribution does not include it:

```bash
sudo apt-get install python3-tk
```

Start AeroBeam:

```bash
python3 wing_stress_gui.py
```

## Smoke test

From the repository root:

```bash
python3 -m py_compile wing_stress_gui.py wing_stress_analyzer.py spar_sections.py airfoil_database.py common_tube_spars.py
python3 - <<'PY'
import tkinter
import wing_stress_gui
print("AeroBeam GUI imports OK")
PY
```

## Build a portable Windows app

On Windows, run:

```bat
build_portable.bat
```
