# AGENTS.md

## Cursor Cloud specific instructions

AeroBeam is a single desktop GUI application: a Python 3 + Tkinter wing
bending/stress analyzer. There is no backend/server, no database, and no test
suite or linter configured in this repo.

### Services / how to run

- Run the app (development mode): `DISPLAY=:1 python3 wing_stress_gui.py`
  (a VNC X display is available at `:1`). It is a GUI app, so it needs a display.
- The physics engine can be exercised headlessly without a display:
  set `matplotlib.use("Agg")`, then
  `from wing_stress_analyzer import WingStressAnalyzer; WingStressAnalyzer().analyze()`.
  PDF/Excel export work the same way via `export_pdf(path)` / `export_excel(path)`.

### Dependencies

- Python deps (`numpy`, `matplotlib`, `openpyxl`, `xlsxwriter`) are refreshed by
  the startup update script; see `requirements.txt`.
- `python3-tk` (Tkinter) is a **system** package, not pip-installable. It is
  provided by the VM snapshot, not the update script. If `import tkinter` fails,
  install it with `sudo apt-get install -y python3-tk`.

### Known caveats

- Startup TclError is expected and harmless on Linux: the GUI calls
  `self.root.state("zoomed")` (a Windows-only window state), which raises a
  non-fatal `_tkinter.TclError: bad argument "zoomed"` in an `after` callback.
  The window still opens normally; just maximize it manually if needed.
- The PyInstaller build (`build_portable.bat` + `wing_stress.spec`) targets
  Windows `.exe` only and is not used for Linux development.
- No automated tests or lint config exist; "build/run" in dev mode just means
  running the GUI (or the engine headlessly as above).
