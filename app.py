from flask import Flask, render_template, request, send_file, jsonify
import os
from markupsafe import Markup
import re
import uuid
from docx_generator import generate_docx
from graph_builder import build_graph
from document_loader import load_document
from pdf_generator import generate_pdf

# ✅ RAG
from vector_store import store_data

# ============================================
# FLASK APP SETUP
# ============================================

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

LAST_GENERATED_FILE = None
LAST_RESULTS = None   # ✅ STORES FINAL RESULT FOR DOWNLOAD


# ============================================
# SHORT SUMMARY GENERATOR
# ============================================

def summarize_for_web(full_text):
    text = str(full_text).replace("\n\n", "\n").strip()
    lines = text.split("\n")
    summary = []

    KEY_SECTIONS = [
        "Risk", "Payment", "Penalty", "Cost",
        "Financial", "Exposure", "Concern",
        "Issue", "Refund", "Liability", "Recommendation"
    ]

    for line in lines:
        clean = line.strip()
        if any(key.lower() in clean.lower() for key in KEY_SECTIONS):
            summary.append(clean)

        if clean[:1].isdigit() and clean[1:2] == ".":
            summary.append(clean)

    if len(summary) == 0:
        return text[:600] + "..."

    return "\n".join(summary[:10])


# ============================================
# CLAUSE HIGHLIGHTING
# ============================================

def extract_risky_clauses(analysis_text):
    pattern = r'Clause:\s*"(.*?)"'
    return re.findall(pattern, analysis_text)


def highlight_clauses(contract_text, risky_clauses):
    for clause in risky_clauses:
        if clause in contract_text:
            contract_text = contract_text.replace(
                clause,
                f"<mark style='background-color:#ff4d4d; color:white; padding:2px; border-radius:4px'>{clause}</mark>"
            )
    return contract_text


# ============================================
# HOME PAGE
# ============================================

@app.route('/')
def home():
    return render_template("index.html")


# ============================================
# ANALYZE ROUTE
# ============================================

@app.route('/analyze', methods=['POST'])
def analyze():

    global LAST_GENERATED_FILE, LAST_RESULTS

    file = request.files.get("file")

    # ==========================
    # FILE OR TEXT INPUT
    # ==========================
    if file and file.filename != "":
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(filepath)
        contract_text = load_document(filepath)
        uploaded_filename = file.filename
    else:
        contract_text = request.form.get("clause")
        uploaded_filename = "Contract.txt"

    if not contract_text:
        return "No contract text provided", 400

    # ==========================
    # RAG STORE
    # ==========================
    store_data(str(uuid.uuid4()), contract_text)

    # ==========================
    # RUN GRAPH
    # ==========================
    graph = build_graph()
    state = {"contract_text": contract_text}
    result_state = graph.invoke(state)

    full_results = result_state.get("final_report", {})

    # ADD FIXED SUGGESTIONS
    full_results["Suggestions"] = """
1. Define clear refund policy
2. Add proper IP ownership clause
3. Improve data protection compliance (GDPR/IT Act)
4. Add milestone-based delivery terms
"""
    full_results["Contract Name"] = uploaded_filename

    print("FULL REPORT:", full_results)

    # ==========================
    # CLAUSE HIGHLIGHTING
    # ==========================
    all_risky_clauses = []

    for key in ["Legal Analysis", "Finance Analysis", "Compliance Analysis"]:
        if key in full_results:
            extracted = extract_risky_clauses(full_results[key])
            all_risky_clauses.extend(extracted)

    highlighted_contract = highlight_clauses(contract_text, all_risky_clauses)

    # ==========================
    # SHORT RESULTS
    # ==========================
    short_results = full_results.copy()

    if "Legal Analysis" in full_results:
        short_results["Legal Analysis"] = summarize_for_web(full_results["Legal Analysis"])

    if "Finance Analysis" in full_results:
        short_results["Finance Analysis"] = summarize_for_web(full_results["Finance Analysis"])

    if "Compliance Analysis" in full_results:
        short_results["Compliance Analysis"] = summarize_for_web(full_results["Compliance Analysis"])

    # ==========================
    # STORE RESULTS FOR DOWNLOAD
    # ==========================
    filename = f"{uploaded_filename}_Report.pdf"
    LAST_GENERATED_FILE = filename
    LAST_RESULTS = full_results

    # ==========================
    # RISK SCORE
    # ==========================
    risk_score_text = full_results.get("Risk Score", "0/100")
    risk_score = risk_score_text.split("/")[0]
    confidence = str(full_results.get("Confidence", "N/A")) + "%"

    # ==========================
    # FORMAT HTML
    # ==========================
    formatted_results = {}
    for key, value in short_results.items():
        formatted_results[key] = Markup(str(value).replace("\n", "<br>"))

    # ==========================
    # RENDER PAGE
    # ==========================
    return render_template(
        "result.html",
        results=formatted_results,
        score=risk_score,
        confidence=confidence,
        pdf_ready=True,
        highlighted_contract=Markup(highlighted_contract),
        contract_name=uploaded_filename
    )


