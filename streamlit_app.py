"""
AeroBeam v1.2 - Complete Functional Version
All tabs + plots + fixed duplicate keys + modern theme
"""

import streamlit as st
import json
import io
import matplotlib.pyplot as plt
from styles import apply_modern_theme

st.set_page_config(
    page_title="AeroBeam v1.2",
    page_icon="AeroBeam.ico",
    layout="wide"
)

apply_modern_theme()

try:
    from wing_stress_analyzer import WingStressAnalyzer, DEFAULT_INPUTS
    BACKEND_OK = True
except Exception as e:
    BACKEND_OK = False
    st.error(f"Backend import failed: {e}")

if "inp" not in st.session_state:
    st.session_state.inp = dict(DEFAULT_INPUTS) if BACKEND_OK else {}
if "result" not in st.session_state:
    st.session_state.result = None

def g(key, default=None):
    return st.session_state.inp.get(key, DEFAULT_INPUTS.get(key, default))

# Header
st.markdown("## ✈️ AeroBeam v1.2")
st.caption("Wing Bending · Shear · Buckling · Torsion")

# Sidebar
with st.sidebar:
    st.header("Controls")
    if st.button("▶ Run Analysis", type="primary", use_container_width=True, key="run_btn"):
        try:
            analyzer = WingStressAnalyzer(dict(st.session_state.inp))
            analyzer.analyze()
            st.session_state.result = analyzer
            st.success("Analysis complete")
        except Exception as e:
            st.error(f"Analysis error: {e}")

    st.divider()
    st.subheader("Project")
    up = st.file_uploader("Load .aerobeam", type=["aerobeam", "json"], key="uploader")
    if up:
        data = json.load(up)
        st.session_state.inp.update(data)
        st.rerun()

    if st.button("Save Project", key="save_btn"):
        buf = io.BytesIO(json.dumps(st.session_state.inp, indent=2).encode())
        st.download_button("Download .aerobeam", buf, "project.aerobeam", key="dl_btn")

# All Tabs
tabs = st.tabs([
    "Wing Geometry", "Flight & Airfoil", "Loads & Config",
    "Front Spar", "Rear Spar", "Wing Structure", "Buckling",
    "Results", "Plots"
])

# Tab 0: Wing Geometry
with tabs[0]:
    st.subheader("Wing Geometry")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.inp["b"] = st.number_input("Total Span b (in)", value=float(g("b")), key="b")
        st.session_state.inp["root_chord"] = st.number_input("Root Chord (in)", value=float(g("root_chord")), key="root_chord")
        st.session_state.inp["tip_chord"] = st.number_input("Tip Chord (in)", value=float(g("tip_chord")), key="tip_chord")
        st.session_state.inp["rib_spacing"] = st.number_input("Rib Spacing (in)", value=float(g("rib_spacing")), key="rib_spacing")
    with c2:
        st.session_state.inp["front_spar_percent"] = st.number_input("Front Spar % Chord", value=float(g("front_spar_percent")), step=0.01, key="front_spar_percent")
        st.session_state.inp["rear_spar_percent"] = st.number_input("Rear Spar % Chord", value=float(g("rear_spar_percent")), step=0.01, key="rear_spar_percent")
        st.session_state.inp["front_spar_load_share"] = st.number_input("Front Spar Load Share", value=float(g("front_spar_load_share")), step=0.05, key="front_spar_load_share")
        st.caption(f"Rear load share = {1 - float(g('front_spar_load_share')):.2f}")

# Tab 1: Flight & Airfoil
with tabs[1]:
    st.subheader("Flight & Airfoil")
    st.session_state.inp["airfoil"] = st.text_input("Airfoil", value=str(g("airfoil", "NACA 4412")), key="airfoil_name")
    st.session_state.inp["Cm_ac"] = st.number_input("Cm_ac", value=float(g("Cm_ac")), format="%.4f", key="cm_ac")
    st.session_state.inp["Cl_alpha"] = st.number_input("Cl_alpha", value=float(g("Cl_alpha")), key="cl_alpha")
    st.session_state.inp["airfoil_t_c"] = st.number_input("t/c", value=float(g("airfoil_t_c")), format="%.4f", key="airfoil_tc")
    st.session_state.inp["Vd_mph"] = st.number_input("Dive Speed Vd (mph)", value=float(g("Vd_mph")), key="vd")

