import streamlit as st
from wing_stress_analyzer import WingStressAnalyzer, DEFAULT_INPUTS

st.set_page_config(page_title="AeroBeam v1.2", page_icon="✈️", layout="wide")

st.title("✈️ AeroBeam v1.2")
st.caption("Wing Bending, Shear & Buckling Analysis — Streamlit Version")

# Sidebar
with st.sidebar:
    st.header("Analysis Controls")
    if st.button("▶ Run Analysis", type="primary", use_container_width=True):
        st.session_state.run_analysis = True
        st.rerun()
    st.divider()
    st.info("Streamlit version in development")

tab_names = ["Wing Geometry", "Flight & Airfoil", "Loads & Config",
             "Front Spar", "Rear Spar", "Wing Structure", "Buckling"]
tabs = st.tabs(tab_names)

# ======================
# Collect inputs (simplified)
# ======================
if "inputs" not in st.session_state:
    st.session_state.inputs = {}

# ======================
# TAB: Wing Geometry
# ======================
with tabs[0]:
    st.header("Wing Geometry")
    col1, col2 = st.columns(2)
    with col1:
        b = st.number_input("Total Span b (in)", value=320.0)
        r = st.number_input("Root Attach Offset r (in)", value=22.0)
        root_chord = st.number_input("Root Chord (in)", value=54.0)
        tip_chord = st.number_input("Tip Chord (in)", value=24.0)
    with col2:
        front_pct = st.slider("Front Spar % Chord", 0.05, 0.5, 0.15)
        rear_pct = st.slider("Rear Spar % Chord", 0.5, 0.95, 0.65)
    
    st.session_state.inputs.update({
        "b": b, "r": r, "root_chord": root_chord, "tip_chord": tip_chord,
        "front_spar_percent": front_pct, "rear_spar_percent": rear_pct
    })

# ======================
# TAB: Flight & Airfoil
# ======================
with tabs[1]:
    st.header("Flight & Airfoil")
    airfoil = st.selectbox("Airfoil", ["NACA 4412", "NACA 23012", "NACA 0012"])
    t_c = st.number_input("t/c", value=0.12)
    st.session_state.inputs.update({"airfoil": airfoil, "airfoil_t_c": t_c})

# ======================
# TAB: Loads & Config
# ======================
with tabs[2]:
    st.header("Loads & Configuration")
    weight = st.number_input("Gross Weight (lb)", value=1750.0)
    n = st.number_input("Load Factor (+g)", value=6.0)
    config = st.selectbox("Configuration", ["strut_braced", "cantilever", "single_strut"])
    st.session_state.inputs.update({"Weight": weight, "n": n, "config": config})

# ======================
# TAB: Front Spar
# ======================
with tabs[3]:
    st.header("Front Spar")
    od = st.number_input("Front Spar OD (in)", value=3.0)
    wall = st.number_input("Front Spar Wall (in)", value=0.065)
    st.session_state.inputs.update({"front_spar_od": od, "front_spar_wall": wall})

# ======================
# TAB: Rear Spar
# ======================
with tabs[4]:
    st.header("Rear Spar")
    od = st.number_input("Rear Spar OD (in)", value=2.0)
    wall = st.number_input("Rear Spar Wall (in)", value=0.065)
    st.session_state.inputs.update({"rear_spar_od": od, "rear_spar_wall": wall})

# ======================
# TAB: Wing Structure
# ======================
with tabs[5]:
    st.header("Wing Structure")
    struct_type = st.selectbox("Structure Type", 
                              ["fabric_tube", "fabric_buildup", "aluminum_skin"])
    st.session_state.inputs.update({"wing_structure_type": struct_type})

# ======================
# TAB: Buckling
# ======================
with tabs[6]:
    st.header("Buckling")
    stiffener = st.number_input("Web Stiffener Spacing (in)", value=0.0)
    st.session_state.inputs.update({"stiffener_spacing": stiffener})

# ======================
# RUN ANALYSIS (NOW CONNECTED)
# ======================
if st.session_state.get("run_analysis"):
    st.subheader("Analysis Results")
    
    try:
        # Merge user inputs with defaults
        full_inputs = dict(DEFAULT_INPUTS)
        full_inputs.update(st.session_state.inputs)
        
        # Run the analyzer
        analyzer = WingStressAnalyzer(full_inputs)
        analyzer.analyze()
        
        st.success("Analysis completed successfully!")
        
        # Show key metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Root Shear (lb)", f"{getattr(analyzer, 'V_root', 0):,.0f}")
        with col2:
            st.metric("Root Moment (lb-in)", f"{getattr(analyzer, 'M_root', 0):,.0f}")
        with col3:
            st.metric("Max Deflection (in)", f"{getattr(analyzer, 'z_max', 0):.3f}")
        
        # Show summary
        if hasattr(analyzer, "summary_text"):
            with st.expander("Full Analysis Summary"):
                st.text(analyzer.summary_text())
        
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
    
    st.session_state.run_analysis = False
