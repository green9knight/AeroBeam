"""
AeroBeam v1.2  —  Streamlit Web App
All input tabs wired, full analysis integration, results + plots.
"""
import streamlit as st
import numpy as np
import json, io, math

st.set_page_config(
    page_title="AeroBeam v1.2",
    page_icon="AeroBeam.ico",
    layout="wide"
)

# ── Import backend ────────────────────────────────────────────────────────────
try:
    from wing_stress_analyzer import WingStressAnalyzer, DEFAULT_INPUTS, dynamic_pressure_psi
    from spar_sections import MATERIAL_DB
    from airfoil_database import AIRFOIL_DB, airfoil_families, get_airfoil
    BACKEND_OK = True
except ImportError as e:
    BACKEND_OK = False
    IMPORT_ERR = str(e)

# ── Palette ───────────────────────────────────────────────────────────────────
PC_BLUE  = "#085097"
PC_GOLD  = "#D2B75F"
PC_GREEN = "#1a6e1a"
PC_RED   = "#cc0000"

# ── Session state init ────────────────────────────────────────────────────────
if "inp" not in st.session_state:
    st.session_state.inp = dict(DEFAULT_INPUTS) if BACKEND_OK else {}
if "result" not in st.session_state:
    st.session_state.result = None

def save_inp(key, val):
    st.session_state.inp[key] = val

def g(key, default=None):
    return st.session_state.inp.get(key, DEFAULT_INPUTS.get(key, default))

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="background:{PC_BLUE};padding:12px 20px;border-radius:6px;margin-bottom:12px">'
    page_icon="AeroBeam.ico" f'<span style="color:#D2B75F;font-size:1.6em;font-weight:700">AeroBeam v1.2</span>'
    f'<span style="color:#B9BCC2;font-size:0.9em;margin-left:16px">'
    f'Wing Bending · Shear · Buckling · Torsion</span></div>',
    unsafe_allow_html=True
)

if not BACKEND_OK:
    st.error(f"Backend import failed: {IMPORT_ERR}")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Controls")

    run = st.button("▶ Run Analysis", type="primary", use_container_width=True)

    st.divider()

    # File save/load
    st.subheader("Project File")
    up = st.file_uploader("Load .aerobeam", type=["aerobeam","json"])
    if up:
        data = json.load(up)
        # Merge: file wins, fall back to defaults for missing keys
        merged = dict(DEFAULT_INPUTS)
        for k, v in data.items():
            if k in ("dcell_enabled","geodetic_enabled","distribute_wing_weight",
                     "secondary_bending","jury_strut"):
                merged[k] = str(v).lower() in ("1","true","yes","true")
            elif isinstance(v, str):
                try:    merged[k] = float(v) if v.strip() else merged.get(k, v)
                except: merged[k] = v
            else:
                merged[k] = v
        lsf = merged.get("front_spar_load_share", 0.55)
        if isinstance(lsf, (int,float)) and lsf > 1.0:
            merged["front_spar_load_share"] = lsf / 100.0
        st.session_state.inp = merged
        st.success(f"Loaded: {up.name}")
        st.rerun()

    if st.button("💾 Save Project", use_container_width=True):
        data = dict(st.session_state.inp)
        data["num_spars"] = 2
        buf = io.BytesIO(json.dumps(data, indent=2, default=str).encode())
        st.download_button("⬇ Download .aerobeam", buf,
                           file_name="aerobeam_project.aerobeam",
                           mime="application/json")

    st.divider()
    if st.session_state.result:
        a = st.session_state.result
        ms_f = a.ms_front.get("MS_ult", 0)
        ms_r = a.ms_rear.get("MS_ult", 0) if a.rear_spar else None
        colour = PC_GREEN if ms_f >= 0 else PC_RED
        st.markdown(f'<span style="color:{colour}">Front MS: {ms_f:+.2f}</span>',
                    unsafe_allow_html=True)
        if ms_r is not None:
            colour_r = PC_GREEN if ms_r >= 0 else PC_RED
            st.markdown(f'<span style="color:{colour_r}">Rear MS:  {ms_r:+.2f}</span>',
                        unsafe_allow_html=True)

# ── Main tabs ─────────────────────────────────────────────────────────────────
inp = st.session_state.inp  # live reference

TAB_NAMES = ["🔷 Wing Geometry","✈ Flight & Airfoil","⚖ Loads & Config",
             "🔩 Front Spar","🔩 Rear Spar","🏗 Wing Structure","📐 Buckling",
             "📊 Results","📈 Plots"]
