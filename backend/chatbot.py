import json
import os
from datetime import datetime
from pypdf import PdfReader
from .quote_analyzer import load_quotes, VALID_CATEGORIES
from .inflation import get_inflation_summary
from .llm_client import get_client, DEPLOYMENT

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "database")


def _load_pdf_texts() -> str:
    """Extract text from all PDF files found in the database folder."""
    parts = []
    for fname in sorted(os.listdir(DB_DIR)):
        if not fname.lower().endswith(".pdf"):
            continue
        path = os.path.join(DB_DIR, fname)
        try:
            reader = PdfReader(path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if text:
                parts.append(f"=== {fname} ===\n{text}")
        except Exception:
            pass
    return "\n\n".join(parts)


def build_system_prompt() -> str:
    quotes = load_quotes()
    quotes_json = json.dumps(quotes, indent=2)
    today = datetime.today().strftime("%Y-%m-%d")

    try:
        inf_summary = get_inflation_summary([2022, 2023, 2024], today)
        lines = "\n".join(
            f"  - From Jan {yr} to {today}: +{pct:.1f}%"
            for yr, pct in sorted(inf_summary.items())
        )
        inflation_block = f"France CPI cumulative inflation to {today}:\n{lines}"
    except Exception:
        inflation_block = "Inflation data temporarily unavailable."

    pdf_texts = _load_pdf_texts()
    pdf_block = (
        f"--- PDF QUOTE DOCUMENTS (database folder) ---\n{pdf_texts}\n--- END OF PDF DOCUMENTS ---"
        if pdf_texts
        else ""
    )

    return f"""You are a smart procurement assistant for a capital project management team.
You have direct access to the company's historical quote database and all PDF quote documents shown below.
Today's date is {today}.

{inflation_block}

When answering questions:
- Cite specific quote IDs (e.g. Q001) or PDF filenames when referencing data.
- Use the inflation figures above when comparing prices across different years.
- Be precise with numbers and dates.
- Keep answers concise and actionable.

--- HISTORICAL QUOTES DATABASE (JSON) ---
{quotes_json}
--- END OF DATABASE ---

{pdf_block}
"""


def parse_quote(text: str, category: str) -> dict:
    """Use the LLM to extract structured fields from raw quote text."""
    categories_list = ", ".join(sorted(VALID_CATEGORIES))
    today = datetime.today().strftime("%Y-%m-%d")

    client = get_client()
    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        temperature=0,
        max_completion_tokens=300,
        messages=[
            {
                "role": "user",
                "content": f"""Extract the following fields from the quote text and return ONLY a valid JSON object.

Fields:
- supplier (string): company providing the quote
- description (string): brief description of goods/services, max 80 chars
- total_price (number): total price as a plain number in GBP, no currency symbols
- date (string): quote date in YYYY-MM-DD format; use {today} if not stated
- category (string): must be exactly one of: {categories_list}

The user has indicated the category is "{category}" — use that unless the text clearly contradicts it.

Quote text:
\"\"\"
{text}
\"\"\"

Return ONLY the JSON object. No markdown fences, no explanation.""",
            }
        ],
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)
