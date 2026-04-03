import difflib
import base64
import json
import mimetypes
import os
import re
import textwrap
from contextlib import contextmanager
import time
from datetime import datetime
from html import escape
import streamlit as st

from core.batch_processor import process_contract_batch
from core.clause_analyzer import analyze_agent_breakdown, analyze_contract
from core.document_loader import load_docx_pages, load_pdf_pages, parse_contract_text
from core.report_generator import (
    ReportOptions,
    build_report_docx_bytes,
    build_report_pdf_bytes,
    generate_report,
)

# Configure page metadata early so Streamlit layout is applied before rendering.
st.set_page_config(page_title="ClauseAI", layout="wide")

# Inject app-wide CSS to enforce the product's custom visual system.
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

:root {
  --ink: #121a2b;
  --muted: #586579;
  --surface: #f5f8fc;
  --panel: #fdfefe;
  --panel-soft: #f7faff;
  --border: #d4ddea;
  --accent: #214d85;
  --accent-soft: #edf4ff;
  --shadow: 0 12px 30px rgba(24, 44, 76, 0.08);
  --shadow-soft: 0 8px 22px rgba(30, 58, 102, 0.07);
}

html, body, [class*="css"] {
  font-family: "Inter", system-ui, sans-serif;
  color: var(--ink);
  font-weight: 500;
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
  font-weight: 650 !important;
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
  font-weight: 600;
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
  font-weight: 650 !important;
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
  font-weight: 600;
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
  font-weight: 550;
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
  font-weight: 550;
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
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  border: 1px solid #d7e0ec;
  border-radius: 16px;
  padding: 20px 22px;
  box-shadow: var(--shadow-soft);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.document-box:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(18, 37, 68, 0.11);
  border-color: #bfd0e8;
}

.sticky-analysis-header {
  position: sticky;
  top: 8px;
  z-index: 5;
  background: rgba(245, 245, 247, 0.92);
  backdrop-filter: blur(8px);
  padding: 8px 0 10px;
}