tabs = st.tabs(TAB_NAMES)

# ═══════════════════════════════════════════════════════════
# TAB 0 — Wing Geometry
# ═══════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("Wing Geometry")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Planform**")
        inp["b"]               = st.number_input("Total Span b (in)", value=float(g("b")), step=1.0, key="b")
        inp["r"]               = st.number_input("Root Attach Offset r — BL of root fitting (in)", value=float(g("r")), step=1.0, key="r")
        inp["root_chord"]      = st.number_input("Root Chord (in)", value=float(g("root_chord")), step=1.0, key="root_chord")
        inp["tip_chord"]       = st.number_input("Tip Chord (in)", value=float(g("tip_chord")), step=1.0, key="tip_chord")
        inp["taper_start_bl"]  = st.number_input("Taper Start BL (in)  [0 = taper from root]", value=float(g("taper_start_bl",0.0)), step=1.0, key="taper_start_bl")
        inp["rib_spacing"]     = st.number_input("Rib Spacing (in)", value=float(g("rib_spacing")), step=0.5, key="rib_spacing")
        inp["num_points"]      = st.number_input("Analysis Stations", value=int(g("num_points",201)), step=50, min_value=50, key="num_points")

    with c2:
        st.markdown("**Spar Positions**")
        inp["front_spar_percent"] = st.slider("Front Spar % Chord", 0.05, 0.50, float(g("front_spar_percent")), 0.01, key="fsp")
        inp["rear_spar_percent"]  = st.slider("Rear Spar % Chord",  0.50, 0.95, float(g("rear_spar_percent")),  0.01, key="rsp")
        inp["front_spar_load_share"] = st.slider("Front Spar Load Share", 0.0, 1.0, float(g("front_spar_load_share")), 0.05, key="lsf")
        st.caption(f"Rear spar load share = {1-float(g('front_spar_load_share')):.2f}")

        st.markdown("**Lift Distribution**")
        inp["lift_distribution_type"] = st.selectbox(
            "Distribution Type",
            ["schrenk","elliptical","chord_based","uniform"],
            index=["schrenk","elliptical","chord_based","uniform"].index(g("lift_distribution_type","schrenk")),
            key="ldt")

    # Live airfoil depth preview
    t_c = float(g("airfoil_t_c", 0.12))
    chord = float(g("root_chord"))
    fp = float(g("front_spar_percent"))
    rp = float(g("rear_spar_percent"))
    def naca_depth(xc, tc, ch):
        y = 5*tc*(0.2969*math.sqrt(max(xc,1e-9))-0.1260*xc-0.3516*xc**2+0.2843*xc**3-0.1015*xc**4)
        return 2*y*ch
    d_f = naca_depth(fp, t_c, chord)
    d_r = naca_depth(rp, t_c, chord)
    st.info(f"Airfoil depth at spars (t/c={t_c:.3f}, chord={chord:.0f}\"): "
            f"**Front {fp*100:.0f}%→ {d_f:.2f}\"** | **Rear {rp*100:.0f}%→ {d_r:.2f}\"**")

