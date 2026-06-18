"""
AeroBeam v1.2 — Streamlit Web App (Themed)
Includes Anthropic-style UI + number inputs + jury warning.
"""

import streamlit as st
import numpy as np
import json, io, math
from styles import apply_anthropic_theme

st.set_page_config(
    page_title="AeroBeam v1.2",
    page_icon="AeroBeam.ico",
    layout="wide"
)

apply_anthropic_theme()

# Backend imports (assumed to be in same folder or path)
try:
    from wing_stress_analyzer import WingStressAnalyzer, DEFAULT_INPUTS, dynamic_pressure_psi
    BACKEND_OK = True
except ImportError as e:
    BACKEND_OK = False
    IMPORT_ERR = str(e)

if "inp" not in st.session_state:
    st.session_state.inp = dict(DEFAULT_INPUTS) if BACKEND_OK else {}
if "result" not in st.session_state:
    st.session_state.result = None

def g(key, default=None):
    return st.session_state.inp.get(key, DEFAULT_INPUTS.get(key, default))

# Header with branding
st.markdown(
    '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
    '<img src="AeroBeam.ico" width="28">'
    '<span style="font-size:1.5rem;font-weight:600;">AeroBeam</span>'
    '<span style="color:#888;font-size:0.95rem;">v1.2</span>'
    '</div>',
    unsafe_allow_html=True
)

if not BACKEND_OK:
    st.error(f"Backend import failed: {IMPORT_ERR}")
    st.stop()

# Sidebar
with st.sidebar:
    st.header("Controls")
    run = st.button("▶ Run Analysis", type="primary", use_container_width=True)
    st.divider()

    st.subheader("Project File")
    up = st.file_uploader("Load .aerobeam", type=["aerobeam","json"])
    if up:
        data = json.load(up)
        merged = dict(DEFAULT_INPUTS)
        for k, v in data.items():
            merged[k] = v
        st.session_state.inp = merged
        st.success(f"Loaded {up.name}")
        st.rerun()

    if st.button("Save Project"):
        data = dict(st.session_state.inp)
        buf = io.BytesIO(json.dumps(data, indent=2).encode())
        st.download_button("Download .aerobeam", buf, "project.aerobeam")

# Tabs
tabs = st.tabs(["Wing Geometry", "Loads & Config", "Results", "Plots"])

with tabs[0]:
    st.subheader("Wing Geometry")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.inp["b"] = st.number_input("Span b (in)", value=float(g("b")))
        st.session_state.inp["root_chord"] = st.number_input("Root Chord", value=float(g("root_chord")))
        st.session_state.inp["tip_chord"] = st.number_input("Tip Chord", value=float(g("tip_chord")))
    with c2:
        st.session_state.inp["front_spar_percent"] = st.number_input("Front Spar %", value=float(g("front_spar_percent")), step=0.01)
        st.session_state.inp["rear_spar_percent"] = st.number_input("Rear Spar %", value=float(g("rear_spar_percent")), step=0.01)
        st.session_state.inp["front_spar_load_share"] = st.number_input("Front Load Share", value=float(g("front_spar_load_share")), step=0.05)

with tabs[1]:
    st.subheader("Loads & Config")
    st.session_state.inp["n"] = st.number_input("Load Factor n", value=float(g("n")))
    st.session_state.inp["Weight"] = st.number_input("Gross Weight", value=float(g("Weight")))
    st.session_state.inp["config"] = st.selectbox("Config", ["strut_braced", "cantilever"], index=0)
    st.session_state.inp["jury_strut"] = st.checkbox("Jury Strut", value=bool(g("jury_strut", False)))

    if st.session_state.inp["jury_strut"]:
        st.warning("Jury strut force is calculated but NOT applied to spar diagrams.")

with tabs[2]:
    st.subheader("Results")
    if st.session_state.result:
        st.text(st.session_state.result)
    else:
        st.info("Run analysis first")

with tabs[3]:
    st.subheader("Plots")
    st.info("Plots remain unchanged from original version.")

if run:
    try:
        a = WingStressAnalyzer(dict(st.session_state.inp))
        a.analyze()
        st.session_state.result = a.summary_text()
        st.success("Analysis complete")
    except Exception as e:
        st.error(str(e))
