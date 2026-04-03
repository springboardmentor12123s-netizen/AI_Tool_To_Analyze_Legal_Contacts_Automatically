import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import inject_custom_css

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Analytics Dashboard", layout="wide", page_icon="📊")
inject_custom_css()

st.title("📊 Complete Analytics Dashboard")

st.markdown("""
### 🧠 What you're seeing:
- Multi-agent risk analysis  
- Domain-wise comparisons  
- Clause-level insights  
- Decision-support visualizations  
""")

# ---------------- DATA CHECK ----------------
if "analysis_results" not in st.session_state or not st.session_state.analysis_results:
    st.warning("No contracts analyzed yet. Please go to the Upload page.")
    st.stop()

results = st.session_state.analysis_results

# ---------------- BUILD DATAFRAME ----------------
all_risks = []
for res in results:
    if "metrics" in res and res.get("metrics") and res["metrics"].get("risks"):
        for r in res["metrics"]["risks"]:
            r["file"] = res["file"]
            all_risks.append(r)

if not all_risks:
    st.info("No structured risks were consistently extracted across the portfolio.")
    st.stop()

df = pd.DataFrame(all_risks)

# ---------------- CLEAN DATA ----------------
df['domain'] = df.get('domain', 'General').astype(str).str.title()
df['domain'] = df['domain'].replace("Finance", "Financial")

if 'severity' not in df.columns:
    df['severity'] = 5

if 'probability' not in df.columns:
    df['probability'] = 5

df['Risk Level'] = df['severity'].apply(
    lambda x: "High" if x >= 8 else "Medium" if x >= 5 else "Low"
)

# ---------------- EXECUTIVE SUMMARY ----------------
st.subheader("🚀 Executive Risk Summary")

total_risks = len(df)
high_risks = len(df[df['Risk Level'] == 'High'])
avg_severity = df['severity'].mean()

# FIXED SCORE NORMALIZATION
normalized_score = (avg_severity / 10) * 100

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=normalized_score,
    title={'text': "Overall Contract Risk Score"},
    gauge={
        'axis': {'range': [None, 100]},
        'bar': {'color': "#1e293b"},
        'steps': [
            {'range': [0, 40], 'color': "rgba(34,197,94,0.3)"},
            {'range': [40, 70], 'color': "rgba(234,179,8,0.3)"},
            {'range': [70, 100], 'color': "rgba(239,68,68,0.3)"}
        ],
    }
))

fig_gauge.update_layout(height=280)

col_metric, col_gauge = st.columns([1, 2])

with col_metric:
    st.metric("Total Issues", total_risks)
    st.metric("High Risk Clauses", high_risks)

    if normalized_score >= 70:
        st.error("🚨 Highly Risky Contract")
    elif normalized_score >= 40:
        st.warning("⚠️ Moderate Risk")
    else:
        st.success("✅ Healthy Contract")

with col_gauge:
    st.plotly_chart(fig_gauge, use_container_width=True)

st.divider()

# ---------------- ROW 1 ----------------
col1, col2 = st.columns(2)

with col1:
    risk_counts = df['Risk Level'].value_counts().reset_index()
    risk_counts.columns = ['Risk Level', 'Count']

    fig_pie = px.pie(
        risk_counts,
        values='Count',
        names='Risk Level',
        title="Overall Risk Distribution",
        color='Risk Level',
        color_discrete_map={
            "High": "#ef4444",
            "Medium": "#eab308",
            "Low": "#22c55e"
        },
        hole=0.4
    )

    st.plotly_chart(fig_pie, use_container_width=True)

    highest = risk_counts.iloc[0]
    percentage = (highest['Count'] / total_risks) * 100

    st.info(f"💡 {highest['Risk Level']} risks dominate ({round(percentage,1)}%) of the contract.")

with col2:
    domain_scores = df.groupby('domain')['severity'].sum().reset_index()

    for d in ["Legal", "Financial", "Compliance", "Operations"]:
        if d not in domain_scores['domain'].values:
            domain_scores = pd.concat([domain_scores, pd.DataFrame([{'domain': d, 'severity': 0}])], ignore_index=True)

    fig_bar = px.bar(
        domain_scores,
        x='domain',
        y='severity',
        title="Total Risk by Domain",
        color='domain',
        category_orders={"domain": ["Legal", "Financial", "Compliance", "Operations"]}
    )

    st.plotly_chart(fig_bar, use_container_width=True)

    if domain_scores['severity'].sum() > 0:
        max_domain = domain_scores.loc[domain_scores['severity'].idxmax()]['domain']
        st.warning(f"💡 {max_domain} domain has highest risk exposure.")

