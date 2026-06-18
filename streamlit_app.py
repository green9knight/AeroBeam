"""
AeroBeam v1.2 - Fully Functional with Plots
"""

import streamlit as st
import json
import io
import matplotlib.pyplot as plt
from styles import apply_modern_theme

st.set_page_config(
    page_title="AeroBeam v1.2",
    page_icon="AeroBeam.ico",   # Make sure AeroBeam.ico is in the same folder
    layout="wide"
)

apply_modern_theme()

try:
    from wing_stress_analyzer import WingStressAnalyzer, DEFAULT_INPUTS
    BACKEND_OK = True
except Exception as e:
    BACKEND_OK = False
    st.error(f"Backend failed: {e}")

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
    up = st.file_uploader("Load .aerobeam", type=["aerobeam", "json"])
    if up:
        data = json.load(up)
        st.session_state.inp.update(data)
        st.rerun()

    if st.button("Save Project"):
        buf = io.BytesIO(json.dumps(st.session_state.inp, indent=2).encode())
        st.download_button("Download .aerobeam", buf, "project.aerobeam")

# Tabs
tabs = st.tabs([
    "Wing Geometry", "Flight & Airfoil", "Loads & Config",
    "Front Spar", "Rear Spar", "Wing Structure", "Buckling",
    "Results", "Plots"
])

# ... (keep all previous tabs the same - Wing Geometry, Loads, Spars, etc.)

# === Results Tab ===
with tabs[7]:
    st.subheader("Results Summary")
    if st.session_state.result:
        try:
            st.text(st.session_state.result.summary_text())
        except Exception as e:
            st.error(f"Could not show summary: {e}")
    else:
        st.info("Run analysis from the sidebar.")

# === Plots Tab (FIXED) ===
with tabs[8]:
    st.subheader("Plots")
    
    if st.session_state.result:
        a = st.session_state.result
        x = a.x

        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle("AeroBeam Analysis Plots", fontsize=14)

        # Shear
        axes[0, 0].plot(x, a.pos["V"], label="+g")
        axes[0, 0].plot(x, a.neg["V"], label="-g", linestyle="--")
        axes[0, 0].set_title("Shear (lb)")
        axes[0, 0].legend()
        axes[0, 0].grid(True)

        # Moment
        axes[0, 1].plot(x, a.pos["M"], label="+g")
        axes[0, 1].plot(x, a.neg["M"], label="-g", linestyle="--")
        axes[0, 1].set_title("Moment (lb·in)")
        axes[0, 1].legend()
        axes[0, 1].grid(True)

        # Deflection
        axes[1, 0].plot(x, a.pos["z_front"], label="Front +g")
        axes[1, 0].plot(x, a.pos["z_rear"], label="Rear +g")
        axes[1, 0].set_title("Deflection (in)")
        axes[1, 0].legend()
        axes[1, 0].grid(True)

        # Lift
        axes[1, 1].plot(x, a.pos["w"], label="Lift")
        axes[1, 1].set_title("Lift Distribution (lb/in)")
        axes[1, 1].legend()
        axes[1, 1].grid(True)

        st.pyplot(fig)
        plt.close(fig)
    else:
        st.info("Run analysis to see plots.")
