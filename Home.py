import streamlit as st
import os

from utils.helpers import inject_custom_css

def main():
    st.set_page_config(page_title="Smart Contract Dashboard", layout="wide", page_icon="⚡")
    inject_custom_css()

    # --- Initialize App State ---
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_file_names = [] # Storing names or handling files memory-safely across pages
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "tone" not in st.session_state:
        st.session_state.tone = "Executive Summary"
    if "focus" not in st.session_state:
        st.session_state.focus = "All Domains"
    if "structure" not in st.session_state:
        st.session_state.structure = "Concise bullet points"

    col_hero1, col_hero2 = st.columns([3, 1])
    with col_hero1:
        st.title("⚡ Smart Contract Dashboard")
        st.markdown("### Welcome to the AI-Powered Contract Analysis Platform.")
        st.markdown("Upload your contracts, customize your reports, and let our multi-agent AI system extract critical risks, obligations, and insights instantly.")
        
        st.write("---")
        
        if st.button("🚀 Get Started / Upload a Contract", type="primary"):
            st.switch_page("pages/1_Upload.py")
    
    with col_hero2:
        image_path = os.path.join(os.path.dirname(__file__), "assets", "banner.png")
        if os.path.exists(image_path):
            st.image(image_path, use_container_width=True)

if __name__ == "__main__":
    main()
