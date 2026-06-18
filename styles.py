"""
styles.py
Targeted CSS improvements following modern Streamlit theming practices.
Does NOT affect matplotlib or PDF output.
"""

import streamlit as st

def apply_modern_theme():
    css = """
    <style>
    /* Improve overall spacing and card look */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    /* Make input fields and selects cleaner */
    .stTextInput, .stNumberInput, .stSelectbox, .stSlider {
        margin-bottom: 0.6rem;
    }

    /* Better tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px 6px 0 0;
    }

    /* Make buttons more modern */
    .stButton > button {
        border-radius: 6px;
        padding: 0.5rem 1.1rem;
        font-weight: 500;
    }

    /* Warning box improvement */
    .stAlert {
        border-radius: 8px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