# ═══════════════════════════════════════════════════════════
# TAB 1 — Flight & Airfoil
# ═══════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Flight & Airfoil")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Airfoil Selection**")
        fams = ["(All)"] + airfoil_families()
        fam = st.selectbox("Family filter", fams, key="af_fam")
        search = st.text_input("Search airfoil name", key="af_search")
        # Filter
        all_names = [k for k in AIRFOIL_DB if k != "Manual Entry"]
        if fam != "(All)":
            all_names = [n for n in all_names if AIRFOIL_DB[n].get("family","") == fam]
        if search:
            all_names = [n for n in all_names if search.lower() in n.lower()]
        all_names = all_names[:300]
        cur = g("airfoil","NACA 4412")
        idx = all_names.index(cur) if cur in all_names else 0
        selected = st.selectbox("Airfoil", all_names, index=idx, key="af_sel")
        if st.button("Apply airfoil data"):
            af = get_airfoil(selected)
            if af:
                inp["airfoil"]    = selected
                inp["airfoil_t_c"] = af.get("t_c") or g("airfoil_t_c")
                inp["Cm_ac"]      = af.get("Cm_ac") or g("Cm_ac")
                inp["Cl_alpha"]   = af.get("Cl_alpha") or g("Cl_alpha")
                inp["x_ac_c"]     = af.get("x_ac_c") or g("x_ac_c")
                st.success(f"Applied: {selected}  t/c={inp['airfoil_t_c']:.4f}  Cm={inp['Cm_ac']:.4f}")
                st.rerun()

        st.markdown("**Aerodynamic Parameters**")
        inp["Cm_ac"]      = st.number_input("Cm_ac (pitching moment)", value=float(g("Cm_ac")), format="%.4f", key="cm_ac")
        inp["Cm_flap"]    = st.number_input("ΔCm full flap (add to Cm_ac)", value=float(g("Cm_flap",0.0)), format="%.4f", key="cm_flap")
        inp["Cl_alpha"]   = st.number_input("Cl_alpha (per radian)", value=float(g("Cl_alpha")), format="%.3f", key="cl_alpha")
        inp["x_ac_c"]     = st.number_input("AC position (x/c)", value=float(g("x_ac_c")), format="%.4f", key="xac")
        inp["airfoil_t_c"]= st.number_input("t/c (thickness ratio)", value=float(g("airfoil_t_c")), format="%.4f", key="tc")

    with c2:
        st.markdown("**Flight Speeds**")
        inp["Vd_mph"]      = st.number_input("Design Dive Speed Vd (mph)", value=float(g("Vd_mph")), step=1.0, key="vd")
        inp["Vc_mph"]      = st.number_input("Cruise Speed Vc (mph)", value=float(g("Vc_mph",80.0)), step=1.0, key="vc")
        inp["Va_mph"]      = st.number_input("Manoeuvre Speed Va (mph)", value=float(g("Va_mph",60.0)), step=1.0, key="va")
        inp["altitude_ft"] = st.number_input("Altitude (ft)", value=float(g("altitude_ft")), step=500.0, key="alt")

        q = dynamic_pressure_psi(float(g("Vd_mph")), float(g("altitude_ft")))
        st.info(f"Dynamic pressure at Vd: **q = {q:.4f} psi**")

# ═══════════════════════════════════════════════════════════
# TAB 2 — Loads & Config
# ═══════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("Loads & Configuration")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Loads**")
        inp["ng_lift"]   = st.number_input("Semi-span Design Lift ng_lift (lb)", value=float(g("ng_lift")), step=10.0, key="ngl")
        inp["n"]         = st.number_input("Positive Load Factor n (ultimate)", value=float(g("n")), step=0.5, key="n_pos")
        inp["n_neg"]     = st.number_input("Negative Load Factor n_neg", value=float(g("n_neg")), step=0.5, key="n_neg")
        inp["Weight"]    = st.number_input("Gross Weight (lb)", value=float(g("Weight")), step=10.0, key="weight")
        inp["Wing_Weight"]= st.number_input("Wing Weight one side (lb)", value=float(g("Wing_Weight")), step=5.0, key="ww")
        inp["Tail_Down_1g"]= st.number_input("Tail Down Load 1g (lb)", value=float(g("Tail_Down_1g")), step=5.0, key="tdl")
        inp["distribute_wing_weight"] = st.checkbox("Distribute wing weight (inertia relief)", value=bool(g("distribute_wing_weight",False)), key="dww")

    with c2:
        st.markdown("**Structural Configuration**")
        cfg_opts = ["strut_braced","single_strut","cantilever"]
        inp["config"] = st.selectbox("Config", cfg_opts,
            index=cfg_opts.index(g("config","strut_braced")), key="cfg")

        if g("config") != "cantilever":
            inp["strut_bl"]      = st.number_input("Strut BL (in)", value=float(g("strut_bl")), step=1.0, key="sbl")
            inp["strut_vert"]    = st.number_input("Strut Vertical Rise (in)", value=float(g("strut_vert")), step=1.0, key="sv")
            inp["strut_fuse_bl"] = st.number_input("Strut Fuselage BL (in)", value=float(g("strut_fuse_bl",0.0)), step=1.0, key="sfbl")
            strut_mats = ["4130 Chromoly (normalized)","4130 Chromoly (heat treated)","6061-T6","2024-T3"]
            inp["strut_mat"]     = st.selectbox("Strut Material", strut_mats,
                index=strut_mats.index(g("strut_mat","4130 Chromoly (normalized)")), key="smat")
            inp["strut_tube_od"] = st.number_input("Strut OD (in)", value=float(g("strut_tube_od")), format="%.3f", key="sod")
            inp["strut_tube_wall"]= st.number_input("Strut Wall (in)", value=float(g("strut_tube_wall")), format="%.4f", key="swall")
            inp["jury_strut"]    = st.checkbox("Jury Strut", value=bool(g("jury_strut",False)), key="jury")
            if g("jury_strut"):
                inp["jury_spar_bl"] = st.number_input("Jury BL (in)", value=float(g("jury_spar_bl",60.0)), key="jbl")
        inp["secondary_bending"] = st.checkbox("P-delta secondary bending", value=bool(g("secondary_bending",False)), key="pdelta")

