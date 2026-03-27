from flask import Flask, render_template, request, jsonify
from graph_builder import build_graph
import markdown
from markupsafe import Markup
import os
from pdf_generator import generate_pdf
from document_loader import load_document

# ============================================
# FLASK APP SETUP
# ============================================
app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


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

    clause = None

    # File upload
    file = request.files.get("file")

    if file and file.filename != "":
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(filepath)
        clause = load_document(filepath)
    else:
        clause = request.form.get("clause")

    if not clause:
        return "No contract text provided", 400

    # --------------------------------------
    # Run LangGraph
    # --------------------------------------
    graph = build_graph()

    state = {"contract_text": clause}
    result_state = graph.invoke(state)

    results = result_state["final_report"]

    # --------------------------------------
    # PDF Generation
    # --------------------------------------
    generate_pdf(results)

    # --------------------------------------
    # ⭐ Extract Risk Score
    # --------------------------------------
    risk_score_text = results.get("Risk Score", "0/100")
    risk_score = risk_score_text.split("/")[0]

    # --------------------------------------
    # ⭐ Create Dashboard Link
    # --------------------------------------
    dash_url = f"/dashboard?score={risk_score}"

    results["Dashboard"] = f"<a href='{dash_url}' target='_blank'>View Dashboard</a>"

    # --------------------------------------
    # Format for HTML
    # --------------------------------------
    formatted_results = {}

    for key, value in results.items():
        html = markdown.markdown(str(value))
        formatted_results[key] = Markup(html)

    return render_template("result.html", results=formatted_results)


# ============================================
# ⭐ DASHBOARD PAGE (NEW FEATURE)
# ============================================
@app.route('/dashboard')
def dashboard():
    score = request.args.get("score", "0")

    return f"""
    <html>
    <head>
        <title>Risk Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #0f0f1a;
                color: white;
                text-align: center;
                padding: 50px;
            }}
            .score {{
                font-size: 60px;
                font-weight: bold;
                color: #ff4b5c;
                margin-top: 20px;
            }}
            .box {{
                max-width: 500px;
                margin: auto;
                padding: 30px;
                border-radius: 12px;
                background: rgba(255,255,255,0.08);
                backdrop-filter: blur(10px);
            }}
            a {{
                display: inline-block;
                margin-top: 30px;
                padding: 12px 25px;
                background: #764ba2;
                color: white;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
            }}
            a:hover {{
                background: #5b3b88;
            }}
        </style>
    </head>

    <body>
        <h1>📊 Risk Score Dashboard</h1>
        <div class="box">
            <p>Your Contract Risk Score is:</p>
            <div class="score">{score}/100</div>
        </div>
        <a href="/">Analyze Another Contract</a>
    </body>
    </html>
    """


# ============================================
# RUN APP
# ============================================
if __name__ == '__main__':
    app.run(debug=True)