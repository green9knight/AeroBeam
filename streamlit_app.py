"""
AeroBeam v1.2 - Full Streamlit App
Clean tube lookup from common_tube_spars.py
Proper airfoil apply with spar depth display
"""

import streamlit as st
import json
import io
import math
import matplotlib
matplotlib.use("Agg")
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
    from common_tube_spars import COMMON_TUBE_SIZES, list_tube_descriptions
    BACKEND_OK = True
except Exception as e:
    BACKEND_OK = False
    st.error(f"Backend import failed: {e}")
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
if "inp" not in st.session_state:
    st.session_state.inp = dict(DEFAULT_INPUTS)
if "result" not in st.session_state:
    st.session_state.result = None

def g(key, default=None):
    """Get value from session inputs, falling back to DEFAULT_INPUTS then default."""
    return st.session_state.inp.get(key, DEFAULT_INPUTS.get(key, default))

# ── Spar depth helper ─────────────────────────────────────────────────────────
def airfoil_depth_at(x_c: float, t_c: float, chord: float) -> float:
    """
    NACA 4-digit thickness distribution: total depth at chord position x_c.
    For non-NACA airfoils this gives a reasonable estimate since most airfoils
    follow a similar distribution near the spar stations.
    """
    xc = max(min(x_c, 1.0), 0.0)
    y  = 5*t_c*(0.2969*math.sqrt(xc) - 0.1260*xc - 0.3516*xc**2
                + 0.2843*xc**3 - 0.1015*xc**4)
    return 2 * y * chord  # total depth (upper + lower surface)

def spar_depth_info(prefix: str) -> str:
    """Return a one-line depth hint for a spar station."""
    t_c   = float(g("airfoil_t_c", 0.12))
    chord = float(g("root_chord", 54.0))
    pct   = float(g(f"{prefix}_spar_percent", 0.15))
    # Use x_t_c from currently selected airfoil if available
    af    = get_airfoil(str(g("airfoil", ""))) or {}
    x_t_c = af.get("x_t_c") or 0.30   # default max-thickness at 30%c
    depth = airfoil_depth_at(pct, t_c, chord)
    max_d = airfoil_depth_at(x_t_c, t_c, chord)
    return (f"Airfoil depth at {pct*100:.0f}%c = **{depth:.2f}\"**  "
            f"(max depth {max_d:.2f}\" at {x_t_c*100:.0f}%c, t/c={t_c:.3f})")

# ── Tube selector helper ──────────────────────────────────────────────────────
TUBE_LABELS = list_tube_descriptions()   # from common_tube_spars.py

def tube_selector(prefix: str, label: str):
    """
    Dropdown of tubes from common_tube_spars.py.
    Sets {prefix}_od and {prefix}_wall in session state.
    Shows depth vs available spar space.
    """
    # Find current selection index
    cur_od   = float(g(f"{prefix}_od",   2.0))
    cur_wall = float(g(f"{prefix}_wall", 0.065))
    # Match current OD/wall to a label
    cur_idx = 0
    for i, tube in enumerate(COMMON_TUBE_SIZES):
        if abs(tube.od - cur_od) < 0.001 and abs(tube.wall - cur_wall) < 0.001:
            cur_idx = i
            break

    sel_label = st.selectbox(f"{label} Size", TUBE_LABELS, index=cur_idx, key=f"{prefix}_tube_sel")
    # Find matching tube object
    sel_tube = COMMON_TUBE_SIZES[TUBE_LABELS.index(sel_label)]
    st.session_state.inp[f"{prefix}_od"]   = sel_tube.od
    st.session_state.inp[f"{prefix}_wall"] = sel_tube.wall
    st.session_state.inp[f"{prefix}_mat"]  = "6061-T6"

    # Depth check: tube OD vs available airfoil depth at spar station
    avail = airfoil_depth_at(
        float(g(f"{prefix}_spar_percent", 0.15)),
        float(g("airfoil_t_c", 0.12)),
        float(g("root_chord", 54.0))
    )
    I_val = sel_tube.I
    EI_val = sel_tube.EI
    fit = "✅ fits" if sel_tube.od <= avail else f"⚠️ OD {sel_tube.od:.3f}\" > airfoil depth {avail:.2f}\""
    st.caption(f"OD={sel_tube.od:.3f}\"  wall={sel_tube.wall:.3f}\"  "
               f"I={I_val:.4f} in⁴  EI={EI_val/1e6:.2f}×10⁶ lb·in²  —  {fit}")

# ── Header ────────────────────────────────────────────────────────────────────
# ── Header ────────────────────────────────────────────────────────────────────
_hc1, _hc2 = st.columns([0.08, 0.92])
with _hc1:
    if _ico:
        st.image(_ico, width=42)
    else:
        st.markdown("### ✈️")