# ═══════════════════════════════════════════════════════════
# TAB 3 — Front Spar
# ═══════════════════════════════════════════════════════════
SPAR_TYPES = ["Round Tube","I-Beam","C-Channel","Double I-Beam","Box Spar",
              "Routed (Monolithic)","Aluminum I-Beam","Aluminum C-Spar","Plain Rectangular"]
WOOD_MATS  = [k for k,v in MATERIAL_DB.items() if v.get("is_wood")]
METAL_MATS = [k for k,v in MATERIAL_DB.items() if not v.get("is_wood")]
ALL_MATS   = list(MATERIAL_DB.keys())

def spar_ui(prefix, tab_ref, label):
    with tab_ref:
        st.subheader(label)
        c1, c2 = st.columns(2)
        with c1:
            stype = st.selectbox("Spar Type", SPAR_TYPES,
                index=SPAR_TYPES.index(g(f"{prefix}_type","Round Tube")), key=f"{prefix}_type_sel")
            inp[f"{prefix}_type"] = stype

            if stype == "Round Tube":
                inp[f"{prefix}_od"]   = st.number_input("OD (in)", value=float(g(f"{prefix}_od",2.0)), format="%.4f", key=f"{prefix}_od")
                inp[f"{prefix}_wall"] = st.number_input("Wall (in)", value=float(g(f"{prefix}_wall",0.065)), format="%.4f", key=f"{prefix}_wall")
                inp[f"{prefix}_mat"]  = st.selectbox("Material", ALL_MATS,
                    index=ALL_MATS.index(g(f"{prefix}_mat","6061-T6")), key=f"{prefix}_mat")
                OD = float(g(f"{prefix}_od",2.0)); W = float(g(f"{prefix}_wall",0.065))
                st.caption(f"ID = {OD-2*W:.4f}\"  A = {math.pi/4*((OD)**2-(OD-2*W)**2):.4f} in²")

            elif stype == "Plain Rectangular":
                inp[f"{prefix}_width"]  = st.number_input("Width (in)", value=float(g(f"{prefix}_width",2.0)), format="%.3f", key=f"{prefix}_w")
                inp[f"{prefix}_height"] = st.number_input("Height (in)", value=float(g(f"{prefix}_height",4.0)), format="%.3f", key=f"{prefix}_h")
                inp[f"{prefix}_cap_mat"]= st.selectbox("Material", ALL_MATS,
                    index=ALL_MATS.index(g(f"{prefix}_cap_mat","Sitka Spruce")), key=f"{prefix}_cm")

            elif stype == "Box Spar":
                inp[f"{prefix}_b_outer"] = st.number_input("Outer Width (in)", value=float(g(f"{prefix}_b_outer",2.0)), format="%.3f", key=f"{prefix}_bo")
                inp[f"{prefix}_h_outer"] = st.number_input("Outer Height (in)", value=float(g(f"{prefix}_h_outer",5.0)), format="%.3f", key=f"{prefix}_ho")
                inp[f"{prefix}_t_web"]   = st.number_input("Web Thickness (in)", value=float(g(f"{prefix}_t_web",0.125)), format="%.4f", key=f"{prefix}_tw")
                inp[f"{prefix}_t_cap"]   = st.number_input("Cap/Flange Thickness (in)", value=float(g(f"{prefix}_t_cap",0.75)), format="%.4f", key=f"{prefix}_tc")
                inp[f"{prefix}_cap_mat"] = st.selectbox("Cap Material", ALL_MATS,
                    index=ALL_MATS.index(g(f"{prefix}_cap_mat","Sitka Spruce")), key=f"{prefix}_cm")
                inp[f"{prefix}_web_mat"] = st.selectbox("Web Material", ALL_MATS,
                    index=ALL_MATS.index(g(f"{prefix}_web_mat","Birch Plywood")), key=f"{prefix}_wm")

            elif stype in ("Aluminum I-Beam","Aluminum C-Spar"):
                inp[f"{prefix}_b_top"]   = st.number_input("Cap Width (in)", value=float(g(f"{prefix}_b_top",1.5)), format="%.3f", key=f"{prefix}_bt")
                inp[f"{prefix}_t_top"]   = st.number_input("Cap Thickness (in)", value=float(g(f"{prefix}_t_top",0.125)), format="%.4f", key=f"{prefix}_tt")
                inp[f"{prefix}_h_web"]   = st.number_input("Web Height (in)", value=float(g(f"{prefix}_h_web",5.0)), format="%.3f", key=f"{prefix}_hw")
                inp[f"{prefix}_t_web"]   = st.number_input("Web Thickness (in)", value=float(g(f"{prefix}_t_web",0.050)), format="%.4f", key=f"{prefix}_tw")
                inp[f"{prefix}_cap_mat"] = st.selectbox("Material", METAL_MATS,
                    index=METAL_MATS.index(g(f"{prefix}_cap_mat","6061-T6")) if g(f"{prefix}_cap_mat","6061-T6") in METAL_MATS else 0, key=f"{prefix}_cm")
                inp[f"{prefix}_web_mat"] = inp[f"{prefix}_cap_mat"]
                if stype == "Aluminum C-Spar":
                    inp[f"{prefix}_cap_side"] = st.selectbox("Cap Side", ["top","bottom"],
                        index=0 if g(f"{prefix}_cap_side","top")=="top" else 1, key=f"{prefix}_cs")
                total_h = float(g(f"{prefix}_h_web",5.0)) + float(g(f"{prefix}_t_top",0.125))
                st.caption(f"Total spar depth = {total_h:.3f}\" (cap + web, no bottom cap)")

            else:  # I-Beam, C-Channel, Double I-Beam, Routed
                inp[f"{prefix}_b_top"] = st.number_input("Cap Width top (in)", value=float(g(f"{prefix}_b_top",1.5)), format="%.3f", key=f"{prefix}_bt")
                inp[f"{prefix}_t_top"] = st.number_input("Cap Height top (in)", value=float(g(f"{prefix}_t_top",0.75)), format="%.4f", key=f"{prefix}_tt")
                inp[f"{prefix}_b_bot"] = st.number_input("Cap Width bot (in)", value=float(g(f"{prefix}_b_bot",1.5)), format="%.3f", key=f"{prefix}_bb")
                inp[f"{prefix}_t_bot"] = st.number_input("Cap Height bot (in)", value=float(g(f"{prefix}_t_bot",0.75)), format="%.4f", key=f"{prefix}_tb")
                inp[f"{prefix}_h_web"] = st.number_input("Web Height (in)", value=float(g(f"{prefix}_h_web",4.5)), format="%.3f", key=f"{prefix}_hw")
                inp[f"{prefix}_t_web"] = st.number_input("Web Thickness (in)", value=float(g(f"{prefix}_t_web",0.125)), format="%.4f", key=f"{prefix}_tw")
                if stype == "Double I-Beam":
                    inp[f"{prefix}_web_spacing"] = st.number_input("Web Spacing (in)", value=float(g(f"{prefix}_web_spacing",1.0)), format="%.3f", key=f"{prefix}_ws")
                is_metal_type = stype in ("C-Channel",)
                mat_list = METAL_MATS if is_metal_type else ALL_MATS
                inp[f"{prefix}_cap_mat"] = st.selectbox("Cap Material", mat_list,
                    index=mat_list.index(g(f"{prefix}_cap_mat","Sitka Spruce")) if g(f"{prefix}_cap_mat","Sitka Spruce") in mat_list else 0, key=f"{prefix}_cm")
                inp[f"{prefix}_web_mat"] = st.selectbox("Web Material", ALL_MATS,
                    index=ALL_MATS.index(g(f"{prefix}_web_mat","Birch Plywood")), key=f"{prefix}_wm")
                total_h = float(g(f"{prefix}_h_web",4.5)) + float(g(f"{prefix}_t_top",0.75)) + float(g(f"{prefix}_t_bot",0.75))
                st.caption(f"Total spar depth = {total_h:.3f}\"")

        with c2:
            st.markdown("**Web Doublers**")
            inp[f"{prefix}_doubler_t"]      = st.number_input("Doubler Thickness (in) [0=none]", value=float(g(f"{prefix}_doubler_t",0.0)), format="%.4f", key=f"{prefix}_dt")
            inp[f"{prefix}_doubler_extent"]  = st.number_input("Doubler Extent (rib bays)", value=int(g(f"{prefix}_doubler_extent",1)), min_value=0, step=1, key=f"{prefix}_de")

