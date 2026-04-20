import base64
import io
import json
import os
import re

import streamlit.components.v1 as components

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pypdf import PdfReader

from backend.chatbot import build_system_prompt, parse_quote
from backend.llm_client import DEPLOYMENT, get_client
from backend.quote_analyzer import analyze_quote, get_dataframe, load_quotes

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AquaCapital — Quote Intelligence",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ---------- font & base ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ---------- hide default streamlit chrome ---------- */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0 !important; }

/* ---------- hero banner ---------- */
.hero {
    background: linear-gradient(135deg, #003B6F 0%, #005F9E 50%, #0097A7 100%);
    border-radius: 16px;
    padding: 32px 40px 28px 40px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: "";
    position: absolute;
    top: -60px; right: -60px;
    width: 260px; height: 260px;
    border-radius: 50%;
    background: rgba(255,255,255,0.06);
}
.hero::after {
    content: "";
    position: absolute;
    bottom: -80px; right: 120px;
    width: 320px; height: 320px;
    border-radius: 50%;
    background: rgba(0,151,167,0.18);
}
.hero-title {
    color: #ffffff;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
    margin: 0 0 4px 0;
}
.hero-sub {
    color: #B3D9F0;
    font-size: 14px;
    font-weight: 400;
    margin: 0 0 20px 0;
}
.hero-pills { display: flex; gap: 10px; flex-wrap: wrap; }
.hero-pill {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    color: #ffffff;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 14px;
    border-radius: 20px;
    backdrop-filter: blur(4px);
}

/* ---------- KPI cards ---------- */
.kpi-grid { display: flex; gap: 14px; margin-bottom: 20px; flex-wrap: wrap; }
.kpi-card {
    flex: 1; min-width: 140px;
    border-radius: 12px;
    padding: 18px 20px 14px 20px;
    position: relative;
    overflow: hidden;
}
.kpi-card.blue  { background: linear-gradient(135deg, #003B6F, #0072BC); }
.kpi-card.teal  { background: linear-gradient(135deg, #006064, #0097A7); }
.kpi-card.green { background: linear-gradient(135deg, #1B5E20, #2E7D32); }
.kpi-card.amber { background: linear-gradient(135deg, #E65100, #F57C00); }
.kpi-card::after {
    content: "";
    position: absolute;
    bottom: -20px; right: -20px;
    width: 90px; height: 90px;
    border-radius: 50%;
    background: rgba(255,255,255,0.08);
}
.kpi-icon { font-size: 22px; margin-bottom: 8px; }
.kpi-label {
    color: rgba(255,255,255,0.75);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 4px;
}
.kpi-value {
    color: #ffffff;
    font-size: 22px;
    font-weight: 700;
    line-height: 1;
}
.kpi-delta {
    color: rgba(255,255,255,0.6);
    font-size: 11px;
    margin-top: 4px;
}

/* ---------- section headers ---------- */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 20px 0 12px 0;
}
.section-icon {
    width: 32px; height: 32px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}
.section-icon.blue  { background: #E3F2FD; }
.section-icon.teal  { background: #E0F7FA; }
.section-icon.green { background: #E8F5E9; }
.section-icon.amber { background: #FFF3E0; }
.section-title {
    font-size: 15px;
    font-weight: 600;
    color: #1A237E;
    margin: 0;
}
.section-divider {
    height: 2px;
    background: linear-gradient(90deg, #0072BC, #0097A7, transparent);
    border-radius: 2px;
    margin-bottom: 16px;
}

/* ---------- metric cards (analysis) ---------- */
.metric-row { display: flex; gap: 12px; margin-bottom: 18px; }
.metric-box {
    flex: 1;
    border-radius: 12px;
    padding: 16px 18px;
    text-align: center;
    border: 1px solid;
}
.metric-box.neutral { background: #F0F7FF; border-color: #B3D4F0; }
.metric-box.good    { background: #F0FFF4; border-color: #86EFAC; }
.metric-box.warn    { background: #FFFBEB; border-color: #FCD34D; }
.metric-box.bad     { background: #FFF0F0; border-color: #FCA5A5; }
.metric-box-label { font-size: 11px; color: #64748B; font-weight: 500; text-transform: uppercase; letter-spacing: 0.6px; }
.metric-box-value { font-size: 22px; font-weight: 700; color: #1E293B; margin: 4px 0 2px; }
.metric-box-delta { font-size: 12px; font-weight: 600; }
.delta-pos { color: #16A34A; }
.delta-neg { color: #DC2626; }
.delta-neu { color: #64748B; }

/* ---------- insight card ---------- */
.insight-card {
    background: linear-gradient(135deg, #F0F7FF 0%, #E8F4FE 100%);
    border: 1px solid #BFDBFE;
    border-left: 4px solid #0072BC;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 8px;
}
.insight-card p { margin: 0; color: #1E3A5F; font-size: 14px; line-height: 1.6; }

/* ---------- chat styling ---------- */
.chat-header {
    background: linear-gradient(135deg, #E3F2FD, #E0F7FA);
    border: 1px solid #B3D9F0;
    border-radius: 12px;
    padding: 12px 18px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.chat-badge {
    background: linear-gradient(135deg, #0072BC, #0097A7);
    color: white;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.chat-title { font-size: 14px; font-weight: 600; color: #1A237E; }
.chat-sub   { font-size: 12px; color: #546E7A; margin-top: 2px; }

/* ---------- upload panel ---------- */
.upload-panel {
    background: #F8FAFE;
    border: 1.5px dashed #90CAF9;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 14px;
}
.upload-panel-solid {
    background: #F8FAFE;
    border: 1px solid #DBEAFE;
    border-radius: 12px;
    padding: 20px;
}

/* ---------- status badges ---------- */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
}
.badge-accepted { background: #DCFCE7; color: #166534; }
.badge-rejected { background: #FEE2E2; color: #991B1B; }
.badge-pending  { background: #FEF9C3; color: #854D0E; }

/* ---------- tab override ---------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #EFF6FF;
    border-radius: 10px;
    padding: 4px;
    border: 1px solid #DBEAFE;
    margin-bottom: 20px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 500;
    font-size: 14px;
    color: #475569;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #0072BC, #0097A7) !important;
    color: white !important;
}

/* ---------- button override ---------- */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0072BC, #0097A7);
    border: none;
    border-radius: 8px;
    font-weight: 600;
    letter-spacing: 0.3px;
    transition: opacity 0.2s;
}
.stButton > button[kind="primary"]:hover { opacity: 0.88; }

/* ---------- form submit button ---------- */
.stFormSubmitButton > button {
    border-radius: 8px;
    font-weight: 600;
}

/* ---------- expander ---------- */
.streamlit-expanderHeader {
    background: #F0F7FF;
    border-radius: 8px;
    font-weight: 500;
}

/* ---------- dataframe ---------- */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* ---------- source panel ---------- */
.src-panel-title {
    font-size: 11px;
    font-weight: 700;
    color: #94A3B8;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid #E2ECF8;
}
.src-file-card {
    background: #fff;
    border: 1px solid #E2ECF8;
    border-radius: 10px;
    margin-bottom: 12px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.src-file-header {
    background: linear-gradient(90deg, #EEF4FF 0%, #F0F7FF 100%);
    padding: 9px 14px;
    font-size: 12px;
    font-weight: 600;
    color: #0072BC;
    border-bottom: 1px solid #E2ECF8;
    display: flex;
    align-items: center;
    gap: 6px;
}
.src-file-body {
    padding: 10px 14px;
    font-size: 11px;
    color: #475569;
    line-height: 1.6;
    max-height: 160px;
    overflow-y: auto;
    white-space: pre-wrap;
    font-family: 'Inter', monospace;
}
.src-quote-card {
    background: #fff;
    border: 1px solid #E2ECF8;
    border-left: 3px solid #0097A7;
    border-radius: 10px;
    padding: 11px 14px;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.src-quote-id {
    font-weight: 700;
    color: #0072BC;
    font-size: 13px;
    margin-bottom: 5px;
}
.src-quote-field {
    font-size: 12px;
    color: #64748B;
    margin-top: 3px;
    line-height: 1.4;
}
.src-empty {
    text-align: center;
    padding: 50px 20px;
    color: #CBD5E1;
}
.src-cited-badge {
    display: inline-block;
    background: #0097A7;
    color: #fff;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 2px 7px;
    border-radius: 20px;
    margin-left: 8px;
    vertical-align: middle;
    text-transform: uppercase;
}

/* ---------- hide "press enter to submit" hint ---------- */
[data-testid="InputInstructions"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

client = get_client()


def _stream(api_stream):
    for chunk in api_stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database")


try:
    import fitz as _fitz
except ImportError:
    _fitz = None


def _extract_highlight_terms(response_text: str) -> list[str]:
    terms: set[str] = set()
    terms.update(re.findall(r'£[\d,]+(?:\.\d+)?', response_text))
    terms.update(re.findall(r'\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b', response_text))
    terms.update(re.findall(r'\b\d{4,6}\b', response_text))
    terms.update(re.findall(r'\b\d{4}-\d{2}-\d{2}\b', response_text))
    terms.update(re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b', response_text))
    return [t for t in terms if len(t) >= 3]


def _make_highlighted_pdf(pdf_path: str, terms: list[str]) -> bytes:
    if _fitz is None:
        with open(pdf_path, "rb") as f:
            return f.read()
    doc = _fitz.open(pdf_path)
    for page in doc:
        for term in terms:
            for rect in page.search_for(term):
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=(1.0, 0.92, 0.23))
                annot.update()
    return doc.tobytes()


def _extract_sources(response_text: str) -> dict:
    sources: dict = {"pdfs": [], "quotes": [], "response_text": response_text}
    cited_pdfs = {p.lower() for p in re.findall(r"\b([\w\-]+\.pdf)\b", response_text, re.IGNORECASE)}
    for fname in sorted(os.listdir(_DB_DIR)):
        if not fname.lower().endswith(".pdf"):
            continue
        stem = re.sub(r"_\d{8}", "", fname[:-4]).lower()
        if fname.lower() in cited_pdfs or stem in response_text.lower():
            fpath = os.path.join(_DB_DIR, fname)
            try:
                reader = PdfReader(fpath)
                text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
                if text:
                    sources["pdfs"].append({"filename": fname, "text": text, "path": fpath})
            except Exception:
                pass
    cited_ids = set(re.findall(r"\b(Q\d{3,4})\b", response_text))
    if cited_ids:
        sources["quotes"] = [q for q in load_quotes() if q.get("id") in cited_ids]
    return sources


# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_sources" not in st.session_state:
    st.session_state.last_sources = {"pdfs": [], "quotes": [], "response_text": ""}
if "pending_response" not in st.session_state:
    st.session_state.pending_response = False

# ── Hero banner ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-title">💧 AquaCapital — Quote Intelligence Platform</div>
  <div class="hero-sub">AI-powered capital project procurement analysis for UK water utilities · AMP8 benchmarked</div>
  <div class="hero-pills">
    <span class="hero-pill">🏗️ Capital Projects</span>
    <span class="hero-pill">📊 AMP8 Benchmarks</span>
    <span class="hero-pill">🤖 AI Insights</span>
    <span class="hero-pill">💷 GBP · Inflation-Adjusted</span>
    <span class="hero-pill">📄 PDF Quote Analysis</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["💬  Quote Chatbot", "📊  Quote Analysis"])

CATEGORIES = [
    "Water Treatment Infrastructure",
    "Pipeline Infrastructure",
    "Pumping Infrastructure",
    "Network Rehabilitation",
    "Civil & Structural Works",
    "Mechanical & Electrical",
    "Environmental & Compliance",
    "Project Management & Consulting",
]

# ── Tab 1 : Chatbot ────────────────────────────────────────────────────────────
with tab1:
    chat_col, src_col = st.columns([3, 2], gap="large")

    with chat_col:
        st.markdown("""
        <div class="chat-header">
          <div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span class="chat-title">Procurement Intelligence Assistant</span>
              <span class="chat-badge">AI</span>
            </div>
            <div class="chat-sub">Ask about historical quotes, contractor performance, pricing trends, AMP8 benchmarks&hellip;</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("chat_form", clear_on_submit=True):
            col_input, col_btn, col_clear = st.columns([5, 2, 1.5])
            with col_input:
                prompt = st.text_input(
                    "prompt",
                    placeholder="e.g. What did we pay for ductile iron pipes? Which contractor quoted lowest on pipeline work?",
                    label_visibility="collapsed",
                )
            with col_btn:
                submitted = st.form_submit_button("Send ➤", use_container_width=True)
            with col_clear:
                cleared = st.form_submit_button("Clear", use_container_width=True)

        if cleared:
            st.session_state.messages = []
            st.session_state.last_sources = {"pdfs": [], "quotes": [], "response_text": ""}
            st.session_state.pending_response = False
            st.rerun()

        # Stage 1: store user message immediately, then rerun to show it
        if submitted and prompt.strip():
            st.session_state.messages.append({"role": "user", "content": prompt.strip()})
            st.session_state.pending_response = True
            st.rerun()

        # Show all messages (user message visible straight away)
        for msg in reversed(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align:center;padding:40px 20px;color:#94A3B8;">
              <div style="font-size:40px;margin-bottom:12px;">💬</div>
              <div style="font-size:15px;font-weight:500;color:#64748B;">No conversation yet</div>
              <div style="font-size:13px;margin-top:6px;">Try asking about quotes, contractors, or price trends</div>
            </div>
            """, unsafe_allow_html=True)

        # Stage 2: call API after user message is rendered
        if st.session_state.pending_response:
            with st.spinner("Analysing your question…"):
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
                response = "".join(_stream(stream))
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.last_sources = _extract_sources(response)
            st.session_state.pending_response = False
            st.rerun()

    with src_col:
        sources = st.session_state.last_sources
        has_sources = bool(sources["pdfs"] or sources["quotes"])

        st.markdown('<div class="src-panel-title">📎 &nbsp;Sources</div>', unsafe_allow_html=True)

        if not has_sources:
            st.markdown("""
            <div class="src-empty">
              <div style="font-size:32px;margin-bottom:10px;">📂</div>
              <div style="font-size:13px;font-weight:500;color:#94A3B8;">No sources yet</div>
              <div style="font-size:12px;margin-top:6px;color:#CBD5E1;">Files cited by the AI will<br>appear here after your first question.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            response_text = sources.get("response_text", "")
            terms = _extract_highlight_terms(response_text)

            for pdf in sources["pdfs"]:
                st.markdown(
                    f'<div class="src-file-header">📄 &nbsp;{pdf["filename"]}</div>',
                    unsafe_allow_html=True,
                )
                pdf_bytes = _make_highlighted_pdf(pdf["path"], terms)
                b64 = base64.b64encode(pdf_bytes).decode()
                components.html(
                    f"""<html><body style="margin:0;padding:0;background:#F8FAFE">
                    <embed src="data:application/pdf;base64,{b64}"
                           type="application/pdf"
                           width="100%" height="430px"
                           style="border:none;border-radius:0 0 10px 10px;display:block">
                    </body></html>""",
                    height=438,
                )

            for q in sources["quotes"]:
                price = q.get("total_price", 0)
                price_fmt = f"£{price:,.0f}" if isinstance(price, (int, float)) else str(price)
                st.markdown(f"""
                <div class="src-quote-card">
                  <div class="src-quote-id">{q.get("id", "—")}</div>
                  <div class="src-quote-field">🏢 &nbsp;{q.get("supplier", "—")}</div>
                  <div class="src-quote-field">📋 &nbsp;{q.get("description", "—")}</div>
                  <div class="src-quote-field">💷 &nbsp;{price_fmt} &nbsp;·&nbsp; {q.get("date", "—")}</div>
                  <div class="src-quote-field">🏷️ &nbsp;{q.get("category", "—")}</div>
                </div>
                """, unsafe_allow_html=True)


# ── Tab 2 : Quote Analysis ─────────────────────────────────────────────────────
with tab2:
    col_upload, col_results = st.columns([1, 1.4], gap="large")

    # ── Left panel: upload ─────────────────────────────────────────────────────
    with col_upload:
        st.markdown("""
        <div class="section-header">
          <div class="section-icon blue">📥</div>
          <div>
            <div class="section-title">Submit a Quote for Analysis</div>
          </div>
        </div>
        <div class="section-divider"></div>
        """, unsafe_allow_html=True)

        input_mode = st.radio(
            "Input method",
            ["✏️  Paste text", "📎  Upload file"],
            horizontal=True,
            label_visibility="collapsed",
        )

        quote_text = ""
        if "Paste" in input_mode:
            st.markdown('<div class="upload-panel">', unsafe_allow_html=True)
            quote_text = st.text_area(
                "Quote content",
                height=200,
                placeholder="Paste quote content here — supplier name, scope of works, line items, prices, date…",
                label_visibility="collapsed",
            )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            uploaded = st.file_uploader(
                "Upload a quote document",
                type=["txt", "json", "csv", "pdf"],
                label_visibility="collapsed",
            )
            if uploaded:
                try:
                    raw_bytes = uploaded.read()
                    if len(raw_bytes) == 0:
                        st.error("The uploaded file is empty.")
                    elif uploaded.name.lower().endswith(".pdf"):
                        reader = PdfReader(io.BytesIO(raw_bytes))
                        quote_text = "\n".join(
                            page.extract_text() or "" for page in reader.pages
                        ).strip()
                        if not quote_text:
                            st.error("Could not extract text from this PDF — it may be image-based.")
                        else:
                            with st.expander("📄 Extracted PDF content", expanded=False):
                                st.text_area("", quote_text, height=180, label_visibility="collapsed")
                            st.success(f"PDF parsed — {len(quote_text):,} characters extracted")
                    else:
                        quote_text = raw_bytes.decode("utf-8")
                        with st.expander("📄 File content preview", expanded=False):
                            st.text_area("", quote_text, height=180, label_visibility="collapsed")
                except Exception as e:
                    st.error(f"Could not read file: {e}")

        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

        cat_col, _ = st.columns([1, 0.01])
        with cat_col:
            category = st.selectbox(
                "Work Category",
                CATEGORIES,
                help="Select the AMP8 capital work category that best matches this quote.",
            )

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        run_btn = st.button(
            "🔍  Run Analysis",
            type="primary",
            use_container_width=True,
            disabled=not bool(quote_text.strip()),
        )

        if run_btn and quote_text.strip():
            parsed = None
            with st.spinner("Extracting structured data from quote…"):
                try:
                    parsed = parse_quote(quote_text, category)
                    parsed["category"] = category
                except json.JSONDecodeError:
                    st.error("Could not parse quote into structured data. Try adding more detail.")
                except Exception as e:
                    st.error(f"Parsing error: {e}")

            if parsed:
                with st.expander("✅ Parsed quote data", expanded=False):
                    st.json(parsed)
                with st.spinner("Benchmarking against historical data…"):
                    analysis = analyze_quote(parsed)
                st.session_state["analysis"] = analysis
                st.session_state["parsed_quote"] = parsed
                st.rerun()

        # ── Database overview when idle ────────────────────────────────────────
        if "analysis" not in st.session_state:
            st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="section-header">
              <div class="section-icon teal">🗄️</div>
              <div><div class="section-title">Database Snapshot</div></div>
            </div>
            <div class="section-divider"></div>
            """, unsafe_allow_html=True)
            try:
                df = get_dataframe()
                total_spend = df["total_price"].sum()
                n_quotes    = len(df)
                n_suppliers = df["supplier"].nunique()
                accepted_pct = (df["status"] == "accepted").mean() * 100

                st.markdown(f"""
                <div class="kpi-grid">
                  <div class="kpi-card blue">
                    <div class="kpi-icon">💷</div>
                    <div class="kpi-label">Total Spend</div>
                    <div class="kpi-value">£{total_spend/1e6:.1f}M</div>
                  </div>
                  <div class="kpi-card teal">
                    <div class="kpi-icon">📋</div>
                    <div class="kpi-label">Quotes</div>
                    <div class="kpi-value">{n_quotes}</div>
                  </div>
                  <div class="kpi-card green">
                    <div class="kpi-icon">🏢</div>
                    <div class="kpi-label">Contractors</div>
                    <div class="kpi-value">{n_suppliers}</div>
                  </div>
                  <div class="kpi-card amber">
                    <div class="kpi-icon">✅</div>
                    <div class="kpi-label">Accepted</div>
                    <div class="kpi-value">{accepted_pct:.0f}%</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            except Exception:
                pass

    # ── Right panel: results ───────────────────────────────────────────────────
    with col_results:
        if "analysis" in st.session_state:
            analysis = st.session_state["analysis"]
            parsed   = st.session_state["parsed_quote"]

            if "error" in analysis:
                st.error(analysis["error"])
            else:
                pct = analysis["new_quote_vs_mean_pct"]

                # ── Metric cards ───────────────────────────────────────────────
                st.markdown("""
                <div class="section-header">
                  <div class="section-icon blue">📊</div>
                  <div><div class="section-title">Benchmark Summary</div></div>
                </div>
                <div class="section-divider"></div>
                """, unsafe_allow_html=True)

                delta_class = "delta-pos" if pct < 0 else ("delta-neu" if abs(pct) < 5 else "delta-neg")
                delta_sign  = "▼" if pct < 0 else "▲"
                pct_label   = f'<span class="{delta_class}">{delta_sign} {abs(pct):.1f}% vs benchmark avg</span>'

                pct_rank = analysis["new_quote_percentile"]
                if pct_rank <= 33:
                    box_class, rank_note = "good",    "Low-cost quartile"
                elif pct_rank <= 66:
                    box_class, rank_note = "neutral",  "Mid-range"
                else:
                    box_class, rank_note = "bad",  "High-cost quartile"

                st.markdown(f"""
                <div class="metric-row">
                  <div class="metric-box neutral">
                    <div class="metric-box-label">Submitted Quote</div>
                    <div class="metric-box-value">£{analysis['new_quote_price']:,.0f}</div>
                    <div class="metric-box-delta">&nbsp;</div>
                  </div>
                  <div class="metric-box {'good' if pct < 0 else 'bad'}">
                    <div class="metric-box-label">Benchmark Avg (adj.)</div>
                    <div class="metric-box-value">£{analysis['inflation_adjusted_mean']:,.0f}</div>
                    <div class="metric-box-delta">{pct_label}</div>
                  </div>
                  <div class="metric-box {box_class}">
                    <div class="metric-box-label">Percentile Rank</div>
                    <div class="metric-box-value">{pct_rank:.0f}<sup style="font-size:13px">th</sup></div>
                    <div class="metric-box-delta" style="color:#64748B">{rank_note}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # ── Contractor benchmark chart ──────────────────────────────────
                st.markdown("""
                <div class="section-header">
                  <div class="section-icon teal">🏗️</div>
                  <div><div class="section-title">Contractor Benchmark (Inflation-Adjusted)</div></div>
                </div>
                <div class="section-divider"></div>
                """, unsafe_allow_html=True)

                bench_df = pd.DataFrame(analysis["benchmark"])
                colors_bar = [
                    "#0097A7" if s != parsed.get("supplier", "") else "#FF6B35"
                    for s in bench_df["supplier"]
                ]
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=bench_df["supplier"],
                    y=bench_df["avg_adjusted"],
                    marker_color=colors_bar,
                    text=bench_df["avg_adjusted"].apply(lambda v: f"£{v:,.0f}"),
                    textposition="outside",
                    textfont=dict(size=11),
                ))
                fig.add_hline(
                    y=analysis["new_quote_price"],
                    line_dash="dash",
                    line_color="#E53935",
                    line_width=2,
                    annotation_text=f"  Submitted  £{analysis['new_quote_price']:,.0f}",
                    annotation_position="top left",
                    annotation_font=dict(color="#E53935", size=11),
                )
                fig.update_layout(
                    plot_bgcolor="#F8FAFE",
                    paper_bgcolor="#F8FAFE",
                    xaxis=dict(tickangle=-20, tickfont=dict(size=11), gridcolor="#E2ECF8"),
                    yaxis=dict(title="Price (GBP)", tickfont=dict(size=11),
                               gridcolor="#E2ECF8", tickprefix="£"),
                    height=290,
                    margin=dict(t=30, b=10, l=10, r=10),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

                # ── Distribution strip ─────────────────────────────────────────
                st.markdown("""
                <div class="section-header">
                  <div class="section-icon green">📈</div>
                  <div><div class="section-title">Historical Price Distribution</div></div>
                </div>
                <div class="section-divider"></div>
                """, unsafe_allow_html=True)

                hist_df = pd.DataFrame(analysis["historical_quotes"])
                fig2 = go.Figure()
                fig2.add_trace(go.Histogram(
                    x=hist_df["adjusted_price"],
                    nbinsx=12,
                    marker_color="#0097A7",
                    opacity=0.75,
                    name="Historical (adj.)",
                ))
                fig2.add_vline(
                    x=analysis["new_quote_price"],
                    line_dash="dash", line_color="#E53935", line_width=2,
                    annotation_text="Submitted",
                    annotation_position="top right",
                    annotation_font=dict(color="#E53935", size=11),
                )
                fig2.add_vline(
                    x=analysis["inflation_adjusted_mean"],
                    line_dash="dot", line_color="#0072BC", line_width=2,
                    annotation_text="Avg",
                    annotation_position="top left",
                    annotation_font=dict(color="#0072BC", size=11),
                )
                fig2.update_layout(
                    plot_bgcolor="#F8FAFE",
                    paper_bgcolor="#F8FAFE",
                    xaxis=dict(title="Inflation-Adjusted Price (GBP)", tickprefix="£",
                               tickfont=dict(size=11), gridcolor="#E2ECF8"),
                    yaxis=dict(title="Count", tickfont=dict(size=11), gridcolor="#E2ECF8"),
                    height=220,
                    margin=dict(t=20, b=10, l=10, r=10),
                    showlegend=False,
                )
                st.plotly_chart(fig2, use_container_width=True)

                # ── Outlier alert ──────────────────────────────────────────────
                if analysis["outliers"]:
                    st.warning(f"⚠️  {len(analysis['outliers'])} outlier(s) detected in historical data.")
                    with st.expander("View outlier records"):
                        st.dataframe(pd.DataFrame(analysis["outliers"]), use_container_width=True)
                else:
                    st.success("✅  No outliers detected in historical benchmark data.")

                # ── Historical quotes table ────────────────────────────────────
                with st.expander(
                    f"📋  Historical quotes — {analysis['category']}  ({analysis['sample_size']} records)"
                ):
                    st.dataframe(pd.DataFrame(analysis["historical_quotes"]), use_container_width=True)

                # ── AI Insights ────────────────────────────────────────────────
                st.markdown("""
                <div class="section-header" style="margin-top:20px">
                  <div class="section-icon amber">🤖</div>
                  <div><div class="section-title">AI Procurement Insights</div></div>
                </div>
                <div class="section-divider"></div>
                """, unsafe_allow_html=True)

                insight_prompt = f"""You are a capital project procurement specialist for a UK water company \
operating under Ofwat's AMP8 regulatory framework.

Analyse the following capital project quote and provide exactly 4 concise, numbered insights \
tailored to the water industry context.

Submitted quote:
{json.dumps(parsed, indent=2)}

Benchmark analysis results:
- Work category: {analysis['category']}
- Submitted price: £{analysis['new_quote_price']:,.0f}
- Inflation-adjusted benchmark average: £{analysis['inflation_adjusted_mean']:,.0f}
- Inflation-adjusted benchmark median: £{analysis['inflation_adjusted_median']:,.0f}
- Position vs. benchmark average: {pct:+.1f}%
- Percentile rank among historical quotes: {analysis['new_quote_percentile']:.0f}th
- Z-score: {analysis['new_quote_z_score']}
- Historical sample size: {analysis['sample_size']} quotes
- Outliers in dataset: {len(analysis['outliers'])}
- Contractor benchmark (inflation-adjusted): {json.dumps(analysis['benchmark'], indent=2)}

Address the following in your 4 insights:
1. Price competitiveness vs. AMP8 water sector benchmarks
2. Contractor/supplier value assessment based on historical performance
3. Regulatory or delivery risk flags relevant to water capital projects \
(e.g. Ofwat totex, CDM, WINEP obligations)
4. Specific negotiation or procurement recommendations

Be direct, use numbers, and reference contractor names and water industry standards where relevant."""

                stream = client.chat.completions.create(
                    model=DEPLOYMENT,
                    messages=[{"role": "user", "content": insight_prompt}],
                    stream=True,
                    temperature=0.4,
                    max_completion_tokens=600,
                )
                insight_text = "".join(_stream(stream))
                st.markdown(
                    f'<div class="insight-card"><p>{insight_text.replace(chr(10), "<br>")}</p></div>',
                    unsafe_allow_html=True,
                )

                st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
                if st.button("🔄  Clear analysis", use_container_width=False):
                    del st.session_state["analysis"]
                    del st.session_state["parsed_quote"]
                    st.rerun()

        else:
            # ── Overview charts ────────────────────────────────────────────────
            st.markdown("""
            <div class="section-header">
              <div class="section-icon teal">📊</div>
              <div><div class="section-title">Portfolio Overview</div></div>
            </div>
            <div class="section-divider"></div>
            """, unsafe_allow_html=True)

            try:
                df = get_dataframe()
                total_spend = df["total_price"].sum()
                n_quotes    = len(df)
                n_suppliers = df["supplier"].nunique()
                accepted_pct = (df["status"] == "accepted").mean() * 100

                st.markdown(f"""
                <div class="kpi-grid">
                  <div class="kpi-card blue">
                    <div class="kpi-icon">💷</div>
                    <div class="kpi-label">Total Portfolio Spend</div>
                    <div class="kpi-value">£{total_spend/1e6:.1f}M</div>
                    <div class="kpi-delta">All categories · all years</div>
                  </div>
                  <div class="kpi-card teal">
                    <div class="kpi-icon">📋</div>
                    <div class="kpi-label">Quotes on Record</div>
                    <div class="kpi-value">{n_quotes}</div>
                    <div class="kpi-delta">Across {df['category'].nunique()} categories</div>
                  </div>
                  <div class="kpi-card green">
                    <div class="kpi-icon">🏢</div>
                    <div class="kpi-label">Contractors</div>
                    <div class="kpi-value">{n_suppliers}</div>
                    <div class="kpi-delta">Active supply chain</div>
                  </div>
                  <div class="kpi-card amber">
                    <div class="kpi-icon">✅</div>
                    <div class="kpi-label">Acceptance Rate</div>
                    <div class="kpi-value">{accepted_pct:.0f}%</div>
                    <div class="kpi-delta">Of all submitted quotes</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    cat_cnt = df["category"].value_counts().reset_index()
                    cat_cnt.columns = ["Category", "Count"]
                    fig = px.pie(
                        cat_cnt,
                        names="Category",
                        values="Count",
                        title="Quotes by Category",
                        hole=0.42,
                        color_discrete_sequence=px.colors.sequential.Blues_r,
                    )
                    fig.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        margin=dict(t=40, b=10),
                        legend=dict(font=dict(size=10)),
                        title_font=dict(size=13, color="#1A237E"),
                    )
                    fig.update_traces(textposition="inside", textinfo="percent+label",
                                      textfont_size=10)
                    st.plotly_chart(fig, use_container_width=True)

                with c2:
                    sup_avg = (
                        df.groupby("supplier")["total_price"]
                        .mean()
                        .reset_index()
                        .rename(columns={"total_price": "Avg Quote (GBP)", "supplier": "Supplier"})
                        .sort_values("Avg Quote (GBP)", ascending=True)
                    )
                    fig2 = px.bar(
                        sup_avg,
                        x="Avg Quote (GBP)",
                        y="Supplier",
                        orientation="h",
                        title="Avg Quote Value by Contractor",
                        color="Avg Quote (GBP)",
                        color_continuous_scale=["#B3D9F0", "#0072BC", "#003B6F"],
                        text="Avg Quote (GBP)",
                    )
                    fig2.update_traces(
                        texttemplate="£%{text:,.0f}",
                        textposition="outside",
                        textfont=dict(size=10),
                    )
                    fig2.update_layout(
                        plot_bgcolor="#F8FAFE",
                        paper_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(tickprefix="£", tickfont=dict(size=10),
                                   gridcolor="#E2ECF8", title=""),
                        yaxis=dict(tickfont=dict(size=10), title=""),
                        margin=dict(t=40, b=10, l=10, r=80),
                        coloraxis_showscale=False,
                        title_font=dict(size=13, color="#1A237E"),
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                # ── Spend over time ────────────────────────────────────────────
                df["year"] = df["date"].dt.year
                yearly = df.groupby("year")["total_price"].sum().reset_index()
                yearly.columns = ["Year", "Total Spend"]
                fig3 = px.area(
                    yearly, x="Year", y="Total Spend",
                    title="Annual Quote Spend",
                    color_discrete_sequence=["#0097A7"],
                )
                fig3.update_traces(fill="tozeroy", line_width=2,
                                   fillcolor="rgba(0,151,167,0.15)")
                fig3.update_layout(
                    plot_bgcolor="#F8FAFE",
                    paper_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(tickfont=dict(size=11), gridcolor="#E2ECF8", title=""),
                    yaxis=dict(tickprefix="£", tickfont=dict(size=11),
                               gridcolor="#E2ECF8", title=""),
                    height=220,
                    margin=dict(t=40, b=10, l=10, r=10),
                    title_font=dict(size=13, color="#1A237E"),
                )
                st.plotly_chart(fig3, use_container_width=True)

                # ── Quote table ────────────────────────────────────────────────
                with st.expander("📋  Full quote register", expanded=False):
                    st.dataframe(
                        df[["id", "date", "supplier", "category", "description",
                            "total_price", "currency", "status"]]
                        .assign(date=df["date"].dt.strftime("%Y-%m-%d"))
                        .sort_values("date", ascending=False)
                        .reset_index(drop=True),
                        use_container_width=True,
                    )
            except Exception as e:
                st.error(f"Could not load database: {e}")


if __name__ == "__main__":
    import os
    import subprocess
    import sys
    import threading
    import time

    if not os.environ.get("_AQUACAPITAL_LAUNCHED"):
        import socket

        def _open_edge():
            for _ in range(30):
                time.sleep(1)
                try:
                    with socket.create_connection(("localhost", 8501), timeout=1):
                        break
                except OSError:
                    continue
            subprocess.Popen(["cmd", "/c", "start", "msedge", "http://localhost:8501"])

        threading.Thread(target=_open_edge, daemon=True).start()
        env = os.environ.copy()
        env["_AQUACAPITAL_LAUNCHED"] = "1"
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", __file__, "--server.headless=true"],
            env=env,
        )
