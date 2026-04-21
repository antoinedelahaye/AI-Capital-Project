import json
import os
from datetime import datetime
from .quote_analyzer import load_quotes
from .inflation import get_inflation_summary
from .llm_client import get_client, DEPLOYMENT
from .rag import build_index, retrieve, retrieve_by_document

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "database")


def build_system_prompt(query: str = "") -> str:
    """
    Build the system prompt for the chatbot.

    When *query* is provided the prompt includes only the PDF chunks most
    relevant to that query (RAG).  The full quotes.json metadata is always
    included — it is small and gives the model reliable structured facts.
    """
    quotes = load_quotes()
    quotes_json = json.dumps(quotes, indent=2)
    today = datetime.today().strftime("%Y-%m-%d")

    try:
        inf_summary = get_inflation_summary([2022, 2023, 2024, 2025], today)
        lines = "\n".join(
            f"  - From Jan {yr} to {today}: +{pct:.1f}%"
            for yr, pct in sorted(inf_summary.items())
        )
        inflation_block = f"France CPI cumulative inflation to {today}:\n{lines}"
    except Exception:
        inflation_block = "Inflation data temporarily unavailable."

    # ── RAG: retrieve only relevant PDF chunks ─────────────────────────────────
    pdf_block = ""
    if query.strip():
        try:
            chunks = retrieve(query, k=6)
            if chunks:
                excerpts = "\n\n".join(
                    f"[{c['quote_id']} — {c['source']} | relevance {c['score']:.2f}]\n{c['text']}"
                    for c in chunks
                )
                pdf_block = (
                    "--- RELEVANT PDF EXCERPTS (retrieved for this query) ---\n"
                    f"{excerpts}\n"
                    "--- END OF EXCERPTS ---"
                )
        except Exception:
            pass  # RAG unavailable — answer from metadata alone

    return f"""You are a smart procurement assistant for a capital project management team.
You have direct access to the company's historical quote database and the most relevant
excerpts from the PDF quote documents (retrieved for this specific question).
Today's date is {today}.

{inflation_block}

When answering questions:
- Cite specific quote IDs (e.g. WQ-2025-003) or PDF filenames when referencing data.
- Use the inflation figures above when comparing prices across different years.
- Be precise with numbers and dates.
- Keep answers concise and actionable.

--- HISTORICAL QUOTES DATABASE (JSON) ---
{quotes_json}
--- END OF DATABASE ---

{pdf_block}
"""


def find_comparable_quotes(submitted_text: str, parsed_quote: dict) -> dict:
    """
    Use RAG + LLM to identify which database PDFs are comparable to the
    submitted quote.  Returns {{"comparable_ids": [...], "reasoning": "..."}}.
    """
    client = get_client()
    db_quotes = load_quotes()

    # Build index if needed (no-op if fresh)
    build_index()

    # Retrieve the best-matching document excerpts for the submitted quote text
    query = (
        f"{parsed_quote.get('description', '')} "
        f"{submitted_text[:800]}"
    )
    doc_results = retrieve_by_document(query, top_docs=len(db_quotes), chunks_per_doc=2)

    # Build per-quote summaries using retrieved excerpts
    id_to_meta = {q["id"]: q for q in db_quotes}
    db_summaries_parts = []
    for doc in doc_results:
        qid = doc["quote_id"]
        meta = id_to_meta.get(qid, {})
        excerpt = "\n".join(doc["excerpts"])
        db_summaries_parts.append(
            f"--- {qid} ({meta.get('supplier','')}, "
            f"£{meta.get('total_price',0):,.0f}, {meta.get('date','')}) ---\n"
            f"Description: {meta.get('description','')}\n"
            f"Scope excerpt:\n{excerpt}"
        )
    db_summaries = "\n\n".join(db_summaries_parts)

    prompt = f"""You are a water infrastructure procurement specialist.

A new capital project quote has been submitted. Your task is to identify which quotes in the database
are genuinely comparable — meaning they cover a similar type of infrastructure work and broadly similar
scope (e.g. both are pumping station replacements, or both are pipeline construction projects).

Do NOT mark quotes as comparable if they are fundamentally different types of work
(e.g. do not match a WTW upgrade with a sewer rehabilitation project).

SUBMITTED QUOTE:
Supplier: {parsed_quote.get('supplier', 'Unknown')}
Total price: £{parsed_quote.get('total_price', 0):,.0f}
Description: {parsed_quote.get('description', '')}

Full text:
\"\"\"{submitted_text[:2000]}\"\"\"

DATABASE QUOTES:
{db_summaries}

Return ONLY a JSON object:
{{
  "comparable_ids": ["WQ-XXXX-XXX", ...],
  "reasoning": "One sentence explaining why these are comparable."
}}

If no quote is comparable, return {{"comparable_ids": [], "reasoning": "No comparable quotes found."}}
No markdown fences."""

    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_completion_tokens=300,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)


