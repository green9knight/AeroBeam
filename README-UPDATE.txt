AeroBeam GUI Update - June 2026

This zip contains the updated desktop GUI that now uses the **same input validation and error handling logic** as the web version.

Files included:
- wing_stress_gui.py   ← Updated (main change)
- input_validation.py  ← Shared validation module (new dependency for the GUI)

Changes made:
- Added import and usage of validate_inputs()
- Critical validation errors now show clean user-friendly messages
- Non-critical warnings are logged to console
- All other errors use sanitize_error_message() (same as web_app.py)
- Validation runs before creating WingStressAnalyzer (consistent with web backend)

How to use:
1. Replace your current wing_stress_gui.py with the one in this zip
2. Place input_validation.py in the same folder as wing_stress_gui.py
3. Rebuild your .exe using your normal PyInstaller / build script

The web version (web_app.py) was left completely unchanged.
