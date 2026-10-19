"""Load the CSVs in data/ and compute the market statistics the model uses."""
import csv
import statistics
from datetime import date
from pathlib import Path

from .assumptions import ASIA

DATA = Path(__file__).resolve().parents[1] / "data"


def _read(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rental_prices():
    rows = _read("rental_prices.csv")
    for r in rows:
        r["usd_per_gpu_hr"] = float(r["usd_per_gpu_hr"])
    return rows


def hardware_prices():
    rows = _read("hardware_prices.csv")
    for r in rows:
        r["usd_per_gpu"] = float(r["usd_per_gpu"])
        r["date"] = date.fromisoformat(r["date"])
    return rows


def electricity_prices():
    rows = _read("electricity_prices.csv")
    for r in rows:
        r["usd_per_kwh"] = float(r["usd_per_kwh"])
    return {r["country"]: r for r in rows}


def h100_on_demand(rows, provider_types, asia=True):
    return [r for r in rows
            if r["gpu"] == "H100 SXM" and r["contract"] == "on-demand"
            and r["provider_type"] in provider_types
            and ((r["country"] in ASIA) if asia else True)]


def market_summary(rows):
    """Headline price statistics for H100 SXM on-demand, USD per GPU-hour."""
    asia_hyper = h100_on_demand(rows, {"hyperscaler"})
    asia_other = h100_on_demand(rows, {"marketplace", "neocloud", "asia-cloud"})
    us_hyper = [r for r in h100_on_demand(rows, {"hyperscaler"}, asia=False) if r["country"] == "US"]
    index = sorted((r for r in rows if r["provider_type"] == "index"), key=lambda r: r["date"])

    # Same provider, same instance: Asian region price / US East price
    us = {r["provider"]: r["usd_per_gpu_hr"] for r in us_hyper}
    premium = {f'{r["provider"]} {r["country"]}': round(r["usd_per_gpu_hr"] / us[r["provider"]], 2)
               for r in asia_hyper if r["provider"] in us}

    hyper_median = statistics.median(r["usd_per_gpu_hr"] for r in asia_hyper)
    other_median = statistics.median(r["usd_per_gpu_hr"] for r in asia_other)
    return {
        "asia_hyperscaler_median": round(hyper_median, 2),
        "asia_hyperscaler_range": [min(r["usd_per_gpu_hr"] for r in asia_hyper), max(r["usd_per_gpu_hr"] for r in asia_hyper)],
        "asia_non_hyperscaler_median": round(other_median, 2),
        "asia_non_hyperscaler_n": len(asia_other),
        "hyperscaler_to_non_hyperscaler": round(hyper_median / other_median, 1),
        "asia_vs_us_same_instance": premium,
        "silicon_data_latest": index[-1]["usd_per_gpu_hr"] if index else None,
        "n_quotes": len(rows),
    }
