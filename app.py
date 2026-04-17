import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backend.chatbot import build_system_prompt, parse_quote
from backend.llm_client import DEPLOYMENT, get_client
from backend.quote_analyzer import analyze_quote, get_dataframe

st.set_page_config(
    page_title="Capital Quote Analyser",
    page_icon="📊",
    layout="wide",
)

st.title("Capital Quote Analyser")

client = get_client()


def _stream(api_stream):
    for chunk in api_stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

tab1, tab2 = st.tabs(["💬 Quote Chatbot", "📊 Quote Analysis"])


# ── Tab 1: Chatbot ─────────────────────────────────────────────────────────────
with tab1:
    st.caption("Ask anything about historical quotes — prices, suppliers, categories, trends.")

    if st.button("Clear conversation", key="clear_chat"):
        st.session_state.messages = []
        st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about past quotes…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner(""):
                system_prompt = build_system_prompt()
            api_messages = [{"role": "system", "content": system_prompt}] + [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
            stream = client.chat.completions.create(
                model=DEPLOYMENT,
                messages=api_messages,
                stream=True,
                temperature=0.3,
                max_completion_tokens=800,
            )
            response = st.write_stream(_stream(stream))

        st.session_state.messages.append({"role": "assistant", "content": response})


# ── Tab 2: Quote Analysis ──────────────────────────────────────────────────────
with tab2:
    col_upload, col_results = st.columns([1, 1.2], gap="large")

    CATEGORIES = [
        "Server Infrastructure",
        "Network Equipment",
        "Software Licenses",
        "Cloud Services",
        "IT Consulting",
        "Cybersecurity Solutions",
    ]

    with col_upload:
        st.subheader("Upload a Quote")
        input_mode = st.radio("Input method", ["Paste text", "Upload file"], horizontal=True)

        quote_text = ""
        if input_mode == "Paste text":
            quote_text = st.text_area(
                "Paste the quote here",
                height=220,
                placeholder="Enter quote details — supplier name, item descriptions, prices, date…",
            )
        else:
            uploaded = st.file_uploader("Upload file", type=["txt", "json", "csv"])
            if uploaded:
                try:
                    raw_bytes = uploaded.read()
                    if len(raw_bytes) == 0:
                        st.error("The uploaded file is empty.")
                    else:
                        quote_text = raw_bytes.decode("utf-8")
                        st.text_area("File content (preview)", quote_text, height=220)
                except Exception:
                    st.error("Could not read file. Please use a plain text, JSON, or CSV file.")

        category = st.selectbox("Quote Category", CATEGORIES)

        run_btn = st.button(
            "Run Analysis",
            type="primary",
            disabled=not bool(quote_text.strip()),
        )

        if run_btn and quote_text.strip():
            parsed = None
            with st.spinner("Parsing quote with AI…"):
                try:
                    parsed = parse_quote(quote_text, category)
                    parsed["category"] = category
                except json.JSONDecodeError:
                    st.error("Could not parse the quote into structured data. Try rephrasing or adding more detail.")
                except Exception as e:
                    st.error(f"Parsing error: {e}")

            if parsed:
                st.success("Quote parsed successfully")
                st.json(parsed)

                with st.spinner("Running analysis…"):
                    analysis = analyze_quote(parsed)

                st.session_state["analysis"] = analysis
                st.session_state["parsed_quote"] = parsed

    with col_results:
        if "analysis" in st.session_state:
            analysis = st.session_state["analysis"]
            parsed = st.session_state["parsed_quote"]

            if "error" in analysis:
                st.error(analysis["error"])
            else:
                pct = analysis["new_quote_vs_mean_pct"]
                m1, m2, m3 = st.columns(3)
                m1.metric("Your Quote", f"€{analysis['new_quote_price']:,.0f}")
                m2.metric(
                    "Market Avg (infl.-adj.)",
                    f"€{analysis['inflation_adjusted_mean']:,.0f}",
                    f"{pct:+.1f}%",
                    delta_color="inverse",
                )
                m3.metric("Percentile", f"{analysis['new_quote_percentile']:.0f}th")

                st.markdown("---")

                # Supplier benchmark chart
                st.subheader("Supplier Benchmark (Inflation-Adjusted to Today)")
                bench_df = pd.DataFrame(analysis["benchmark"])
                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=bench_df["supplier"],
                        y=bench_df["avg_adjusted"],
                        name="Hist. Avg (adj.)",
                        marker_color="#4C72B0",
                        text=bench_df["avg_adjusted"].apply(lambda v: f"€{v:,.0f}"),
                        textposition="outside",
                    )
                )
                fig.add_hline(
                    y=analysis["new_quote_price"],
                    line_dash="dash",
                    line_color="#DD4444",
                    annotation_text=f"Your Quote  €{analysis['new_quote_price']:,.0f}",
                    annotation_position="top right",
                )
                fig.update_layout(
                    xaxis_tickangle=-20,
                    yaxis_title="Price (EUR)",
                    height=320,
                    margin=dict(t=40, b=10),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

                # Outlier flag
                if analysis["outliers"]:
                    st.warning(
                        f"{len(analysis['outliers'])} outlier(s) detected in historical data for this category."
                    )
                    with st.expander("View Outliers"):
                        st.dataframe(pd.DataFrame(analysis["outliers"]), use_container_width=True)
                else:
                    st.info("No outliers detected in historical data for this category.")

                # Historical table
                with st.expander(f"Historical Quotes — {analysis['category']} ({analysis['sample_size']} records)"):
                    st.dataframe(pd.DataFrame(analysis["historical_quotes"]), use_container_width=True)

                # AI Insights (streamed)
                st.subheader("AI Insights")
                insight_prompt = f"""Analyse the following procurement quote and provide exactly 4 concise, numbered business insights.

Submitted quote:
{json.dumps(parsed, indent=2)}

Analysis results:
- Category: {analysis['category']}
- Submitted price: €{analysis['new_quote_price']:,.0f}
- Inflation-adjusted market average: €{analysis['inflation_adjusted_mean']:,.0f}
- Inflation-adjusted market median: €{analysis['inflation_adjusted_median']:,.0f}
- Position vs. market average: {pct:+.1f}%
- Percentile rank among historical quotes: {analysis['new_quote_percentile']:.0f}th
- Z-score: {analysis['new_quote_z_score']}
- Historical sample size: {analysis['sample_size']} quotes
- Outliers in DB: {len(analysis['outliers'])}
- Supplier benchmark (inflation-adjusted): {json.dumps(analysis['benchmark'], indent=2)}

Address: price competitiveness, supplier comparison, risk flags, and negotiation recommendations.
Be direct and specific — reference numbers and supplier names where relevant."""

                stream = client.chat.completions.create(
                    model=DEPLOYMENT,
                    messages=[{"role": "user", "content": insight_prompt}],
                    stream=True,
                    temperature=0.4,
                    max_completion_tokens=600,
                )
                st.write_stream(_stream(stream))

        else:
            # Overview of the historical database
            st.subheader("Historical Database Overview")
            try:
                df = get_dataframe()

                c1, c2 = st.columns(2)
                with c1:
                    cat_cnt = df["category"].value_counts().reset_index()
                    cat_cnt.columns = ["Category", "Count"]
                    fig = px.pie(
                        cat_cnt,
                        names="Category",
                        values="Count",
                        title="Quotes by Category",
                        hole=0.35,
                    )
                    fig.update_layout(margin=dict(t=40, b=0))
                    st.plotly_chart(fig, use_container_width=True)

                with c2:
                    sup_avg = (
                        df.groupby("supplier")["total_price"]
                        .mean()
                        .reset_index()
                        .rename(columns={"total_price": "Avg Price (EUR)", "supplier": "Supplier"})
                        .sort_values("Avg Price (EUR)", ascending=False)
                    )
                    fig = px.bar(
                        sup_avg,
                        x="Supplier",
                        y="Avg Price (EUR)",
                        title="Avg Quote Value by Supplier",
                        color="Avg Price (EUR)",
                        color_continuous_scale="Blues",
                    )
                    fig.update_layout(
                        xaxis_tickangle=-30,
                        margin=dict(t=40, b=0),
                        showlegend=False,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.dataframe(
                    df[["id", "date", "supplier", "category", "description", "total_price", "currency", "status"]]
                    .assign(date=df["date"].dt.strftime("%Y-%m-%d"))
                    .sort_values("date", ascending=False)
                    .reset_index(drop=True),
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Could not load database: {e}")
