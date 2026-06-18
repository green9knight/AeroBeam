"""
styles.py - Anthropic/Claude style theme for AeroBeam
"""

import streamlit as st

def apply_anthropic_theme():
    css = """
    <style>
    .stApp { background-color: #0F0F0F; color: #EAEAEA; }
    section[data-testid="stSidebar"] { background-color: #1A1A1A; border-right: 1px solid #333; }
    .stButton > button { background-color: #3B82F6; color: white; border-radius: 6px; }
    .stTabs [aria-selected="true"] { border-bottom: 2px solid #3B82F6; color: #EAEAEA; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
