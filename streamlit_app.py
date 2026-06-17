import streamlit as st

st.set_page_config(
    page_title="AeroBeam v1.2",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ AeroBeam v1.2")
st.caption("Wing Bending, Shear & Buckling Analysis — Streamlit Version")

# Initialize session state for inputs
if "inputs" not in st.session_state:
    st.session_state.inputs = {}

# ======================
# Sidebar
# ======================
with st.sidebar:
    st.header("Analysis Controls")
    
    if st.button("▶ Run Analysis", type="primary", use_container_width=True):
        st.session_state.run_analysis = True
        st.rerun()
    
    st.divider()
    st.write("**Status:**")
    if st.session_state.get("run_analysis"):
        st.success("Analysis ready to run")
    else:
        st.info("Adjust inputs and click Run Analysis")

# ======================
# Main Tabs
# ======================
tab_names = [
    "Wing Geometry", 
    "Flight & Airfoil", 
    "Loads & Config",
    "Front Spar", 
    "Rear Spar", 
    "Wing Structure", 
    "Buckling"
]

tabs = st.tabs(tab_names)

# ======================
# TAB 1: Wing Geometry (NOW FUNCTIONAL)
# ======================
with tabs[0]:
    st.header("Wing Geometry")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Planform")
        b = st.number_input("Total Span b (in)", value=320.0, step=1.0)
        r = st.number_input("Root Attach Offset r (in)", value=22.0, step=1.0)
        root_chord = st.number_input("Root Chord (in)", value=54.0, step=1.0)
        tip_chord = st.number_input("Tip Chord (in)", value=24.0, step=1.0)
        taper_start = st.number_input("Taper Start BL (in)", value=0.0, step=1.0)
        rib_spacing = st.number_input("Rib Spacing (in)", value=12.0, step=0.5)
    
    with col2:
        st.subheader("Spar Positions")
        front_pct = st.slider("Front Spar % Chord", 0.05, 0.50, 0.15, 0.01)
        rear_pct = st.slider("Rear Spar % Chord", 0.50, 0.95, 0.65, 0.01)
        load_share = st.slider("Front Spar Load Share", 0.0, 1.0, 0.55, 0.05)
        
        st.subheader("Lift Distribution")
        lift_type = st.selectbox(
            "Distribution Type",
            ["schrenk", "elliptical", "chord_based", "uniform"],
            index=0
        )
        num_points = st.number_input("Analysis Stations", value=201, min_value=50, step=50)
    
    # Save inputs to session state
    st.session_state.inputs.update({
        "b": b,
        "r": r,
        "root_chord": root_chord,
        "tip_chord": tip_chord,
        "taper_start_bl": taper_start,
        "rib_spacing": rib_spacing,
        "front_spar_percent": front_pct,
        "rear_spar_percent": rear_pct,
        "front_spar_load_share": load_share,
        "lift_distribution_type": lift_type,
        "num_points": num_points
    })
    
    st.success("Wing Geometry inputs saved")

# ======================
# Other tabs (placeholders for now)
# ======================
with tabs[1]:
    st.header("Flight & Airfoil")
    st.info("Coming soon...")

with tabs[2]:
    st.header("Loads & Configuration")
    st.info("Coming soon...")

with tabs[3]:
    st.header("Front Spar")
    st.info("Coming soon... (Round Tube, I-Beam, Rectangular, etc.)")

with tabs[4]:
    st.header("Rear Spar")
    st.info("Coming soon...")

with tabs[5]:
    st.header("Wing Structure")
    st.info("Coming soon...")

with tabs[6]:
    st.header("Buckling")
    st.info("Coming soon...")

# ======================
# Analysis Trigger (placeholder)
# ======================
if st.session_state.get("run_analysis"):
    st.subheader("Analysis Results")
    st.write("**Current saved inputs:**")
    st.json(st.session_state.inputs)
    st.warning("Full analysis integration coming in the next step.")
    st.session_state.run_analysis = False