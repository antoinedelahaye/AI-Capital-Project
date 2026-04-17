import json
import os
import pandas as pd
from datetime import datetime
from .inflation import get_inflation_multiplier

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "quotes.json")

VALID_CATEGORIES = {
    "Water Treatment Infrastructure",
    "Pipeline Infrastructure",
    "Pumping Infrastructure",
    "Network Rehabilitation",
    "Civil & Structural Works",
    "Mechanical & Electrical",
    "Environmental & Compliance",
    "Project Management & Consulting",
}


def load_quotes() -> list[dict]:
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_dataframe() -> pd.DataFrame:
    df = pd.DataFrame(load_quotes())
    df["date"] = pd.to_datetime(df["date"])
    return df


def _clean_price(val) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    return float(str(val).replace("€", "").replace(",", "").replace(" ", "").strip())


def analyze_quote(new_quote: dict) -> dict:
    """
    Compare new_quote against inflation-adjusted historical quotes in the same category.

    Required fields in new_quote: category, total_price
    Optional: supplier, description, date (defaults to today)
    """
    df = get_dataframe()
    today = datetime.today().strftime("%Y-%m-%d")
    category = new_quote.get("category", "").strip()

    same_cat = df[df["category"].str.strip().str.lower() == category.lower()].copy()
    if same_cat.empty:
        return {"error": f"No historical quotes found for category: '{category}'"}

    # Inflate each historical quote's price to today's money
    same_cat["inflation_mult"] = same_cat["date"].apply(
        lambda d: get_inflation_multiplier(d.strftime("%Y-%m-%d"), today)
    )
    same_cat["adjusted_price"] = same_cat["total_price"] * same_cat["inflation_mult"]
    same_cat["date_str"] = same_cat["date"].dt.strftime("%Y-%m-%d")

    new_price = _clean_price(new_quote["total_price"])
    adj = same_cat["adjusted_price"]

    mean_p = adj.mean()
    median_p = adj.median()
    std_p = adj.std()

    # Benchmark per supplier
    bench = (
        same_cat.groupby("supplier")
        .agg(
            avg_adjusted=("adjusted_price", "mean"),
            min_adjusted=("adjusted_price", "min"),
            max_adjusted=("adjusted_price", "max"),
            quotes=("id", "count"),
        )
        .reset_index()
        .round(0)
        .to_dict("records")
    )

    # Outlier detection: IQR method
    q1, q3 = adj.quantile(0.25), adj.quantile(0.75)
    iqr = q3 - q1
    outlier_mask = (adj < q1 - 1.5 * iqr) | (adj > q3 + 1.5 * iqr)
    outliers = (
        same_cat[outlier_mask][["id", "supplier", "date_str", "description", "total_price", "adjusted_price"]]
        .rename(columns={"date_str": "date"})
        .round(0)
        .to_dict("records")
    )

    percentile = float((adj < new_price).mean() * 100)
    z_score = float((new_price - mean_p) / std_p) if std_p > 0 else 0.0
    vs_mean_pct = float((new_price - mean_p) / mean_p * 100) if mean_p > 0 else 0.0

    historical = (
        same_cat[["id", "supplier", "date_str", "description", "total_price", "adjusted_price"]]
        .rename(columns={"date_str": "date"})
        .sort_values("date", ascending=False)
        .round(0)
        .to_dict("records")
    )

    return {
        "category": category,
        "new_quote_price": round(new_price, 0),
        "inflation_adjusted_mean": round(mean_p, 0),
        "inflation_adjusted_median": round(median_p, 0),
        "inflation_adjusted_std": round(std_p, 0),
        "new_quote_vs_mean_pct": round(vs_mean_pct, 1),
        "new_quote_percentile": round(percentile, 1),
        "new_quote_z_score": round(z_score, 2),
        "benchmark": bench,
        "outliers": outliers,
        "historical_quotes": historical,
        "sample_size": len(same_cat),
    }