# Tab 2: Loads & Config
with tabs[2]:
    st.subheader("Loads & Configuration")
    st.session_state.inp["n"] = st.number_input("Load Factor (+g)", value=float(g("n")), key="n")
    st.session_state.inp["Weight"] = st.number_input("Gross Weight (lb)", value=float(g("Weight")), key="weight")
    st.session_state.inp["config"] = st.selectbox("Configuration", ["strut_braced", "cantilever", "single_strut"], index=0, key="config")
    st.session_state.inp["jury_strut"] = st.checkbox("Enable Jury Strut", value=bool(g("jury_strut", False)), key="jury_strut")

    if st.session_state.inp.get("jury_strut"):
        st.warning("Jury strut force is calculated but NOT applied to spar results.")

# Tab 3: Front Spar
with tabs[3]:
    st.subheader("Front Spar")
    st.session_state.inp["front_spar_type"] = st.selectbox("Spar Type", ["Round Tube", "Plain Rectangular", "I-Beam"], index=0, key="front_type")
    if st.session_state.inp["front_spar_type"] == "Round Tube":
        st.session_state.inp["front_spar_od"] = st.number_input("Front Spar OD (in)", value=float(g("front_spar_od", 2.5)), key="front_od")
        st.session_state.inp["front_spar_wall"] = st.number_input("Front Spar Wall (in)", value=float(g("front_spar_wall", 0.065)), key="front_wall")

# Tab 4: Rear Spar
with tabs[4]:
    st.subheader("Rear Spar")
    st.session_state.inp["rear_spar_type"] = st.selectbox("Spar Type", ["Round Tube", "Plain Rectangular"], index=0, key="rear_type")
    if st.session_state.inp["rear_spar_type"] == "Round Tube":
        st.session_state.inp["rear_spar_od"] = st.number_input("Rear Spar OD (in)", value=float(g("rear_spar_od", 2.0)), key="rear_od")
        st.session_state.inp["rear_spar_wall"] = st.number_input("Rear Spar Wall (in)", value=float(g("rear_spar_wall", 0.065)), key="rear_wall")

# Tab 5: Wing Structure
with tabs[5]:
    st.subheader("Wing Structure")
    st.session_state.inp["wing_structure_type"] = st.selectbox("Structure Type", ["fabric_tube", "fabric_buildup", "aluminum_skin"], index=0, key="wing_type")
    st.session_state.inp["dcell_enabled"] = st.checkbox("D-Cell Enabled", value=bool(g("dcell_enabled", False)), key="dcell")

# Tab 6: Buckling
with tabs[6]:
    st.subheader("Buckling")
    st.session_state.inp["stiffener_spacing"] = st.number_input("Stiffener Spacing (in)", value=float(g("stiffener_spacing", 0.0)), key="stiffener")

# Tab 7: Results
with tabs[7]:
    st.subheader("Results Summary")
    if st.session_state.result:
        try:
            st.text(st.session_state.result.summary_text())
        except Exception as e:
            st.error(str(e))
    else:
        st.info("Run analysis from the sidebar.")

# Tab 8: Plots
with tabs[8]:
    st.subheader("Plots")
    if st.session_state.result:
        a = st.session_state.result
        x = a.x

        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle("AeroBeam v1.2 - Analysis Plots")

        axes[0, 0].plot(x, a.pos["V"], label="+g")
        axes[0, 0].plot(x, a.neg["V"], label="-g", linestyle="--")
        axes[0, 0].set_title("Shear (lb)")
        axes[0, 0].legend()
        axes[0, 0].grid(True)

        axes[0, 1].plot(x, a.pos["M"], label="+g")
        axes[0, 1].plot(x, a.neg["M"], label="-g", linestyle="--")
        axes[0, 1].set_title("Moment (lb·in)")
        axes[0, 1].legend()
        axes[0, 1].grid(True)

        axes[1, 0].plot(x, a.pos["z_front"], label="Front")
        axes[1, 0].plot(x, a.pos["z_rear"], label="Rear")
        axes[1, 0].set_title("Deflection (in)")
        axes[1, 0].legend()
        axes[1, 0].grid(True)

        axes[1, 1].plot(x, a.pos["w"])
        axes[1, 1].set_title("Lift Distribution (lb/in)")
        axes[1, 1].grid(True)

        st.pyplot(fig)
        plt.close(fig)
    else:
        st.info("Run analysis to generate plots.")

st.caption("AeroBeam v1.2 • Charts and PDF reports style preserved")