.report-highlight {
  background: linear-gradient(135deg, #f8fbff 0%, #eef5ff 100%);
  border: 1px solid #d2e1f5;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 10px 22px rgba(21, 41, 70, 0.08);
}

.risk-showcase-card {
  min-height: 390px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.risk-ring-shell {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 10px 0 18px;
}

.risk-ring {
  width: 254px;
  height: 254px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.risk-ring::before {
  content: "";
  position: absolute;
  inset: 28px;
  border-radius: 50%;
  background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
  border: 1px solid #e2e9f3;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.9);
}

.risk-marker {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 3px solid #ffffff;
  box-shadow: 0 4px 10px rgba(23, 41, 71, 0.2);
  z-index: 2;
}

.risk-ring-center {
  position: relative;
  text-align: center;
  z-index: 1;
  max-width: 180px;
}

.risk-level {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 32px;
  line-height: 1.05;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #142235;
  white-space: nowrap;
  word-break: keep-all;
}

.risk-subtitle {
  margin-top: 8px;
  color: #617085;
  font-size: 14px;
  font-weight: 700;
}

.risk-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 11px 18px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  color: #5f4d12;
  background: linear-gradient(180deg, #fff7da 0%, #f8e8b0 100%);
  border: 1px solid #ecd793;
}

.risk-factor-wheel {
  width: 228px;
  height: 228px;
  border-radius: 50%;
  margin: 56px auto 0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.risk-factor-wheel::before {
  content: "";
  position: absolute;
  inset: 34px;
  border-radius: 50%;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  border: 1px solid #dde5f1;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.9);
}

.risk-factor-center {
  position: relative;
  z-index: 1;
  text-align: center;
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 14px;
  font-weight: 800;
  color: #15253b;
  line-height: 1.25;
}

.risk-factor-stage {
  position: relative;
  width: 100%;
  min-height: 370px;
  max-width: 420px;
  margin: 0 auto;
  overflow: visible;
}

.risk-factor-node {
  position: absolute;
  width: 130px;
  min-height: 84px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 12px;
  border-radius: 22px;
  color: #18304d;
  background: linear-gradient(180deg, #ffffff 0%, #fffdfd 100%);
  border: 1px solid #f1cad7;
  box-shadow: 0 16px 26px rgba(24, 44, 76, 0.08);
  font-size: 11px;
  line-height: 1.28;
  font-weight: 700;
  text-align: center;
  z-index: 3;
}

.risk-factor-node.node-top-left { top: 86px; left: 18px; transform: rotate(-22deg); }
.risk-factor-node.node-top { top: 16px; left: 145px; }
.risk-factor-node.node-top-right { top: 86px; right: 18px; transform: rotate(22deg); }
.risk-factor-node.node-bottom-left { bottom: 14px; left: 82px; transform: rotate(-14deg); }
.risk-factor-node.node-bottom { bottom: -4px; left: 145px; }
.risk-factor-node.node-bottom-right { bottom: 14px; right: 82px; transform: rotate(14deg); }

.risk-factor-node-content {
  transform: rotate(0deg);
}

.risk-factor-node.node-top-left .risk-factor-node-content { transform: rotate(22deg); }
.risk-factor-node.node-top-right .risk-factor-node-content { transform: rotate(-22deg); }
.risk-factor-node.node-bottom-left .risk-factor-node-content { transform: rotate(14deg); }
.risk-factor-node.node-bottom-right .risk-factor-node-content { transform: rotate(-14deg); }

.risk-overview-box {
  width: 100%;
}

.risk-overview-panel {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
}

.risk-factor-card-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 10px;
}

.risk-factor-card {
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  border: 1px solid #d9e3f0;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 10px 24px rgba(22, 41, 70, 0.08);
  min-height: 210px;
  position: relative;
  transition: box-shadow 0.18s ease, border-color 0.18s ease;
}

.risk-factor-card:hover {
  box-shadow: 0 18px 34px rgba(23, 54, 99, 0.16);
  border-color: #9db9df;
}

.risk-factor-card-head {
  padding: 12px 14px;
  color: #ffffff;
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 16px;
  font-weight: 800;
  line-height: 1.15;
}

.risk-factor-card-body {
  padding: 14px 14px 16px;
  display: flex;
  flex-direction: column;
}

.risk-factor-mini-ring {
  width: 108px;
  height: 108px;
  border-radius: 50%;
  margin: 4px auto 12px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.risk-factor-mini-ring::before {
  content: "";
  position: absolute;
  inset: 18px;
  border-radius: 50%;
  background: #ffffff;
  border: 1px solid #e0e7f1;
}

.risk-factor-mini-center {
  position: relative;
  z-index: 1;
  text-align: center;
}

.risk-factor-mini-score {
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 24px;
  line-height: 1;
  font-weight: 800;
  color: #182842;
}

.risk-factor-mini-label {
  margin-top: 4px;
  font-size: 11px;
  font-weight: 700;
  color: #6b778a;
}

.risk-factor-card-copy {
  font-size: 13px;
  line-height: 1.45;
  color: #2d405e;
  font-weight: 650;
  text-align: center;
}

.feedback-bar {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e1e5ec;
}

.feedback-rating-card {
  margin-top: 12px;
  padding: 18px 18px 14px;
  border-radius: 18px;
  background: linear-gradient(145deg, #214d85 0%, #173864 55%, #102948 100%);
  box-shadow: 0 16px 34px rgba(18, 44, 85, 0.18);
  text-align: center;
}

.feedback-rating-title {
  color: #ffffff;
  font-family: "Plus Jakarta Sans", sans-serif;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.feedback-rating-copy {
  margin-top: 6px;
  color: #d7e7fb;
  font-size: 13px;
  font-weight: 600;
}

.skeleton-card {
  border-radius: 12px;
  background: linear-gradient(90deg, #f1f3f6 25%, #fafbfc 50%, #f1f3f6 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
  height: 96px;
  border: 1px solid #e3e6eb;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Keep bordered Streamlit containers visually consistent with document-box cards. */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%) !important;
  border: 1px solid #d7e0ec !important;
  border-radius: 16px !important;
  box-shadow: var(--shadow-soft) !important;
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
  font-weight: 700;
  margin: 4px 0 10px;
  color: #16243b;
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
  background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
  border: 1px solid #d4deec;
  border-radius: 14px;
  margin: 8px 0 12px;
  box-shadow: 0 8px 18px rgba(24, 44, 76, 0.06);
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stCaptionContainer"],
.stCaption,
.stAlert,
[data-testid="stExpander"] summary,
[data-baseweb="tab-list"] button,
[data-testid="stFileUploader"] small,
label,
.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] * {
  font-weight: 550 !important;
  color: #1b2435;
}

[data-baseweb="tab-list"] {
  gap: 8px;
}

[data-baseweb="tab"] {
  background: rgba(255, 255, 255, 0.72) !important;
  border: 1px solid #d6e0ee !important;
  border-radius: 12px 12px 0 0 !important;
  padding: 10px 14px !important;
}

[data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(180deg, #ffffff 0%, #f5f9ff 100%) !important;
  border-color: #bcd0ea !important;
  color: #133256 !important;
}

[data-testid="stExpander"] {
  border: 1px solid #d7e0ec !important;
  border-radius: 14px !important;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%) !important;
  box-shadow: 0 8px 20px rgba(20, 37, 66, 0.05);
}

[data-testid="stExpander"] summary {
  font-size: 15px !important;
}

.stCaption {
  color: #4d5d76 !important;
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
  font-weight: 500;
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
  font-weight: 600;
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
  font-weight: 700;
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
  background:
    radial-gradient(280px 140px at 100% 0%, rgba(216, 232, 255, 0.55) 0%, rgba(216, 232, 255, 0) 70%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
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
  font-weight: 600;
}

.upload-drop-note {
  margin-top: 8px;
  margin-bottom: 2px;
  font-size: 13px;
  color: #7b889b;
  font-weight: 600;
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
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
  color: #1e2b3f !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  box-shadow: 0 8px 18px rgba(20, 37, 66, 0.05) !important;
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
  background:
    radial-gradient(240px 130px at 50% 0%, rgba(227, 239, 255, 0.8) 0%, rgba(227, 239, 255, 0) 72%),
    #f7fbff !important;
  min-height: 220px !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

[data-testid="stFileUploaderDropzone"]::before {
  content: "Drag & drop your contract here";
  color: #1f2f49;
  font-size: 17px;
  font-weight: 700;
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
app_dir = os.path.dirname(os.path.abspath(__file__))
local_hero_candidates = [
    os.path.join(app_dir, "assets", "hero.jpg"),
    os.path.join(app_dir, "assets", "hero.jpeg"),
    os.path.join(app_dir, "assets", "hero.png"),
    os.path.join(app_dir, "assets", "professional.jpg"),
    os.path.join(app_dir, "assets", "professional.png"),
]
hero_image_source = next(
    (p for p in local_hero_candidates if os.path.exists(p)), None)
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
    st.markdown('<div class="sidebar-section-title">SETTINGS</div>',
                unsafe_allow_html=True)

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
    summary_length = st.selectbox(
        "Summary Length", ["Short", "Medium (Standard)", "Detailed"], index=2)
    risk_sensitivity = st.selectbox(
        "Risk Sensitivity", ["Conservative", "Balanced", "Aggressive"], index=1)
    contract_type = st.selectbox(
        "Contract Type", ["Auto-detect", "NDA", "MSA", "Lease", "Employment"], index=0)

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
    language = st.selectbox(
        "Language", ["Formal English", "Simple English"], index=0)

    st.markdown('<div class="sidebar-section-title">REPORT</div>',
                unsafe_allow_html=True)
    report_tone = st.selectbox(
        "Report Tone", ["Formal", "Simplified", "Legal-Professional"], index=0)
    report_structure = st.selectbox(
        "Report Structure", ["Detailed", "Concise"], index=0)
    report_focus = st.selectbox(
        "Focus Area",
        ["Balanced", "Risk-Focused", "Financial-Focused", "Legal-Focused"],
        index=0,
    )

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
if "multi_upload_mode" not in st.session_state:
    st.session_state["multi_upload_mode"] = "compare"
if "analysis_results" not in st.session_state:
    st.session_state["analysis_results"] = None

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
batch_upload_mode = multiple_upload_mode and st.session_state.get(
    "multi_upload_mode") == "batch"

if multiple_upload_mode:
    st.markdown(
        """
<div style="margin: 10px 0 4px; font-size: 14px; font-weight: 700; color: #27476f;">
  Multiple upload option
</div>
""",
        unsafe_allow_html=True,
    )
    selected_multi_mode = st.radio(
        "Choose multiple upload type",
        options=["Compare 2 Files", "Batch Upload"],
        index=1 if batch_upload_mode else 0,
        key="multi_upload_mode_selector",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state["multi_upload_mode"] = "batch" if selected_multi_mode == "Batch Upload" else "compare"
    batch_upload_mode = st.session_state["multi_upload_mode"] == "batch"
    st.caption(
        "Selected mode: Batch Upload"
        if batch_upload_mode
        else "Selected mode: Multiple Upload (2-file comparison)"
    )
else:
    st.caption("Selected mode: Single Upload")

uploaded_file = None
uploaded_file_a = None
uploaded_file_b = None
uploaded_batch_files = []
if batch_upload_mode:
    uploaded_batch_files = st.file_uploader(
        "Upload contracts",
        type=["pdf", "docx", "txt"],
        label_visibility="collapsed",
        accept_multiple_files=True,
        key="batch_contracts_main",
    )
elif not multiple_upload_mode:
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
    "Process Batch" if batch_upload_mode else (
        "Analyze Contracts" if multiple_upload_mode else "Analyze Contract"),
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


def _is_placeholder_text(text: str) -> bool:
    value = re.sub(r"\s+", " ", (text or "").strip(" -.:")).lower()
    if not value:
        return True
    placeholders = {
        "not stated",
        "not available",
        "none stated",
        "n/a",
        "na",
        "unknown",
        "tbd",
        "not generated",
        "no output generated",
        "further review recommended",
        "risk score unavailable",
    }
    blocked_phrases = (
        "temporary ai provider failure",
        "no contract analysis was generated",
        "analysis unavailable due to provider",
        "no reliable ai risk analysis was generated",
        "provider quota exhaustion",
        "provider connection failure",
        "provider rate limiting",
        "reduce request volume",
    )
    return (
        value in placeholders
        or value.startswith("not generated because")
        or value.startswith("not generated due to")
        or any(phrase in value for phrase in blocked_phrases)
    )


def _complete_sentence(text: str) -> str:
    value = re.sub(r"\s+", " ", (text or "").strip())
    if not value:
        return ""
    trailing_terms = (" and", " or", " to", " for", " with", " without", " of", " the", " a", " an")
    lowered = value.lower().rstrip(". ")
    if value.endswith("...") or value.endswith("..") or any(lowered.endswith(term) for term in trailing_terms):
        value = re.sub(r"(\.\.\.|\.{2,})$", "", value).rstrip(" ,;:-")
        words = value.split()
        while words:
            candidate = " ".join(words)
            lowered_candidate = candidate.lower()
            if not any(lowered_candidate.endswith(term) for term in trailing_terms):
                value = candidate
                break
            words.pop()
        value = value.strip(" ,;:-")
    if not value:
        return ""
    if value[-1] not in ".!?":
        value += "."
    return value


def _strip_section_label(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    value = re.sub(
        r"^(key clauses|risks|missing\s*/\s*weak|plain summary|risk score)\s*:\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"^(key clauses|risks|missing\s*/\s*weak|plain summary)\s*-\s*", "", value, flags=re.IGNORECASE)
    return value.strip()


def _extract_candidate_sentences(text: str, limit: int = 4):
    raw_sections = _split_sections(text or "")
    section_sources = [
        raw_sections.get("Key Clauses", ""),
        raw_sections.get("Risks", ""),
        raw_sections.get("Missing / Weak", ""),
        raw_sections.get("Plain Summary", ""),
    ]
    normalized = re.sub(r"\s+", " ", "\n".join(part for part in section_sources if part).strip())
    if not normalized:
        normalized = re.sub(r"\s+", " ", (text or "").strip())
    if not normalized or _is_placeholder_text(normalized):
        return []
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    results = []
    seen = set()
    for part in parts:
        cleaned = _complete_sentence(_strip_section_label(part.lstrip("-").strip()))
        if not cleaned or _is_placeholder_text(cleaned):
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(cleaned)
        if len(results) >= limit:
            break
    return results


def _resolve_display_lines(text: str, fallback_text: str = "", limit: int = 4):
    values = []
    seen = set()
    for source in (_normalize_section_text(text), _normalize_section_text(fallback_text)):
        if not source:
            continue
        for raw_line in source.split("\n"):
            cleaned = _complete_sentence(_strip_section_label(raw_line.strip().lstrip("-").strip()))
            if not cleaned or _is_placeholder_text(cleaned):
                continue
            if cleaned.lower().startswith("risk score"):
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            values.append(cleaned)
            if len(values) >= limit:
                return values
    return values


def _infer_structured_fallbacks(result_text: str):
    raw_sections = _split_sections(result_text or "")
    raw_body = "\n".join(
        section
        for section in (
            raw_sections.get("Key Clauses", ""),
            raw_sections.get("Risks", ""),
            raw_sections.get("Missing / Weak", ""),
            raw_sections.get("Plain Summary", ""),
        )
        if section
    )
    sentences = _extract_candidate_sentences(raw_body, limit=6)
    missing_like = [
        sentence for sentence in sentences
        if any(term in sentence.lower() for term in ("missing", "unclear", "not specify", "not specified", "not define", "not defined", "absent", "silent", "weak"))
    ]
    risk_like = [
        sentence for sentence in sentences
        if any(term in sentence.lower() for term in ("risk", "liability", "termination", "indemn", "penalty", "breach", "exposure", "unclear", "missing"))
    ]
    key_clauses = _resolve_display_lines(raw_sections.get("Key Clauses", ""), fallback_text="\n".join(sentences[:3]), limit=4)
    risks = _resolve_display_lines(raw_sections.get("Risks", ""), fallback_text="\n".join((risk_like or missing_like or sentences)[:3]), limit=4)
    missing_weak = _resolve_display_lines(raw_sections.get("Missing / Weak", ""), fallback_text="\n".join((missing_like or risk_like or sentences)[:3]), limit=4)
    summary_candidates = _resolve_display_lines(raw_sections.get("Plain Summary", ""), fallback_text="\n".join(sentences[:2]), limit=2)
    summary = " ".join(summary_candidates[:2]).strip()
    if not summary:
        summary = _complete_sentence(sentences[0]) if sentences else "Summary generated from the available analysis."
    risk_score = raw_sections.get("Risk Score", "").strip() or "Risk Score: Medium"
    return {
        "Key Clauses": key_clauses,
        "Risks": risks,
        "Missing / Weak": missing_weak,
        "Plain Summary": [summary],
        "Risk Score": risk_score,
    }


def _compress_summary_sentence(text: str, target_chars: int = 120) -> str:
    cleaned = _complete_sentence(text)
    if not cleaned:
        return ""
    if len(cleaned) <= target_chars:
        return cleaned

    # Prefer trimming at natural clause boundaries while keeping a full sentence.
    boundary_patterns = [", which", ", including", ", such as", ";", " because ", " if ", " when "]
    lowered = cleaned.lower()
    for marker in boundary_patterns:
        idx = lowered.find(marker)
        if idx > 40:
            candidate = cleaned[:idx].rstrip(" ,;:-")
            candidate = _complete_sentence(candidate)
            if candidate and len(candidate) <= target_chars + 20:
                return candidate

    words = cleaned.rstrip(".").split()
    while len(" ".join(words)) > target_chars and len(words) > 8:
        words.pop()
    return _complete_sentence(" ".join(words))


def _build_preview_plain_summary(sections, fallback_sections) -> str:
    key_points = _resolve_display_lines(
        sections.get("Key Clauses", ""),
        fallback_text="\n".join(fallback_sections.get("Key Clauses", [])),
        limit=1,
    )
    risk_points = _resolve_display_lines(
        sections.get("Risks", ""),
        fallback_text="\n".join(fallback_sections.get("Risks", [])),
        limit=1,
    )
    gap_points = _resolve_display_lines(
        sections.get("Missing / Weak", ""),
        fallback_text="\n".join(fallback_sections.get("Missing / Weak", [])),
        limit=1,
    )
    summary_lines = _resolve_display_lines(
        sections.get("Plain Summary", ""),
        fallback_text="\n".join(fallback_sections.get("Plain Summary", [])),
        limit=1,
    )

    source_size = len(
        "".join(
            [
                sections.get("Key Clauses", ""),
                sections.get("Risks", ""),
                sections.get("Missing / Weak", ""),
                sections.get("Plain Summary", ""),
            ]
        )
    )
    sentence_target = 150 if source_size > 900 else 110
    max_sentences = 3 if source_size > 1400 else 2

    ordered_points = []
    seen = set()
    for point in [*key_points, *risk_points, *gap_points, *summary_lines]:
        cleaned = _complete_sentence(point)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered_points.append(cleaned)
        if len(ordered_points) >= 3:
            break

    if not ordered_points:
        return "Summary generated from the available analysis."

    primary = _compress_summary_sentence(ordered_points[0], target_chars=sentence_target)
    risk_sentence = ""
    missing_sentence = ""

    if len(ordered_points) > 1:
        risk_text = ordered_points[1].rstrip(".")
        risk_sentence = _compress_summary_sentence(
            f"The main risk is that {risk_text[:1].lower() + risk_text[1:] if risk_text else ''}.",
            target_chars=sentence_target,
        )
    if len(ordered_points) > 2 and max_sentences >= 3:
        missing_text = ordered_points[2].rstrip(".")
        missing_sentence = _compress_summary_sentence(
            f"A key missing or unclear point is that {missing_text[:1].lower() + missing_text[1:] if missing_text else ''}.",
            target_chars=sentence_target,
        )

    summary_parts = [part for part in [primary, risk_sentence, missing_sentence] if part]
    return " ".join(summary_parts[:max_sentences])


def _build_preview_bullet_block(text: str, fallback_text: str = "", limit: int = 4) -> str:
    resolved_lines = _resolve_display_lines(text, fallback_text=fallback_text, limit=limit)
    if not resolved_lines:
        return ""
    return "\n".join(f"- {line}" for line in resolved_lines)


def _extract_bullet_points(text: str, limit: int = 5):
    values = []
    seen = set()
    normalized = _normalize_section_text(text)
    for raw_line in normalized.split("\n"):
        line = _complete_sentence(raw_line.strip().lstrip("-").strip())
        if not line:
            continue
        key = line.lower()
        if key in seen or _is_placeholder_text(line):
            continue
        seen.add(key)
        values.append(line.rstrip("."))
        if len(values) >= limit:
            break
    return values


def _format_risk_factor_label(text: str, width: int = 20, max_lines: int = 3) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip(" -.:"))
    if not cleaned:
        return "Further review recommended"
    shortened = textwrap.shorten(cleaned, width=46, placeholder="...")
    lines = textwrap.wrap(shortened, width=16)[:max_lines]
    return "<br>".join(escape(line) for line in lines) if lines else escape(shortened)


def _risk_factor_title(text: str) -> str:
    lowered = (text or "").lower()
    title_rules = [
        ("for cause", "Termination Risk"),
        ("terminated", "Termination Risk"),
        ("termination", "Termination Risk"),
        ("confidential", "Confidentiality Risk"),
        ("intellectual property", "IP Risk"),
        ("property", "Property Return Risk"),
        ("permitted use", "Permitted Use Risk"),
        ("disclosure", "Disclosure Risk"),
        ("data", "Data Protection Risk"),
        ("privacy", "Privacy Risk"),
        ("payment", "Payment Risk"),
        ("compensation", "Payment Risk"),
        ("salary", "Payment Risk"),
        ("fees", "Payment Risk"),
        ("invoice", "Payment Risk"),
        ("liability", "Liability Risk"),
        ("indemn", "Indemnity Risk"),
        ("dispute", "Dispute Risk"),
        ("jurisdiction", "Jurisdiction Risk"),
        ("scope", "Scope Risk"),
        ("breach", "Breach Risk"),
        ("warranty", "Warranty Risk"),
    ]
    for keyword, title in title_rules:
        if keyword in lowered:
            return title
    words = re.findall(r"[A-Za-z]+", text or "")
    if not words:
        return "Risk Factor"
    return f"{' '.join(words[:2]).title()} Risk"


def _rewrite_legalese(text: str) -> str:
    value = re.sub(r"\s+", " ", (text or "").strip())
    if not value:
        return ""

    replacements = [
        (r"\bpayment in lieu thereof\b", "pay in place of notice"),
        (r"\bwithout any notice or payment in lieu thereof\b", "without notice or pay in place of notice"),
        (r"\bmaterial breach of this Agreement\b", "material breach of the agreement"),
        (r"\bdereliction of duties\b", "serious failure to perform duties"),
        (r"\binsubordination\b", "refusal to follow lawful instructions"),
    ]
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)

    lowered = value.lower()
    if "terminated immediately for cause" in lowered or "termination" in lowered:
        if "without notice" in lowered or "pay in place of notice" in lowered:
            return "Immediate termination for cause without notice or pay in place of notice may create employee-side dispute risk."
        return "Broad termination-for-cause language may create employee-side dispute risk."
    if "confidential" in lowered and ("disclose" in lowered or "disclosure" in lowered):
        return "Confidential information could be disclosed or misused if the confidentiality obligations are breached."
    if "property" in lowered and ("return" in lowered or "returned" in lowered):
        return "Company property return obligations may create loss or misuse risk if they are not followed at termination."

    return value


def _risk_factor_statement(text: str) -> str:
    cleaned = _rewrite_legalese(re.sub(r"\s+", " ", (text or "").strip(" -.:")))
    cleaned = _complete_sentence(cleaned)
    if cleaned and len(cleaned) > 180:
        cleaned = textwrap.shorten(cleaned, width=180, placeholder="...")
        cleaned = _complete_sentence(cleaned.rstrip("."))
    return cleaned or "Further review recommended."


def _group_risk_factors(risk_factors, risk_level: str, source_corpus: str, source_contract_text: str = ""):
    grouped = {}
    for index, factor in enumerate(risk_factors):
        title = _risk_factor_title(factor)
        statement = _risk_factor_statement(factor)
        score = _score_risk_factor(factor, risk_level, source_corpus, source_contract_text, index)
        bucket = grouped.setdefault(
            title,
            {
                "title": title,
                "statements": [],
                "statement_keys": set(),
                "scores": [],
                "order": index,
            },
        )
        statement_key = statement.lower()
        if statement and statement_key not in bucket["statement_keys"]:
            bucket["statement_keys"].add(statement_key)
            bucket["statements"].append(statement)
        bucket["scores"].append(score)

    grouped_items = []
    for item in sorted(grouped.values(), key=lambda value: value["order"]):
        item["score"] = round(sum(item["scores"]) / max(1, len(item["scores"])))
        statements = item["statements"][:2]
        if not statements:
            item["summary"] = "Further review recommended."
        elif len(statements) == 1:
            item["summary"] = statements[0]
        else:
            item["summary"] = " ".join(statements)
        grouped_items.append(item)
    return grouped_items


def _build_risk_source_corpus(source_analysis: str = "", source_contract_text: str = "", agent_outputs=None) -> str:
    chunks = []
    if source_contract_text:
        chunks.append(source_contract_text)
    if source_analysis:
        chunks.append(source_analysis)
    if isinstance(agent_outputs, dict):
        chunks.extend(str(value) for value in agent_outputs.values() if value)
    return "\n".join(chunks)


def _derive_risk_level(sections, source_analysis: str = "", fallback: str = "Medium") -> str:
    raw_sections = _split_sections(source_analysis or "")
    candidates = [
        raw_sections.get("Risk Score", ""),
        sections.get("Overall Risk Rating", ""),
        fallback,
    ]
    for candidate in candidates:
        resolved = _resolve_risk_level(candidate)
        if resolved:
            return resolved
    return "Medium"


def _derive_document_risk_signals(source_contract_text: str = "", limit: int = 6):
    text = (source_contract_text or "").lower()
    if not text:
        return []
    checks = [
        ("Liability cap or limitation language is not clearly stated.", (r"\bliability\b", r"\blimit(?:ation)? of liability\b|\bliability cap\b|\baggregate liability\b")),
        ("Termination rights or exit triggers are not clearly defined.", (r"\bterminate|termination|for cause|for convenience\b", r"\bterminate|termination\b")),
        ("Indemnity allocation is missing or unclear.", (r"\bindemn", r"\bindemn")),
        ("Dispute resolution and governing law terms are not explicit.", (r"\bgoverning law|jurisdiction|venue|arbitration|dispute resolution\b", r"\bgoverning law|jurisdiction|arbitration\b")),
        ("Confidentiality or data-protection language appears limited.", (r"\bconfidential|non-disclosure|privacy|data protection|personal data\b", r"\bconfidential|non-disclosure|privacy|data protection\b")),
    ]
    signals = []
    for message, (presence_pattern, strength_pattern) in checks:
        has_presence = re.search(presence_pattern, text) is not None
        has_strength = re.search(strength_pattern, text) is not None
        if not has_presence or not has_strength:
            signals.append(message)
        if len(signals) >= limit:
            break
    return signals


def _extract_distinct_risk_factors(sections, source_analysis: str = "", source_contract_text: str = "", agent_outputs=None, limit: int = 6):
    raw_sections = _split_sections(source_analysis or "")
    candidates = []
    candidates.extend(_extract_bullet_points(raw_sections.get("Risks", ""), limit=6))
    candidates.extend(_extract_bullet_points(raw_sections.get("Missing / Weak", ""), limit=6))
    candidates.extend(_extract_bullet_points(sections.get("Critical Issues", ""), limit=4))
    candidates.extend(_extract_bullet_points(sections.get("Missing Protections / Negotiation Gaps", ""), limit=4))
    candidates.extend(_extract_bullet_points(sections.get("Recommended Actions", ""), limit=3))
    if isinstance(agent_outputs, dict):
        for role_text in agent_outputs.values():
            agent_sections = _split_agent_sections(str(role_text or ""))
            candidates.extend(_extract_bullet_points(agent_sections.get("Risks", ""), limit=2))
            candidates.extend(_extract_bullet_points(agent_sections.get("Missing / Weak points", ""), limit=1))
    candidates.extend(_derive_document_risk_signals(
        source_contract_text, limit=3))

    values = []
    seen = set()
    for item in candidates:
        cleaned = re.sub(r"\s+", " ", (item or "").strip(" -.:"))
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen or key in {"not stated", "not stated."}:
            continue
        seen.add(key)
        values.append(cleaned)
        if len(values) >= limit:
            break
    return values or ["Further review recommended"]


def _score_risk_factor(
    factor: str,
    risk_level: str,
    source_corpus: str,
    source_contract_text: str = "",
    position: int = 0,
) -> int:
    base_scores = {
        "Low": 26,
        "Medium-Low": 38,
        "Medium": 54,
        "Medium-High": 68,
        "High": 82,
        "Critical": 92,
    }
    factor_lower = (factor or "").lower()
    corpus_lower = (source_corpus or "").lower()
    score = base_scores.get(risk_level, 54)

    severity_bonuses = {
        10: ("termination", "indemn", "liability", "unlimited", "breach", "penalty"),
        8: ("privacy", "personal data", "security", "confidential", "dispute", "jurisdiction"),
        7: ("payment", "fees", "invoice", "late payment", "renewal", "auto-renew"),
        6: ("sla", "service level", "uptime", "delivery", "acceptance", "warranty"),
        5: ("notice", "audit", "insurance", "maintenance", "utilities"),
    }
    for bonus, keywords in severity_bonuses.items():
        if any(keyword in factor_lower for keyword in keywords):
            score += bonus
            break

    if any(term in factor_lower for term in ("missing", "unclear", "not stated", "not defined", "weak", "silent", "absent")):
        score += 6

    tokens = [
        token for token in re.findall(r"[a-z]{4,}", factor_lower)
        if token not in {"that", "this", "with", "from", "under", "there", "their", "party", "clause", "contract", "agreement"}
    ]
    evidence_hits = sum(1 for token in dict.fromkeys(tokens) if token in corpus_lower)
    score += min(10, evidence_hits * 2)

    document_lower = (source_contract_text or "").lower()
    if document_lower:
        doc_hits = sum(
            len(re.findall(rf"\b{re.escape(token)}\b", document_lower))
            for token in dict.fromkeys(tokens[:6])
        )
        score += min(12, doc_hits)
        if factor_lower and factor_lower in document_lower:
            score += 4

    score -= min(8, position * 2)
    return max(18, min(96, score))


def _find_risk_factor_evidence(factor: str, source_corpus: str) -> str:
    if not source_corpus:
        return ""
    tokens = [
        token for token in re.findall(r"[a-z]{4,}", (factor or "").lower())
        if token not in {"that", "this", "with", "from", "under", "there", "their", "party", "clause", "contract", "agreement"}
    ]
    lines = []
    for raw_line in source_corpus.splitlines():
        normalized = re.sub(r"\s+", " ", raw_line.strip())
        lowered = normalized.lower()
        if not normalized or normalized.endswith(":"):
            continue
        if any(token in lowered for token in tokens[:4]):
            lines.append(normalized.lstrip("- ").strip())
        if len(lines) >= 2:
            break
    if not lines:
        return ""
    combined = " ".join(lines)
    return textwrap.shorten(combined, width=110, placeholder="...")


def _escape_attr(value: str) -> str:
    return escape(str(value or ""), quote=True)


def _resolve_risk_level(raw_value: str) -> str:
    raw = (raw_value or "").strip()
    lowered = raw.lower()
    if "critical" in lowered:
        return "Critical"
    if "medium-high" in lowered or "medium high" in lowered:
        return "Medium-High"
    if "medium-low" in lowered or "medium low" in lowered:
        return "Medium-Low"
    if "high" in lowered:
        return "High"
    if "medium" in lowered:
        return "Medium"
    if "low" in lowered:
        return "Low"
    return raw or "Medium"


def _risk_visual_config(risk_level: str):
    configs = {
        "Low": {
            "pill": "#e8f7ec",
            "pill_border": "#bfe7c9",
            "pill_text": "#246b3b",
            "marker_color": "#2cab5b",
            "marker_angle": 218,
        },
        "Medium-Low": {
            "pill": "#eef7df",
            "pill_border": "#d7e9b8",
            "pill_text": "#567529",
            "marker_color": "#7caf3a",
            "marker_angle": 245,
        },
        "Medium": {
            "pill": "#fff4d6",
            "pill_border": "#efd48a",
            "pill_text": "#7b5d07",
            "marker_color": "#f0b52a",
            "marker_angle": 270,
        },
        "Medium-High": {
            "pill": "#fff0e1",
            "pill_border": "#f0c999",
            "pill_text": "#8a4d14",
            "marker_color": "#de7b2b",
            "marker_angle": 312,
        },
        "High": {
            "pill": "#ffe6e1",
            "pill_border": "#f0b9ae",
            "pill_text": "#8d2d20",
            "marker_color": "#df524b",
            "marker_angle": 334,
        },
        "Critical": {
            "pill": "#ffe1ea",
            "pill_border": "#edafc0",
            "pill_text": "#76152a",
            "marker_color": "#b62645",
            "marker_angle": 348,
        },
    }
    return configs.get(risk_level, configs["Medium"])


def _render_risk_overview(
    sections,
    source_analysis: str = "",
    source_contract_text: str = "",
    agent_outputs=None,
    fallback_risk_label: str = "Medium",
):
    risk_level = _derive_risk_level(
        sections,
        source_analysis=source_analysis,
        fallback=fallback_risk_label,
    )
    risk_factors = _extract_distinct_risk_factors(
        sections,
        source_analysis=source_analysis,
        source_contract_text=source_contract_text,
        agent_outputs=agent_outputs,
        limit=6,
    )
    source_corpus = _build_risk_source_corpus(
        source_analysis=source_analysis,
        source_contract_text=source_contract_text,
        agent_outputs=agent_outputs,
    )
    grouped_risk_factors = _group_risk_factors(
        risk_factors,
        risk_level=risk_level,
        source_corpus=source_corpus,
        source_contract_text=source_contract_text,
    )
    factor_cards = "".join(
        f"""
<div class="risk-factor-card">
  <div class="risk-factor-card-head" style="background:linear-gradient(135deg, #214d85 0%, #173864 100%);">{escape(item["title"])}</div>
  <div class="risk-factor-card-body">
    <div class="risk-factor-mini-ring" style="background:conic-gradient(#214d85 0% {item["score"]}%, #d7dde7 {item["score"]}% 100%);">
      <div class="risk-factor-mini-center">
        <div class="risk-factor-mini-score">{item["score"]}</div>
        <div class="risk-factor-mini-label">risk %</div>
      </div>
    </div>
    <div class="risk-factor-card-copy">{escape(item["summary"])}</div>
  </div>
</div>
"""
        for item in grouped_risk_factors
    )
    with st.container(border=True):
        st.markdown(
            f'<div class="section-title">Overall Risk Rating: <span style="font-weight:800;color:#193153;">{escape(risk_level)}</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="risk-factor-card-grid">{factor_cards}</div>',
            unsafe_allow_html=True,
        )


def _split_agent_sections(text: str):
    sections = {
        "Findings": "",
        "Risks": "",
        "Missing / Weak points": "",
        "Recommended follow-up actions": "",
    }
    aliases = {
        "findings": "Findings",
        "key clauses": "Findings",
        "risks": "Risks",
        "missing / weak points": "Missing / Weak points",
        "missing / weak": "Missing / Weak points",
        "recommended follow-up actions": "Recommended follow-up actions",
        "recommended actions": "Recommended follow-up actions",
    }
    current = None
    for line in (text or "").splitlines():
        stripped = line.strip().replace("**", "")
        heading = re.sub(r"^\d+\s*[\)\.\-:]\s*", "",
                         stripped).rstrip(":").strip().lower()
        canonical = aliases.get(heading)
        if canonical:
            current = canonical
            continue
        if current:
            sections[current] += line + "\n"
    return sections


def _sanitize_agent_section_text(text: str, section_name: str) -> str:
    lines = []
    for raw_line in _normalize_section_text(text).split("\n"):
        value = _complete_sentence(raw_line.strip())
        if not value:
            continue
        plain = value.lstrip("-").strip()
        if _is_placeholder_text(plain):
            continue
        lines.append(value)
    if lines:
        return "\n".join(lines)
    if section_name == "Recommended follow-up actions":
        return "Review the source contract and add a complete follow-up action for the unresolved issue."
    return "No additional document-specific details were available for this section."


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

    fallback_sections = _infer_structured_fallbacks(body)
    lines = [title, ""]
    for section_name in ("Key Clauses", "Risks", "Missing / Weak", "Plain Summary"):
        if section_name == "Plain Summary":
            section_body = _build_preview_plain_summary(sections, fallback_sections)
        else:
            section_body = _build_preview_bullet_block(
                sections[section_name],
                fallback_text="\n".join(fallback_sections.get(section_name, [])),
                limit=3 if section_name == "Key Clauses" else 2,
            )
        if not section_body and not include_empty:
            continue
        if not section_body:
            section_body = "No supported detail was available for this section."
        lines.append(f"{section_name}:")
        lines.append(section_body)
        lines.append("")
    if include_risk:
        risk_score = sections["Risk Score"].strip() or fallback_sections["Risk Score"]
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
        fallback_sections = _infer_structured_fallbacks(result_text or "")
        rows = []
        for section_name in ("Key Clauses", "Risks", "Missing / Weak", "Plain Summary"):
            if section_name == "Plain Summary":
                section_body = _build_preview_plain_summary(sections, fallback_sections)
            else:
                section_body = _build_preview_bullet_block(
                    sections[section_name],
                    fallback_text="\n".join(fallback_sections.get(section_name, [])),
                    limit=3 if section_name == "Key Clauses" else 2,
                )
            if not section_body and not include_empty:
                continue
            if not section_body:
                section_body = "No supported detail was available for this section."
            rows.append(
                f"""
<div style="margin-top:12px;">
  <div style="font-size:14px; font-weight:700; color:#223553; letter-spacing:0.01em;">{escape(section_name)}</div>
  <div style="margin-top:6px; white-space: pre-wrap; line-height:1.7; font-weight:560; color:#233047;">{escape(section_body)}</div>
</div>
"""
            )
        risk_score = sections["Risk Score"].strip() or fallback_sections["Risk Score"]
    else:
        raw_body = _normalize_section_text(
            (result_text or "").strip()) or "No output generated."
        rows = [
            f"""
<div style="margin-top:12px;">
  <div style="font-size:14px; font-weight:700; color:#223553; letter-spacing:0.01em;">Analysis</div>
  <div style="margin-top:6px; white-space: pre-wrap; line-height:1.7; font-weight:560; color:#233047;">{escape(raw_body)}</div>
</div>
"""
        ]
        risk_score = "Risk Score: Medium"
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


def _render_agent_breakdown_content(agent_outputs):
    if not agent_outputs:
        st.caption("No agent output available.")
        st.info("No agent output generated.")
        return

    role_items = list(agent_outputs.items())
    tabs = st.tabs([role_name.title() for role_name, _ in role_items])
    for tab, (role_name, role_text) in zip(tabs, role_items):
        with tab:
            sections = _split_agent_sections(role_text)
            rows = []
            for section_name in (
                "Findings",
                "Risks",
                "Missing / Weak points",
                "Recommended follow-up actions",
            ):
                section_body = _sanitize_agent_section_text(
                    sections.get(section_name, ""),
                    section_name,
                )
                if not section_body:
                    section_body = "No additional document-specific details were available for this section."
                rows.append(
                    f"""
<div style="margin-top:12px;">
  <div style="font-size:14px; font-weight:700; color:#223553; letter-spacing:0.01em;">{escape(section_name)}</div>
  <div style="margin-top:6px; white-space: pre-wrap; line-height:1.7; font-weight:560; color:#233047;">{escape(section_body)}</div>
</div>
"""
                )
            st.markdown(
                f"""
<div class="document-box" style="margin-bottom:12px;">
  <div class="section-title">{escape(role_name.title() + " Agent Analysis")}</div>
  {''.join(rows)}
</div>
""",
                unsafe_allow_html=True,
            )


# Show per-agent detail in tabs so users can inspect specialist reasoning.
def _render_agent_breakdown(agent_outputs, state_key: str = "single_agent_analysis_open"):
    if state_key not in st.session_state:
        st.session_state[state_key] = False
    with st.expander("View agent-by-agent analysis", expanded=st.session_state.get(state_key, False)):
        _render_agent_breakdown_content(agent_outputs)


# Convert report text to RTF bytes so users can download a Word-compatible file.
@st.cache_data(show_spinner=False, max_entries=64)
def _build_word_rtf_bytes(result_text: str) -> bytes:
    text = (result_text or "").replace(
        "\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    text = text.replace("\r\n", "\n").replace(
        "\r", "\n").replace("\n", r"\par " + "\n")
    rtf = r"{\rtf1\ansi\deff0{\fonttbl{\f0 Calibri;}}\f0\fs22 " + text + "}"
    return rtf.encode("utf-8")


# Build a lightweight PDF in code so export works without extra PDF dependencies.
@st.cache_data(show_spinner=False, max_entries=64)
def _build_simple_pdf_bytes(result_text: str) -> bytes:
    page_width = 612
    page_height = 792
    margin = 50
    line_height = 14
    start_y = page_height - margin
    wrap_width = 92
    max_lines_per_page = max(
        1, int((page_height - (2 * margin)) / line_height))

    # Escape PDF-sensitive characters to keep generated content stream valid.
    def _safe_pdf_text(line: str) -> str:
        normalized = line.encode("latin-1", "replace").decode("latin-1")
        return normalized.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    logical_lines = []
    for raw_line in (result_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        wrapped = textwrap.wrap(
            raw_line, width=wrap_width) if raw_line.strip() else [""]
        logical_lines.extend(wrapped)

    if not logical_lines:
        logical_lines = ["No output generated."]

    pages = [logical_lines[i:i + max_lines_per_page]
             for i in range(0, len(logical_lines), max_lines_per_page)]

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
            b"<< /Length " + str(len(stream_data)).encode("ascii") +
            b" >>\nstream\n" + stream_data + b"\nendstream"
        )
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R "
            + f"/MediaBox [0 0 {page_width} {page_height}] ".encode("ascii")
            + b"/Resources << /Font << /F1 3 0 R >> >> "
            + f"/Contents {content_id} 0 R >>".encode("ascii")
        )

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[2] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode(
        "ascii")

    max_id = max(objects.keys())
    parts = [b"%PDF-1.4\n"]
    offsets = [0] * (max_id + 1)
    current_offset = len(parts[0])

    for obj_id in range(1, max_id + 1):
        offsets[obj_id] = current_offset
        block = f"{obj_id} 0 obj\n".encode(
            "ascii") + objects[obj_id] + b"\nendobj\n"
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

    trailer = f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
        "ascii")
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


def _feedback_rating_value(raw_value) -> int | None:
    if raw_value is None:
        return None
    try:
        numeric = int(raw_value)
    except (TypeError, ValueError):
        return None
    return numeric + 1 if 0 <= numeric <= 4 else numeric


def _store_feedback(report_text: str, rating: int | None, notes: str, context: str):
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "helpful": bool(rating and rating >= 4),
        "rating": rating,
        "notes": (notes or "").strip(),
        "context": context,
        "report_preview": (report_text or "")[:1000],
    }
    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "report_feedback.jsonl"), "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _render_feedback_section(
    report_text: str,
    feedback_key_prefix: str,
    feedback_status_key: str,
    report_open_key: str,
    reports_expander_open_key: str,
    related_agent_state_key: str | None = None,
):
    st.markdown('<div class="feedback-bar"></div>', unsafe_allow_html=True)
    st.markdown(
        """
<div class="feedback-rating-card">
  <div class="feedback-rating-title">Please Rate Your Experience</div>
  <div class="feedback-rating-copy">Your feedback helps us improve the quality of contract review.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    feedback_raw = st.feedback("stars", key=f"{feedback_key_prefix}_stars")
    rating = _feedback_rating_value(feedback_raw)

    if rating:
        st.caption(f"Selected rating: {rating}/5")

    feedback_notes = ""
    if rating is not None and rating < 5:
        feedback_notes = st.text_area(
            "Optional feedback",
            key=f"{feedback_key_prefix}_notes",
            placeholder="Share any issue, concern, or suggested improvement...",
            height=110,
        )
    else:
        st.session_state.pop(f"{feedback_key_prefix}_notes", None)

    submit_disabled = rating is None
    if st.button(
        "Submit Feedback",
        key=f"{feedback_key_prefix}_submit_feedback",
        use_container_width=True,
        disabled=submit_disabled,
    ):
        _store_feedback(report_text, rating, feedback_notes, feedback_key_prefix)
        st.session_state[feedback_status_key] = "Thank you for submitting the feedback."
        st.session_state[report_open_key] = True
        st.session_state[reports_expander_open_key] = True
        if related_agent_state_key:
            st.session_state[related_agent_state_key] = True

    if st.session_state.get(feedback_status_key):
        st.success(st.session_state[feedback_status_key])


def _render_loading_skeleton(label: str):
    st.markdown(
        f"""
<div class="document-box" style="margin-bottom:12px;">
  <div class="section-title">{escape(label)}</div>
  <div class="skeleton-card"></div>
</div>
""",
        unsafe_allow_html=True,
    )


def _generate_report_with_progress(
    result_text: str,
    agent_outputs,
    report_options,
    show_progress: bool = True,
    source_contract_text: str = "",
):
    progress_placeholder = st.empty() if show_progress else None
    if progress_placeholder is not None:
        progress_placeholder.markdown(_build_stage_markdown(
            "Generating report..."), unsafe_allow_html=True)
    report_payload = generate_report(
        result_text, agent_outputs, report_options)
    if isinstance(report_payload, dict):
        report_payload["source_analysis"] = result_text
        report_payload["source_agent_outputs"] = agent_outputs or {}
        report_payload["source_contract_text"] = source_contract_text or ""
    if progress_placeholder is not None:
        progress_placeholder.empty()
    return report_payload


def _ensure_report_payload(
    container: dict,
    payload_key: str,
    result_text: str,
    agent_outputs,
    report_options,
    source_contract_text: str = "",
):
    existing = container.get(payload_key)
    if existing:
        return existing
    payload = _generate_report_with_progress(
        result_text,
        agent_outputs,
        report_options,
        source_contract_text=source_contract_text,
    )
    container[payload_key] = payload
    return payload


@contextmanager
def _temporary_env(overrides: dict[str, str]):
    previous = {key: os.getenv(key) for key in overrides}
    try:
        for key, value in overrides.items():
            os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _lightweight_analysis_env() -> dict[str, str]:
    return {
        "CLAUSEAI_DEEP_ANALYSIS": "0",
        "CLAUSEAI_ENABLE_MULTI_TURN_AGENT_INTERACTION": "0",
        "CLAUSEAI_ENABLE_PARALLEL_CLAUSE_EXTRACTION": "0",
        "CLAUSEAI_AGENT_WORKERS": "1",
        "CLAUSEAI_CLAUSE_WORKERS": "1",
    }


def _ensure_agent_outputs(
    container: dict,
    payload_key: str,
    pages,
    contract_type: str = "Auto-detect",
):
    existing = container.get(payload_key)
    if isinstance(existing, dict) and existing:
        return existing
    progress_placeholder = st.empty()
    progress_placeholder.markdown(_build_stage_markdown(
        "Planning agent execution..."), unsafe_allow_html=True)
    try:
        with _temporary_env({
            "CLAUSEAI_AGENT_WORKERS": "1",
            "CLAUSEAI_ENABLE_MULTI_TURN_AGENT_INTERACTION": "0",
        }):
            payload = analyze_agent_breakdown(
                pages,
                contract_type=contract_type,
                progress_callback=lambda stage: progress_placeholder.markdown(
                    _build_stage_markdown(stage),
                    unsafe_allow_html=True,
                ),
            )
    finally:
        progress_placeholder.empty()
    container[payload_key] = payload
    return payload


def _key_highlights(report_text: str, raw_text: str = ""):
    sections = _split_sections(report_text or "")
    fallback_sections = _infer_structured_fallbacks(raw_text or report_text or "")
    risk_score = sections.get(
        "Risk Score", "").strip() or fallback_sections["Risk Score"]

    def _pick_points(section_name: str, limit: int = 2):
        resolved = _resolve_display_lines(
            sections.get(section_name, ""),
            fallback_text="\n".join(fallback_sections.get(section_name, [])),
            limit=limit,
        )
        return resolved or fallback_sections.get(section_name, [])[:limit] or ["No supported detail available."]

    return {
        "risk_score": risk_score,
        "key_clauses": _pick_points("Key Clauses", limit=2),
        "risks": _pick_points("Risks", limit=2),
        "missing_weak": _pick_points("Missing / Weak", limit=2),
        "summary": _pick_points("Plain Summary", limit=1),
    }


def _render_generated_report(
    report_payload,
    file_stem: str,
    feedback_key_prefix: str,
    show_view_button: bool = True,
    force_open: bool = False,
    header_title: str = "Generated Report",
    related_agent_state_key: str | None = None,
    container: dict | None = None,
    payload_key: str | None = None,
    result_text: str = "",
    agent_outputs=None,
    report_options: ReportOptions | None = None,
    source_contract_text: str = "",
):
    report_open_key = f"{feedback_key_prefix}_report_open"
    feedback_status_key = f"{feedback_key_prefix}_feedback_status"
    reports_expander_open_key = f"{feedback_key_prefix}_reports_expander_open"

    if report_open_key not in st.session_state:
        st.session_state[report_open_key] = False
    if feedback_status_key not in st.session_state:
        st.session_state[feedback_status_key] = ""

    if show_view_button and st.button("View Report", key=f"{feedback_key_prefix}_view_report", use_container_width=True):
        st.session_state[report_open_key] = True
        if related_agent_state_key:
            st.session_state[related_agent_state_key] = True
    if not force_open and not st.session_state.get(report_open_key):
        return
    if not report_payload and container is not None and payload_key and report_options is not None:
        report_payload = _ensure_report_payload(
            container,
            payload_key,
            result_text,
            agent_outputs or {},
            report_options,
            source_contract_text=source_contract_text,
        )

    sections = report_payload.get("sections", {}) if isinstance(
        report_payload, dict) else {}
    metadata = report_payload.get("metadata", {}) if isinstance(
        report_payload, dict) else {}
    report_text = report_payload.get("report_text", "") if isinstance(
        report_payload, dict) else str(report_payload or "")
    source_analysis = report_payload.get("source_analysis", "") if isinstance(
        report_payload, dict) else ""
    source_contract_text = report_payload.get("source_contract_text", "") if isinstance(
        report_payload, dict) else source_contract_text
    source_agent_outputs = report_payload.get("source_agent_outputs", {}) if isinstance(
        report_payload, dict) else (agent_outputs or {})
    fallback_analysis = _infer_structured_fallbacks(source_analysis or result_text or report_text)
    executive_summary = _complete_sentence(
        sections.get("Executive Summary")
        or fallback_analysis["Plain Summary"][0]
        or "Summary generated from the available analysis."
    )
    report_objective = _complete_sentence(
        sections.get("Report Objective")
        or "Provide a contract review highlighting obligations, risks, weak protections, and recommended next steps."
    )
    document_profile = sections.get("Document Profile") or "\n".join([
        "- Document type: Auto-detected from uploaded contract analysis.",
        "- Review scope: Contract obligations, risk exposure, and weak protections.",
        f"- Current assessment basis: {executive_summary}",
    ])
    source_risk_chip = _split_sections(source_analysis or result_text).get("Risk Score", "").strip()
    risk_chip = source_risk_chip or metadata.get("risk_score", fallback_analysis["Risk Score"].replace("Risk Score:", "").strip())
    section_names = (
        "Overall Risk Rating",
        "Critical Issues",
        "Key Obligations",
        "Missing Protections / Negotiation Gaps",
        "Recommended Actions",
        "Conclusion",
        "Appendix - Supporting Notes",
    )

    with st.container():
        st.markdown(
            f'<div class="sticky-analysis-header"><h3 style="margin:0;">{escape(header_title)}</h3></div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Generated report - Overall Risk Score: {risk_chip}")
        summary_tab, profile_tab = st.tabs(["Executive Summary", "Document Profile"])
        with summary_tab:
            st.markdown(
                f"""
<div class="document-box" style="margin-bottom:12px;">
  <div style="font-size:14px;font-weight:700;color:#244266;margin-bottom:6px;">Executive Summary</div>
  <div style="white-space:pre-wrap;line-height:1.7;">{escape(executive_summary)}</div>
  <div style="margin-top:14px;font-size:14px;font-weight:700;color:#244266;">Report Objective</div>
  <div style="margin-top:6px;white-space:pre-wrap;line-height:1.7;">{escape(report_objective)}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with profile_tab:
            st.markdown(
                f"""
<div class="document-box" style="margin-bottom:12px;">
  <div style="font-size:14px;font-weight:700;color:#244266;letter-spacing:0.01em;">Document Profile</div>
  <div style="margin-top:8px;white-space:pre-wrap;line-height:1.7;font-weight:560;color:#24354f;">{escape(document_profile)}</div>
</div>
""",
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            report_tabs = st.tabs(list(section_names))
            for tab, section_name in zip(report_tabs, section_names):
                with tab:
                    if section_name == "Overall Risk Rating":
                        _render_risk_overview(
                            sections,
                            source_analysis=source_analysis,
                            source_contract_text=source_contract_text,
                            agent_outputs=source_agent_outputs,
                            fallback_risk_label=risk_chip,
                        )
                    else:
                        section_body = sections.get(section_name, "").strip()
                        if not section_body:
                            fallback_map = {
                                "Critical Issues": "\n".join(f"- {item}" for item in fallback_analysis["Risks"]),
                                "Key Obligations": "\n".join(f"- {item}" for item in fallback_analysis["Key Clauses"]),
                                "Missing Protections / Negotiation Gaps": "\n".join(f"- {item}" for item in fallback_analysis["Missing / Weak"]),
                                "Recommended Actions": "\n".join(
                                    f"- Review and address: {item.rstrip('.')}."
                                    for item in fallback_analysis["Missing / Weak"][:3]
                                ) or "- Review the highlighted risks and confirm whether additional protections are needed.",
                                "Conclusion": executive_summary,
                                "Appendix - Supporting Notes": "\n".join(
                                    f"- {item}" for item in (
                                        fallback_analysis["Key Clauses"][:1]
                                        + fallback_analysis["Risks"][:2]
                                        + fallback_analysis["Missing / Weak"][:1]
                                    )
                                ),
                            }
                            section_body = fallback_map.get(section_name, "")
                        section_body = _normalize_section_text(section_body)
                        if not section_body:
                            section_body = "No supported detail was available for this section."
                        st.markdown(
                            f"""
<div class="document-box" style="margin-bottom:12px;">
  <div class="section-title">{escape(section_name)}</div>
  <div style="white-space:pre-wrap;line-height:1.7;font-weight:560;color:#24354f;">{escape(section_body)}</div>
</div>
""",
                            unsafe_allow_html=True,
                        )

            download_col_1, download_col_2 = st.columns([1.2, 1.2])
            with download_col_1:
                st.download_button(
                    "Download PDF",
                    data=build_report_pdf_bytes(report_text),
                    file_name=f"{file_stem}_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            with download_col_2:
                st.download_button(
                    "Download DOCX",
                    data=build_report_docx_bytes(report_text, metadata),
                    file_name=f"{file_stem}_report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

            _render_feedback_section(
                report_text=report_text,
                feedback_key_prefix=feedback_key_prefix,
                feedback_status_key=feedback_status_key,
                report_open_key=report_open_key,
                reports_expander_open_key=reports_expander_open_key,
                related_agent_state_key=related_agent_state_key,
            )


def _render_batch_results(batch_results):
    if not batch_results:
        st.info("No batch results available yet.")
        return

    st.markdown(
        '<div class="sticky-analysis-header"><h3 style="margin:0;">Batch Analysis</h3></div>',
        unsafe_allow_html=True,
    )
    batch_tabs = st.tabs([item["name"] for item in batch_results])

    for tab, item in zip(batch_tabs, batch_results):
        with tab:
            state = item.get("status", "Unknown")
            chip_class = (
                "chip-green"
                if state == "Completed"
                else ("chip-red" if state == "Failed" else "chip-blue")
            )
            st.markdown(
                f"<div style='margin-bottom:12px;'><span class='chip {chip_class}'>{escape(state)}</span></div>",
                unsafe_allow_html=True,
            )
            if item["status"] != "Completed":
                st.error(item.get("error", "Unknown batch-processing error."))
                continue
            _render_full_output_box(
                item["complete_report"], title=f"{item['name']} Document Preview")
            agent_state_key = f"{item['feedback_key_prefix']}_agent_open"
            if agent_state_key not in st.session_state:
                st.session_state[agent_state_key] = False
            if st.button("View Agent Analysis", key=f"{item['feedback_key_prefix']}_view_agents", use_container_width=True):
                st.session_state[agent_state_key] = True
            if st.session_state.get(agent_state_key):
                with st.expander("Agent-by-agent analysis", expanded=True):
                    _render_agent_breakdown_content(item.get("agent_outputs", {}))

            _render_generated_report(
                item.get("report_payload"),
                file_stem=item["file_stem"],
                feedback_key_prefix=item["feedback_key_prefix"],
                header_title=f"{item['name']} Generated Report",
                container=item,
                payload_key="report_payload",
                result_text=item.get("result_text", ""),
                agent_outputs=item.get("agent_outputs", {}),
                report_options=ReportOptions(
                    tone=report_tone,
                    structure=report_structure,
                    focus_area=report_focus,
                ),
                source_contract_text=item.get("source_contract_text", ""),
            )


def _render_single_results(single_result):
    st.markdown('<div class="sticky-analysis-header"><h3 style="margin:0;">AI Analysis</h3></div>',
                unsafe_allow_html=True)
    _render_full_output_box(
        single_result["complete_report"], title="AI Analysis Document Preview")
    if st.button("View Agent Analysis", key="single_view_agents", use_container_width=True):
        st.session_state["single_agent_analysis_open"] = True
    if st.session_state.get("single_agent_analysis_open"):
        _render_agent_breakdown(single_result.get("agent_outputs"), state_key="single_agent_analysis_open")
    if single_result.get("report_payload") is None:
        if st.button("Generate Detailed Report", key="generate_report_btn", use_container_width=True):
            time.sleep(2)
            report_payload = _generate_report_with_progress(
                single_result.get("result_text", ""),
                single_result.get("agent_outputs", {}),
                single_result.get(
                    "report_options",
                    ReportOptions(
                        tone=report_tone,
                        structure=report_structure,
                        focus_area=report_focus,
                    ),
                ),
                source_contract_text=single_result.get("source_contract_text", ""),
            )
            single_result["report_payload"] = report_payload
            st.session_state["analysis_results"] = single_result
        else:
            st.info("Click 'Generate Detailed Report' above when you are ready.")
    if single_result.get("report_payload") is not None:
        _render_generated_report(
            single_result.get("report_payload"),
            file_stem=single_result["file_stem"],
            feedback_key_prefix=single_result["feedback_key_prefix"],
            container=single_result,
            payload_key="report_payload",
            result_text=single_result.get("result_text", ""),
            agent_outputs=single_result.get("agent_outputs", {}),
            report_options=single_result.get(
                "report_options",
                ReportOptions(
                    tone=report_tone,
                    structure=report_structure,
                    focus_area=report_focus,
                ),
            ),
            source_contract_text=single_result.get("source_contract_text", ""),
        )


def _render_compare_results(compare_result):
    file_name_a = compare_result.get("file_name_a", "Contract 1")
    file_name_b = compare_result.get("file_name_b", "Contract 2")
    file_stem_a = compare_result.get("file_stem_a", "contract_1_analysis")
    file_stem_b = compare_result.get("file_stem_b", "contract_2_analysis")
    feedback_key_prefix_a = compare_result.get(
        "feedback_key_prefix_a", "multi_report_a")
    feedback_key_prefix_b = compare_result.get(
        "feedback_key_prefix_b", "multi_report_b")

    st.subheader("Multi-Contract Analysis")
    view_tab_1, view_tab_2, compare_tab = st.tabs(
        [file_name_a, file_name_b, "Compare Contracts"])
    with view_tab_1:
        _render_full_output_box(
            compare_result["complete_report_a"], title=f"{file_name_a} Document Preview")
    with view_tab_2:
        _render_full_output_box(
            compare_result["complete_report_b"], title=f"{file_name_b} Document Preview")
    with compare_tab:
        st.markdown("### Important Key Highlights")
        if compare_result.get("fast_mode"):
            st.info("Fast mode generates summary-only output. Comparison highlights may rely more heavily on inferred summaries and extracted risk cues.")

        def _fmt_points_html(items, limit: int = 2):
            values = items if items else ["No supported detail available."]
            bullet_items = "".join(
                f"<li>{escape(str(point))}</li>" for point in values[:limit])
            return f"<ul style='margin:0; padding-left:18px;'>{bullet_items}</ul>"

        compare_rows = [
            ("Risk Score", f"<div>{escape(compare_result['highlights_a']['risk_score'])}</div>",
             f"<div>{escape(compare_result['highlights_b']['risk_score'])}</div>"),
            ("Key Clauses", _fmt_points_html(compare_result["highlights_a"]["key_clauses"], limit=2), _fmt_points_html(
                compare_result["highlights_b"]["key_clauses"], limit=2)),
            ("Top Risks", _fmt_points_html(compare_result["highlights_a"]["risks"], limit=2), _fmt_points_html(
                compare_result["highlights_b"]["risks"], limit=2)),
            ("Missing / Weak", _fmt_points_html(compare_result["highlights_a"]["missing_weak"], limit=1), _fmt_points_html(
                compare_result["highlights_b"]["missing_weak"], limit=1)),
            ("Summary", _fmt_points_html(compare_result["highlights_a"]["summary"], limit=1), _fmt_points_html(
                compare_result["highlights_b"]["summary"], limit=1)),
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
    <div><strong>{escape(file_name_a)}</strong></div>
    <div><strong>{escape(file_name_b)}</strong></div>
  </div>
  {row_html}
</div>
""",
            unsafe_allow_html=True,
        )

    compare_agent_expander_key = "compare_agent_analysis_open"
    if compare_agent_expander_key not in st.session_state:
        st.session_state[compare_agent_expander_key] = False
    if st.button("View Agent Analysis", key="compare_view_agents_button", use_container_width=True):
        st.session_state[compare_agent_expander_key] = True
    if st.session_state.get(compare_agent_expander_key):
        agent_tabs = st.tabs([file_name_a, file_name_b])
        agent_items = [
            (agent_tabs[0], "agent_outputs_a"),
            (agent_tabs[1], "agent_outputs_b"),
        ]
        for tab, payload_key in agent_items:
            with tab:
                _render_agent_breakdown_content(compare_result.get(payload_key, {}))

    keep_reports_open = any(
        st.session_state.get(f"{prefix}_reports_expander_open", False)
        for prefix in [feedback_key_prefix_a, feedback_key_prefix_b]
    )
    compare_reports_open_key = "compare_reports_open"
    if st.button("View Reports", key="compare_view_reports_button", use_container_width=True):
        st.session_state[compare_reports_open_key] = True
    if keep_reports_open:
        st.session_state[compare_reports_open_key] = True

    if st.session_state.get(compare_reports_open_key):
        report_tabs = st.tabs([file_name_a, file_name_b])
        report_items = [
            ("report_payload_a", compare_result.get("result_text_a", ""), compare_result.get("agent_outputs_a", {}), compare_result.get("source_contract_text_a", ""), file_stem_a, feedback_key_prefix_a, f"{file_name_a} Generated Report"),
            ("report_payload_b", compare_result.get("result_text_b", ""), compare_result.get("agent_outputs_b", {}), compare_result.get("source_contract_text_b", ""), file_stem_b, feedback_key_prefix_b, f"{file_name_b} Generated Report"),
        ]
        for tab, (payload_key, result_text, agent_outputs, source_contract_text, file_stem, feedback_key_prefix, header_title) in zip(report_tabs, report_items):
            with tab:
                _render_generated_report(
                    compare_result.get(payload_key),
                    file_stem=file_stem,
                    feedback_key_prefix=feedback_key_prefix,
                    show_view_button=False,
                    force_open=True,
                    header_title=header_title,
                    container=compare_result,
                    payload_key=payload_key,
                    result_text=result_text,
                    agent_outputs=agent_outputs,
                    report_options=ReportOptions(
                        tone=report_tone,
                        structure=report_structure,
                        focus_area=report_focus,
                    ),
                    source_contract_text=source_contract_text,
                )


# Compute a compact unified diff so side-by-side contract changes are easy to review.
def _diff_text(a: str, b: str, limit: int = 200):
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    diff = list(difflib.unified_diff(a_lines, b_lines,
                fromfile="Contract A", tofile="Contract B", lineterm=""))
    if len(diff) > limit:
        diff = diff[:limit] + ["... diff truncated ..."]
    return "\n".join(diff)


# Load any supported upload type into a shared page-text structure for analysis.
def _load_any_contract(upload):
    if upload.name.lower().endswith(".pdf"):
        return load_pdf_pages(upload)
    if upload.name.lower().endswith(".docx"):
        return load_docx_pages(upload)
    if upload.name.lower().endswith(".txt"):
        raw = upload.read().decode("utf-8", errors="ignore")
        return [{"page": 1, "text": raw}]
    st.warning("Unsupported file format. Upload PDF, DOCX, or TXT.")
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
    report_options = ReportOptions(
        tone=report_tone,
        structure=report_structure,
        focus_area=report_focus,
    )
    analyze_kwargs = {
        "fast_mode": fast_mode,
        "summary_length": summary_length.replace(" (Standard)", ""),
        "risk_sensitivity": risk_sensitivity,
        "contract_type": contract_type,
        "output_format": output_format,
        "language": language,
        "return_agent_outputs": True,
    }

    if batch_upload_mode:
        if not uploaded_batch_files:
            st.warning("Upload at least one contract to process a batch.")
            st.stop()
        batch_items = []
        for uploaded in uploaded_batch_files:
            pages = _load_any_contract(uploaded)
            if pages:
                batch_items.append({"name": uploaded.name, "pages": pages})
        if not batch_items:
            st.stop()

        st.subheader("Batch Processing")
        progress_box = st.container()
        status_map = {item["name"]: "Queued" for item in batch_items}
        status_placeholder = progress_box.empty()
        batch_progress_placeholder = progress_box.empty()
        batch_progress_placeholder.progress(
            0, text=f"Processing 0 of {len(batch_items)} files")

        def _render_batch_status():
            status_html = "".join(
                f"""
<div class="document-box" style="margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;">
    <strong>{escape(name)}</strong>
    <span class="chip {'chip-green' if state == 'Completed' else ('chip-red' if state == 'Failed' else 'chip-blue')}">{escape(state)}</span>
  </div>
</div>
"""
                for name, state in status_map.items()
            )
            status_placeholder.markdown(status_html, unsafe_allow_html=True)

        _render_batch_status()

        def _update_batch_progress(item_result, completed_count, total_count):
            status_map[item_result["name"]] = item_result["status"]
            _render_batch_status()
            batch_progress_placeholder.progress(
                completed_count / total_count,
                text=f"Processing {completed_count} of {total_count} files",
            )

        batch_results = process_contract_batch(
            batch_items,
            analyze_kwargs,
            item_callback=_update_batch_progress,
        )
        batch_progress_placeholder.progress(
            1.0, text=f"Completed {len(batch_items)} of {len(batch_items)} files")

        cached_batch_results = []
        batch_contract_text_map = {
            item["name"]: parse_contract_text(item.get("pages", []))
            for item in batch_items
        }
        for item in batch_results:
            cached_item = {
                "name": item["name"],
                "status": item["status"],
                "error": item.get("error"),
            }
            if item["status"] == "Completed":
                result = item["result"]
                result_text = result["final_output"] if isinstance(
                    result, dict) else result
                agent_outputs = result.get(
                    "agent_outputs", {}) if isinstance(result, dict) else {}
                cached_item.update(
                    {
                        "result_text": result_text,
                        "complete_report": _build_complete_report_text(result_text, title=f"{item['name']} Analysis"),
                        "agent_outputs": agent_outputs,
                        "report_payload": None,
                        "pages": next((batch_item.get("pages", []) for batch_item in batch_items if batch_item["name"] == item["name"]), []),
                        "contract_type": contract_type,
                        "source_contract_text": batch_contract_text_map.get(item["name"], ""),
                        "file_stem": os.path.splitext(item["name"])[0],
                        "feedback_key_prefix": f"batch_{re.sub(r'[^a-zA-Z0-9_]+', '_', item['name'])}",
                    }
                )
            cached_batch_results.append(cached_item)
        st.session_state["analysis_results"] = {
            "mode": "batch", "items": cached_batch_results}

    elif not multiple_upload_mode:
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
        stage_placeholder.markdown(_build_stage_markdown(
            "Starting analysis..."), unsafe_allow_html=True)

        stage_state = {"index": -1}
        stage_lookup = {name: idx for idx, name in enumerate(LIVE_STAGES)}

        # Advance the displayed stage only forward to avoid flicker and regressions.
        def update_stage(stage_name: str):
            stage_idx = stage_lookup.get(stage_name)
            if stage_idx is None or stage_idx <= stage_state["index"]:
                return
            stage_state["index"] = stage_idx
            stage_placeholder.markdown(_build_stage_markdown(
                stage_name), unsafe_allow_html=True)

        update_stage("Uploading document...")
        update_stage("Extracting text...")

        contract_pages = _load_any_contract(uploaded_file)
        if not contract_pages:
            stage_placeholder.empty()
            st.stop()

        try:
            result = analyze_contract(
                contract_pages,
                fast_mode=fast_mode,
                summary_length=summary_length.replace(" (Standard)", ""),
                risk_sensitivity=risk_sensitivity,
                contract_type=contract_type,
                output_format=output_format,
                language=language,
                progress_callback=update_stage,
                return_agent_outputs=True,
            )
        except RuntimeError as err:
            stage_placeholder.empty()
            st.error(f"Analysis failed: {str(err)}")
            st.warning(
                "This is usually caused by Groq API rate limits. "
                "Wait 1-2 minutes and click Analyze again. "
                "If the problem persists, check your API key at https://console.groq.com/keys"
            )
            st.stop()

        stage_placeholder.markdown(
            '<div class="loader"><strong>Completed</strong></div>',
            unsafe_allow_html=True,
        )

        result_text = result["final_output"] if isinstance(
            result, dict) else result
        agent_outputs = result.get(
            "agent_outputs", {}) if isinstance(result, dict) else {}
        source_contract_text = parse_contract_text(contract_pages)
        st.session_state["analysis_results"] = {
            "result_text": result_text,
            "mode": "single",
            "complete_report": _build_complete_report_text(result_text, title="AI Analysis"),
            "agent_outputs": agent_outputs,
            "report_payload": None,
            "pages": contract_pages,
            "contract_type": contract_type,
            "source_contract_text": source_contract_text,
            "report_options": report_options,
            "file_stem": "contract_analysis",
            "feedback_key_prefix": "single_report",
        }
    else:
        if not uploaded_file_a or not uploaded_file_b:
            st.warning("Upload both contracts to run multi-file analysis.")
            st.stop()

        with st.spinner("Analyzing both contracts..."):
            pages_a = _load_any_contract(uploaded_file_a)
            pages_b = _load_any_contract(uploaded_file_b)
            if not pages_a or not pages_b:
                st.stop()
            compare_kwargs = {
                "fast_mode": fast_mode,
                "summary_length": summary_length.replace(" (Standard)", ""),
                "risk_sensitivity": risk_sensitivity,
                "contract_type": contract_type,
                "output_format": output_format,
                "language": language,
                "return_agent_outputs": True,
            }
            try:
                result_a = analyze_contract(pages_a, **compare_kwargs)
                time.sleep(5)
                result_b = analyze_contract(pages_b, **compare_kwargs)
            except RuntimeError as err:
                st.error(f"Analysis failed: {str(err)}")
                st.warning(
                    "This is usually caused by Groq API rate limits. "
                    "Wait 1-2 minutes and click Analyze again. "
                    "If the problem persists, check your API key at https://console.groq.com/keys"
                )
                st.stop()

        result_text_a = result_a["final_output"] if isinstance(
            result_a, dict) else result_a
        agent_outputs_a = result_a.get(
            "agent_outputs", {}) if isinstance(result_a, dict) else {}
        complete_report_a = _build_complete_report_text(
            result_text_a, title=f"{uploaded_file_a.name} Analysis")

        result_text_b = result_b["final_output"] if isinstance(
            result_b, dict) else result_b
        agent_outputs_b = result_b.get(
            "agent_outputs", {}) if isinstance(result_b, dict) else {}
        complete_report_b = _build_complete_report_text(
            result_text_b, title=f"{uploaded_file_b.name} Analysis")
        source_contract_text_a = parse_contract_text(pages_a)
        source_contract_text_b = parse_contract_text(pages_b)

        st.session_state["analysis_results"] = {
            "mode": "compare",
            "complete_report_a": complete_report_a,
            "complete_report_b": complete_report_b,
            "agent_outputs_a": agent_outputs_a,
            "agent_outputs_b": agent_outputs_b,
            "report_payload_a": None,
            "report_payload_b": None,
            "highlights_a": _key_highlights(complete_report_a, raw_text=result_text_a),
            "highlights_b": _key_highlights(complete_report_b, raw_text=result_text_b),
            "fast_mode": fast_mode,
            "contract_type": contract_type,
            "file_name_a": uploaded_file_a.name,
            "file_name_b": uploaded_file_b.name,
            "file_stem_a": os.path.splitext(uploaded_file_a.name)[0],
            "file_stem_b": os.path.splitext(uploaded_file_b.name)[0],
            "feedback_key_prefix_a": f"compare_{re.sub(r'[^a-zA-Z0-9_]+', '_', uploaded_file_a.name)}",
            "feedback_key_prefix_b": f"compare_{re.sub(r'[^a-zA-Z0-9_]+', '_', uploaded_file_b.name)}",
            "result_text_a": result_text_a,
            "result_text_b": result_text_b,
            "pages_a": pages_a,
            "pages_b": pages_b,
            "source_contract_text_a": source_contract_text_a,
            "source_contract_text_b": source_contract_text_b,
        }

saved_analysis = st.session_state.get("analysis_results")
if saved_analysis:
    if saved_analysis.get("mode") == "batch":
        _render_batch_results(saved_analysis.get("items", []))
    elif saved_analysis.get("mode") == "single":
        _render_single_results(saved_analysis)
    elif saved_analysis.get("mode") == "compare":
        _render_compare_results(saved_analysis)