spar_ui("front_spar", tabs[3], "Front Spar")
spar_ui("rear_spar",  tabs[4], "Rear Spar")

# ═══════════════════════════════════════════════════════════
# TAB 5 — Wing Structure
# ═══════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("Wing Structure")
    c1, c2 = st.columns(2)

    with c1:
        struct_types = ["fabric_tube","fabric_buildup","aluminum_skin"]
        inp["wing_structure_type"] = st.selectbox("Structure Type", struct_types,
            index=struct_types.index(g("wing_structure_type","fabric_tube")), key="wst")

        st.markdown("**D-Cell (Nose Box)**")
        inp["dcell_enabled"] = st.checkbox("D-Cell enabled", value=bool(g("dcell_enabled",False)), key="dce")
        if g("dcell_enabled"):
            inp["dcell_skin_mat"]   = st.selectbox("D-Cell Skin Material", ALL_MATS,
                index=ALL_MATS.index(g("dcell_skin_mat","Birch Plywood")), key="dcsm")
            inp["dcell_skin_thick"] = st.number_input("D-Cell Skin Thickness (in)", value=float(g("dcell_skin_thick",0.0625)), format="%.4f", key="dcst")

        st.markdown("**Geodetic Bracing**")
        inp["geodetic_enabled"] = st.checkbox("Geodetic enabled", value=bool(g("geodetic_enabled",False)), key="ge")
        if g("geodetic_enabled"):
            inp["geodetic_mat"]         = st.selectbox("Geodetic Material", WOOD_MATS,
                index=WOOD_MATS.index(g("geodetic_mat","Sitka Spruce")) if g("geodetic_mat","Sitka Spruce") in WOOD_MATS else 0, key="gm")
            inp["geodetic_w"]           = st.number_input("Strip Width (in)", value=float(g("geodetic_w",1.0)), format="%.3f", key="gw")
            inp["geodetic_t"]           = st.number_input("Strip Thickness (in)", value=float(g("geodetic_t",0.125)), format="%.4f", key="gt")
            inp["geodetic_strips_per_bay"] = st.number_input("Strips per Bay", value=int(g("geodetic_strips_per_bay",2)), min_value=1, key="gspb")
            inp["geodetic_angle"]       = st.number_input("Angle (°)", value=float(g("geodetic_angle",45.0)), step=5.0, key="ga")

        if g("wing_structure_type") == "aluminum_skin":
            st.markdown("**Aluminum Skin**")
            inp["skin_top_mat"]   = st.selectbox("Top Skin Material", METAL_MATS,
                index=METAL_MATS.index(g("skin_top_mat","6061-T6")) if g("skin_top_mat","6061-T6") in METAL_MATS else 0, key="stm")
            inp["skin_top_thick"] = st.number_input("Top Skin Thickness (in)", value=float(g("skin_top_thick",0.025)), format="%.4f", key="stt")
            inp["skin_bot_mat"]   = st.selectbox("Bottom Skin Material", METAL_MATS,
                index=METAL_MATS.index(g("skin_bot_mat","6061-T6")) if g("skin_bot_mat","6061-T6") in METAL_MATS else 0, key="sbm")
            inp["skin_bot_thick"] = st.number_input("Bottom Skin Thickness (in)", value=float(g("skin_bot_thick",0.025)), format="%.4f", key="sbt")

    with c2:
        st.markdown("**Wood Knockdown**")
        inp["wood_knockdown"] = st.number_input("Wood Knockdown Factor (0.75 = AC 43.13-1B)", value=float(g("wood_knockdown",0.75)), format="%.3f", key="wkd")

        st.markdown("**Rib Structure (torsion transfer)**")
        inp["rib_h_web"] = st.number_input("Rib Web Height (in)", value=float(g("rib_h_web",3.0)), format="%.3f", key="rhw")
        inp["rib_t_web"] = st.number_input("Rib Web Thickness (in)", value=float(g("rib_t_web",0.125)), format="%.4f", key="rtw")
        inp["rib_b_cap"] = st.number_input("Rib Cap Width (in)", value=float(g("rib_b_cap",0.75)), format="%.3f", key="rbc")
        inp["rib_t_cap"] = st.number_input("Rib Cap Thickness (in)", value=float(g("rib_t_cap",0.125)), format="%.4f", key="rtc")
        inp["rib_mat"]   = st.selectbox("Rib Material", ALL_MATS,
            index=ALL_MATS.index(g("rib_mat","Birch Plywood")), key="rm")

