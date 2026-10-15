"""
AeroBeam v1.2.3 - Full Version
Includes custom filename for PDF reports
"""

import streamlit as st
import json
import io
import matplotlib.pyplot as plt
import tempfile
import os
from input_validation import ValidationError, validate_inputs
from styles import apply_modern_theme

_ico = None
_favicon = "✈️"
try:
    from PIL import Image as _PIL_Image
    for _icon_path in ("AeroBeam.ico", os.path.join("web", "AeroBeam.ico")):
        if os.path.isfile(_icon_path):
            _ico = _PIL_Image.open(_icon_path).convert("RGBA")
            _favicon = _ico
            break
except Exception:
    _ico = None
    _favicon = "✈️"

st.set_page_config(page_title="AeroBeam v1.2.3", page_icon=_favicon, layout="wide")
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
             style="height:44px;width:auto;flex-shrink:0;object-fit:contain"/>
        <div>
            <div style="font-size:1.6rem;font-weight:700;line-height:1.2">AeroBeam v1.2.3</div>
            <div style="font-size:0.85rem;color:#888;margin-top:2px">Wing Bending · Shear · Buckling · Torsion</div>
        </div></div>''',
        unsafe_allow_html=True
    )
else:
    st.markdown("## ✈️ AeroBeam v1.2.3")
    st.caption("Wing Bending · Shear · Buckling · Torsion")

st.caption(
    "Preliminary design only. Not for airworthiness or final sizing. "
    "MIT License — Copyright (c) 2026 Phil Ramer."
)

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
            <span style="font-weight:700;font-size:1rem">AeroBeam v1.2.3</span>
            </div>''',
            unsafe_allow_html=True
        )
        st.divider()
    else:
        st.header("Controls")

    if st.button("▶ Run Analysis", type="primary", use_container_width=True, key="run_btn"):
        with st.spinner("Analysing..."):
            try:
                import traceback as _tb
                # Take a snapshot of inp at click time - this is what gets analysed
                _inp = dict(st.session_state.inp)
                from wing_stress_analyzer import _sanitize_spar_inputs
                _inp = _sanitize_spar_inputs(_inp, "front_spar")
                _inp = _sanitize_spar_inputs(_inp, "rear_spar")
                # Store the sanitized snapshot so results match what was run
                st.session_state.last_run_inp = dict(_inp)
                _inp, _warnings = validate_inputs(_inp)
                analyzer = WingStressAnalyzer(_inp)
                analyzer.validation_warnings = _warnings
                analyzer.analyze()
                st.session_state.result = analyzer
                if analyzer.validation_warnings:
                    st.warning(
                        "\n".join(item.message for item in analyzer.validation_warnings)
                    )
                st.success("Analysis complete")
            except ValidationError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Analysis error: {e}")
                st.code(_tb.format_exc())

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
    up = st.file_uploader("Load .aerobeam", type=["aerobeam","json"], key="uploader")
    if up is not None and st.session_state.get("_last_uploaded") != up.name:
        try:
            raw = json.load(up)
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
            lsf = merged.get("front_spar_load_share", 0.55)
            if isinstance(lsf, (int,float)) and lsf > 1.0:
                merged["front_spar_load_share"] = lsf / 100.0
            st.session_state.inp = merged
            st.session_state._last_uploaded = up.name
            st.session_state.result = None
            st.success(f"Loaded: {up.name} — click Run Analysis")
        except Exception as e:
            st.error(f"Load failed: {e}")
        st.rerun()

    if st.button("💾 Save Project", key="save_btn"):
        buf = io.BytesIO(json.dumps(st.session_state.inp, indent=2, default=str).encode())
        st.download_button("⬇ Download .aerobeam", buf, "project.aerobeam",
                           mime="application/json", key="download_btn")

