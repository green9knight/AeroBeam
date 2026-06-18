import streamlit as st

def apply_modern_theme():
    css = """
    <style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .stTabs [data-baseweb="tab"] { padding: 8px 16px; font-weight: 500; }
    .stButton > button { border-radius: 6px; font-weight: 500; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