with _hc2:
    st.markdown("<div style='padding-top:8px'><h2 style='margin:0'>AeroBeam v1.2</h2></div>", unsafe_allow_html=True)
    st.caption("Wing Bending · Shear · Buckling · Torsion")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo + title in sidebar
    if _ico:
        _sc1, _sc2 = st.columns([0.25, 0.75])
        with _sc1:
            st.image(_ico, width=60)
        with _sc2:
            st.markdown("**AeroBeam v1.2**")
    else:
        st.header("Controls")
    st.divider()

    if st.button("▶ Run Analysis", type="primary", use_container_width=True, key="run_btn"):
        with st.spinner("Analysing…"):
            try:
                a = WingStressAnalyzer(dict(st.session_state.inp))
                a.analyze()
                st.session_state.result = a
                st.success("Analysis complete")
            except Exception as e:
                st.error(f"Analysis error: {e}")
                import traceback; st.code(traceback.format_exc())

    # Live MS status
    if st.session_state.result:
        a = st.session_state.result
        ms_f = a.ms_front.get("MS_ult", 0)
        ms_r = a.ms_rear.get("MS_ult", 0) if a.rear_spar else None
        c_f  = "🟢" if ms_f >= 0 else "🔴"
        st.markdown(f"{c_f} Front MS: **{ms_f:+.2f}**")
        if ms_r is not None:
            c_r = "🟢" if ms_r >= 0 else "🔴"
            st.markdown(f"{c_r} Rear MS:  **{ms_r:+.2f}**")

    st.divider()

    # PDF
    if st.session_state.result:
        st.subheader("PDF Report")
        custom_name = st.text_input("Filename", value="AeroBeam_Report.pdf", key="pdf_name")
        if st.button("📄 Generate PDF", use_container_width=True, key="pdf_btn"):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp_path = tmp.name
                st.session_state.result.export_pdf(path=tmp_path)
                with open(tmp_path, "rb") as f:
                    pdf_bytes = f.read()
                os.unlink(tmp_path)
                fname = custom_name if custom_name.lower().endswith(".pdf") else custom_name + ".pdf"
                st.download_button(f"⬇ Download {fname}", pdf_bytes, fname,
                                   mime="application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"PDF failed: {e}")

    st.divider()

    # File save/load
    st.subheader("Project File")
    up = st.file_uploader("Load .aerobeam", type=["aerobeam","json"], key="uploader")
    if up:
        raw = json.load(up)
        # Merge: file wins, defaults fill gaps for new keys
        merged = dict(DEFAULT_INPUTS)
        for k, v in raw.items():
            if isinstance(v, str) and v.strip():
                try:    merged[k] = float(v)
                except: merged[k] = v
            else:
                merged[k] = v
        st.session_state.inp = merged
        st.success(f"Loaded: {up.name}")
        st.rerun()

    if st.button("💾 Save Project", use_container_width=True, key="save_btn"):
        buf = io.BytesIO(json.dumps(st.session_state.inp, indent=2, default=str).encode())
        st.download_button("⬇ Download .aerobeam", buf, "project.aerobeam",
                           mime="application/json", key="dl_btn")

# ── Main tabs ─────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🔷 Wing Geometry", "✈ Flight & Airfoil", "⚖ Loads & Config",
    "🔩 Front Spar", "🔩 Rear Spar", "🏗 Wing Structure", "📐 Buckling",
    "📊 Results", "📈 Plots"
])

# ═══════════════════════════════════════════════════════════
# TAB 0 — Wing Geometry
# ═══════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("Wing Geometry")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Planform**")
        st.session_state.inp["b"]              = st.number_input("Total Span b (in)", value=float(g("b")), step=1.0, key="b")
        st.session_state.inp["r"]              = st.number_input("Root Attach BL (in)", value=float(g("r", 11.0)), step=1.0, key="r")
        st.session_state.inp["root_chord"]     = st.number_input("Root Chord (in)", value=float(g("root_chord")), step=1.0, key="root_chord")
        st.session_state.inp["tip_chord"]      = st.number_input("Tip Chord (in)", value=float(g("tip_chord")), step=1.0, key="tip_chord")
        st.session_state.inp["taper_start_bl"] = st.number_input("Taper Start BL (in)  [0 = taper from root]", value=float(g("taper_start_bl", 0.0)), step=1.0, key="taper_start_bl")
        st.session_state.inp["rib_spacing"]    = st.number_input("Rib Spacing (in)", value=float(g("rib_spacing")), step=0.5, key="rib_spacing")
    with c2:
        st.markdown("**Spar Positions**")
        st.session_state.inp["front_spar_percent"] = st.slider("Front Spar % Chord", 0.05, 0.50, float(g("front_spar_percent")), 0.01, key="fsp")
        st.session_state.inp["rear_spar_percent"]  = st.slider("Rear Spar % Chord",  0.50, 0.95, float(g("rear_spar_percent")),  0.01, key="rsp")
        st.session_state.inp["front_spar_load_share"] = st.slider("Front Spar Load Share", 0.0, 1.0, float(g("front_spar_load_share")), 0.05, key="lsf")
        st.caption(f"Rear spar load share = {1 - float(g('front_spar_load_share')):.2f}")

        st.markdown("**Lift Distribution**")
        lift_opts = ["schrenk","elliptical","chord_based","uniform"]
        st.session_state.inp["lift_distribution_type"] = st.selectbox(
            "Distribution", lift_opts,
            index=lift_opts.index(g("lift_distribution_type","schrenk")), key="ldt")

    # Spar depth preview (uses current airfoil + chord + spar positions)
    st.info(spar_depth_info("front") + "   |   " + spar_depth_info("rear"))

