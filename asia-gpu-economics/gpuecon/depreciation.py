"""Fit an exponential depreciation curve, V(t) = V0 * exp(-k t), to observed H100 prices.

Different kinds of price tell different stories, so each is fitted on its own:
  dealer asks      what sellers hope to get
  realized sales   what buyers actually paid
  residual forecast  an appraiser's forward view
"""
import math
from datetime import date

from .assumptions import H100_NEW_DATE, H100_NEW_PRICE

GROUPS = {
    "dealer asks": {"ask", "dealer ask", "indicative"},
    "realized sales": {"realized"},
    "residual forecast": {"forecast"},
}


def age_years(d: date, launch: date = date.fromisoformat(H100_NEW_DATE)) -> float:
    return (d - launch).days / 365.25


def fit_rate(points, v0=H100_NEW_PRICE):
    """Least-squares k for ln(V/V0) = -k t, with the curve pinned at V0 when new."""
    num = sum(t * math.log(v / v0) for t, v in points)
    den = sum(t * t for t, _ in points)
    return -num / den


def half_life(k: float) -> float:
    return math.log(2) / k


def value_fraction(months: float, half_life_years: float) -> float:
    """Share of value left after `months`, for a given half-life."""
    return 0.5 ** (months / 12 / half_life_years)


def h100_points(hardware_rows):
    """Per-GPU H100 observations by group. Whole-node prices and the 2024 scarcity peak are left out."""
    out = {g: [] for g in GROUPS}
    for r in hardware_rows:
        if r["gpu"] != "H100 SXM" or r["unit"] != "per GPU" or r["condition"] == "new":
            continue
        for g, types in GROUPS.items():
            if r["price_type"] in types:
                out[g].append((age_years(r["date"]), r["usd_per_gpu"]))
    return out


def fit_groups(hardware_rows):
    """Half-life in years for each group, sorted fastest first."""
    fits = {g: half_life(fit_rate(pts)) for g, pts in h100_points(hardware_rows).items() if pts}
    return dict(sorted(fits.items(), key=lambda kv: kv[1]))