# ═══════════════════════════════════════════════════════════
# TAB 6 — Buckling
# ═══════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("Buckling Controls")
    c1, c2 = st.columns(2)
    with c1:
        inp["stiffener_spacing"] = st.number_input("Stiffener Spacing (in) [0=rib spacing]", value=float(g("stiffener_spacing",0.0)), step=1.0, key="ss")
        inp["nose_rib_spacing"]  = st.number_input("Nose Rib Spacing (in) [0=rib spacing]", value=float(g("nose_rib_spacing",0.0)), step=1.0, key="nrs")
    with c2:
        inp["front_spar_doubler_t"]       = st.number_input("Front Spar Doubler Thickness (in)", value=float(g("front_spar_doubler_t",0.0)), format="%.4f", key="fsdt")
        inp["front_spar_doubler_extent"]  = st.number_input("Front Doubler Extent (rib bays)", value=int(g("front_spar_doubler_extent",1)), min_value=0, key="fsde")
        inp["rear_spar_doubler_t"]        = st.number_input("Rear Spar Doubler Thickness (in)", value=float(g("rear_spar_doubler_t",0.0)), format="%.4f", key="rsdt")
        inp["rear_spar_doubler_extent"]   = st.number_input("Rear Doubler Extent (rib bays)", value=int(g("rear_spar_doubler_extent",1)), min_value=0, key="rsde")

