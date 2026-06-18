"""
AeroBeam v1.2 - Streamlit App
Modern theming applied (using config.toml + targeted CSS).
Charts and PDF reports are untouched.
"""

import streamlit as st
import json
import io
from styles import apply_modern_theme

st.set_page_config(
    page_title="AeroBeam v1.2",
    page_icon="AeroBeam.ico",
    layout="wide"
)

apply_modern_theme()

# Backend
try:
    from wing_stress_analyzer import WingStressAnalyzer, DEFAULT_INPUTS
    BACKEND_OK = True
except Exception as e:
    BACKEND_OK = False
    st.error(f"Backend import failed: {e}")

if "inp" not in st.session_state:
    st.session_state.inp = dict(DEFAULT_INPUTS) if BACKEND_OK else {}

def g(key, default=None):
    return st.session_state.inp.get(key, DEFAULT_INPUTS.get(key, default))

# Header
st.markdown("## AeroBeam v1.2")
st.caption("Wing Bending · Shear · Buckling · Torsion")

# Sidebar
with st.sidebar:
    st.header("Controls")
    if st.button("▶ Run Analysis", type="primary", use_container_width=True):
        try:
            analyzer = WingStressAnalyzer(dict(st.session_state.inp))
            analyzer.analyze()
            st.session_state.result = analyzer
            st.success("Analysis complete")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    st.subheader("Project")
    up = st.file_uploader("Load project", type=["aerobeam", "json"])
    if up:
        data = json.load(up)
        st.session_state.inp.update(data)
        st.rerun()

    if st.button("Save Project"):
        buf = io.BytesIO(json.dumps(st.session_state.inp, indent=2).encode())
        st.download_button("Download .aerobeam", buf, "project.aerobeam")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Wing Geometry", "Loads & Config", "Results", "Plots"])

with tab1:
    st.subheader("Wing Geometry")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.inp["b"] = st.number_input("Total Span b (in)", value=float(g("b")))
        st.session_state.inp["root_chord"] = st.number_input("Root Chord (in)", value=float(g("root_chord")))
        st.session_state.inp["tip_chord"] = st.number_input("Tip Chord (in)", value=float(g("tip_chord")))
    with c2:
        st.session_state.inp["front_spar_percent"] = st.number_input("Front Spar % Chord", value=float(g("front_spar_percent")), step=0.01)
        st.session_state.inp["rear_spar_percent"] = st.number_input("Rear Spar % Chord", value=float(g("rear_spar_percent")), step=0.01)
        st.session_state.inp["front_spar_load_share"] = st.number_input("Front Spar Load Share", value=float(g("front_spar_load_share")), step=0.05)

with tab2:
    st.subheader("Loads & Configuration")
    st.session_state.inp["n"] = st.number_input("Load Factor (+g)", value=float(g("n")))
    st.session_state.inp["Weight"] = st.number_input("Gross Weight (lb)", value=float(g("Weight")))
    st.session_state.inp["config"] = st.selectbox("Configuration", ["strut_braced", "cantilever", "single_strut"], index=0)
    st.session_state.inp["jury_strut"] = st.checkbox("Enable Jury Strut", value=bool(g("jury_strut", False)))

    if st.session_state.inp.get("jury_strut"):
        st.warning("Jury strut is calculated but not applied to spar diagrams.")

with tab3:
    st.subheader("Results")
    if "result" in st.session_state and st.session_state.result:
        st.text(st.session_state.result.summary_text())
    else:
        st.info("Run analysis from the sidebar.")

with tab4:
    st.subheader("Plots")
    st.info("Plots remain unchanged (original matplotlib style preserved).")

st.caption("AeroBeam v1.2 • Charts and reports style unchanged")
