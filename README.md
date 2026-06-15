# AeroBeam
Wing spar design and stress analysis.

## Engineering status

AeroBeam is currently a beta/preliminary design tool. Do not use results for
airworthiness or final structural sizing without independent verification by a
qualified aircraft structures engineer.

Before relying on a result, read:

- `docs/STRUCTURAL_METHODS_AUDIT.md`
- `docs/VALIDATION_PLAN.md`

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

The web UI can save and load input files:

- **Download Inputs** saves the current setup as `aerobeam-inputs.aerobeam`.
- **Upload Inputs** loads `.aerobeam` or `.json` files and reruns the analysis.

Optional beta password protection:

```bash
AEROBEAM_BETA_PASSWORD=your-password python3 web_app.py
```

## Deploy to Render

This repo includes `render.yaml` for Render Blueprint deployment.

1. Push this branch to GitHub.
2. In Render, choose **New + → Blueprint**.
3. Select the AeroBeam repository and branch.
4. Render will detect `render.yaml`.
5. Set the secret environment variable:

```text
AEROBEAM_BETA_PASSWORD
```

6. Deploy and share the generated Render URL with beta testers.

Render supplies the `PORT` value automatically. The app binds to `0.0.0.0` via
the `HOST` value in `render.yaml`, and `/healthz` is used for health checks.

## Run the desktop GUI

Linux may need Tkinter installed first:

```bash
sudo apt-get install python3-tk
```

Then run:

```bash
python3 wing_stress_gui.py
```