# ═══════════════════════════════════════════════════════════
# RUN ANALYSIS
# ═══════════════════════════════════════════════════════════
if run:
    with st.spinner("Analysing…"):
        try:
            inp["num_spars"] = 2
            a = WingStressAnalyzer(dict(inp))
            a.analyze()
            st.session_state.result = a
            st.session_state.result_summary = a.summary_text()
        except Exception as e:
            st.session_state.result = None
            st.error(f"Analysis error: {e}")
            import traceback; st.code(traceback.format_exc())

# ═══════════════════════════════════════════════════════════
# TAB 7 — Results
# ═══════════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("Results Summary")
    if not st.session_state.result:
        st.info("Run analysis first (▶ Run Analysis in sidebar)")
    else:
        a = st.session_state.result
        txt = st.session_state.result_summary

        # Colour-coded line rendering
        def ms_colour(line):
            if "✗" in line or "*** FAIL" in line or "***" in line: return "🔴"
            if "✓" in line: return "🟢"
            if "⚠" in line or "!! " in line: return "🟡"
            return ""

        # Top KPIs
        kc1,kc2,kc3,kc4 = st.columns(4)
        ms_f = a.ms_front.get("MS_ult",0)
        ms_r = a.ms_rear.get("MS_ult",0) if a.rear_spar else None
        kc1.metric("Front Spar MS", f"{ms_f:+.2f}", delta="PASS" if ms_f>=0 else "FAIL")
        if ms_r is not None:
            kc2.metric("Rear Spar MS",  f"{ms_r:+.2f}", delta="PASS" if ms_r>=0 else "FAIL")
        if a.torsion:
            phi = math.degrees(a.torsion["phi"][0])
            kc3.metric("Wing Twist", f"{phi:.3f}°", delta="OK" if abs(phi)<1 else "HIGH")
        if a.divergence:
            sf_div = a.divergence.get("SF_div",0)
            kc4.metric("Divergence SF", f"{sf_div:.2f}", delta="OK" if sf_div>1.5 else "LOW")

        st.divider()

        # Two-column text display
        lines = txt.splitlines()
        mid = len(lines)//2 + 3
        tc1, tc2 = st.columns(2)
        with tc1:
            for l in lines[:mid]:
                em = ms_colour(l)
                if em:
                    st.markdown(f"{em} `{l}`")
                elif l.startswith("══") or l.startswith("──") or l.startswith("--"):
                    st.markdown(f"**{l}**")
                else:
                    st.text(l)
        with tc2:
            for l in lines[mid:]:
                em = ms_colour(l)
                if em:
                    st.markdown(f"{em} `{l}`")
                elif l.startswith("══") or l.startswith("──") or l.startswith("--"):
                    st.markdown(f"**{l}**")
                else:
                    st.text(l)

        # PDF export
        st.divider()
        if st.button("Generate PDF Report"):
            buf = io.BytesIO()
            a.export_pdf(buf)
            buf.seek(0)
            st.download_button("⬇ Download PDF", buf, file_name="AeroBeam_Report.pdf", mime="application/pdf")

