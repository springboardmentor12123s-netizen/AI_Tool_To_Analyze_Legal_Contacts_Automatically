import difflib
import base64
import mimetypes
import os
import re
import textwrap
from html import escape
import streamlit as st

from core.clause_analyzer import analyze_contract
from core.document_loader import load_pdf_pages

# Configure page metadata early so Streamlit layout is applied before rendering.
st.set_page_config(page_title="ClauseAI", layout="wide")

# Inject app-wide CSS to enforce the product's custom visual system.
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

:root {
  --ink: #14161c;
  --muted: #6a6f79;
  --surface: #f5f5f7;
  --panel: #f8f8fa;
  --border: #d8d9dd;
  --shadow: 0 2px 10px rgba(17, 24, 39, 0.06);
}

html, body, [class*="css"] {
  font-family: "Inter", system-ui, sans-serif;
  color: var(--ink);
}

[data-testid="stAppViewContainer"] {
  background: var(--surface);
  --primary-color: #14161c;
}

[data-testid="stSidebar"] {
  background:
    radial-gradient(760px 320px at 12% -14%, #e9f2ff 0%, rgba(233, 242, 255, 0) 65%),
    linear-gradient(180deg, #f7fbff 0%, #eef4fc 100%);
  border-right: 1px solid #cfdcec;
}

[data-testid="stSidebar"] .stSelectbox label {
  font-size: 16px !important;
  font-weight: 600 !important;
  color: #1f3657 !important;
}

[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
  background: #fbfdff;
  border: 1px solid #cbd9ee;
  border-radius: 10px;
  min-height: 48px;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #d4e0ef;
  border-radius: 14px;
  background: linear-gradient(135deg, #ffffff 0%, #f4f8ff 100%);
}

.sidebar-mark {
  width: 44px;
  height: 44px;
  border-radius: 11px;
  background: linear-gradient(135deg, #21406b 0%, #162b4a 100%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 18px rgba(22, 43, 74, 0.18);
}

.sidebar-title {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1;
  color: #10243f;
}

.sidebar-subtitle {
  font-size: 16px;
  color: #4f6481;
}

.sidebar-section-title {
  margin-top: 2px;
  margin-bottom: 4px;
  color: #1e3a62;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.06em;
}

[data-testid="stSidebar"] .stToggle label {
  font-size: 15px !important;
  font-weight: 600 !important;
  color: #1f3657 !important;
}

[data-testid="stSidebar"] .stToggle div[data-testid="stMarkdownContainer"] p {
  color: #1f3657 !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] {
  box-shadow: 0 4px 12px rgba(31, 58, 98, 0.06);
}

[data-testid="stSidebar"] hr {
  border-color: #d1deef !important;
}

.hero {
  background: var(--surface);
  border: 1px solid #d9dadd;
  border-radius: 14px;
  padding: 28px 30px 20px;
  box-shadow: var(--shadow);
}

.pill {
  display: inline-block;
  padding: 7px 14px;
  background: #f0f1f3;
  border: 1px solid #d4d6dc;
  border-radius: 999px;
  font-size: 14px;
  color: #676d78;
  font-weight: 500;
}

.hero-title {
  margin-top: 14px;
  margin-bottom: 10px;
  font-size: 44px;
  font-weight: 800;
  line-height: 1.02;
  letter-spacing: -0.03em;
}

.hero-title .muted {
  color: #4c4f58;
}

.hero-subtext {
  font-size: 16px;
  color: var(--muted);
  line-height: 1.45;
  max-width: 980px;
  margin-top: 12px;
}

.steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 30px;
  margin-top: 28px;
  padding-top: 16px;
  border-top: 1px solid #d8dadd;
}

.step-num {
  font-size: 14px;
  font-weight: 700;
  color: #262a33;
  letter-spacing: 0.08em;
}

.step-title {
  margin-top: 8px;
  font-size: 22px;
  font-weight: 700;
  color: #191d23;
}

.step-copy {
  margin-top: 4px;
  font-size: 16px;
  color: #686d78;
  line-height: 1.2;
}

.dropzone {
  margin-top: 16px;
  border: 2px dashed #d5d7dc;
  border-radius: 16px;
  padding: 44px 20px;
  text-align: center;
  background: #f8f8fa;
}

.drop-circle {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: #ececef;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}

.drop-title {
  font-size: 28px;
  font-weight: 700;
  color: #20232b;
}

.drop-copy {
  margin-top: 4px;
  color: #727783;
  font-size: 18px;
}

.check-panel {
  margin-top: 16px;
  border: 1px solid #d8dadd;
  border-radius: 12px;
  padding: 12px 14px;
  background: #f4f4f6;
}

[data-testid="stFileUploader"] {
  position: relative;
  margin-top: 18px !important;
  padding-bottom: 78px !important;
}

[data-testid="stFileUploaderDropzone"] {
  border: 2px dashed #d5d7dc !important;
  border-radius: 16px !important;
  background: #f8f8fa !important;
  padding: 26px 20px !important;
  min-height: 260px !important;
  position: relative;
  display: block !important;
  text-align: center !important;
}

[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzoneInstructions"] {
  display: none !important;
}

[data-testid="stFileUploaderDropzone"]::before {
  content: "Drag & drop your contract\\A Supports PDF, DOCX, TXT (up to 200MB)";
  white-space: pre;
  position: absolute;
  top: 126px;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  text-align: center;
  color: #20232b;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.5;
  pointer-events: none;
}

[data-testid="stFileUploaderDropzone"] button {
  position: absolute !important;
  left: 0 !important;
  bottom: -62px !important;
  transform: none !important;
  margin: 0 !important;
  z-index: 2;
}

[data-testid="stFileUploaderDropzone"]::after {
  content: "";
  position: absolute;
  top: 44px;
  left: 50%;
  transform: translateX(-50%);
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: #ececef url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%235f6673' stroke-width='1.9' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 16.6A4.6 4.6 0 0 0 18 8h-1.1A6.2 6.2 0 0 0 5.1 9.8 4.2 4.2 0 0 0 6 18h12a2.7 2.7 0 0 0 2-1.4'/%3E%3Cpath d='M12 14V8'/%3E%3Cpath d='m9.7 10.3 2.3-2.3 2.3 2.3'/%3E%3C/svg%3E") center / 38px 38px no-repeat;
  pointer-events: none;
}

[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
  margin-top: 44px !important;
  clear: both;
}
[data-testid="stButton"] > button,
.stButton > button {
  background: #ffffff;
  color: #222530;
  border: 1px solid #646a74 !important;
  border-radius: 10px;
  padding: 10px 18px;
  font-weight: 600;
  width: 100%;
  box-shadow: none;
  font-size: 18px;
}

[data-testid="stButton"] > button:hover,
.stButton > button:hover {
  border-color: #4e5561 !important;
  background: #fdfdfd;
}

.card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px 18px;
}

.document-box {
  background: #ffffff;
  border: 1px solid #d3d7df;
  border-radius: 10px;
  padding: 20px 22px;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
}

/* Keep bordered Streamlit containers visually consistent with document-box cards. */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: #ffffff !important;
  border: 1px solid #d3d7df !important;
  border-radius: 10px !important;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06) !important;
}

.progress-wrap {
  margin-top: 16px;
  border: 1px solid #d8dadd;
  border-radius: 12px;
  background: #fafafc;
  padding: 12px 14px;
}

.progress-title {
  font-weight: 700;
  font-size: 14px;
  color: #2d3240;
  margin-bottom: 8px;
}

.chip {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: var(--ink);
  background: #eff1f5;
  border: 1px solid #d6dae3;
}

.chip-blue { background: #e7f2ff; border-color: #cfe4ff; }
.chip-amber { background: #fff4df; border-color: #ffe1b3; }
.chip-red { background: #ffe7e7; border-color: #ffc9c9; }
.chip-green { background: #e6f6ee; border-color: #c9ecd9; }

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 4px 0 10px;
}

.icon {
  font-size: 18px;
  margin-right: 8px;
}

.loader {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #d9dce3;
  border-radius: 12px;
  margin: 8px 0 12px;
}

.spinner-ring {
  width: 14px;
  height: 14px;
  border: 2px solid #d3d7df;
  border-top-color: #2f3a4d;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #222b3a;
  opacity: 0.2;
  animation: pulse 1.2s infinite;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 100% { opacity: 0.2; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-2px); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 900px) {
  .hero-title { font-size: 34px; }
  .hero-subtext { font-size: 16px; }
  .steps { grid-template-columns: 1fr; gap: 16px; }
  .step-num { font-size: 13px; }
  .step-title { font-size: 22px; }
  .step-copy { font-size: 16px; }
  .drop-title { font-size: 24px; }
  .drop-copy { font-size: 18px; }
}
</style>
""",
    unsafe_allow_html=True,
)

# Layer additional UI overrides for the new hero/banner/upload card without changing sidebar behavior.
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1200px 580px at 90% -10%, #deebff 0%, rgba(222, 235, 255, 0) 65%),
    radial-gradient(980px 420px at 12% -14%, #eef5ff 0%, rgba(238, 245, 255, 0) 62%),
    linear-gradient(180deg, #f8fbff 0%, #f2f6fb 100%);
}

html, body, [class*="css"] {
  font-family: "Manrope", system-ui, sans-serif;
}

.top-banner {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  margin-bottom: 14px;
  border-radius: 999px;
  border: 1px solid #c7d8f2;
  background: linear-gradient(90deg, #e9f2ff 0%, #f3f8ff 100%);
  color: #1f3a60;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .03em;
}

.hero {
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #d8e2f0;
  border-radius: 22px;
  padding: 26px 28px;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.10);
}

.pill {
  display: inline-block;
  padding: 8px 14px;
  background: #ecf3ff;
  border: 1px solid #cedcf1;
  border-radius: 999px;
  font-size: 13px;
  color: #25456f;
  font-weight: 700;
  letter-spacing: .02em;
}

.hero-title {
  margin-top: 14px;
  margin-bottom: 10px;
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 48px;
  font-weight: 800;
  line-height: 1.04;
  letter-spacing: -0.03em;
  color: #0f172a;
}

.hero-subtext {
  font-size: 17px;
  color: #51637f;
  line-height: 1.52;
  margin-top: 10px;
}

.hero-steps {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(240px, 0.75fr);
  gap: 20px;
  align-items: start;
}

.hero-media {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px 0;
}

.hero-media img {
  width: 100%;
  max-width: 300px;
  border-radius: 16px;
  border: 1px solid #d5e0ef;
  box-shadow: 0 14px 28px rgba(30, 58, 102, 0.14);
}

.hero-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #dbe5f3;
  background: #ffffff;
}

.hero-step-num {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 800;
  color: #1f3556;
  background: #eaf2ff;
}

.hero-step-label {
  font-size: 16px;
  color: #1e2b3f;
  font-weight: 600;
}

.hero-image-card {
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid #d5e0ef;
  box-shadow: 0 18px 36px rgba(30, 58, 102, 0.18);
  background: #ffffff;
}

.upload-card {
  margin-top: 16px;
  border: 1px solid #d5e0ef;
  border-radius: 18px;
  padding: 18px 18px 12px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.upload-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.upload-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #eaf2ff;
  border: 1px solid #d4e2f7;
}

.upload-title {
  font-size: 20px;
  font-weight: 800;
  color: #14233b;
}

.upload-subtitle {
  font-size: 14px;
  color: #5f7089;
  margin-top: 2px;
}

.upload-drop-note {
  margin-top: 8px;
  margin-bottom: 2px;
  font-size: 13px;
  color: #7b889b;
}

/* Keep upload-mode control aligned cleanly within the same upload section row. */
.stCheckbox {
  margin-top: 0.1rem;
}

/* Mode selectors styled like hero step boxes. */
button[aria-label="Upload File"],
button[aria-label="Upload Multiple Files"] {
  min-height: 54px !important;
  text-align: left !important;
  padding: 10px 12px !important;
  border-radius: 12px !important;
  border: 1px solid #dbe5f3 !important;
  background: #ffffff !important;
  color: #1e2b3f !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}

button[aria-label="Upload File"]:hover,
button[aria-label="Upload Multiple Files"]:hover {
  border-color: #b9ccea !important;
  background: #f8fbff !important;
}

[data-testid="stFileUploader"] {
  margin-top: 8px !important;
}

[data-testid="stFileUploaderDropzone"] {
  border: 2px dashed #c8d7ee !important;
  background: #f7fbff !important;
  min-height: 220px !important;
}

[data-testid="stFileUploaderDropzone"]::before {
  content: "Drag & drop your contract here";
  color: #1f2f49;
  font-size: 17px;
  top: 128px;
}

[data-testid="stFileUploaderDropzone"]::after {
  top: 42px;
  background: #e8f2ff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23335580' stroke-width='1.9' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 16.6A4.6 4.6 0 0 0 18 8h-1.1A6.2 6.2 0 0 0 5.1 9.8 4.2 4.2 0 0 0 6 18h12a2.7 2.7 0 0 0 2-1.4'/%3E%3Cpath d='M12 14V8'/%3E%3Cpath d='m9.7 10.3 2.3-2.3 2.3 2.3'/%3E%3C/svg%3E") center / 38px 38px no-repeat;
}

@media (max-width: 900px) {
  .top-banner {
    width: 100%;
    justify-content: center;
    text-align: center;
  }
  .hero {
    padding: 18px;
  }
  .hero-title {
    font-size: 34px;
  }
  .hero-layout {
    grid-template-columns: 1fr;
    gap: 14px;
  }
  .hero-media img {
    max-width: 220px;
  }
  .upload-title {
    font-size: 18px;
  }
}
</style>
""",
    unsafe_allow_html=True,
)

# Professional top banner + hero card with photo inside the same box.
st.markdown(
    """
<div class="top-banner">
  <span>Secure - Private - AI-Powered Contract Intelligence</span>
</div>
""",
    unsafe_allow_html=True,
)
local_hero_candidates = [
    os.path.join("assets", "hero.jpg"),
    os.path.join("assets", "hero.jpeg"),
    os.path.join("assets", "hero.png"),
    os.path.join("assets", "professional.jpg"),
    os.path.join("assets", "professional.png"),
]
hero_image_source = next((p for p in local_hero_candidates if os.path.exists(p)), None)
if hero_image_source:
    mime = mimetypes.guess_type(hero_image_source)[0] or "image/jpeg"
    with open(hero_image_source, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    hero_image_src = f"data:{mime};base64,{encoded}"
else:
    hero_image_src = "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?auto=format&fit=crop&w=1200&q=80"

st.markdown(
    f"""
<div class="hero">
  <div class="hero-layout">
    <div>
      <div class="pill">Enterprise-grade Legal AI Workspace</div>
      <div class="hero-title">Multi-Agent Contract Intelligence System</div>
      <div class="hero-subtext">
        ClauseAI helps legal, operations, and finance teams identify key obligations, spot hidden
        risk exposure, and generate practical recommendations with specialist AI agents.
      </div>
      <div class="hero-steps">
        <div class="hero-step"><span class="hero-step-num">1</span><span class="hero-step-label">Upload Contract</span></div>
        <div class="hero-step"><span class="hero-step-num">2</span><span class="hero-step-label">Click Analyze</span></div>
        <div class="hero-step"><span class="hero-step-num">3</span><span class="hero-step-label">Review Insights</span></div>
      </div>
    </div>
    <div class="hero-media">
      <img src="{escape(hero_image_src)}" alt="Legal AI professional" />
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Build sidebar controls to capture analysis preferences before execution.
with st.sidebar:
    st.markdown(
        """
<div class="sidebar-brand">
  <span class="sidebar-mark">
    <svg width="23" height="23" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M12 2.5 4.5 5.8v5.4c0 4.4 2.8 8.5 7.5 10.3 4.7-1.8 7.5-5.9 7.5-10.3V5.8L12 2.5Z" stroke="#fff" stroke-width="1.7"/>
      <path d="M9.5 11.6 11.2 13.3 14.8 9.7" stroke="#fff" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </span>
  <div>
    <div class="sidebar-title">ClauseAI</div>
    <div class="sidebar-subtitle">Contract Analysis System</div>
  </div>
</div>
<hr style="border:none;border-top:1px solid #d1deef;margin:14px 0 18px;" />
""",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-section-title">SETTINGS</div>', unsafe_allow_html=True)

    if "output_format" not in st.session_state:
        st.session_state["output_format"] = "Bullets + summary"
    if "show_fast_warning" not in st.session_state:
        st.session_state["show_fast_warning"] = False

    # Auto-lock output format in fast mode to avoid unsupported combinations.
    def _on_fast_mode_change():
        if st.session_state.get("fast_mode"):
            st.session_state["output_format"] = "Summary only"
            st.session_state["show_fast_warning"] = False

    fast_mode = st.toggle(
        "Fast mode (short summary only)",
        value=False,
        key="fast_mode",
        on_change=_on_fast_mode_change,
    )
    stream_output = st.toggle("Stream output", value=False)
    summary_length = st.selectbox("Summary Length", ["Short", "Medium (Standard)", "Detailed"], index=2)
    risk_sensitivity = st.selectbox("Risk Sensitivity", ["Conservative", "Balanced", "Aggressive"], index=1)
    contract_type = st.selectbox("Contract Type", ["Auto-detect", "NDA", "MSA", "Lease", "Employment"], index=0)

    # Enforce fast-mode format constraints so UI state stays valid.
    def _on_output_format_change():
        if st.session_state.get("fast_mode") and st.session_state.get("output_format") != "Summary only":
            st.session_state["show_fast_warning"] = True
            st.session_state["output_format"] = "Summary only"
        else:
            st.session_state["show_fast_warning"] = False

    output_format = st.selectbox(
        "Output Format",
        ["Summary only", "Bullets + summary", "Bullets only"],
        key="output_format",
        on_change=_on_output_format_change,
    )
    language = st.selectbox("Language", ["Formal English", "Simple English"], index=0)

    if fast_mode and st.session_state["output_format"] != "Summary only":
        st.session_state["output_format"] = "Summary only"
    output_format = st.session_state["output_format"]

    warning_slot = st.empty()
    if st.session_state.get("show_fast_warning"):
        warning_slot.warning("Fast mode only supports Summary only output.")

    st.markdown("---")

# Upload mode selector as two side-by-side sub-boxes.
if "upload_mode" not in st.session_state:
    st.session_state["upload_mode"] = "single"

st.markdown(
    """
<div class="upload-card">
  <div class="upload-head">
    <span class="upload-icon">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M20 16.6A4.6 4.6 0 0 0 18 8h-1.1A6.2 6.2 0 0 0 5.1 9.8 4.2 4.2 0 0 0 6 18h12a2.7 2.7 0 0 0 2-1.4" stroke="#234770" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M12 14V8" stroke="#234770" stroke-width="1.8" stroke-linecap="round"/>
        <path d="m9.7 10.3 2.3-2.3 2.3 2.3" stroke="#234770" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </span>
    <div>
      <div class="upload-title">Choose Upload Mode</div>
      <div class="upload-subtitle">Click one mode box below to switch the drag-and-drop area</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

mode_col_single, mode_col_multi = st.columns(2, gap="small")
with mode_col_single:
    if st.button(
        "Upload File",
        key="mode_single_box",
        use_container_width=True,
    ):
        st.session_state["upload_mode"] = "single"
    st.caption("Supports PDF, DOCX, TXT (up to 200MB)")
with mode_col_multi:
    if st.button(
        "Upload Multiple Files",
        key="mode_multiple_box",
        use_container_width=True,
    ):
        st.session_state["upload_mode"] = "multiple"
    st.caption("Supports PDF, DOCX, TXT")

multiple_upload_mode = st.session_state.get("upload_mode") == "multiple"
st.caption(f"Selected mode: {'Multiple Upload' if multiple_upload_mode else 'Single Upload'}")

uploaded_file = None
uploaded_file_a = None
uploaded_file_b = None
if not multiple_upload_mode:
    uploaded_file = st.file_uploader(
        "Upload contract",
        type=["pdf", "docx", "txt"],
        label_visibility="collapsed",
        key="single_contract_main",
    )
else:
    up_col_a, up_col_b = st.columns(2, gap="small")
    with up_col_a:
        uploaded_file_a = st.file_uploader(
            "Upload Contract 1",
            type=["pdf", "docx", "txt"],
            key="multi_contract_1",
        )
    with up_col_b:
        uploaded_file_b = st.file_uploader(
            "Upload Contract 2",
            type=["pdf", "docx", "txt"],
            key="multi_contract_2",
        )

analyze_trigger = st.button(
    "Analyze Contracts" if multiple_upload_mode else "Analyze Contract",
    key="analyze_main_action",
    use_container_width=True,
)


# Parse model text into known sections so rendering and export stay structured.
def _split_sections(text: str):
    sections = {
        "Key Clauses": "",
        "Risks": "",
        "Missing / Weak": "",
        "Plain Summary": "",
        "Risk Score": "",
    }
    aliases = {
        "key clauses": "Key Clauses",
        "findings": "Key Clauses",
        "risks": "Risks",
        "missing / weak": "Missing / Weak",
        "missing / weak points": "Missing / Weak",
        "missing/weak points": "Missing / Weak",
        "missing or weak points": "Missing / Weak",
        "plain summary": "Plain Summary",
        "recommended follow-up actions": "Plain Summary",
        "recommended actions": "Plain Summary",
    }

    def _canonical_heading(value: str):
        cleaned = (value or "").strip().replace("**", "")
        if cleaned.startswith("###"):
            cleaned = cleaned.lstrip("#").strip()
        cleaned = re.sub(r"^\d+\s*[\)\.\-:]\s*", "", cleaned).strip()
        cleaned = cleaned.rstrip(":").strip()
        cleaned = re.sub(r"\s*\(.*?\)\s*$", "", cleaned).strip()
        lowered = cleaned.lower()

        if lowered.startswith("risk score"):
            return "Risk Score"
        for heading, canonical in aliases.items():
            if lowered == heading or lowered.startswith(f"{heading} "):
                return canonical
        return None

    current = None
    for line in text.splitlines():
        stripped = line.strip().replace("**", "")
        canonical = _canonical_heading(stripped)

        if canonical == "Risk Score":
            sections["Risk Score"] = stripped
            current = None
            continue

        if canonical:
            current = canonical
            continue

        if current:
            sections[current] += line + "\n"
    return sections


# Normalize line breaks and spacing to keep section text clean and consistent.
def _normalize_section_text(text: str) -> str:
    if not text:
        return ""
    lines = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        lines.append(line)
    return "\n".join(lines)


# Build a canonical report string so preview and downloads share the same content.
def _build_complete_report_text(
    result_text: str,
    title: str = "AI Analysis",
    include_empty: bool = True,
    include_risk: bool = True,
) -> str:
    body = (result_text or "").strip()
    sections = _split_sections(body)
    has_structured_output = any(
        sections[key].strip() for key in ("Key Clauses", "Risks", "Missing / Weak", "Plain Summary")
    )
    if not has_structured_output:
        if not body:
            body = "No output generated."
        return f"{title}\n\n{body}"

    lines = [title, ""]
    for section_name in ("Key Clauses", "Risks", "Missing / Weak", "Plain Summary"):
        section_body = _normalize_section_text(sections[section_name])
        if not section_body and not include_empty:
            continue
        if not section_body:
            section_body = "Not stated."
        lines.append(f"{section_name}:")
        lines.append(section_body)
        lines.append("")
    if include_risk:
        risk_score = sections["Risk Score"].strip() or "Risk Score: Not stated"
        lines.append(risk_score)
    return "\n".join(lines).strip()


# Render a styled output card to improve readability of analysis results.
def _render_full_output_box(
    result_text: str,
    title: str = "Analysis Document Preview",
    include_empty: bool = True,
    include_risk: bool = True,
):
    sections = _split_sections(result_text or "")
    has_structured_output = any(
        sections[key].strip() for key in ("Key Clauses", "Risks", "Missing / Weak", "Plain Summary")
    )
    if has_structured_output:
        rows = []
        for section_name in ("Key Clauses", "Risks", "Missing / Weak", "Plain Summary"):
            section_body = _normalize_section_text(sections[section_name])
            if not section_body and not include_empty:
                continue
            if not section_body:
                section_body = "Not stated."
            rows.append(
                f"""
<div style="margin-top:12px;">
  <div style="font-size:14px; font-weight:700; color:#2d3240;">{escape(section_name)}</div>
  <div style="margin-top:4px; white-space: pre-wrap; line-height:1.55;">{escape(section_body)}</div>
</div>
"""
            )
        risk_score = sections["Risk Score"].strip() or "Risk Score: Not stated"
    else:
        raw_body = _normalize_section_text((result_text or "").strip()) or "No output generated."
        rows = [
            f"""
<div style="margin-top:12px;">
  <div style="font-size:14px; font-weight:700; color:#2d3240;">Analysis</div>
  <div style="margin-top:4px; white-space: pre-wrap; line-height:1.55;">{escape(raw_body)}</div>
</div>
"""
        ]
        risk_score = "Risk Score: Not stated"
    st.markdown(
        f"""
<div class="document-box" style="margin-bottom:12px;">
  <div class="section-title">{escape(title)}</div>
  {''.join(rows)}
  {"<div style='margin-top:14px;'><span class='chip chip-red'>" + escape(risk_score) + "</span></div>" if include_risk else ""}
</div>
""",
        unsafe_allow_html=True,
    )


# Show per-agent detail in tabs so users can inspect specialist reasoning.
def _render_agent_breakdown(agent_outputs, stream_output: bool = False):
    with st.expander("View agent-by-agent analysis", expanded=False):
        if not agent_outputs:
            if stream_output:
                st.caption("Agent-by-agent analysis is disabled in Stream output mode. Turn Stream output off.")
            else:
                st.caption("No agent output available.")
            st.info("No agent output generated.")
            return

        role_items = list(agent_outputs.items())
        tabs = st.tabs([role_name.title() for role_name, _ in role_items])
        for tab, (role_name, role_text) in zip(tabs, role_items):
            with tab:
                report_text = _build_complete_report_text(
                    role_text,
                    title=f"{role_name.title()} Agent Analysis",
                    include_empty=False,
                    include_risk=False,
                )
                _render_full_output_box(
                    report_text,
                    title=f"{role_name.title()} Agent Analysis",
                    include_empty=False,
                    include_risk=False,
                )


# Convert report text to RTF bytes so users can download a Word-compatible file.
def _build_word_rtf_bytes(result_text: str) -> bytes:
    text = (result_text or "").replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", r"\par " + "\n")
    rtf = r"{\rtf1\ansi\deff0{\fonttbl{\f0 Calibri;}}\f0\fs22 " + text + "}"
    return rtf.encode("utf-8")


# Build a lightweight PDF in code so export works without extra PDF dependencies.
def _build_simple_pdf_bytes(result_text: str) -> bytes:
    page_width = 612
    page_height = 792
    margin = 50
    line_height = 14
    start_y = page_height - margin
    wrap_width = 92
    max_lines_per_page = max(1, int((page_height - (2 * margin)) / line_height))

    # Escape PDF-sensitive characters to keep generated content stream valid.
    def _safe_pdf_text(line: str) -> str:
        normalized = line.encode("latin-1", "replace").decode("latin-1")
        return normalized.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    logical_lines = []
    for raw_line in (result_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        wrapped = textwrap.wrap(raw_line, width=wrap_width) if raw_line.strip() else [""]
        logical_lines.extend(wrapped)

    if not logical_lines:
        logical_lines = ["No output generated."]

    pages = [logical_lines[i:i + max_lines_per_page] for i in range(0, len(logical_lines), max_lines_per_page)]

    objects = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = None
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    page_ids = []
    next_id = 4
    for page_lines in pages:
        page_id = next_id
        content_id = next_id + 1
        page_ids.append(page_id)
        next_id += 2

        stream_lines = [
            "BT",
            "/F1 11 Tf",
            f"{line_height} TL",
            f"{margin} {start_y} Td",
        ]
        for idx, line in enumerate(page_lines):
            command_prefix = "" if idx == 0 else "T* "
            stream_lines.append(f"{command_prefix}({_safe_pdf_text(line)}) Tj")
        stream_lines.append("ET")
        stream_data = "\n".join(stream_lines).encode("latin-1", "replace")
        objects[content_id] = (
            b"<< /Length " + str(len(stream_data)).encode("ascii") + b" >>\nstream\n" + stream_data + b"\nendstream"
        )
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R "
            + f"/MediaBox [0 0 {page_width} {page_height}] ".encode("ascii")
            + b"/Resources << /Font << /F1 3 0 R >> >> "
            + f"/Contents {content_id} 0 R >>".encode("ascii")
        )

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[2] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode("ascii")

    max_id = max(objects.keys())
    parts = [b"%PDF-1.4\n"]
    offsets = [0] * (max_id + 1)
    current_offset = len(parts[0])

    for obj_id in range(1, max_id + 1):
        offsets[obj_id] = current_offset
        block = f"{obj_id} 0 obj\n".encode("ascii") + objects[obj_id] + b"\nendobj\n"
        parts.append(block)
        current_offset += len(block)

    xref_offset = current_offset
    xref_header = f"xref\n0 {max_id + 1}\n".encode("ascii")
    parts.append(xref_header)
    current_offset += len(xref_header)
    parts.append(b"0000000000 65535 f \n")
    current_offset += len(b"0000000000 65535 f \n")
    for obj_id in range(1, max_id + 1):
        line = f"{offsets[obj_id]:010d} 00000 n \n".encode("ascii")
        parts.append(line)
        current_offset += len(line)

    trailer = f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    parts.append(trailer)
    return b"".join(parts)


# Render export buttons so users can save analysis in common document formats.
def _render_export_buttons(result_text: str, file_stem: str = "clauseai_analysis"):
    col_pdf, col_word = st.columns(2)
    with col_pdf:
        st.download_button(
            "Export as PDF",
            data=_build_simple_pdf_bytes(result_text),
            file_name=f"{file_stem}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col_word:
        st.download_button(
            "Export as Word",
            data=_build_word_rtf_bytes(result_text),
            file_name=f"{file_stem}.doc",
            mime="application/msword",
            use_container_width=True,
        )


# Compute a compact unified diff so side-by-side contract changes are easy to review.
def _diff_text(a: str, b: str, limit: int = 200):
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    diff = list(difflib.unified_diff(a_lines, b_lines, fromfile="Contract A", tofile="Contract B", lineterm=""))
    if len(diff) > limit:
        diff = diff[:limit] + ["... diff truncated ..."]
    return "\n".join(diff)


# Load any supported upload type into a shared page-text structure for analysis.
def _load_any_contract(upload):
    if upload.name.lower().endswith(".pdf"):
        return load_pdf_pages(upload)
    if upload.name.lower().endswith(".txt"):
        raw = upload.read().decode("utf-8", errors="ignore")
        return [{"page": 1, "text": raw}]
    st.warning("DOCX upload UI is ready. Parsing currently supports PDF/TXT.")
    return None


# Define staged status messages to make long-running analysis feel transparent.
LIVE_STAGES = [
    "Uploading document...",
    "Extracting text...",
    "Generating embeddings...",
    "Detecting contract type...",
    "Extracting domain clauses...",
    "Planning agent execution...",
    "Running Compliance Agent...",
    "Running Finance Agent...",
    "Running Legal Agent...",
    "Running Operations Agent...",
    "Aggregating responses...",
    "Finalizing results...",
]


# Render one progress stage row to provide live feedback during analysis.
def _build_stage_markdown(stage_text: str):
    return f"""
<div class="loader">
  <span class="spinner-ring"></span>
  <strong>{stage_text}</strong>
</div>
"""


# Run selected analysis flow only after a contract file is available.
if analyze_trigger:
    if not multiple_upload_mode:
        if not uploaded_file:
            st.warning("Upload a contract to analyze.")
            st.stop()
        progress_shell = st.container()
        progress_shell.markdown(
            """
<div class="progress-wrap">
  <div class="progress-title">LIVE PROGRESS DISPLAY</div>
</div>
""",
            unsafe_allow_html=True,
        )
        stage_placeholder = progress_shell.empty()
        stage_placeholder.markdown(_build_stage_markdown("Starting analysis..."), unsafe_allow_html=True)

        stage_state = {"index": -1}
        stage_lookup = {name: idx for idx, name in enumerate(LIVE_STAGES)}

        # Advance the displayed stage only forward to avoid flicker and regressions.
        def update_stage(stage_name: str):
            stage_idx = stage_lookup.get(stage_name)
            if stage_idx is None or stage_idx <= stage_state["index"]:
                return
            stage_state["index"] = stage_idx
            stage_placeholder.markdown(_build_stage_markdown(stage_name), unsafe_allow_html=True)

        update_stage("Uploading document...")
        update_stage("Extracting text...")

        contract_pages = _load_any_contract(uploaded_file)
        if not contract_pages:
            stage_placeholder.empty()
            st.stop()

        result = analyze_contract(
            contract_pages,
            fast_mode=fast_mode,
            stream=stream_output,
            summary_length=summary_length.replace(" (Standard)", ""),
            risk_sensitivity=risk_sensitivity,
            contract_type=contract_type,
            output_format=output_format,
            language=language,
            progress_callback=update_stage,
            return_agent_outputs=not stream_output,
        )

        stage_placeholder.markdown(
            '<div class="loader"><strong>Completed</strong></div>',
            unsafe_allow_html=True,
        )

        st.subheader("AI Analysis")
        if stream_output:
            stream_chunks = []
            for chunk in result:
                if chunk is None:
                    continue
                stream_chunks.append(str(chunk))
            final_text = "".join(stream_chunks).strip()
            complete_report = _build_complete_report_text(final_text, title="AI Analysis")
            _render_full_output_box(complete_report, title="AI Analysis Document Preview")
            _render_export_buttons(complete_report, file_stem="contract_analysis")
            _render_agent_breakdown(None, stream_output=True)
        else:
            result_text = result["final_output"] if isinstance(result, dict) else result
            agent_outputs = result.get("agent_outputs", {}) if isinstance(result, dict) else {}
            complete_report = _build_complete_report_text(result_text, title="AI Analysis")
            _render_full_output_box(complete_report, title="AI Analysis Document Preview")
            _render_export_buttons(complete_report, file_stem="contract_analysis")
            _render_agent_breakdown(agent_outputs, stream_output=False)
    else:
        if not uploaded_file_a or not uploaded_file_b:
            st.warning("Upload both contracts to run multi-file analysis.")
            st.stop()

        if stream_output:
            st.info("Stream output is disabled in multi-file mode. Showing complete results for both contracts.")

        with st.spinner("Analyzing both contracts..."):
            pages_a = _load_any_contract(uploaded_file_a)
            pages_b = _load_any_contract(uploaded_file_b)
            if not pages_a or not pages_b:
                st.stop()
            result_a = analyze_contract(
                pages_a,
                fast_mode=fast_mode,
                stream=False,
                summary_length=summary_length.replace(" (Standard)", ""),
                risk_sensitivity=risk_sensitivity,
                contract_type=contract_type,
                output_format=output_format,
                language=language,
                return_agent_outputs=True,
            )
            result_b = analyze_contract(
                pages_b,
                fast_mode=fast_mode,
                stream=False,
                summary_length=summary_length.replace(" (Standard)", ""),
                risk_sensitivity=risk_sensitivity,
                contract_type=contract_type,
                output_format=output_format,
                language=language,
                return_agent_outputs=True,
            )

        result_text_a = result_a["final_output"] if isinstance(result_a, dict) else result_a
        agent_outputs_a = result_a.get("agent_outputs", {}) if isinstance(result_a, dict) else {}
        complete_report_a = _build_complete_report_text(result_text_a, title="Contract 1 Analysis")

        result_text_b = result_b["final_output"] if isinstance(result_b, dict) else result_b
        agent_outputs_b = result_b.get("agent_outputs", {}) if isinstance(result_b, dict) else {}
        complete_report_b = _build_complete_report_text(result_text_b, title="Contract 2 Analysis")

        # Build compact highlights for side-by-side contract comparison view.
        def _key_highlights(report_text: str, raw_text: str = ""):
            sections = _split_sections(report_text or "")
            risk_score = sections.get("Risk Score", "").strip() or "Risk Score: Not stated"

            def _pick_points(section_name: str, limit: int = 2):
                raw = _normalize_section_text(sections.get(section_name, ""))
                if not raw:
                    fallback = _normalize_section_text(raw_text)
                    if section_name == "Plain Summary" and fallback:
                        first_line = fallback.split("\n")[0].strip()
                        return [first_line] if first_line else ["Not stated"]
                    return ["Not stated"]
                points = []
                for line in raw.split("\n"):
                    value = line.strip().lstrip("-").strip()
                    if value:
                        points.append(value)
                    if len(points) >= limit:
                        break
                return points or ["Not stated"]

            return {
                "risk_score": risk_score,
                "key_clauses": _pick_points("Key Clauses", limit=2),
                "risks": _pick_points("Risks", limit=2),
                "missing_weak": _pick_points("Missing / Weak", limit=2),
                "summary": _pick_points("Plain Summary", limit=1),
            }

        highlights_a = _key_highlights(complete_report_a, raw_text=result_text_a)
        highlights_b = _key_highlights(complete_report_b, raw_text=result_text_b)

        st.subheader("Multi-Contract Analysis")
        view_tab_1, view_tab_2, compare_tab = st.tabs(["View Contract 1", "View Contract 2", "Compare Contracts"])
        with view_tab_1:
            _render_full_output_box(complete_report_a, title="Contract 1 Document Preview")
            _render_export_buttons(complete_report_a, file_stem="contract_1_analysis")
            _render_agent_breakdown(agent_outputs_a, stream_output=False)
        with view_tab_2:
            _render_full_output_box(complete_report_b, title="Contract 2 Document Preview")
            _render_export_buttons(complete_report_b, file_stem="contract_2_analysis")
            _render_agent_breakdown(agent_outputs_b, stream_output=False)
        with compare_tab:
            st.markdown("### Important Key Highlights")
            if fast_mode:
                st.info("Fast mode generates summary-only output. Key Clauses, Top Risks, and Missing / Weak may show Not stated in comparison.")
            def _fmt_points_html(items, limit: int = 2):
                values = items if items else ["Not stated"]
                bullet_items = "".join(f"<li>{escape(str(point))}</li>" for point in values[:limit])
                return f"<ul style='margin:0; padding-left:18px;'>{bullet_items}</ul>"

            compare_rows = [
                ("Risk Score", f"<div>{escape(highlights_a['risk_score'])}</div>", f"<div>{escape(highlights_b['risk_score'])}</div>"),
                ("Key Clauses", _fmt_points_html(highlights_a["key_clauses"], limit=2), _fmt_points_html(highlights_b["key_clauses"], limit=2)),
                ("Top Risks", _fmt_points_html(highlights_a["risks"], limit=2), _fmt_points_html(highlights_b["risks"], limit=2)),
                ("Missing / Weak", _fmt_points_html(highlights_a["missing_weak"], limit=1), _fmt_points_html(highlights_b["missing_weak"], limit=1)),
                ("Summary", _fmt_points_html(highlights_a["summary"], limit=1), _fmt_points_html(highlights_b["summary"], limit=1)),
            ]

            row_html = "".join(
                f"""
<div style='display:grid; grid-template-columns: 1.05fr 1.9fr 1.9fr; gap:12px; padding:10px 0; border-top:1px solid #e8ebf1;'>
  <div><strong>{escape(metric)}</strong></div>
  <div>{value_a}</div>
  <div>{value_b}</div>
</div>
"""
                for metric, value_a, value_b in compare_rows
            )

            st.markdown(
                f"""
<div class='document-box' style='margin-bottom:12px;'>
  <div class='section-title'>Contract Comparison Highlights</div>
  <div style='display:grid; grid-template-columns: 1.05fr 1.9fr 1.9fr; gap:12px; padding:4px 0 10px; border-bottom:1px solid #e0e4ec;'>
    <div><strong>Metric</strong></div>
    <div><strong>Contract 1</strong></div>
    <div><strong>Contract 2</strong></div>
  </div>
  {row_html}
</div>
""",
                unsafe_allow_html=True,
            )