# ═══════════════════════════════════════════════════════════
# TAB 1 — Flight & Airfoil
# ═══════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Flight & Airfoil")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Airfoil Selection**")
        fams = ["(All)"] + airfoil_families()
        fam  = st.selectbox("Family filter", fams, key="af_fam")
        srch = st.text_input("Search airfoil name", key="af_search")

        # Build filtered list
        all_names = [k for k in AIRFOIL_DB if k != "Manual Entry"]
        if fam != "(All)":
            all_names = [n for n in all_names if AIRFOIL_DB[n].get("family","") == fam]
        if srch:
            all_names = [n for n in all_names if srch.lower() in n.lower()]
        all_names = all_names[:300]

        cur = g("airfoil", "NACA 4412")
        idx = all_names.index(cur) if cur in all_names else 0
        selected = st.selectbox("Airfoil", all_names, index=idx, key="af_sel")

        if st.button("✅ Apply airfoil data", key="apply_af"):
            af = get_airfoil(selected)
            if af:
                st.session_state.inp["airfoil"]      = selected
                st.session_state.inp["airfoil_t_c"]  = float(af.get("t_c")   or g("airfoil_t_c", 0.12))
                st.session_state.inp["Cm_ac"]        = float(af.get("Cm_ac") or g("Cm_ac", 0.0))
                st.session_state.inp["Cl_alpha"]     = float(af.get("Cl_alpha") or 6.283)
                st.session_state.inp["x_ac_c"]       = float(af.get("x_ac_c") or 0.25)
                # Store x_t_c for spar depth calc
                if af.get("x_t_c"):
                    st.session_state.inp["x_t_c"]    = float(af["x_t_c"])
                st.success(f"Applied: {selected}  t/c={st.session_state.inp['airfoil_t_c']:.4f}  Cm={st.session_state.inp['Cm_ac']:.4f}")
                st.rerun()

    with c2:
        st.markdown("**Aerodynamic Parameters**")
        st.session_state.inp["Cm_ac"]       = st.number_input("Cm_ac (pitching moment)", value=float(g("Cm_ac")), format="%.4f", key="cm_ac")
        st.session_state.inp["Cm_flap"]     = st.number_input("ΔCm full flap (adds to Cm_ac)", value=float(g("Cm_flap", 0.0)), format="%.4f", key="cm_flap")
        st.session_state.inp["Cl_alpha"]    = st.number_input("Cl_alpha (per radian)", value=float(g("Cl_alpha")), format="%.3f", key="cl_alpha")
        st.session_state.inp["x_ac_c"]      = st.number_input("AC position x/c", value=float(g("x_ac_c", 0.25)), format="%.4f", key="xac")
        st.session_state.inp["airfoil_t_c"] = st.number_input("t/c (thickness ratio)", value=float(g("airfoil_t_c")), format="%.4f", key="tc")

        st.markdown("**Flight Speeds**")
        st.session_state.inp["Vd_mph"]      = st.number_input("Design Dive Speed Vd (mph)", value=float(g("Vd_mph")), step=1.0, key="vd")
        st.session_state.inp["Vc_mph"]      = st.number_input("Cruise Speed Vc (mph)", value=float(g("Vc_mph", 80.0)), step=1.0, key="vc")
        st.session_state.inp["Va_mph"]      = st.number_input("Manoeuvre Speed Va (mph)", value=float(g("Va_mph", 60.0)), step=1.0, key="va")
        st.session_state.inp["altitude_ft"] = st.number_input("Altitude (ft)", value=float(g("altitude_ft", 2000.0)), step=500.0, key="alt")

    # Spar depth preview updates with new t/c
    st.info(spar_depth_info("front") + "   |   " + spar_depth_info("rear"))

