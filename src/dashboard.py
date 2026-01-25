import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import io
import os
import uuid

# --- CONFIGURATION ---
st.set_page_config(page_title="Thesis BI Chat", layout="wide", page_icon="🤖")
AGENT_API_URL = os.getenv("AGENT_API_URL", "http://agent_app:8000")

# --- SESSION STATE ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("🗂️ Session History")
    st.caption(f"ID: {st.session_state.session_id}")
    use_external_prices = st.toggle(
        "Use external prices (Tavily)",
        value=True,
        help="When off, price questions use only internal database data."
    )
    if st.button("Clear Memory"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# --- HELPER: SAFE CHART DRAWING ---
def render_chart(chart_json):
    """Render chart by type (bar, line, pie, scatter)."""
    try:
        if not chart_json or "data" not in chart_json:
            return

        chart_type = (chart_json.get("type") or "bar").lower()
        labels = chart_json["data"].get("labels", [])
        values = chart_json["data"].get("values", [])

        # Ensure arrays are same length
        min_len = min(len(labels), len(values))
        if min_len == 0:
            st.warning("Chart data is empty.")
            return

        df = pd.DataFrame({
            "Label": labels[:min_len],
            "Value": values[:min_len]
        })

        if "title" in chart_json:
            st.caption(chart_json["title"])

        if chart_type == "line":
            fig = px.line(df, x="Label", y="Value", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "pie":
            fig = px.pie(df, names="Label", values="Value")
            st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "scatter":
            fig = px.scatter(df, x="Label", y="Value")
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = px.bar(df, x="Label", y="Value")
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"Could not render chart: {e}")

# --- MAIN CHAT ---
st.title("🤖 Agentic BI Analyst (Search + Aggregation)")

# 1. History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "artifacts" in message:
            art = message["artifacts"]
            
            # 1. Chart
            render_chart(art.get("chart_data"))
            
            # 2. Technical Details (Always Valid)
            with st.expander("🛠️ View SQL & Data"):
                st.code(art.get("sql_query", "-- No SQL Saved --"), language="sql")
                if art.get("raw_data"):
                    try:
                        st.dataframe(pd.read_csv(io.StringIO(art["raw_data"])))
                    except: st.text("Data format error")

# 2. Input
if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            try:
                # REQUEST TO API
                response = requests.post(
                    f"{AGENT_API_URL}/ask", 
                    json={
                        "prompt": prompt,
                        "session_id": st.session_state.session_id,
                        "use_external_prices": use_external_prices
                    },
                    timeout=300  # <--- INCREASED TIMEOUT TO 5 MINS
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "No answer.")
                    st.markdown(answer)
                    
                    # 1. VISUALIZATION
                    render_chart(data.get("chart_data"))

                    # 2. VALIDATION LAYER (Always Show)
                    st.divider()
                    st.subheader("🧐 Validation & Transparency")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        with st.expander("📄 SQL Query Used", expanded=False):
                            sql = data.get("sql_query")
                            if sql:
                                st.code(sql, language="sql")
                            else:
                                st.warning("SQL missing from API response.")

                    with col2:
                        with st.expander("📊 Source Data (First 100 rows)"):
                            raw = data.get("raw_data")
                            if raw:
                                try:
                                    df = pd.read_csv(io.StringIO(raw))
                                    st.dataframe(df, use_container_width=True)
                                    st.caption(f"Rows: {len(df)}")
                                except: st.text(raw)
                            else:
                                st.info("No tabular data returned.")
                    
                    # 3. Save to History
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "artifacts": data
                    })
                else:
                    st.error(f"API Error: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")