# Tabs
tabs = st.tabs([
    "Wing Geometry", "Flight & Airfoil", "Loads & Config", "Wing Structure",
    "Front Spar", "Rear Spar", "Buckling",
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
        _taper_refs = ["Leading edge", "Main spar", "Trailing edge"]
        _taper_cur = g("taper_reference", "Leading edge")
        st.session_state.inp["taper_reference"] = st.selectbox(
            "Keep straight when the chord tapers", _taper_refs,
            index=_taper_refs.index(_taper_cur) if _taper_cur in _taper_refs else 0,
            key="taper_reference")
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
            st.session_state["tc"] = float(af.get("t_c", 0.12) or 0.12) * 100.0
            st.success(f"Applied {selected}")
            st.rerun()
    st.session_state.inp["Cm_ac"] = st.number_input("Cm_ac", value=float(g("Cm_ac")), format="%.4f", key="cm_ac")
    st.session_state.inp["Cl_alpha"] = st.number_input("Cl_alpha", value=float(g("Cl_alpha")), key="cl_alpha")
    _tc_stored = float(g("airfoil_t_c", 0.15))
    _tc_shown = _tc_stored * 100.0 if abs(_tc_stored) <= 1.0 else _tc_stored
    _tc_pct = st.number_input("Thickness %", value=_tc_shown, format="%.2f", key="tc")
    from wing_stress_analyzer import parse_fraction
    st.session_state.inp["airfoil_t_c"] = parse_fraction(_tc_pct, 0.15)
    st.session_state.inp["Vd_mph"] = st.number_input("Dive Speed Vd (mph)", value=float(g("Vd_mph")), key="vd")

# Loads & Config
with tabs[2]:
    st.subheader("Loads & Configuration")
    _configs = ["strut_braced", "cantilever", "single_strut"]
    _cfg = g("config", "strut_braced")
    st.session_state.inp["config"] = st.selectbox(
        "Configuration", _configs,
        index=_configs.index(_cfg) if _cfg in _configs else 0,
        key="config",
    )
    if st.session_state.inp["config"] != "cantilever":
        st.session_state.inp["jury_strut"] = st.checkbox(
            "Enable Jury Strut", value=bool(g("jury_strut", False)), key="jury_strut")
    else:
        st.session_state.inp["jury_strut"] = False
    st.session_state.inp["n"] = st.number_input("Load Factor (+g)", value=float(g("n")), key="n")
    st.session_state.inp["Weight"] = st.number_input("Gross Weight (lb)", value=float(g("Weight")), key="weight")


# Front Spar
with tabs[4]:
    st.subheader("Front Spar")

    try:
        from spar_sections import MATERIAL_DB
        _ALL_MATS  = list(MATERIAL_DB.keys())
        _WOOD_MATS = [k for k,v in MATERIAL_DB.items() if v.get("is_wood")]
        _METAL_MATS= [k for k,v in MATERIAL_DB.items() if not v.get("is_wood")]
    except:
        _ALL_MATS = _WOOD_MATS = _METAL_MATS = ["6061-T6","2024-T3","Sitka Spruce","Birch Plywood"]

    _SPAR_TYPES = ["Round Tube","Plain Rectangular","I-Beam","C-Channel",
                   "Double I-Beam","Box Spar","Aluminum I-Beam","Aluminum C-Spar"]
    _fst = st.selectbox("Spar Type", _SPAR_TYPES,
        index=_SPAR_TYPES.index(g("front_spar_type","Round Tube"))
              if g("front_spar_type","Round Tube") in _SPAR_TYPES else 0,
        key="front_type")
    st.session_state.inp["front_spar_type"] = _fst

    if _fst == "Round Tube":
        from common_tube_spars import COMMON_TUBE_SIZES, list_tube_descriptions
        _tl = list_tube_descriptions()
        _co = float(g("front_spar_od", 2.5))
        _cw = float(g("front_spar_wall", 0.065))
        _ci = next((i for i,t in enumerate(COMMON_TUBE_SIZES)
                    if abs(t.od-_co)<0.001 and abs(t.wall-_cw)<0.001), 0)
        def _on_front_tube():
            _sel = st.session_state["front_tube"]
            _t   = COMMON_TUBE_SIZES[list_tube_descriptions().index(_sel)]
            st.session_state.inp["front_spar_od"]   = _t.od
            st.session_state.inp["front_spar_wall"] = _t.wall
            st.session_state.inp["front_spar_mat"]  = "6061-T6"
        _fs = st.selectbox("Front Spar Tube", _tl, index=_ci,
                           key="front_tube", on_change=_on_front_tube)
        _ft = COMMON_TUBE_SIZES[_tl.index(_fs)]
        # Only set if not already matching (prevents overwrite on rerun)
        if abs(st.session_state.inp.get("front_spar_od",0) - _ft.od) > 0.001:
            st.session_state.inp["front_spar_od"]   = _ft.od
            st.session_state.inp["front_spar_wall"] = _ft.wall
            st.session_state.inp["front_spar_mat"]  = "6061-T6"
        st.caption(str(_ft))

    elif _fst == "Plain Rectangular":
        st.session_state.inp["front_spar_width"]   = st.number_input("Width (in)", value=float(g("front_spar_width",2.0)), format="%.3f", key="f_w")
        st.session_state.inp["front_spar_height"]  = st.number_input("Height (in)", value=float(g("front_spar_height",4.0)), format="%.3f", key="f_h")
        _def_cm = g("front_spar_cap_mat","Sitka Spruce")
        _cm_idx = _ALL_MATS.index(_def_cm) if _def_cm in _ALL_MATS else 0
        st.session_state.inp["front_spar_cap_mat"] = st.selectbox("Material", _ALL_MATS, index=_cm_idx, key="f_cm")

    elif _fst in ("I-Beam","C-Channel","Double I-Beam"):
        c1f, c2f = st.columns(2)
        with c1f:
            st.session_state.inp["front_spar_b_top"] = st.number_input("Root cap width top (in)", value=float(g("front_spar_b_top",1.5)), format="%.3f", key="f_bt")
            st.session_state.inp["front_spar_t_top"] = st.number_input("Root cap height top (in)", value=float(g("front_spar_t_top",0.75)), format="%.4f", key="f_tt")
            st.session_state.inp["front_spar_b_bot"] = st.number_input("Root cap width bottom (in)", value=float(g("front_spar_b_bot",1.5)), format="%.3f", key="f_bb")
            st.session_state.inp["front_spar_t_bot"] = st.number_input("Root cap height bottom (in)", value=float(g("front_spar_t_bot",0.75)), format="%.4f", key="f_tb")
            st.session_state.inp["front_spar_b_top_tip"] = st.number_input("Tip cap width top (in)", value=float(g("front_spar_b_top_tip", g("front_spar_b_top",1.5))), format="%.3f", key="f_btt")
            st.session_state.inp["front_spar_t_top_tip"] = st.number_input("Tip cap height top (in)", value=float(g("front_spar_t_top_tip", g("front_spar_t_top",0.75))), format="%.4f", key="f_ttt")
            st.session_state.inp["front_spar_b_bot_tip"] = st.number_input("Tip cap width bottom (in)", value=float(g("front_spar_b_bot_tip", g("front_spar_b_bot",1.5))), format="%.3f", key="f_bbt")
            st.session_state.inp["front_spar_t_bot_tip"] = st.number_input("Tip cap height bottom (in)", value=float(g("front_spar_t_bot_tip", g("front_spar_t_bot",0.75))), format="%.4f", key="f_tbt")
        with c2f:
            st.session_state.inp["front_spar_h_web"] = st.number_input("Web Height (in)", value=float(g("front_spar_h_web",4.5)), format="%.3f", key="f_hw")
            st.session_state.inp["front_spar_t_web"] = st.number_input("Web Thickness (in)", value=float(g("front_spar_t_web",0.125)), format="%.4f", key="f_tw")
            if _fst == "Double I-Beam":
                st.session_state.inp["front_spar_web_spacing"] = st.number_input("Web Spacing (in)", value=float(g("front_spar_web_spacing",1.0)), format="%.3f", key="f_ws")
            _def_cm = g("front_spar_cap_mat","Sitka Spruce")
            _cm_idx = _ALL_MATS.index(_def_cm) if _def_cm in _ALL_MATS else 0
            st.session_state.inp["front_spar_cap_mat"] = st.selectbox("Cap Material", _ALL_MATS, index=_cm_idx, key="f_cm")
            _def_wm = g("front_spar_web_mat","Birch Plywood")
            _wm_idx = _ALL_MATS.index(_def_wm) if _def_wm in _ALL_MATS else 0
            st.session_state.inp["front_spar_web_mat"] = st.selectbox("Web Material", _ALL_MATS, index=_wm_idx, key="f_wm")
        total_h = float(g("front_spar_h_web",4.5))+float(g("front_spar_t_top",0.75))+float(g("front_spar_t_bot",0.75))
        st.caption(f"Total depth at the root = {total_h:.3f} in. Caps change in a straight line from the taper-start station to the tip. Web height still follows the chord.")

    elif _fst == "Box Spar":
        c1f, c2f = st.columns(2)
        with c1f:
            st.session_state.inp["front_spar_b_outer"] = st.number_input("Root outer width (in)", value=float(g("front_spar_b_outer",2.0)), format="%.3f", key="f_bo")
            st.session_state.inp["front_spar_b_outer_tip"] = st.number_input("Tip outer width (in)", value=float(g("front_spar_b_outer_tip", g("front_spar_b_outer",2.0))), format="%.3f", key="f_bot")
            st.session_state.inp["front_spar_h_outer"] = st.number_input("Outer height at root (in)", value=float(g("front_spar_h_outer",5.0)), format="%.3f", key="f_ho")
            st.session_state.inp["front_spar_t_web"]   = st.number_input("Web Thickness (in)", value=float(g("front_spar_t_web",0.125)), format="%.4f", key="f_tw")
            st.session_state.inp["front_spar_t_cap"]   = st.number_input("Root cap thickness (in)", value=float(g("front_spar_t_cap",0.75)), format="%.4f", key="f_tc")
            st.session_state.inp["front_spar_t_cap_tip"] = st.number_input("Tip cap thickness (in)", value=float(g("front_spar_t_cap_tip", g("front_spar_t_cap",0.75))), format="%.4f", key="f_tct")
        with c2f:
            _def_cm = g("front_spar_cap_mat","Sitka Spruce")
            _cm_idx = _ALL_MATS.index(_def_cm) if _def_cm in _ALL_MATS else 0
            st.session_state.inp["front_spar_cap_mat"] = st.selectbox("Cap Material", _ALL_MATS, index=_cm_idx, key="f_cm")
            _def_wm = g("front_spar_web_mat","Birch Plywood")
            _wm_idx = _ALL_MATS.index(_def_wm) if _def_wm in _ALL_MATS else 0
            st.session_state.inp["front_spar_web_mat"] = st.selectbox("Web Material", _ALL_MATS, index=_wm_idx, key="f_wm")

    elif _fst in ("Aluminum I-Beam","Aluminum C-Spar"):
        c1f, c2f = st.columns(2)
        with c1f:
            st.session_state.inp["front_spar_b_top"] = st.number_input("Root cap width (in)", value=float(g("front_spar_b_top",1.5)), format="%.3f", key="f_bt")
            st.session_state.inp["front_spar_t_top"] = st.number_input("Root cap thickness (in)", value=float(g("front_spar_t_top",0.125)), format="%.4f", key="f_tt")
            st.session_state.inp["front_spar_b_top_tip"] = st.number_input("Tip cap width (in)", value=float(g("front_spar_b_top_tip", g("front_spar_b_top",1.5))), format="%.3f", key="f_btt")
            st.session_state.inp["front_spar_t_top_tip"] = st.number_input("Tip cap thickness (in)", value=float(g("front_spar_t_top_tip", g("front_spar_t_top",0.125))), format="%.4f", key="f_ttt")
            st.session_state.inp["front_spar_h_web"] = st.number_input("Web Height (in)", value=float(g("front_spar_h_web",5.0)), format="%.3f", key="f_hw")
            st.session_state.inp["front_spar_t_web"] = st.number_input("Web Thickness (in)", value=float(g("front_spar_t_web",0.050)), format="%.4f", key="f_tw")
        with c2f:
            _def_cm = g("front_spar_cap_mat","6061-T6")
            _cm_idx = _METAL_MATS.index(_def_cm) if _def_cm in _METAL_MATS else 0
            st.session_state.inp["front_spar_cap_mat"] = st.selectbox("Material", _METAL_MATS, index=_cm_idx, key="f_cm")
            st.session_state.inp["front_spar_web_mat"] = st.session_state.inp["front_spar_cap_mat"]
        total_h = float(g("front_spar_h_web",5.0))+float(g("front_spar_t_top",0.125))
        st.caption(f"Total depth = {total_h:.3f} in")


# Rear Spar
with tabs[5]:
    st.subheader("Rear Spar")

    try:
        from spar_sections import MATERIAL_DB
        _ALL_MATS_R  = list(MATERIAL_DB.keys())
        _METAL_MATS_R= [k for k,v in MATERIAL_DB.items() if not v.get("is_wood")]
    except:
        _ALL_MATS_R = _METAL_MATS_R = ["6061-T6","2024-T3","Sitka Spruce","Birch Plywood"]

    _REAR_TYPES = ["Round Tube","Plain Rectangular","I-Beam","Box Spar","Aluminum I-Beam","Aluminum C-Spar"]
    _rst = st.selectbox("Spar Type", _REAR_TYPES,
        index=_REAR_TYPES.index(g("rear_spar_type","Round Tube"))
              if g("rear_spar_type","Round Tube") in _REAR_TYPES else 0,
        key="rear_type")
    st.session_state.inp["rear_spar_type"] = _rst

    if _rst == "Round Tube":
        from common_tube_spars import COMMON_TUBE_SIZES, list_tube_descriptions
        _tlr = list_tube_descriptions()
        _cor = float(g("rear_spar_od", 2.5))
        _cwr = float(g("rear_spar_wall", 0.065))
        _cir = next((i for i,t in enumerate(COMMON_TUBE_SIZES)
                     if abs(t.od-_cor)<0.001 and abs(t.wall-_cwr)<0.001), 0)
        def _on_rear_tube():
            _sel = st.session_state["rear_tube"]
            _t   = COMMON_TUBE_SIZES[list_tube_descriptions().index(_sel)]
            st.session_state.inp["rear_spar_od"]   = _t.od
            st.session_state.inp["rear_spar_wall"] = _t.wall
            st.session_state.inp["rear_spar_mat"]  = "6061-T6"
        _rss = st.selectbox("Rear Spar Tube", _tlr, index=_cir,
                            key="rear_tube", on_change=_on_rear_tube)
        _rt  = COMMON_TUBE_SIZES[_tlr.index(_rss)]
        if abs(st.session_state.inp.get("rear_spar_od",0) - _rt.od) > 0.001:
            st.session_state.inp["rear_spar_od"]   = _rt.od
            st.session_state.inp["rear_spar_wall"] = _rt.wall
            st.session_state.inp["rear_spar_mat"]  = "6061-T6"
        st.caption(str(_rt))

    elif _rst == "Plain Rectangular":
        st.session_state.inp["rear_spar_width"]   = st.number_input("Width (in)", value=float(g("rear_spar_width",1.5)), format="%.3f", key="r_w")
        st.session_state.inp["rear_spar_height"]  = st.number_input("Height (in)", value=float(g("rear_spar_height",3.0)), format="%.3f", key="r_h")
        _def_rm = g("rear_spar_cap_mat","Sitka Spruce")
        _rm_idx = _ALL_MATS_R.index(_def_rm) if _def_rm in _ALL_MATS_R else 0
        st.session_state.inp["rear_spar_cap_mat"] = st.selectbox("Material", _ALL_MATS_R, index=_rm_idx, key="r_cm")

    elif _rst == "I-Beam":
        c1r, c2r = st.columns(2)
        with c1r:
            st.session_state.inp["rear_spar_b_top"] = st.number_input("Root cap width top (in)", value=float(g("rear_spar_b_top",1.0)), format="%.3f", key="r_bt")
            st.session_state.inp["rear_spar_t_top"] = st.number_input("Root cap height top (in)", value=float(g("rear_spar_t_top",0.5)), format="%.4f", key="r_tt")
            st.session_state.inp["rear_spar_b_bot"] = st.number_input("Root cap width bottom (in)", value=float(g("rear_spar_b_bot",1.0)), format="%.3f", key="r_bb")
            st.session_state.inp["rear_spar_t_bot"] = st.number_input("Root cap height bottom (in)", value=float(g("rear_spar_t_bot",0.5)), format="%.4f", key="r_tb")
            st.session_state.inp["rear_spar_b_top_tip"] = st.number_input("Tip cap width top (in)", value=float(g("rear_spar_b_top_tip", g("rear_spar_b_top",1.0))), format="%.3f", key="r_btt")
            st.session_state.inp["rear_spar_t_top_tip"] = st.number_input("Tip cap height top (in)", value=float(g("rear_spar_t_top_tip", g("rear_spar_t_top",0.5))), format="%.4f", key="r_ttt")
            st.session_state.inp["rear_spar_b_bot_tip"] = st.number_input("Tip cap width bottom (in)", value=float(g("rear_spar_b_bot_tip", g("rear_spar_b_bot",1.0))), format="%.3f", key="r_bbt")
            st.session_state.inp["rear_spar_t_bot_tip"] = st.number_input("Tip cap height bottom (in)", value=float(g("rear_spar_t_bot_tip", g("rear_spar_t_bot",0.5))), format="%.4f", key="r_tbt")
        with c2r:
            st.session_state.inp["rear_spar_h_web"] = st.number_input("Web Height (in)", value=float(g("rear_spar_h_web",3.0)), format="%.3f", key="r_hw")
            st.session_state.inp["rear_spar_t_web"] = st.number_input("Web Thickness (in)", value=float(g("rear_spar_t_web",0.125)), format="%.4f", key="r_tw")
            _def_rm = g("rear_spar_cap_mat","Sitka Spruce")
            _rm_idx = _ALL_MATS_R.index(_def_rm) if _def_rm in _ALL_MATS_R else 0
            st.session_state.inp["rear_spar_cap_mat"] = st.selectbox("Cap Material", _ALL_MATS_R, index=_rm_idx, key="r_cm")
            _def_rwm = g("rear_spar_web_mat","Birch Plywood")
            _rwm_idx = _ALL_MATS_R.index(_def_rwm) if _def_rwm in _ALL_MATS_R else 0
            st.session_state.inp["rear_spar_web_mat"] = st.selectbox("Web Material", _ALL_MATS_R, index=_rwm_idx, key="r_wm")
        total_hr = float(g("rear_spar_h_web",3.0))+float(g("rear_spar_t_top",0.5))+float(g("rear_spar_t_bot",0.5))
        st.caption(f"Total depth at the root = {total_hr:.3f} in. Caps change in a straight line from the taper-start station to the tip. Web height still follows the chord.")

    elif _rst == "Box Spar":
        c1r, c2r = st.columns(2)
        with c1r:
            st.session_state.inp["rear_spar_b_outer"] = st.number_input("Root outer width (in)", value=float(g("rear_spar_b_outer",1.5)), format="%.3f", key="r_bo")
            st.session_state.inp["rear_spar_b_outer_tip"] = st.number_input("Tip outer width (in)", value=float(g("rear_spar_b_outer_tip", g("rear_spar_b_outer",1.5))), format="%.3f", key="r_bot")
            st.session_state.inp["rear_spar_h_outer"] = st.number_input("Outer height at root (in)", value=float(g("rear_spar_h_outer",3.0)), format="%.3f", key="r_ho")
            st.session_state.inp["rear_spar_t_web"]   = st.number_input("Web Thickness (in)", value=float(g("rear_spar_t_web",0.125)), format="%.4f", key="r_tw")
            st.session_state.inp["rear_spar_t_cap"]   = st.number_input("Root cap thickness (in)", value=float(g("rear_spar_t_cap",0.5)), format="%.4f", key="r_tc")
            st.session_state.inp["rear_spar_t_cap_tip"] = st.number_input("Tip cap thickness (in)", value=float(g("rear_spar_t_cap_tip", g("rear_spar_t_cap",0.5))), format="%.4f", key="r_tct")
        with c2r:
            _def_rm = g("rear_spar_cap_mat","Sitka Spruce")
            _rm_idx = _ALL_MATS_R.index(_def_rm) if _def_rm in _ALL_MATS_R else 0
            st.session_state.inp["rear_spar_cap_mat"] = st.selectbox("Cap Material", _ALL_MATS_R, index=_rm_idx, key="r_cm")
            _def_rwm = g("rear_spar_web_mat","Birch Plywood")
            _rwm_idx = _ALL_MATS_R.index(_def_rwm) if _def_rwm in _ALL_MATS_R else 0
            st.session_state.inp["rear_spar_web_mat"] = st.selectbox("Web Material", _ALL_MATS_R, index=_rwm_idx, key="r_wm")

    elif _rst in ("Aluminum I-Beam","Aluminum C-Spar"):
        c1r, c2r = st.columns(2)
        with c1r:
            st.session_state.inp["rear_spar_b_top"] = st.number_input("Root cap width (in)", value=float(g("rear_spar_b_top",1.0)), format="%.3f", key="r_bt")
            st.session_state.inp["rear_spar_t_top"] = st.number_input("Root cap thickness (in)", value=float(g("rear_spar_t_top",0.083)), format="%.4f", key="r_tt")
            st.session_state.inp["rear_spar_b_top_tip"] = st.number_input("Tip cap width (in)", value=float(g("rear_spar_b_top_tip", g("rear_spar_b_top",1.0))), format="%.3f", key="r_btt")
            st.session_state.inp["rear_spar_t_top_tip"] = st.number_input("Tip cap thickness (in)", value=float(g("rear_spar_t_top_tip", g("rear_spar_t_top",0.083))), format="%.4f", key="r_ttt")
            st.session_state.inp["rear_spar_h_web"] = st.number_input("Web Height (in)", value=float(g("rear_spar_h_web",3.0)), format="%.3f", key="r_hw")
            st.session_state.inp["rear_spar_t_web"] = st.number_input("Web Thickness (in)", value=float(g("rear_spar_t_web",0.040)), format="%.4f", key="r_tw")
        with c2r:
            _def_rm = g("rear_spar_cap_mat","6061-T6")
            _rm_idx = _METAL_MATS_R.index(_def_rm) if _def_rm in _METAL_MATS_R else 0
            st.session_state.inp["rear_spar_cap_mat"] = st.selectbox("Material", _METAL_MATS_R, index=_rm_idx, key="r_cm")
            st.session_state.inp["rear_spar_web_mat"] = st.session_state.inp["rear_spar_cap_mat"]
        total_hr = float(g("rear_spar_h_web",3.0))+float(g("rear_spar_t_top",0.083))
        st.caption(f"Total depth = {total_hr:.3f} in")

# Wing Structure
with tabs[3]:
    st.subheader("Wing Structure")

    try:
        from spar_sections import MATERIAL_DB
        _WS_ALL   = list(MATERIAL_DB.keys())
        _WS_WOOD  = [k for k,v in MATERIAL_DB.items() if v.get("is_wood")]
        _WS_METAL = [k for k,v in MATERIAL_DB.items() if not v.get("is_wood")]
    except:
        _WS_ALL = _WS_WOOD = _WS_METAL = ["6061-T6","Sitka Spruce","Birch Plywood"]

    _ws_types = ["fabric_tube","fabric_buildup","aluminum_skin"]
    _ws_cur   = g("wing_structure_type","fabric_tube")
    st.session_state.inp["wing_structure_type"] = st.selectbox(
        "Structure Type", _ws_types,
        index=_ws_types.index(_ws_cur) if _ws_cur in _ws_types else 0,
        key="wing_type")

    st.markdown("**D-Cell (Nose Box)**")
    st.session_state.inp["dcell_enabled"] = st.checkbox(
        "D-Cell enabled", value=bool(g("dcell_enabled", False)), key="dcell")
    if g("dcell_enabled"):
        _dc_mat = g("dcell_skin_mat","Birch Plywood")
        st.session_state.inp["dcell_skin_mat"] = st.selectbox(
            "D-Cell Skin Material", _WS_ALL,
            index=_WS_ALL.index(_dc_mat) if _dc_mat in _WS_ALL else 0, key="dcsm")
        st.session_state.inp["dcell_skin_thick"] = st.number_input(
            "D-Cell Skin Thickness (in)", value=float(g("dcell_skin_thick",0.0625)),
            format="%.4f", key="dcst")

    st.markdown("**Geodetic Bracing**")
    st.session_state.inp["geodetic_enabled"] = st.checkbox(
        "Geodetic enabled", value=bool(g("geodetic_enabled", False)), key="ge")
    if g("geodetic_enabled"):
        _geo_mat = g("geodetic_mat","Sitka Spruce")
        st.session_state.inp["geodetic_mat"] = st.selectbox(
            "Geodetic Strip Material", _WS_WOOD if _WS_WOOD else _WS_ALL,
            index=(_WS_WOOD.index(_geo_mat) if _geo_mat in _WS_WOOD else 0), key="gm")
        c1ws, c2ws = st.columns(2)
        with c1ws:
            st.session_state.inp["geodetic_w"] = st.number_input(
                "Strip Width (in)", value=float(g("geodetic_w",1.0)), format="%.3f", key="gw")
            st.session_state.inp["geodetic_t"] = st.number_input(
                "Strip Thickness (in)", value=float(g("geodetic_t",0.125)), format="%.4f", key="gt")
        with c2ws:
            st.session_state.inp["geodetic_strips_per_bay"] = st.number_input(
                "Strips per Bay", value=int(g("geodetic_strips_per_bay",2)), min_value=1, key="gspb")
            st.session_state.inp["geodetic_angle"] = st.number_input(
                "Angle (deg)", value=float(g("geodetic_angle",45.0)), step=5.0, key="ga")

    st.markdown("**Inboard torsion box**")
    st.session_state.inp["torsion_box_enabled"] = st.checkbox(
        "Sheet the inboard rib bays",
        value=bool(g("torsion_box_enabled", False)), key="tbx")
    if g("torsion_box_enabled"):
        st.session_state.inp["torsion_box_bays"] = int(st.number_input(
            "Rib bays from the root", value=int(g("torsion_box_bays", 4)),
            min_value=0, step=1, key="tb_bays"))
        _tb1, _tb2 = st.columns(2)
        with _tb1:
            _ttm = g("torsion_box_top_mat", "Birch Plywood")
            st.session_state.inp["torsion_box_top_mat"] = st.selectbox(
                "Top sheet material", _WS_ALL,
                index=_WS_ALL.index(_ttm) if _ttm in _WS_ALL else 0, key="tb_tm")
            st.session_state.inp["torsion_box_top_thick"] = st.number_input(
                "Top sheet thickness (in)", value=float(g("torsion_box_top_thick", 0.125)),
                format="%.4f", key="tb_tt")
        with _tb2:
            _tbm = g("torsion_box_bot_mat", "Birch Plywood")
            st.session_state.inp["torsion_box_bot_mat"] = st.selectbox(
                "Bottom sheet material", _WS_ALL,
                index=_WS_ALL.index(_tbm) if _tbm in _WS_ALL else 0, key="tb_bm")
            st.session_state.inp["torsion_box_bot_thick"] = st.number_input(
                "Bottom sheet thickness (in)", value=float(g("torsion_box_bot_thick", 0.125)),
                format="%.4f", key="tb_bt")

    if g("wing_structure_type") == "aluminum_skin":
        st.markdown("**Aluminum Skin**")
        c1ws, c2ws = st.columns(2)
        with c1ws:
            _stm = g("skin_top_mat","6061-T6")
            st.session_state.inp["skin_top_mat"] = st.selectbox(
                "Top Skin Material", _WS_METAL,
                index=_WS_METAL.index(_stm) if _stm in _WS_METAL else 0, key="stm")
            st.session_state.inp["skin_top_thick"] = st.number_input(
                "Top Skin Thickness (in)", value=float(g("skin_top_thick",0.025)),
                format="%.4f", key="stt")
        with c2ws:
            _sbm = g("skin_bot_mat","6061-T6")
            st.session_state.inp["skin_bot_mat"] = st.selectbox(
                "Bottom Skin Material", _WS_METAL,
                index=_WS_METAL.index(_sbm) if _sbm in _WS_METAL else 0, key="sbm")
            st.session_state.inp["skin_bot_thick"] = st.number_input(
                "Bottom Skin Thickness (in)", value=float(g("skin_bot_thick",0.025)),
                format="%.4f", key="sbt")

    st.markdown("**Wood Knockdown**")
    st.session_state.inp["wood_knockdown"] = st.number_input(
        "Wood Knockdown Factor (0.75 = AC 43.13-1B)",
        value=float(g("wood_knockdown",0.75)), format="%.3f", key="wkd")

    st.markdown("**Ribs**")
    _rib_types = ["Plywood web", "Sheet aluminum formed", "Dow foam with spruce caps"]
    _rib_cur = g("rib_type", "Plywood web")
    st.session_state.inp["rib_type"] = st.selectbox(
        "Rib type", _rib_types,
        index=_rib_types.index(_rib_cur) if _rib_cur in _rib_types else 0,
        key="rib_type")
    _rc1, _rc2 = st.columns(2)
    with _rc1:
        st.session_state.inp["rib_h_web"] = st.number_input(
            "Web / foam height (in)", value=float(g("rib_h_web", 3.0)),
            format="%.3f", key="rhw")
        st.session_state.inp["rib_t_web"] = st.number_input(
            "Web, sheet, or foam thickness (in)", value=float(g("rib_t_web", 0.125)),
            format="%.4f", key="rtw")
    with _rc2:
        st.session_state.inp["rib_b_cap"] = st.number_input(
            "Cap or flange width (in)", value=float(g("rib_b_cap", 0.75)),
            format="%.3f", key="rbc")
        if g("rib_type") != "Sheet aluminum formed":
            st.session_state.inp["rib_t_cap"] = st.number_input(
                "Cap thickness (in)", value=float(g("rib_t_cap", 0.125)),
                format="%.4f", key="rtc")
    if g("rib_type") == "Dow foam with spruce caps":
        st.caption("Dow Styrofoam core, ASTM C273 minimums G = 300 psi and shear strength = 25 psi. Caps are Sitka spruce. Glue is not checked.")
    elif g("rib_type") == "Sheet aluminum formed":
        _rib_mats = _WS_METAL or ["2024-T3"]
        _rm = g("rib_mat", "2024-T3")
        if _rm not in _rib_mats:
            _rm = "2024-T3" if "2024-T3" in _rib_mats else _rib_mats[0]
        st.session_state.inp["rib_mat"] = st.selectbox(
            "Sheet material", _rib_mats, index=_rib_mats.index(_rm), key="rm_sheet")
        st.caption("The formed flange thickness equals the sheet. Shear uses the web only.")
    else:
        _rib_mats = _WS_WOOD or ["Birch Plywood"]
        _rm = g("rib_mat", "Birch Plywood")
        if _rm not in _rib_mats:
            _rm = "Birch Plywood" if "Birch Plywood" in _rib_mats else _rib_mats[0]
        st.session_state.inp["rib_mat"] = st.selectbox(
            "Rib material", _rib_mats, index=_rib_mats.index(_rm), key="rm_wood")

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
        ax3.set_title("Spar position (in, includes twist)")
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax4 = fig.add_subplot(3, 2, 4)
        ax4.plot(x, a.pos.get("M", []), label="+g")
        ax4.plot(x, a.neg.get("M", []), label="-g", linestyle="--")
        ax4.set_title("Moment (lb·in)")
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        try:
            pass  # geometry drawn below
        except:
            pass
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        st.subheader("Wing Geometry")
        try:
            fig_top, ax_top = plt.subplots(1, 1, figsize=(14, 4))
            fig_side, ax_side = plt.subplots(1, 1, figsize=(14, 4))
            a.draw_geometry(ax_top, ax_side)
            fig_top.tight_layout()
            fig_side.tight_layout()
            st.pyplot(fig_top)
            plt.close(fig_top)
            st.pyplot(fig_side)
            plt.close(fig_side)
        except Exception as e:
            st.warning(f"Geometry plot error: {e}")
    else:
        st.info("Run analysis to see plots.")

st.caption("AeroBeam v1.2.3 • Custom PDF filename supported")
