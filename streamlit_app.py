"""
AeroBeam v1.2 - Working Version with Libraries
"""

import streamlit as st
import json
import io
import matplotlib.pyplot as plt
from styles import apply_modern_theme

st.set_page_config(page_title="AeroBeam v1.2", page_icon="AeroBeam.ico", layout="wide")
apply_modern_theme()

try:
    from wing_stress_analyzer import WingStressAnalyzer, DEFAULT_INPUTS
    from airfoil_database import AIRFOIL_DB, airfoil_families, get_airfoil
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
            st.error(f"Error: {e}")

    if st.session_state.result:
        if st.button("📄 Generate PDF Report", use_container_width=True, key="pdf_btn"):
            try:
                if hasattr(st.session_state.result, "export_pdf"):
                    pdf_data = st.session_state.result.export_pdf()
                else:
                    st.error("PDF method not found")
                    pdf_data = None
                if pdf_data:
                    st.download_button("⬇ Download PDF", pdf_data, "AeroBeam_Report.pdf", "application/pdf")
            except Exception as e:
                st.error(f"PDF failed: {e}")

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

tabs = st.tabs([
    "Wing Geometry", "Flight & Airfoil", "Loads & Config",
    "Front Spar", "Rear Spar", "Wing Structure", "Buckling",
    "Results", "Plots"
])

# Wing Geometry
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

# Flight & Airfoil (with lookup)
with tabs[1]:
    st.subheader("Flight & Airfoil")
    fams = ["(All)"] + airfoil_families()
    fam = st.selectbox("Family", fams, key="af_fam")
    search = st.text_input("Search airfoil", key="af_search")
    all_names = [k for k in AIRFOIL_DB.keys() if k != "Manual Entry"]
    if fam != "(All)":
        all_names = [n for n in all_names if AIRFOIL_DB.get(n, {}).get("family") == fam]
    if search:
        all_names = [n for n in all_names if search.lower() in n.lower()]
    cur = g("airfoil", "NACA 4412")
    idx = all_names.index(cur) if cur in all_names else 0
    selected = st.selectbox("Airfoil", all_names[:200], index=min(idx, len(all_names)-1), key="af_sel")
    if st.button("Apply Airfoil Data"):
        af = get_airfoil(selected)
        if af:
            st.session_state.inp["airfoil"] = selected
            st.session_state.inp["Cm_ac"] = af.get("Cm_ac", 0.0)
            st.session_state.inp["Cl_alpha"] = af.get("Cl_alpha", 0.0)
            st.session_state.inp["airfoil_t_c"] = af.get("t_c", 0.12)
            st.success(f"Applied {selected}")
            st.rerun()

    st.session_state.inp["Cm_ac"] = st.number_input("Cm_ac", value=float(g("Cm_ac")), format="%.4f", key="cm_ac")
    st.session_state.inp["Cl_alpha"] = st.number_input("Cl_alpha", value=float(g("Cl_alpha")), key="cl_alpha")
    st.session_state.inp["airfoil_t_c"] = st.number_input("t/c", value=float(g("airfoil_t_c")), format="%.4f", key="tc")
    st.session_state.inp["Vd_mph"] = st.number_input("Dive Speed Vd (mph)", value=float(g("Vd_mph")), key="vd")

# Loads & Config
with tabs[2]:
    st.subheader("Loads & Configuration")
    st.session_state.inp["n"] = st.number_input("Load Factor (+g)", value=float(g("n")), key="n")
    st.session_state.inp["Weight"] = st.number_input("Gross Weight (lb)", value=float(g("Weight")), key="weight")
    st.session_state.inp["config"] = st.selectbox("Configuration", ["strut_braced", "cantilever", "single_strut"], index=0, key="config")
    st.session_state.inp["jury_strut"] = st.checkbox("Enable Jury Strut", value=bool(g("jury_strut", False)), key="jury_strut")

