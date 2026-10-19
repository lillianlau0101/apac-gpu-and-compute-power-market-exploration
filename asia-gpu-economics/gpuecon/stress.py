"""Stress tests and loan structuring."""
from dataclasses import replace

from .assumptions import Scenario
from .cashflow import loan_balances, min_dscr
from .depreciation import value_fraction


def with_market(s: Scenario, **kw) -> Scenario:
    return replace(s, market=replace(s.market, **kw))


def with_cluster(s: Scenario, **kw) -> Scenario:
    return replace(s, cluster=replace(s.cluster, **kw))


def with_financing(s: Scenario, **kw) -> Scenario:
    return replace(s, financing=replace(s.financing, **kw))


def scenarios(base: Scenario) -> dict:
    m, c = base.market, base.cluster
    return {
        "Base case": base,
        "Flat rents (no decline)": with_market(base, rent_decline_per_year=0.0),
        "Rent -30%": with_market(base, rent_usd_per_gpu_hr=m.rent_usd_per_gpu_hr * 0.7),
        "Utilisation 50%": with_market(base, utilization=0.50),
        "Electricity +50%": with_cluster(base, electricity_usd_per_kwh=c.electricity_usd_per_kwh * 1.5),
        "Rent -30% and util. 50%": with_market(base, rent_usd_per_gpu_hr=m.rent_usd_per_gpu_hr * 0.7, utilization=0.50),
    }


def run(base: Scenario) -> dict:
    return {name: min_dscr(s) for name, s in scenarios(base).items()}


def required_rent(base: Scenario, target: float = 1.0) -> float:
    """Starting rent (USD per GPU-hour) at which the weakest-year DSCR equals `target`."""
    lo, hi = 0.0, 50.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if min_dscr(with_market(base, rent_usd_per_gpu_hr=mid)) < target else (lo, mid)
    return hi


def breakeven_utilization(base: Scenario, target: float = 1.0) -> float:
    """Lowest utilisation that keeps the weakest-year DSCR at `target`."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if min_dscr(with_market(base, utilization=mid)) >= target else (mid, hi)
    return hi


def dscr_grid(base: Scenario, ltvs=(0.5, 0.6, 0.7), terms=(36, 48, 60)) -> dict:
    """Weakest-year DSCR for each (LTV, term) pair."""
    return {(ltv, t): min_dscr(with_financing(base, ltv=ltv, term_months=t)) for ltv in ltvs for t in terms}


def underwater_month(ltv: float, rate: float, term_months: int, half_life_years: float):
    """First month the loan balance exceeds the GPUs' market value, or None if it never does.
    Values are per dollar of hardware bought."""
    for month, bal in enumerate(loan_balances(ltv, rate, term_months)):
        if bal > value_fraction(month, half_life_years) + 1e-12:
            return month
    return None


def max_safe_ltv(rate: float, term_months: int, half_life_years: float) -> float:
    """Highest LTV for which the loan never exceeds collateral value over its life."""
    bal = loan_balances(1.0, rate, term_months)
    return min(value_fraction(m, half_life_years) / b for m, b in enumerate(bal) if b > 0)