# ═══════════════════════════════════════════════════════════
# TAB 2 — Loads & Config
# ═══════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("Loads & Configuration")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Loads**")
        st.session_state.inp["n"]           = st.number_input("Positive Load Factor n (ultimate)", value=float(g("n")), step=0.5, key="n_pos")
        st.session_state.inp["n_neg"]       = st.number_input("Negative Load Factor n_neg", value=float(g("n_neg", -3.0)), step=0.5, key="n_neg")
        st.session_state.inp["Weight"]      = st.number_input("Gross Weight (lb)", value=float(g("Weight")), step=10.0, key="weight")
        st.session_state.inp["Wing_Weight"] = st.number_input("Wing Weight one side (lb)", value=float(g("Wing_Weight", 25.0)), step=5.0, key="ww")
        st.session_state.inp["Tail_Down_1g"]= st.number_input("Tail Down Load at 1g (lb)", value=float(g("Tail_Down_1g", 0.0)), step=5.0, key="tdl")

        # ng_lift auto-calculated
        n_val    = float(g("n", 6.0))
        w_val    = float(g("Weight", 1750.0))
        td_val   = float(g("Tail_Down_1g", 0.0))
        ng_auto  = n_val * (w_val / 2.0 + td_val)
        manual   = st.checkbox("Override ng_lift manually", value=bool(g("ng_lift_manual", False)), key="ngl_manual")
        st.session_state.inp["ng_lift_manual"] = manual
        if manual:
            st.session_state.inp["ng_lift"] = st.number_input("ng_lift (lb) — override", value=float(g("ng_lift", ng_auto)), step=10.0, key="ngl")
        else:
            st.session_state.inp["ng_lift"] = ng_auto
            st.info(f"Semi-span design lift: **ng_lift = {ng_auto:,.0f} lb**  (n × W/2 + Tail)")

        st.session_state.inp["dist_wing_weight"] = st.checkbox(
            "Distribute wing weight (inertia relief)",
            value=bool(g("dist_wing_weight", False)), key="dww")

    with c2:
        st.markdown("**Structural Configuration**")
        cfg_opts = ["strut_braced","single_strut","cantilever"]
        st.session_state.inp["config"] = st.selectbox("Config", cfg_opts,
            index=cfg_opts.index(g("config","strut_braced")), key="cfg")

        if g("config") != "cantilever":
            st.session_state.inp["strut_bl"]      = st.number_input("Strut BL (in)", value=float(g("strut_bl", 96.0)), step=1.0, key="sbl")
            st.session_state.inp["strut_vert"]    = st.number_input("Strut Vertical Rise (in)", value=float(g("strut_vert", 44.0)), step=1.0, key="sv")
            st.session_state.inp["strut_fuse_bl"] = st.number_input("Strut Fuselage BL (in)", value=float(g("strut_fuse_bl", 11.0)), step=1.0, key="sfbl")
            strut_mats = ["4130 Chromoly (normalized)","4130 Chromoly (heat treated)","6061-T6","2024-T3"]
            st.session_state.inp["strut_mat"]     = st.selectbox("Strut Material", strut_mats,
                index=strut_mats.index(g("strut_mat","4130 Chromoly (normalized)")), key="smat")
            st.session_state.inp["strut_tube_od"]  = st.number_input("Strut OD (in)", value=float(g("strut_tube_od", 2.0)), format="%.3f", key="sod")
            st.session_state.inp["strut_tube_wall"]= st.number_input("Strut Wall (in)", value=float(g("strut_tube_wall", 0.065)), format="%.4f", key="swall")

            st.session_state.inp["jury_strut"] = st.checkbox("Jury Strut (Euler brace only — no spar load)", value=bool(g("jury_strut", False)), key="jury")
            if g("jury_strut"):
                st.session_state.inp["jury_spar_bl"] = st.number_input("Jury BL (in)", value=float(g("jury_spar_bl", 48.0)), step=1.0, key="jbl")
                st.caption("Jury reduces main strut Euler buckling length. Does NOT affect spar deflection or moment.")

        st.session_state.inp["secondary_bending"] = st.checkbox("P-delta secondary bending", value=bool(g("secondary_bending", False)), key="pdelta")

