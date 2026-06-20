"""
AeroBeam v1.2 - Full Version
Includes custom filename for PDF reports
"""

import streamlit as st
import json
import io
import matplotlib.pyplot as plt
import tempfile
import os
from styles import apply_modern_theme

try:
    from PIL import Image as _PIL_Image
    _ico = _PIL_Image.open("AeroBeam.ico").convert("RGBA")
    _favicon = _ico
except Exception:
    _ico = None
    _favicon = "✈️"

st.set_page_config(page_title="AeroBeam v1.2", page_icon=_favicon, layout="wide")
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

# Header with logo — base64 inline avoids Streamlit column clipping
if _ico:
    import base64 as _b64mod, io as _bio
    _buf = _bio.BytesIO()
    _ico.save(_buf, format="PNG")
    _b64 = _b64mod.b64encode(_buf.getvalue()).decode()
    st.markdown(
        f'''<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px">
        <img src="data:image/png;base64,{_b64}"
             style="height:56px;width:auto;flex-shrink:0;vertical-align:middle"/>
        <div>
            <div style="font-size:1.6rem;font-weight:700;line-height:1.2">AeroBeam v1.2</div>
            <div style="font-size:0.85rem;color:#888;margin-top:2px">Wing Bending · Shear · Buckling · Torsion</div>
        </div></div>''',
        unsafe_allow_html=True
    )
else:
    st.markdown("## ✈️ AeroBeam v1.2")
    st.caption("Wing Bending · Shear · Buckling · Torsion")

