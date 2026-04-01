import json
import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import streamlit as st
from graph import contract_graph
from pypdf import PdfReader
from docx import Document


# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Contract AI",
    page_icon="AI",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------- DATABASE ----------------
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT)")
c.execute(
    """
    CREATE TABLE IF NOT EXISTS report_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        contract_name TEXT NOT NULL,
        tone TEXT,
        focus TEXT,
        created_at TEXT NOT NULL,
        report_json TEXT NOT NULL
    )
    """
)
conn.commit()


# ---------------- AUTH ----------------
def signup(email, password):
    try:
        c.execute("INSERT INTO users VALUES (?, ?)", (email, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def login(email, password):
    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    return c.fetchone() is not None


# ---------------- FILE EXTRACTION ----------------
def extract_text(file):
    file_name = getattr(file, "name", "").lower()

    if file_name.endswith(".pdf"):
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text[:1500]

    if file_name.endswith(".docx"):
        document = Document(BytesIO(file.getvalue()))
        text = "\n".join(
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text and paragraph.text.strip()
        )
        return text[:1500]

    if file_name.endswith(".txt"):
        content = file.getvalue()
        text = content.decode("utf-8", errors="ignore")
        return text[:1500]

    raise ValueError(f"Unsupported file type: {file_name}")


# ---------------- ANALYSIS ----------------
def analyze_contract(file, tone, focus):
    text = extract_text(file)
    return contract_graph.invoke(
        {
            "contract": text,
            "tone": tone,
            "focus": focus,
        }
    )


# ---------------- QUERY ----------------
def ask_query(question, report):
    prompt = f"""
Context:
{report[:1000]}

Question:
{question}
Answer concisely:
"""
    res = contract_graph.invoke({"contract": prompt})
    return res["final_report"]


def _pdf_escape(text):
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def build_pdf_bytes(title, sections):
    lines = [title, ""]
    for heading, content in sections:
        lines.append(heading)
        if isinstance(content, list):
            for item in content:
                lines.append(f"- {item}")
        else:
            for line in str(content).splitlines():
                lines.append(line)
        lines.append("")

    normalized = []
    for line in lines:
        cleaned = line.encode("latin-1", "replace").decode("latin-1")
        if len(cleaned) <= 95:
            normalized.append(cleaned)
            continue
        words = cleaned.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > 95 and current:
                normalized.append(current)
                current = word
            else:
                current = candidate
        if current:
            normalized.append(current)

    pages = []
    page_lines = []
    for line in normalized:
        page_lines.append(line)
        if len(page_lines) >= 42:
            pages.append(page_lines)
            page_lines = []
    if page_lines:
        pages.append(page_lines)
    if not pages:
        pages = [["Report unavailable"]]

    objects = []

    def add_object(content):
        objects.append(content)
        return len(objects)

    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    content_ids = []
    pages_id_placeholder = None

    for page in pages:
        commands = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
        first_line = True
        for line in page:
            text = _pdf_escape(line)
            if first_line:
                commands.append(f"({text}) Tj")
                first_line = False
            else:
                commands.append(f"T* ({text}) Tj")
        commands.append("ET")
        stream = "\n".join(commands)
        content_id = add_object(
            f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream"
        )
        content_ids.append(content_id)
        page_id = add_object(
            f"<< /Type /Page /Parent PAGES_ID 0 R /MediaBox [0 0 612 842] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_id_placeholder = add_object(f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>")

    for page_id in page_ids:
        objects[page_id - 1] = objects[page_id - 1].replace("PAGES_ID", str(pages_id_placeholder))

    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id_placeholder} 0 R >>")

    pdf_parts = ["%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part.encode("latin-1")) for part in pdf_parts))
        pdf_parts.append(f"{index} 0 obj\n{obj}\nendobj\n")

    xref_offset = sum(len(part.encode("latin-1")) for part in pdf_parts)
    pdf_parts.append(f"xref\n0 {len(objects) + 1}\n")
    pdf_parts.append("0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf_parts.append(f"{offset:010d} 00000 n \n")
    pdf_parts.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
    )
    return "".join(pdf_parts).encode("latin-1")


def build_report_pdf(contract_name, tone, focus, report_data, created_at):
    sections = [
        ("Generated For", st.session_state.email or "Unknown user"),
        ("Contract", contract_name),
        ("Created At", created_at),
        ("Report Tone", tone),
        ("Analysis Focus", focus),
        ("Final Report", report_data.get("final_report", "No final report available.")),
    ]

    agent_map = [
        ("Compliance Analysis", report_data.get("compliance_result", {})),
        ("Legal Analysis", report_data.get("legal_result", {})),
        ("Finance Analysis", report_data.get("finance_result", {})),
        ("Operations Analysis", report_data.get("operations_result", {})),
    ]

    for title, result in agent_map:
        if isinstance(result, dict):
            sections.append((f"{title} Summary", result.get("summary", "No summary available.")))
            sections.append((f"{title} Risks", result.get("risks", [])))
            sections.append((f"{title} Recommendations", result.get("recommendations", [])))
        else:
            sections.append((title, result))

    return build_pdf_bytes("Contract AI Report", sections)


def save_report_history(email, contract_name, tone, focus, report_data):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """
        INSERT INTO report_history (email, contract_name, tone, focus, created_at, report_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (email, contract_name, tone, focus, created_at, json.dumps(report_data)),
    )
    conn.commit()
    return created_at


def load_report_history(email):
    c.execute(
        """
        SELECT id, contract_name, tone, focus, created_at, report_json
        FROM report_history
        WHERE email=?
        ORDER BY id DESC
        """,
        (email,),
    )
    rows = c.fetchall()
    history = []
    for row in rows:
        history.append(
            {
                "id": row[0],
                "contract_name": row[1],
                "tone": row[2],
                "focus": row[3],
                "created_at": row[4],
                "report_data": json.loads(row[5]),
            }
        )
    return history


# ---------------- HELPERS ----------------
def inject_global_styles():
    st.markdown(
        """
        <style>
        :root {
            --bg: #f4f7fb;
            --panel: rgba(255, 255, 255, 0.9);
            --panel-strong: #ffffff;
            --text: #14213d;
            --muted: #5c677d;
            --line: rgba(20, 33, 61, 0.1);
            --primary: #0f766e;
            --primary-soft: #dff6f3;
            --accent: #f59e0b;
            --accent-soft: #fff3d6;
            --danger: #b91c1c;
            --shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
            --radius: 20px;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(15, 118, 110, 0.14), transparent 28%),
                radial-gradient(circle at top right, rgba(245, 158, 11, 0.14), transparent 20%),
                linear-gradient(180deg, #f8fbff 0%, var(--bg) 100%);
            color: var(--text);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #162033 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        [data-testid="stSidebar"] * {
            color: #f8fafc !important;
        }

        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .stButton button {
            color: #f8fafc !important;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2.5rem;
        }

        .hero-shell {
            background: linear-gradient(135deg, #10243f 0%, #123f5d 55%, #0f766e 100%);
            border-radius: 28px;
            padding: 2rem;
            color: white;
            box-shadow: var(--shadow);
            overflow: hidden;
            position: relative;
            margin-bottom: 1.4rem;
        }

        .hero-shell::after {
            content: "";
            position: absolute;
            inset: auto -40px -50px auto;
            width: 180px;
            height: 180px;
            background: rgba(255, 255, 255, 0.09);
            border-radius: 50%;
        }

        .eyebrow {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.12);
            font-size: 0.82rem;
            letter-spacing: 0.04em;
            margin-bottom: 0.9rem;
        }

        .hero-title {
            font-size: 2.1rem;
            font-weight: 700;
            margin: 0;
        }

        .hero-copy {
            margin-top: 0.7rem;
            max-width: 760px;
            color: rgba(255, 255, 255, 0.86);
            line-height: 1.55;
        }

        .glass-card {
            background: var(--panel);
            border: 1px solid rgba(255, 255, 255, 0.65);
            border-radius: var(--radius);
            padding: 1.2rem 1.25rem;
            box-shadow: var(--shadow);
            backdrop-filter: blur(12px);
            margin-bottom: 1rem;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 0.2rem;
        }

        .section-copy {
            color: var(--muted);
            margin-bottom: 0;
        }

        .metric-card {
            background: var(--panel-strong);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.05);
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.86rem;
            margin-bottom: 0.25rem;
        }

        .metric-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text);
        }

        .metric-hint {
            color: var(--muted);
            font-size: 0.82rem;
            margin-top: 0.25rem;
        }

        .workflow-card {
            padding: 1rem 1rem 0.9rem 1rem;
            border-radius: 18px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.82);
            min-height: 135px;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.04);
        }

        .workflow-card.active {
            background: linear-gradient(135deg, #e6fffb 0%, #dff6f3 100%);
            border-color: rgba(15, 118, 110, 0.28);
        }

        .workflow-card.done {
            background: linear-gradient(135deg, #f8fafc 0%, #eefdfb 100%);
        }

        .workflow-step {
            color: var(--primary);
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.45rem;
        }

        .workflow-title {
            font-weight: 700;
            color: var(--text);
            margin-bottom: 0.35rem;
        }

        .workflow-copy {
            color: var(--muted);
            font-size: 0.86rem;
            line-height: 1.45;
            margin: 0;
        }

        .contract-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
            margin-bottom: 0.9rem;
        }

        .contract-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text);
            margin: 0;
        }

        .pill {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: var(--primary-soft);
            color: var(--primary);
            font-weight: 600;
            font-size: 0.78rem;
        }

        .status-banner {
            background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%);
            border: 1px solid rgba(245, 158, 11, 0.25);
            color: #92400e;
            border-radius: 16px;
            padding: 0.9rem 1rem;
            margin-bottom: 1rem;
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.85);
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 14px;
            border: 0;
            padding: 0.7rem 1rem;
            font-weight: 600;
            box-shadow: 0 10px 20px rgba(15, 118, 110, 0.14);
        }

        .stButton > button[kind="primary"],
        .stDownloadButton > button {
            background: linear-gradient(135deg, #0f766e 0%, #115e59 100%);
            color: white;
        }

        .stTextInput > div > div,
        .stTextArea textarea,
        .stSelectbox > div > div,
        .stFileUploader {
            border-radius: 14px !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            background: rgba(255, 255, 255, 0.12) !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] span,
        [data-testid="stSidebar"] [data-baseweb="select"] div {
            color: #f8fafc !important;
        }

        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] p {
            color: rgba(248, 250, 252, 0.88) !important;
        }

        [data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
            color: white !important;
            border: 0 !important;
        }

        .sidebar-card {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            margin-bottom: 1rem;
        }

        .review-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(20, 33, 61, 0.15), transparent);
            margin: 1.2rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label, value, hint):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-hint">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_overview(current_step):
    steps = {
        1: ("History", "Open previously generated reports before starting a new review."),
        2: ("Upload contracts", "Add one or more PDF agreements for analysis."),
        3: ("Analyze content", "Run the multi-agent workflow with your selected focus."),
        4: ("Review results", "Inspect reports, compare agent outputs, and ask follow-up questions."),
    }

    cols = st.columns(4)
    for index, (step, (title, copy)) in enumerate(steps.items()):
        css_class = "workflow-card"
        if step < current_step:
            css_class += " done"
        elif step == current_step:
            css_class += " active"

        with cols[index]:
            st.markdown(
                f"""
                <div class="{css_class}">
                    <div class="workflow-step">Step {step}</div>
                    <div class="workflow-title">{title}</div>
                    <p class="workflow-copy">{copy}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def initialize_session():
    defaults = {
        "logged_in": False,
        "step": 1,
        "email": "",
        "files": [],
        "results": [],
        "result_meta": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_analysis_state():
    st.session_state.results = []
    st.session_state.result_meta = []


def render_agent_section(title, result, expanded=False):
    with st.expander(title, expanded=expanded):
        if isinstance(result, dict):
            summary = result.get("summary") or result.get("analysis") or result.get("overview")
            risks = result.get("risks")
            recommendations = result.get("recommendations")

            if summary:
                st.markdown("**Summary**")
                st.write(summary)

            if risks:
                st.markdown("**Risks**")
                if isinstance(risks, list):
                    for item in risks:
                        st.write(f"- {item}")
                else:
                    st.write(risks)

            if recommendations:
                st.markdown("**Recommendations**")
                if isinstance(recommendations, list):
                    for item in recommendations:
                        st.write(f"- {item}")
                else:
                    st.write(recommendations)

            extra_keys = [
                key for key in result.keys()
                if key not in {"summary", "analysis", "overview", "risks", "recommendations"}
            ]
            for key in extra_keys:
                st.markdown(f"**{key.replace('_', ' ').title()}**")
                st.write(result[key])
        else:
            st.write(result if result else "No output available.")


def render_history_list(email):
    history_items = load_report_history(email)
    if not history_items:
        st.info("No saved report history yet. Run an analysis to create your first report.")
        return

    for item in history_items:
        report_data = item["report_data"]
        pdf_bytes = build_report_pdf(
            item["contract_name"],
            item["tone"],
            item["focus"],
            report_data,
            item["created_at"],
        )
        with st.expander(
            f'{item["contract_name"]} • {item["created_at"]}',
            expanded=False,
        ):
            st.write(f'**Tone:** {item["tone"]}')
            st.write(f'**Focus:** {item["focus"]}')
            st.write(report_data.get("final_report", "No final report available."))
            st.download_button(
                "Download PDF report",
                pdf_bytes,
                file_name=f'report_{item["id"]}.pdf',
                mime="application/pdf",
                key=f'history_pdf_{item["id"]}',
            )


# ---------------- SESSION ----------------
initialize_session()
inject_global_styles()


# ---------------- LOGIN UI ----------------
def show_auth():
    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown(
            """
            <div class="hero-shell" style="min-height: 480px;">
                <div class="eyebrow">AI-powered contract workspace</div>
                <h1 class="hero-title">Review contracts with a cleaner workflow.</h1>
                <p class="hero-copy">
                    Upload agreements, generate structured multi-agent analysis, and ask focused
                    follow-up questions from one streamlined dashboard.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
            <div class="glass-card">
                <div class="section-title">Secure access</div>
                <p class="section-copy">Sign in to manage uploads, launch analysis, and review reports.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        option = st.radio("Choose access mode", ["Login", "Signup"], horizontal=True)
        email = st.text_input("Email address", placeholder="name@company.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        if option == "Signup":
            if st.button("Create account", use_container_width=True, type="primary"):
                if not email or not password:
                    st.warning("Please enter both email and password.")
                elif signup(email, password):
                    st.success("Account created successfully. You can log in now.")
                else:
                    st.error("This email is already registered.")
        else:
            if st.button("Log in", use_container_width=True, type="primary"):
                if not email or not password:
                    st.warning("Please enter both email and password.")
                elif login(email, password):
                    st.session_state.logged_in = True
                    st.session_state.email = email
                    st.rerun()
                else:
                    st.error("Invalid email or password.")


# ---------------- MAIN UI ----------------
def show_app():
    with st.sidebar:
        st.markdown("## Control Center")
        st.caption("Tune the analysis before running the workflow.")
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        tone = st.selectbox("Response tone", ["Formal", "Simple"])
        focus = st.selectbox("Analysis focus", ["All", "Legal", "Finance"])
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(
            f"""
            <div class="sidebar-card">
                <strong>Signed in as</strong><br>
                {st.session_state.email}<br><br>
                <strong>Current step</strong><br>
                Step {st.session_state.step} of 4
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.step = 1
            st.session_state.email = ""
            st.session_state.files = []
            st.session_state.results = []
            st.session_state.result_meta = []
            st.rerun()

    file_count = len(st.session_state.files)
    result_count = len(st.session_state.results)

    st.markdown(
        """
        <div class="hero-shell">
            <div class="eyebrow">Contract Intelligence Dashboard</div>
            <h2 class="hero-title">Multi-agent review with a more professional interface</h2>
            <p class="hero-copy">
                Move from upload to analysis to final review with a guided workflow, clearer status
                indicators, and easier access to contract reports.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        render_metric_card("Uploaded contracts", file_count, "PDF files currently in this session")
    with metric_col2:
        render_metric_card("Completed analyses", result_count, "Reports ready for review and download")
    with metric_col3:
        render_metric_card("Active focus", focus, "Current analysis scope from the sidebar")

    st.markdown(
        """
        <div class="glass-card">
            <div class="section-title">Workflow</div>
            <p class="section-copy">Use the guided steps below to move through the review pipeline.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_step_overview(st.session_state.step)

    nav1, nav2, nav3, nav4 = st.columns(4)
    with nav1:
        if st.button("Go to History", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with nav2:
        if st.button("Go to Upload", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with nav3:
        if st.button("Go to Analyze", use_container_width=True):
            if st.session_state.files:
                st.session_state.step = 3
                st.rerun()
            else:
                st.warning("Upload at least one contract first.")
    with nav4:
        if st.button("Go to Review", use_container_width=True):
            if st.session_state.results:
                st.session_state.step = 4
                st.rerun()
            else:
                st.warning("Run the analysis before opening review.")

    if st.session_state.step == 1:
        st.markdown(
            """
            <div class="glass-card">
                <div class="section-title">Report history</div>
                <p class="section-copy">Reopen and download previous contract reports before starting a new run.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_history_list(st.session_state.email)

        if st.button("Start a new contract review", type="primary"):
            st.session_state.step = 2
            st.rerun()

    elif st.session_state.step == 2:
        st.markdown(
            """
            <div class="glass-card">
                <div class="section-title">Upload contracts</div>
                <p class="section-copy">Add one or more PDF, DOCX, or TXT files to begin the contract review workflow.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        files = st.file_uploader(
            "Select contract files",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            help="You can upload multiple PDF, DOCX, or TXT agreements in one batch.",
        )

        if files:
            st.session_state.files = files
            clear_analysis_state()

            file_names = ", ".join(file.name for file in files[:3])
            if len(files) > 3:
                file_names += f" and {len(files) - 3} more"

            st.success(f"{len(files)} file(s) uploaded successfully.")
            st.info(f"Loaded files: {file_names}")

            if st.button("Continue to analysis", type="primary"):
                st.session_state.step = 3
                st.rerun()
        else:
            st.markdown(
                """
                    <div class="status-banner">
                        No contracts uploaded yet. Add PDF, DOCX, or TXT files here to unlock analysis and review.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    elif st.session_state.step == 3:
        st.markdown(
            """
            <div class="glass-card">
                <div class="section-title">Run analysis</div>
                <p class="section-copy">Apply your current tone and focus settings to each uploaded contract.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.files:
            summary_left, summary_right = st.columns([1.3, 1], gap="large")
            with summary_left:
                st.write(f"**Ready for processing:** {len(st.session_state.files)} contract(s)")
                st.write(f"**Tone:** {tone}")
                st.write(f"**Focus:** {focus}")
            with summary_right:
                st.markdown(
                    """
                    <div class="status-banner">
                        Analysis uses the uploaded document text plus your selected sidebar options.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if st.button("Start analysis", use_container_width=True, type="primary"):
                with st.spinner("Running contract analysis..."):
                    with ThreadPoolExecutor() as executor:
                        results = list(
                            executor.map(
                                lambda uploaded_file: analyze_contract(uploaded_file, tone, focus),
                                st.session_state.files,
                            )
                        )

                st.session_state.results = results
                st.session_state.result_meta = []
                for index, report_data in enumerate(results):
                    contract_name = (
                        st.session_state.files[index].name
                        if index < len(st.session_state.files)
                        else f"Contract {index + 1}"
                    )
                    created_at = save_report_history(
                        st.session_state.email,
                        contract_name,
                        tone,
                        focus,
                        report_data,
                    )
                    st.session_state.result_meta.append(
                        {
                            "contract_name": contract_name,
                            "tone": tone,
                            "focus": focus,
                            "created_at": created_at,
                        }
                    )
                st.success("Analysis complete. Reports are ready to review.")

            if st.session_state.results:
                if st.button("Open review workspace", use_container_width=True):
                    st.session_state.step = 4
                    st.rerun()
        else:
            st.warning("Upload a contract before starting analysis.")

    elif st.session_state.step == 4:
        st.markdown(
            """
            <div class="glass-card">
                <div class="section-title">Review workspace</div>
                <p class="section-copy">Inspect each report, expand agent outputs, download PDF reports, and ask questions.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state.results:
            st.warning("No completed analysis found yet. Please run analysis first.")
            return

        for i, data in enumerate(st.session_state.results):
            meta = (
                st.session_state.result_meta[i]
                if i < len(st.session_state.result_meta)
                else {
                    "contract_name": (
                        st.session_state.files[i].name
                        if i < len(st.session_state.files)
                        else f"Contract {i + 1}"
                    ),
                    "tone": tone,
                    "focus": focus,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            file_name = meta["contract_name"]
            pdf_bytes = build_report_pdf(
                file_name,
                meta["tone"],
                meta["focus"],
                data,
                meta["created_at"],
            )

            with st.container():
                st.markdown(
                    f"""
                    <div class="glass-card">
                        <div class="contract-header">
                            <div>
                                <p class="contract-title">{file_name}</p>
                                <span class="pill">Saved {meta["created_at"]}</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                tab1, tab2, tab3 = st.tabs(["Final Report", "Agent Breakdown", "Ask Questions"])

                with tab1:
                    st.write(data.get("final_report", "No final report available."))
                    st.download_button(
                        "Download PDF report",
                        pdf_bytes,
                        file_name=f"contract_{i + 1}.pdf",
                        mime="application/pdf",
                        key=f"download_pdf_{i}",
                    )

                with tab2:
                    render_agent_section(
                        "Compliance analysis",
                        data.get("compliance_result", "No compliance output available."),
                        expanded=True,
                    )
                    render_agent_section(
                        "Legal analysis",
                        data.get("legal_result", "No legal output available."),
                    )
                    render_agent_section(
                        "Finance analysis",
                        data.get("finance_result", "No finance output available."),
                    )
                    render_agent_section(
                        "Operations analysis",
                        data.get("operations_result", "No operations output available."),
                    )

                with tab3:
                    st.caption("Ask a focused question about this contract summary.")
                    query = st.text_input(
                        f"Question for {file_name}",
                        key=f"q{i}",
                        placeholder="Example: What are the main payment risks in this contract?",
                    )
                    if query:
                        with st.spinner("Generating answer..."):
                            answer = ask_query(query, data.get("final_report", ""))
                        st.success(answer)

                st.markdown('<div class="review-divider"></div>', unsafe_allow_html=True)


# ---------------- FLOW ----------------
if not st.session_state.logged_in:
    show_auth()
else:
    show_app()