def parse_line_items(quote_text: str, scope_description: str, total_price: float, market_avg: float) -> list[dict]:
    """Extract line items from quote text with market estimates and risk flags."""
    client = get_client()
    today = datetime.today().strftime("%Y-%m-%d")
    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        temperature=0,
        max_completion_tokens=900,
        messages=[{
            "role": "user",
            "content": f"""Extract all line items from this capital project quote for a UK water utility.
Scope: {scope_description}
Total quoted price: £{total_price:,.0f}
Comparable market average (inflation-adjusted): £{market_avg:,.0f}
Today: {today}

For each line item return:
- description (string): clear label for the cost component
- amount (number): quoted price in GBP as a plain number
- unit (string): "lump sum", "per metre", "per unit", etc.
- market_estimate (number): typical UK water industry market rate for this component in GBP
- risk_level (string): "Low", "Amber", or "High" based on how amount compares to market
- notes (string): one sentence explaining the risk level

If the quote lacks explicit line items, decompose the total intelligently into typical components
for this type of work (labour, materials, plant, preliminaries, contingency, etc.).

Quote text:
\"\"\"{quote_text}\"\"\"

Return ONLY a valid JSON array. No markdown fences, no explanation.""",
        }],
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    items = json.loads(raw)
    for item in items:
        item["amount"] = float(item.get("amount") or 0)
        item["market_estimate"] = float(item.get("market_estimate") or 0)
    return items


def build_agent_summary(parsed: dict, analysis: dict, line_items: list[dict]) -> dict:
    """Generate an executive procurement summary and any additional KPIs."""
    client = get_client()
    today = datetime.today().strftime("%Y-%m-%d")

    comparable_ids = analysis.get("comparable_ids", [])
    supplier_line = (
        f"- Supplier own avg (comparable set): £{analysis['supplier_own_avg']:,.0f} "
        f"({analysis['supplier_premium_pct']:+.1f}% premium)"
        if analysis.get("supplier_own_avg") is not None
        else "- No prior quotes from this supplier in the comparable set"
    )

    prompt = f"""You are a senior procurement director at a UK water utility (AMP8 framework). Today: {today}.

Review the quote, benchmark data, and line items below. Respond with a single JSON object:
{{
  "summary": "<markdown string with sections: **Overall Verdict**, **Key Findings**, **Risk Flags**, **Recommended Actions**>",
  "additional_kpis": [
    {{"label": "<metric name>", "value": "<formatted value>", "status": "green|amber|red|neutral", "note": "<one line>"}}
  ]
}}

Rules:
- summary must contain exactly these four sections using **bold** headers
- **Overall Verdict**: one sentence with Accept / Negotiate / Reject + rationale
- **Key Findings**: 3-5 bullet points with specific numbers
- **Risk Flags**: ⚠️ prefix each flag; write "No significant risk flags." if none
- **Recommended Actions**: 2-3 numbered actionable steps
- additional_kpis: only include genuinely insightful extra metrics; can be []
- Be direct, use actual numbers and supplier names

SUBMITTED QUOTE:
{json.dumps(parsed, indent=2)}

BENCHMARK (compared against {len(comparable_ids)} comparable database quote(s): {', '.join(comparable_ids)}):
- Submitted price: £{analysis['new_quote_price']:,.0f}
- Comparable avg (adj.): £{analysis['inflation_adjusted_mean']:,.0f} ({analysis['new_quote_vs_mean_pct']:+.1f}%)
- Comparable median (adj.): £{analysis['inflation_adjusted_median']:,.0f}
- Percentile rank: {analysis['new_quote_percentile']:.0f}th
- Z-score: {analysis['new_quote_z_score']}
- Sample size: {analysis['sample_size']} quote(s)
{supplier_line}
- Historical best: £{analysis['best_price']:,.0f} ({analysis['best_price_distance_pct']:+.1f}% above best)
- Contractor benchmarks: {json.dumps(analysis['benchmark'])}

LINE ITEMS:
{json.dumps(line_items, indent=2)}

Return ONLY the JSON object. No markdown fences."""

    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_completion_tokens=1000,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)


def parse_quote(text: str) -> dict:
    """Use the LLM to extract structured fields from raw quote text."""
    today = datetime.today().strftime("%Y-%m-%d")
    client = get_client()
    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        temperature=0,
        max_completion_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""Extract the following fields from the quote text and return ONLY a valid JSON object.

Fields:
- supplier (string): company providing the quote
- description (string): brief description of goods/services, max 100 chars
- total_price (number): total price as a plain number in GBP, no currency symbols
- date (string): quote date in YYYY-MM-DD format; use {today} if not stated

Quote text:
\"\"\"
{text}
\"\"\"

Return ONLY the JSON object. No markdown fences, no explanation.""",
        }],
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)