# ═══════════════════════════════════════════════════════════
# TAB 3 — Front Spar
# ═══════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("Front Spar")
    SPAR_TYPES = ["Round Tube","Plain Rectangular","I-Beam","C-Channel",
                  "Double I-Beam","Box Spar","Routed (Monolithic)",
                  "Aluminum I-Beam","Aluminum C-Spar"]
    try:
        from spar_sections import MATERIAL_DB
        ALL_MATS  = list(MATERIAL_DB.keys())
        WOOD_MATS = [k for k,v in MATERIAL_DB.items() if v.get("is_wood")]
        METAL_MATS= [k for k,v in MATERIAL_DB.items() if not v.get("is_wood")]
    except:
        ALL_MATS = WOOD_MATS = METAL_MATS = ["6061-T6","2024-T3","Sitka Spruce","Birch Plywood"]

    stype = st.selectbox("Spar Type", SPAR_TYPES,
        index=SPAR_TYPES.index(g("front_spar_type","Round Tube")), key="f_stype")
    st.session_state.inp["front_spar_type"] = stype

    c1, c2 = st.columns(2)
    with c1:
        if stype == "Round Tube":
            # Use common_tube_spars.py — the right way
            tube_selector("front_spar", "Front Spar")

        elif stype == "Plain Rectangular":
            st.session_state.inp["front_spar_width"]   = st.number_input("Width (in)", value=float(g("front_spar_width", 2.0)), format="%.3f", key="f_w")
            st.session_state.inp["front_spar_height"]  = st.number_input("Height (in)", value=float(g("front_spar_height", 4.0)), format="%.3f", key="f_h")
            st.session_state.inp["front_spar_cap_mat"] = st.selectbox("Material", ALL_MATS,
                index=ALL_MATS.index(g("front_spar_cap_mat","Sitka Spruce")) if g("front_spar_cap_mat","Sitka Spruce") in ALL_MATS else 0, key="f_cm")

        elif stype == "Box Spar":
            st.session_state.inp["front_spar_b_outer"] = st.number_input("Outer Width (in)", value=float(g("front_spar_b_outer", 2.0)), format="%.3f", key="f_bo")
            st.session_state.inp["front_spar_h_outer"] = st.number_input("Outer Height (in)", value=float(g("front_spar_h_outer", 5.0)), format="%.3f", key="f_ho")
            st.session_state.inp["front_spar_t_web"]   = st.number_input("Web Thickness (in)", value=float(g("front_spar_t_web", 0.125)), format="%.4f", key="f_tw")
            st.session_state.inp["front_spar_t_cap"]   = st.number_input("Cap Thickness (in)", value=float(g("front_spar_t_cap", 0.75)), format="%.4f", key="f_tc")
            st.session_state.inp["front_spar_cap_mat"] = st.selectbox("Cap Material", ALL_MATS, key="f_cm")
            st.session_state.inp["front_spar_web_mat"] = st.selectbox("Web Material", ALL_MATS, key="f_wm")

        elif stype in ("Aluminum I-Beam","Aluminum C-Spar"):
            st.session_state.inp["front_spar_b_top"]   = st.number_input("Cap Width (in)", value=float(g("front_spar_b_top", 1.5)), format="%.3f", key="f_bt")
            st.session_state.inp["front_spar_t_top"]   = st.number_input("Cap Thickness (in)", value=float(g("front_spar_t_top", 0.125)), format="%.4f", key="f_tt")
            st.session_state.inp["front_spar_h_web"]   = st.number_input("Web Height (in)", value=float(g("front_spar_h_web", 5.0)), format="%.3f", key="f_hw")
            st.session_state.inp["front_spar_t_web"]   = st.number_input("Web Thickness (in)", value=float(g("front_spar_t_web", 0.050)), format="%.4f", key="f_tw")
            st.session_state.inp["front_spar_cap_mat"] = st.selectbox("Material", METAL_MATS, key="f_cm")
            st.session_state.inp["front_spar_web_mat"] = st.session_state.inp["front_spar_cap_mat"]
            total_h = float(g("front_spar_h_web", 5.0)) + float(g("front_spar_t_top", 0.125))
            st.caption(f"Total depth = {total_h:.3f}\"")

        else:  # I-Beam, C-Channel, Double I-Beam, Routed
            st.session_state.inp["front_spar_b_top"]   = st.number_input("Cap Width top (in)", value=float(g("front_spar_b_top", 1.5)), format="%.3f", key="f_bt")
            st.session_state.inp["front_spar_t_top"]   = st.number_input("Cap Height top (in)", value=float(g("front_spar_t_top", 0.75)), format="%.4f", key="f_tt")
            st.session_state.inp["front_spar_b_bot"]   = st.number_input("Cap Width bot (in)", value=float(g("front_spar_b_bot", 1.5)), format="%.3f", key="f_bb")
            st.session_state.inp["front_spar_t_bot"]   = st.number_input("Cap Height bot (in)", value=float(g("front_spar_t_bot", 0.75)), format="%.4f", key="f_tb")
            st.session_state.inp["front_spar_h_web"]   = st.number_input("Web Height (in)", value=float(g("front_spar_h_web", 4.5)), format="%.3f", key="f_hw")
            st.session_state.inp["front_spar_t_web"]   = st.number_input("Web Thickness (in)", value=float(g("front_spar_t_web", 0.125)), format="%.4f", key="f_tw")
            if stype == "Double I-Beam":
                st.session_state.inp["front_spar_web_spacing"] = st.number_input("Web Spacing (in)", value=float(g("front_spar_web_spacing", 1.0)), format="%.3f", key="f_ws")
            st.session_state.inp["front_spar_cap_mat"] = st.selectbox("Cap Material", ALL_MATS, key="f_cm")
            st.session_state.inp["front_spar_web_mat"] = st.selectbox("Web Material", ALL_MATS, key="f_wm")
            total_h = float(g("front_spar_h_web",4.5)) + float(g("front_spar_t_top",0.75)) + float(g("front_spar_t_bot",0.75))
            st.caption(f"Total depth = {total_h:.3f}\"")

    with c2:
        st.markdown("**Depth Check**")
        st.info(spar_depth_info("front"))