# ---------------- TOP RISKS ----------------
st.divider()
st.subheader("🚨 Top 5 Critical Risks")

top_risks = df.sort_values(by="severity", ascending=False).head(5)

for _, row in top_risks.iterrows():
    st.error(f"{row['domain']} → {row['risk']}")

# ---------------- ROW 2 ----------------
col3, col4 = st.columns(2)

with col3:
    pivot_df = df.groupby(['domain', 'Risk Level']).size().reset_index(name='Count')

    for d in ["Legal", "Financial", "Compliance", "Operations"]:
        if d not in pivot_df['domain'].values:
            pivot_df = pd.concat([pivot_df, pd.DataFrame([{'domain': d, 'Risk Level': 'Low', 'Count': 0}])], ignore_index=True)

    fig_stack = px.bar(
        pivot_df,
        x='domain',
        y='Count',
        color='Risk Level',
        barmode='stack',
        title="Risk Breakdown per Domain",
        category_orders={"domain": ["Legal", "Financial", "Compliance", "Operations"]},
        color_discrete_map={
            "High": "#ef4444",
            "Medium": "#eab308",
            "Low": "#22c55e"
        }
    )

    st.plotly_chart(fig_stack, use_container_width=True)

with col4:
    agent_counts = df['domain'].value_counts().reset_index()
    agent_counts.columns = ['Agent', 'Count']

    fig_agent = px.pie(
        agent_counts,
        values='Count',
        names='Agent',
        title="Agent Contribution"
    )

    st.plotly_chart(fig_agent, use_container_width=True)

# ---------------- SCATTER ----------------
st.divider()
st.subheader("📍 Severity vs Probability Matrix")

fig_scatter = px.scatter(
    df,
    x="probability",
    y="severity",
    color="domain",
    size="severity",
    hover_data=["risk", "file"],
    title="Critical Risk Positioning",
    size_max=25
)

fig_scatter.update_layout(
    xaxis=dict(range=[0, 11]),
    yaxis=dict(range=[0, 11])
)

st.plotly_chart(fig_scatter, use_container_width=True)

# ---------------- HISTOGRAM ----------------
st.divider()
st.subheader("📊 Risk Frequency Distribution")

fig_hist = px.histogram(df, x="severity", nbins=10)

st.plotly_chart(fig_hist, use_container_width=True)

# ---------------- HEATMAP ----------------
st.divider()
st.subheader("🔥 Risk Heatmap")

df['Short Risk'] = df['risk'].fillna("").apply(
    lambda x: str(x)[:50] + "..." if len(str(x)) > 50 else str(x)
)

heatmap_df = df.pivot_table(
    index='Short Risk',
    columns='domain',
    values='severity',
    aggfunc='mean'
).fillna(0)

for d in ["Legal", "Financial", "Compliance", "Operations"]:
    if d not in heatmap_df.columns:
        heatmap_df[d] = 0

# Reorder columns
cols = [col for col in ["Legal", "Financial", "Compliance", "Operations"] if col in heatmap_df.columns] + [col for col in heatmap_df.columns if col not in ["Legal", "Financial", "Compliance", "Operations"]]
heatmap_df = heatmap_df[cols]

fig_heat = px.imshow(
    heatmap_df,
    color_continuous_scale="Reds",
    aspect="auto"
)

st.plotly_chart(fig_heat, use_container_width=True)

# ---------------- DATA EXPORT ----------------
st.divider()
st.subheader("⬇️ Export Data")

csv = df.to_csv(index=False).encode('utf-8')

st.download_button(
    label="Download CSV",
    data=csv,
    file_name="contract_analysis.csv",
    mime="text/csv"
)

# ---------------- TABLE ----------------
st.divider()
st.subheader("🧾 Raw Data")

st.dataframe(df, use_container_width=True)