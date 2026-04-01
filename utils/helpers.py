import streamlit as st
import json
import re

def inject_custom_css():
    st.markdown("""
    <style>
    /* Add pure aesthetic adjustments across pages here without hurting original code structure */
    
    /* Card Styling */
    .css-1r6slb0, .st-emotion-cache-1wivap2, .st-emotion-cache-1c7y2kd {
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        background-color: white;
        padding: 24px;
        border: 1px solid #e2e8f0;
    }

    /* Make headers more definitive */
    h1, h2, h3 {
        color: #0f172a;
        font-family: 'Helvetica Neue', Arial, sans-serif;
    }

    /* Metric cards inside container styling hack */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #1e40af;
        font-weight: bold;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 1rem;
        font-weight: 500;
        color: #64748b;
    }

    /* Styled Container for contract text */
    .contract-viewer {
        background: #f8fafc;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #cbd5e1;
        height: 60vh;
        overflow-y: auto;
        font-family: monospace;
        line-height: 1.6;
        color: #1e293b;
    }
    </style>
    """, unsafe_allow_html=True)

def highlight_text(raw_text, risks):
    """
    Transforms the raw text string into HTML with specific risk quotes highlighted via <mark>.
    """
    html_text = raw_text.replace('\n', '<br><br>')
    
    for r in risks:
        quote = r.get("quote", "")
        if quote and len(quote) > 10 and quote != "exact text from contract if available":
            
            # Determine color by severity mapping
            sev = r.get("severity", 0)
            if sev >= 8:
                color = "rgba(239, 68, 68, 0.3)" # Red
            elif sev >= 5:
                color = "rgba(234, 179, 8, 0.3)" # Yellow
            else:
                color = "rgba(34, 197, 94, 0.3)" # Green
                
            reasoning = " | ".join(r.get("reasoning_steps", []))
            
            # Create hover tooltip tag
            tag = f'<mark style="background-color: {color}; padding: 2px; border-radius: 4px; cursor: help;" title="AI INSIGHT: {r.get("risk")} \\nREASONING: {reasoning}">{quote}</mark>'
            
            # Simple replace to avoid regex breaking on weird characters
            html_text = html_text.replace(quote, tag)
            
    return f'<div class="contract-viewer">{html_text}</div>'


def extract_json_metrics(report_text):
    """
    Robust JSON extraction from LLM Agent output block.
    """
    try:
        match = re.search(r'```json\s*(.*?)\s*```', report_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except:
        pass
    
    return None
