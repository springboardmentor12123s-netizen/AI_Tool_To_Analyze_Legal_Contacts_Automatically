import streamlit as st
from graph import contract_graph
from pypdf import PdfReader
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import matplotlib.pyplot as plt
import json
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# -------- DATABASE --------
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    password TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    report TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    question TEXT,
    answer TEXT
)
""")

conn.commit()

# -------- AUTH --------
def signup(email, password):
    try:
        c.execute("INSERT INTO users VALUES (?, ?)", (email.strip(), password.strip()))
        conn.commit()
        return True
    except:
        return False

def login(email, password):
    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email.strip(), password.strip()))
    return c.fetchone() is not None

# -------- HISTORY --------
def save_history(email, report, name):
    c.execute(
        "INSERT INTO history (email, report) VALUES (?, ?)",
        (email, json.dumps({"name": name, "data": report}))
    )
    conn.commit()

def get_history(email):
    c.execute("SELECT id, report FROM history WHERE email=?", (email,))
    return c.fetchall()

# -------- QUERY STORAGE --------
def save_query(email, question, answer):
    c.execute("INSERT INTO queries (email, question, answer) VALUES (?, ?, ?)",
              (email, question, answer))
    conn.commit()

# -------- PDF GENERATION --------
def generate_pdf(text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    story = []

    for line in text.split("\n"):
        story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 10))

    doc.build(story)
    buffer.seek(0)
    return buffer

# -------- TEXT EXTRACT --------
def extract_text(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# -------- ANALYSIS --------
def analyze_contract(file, tone, focus):
    text = extract_text(file)[:2000]

    result = contract_graph.invoke({
        "contract": text,
        "tone": tone,
        "focus": focus
    })

    return {
        "final_report": result["final_report"],
        "compliance": result["compliance_result"],
        "legal": result["legal_result"],
        "finance": result["finance_result"],
        "operations": result["operations_result"]
    }

# -------- QUERY --------
def ask_query(question, report_text):
    prompt = f"""
Answer ONLY the question concisely.

Context:
{report_text}

Question:
{question}

