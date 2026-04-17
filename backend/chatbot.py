import json
from datetime import datetime
from .quote_analyzer import load_quotes, VALID_CATEGORIES
from .inflation import get_inflation_summary
from .llm_client import get_client, DEPLOYMENT


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

    return f"""You are a smart procurement assistant for a capital project management team.
You have direct access to the company's historical quote database shown below.
Today's date is {today}.

{inflation_block}

When answering questions:
- Cite specific quote IDs (e.g. Q001) when referencing data.
- Use the inflation figures above when comparing prices across different years.
- Be precise with numbers and dates.
- Keep answers concise and actionable.

--- HISTORICAL QUOTES DATABASE ---
{quotes_json}
--- END OF DATABASE ---
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
- total_price (number): total price as a plain number in EUR, no currency symbols
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