# Sidebar
with st.sidebar:
    # Sidebar logo — same base64 approach, no clipping
    if _ico:
        import base64 as _b64mod2, io as _bio2
        _buf2 = _bio2.BytesIO()
        _ico.save(_buf2, format="PNG")
        _b64_2 = _b64mod2.b64encode(_buf2.getvalue()).decode()
        st.markdown(
            f'''<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
            <img src="data:image/png;base64,{_b64_2}"
                 style="height:42px;width:auto;flex-shrink:0"/>
            <span style="font-weight:700;font-size:1rem">AeroBeam v1.2</span>
            </div>''',
            unsafe_allow_html=True
        )
        st.divider()
    else:
        st.header("Controls")

    if st.button("▶ Run Analysis", type="primary", use_container_width=True, key="run_btn"):
        try:
            analyzer = WingStressAnalyzer(dict(st.session_state.inp))
            analyzer.analyze()
            st.session_state.result = analyzer
            st.success("Analysis complete")
        except Exception as e:
            st.error(f"Analysis error: {e}")

    # === PDF Report with Custom Filename ===
    if st.session_state.result:
        st.divider()
        st.subheader("PDF Report")

        default_name = "AeroBeam_Report.pdf"
        custom_name = st.text_input("Filename", value=default_name, key="pdf_name")

        if st.button("📄 Generate PDF Report", use_container_width=True, key="pdf_btn"):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    temp_path = tmp.name

                st.session_state.result.export_pdf(path=temp_path)

                with open(temp_path, "rb") as f:
                    pdf_bytes = f.read()

                os.unlink(temp_path)

                if not custom_name.lower().endswith(".pdf"):
                    custom_name += ".pdf"

                st.download_button(
                    label=f"⬇ Download {custom_name}",
                    data=pdf_bytes,
                    file_name=custom_name,
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")

    st.divider()
    st.subheader("Project")
    up = st.file_uploader("Load .aerobeam", type=["aerobeam", "json"], key="uploader")
    if up:
        raw = json.load(up)
        # Merge: file wins for keys it contains, defaults fill new keys
        merged = dict(DEFAULT_INPUTS)
        bool_keys = {"dcell_enabled","geodetic_enabled","distribute_wing_weight",
                     "secondary_bending","jury_strut","ng_lift_manual","dist_wing_weight"}
        for k, v in raw.items():
            if k in bool_keys:
                merged[k] = str(v).lower() in ("1","true","yes")
            elif isinstance(v, str):
                try:    merged[k] = float(v) if v.strip() else merged.get(k, v)
                except: merged[k] = v
            else:
                merged[k] = v
        # Normalize load share
        lsf = merged.get("front_spar_load_share", 0.55)
        if isinstance(lsf, (int,float)) and lsf > 1.0:
            merged["front_spar_load_share"] = lsf / 100.0
        st.session_state.inp = merged
        st.success(f"Loaded: {up.name}")
        st.rerun()

    if st.button("💾 Save Project", key="save_btn"):
        buf = io.BytesIO(json.dumps(st.session_state.inp, indent=2, default=str).encode())
        st.download_button("⬇ Download .aerobeam", buf, "project.aerobeam",
                           mime="application/json", key="download_btn")

# Tabs
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

# Flight & Airfoil
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
    all_names = all_names[:300]
    if len(all_names) == 0:
        st.warning("No airfoils found.")
        selected = g("airfoil", "NACA 4412")
    else:
        cur = g("airfoil", "NACA 4412")
        idx = all_names.index(cur) if cur in all_names else 0
        selected = st.selectbox("Airfoil", all_names, index=idx, key="af_sel")
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

# Front Spar
with tabs[3]:
    st.subheader("Front Spar")
    spar_type = st.selectbox("Spar Type", ["Round Tube", "Plain Rectangular", "I-Beam", "Angle Cap"], index=0, key="front_type")
    st.session_state.inp["front_spar_type"] = spar_type
    if spar_type == "Round Tube":
        from common_tube_spars import COMMON_TUBE_SIZES, list_tube_descriptions
        _tl = list_tube_descriptions()
        _co = float(g("front_spar_od", 2.5))
        _cw = float(g("front_spar_wall", 0.065))
        _ci = next((i for i,t in enumerate(COMMON_TUBE_SIZES) if abs(t.od-_co)<0.001 and abs(t.wall-_cw)<0.001), 0)
        _fs = st.selectbox("Front Spar Tube", _tl, index=_ci, key="front_tube")
        _ft = COMMON_TUBE_SIZES[_tl.index(_fs)]
        st.session_state.inp["front_spar_od"] = _ft.od
        st.session_state.inp["front_spar_wall"] = _ft.wall
        st.session_state.inp["front_spar_mat"] = "6061-T6"
        st.caption(str(_ft))
    elif spar_type == "Angle Cap":
        angle_options = ["1/2 x 1/2 x 1/16", "3/4 x 3/4 x 1/16", "3/4 x 3/4 x 3/32", "3/4 x 3/4 x 1/8",
                         "1 x 1 x 1/16", "1 x 1 x 3/32", "1 x 1 x 1/8", "1 x 1 x 3/16",
                         "1-1/4 x 1-1/4 x 1/16", "1-1/4 x 1-1/4 x 3/32", "1-1/4 x 1-1/4 x 1/8",
                         "1-1/2 x 1-1/2 x 1/16", "1-1/2 x 1-1/2 x 3/32", "1-1/2 x 1-1/2 x 1/8",
                         "2 x 2 x 1/8", "2 x 2 x 3/16", "2-1/2 x 2-1/2 x 1/8", "3 x 3 x 1/8"]
        selected = st.selectbox("Aluminum Angle Size", angle_options, key="front_angle")
        st.session_state.inp["front_angle_size"] = selected

# Rear Spar
with tabs[4]:
    st.subheader("Rear Spar")
    spar_type = st.selectbox("Spar Type", ["Round Tube", "Plain Rectangular", "Angle Cap"], index=0, key="rear_type")
    st.session_state.inp["rear_spar_type"] = spar_type
    if spar_type == "Round Tube":
        from common_tube_spars import COMMON_TUBE_SIZES, list_tube_descriptions
        _tlr = list_tube_descriptions()
        _cor = float(g("rear_spar_od", 2.5))
        _cwr = float(g("rear_spar_wall", 0.065))
        _cir = next((i for i,t in enumerate(COMMON_TUBE_SIZES) if abs(t.od-_cor)<0.001 and abs(t.wall-_cwr)<0.001), 0)
        _rs = st.selectbox("Rear Spar Tube", _tlr, index=_cir, key="rear_tube")
        _rt = COMMON_TUBE_SIZES[_tlr.index(_rs)]
        st.session_state.inp["rear_spar_od"] = _rt.od
        st.session_state.inp["rear_spar_wall"] = _rt.wall
        st.session_state.inp["rear_spar_mat"] = "6061-T6"
        st.caption(str(_rt))
    elif spar_type == "Angle Cap":
        angle_options = ["1/2 x 1/2 x 1/16", "3/4 x 3/4 x 1/16", "3/4 x 3/4 x 3/32", "3/4 x 3/4 x 1/8",
                         "1 x 1 x 1/16", "1 x 1 x 3/32", "1 x 1 x 1/8", "1 x 1 x 3/16",
                         "1-1/4 x 1-1/4 x 1/16", "1-1/4 x 1-1/4 x 3/32", "1-1/4 x 1-1/4 x 1/8",
                         "1-1/2 x 1-1/2 x 1/16", "1-1/2 x 1-1/2 x 3/32", "1-1/2 x 1-1/2 x 1/8",
                         "2 x 2 x 1/8", "2 x 2 x 3/16", "2-1/2 x 2-1/2 x 1/8", "3 x 3 x 1/8"]
        selected = st.selectbox("Aluminum Angle Size", angle_options, key="rear_angle")
        st.session_state.inp["rear_angle_size"] = selected

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

st.caption("AeroBeam v1.2 • Custom PDF filename supported")
