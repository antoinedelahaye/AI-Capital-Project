import json
import os
import pandas as pd
from datetime import datetime
from .inflation import get_inflation_multiplier

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "quotes.json")


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
    return float(str(val).replace("£", "").replace("€", "").replace(",", "").replace(" ", "").strip())


def analyze_quote(new_quote: dict, comparable_ids: list[str] | None = None) -> dict:
    """
    Compare new_quote against inflation-adjusted comparable quotes from the database.

    comparable_ids: list of quote IDs to benchmark against (from find_comparable_quotes).
                   If None or empty, falls back to all quotes in the database.
    """
    df = get_dataframe()
    today = datetime.today().strftime("%Y-%m-%d")

    if comparable_ids:
        pool = df[df["id"].isin(comparable_ids)].copy()
    else:
        pool = df.copy()

    if pool.empty:
        return {"error": "No comparable quotes found in the database."}

    # Inflate each historical quote's price to today's money
    pool["inflation_mult"] = pool["date"].apply(
        lambda d: get_inflation_multiplier(d.strftime("%Y-%m-%d"), today)
    )
    pool["adjusted_price"] = pool["total_price"] * pool["inflation_mult"]
    pool["date_str"] = pool["date"].dt.strftime("%Y-%m-%d")

    new_price = _clean_price(new_quote["total_price"])
    adj = pool["adjusted_price"]

    mean_p   = adj.mean()
    median_p = adj.median()
    std_p    = adj.std()

    # Benchmark per supplier
    bench = (
        pool.groupby("supplier")
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

    # Outlier detection: IQR method (meaningful only with n >= 4)
    q1, q3 = adj.quantile(0.25), adj.quantile(0.75)
    iqr = q3 - q1
    outlier_mask = (adj < q1 - 1.5 * iqr) | (adj > q3 + 1.5 * iqr)
    outliers = (
        pool[outlier_mask][["id", "supplier", "date_str", "description", "total_price", "adjusted_price"]]
        .rename(columns={"date_str": "date"})
        .round(0)
        .to_dict("records")
    )

    percentile   = float((adj < new_price).mean() * 100)
    z_score      = float((new_price - mean_p) / std_p) if std_p > 0 else 0.0
    vs_mean_pct  = float((new_price - mean_p) / mean_p * 100) if mean_p > 0 else 0.0

    # Supplier premium vs their own average in this comparable set
    supplier_name = str(new_quote.get("supplier", "")).strip()
    supplier_hist = pool[pool["supplier"].str.strip().str.lower() == supplier_name.lower()] if supplier_name else pd.DataFrame()
    if not supplier_hist.empty:
        supplier_own_avg    = float(supplier_hist["adjusted_price"].mean())
        supplier_premium_pct = float((new_price - supplier_own_avg) / supplier_own_avg * 100) if supplier_own_avg > 0 else None
    else:
        supplier_own_avg    = None
        supplier_premium_pct = None

    # Distance from the best (lowest) inflation-adjusted price on record
    best_price             = float(adj.min())
    best_price_distance_pct = float((new_price - best_price) / best_price * 100) if best_price > 0 else 0.0

    historical = (
        pool[["id", "supplier", "date_str", "description", "total_price", "adjusted_price"]]
        .rename(columns={"date_str": "date"})
        .sort_values("date", ascending=False)
        .round(0)
        .to_dict("records")
    )

    return {
        "comparable_ids": list(pool["id"]),
        "new_quote_price": round(new_price, 0),
        "inflation_adjusted_mean": round(mean_p, 0),
        "inflation_adjusted_median": round(median_p, 0),
        "inflation_adjusted_std": round(std_p, 0),
        "new_quote_vs_mean_pct": round(vs_mean_pct, 1),
        "new_quote_percentile": round(percentile, 1),
        "new_quote_z_score": round(z_score, 2),
        "supplier_own_avg": round(supplier_own_avg, 0) if supplier_own_avg is not None else None,
        "supplier_premium_pct": round(supplier_premium_pct, 1) if supplier_premium_pct is not None else None,
        "best_price": round(best_price, 0),
        "best_price_distance_pct": round(best_price_distance_pct, 1),
        "benchmark": bench,
        "outliers": outliers,
        "historical_quotes": historical,
        "sample_size": len(pool),
    }
