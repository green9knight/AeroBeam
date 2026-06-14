# AeroBeam
Wing spar design and stress analysis.

## Run the web front end

```bash
python3 -m pip install -r requirements.txt
python3 web_app.py
```

Then open:

```text
http://127.0.0.1:8000
```

The web server uses the existing AeroBeam analyzer and a browser-based UI for
quick inputs, advanced JSON inputs, summary output, and plots.

## Run the desktop GUI

Linux may need Tkinter installed first:

```bash
sudo apt-get install python3-tk
```

Then run:

```bash
python3 wing_stress_gui.py
```