# ═══════════════════════════════════════════════════════════
# TAB 4 — Rear Spar
# ═══════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("Rear Spar")
    REAR_SPAR_TYPES = ["Round Tube","Plain Rectangular","I-Beam","Box Spar",
                       "Aluminum I-Beam","Aluminum C-Spar"]
    rstype = st.selectbox("Spar Type", REAR_SPAR_TYPES,
        index=REAR_SPAR_TYPES.index(g("rear_spar_type","Round Tube")) if g("rear_spar_type","Round Tube") in REAR_SPAR_TYPES else 0, key="r_stype")
    st.session_state.inp["rear_spar_type"] = rstype

    c1, c2 = st.columns(2)
    with c1:
        if rstype == "Round Tube":
            tube_selector("rear_spar", "Rear Spar")

        elif rstype == "Plain Rectangular":
            st.session_state.inp["rear_spar_width"]   = st.number_input("Width (in)", value=float(g("rear_spar_width", 1.5)), format="%.3f", key="r_w")
            st.session_state.inp["rear_spar_height"]  = st.number_input("Height (in)", value=float(g("rear_spar_height", 3.0)), format="%.3f", key="r_h")
            st.session_state.inp["rear_spar_cap_mat"] = st.selectbox("Material", ALL_MATS, key="r_cm")

        elif rstype == "Box Spar":
            st.session_state.inp["rear_spar_b_outer"] = st.number_input("Outer Width (in)", value=float(g("rear_spar_b_outer", 1.5)), format="%.3f", key="r_bo")
            st.session_state.inp["rear_spar_h_outer"] = st.number_input("Outer Height (in)", value=float(g("rear_spar_h_outer", 3.0)), format="%.3f", key="r_ho")
            st.session_state.inp["rear_spar_t_web"]   = st.number_input("Web Thickness (in)", value=float(g("rear_spar_t_web", 0.125)), format="%.4f", key="r_tw")
            st.session_state.inp["rear_spar_t_cap"]   = st.number_input("Cap Thickness (in)", value=float(g("rear_spar_t_cap", 0.5)), format="%.4f", key="r_tc")
            st.session_state.inp["rear_spar_cap_mat"] = st.selectbox("Cap Material", ALL_MATS, key="r_cm")
            st.session_state.inp["rear_spar_web_mat"] = st.selectbox("Web Material", ALL_MATS, key="r_wm")

        else:  # Aluminum I-Beam, Aluminum C-Spar, I-Beam
            st.session_state.inp["rear_spar_b_top"]   = st.number_input("Cap Width (in)", value=float(g("rear_spar_b_top", 1.0)), format="%.3f", key="r_bt")
            st.session_state.inp["rear_spar_t_top"]   = st.number_input("Cap Thickness (in)", value=float(g("rear_spar_t_top", 0.083)), format="%.4f", key="r_tt")
            st.session_state.inp["rear_spar_h_web"]   = st.number_input("Web Height (in)", value=float(g("rear_spar_h_web", 3.0)), format="%.3f", key="r_hw")
            st.session_state.inp["rear_spar_t_web"]   = st.number_input("Web Thickness (in)", value=float(g("rear_spar_t_web", 0.040)), format="%.4f", key="r_tw")
            st.session_state.inp["rear_spar_cap_mat"] = st.selectbox("Material", METAL_MATS if "Aluminum" in rstype else ALL_MATS, key="r_cm")
            st.session_state.inp["rear_spar_web_mat"] = st.session_state.inp["rear_spar_cap_mat"]
            total_h = float(g("rear_spar_h_web", 3.0)) + float(g("rear_spar_t_top", 0.083))
            st.caption(f"Total depth = {total_h:.3f}\"")

    with c2:
        st.markdown("**Depth Check**")
        st.info(spar_depth_info("rear"))

