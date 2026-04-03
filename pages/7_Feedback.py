import streamlit as st
import sys, os
import pandas as pd
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import inject_custom_css

st.set_page_config(page_title="Feedback", layout="wide", page_icon="⭐")
inject_custom_css()

st.title("⭐ User Evaluation & Feedback")
st.caption("Help improve the AI Contract Analysis system with your insights.")

# ---------------- FORM ----------------
with st.form("feedback_form"):

    st.subheader("📊 Rate Your Experience")

    col1, col2 = st.columns(2)

    with col1:
        rating = st.slider("Overall Rating", 1, 5, 5)

        usability = st.selectbox(
            "Ease of Use",
            ["Excellent", "Good", "Average", "Difficult"]
        )

        accuracy = st.selectbox(
            "Accuracy of AI Insights",
            ["Very Accurate", "Accurate", "Moderate", "Needs Improvement"]
        )

    with col2:
        best_feature = st.selectbox(
            "Most Useful Feature",
            ["Viewer", "Analytics Dashboard", "Chatbot", "Report Generator"]
        )

        missing_feature = st.text_input(
            "Feature you'd like to see"
        )

    st.subheader("📝 Detailed Feedback")

    feedback = st.text_area(
        "Your feedback or suggestions",
        placeholder="E.g., Financial risk detection can be improved for penalty clauses..."
    )

    submitted = st.form_submit_button("Submit Feedback", type="primary", use_container_width=True)

# ---------------- STORE FEEDBACK ----------------
if submitted:
    
    feedback_data = {
        "timestamp": datetime.now(),
        "rating": rating,
        "usability": usability,
        "accuracy": accuracy,
        "best_feature": best_feature,
        "missing_feature": missing_feature,
        "feedback": feedback
    }

    # Save locally as CSV
    file_path = "feedback_log.csv"
    
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df = pd.concat([df, pd.DataFrame([feedback_data])], ignore_index=True)
    else:
        df = pd.DataFrame([feedback_data])

    df.to_csv(file_path, index=False)

    # ---------------- SUCCESS UI ----------------
    st.balloons()
    st.success("🎉 Thank you! Your feedback has been recorded.")

    # Dynamic response
    if rating >= 4:
        st.info("💡 Glad you liked it! We're working on making it even better.")
    else:
        st.warning("⚠️ Thanks for the feedback! We'll focus on improving your experience.")

# ---------------- SHOW PAST FEEDBACK ----------------
st.divider()
st.subheader("📂 Previous Feedback Insights")

file_path = "feedback_log.csv"

if os.path.exists(file_path):
    df = pd.read_csv(file_path)
    
    colA, colB, colC = st.columns(3)
    
    colA.metric("Total Responses", len(df))
    colB.metric("Avg Rating", round(df["rating"].mean(), 2))
    colC.metric("Top Feature", df["best_feature"].mode()[0])

    st.dataframe(df.tail(5), use_container_width=True)

else:
    st.info("No feedback submitted yet.")