# Front Spar (basic tube + angle)
with tabs[3]:
    st.subheader("Front Spar")
    st.session_state.inp["front_spar_type"] = st.selectbox("Spar Type", ["Round Tube", "Plain Rectangular", "I-Beam", "Angle Cap"], index=0, key="front_type")
    if st.session_state.inp["front_spar_type"] == "Round Tube":
        st.session_state.inp["front_spar_od"] = st.number_input("OD (in)", value=float(g("front_spar_od", 2.5)), key="front_od")
        st.session_state.inp["front_spar_wall"] = st.number_input("Wall (in)", value=float(g("front_spar_wall", 0.065)), key="front_wall")
    elif st.session_state.inp["front_spar_type"] == "Angle Cap":
        st.session_state.inp["front_angle_size"] = st.text_input("Angle Size (e.g. 1x1x1/8)", value=g("front_angle_size", "1x1x1/8"), key="front_angle")

# Rear Spar
with tabs[4]:
    st.subheader("Rear Spar")
    st.session_state.inp["rear_spar_type"] = st.selectbox("Spar Type", ["Round Tube", "Plain Rectangular", "Angle Cap"], index=0, key="rear_type")
    if st.session_state.inp["rear_spar_type"] == "Round Tube":
        st.session_state.inp["rear_spar_od"] = st.number_input("OD (in)", value=float(g("rear_spar_od", 2.0)), key="rear_od")
        st.session_state.inp["rear_spar_wall"] = st.number_input("Wall (in)", value=float(g("rear_spar_wall", 0.065)), key="rear_wall")
    elif st.session_state.inp["rear_spar_type"] == "Angle Cap":
        st.session_state.inp["rear_angle_size"] = st.text_input("Angle Size", value=g("rear_angle_size", "1x1x1/8"), key="rear_angle")

# Wing Structure
with tabs[5]:
    st.subheader("Wing Structure")
    st.session_state.inp["wing_structure_type"] = st.selectbox("Structure Type", ["fabric_tube", "fabric_buildup", "aluminum_skin"], index=0, key="wing_type")
    st.session_state.inp["dcell_enabled"] = st.checkbox("D-Cell Enabled", value=bool(g("dcell_enabled", False)), key="dcell")

# Buckling
with tabs[6]:
    st.subheader("Buckling")
    st.session_state.inp["stiffener_spacing"] = st.number_input("Stiffener Spacing (in)", value=float(g("stiffener_spacing", 0.0)), key="stiffener")

# Results
with tabs[7]:
    st.subheader("Results Summary")
    if st.session_state.result:
        try:
            st.text(st.session_state.result.summary_text())
        except Exception as e:
            st.error(str(e))
    else:
        st.info("Run analysis from the sidebar.")

# Plots
with tabs[8]:
    st.subheader("Plots")
    if st.session_state.result:
        a = st.session_state.result
        x = a.x
        fig = plt.figure(figsize=(16, 14))

        ax1 = fig.add_subplot(3, 2, 1)
        ax1.plot(x, a.pos.get("w", []))
        ax1.set_title("Lift Distribution (lb/in)")
        ax1.grid(True, alpha=0.3)

        ax2 = fig.add_subplot(3, 2, 2)
        ax2.plot(x, a.pos.get("V", []), label="+g")
        ax2.plot(x, a.neg.get("V", []), label="-g", linestyle="--")
        ax2.set_title("Shear (lb)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        ax3 = fig.add_subplot(3, 2, 3)
        ax3.plot(x, a.pos.get("z_front", []), label="Front")
        ax3.plot(x, a.pos.get("z_rear", []), label="Rear")
        ax3.set_title("Deflection (in)")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        ax4 = fig.add_subplot(3, 2, 4)
        ax4.plot(x, a.pos.get("M", []), label="+g")
        ax4.plot(x, a.neg.get("M", []), label="-g", linestyle="--")
        ax4.set_title("Moment (lb·in)")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        try:
            ax5 = fig.add_subplot(3, 2, 5)
            a.draw_geometry(ax5, ax5)
            ax5.set_title("Wing Geometry - Front View")

            ax6 = fig.add_subplot(3, 2, 6)
            a.draw_geometry(ax6, ax6)
            ax6.set_title("Wing Geometry - Top View")
        except:
            pass

        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.info("Run analysis to see plots.")

st.caption("AeroBeam v1.2 • Working version")