# ═══════════════════════════════════════════════════════════
# TAB 5 — Wing Structure
# ═══════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("Wing Structure")
    c1, c2 = st.columns(2)
    with c1:
        struct_types = ["fabric_tube","fabric_buildup","aluminum_skin"]
        st.session_state.inp["wing_structure_type"] = st.selectbox("Structure Type", struct_types,
            index=struct_types.index(g("wing_structure_type","fabric_tube")), key="wst")

        st.markdown("**D-Cell (Nose Box)**")
        st.session_state.inp["dcell_enabled"] = st.checkbox("D-Cell enabled", value=bool(g("dcell_enabled", False)), key="dce")
        if g("dcell_enabled"):
            st.session_state.inp["dcell_skin_mat"]   = st.selectbox("D-Cell Skin Material", ALL_MATS, key="dcsm")
            st.session_state.inp["dcell_skin_thick"] = st.number_input("D-Cell Skin Thickness (in)", value=float(g("dcell_skin_thick", 0.0625)), format="%.4f", key="dcst")

        st.markdown("**Geodetic Bracing**")
        st.session_state.inp["geodetic_enabled"] = st.checkbox("Geodetic enabled", value=bool(g("geodetic_enabled", False)), key="ge")
        if g("geodetic_enabled"):
            st.session_state.inp["geodetic_mat"]            = st.selectbox("Geodetic Material", WOOD_MATS if WOOD_MATS else ALL_MATS, key="gm")
            st.session_state.inp["geodetic_w"]              = st.number_input("Strip Width (in)", value=float(g("geodetic_w", 1.0)), format="%.3f", key="gw")
            st.session_state.inp["geodetic_t"]              = st.number_input("Strip Thickness (in)", value=float(g("geodetic_t", 0.125)), format="%.4f", key="gt")
            st.session_state.inp["geodetic_strips_per_bay"] = st.number_input("Strips per Bay", value=int(g("geodetic_strips_per_bay", 2)), min_value=1, key="gspb")
            st.session_state.inp["geodetic_angle"]          = st.number_input("Angle (°)", value=float(g("geodetic_angle", 45.0)), step=5.0, key="ga")

        if g("wing_structure_type") == "aluminum_skin":
            st.markdown("**Aluminum Skin**")
            st.session_state.inp["skin_top_mat"]   = st.selectbox("Top Skin Material", METAL_MATS if METAL_MATS else ALL_MATS, key="stm")
            st.session_state.inp["skin_top_thick"] = st.number_input("Top Skin Thickness (in)", value=float(g("skin_top_thick", 0.025)), format="%.4f", key="stt")
            st.session_state.inp["skin_bot_mat"]   = st.selectbox("Bottom Skin Material", METAL_MATS if METAL_MATS else ALL_MATS, key="sbm")
            st.session_state.inp["skin_bot_thick"] = st.number_input("Bottom Skin Thickness (in)", value=float(g("skin_bot_thick", 0.025)), format="%.4f", key="sbt")

    with c2:
        st.session_state.inp["wood_knockdown"] = st.number_input("Wood Knockdown Factor (0.75 = AC 43.13-1B)", value=float(g("wood_knockdown", 0.75)), format="%.3f", key="wkd")

        st.markdown("**Rib Structure (torsion transfer)**")
        st.session_state.inp["rib_h_web"] = st.number_input("Rib Web Height (in)", value=float(g("rib_h_web", 3.0)), format="%.3f", key="rhw")
        st.session_state.inp["rib_t_web"] = st.number_input("Rib Web Thickness (in)", value=float(g("rib_t_web", 0.125)), format="%.4f", key="rtw")
        st.session_state.inp["rib_b_cap"] = st.number_input("Rib Cap Width (in)", value=float(g("rib_b_cap", 0.75)), format="%.3f", key="rbc")
        st.session_state.inp["rib_t_cap"] = st.number_input("Rib Cap Thickness (in)", value=float(g("rib_t_cap", 0.125)), format="%.4f", key="rtc")
        st.session_state.inp["rib_mat"]   = st.selectbox("Rib Material", ALL_MATS, key="rm")

# ═══════════════════════════════════════════════════════════
# TAB 6 — Buckling
# ═══════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("Buckling Controls")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.inp["stiffener_spacing"] = st.number_input("Stiffener Spacing (in) [0=rib spacing]", value=float(g("stiffener_spacing", 0.0)), step=1.0, key="ss")
        st.session_state.inp["nose_rib_spacing"]  = st.number_input("Nose Rib Spacing (in) [0=rib spacing]", value=float(g("nose_rib_spacing", 0.0)), step=1.0, key="nrs")

# ═══════════════════════════════════════════════════════════
# TAB 7 — Results
# ═══════════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("Results Summary")
    if not st.session_state.result:
        st.info("Run analysis first (▶ Run Analysis in sidebar)")
    else:
        a   = st.session_state.result
        txt = a.summary_text()

        # KPI row
        kc1, kc2, kc3, kc4 = st.columns(4)
        ms_f = a.ms_front.get("MS_ult", 0)
        ms_r = a.ms_rear.get("MS_ult", 0) if a.rear_spar else None
        kc1.metric("Front Spar MS", f"{ms_f:+.2f}", delta="PASS" if ms_f >= 0 else "FAIL")
        if ms_r is not None:
            kc2.metric("Rear Spar MS", f"{ms_r:+.2f}", delta="PASS" if ms_r >= 0 else "FAIL")
        if a.torsion:
            import math as _m
            phi = _m.degrees(a.torsion.get("phi",[0])[0]) if hasattr(a.torsion.get("phi",[0]),"__len__") else 0
            kc3.metric("Wing Twist", f"{phi:.3f}°", delta="OK" if abs(phi) < 1 else "HIGH")
        if a.divergence:
            sf_div = a.divergence.get("SF_div", 0)
            kc4.metric("Divergence SF", f"{sf_div:.2f}", delta="OK" if sf_div > 1.5 else "LOW")

        st.divider()

        # Colour-coded results
        def line_emoji(line):
            if any(x in line for x in ["✗","*** FAIL","***","FAIL"]): return "🔴"
            if "✓" in line: return "🟢"
            if any(x in line for x in ["⚠","!! "]): return "🟡"
            return ""

        lines = txt.splitlines()
        mid   = len(lines) // 2 + 3
        tc1, tc2 = st.columns(2)
        for col, chunk in [(tc1, lines[:mid]), (tc2, lines[mid:])]:
            with col:
                for l in chunk:
                    em = line_emoji(l)
                    if em:
                        st.markdown(f"{em} `{l}`")
                    elif l.startswith(("══","──","--")):
                        st.markdown(f"**{l}**")
                    else:
                        st.text(l)