Answer:
"""
    response = contract_graph.invoke({"contract": prompt})
    return response["final_report"]

# -------- TABLE --------
def combine_all_agents(data):
    rows = []

    all_text = (
        data["compliance"] + "\n\n" +
        data["legal"] + "\n\n" +
        data["finance"] + "\n\n" +
        data["operations"]
    )

    for block in all_text.split("\n\n"):
        clause = risk_type = risk_level = recommendation = ""

        for line in block.split("\n"):
            if "Clause:" in line:
                clause = line.replace("Clause:", "").strip()
            elif "Risk Type:" in line:
                risk_type = line.replace("Risk Type:", "").strip()
            elif "Risk Level:" in line:
                risk_level = line.replace("Risk Level:", "").strip()
            elif "Recommendation:" in line:
                recommendation = line.replace("Recommendation:", "").strip()

        if clause or risk_type:
            rows.append({
                "Clause": clause,
                "Risk Type": risk_type,
                "Risk Level": risk_level,
                "Recommendation": recommendation
            })

    return pd.DataFrame(rows)

# -------- CHART --------
def plot_risk_trend(df):
    if df.empty:
        st.warning("No data for chart")
        return

    mapping = {"Low": 1, "Medium": 2, "High": 3}
    df["Risk Score"] = df["Risk Level"].map(mapping)
    df = df.dropna()

    fig, ax = plt.subplots()
    ax.plot(df.index, df["Risk Score"], marker='o')

    ax.set_yticks([1, 2, 3])
    ax.set_yticklabels(["Low", "Medium", "High"])
    ax.set_title("Risk Trend Analysis")

    st.pyplot(fig)

# -------- SESSION --------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "remember_user" not in st.session_state:
    st.session_state.remember_user = False

if "email" not in st.session_state:
    st.session_state.email = ""

if "multi_results" not in st.session_state:
    st.session_state.multi_results = []

if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}

# -------- AUTH UI --------
def show_auth():
    st.title("🔐 Contract Analyzer Login")

    if st.session_state.remember_user and st.session_state.email:
        st.success(f"Continue as {st.session_state.email}")
        if st.button("👉 Continue"):
            st.session_state.logged_in = True
            st.rerun()

    option = st.radio("Select Option", ["Login", "Signup"])

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    remember = st.checkbox("Remember Me")

    if option == "Signup":
        if st.button("Create Account"):
            if signup(email, password):
                st.success("Account created! Please login.")
            else:
                st.error("User already exists")
    else:
        if st.button("Login"):
            if login(email, password):
                st.session_state.logged_in = True
                st.session_state.email = email
                if remember:
                    st.session_state.remember_user = True
                st.rerun()
            else:
                st.error("Invalid credentials")

# -------- MAIN APP --------
def show_app():

    st.title("📄 AI Contract Risk Analyzer")

    # Sidebar
    st.sidebar.header("⚙️ Settings")
    tone = st.sidebar.selectbox("Report Tone", ["Simple", "Formal"])
    focus = st.sidebar.selectbox("Focus Area", ["All", "Compliance", "Legal", "Finance"])
    st.sidebar.write(f"👤 {st.session_state.email}")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.remember_user = False
        st.rerun()

    # -------- HISTORY --------
    st.sidebar.subheader("📂 Reports")
    reports = get_history(st.session_state.email)

    for report_id, report_text in reports:
        try:
            data = json.loads(report_text)
            name = data["name"]
            report_data = data["data"]
        except:
            name = "Old Report"
            report_data = json.loads(report_text)

        if st.sidebar.button(f"📄 {name}", key=f"btn_{report_id}"):
            st.session_state.multi_results = [{"name": name, "data": report_data}]

    # -------- UPLOAD --------
    files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

    if files and st.button("🚀 Analyze Contracts"):

        with st.spinner("Analyzing..."):
            with ThreadPoolExecutor() as executor:
                results = list(executor.map(lambda f: analyze_contract(f, tone, focus), files))

                for file, item in zip(files, results):
                    save_history(st.session_state.email, item, file.name)

        st.session_state.multi_results = [
            {"name": f.name, "data": r} for f, r in zip(files, results)
        ]

        st.success("Analysis complete!")

    # -------- DISPLAY --------
    for contract in st.session_state.multi_results:

        name = contract["name"]
        data = contract["data"]

        st.markdown(f"## 📄 {name}")

        with st.expander("📊 Final Report"):
            st.write(data["final_report"])

            pdf = generate_pdf(data["final_report"])
            st.download_button(
                label="📥 Download Report",
                data=pdf,
                file_name=f"{name}_report.pdf",
                mime="application/pdf"
            )

        with st.expander("📋 Risk Summary Table"):
            df = combine_all_agents(data)
            st.dataframe(df)

        with st.expander("📈 Risk Trend Analysis"):
            df = combine_all_agents(data)
            plot_risk_trend(df)

        with st.expander("🧠 Agent Analysis"):
            st.text(data["compliance"])
            st.text(data["legal"])
            st.text(data["finance"])
            st.text(data["operations"])

        # -------- CHAT --------
        st.markdown("### 💬 Ask Questions")

        rid = name

        if rid not in st.session_state.chat_sessions:
            st.session_state.chat_sessions[rid] = []

        chat = st.session_state.chat_sessions[rid]

        for msg in chat:
            st.chat_message("user").write(msg["q"])
            st.chat_message("assistant").write(msg["a"])

        query = st.chat_input(f"Ask about {name}", key=f"chat_{name}")

        if query:
            answer = ask_query(query, data["final_report"])
            chat.append({"q": query, "a": answer})
            save_query(st.session_state.email, query, answer)
            st.rerun()

        st.markdown("---")

# -------- FLOW --------
if not st.session_state.logged_in:
    show_auth()
else:
    show_app()