# ═══════════════════════════════════════════════════════════
# TAB 8 — Plots
# ═══════════════════════════════════════════════════════════
with tabs[8]:
    st.subheader("Analysis Plots")
    if not st.session_state.result:
        st.info("Run analysis first")
    else:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        a = st.session_state.result
        x = a.x

        fig, axes = plt.subplots(2, 2, figsize=(14, 8))
        fig.patch.set_facecolor("#1e2128")
        for ax in axes.flatten():
            ax.set_facecolor("#252930")
            ax.tick_params(colors="#B9BCC2", labelcolor="#e8eaf0")
            ax.spines[:].set_color("#6E7F87")

        ax1,ax2,ax3,ax4 = axes.flatten()

        ax1.plot(x, a.pos["w"], color="#085097", lw=2, label=f"+{a.n:.0f}g")
        ax1.plot(x,-a.neg["w"],color="#D2B75F", lw=1.5, ls="--", label=f"{a.n_neg:.0f}g")
        ax1.set(title="Lift [lb/in]", xlabel="Span [in]")
        ax1.title.set_color("#e8eaf0"); ax1.xaxis.label.set_color("#e8eaf0")
        ax1.legend(fontsize=8); ax1.grid(True, alpha=0.3)

        ax2.plot(x, a.pos["V"], color="#085097", lw=2, label=f"+{a.n:.0f}g")
        ax2.plot(x, a.neg["V"],color="#D2B75F", lw=1.5, ls="--", label=f"{a.n_neg:.0f}g")
        ax2.set(title="Shear [lb]", xlabel="Span [in]")
        ax2.title.set_color("#e8eaf0"); ax2.xaxis.label.set_color("#e8eaf0")
        ax2.legend(fontsize=8); ax2.grid(True, alpha=0.3)

        ax3.plot(x, a.pos["M"], color="#085097", lw=2, label=f"+{a.n:.0f}g")
        ax3.plot(x, a.neg["M"],color="#D2B75F", lw=1.5, ls="--", label=f"{a.n_neg:.0f}g")
        ax3.set(title="Moment [lb·in]", xlabel="Span [in]")
        ax3.title.set_color("#e8eaf0"); ax3.xaxis.label.set_color("#e8eaf0")
        ax3.legend(fontsize=8); ax3.grid(True, alpha=0.3)

        ax4.plot(x, a.pos["z_front"], color="#085097", lw=2,   label="Frt +g")
        ax4.plot(x, a.pos["z_rear"],  color="#B9BCC2", lw=1.5, label="Rr +g")
        ax4.plot(x, a.neg["z_front"], color="#D2B75F", lw=1.5, ls="--", label="Frt -g")
        ax4.plot(x, a.neg["z_rear"],  color="#E5C87A", lw=1,   ls="--", label="Rr -g")
        ax4.axhline(y=0, color="#555", lw=0.5)
        ax4.set(title="Deflection [in]", xlabel="Span [in]")
        ax4.title.set_color("#e8eaf0"); ax4.xaxis.label.set_color("#e8eaf0")
        ax4.legend(fontsize=8); ax4.grid(True, alpha=0.3)

        if a.torsion:
            import numpy as np
            ax1_twin = ax1.twinx()
            ax1_twin.plot(x, np.degrees(a.torsion["phi"]),
                          color="#ffa500", lw=1, ls=":", alpha=0.8)
            ax1_twin.set_ylabel("Twist [°]", fontsize=7, color="orange")
            ax1_twin.tick_params(labelsize=7, colors="orange")
            ax1_twin.yaxis.label.set_color("orange")

        fig.tight_layout(pad=2.5)
        st.pyplot(fig)
        plt.close(fig)

        # Geometry plot
        st.subheader("Wing Geometry")
        fig2, (ax_top, ax_side) = plt.subplots(2, 1, figsize=(14, 7))
        fig2.patch.set_facecolor("#1e2128")
        a.draw_geometry(ax_top, ax_side)
        fig2.tight_layout(pad=2.5)
        st.pyplot(fig2)
        plt.close(fig2)