# ============================================
# CHATBOT API
# ============================================

from llm_setup import groq_llm

@app.route("/chat", methods=["POST"])
def chat():

    global LAST_RESULTS

    user_message = request.json.get("message")

    if not user_message:
        return jsonify({"reply": "No question received"}), 400

    if not LAST_RESULTS:
        return jsonify({"reply": "Please analyze a contract first."})

    summary = LAST_RESULTS.get("Summary", "")
    legal = LAST_RESULTS.get("Legal Analysis", "")
    finance = LAST_RESULTS.get("Finance Analysis", "")
    compliance = LAST_RESULTS.get("Compliance Analysis", "")

    context = f"""
SUMMARY:
{summary}

LEGAL RISKS:
{legal}

FINANCIAL RISKS:
{finance}

COMPLIANCE RISKS:
{compliance}
"""

    prompt = f"""
You are ClauseAI, a professional AI Contract Assistant.

Rules:
- Answer ONLY using the analysis
- If question is unrelated, respond:
  "I only answer contract-related questions."
- Keep answers short and professional

CONTEXT:
{context[:3000]}

USER QUESTION:
{user_message}
"""

    try:
        response = groq_llm.invoke(prompt)
        reply = response.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": "AI is temporarily unavailable."})


# ============================================
# DOWNLOAD ROUTE (NOW USES TONE)
# ============================================

from datetime import datetime

@app.route("/download")
def download_file():
    global LAST_RESULTS
    
    if not LAST_RESULTS:
        return "No analysis found", 400

    # ----------------------------
    # GET TONE + FORMAT
    # ----------------------------
    tone = request.args.get("tone", "Neutral")
    file_format = request.args.get("format", "pdf")  # pdf or docx

    # ----------------------------
    # SAFE FILENAME
    # ----------------------------
    username = "Vaishnavi_A_Kanade"
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")

    project_name = LAST_RESULTS.get("Contract Name", "Contract")
    safe_name = project_name.replace(" ", "_").replace("/", "_")

    # ----------------------------
    # FINAL FILE NAME
    # ----------------------------
    final_name = f"{safe_name}_{username}_{now}_{tone}.{file_format}"

    save_path = f"generated_reports/{final_name}"

    os.makedirs("generated_reports", exist_ok=True)

    # Remove existing file
    if os.path.exists(save_path):
        try:
            os.remove(save_path)
        except:
            return "Close the file and try again.", 400

    # ----------------------------
    # GENERATE FILE
    # ----------------------------
    try:
        if file_format == "docx":
            generate_docx(LAST_RESULTS, save_path, tone=tone)
        else:
            generate_pdf(LAST_RESULTS, save_path, tone=tone)
    except Exception as e:
        return f"Error generating file: {e}", 500

    # ----------------------------
    # RETURN FILE
    # ----------------------------
    return send_file(save_path, as_attachment=True)

# ============================================
# RUN APP
# ============================================

if __name__ == '__main__':
    app.run(debug=True)
