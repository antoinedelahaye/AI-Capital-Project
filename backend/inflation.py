import requests
from datetime import datetime

WORLD_BANK_URL = (
    "https://api.worldbank.org/v2/country/FR/indicator/FP.CPI.TOTL"
    "?format=json&date=2019:2026&per_page=100"
)

_cpi_cache: dict[int, float] | None = None


def _fetch_cpi() -> dict[int, float]:
    try:
        resp = requests.get(WORLD_BANK_URL, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        result: dict[int, float] = {}
        if len(payload) > 1 and payload[1]:
            for entry in payload[1]:
                if entry.get("value") is not None:
                    result[int(entry["date"])] = float(entry["value"])
        return result
    except Exception:
        return {}


def get_cpi_data() -> dict[int, float]:
    global _cpi_cache
    if _cpi_cache is None:
        _cpi_cache = _fetch_cpi()
    return _cpi_cache


def _cpi_for_year(cpi_data: dict[int, float], year: int) -> float | None:
    if year in cpi_data:
        return cpi_data[year]
    prior = [y for y in cpi_data if y <= year]
    if prior:
        return cpi_data[max(prior)]
    return None


def get_inflation_multiplier(from_date: str, to_date: str | None = None) -> float:
    """
    Returns the price multiplier from from_date to to_date based on France CPI.
    E.g. 1.08 means 8% cumulative inflation. Falls back to 3%/yr if data unavailable.
    Adjustment is annual — partial years are rounded to the nearest full year.
    """
    if to_date is None:
        to_date = datetime.today().strftime("%Y-%m-%d")

    from_year = int(from_date[:4])
    to_year = int(to_date[:4])

    if from_year >= to_year:
        return 1.0

    cpi = get_cpi_data()
    from_cpi = _cpi_for_year(cpi, from_year)
    to_cpi = _cpi_for_year(cpi, to_year)

    if from_cpi and to_cpi and from_cpi > 0:
        return round(to_cpi / from_cpi, 6)

    years = to_year - from_year
    return round(1.03**years, 6)


def get_inflation_summary(reference_years: list[int], to_date: str | None = None) -> dict[int, float]:
    """Returns cumulative inflation % from each reference year to to_date."""
    if to_date is None:
        to_date = datetime.today().strftime("%Y-%m-%d")
    return {
        yr: round((get_inflation_multiplier(f"{yr}-01-01", to_date) - 1) * 100, 2)
        for yr in reference_years
    }