# ═══════════════════════════════════════════════════════════
# TAB 8 — Plots
# ═══════════════════════════════════════════════════════════
with tabs[8]:
    st.subheader("Analysis Plots")
    if not st.session_state.result:
        st.info("Run analysis first")
    else:
        a = st.session_state.result
        x = a.x

        fig, axes = plt.subplots(2, 2, figsize=(14, 8))
        fig.patch.set_facecolor("#1e2128")
        for ax in axes.flatten():
            ax.set_facecolor("#252930")
            ax.tick_params(colors="#B9BCC2")
            for sp in ax.spines.values(): sp.set_color("#6E7F87")

        ax1, ax2, ax3, ax4 = axes.flatten()

        ax1.plot(x, a.pos.get("w", x*0), color="#085097", lw=2, label=f"+{a.n:.0f}g")
        ax1.plot(x, a.neg.get("w", x*0), color="#D2B75F", lw=1.5, ls="--", label=f"{a.n_neg:.0f}g")
        ax1.set(title="Lift [lb/in]", xlabel="Span [in]"); ax1.title.set_color("#e8eaf0"); ax1.legend(fontsize=8); ax1.grid(True, alpha=0.3)

        ax2.plot(x, a.pos.get("V", x*0), color="#085097", lw=2, label=f"+{a.n:.0f}g")
        ax2.plot(x, a.neg.get("V", x*0), color="#D2B75F", lw=1.5, ls="--", label=f"{a.n_neg:.0f}g")
        ax2.set(title="Shear [lb]", xlabel="Span [in]"); ax2.title.set_color("#e8eaf0"); ax2.legend(fontsize=8); ax2.grid(True, alpha=0.3)

        ax3.plot(x, a.pos.get("M", x*0), color="#085097", lw=2, label=f"Frt +{a.n:.0f}g")
        ax3.plot(x, a.pos.get("M_rear", a.pos.get("M", x*0)), color="#B9BCC2", lw=1.5, label=f"Rr +{a.n:.0f}g")
        ax3.plot(x, a.neg.get("M", x*0), color="#D2B75F", lw=1.5, ls="--", label=f"Frt {a.n_neg:.0f}g")
        ax3.set(title="Moment [lb·in]", xlabel="Span [in]"); ax3.title.set_color("#e8eaf0"); ax3.legend(fontsize=8); ax3.grid(True, alpha=0.3)

        ax4.plot(x, a.pos.get("z_front", x*0), color="#085097", lw=2,   label="Frt +g")
        ax4.plot(x, a.pos.get("z_rear",  x*0), color="#B9BCC2", lw=1.5, label="Rr +g")
        ax4.plot(x, a.neg.get("z_front", x*0), color="#D2B75F", lw=1.5, ls="--", label="Frt -g")
        ax4.plot(x, a.neg.get("z_rear",  x*0), color="#E5C87A", lw=1,   ls="--", label="Rr -g")
        ax4.axhline(0, color="#555", lw=0.5)
        ax4.set(title="Deflection [in]", xlabel="Span [in]"); ax4.title.set_color("#e8eaf0"); ax4.legend(fontsize=8); ax4.grid(True, alpha=0.3)

        fig.tight_layout(pad=2.5)
        st.pyplot(fig)
        plt.close(fig)

        # Geometry
        st.subheader("Wing Geometry")
        fig2, (ax_top, ax_side) = plt.subplots(2, 1, figsize=(14, 7))
        fig2.patch.set_facecolor("#1e2128")
        try:
            a.draw_geometry(ax_top, ax_side)
        except Exception as e:
            ax_top.text(0.5, 0.5, f"Geometry: {e}", transform=ax_top.transAxes, ha="center")
        fig2.tight_layout(pad=2.5)
        st.pyplot(fig2)
        plt.close(fig2)

st.caption("AeroBeam v1.2 • Wing Stress Analysis")
