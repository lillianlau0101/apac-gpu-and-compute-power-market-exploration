"""What one GPU-hour costs to produce, and where the money goes."""
from dataclasses import replace

from .assumptions import HOURS_PER_YEAR, Cluster


def capital_recovery_factor(rate: float, years: float) -> float:
    """Annual payment per dollar of capex to repay it with interest over `years`."""
    return rate / (1 - (1 + rate) ** -years)


def power_kw(c: Cluster, utilization: float) -> float:
    """Average facility power per GPU: idle floor plus load, times PUE."""
    load = c.idle_power_frac + (1 - c.idle_power_frac) * utilization
    return c.kw_per_gpu * load * c.pue


def annual_opex_per_gpu(c: Cluster, utilization: float) -> dict:
    return {
        "electricity": power_kw(c, utilization) * HOURS_PER_YEAR * c.electricity_usd_per_kwh,
        "colocation": c.kw_per_gpu * c.colo_usd_per_kw_month * 12,
        "operations": c.ops_usd_per_gpu_hr * HOURS_PER_YEAR,
    }


def cost_per_billed_hour(c: Cluster, utilization: float, cost_of_capital: float) -> dict:
    """Full cost per billed GPU-hour, broken down. Capex is annualised over the useful life."""
    annual = {"hardware & infra": c.capex_per_gpu * capital_recovery_factor(cost_of_capital, c.useful_life_years)}
    annual.update(annual_opex_per_gpu(c, utilization))
    billed_hours = HOURS_PER_YEAR * utilization
    parts = {k: v / billed_hours for k, v in annual.items()}
    total = sum(parts.values())
    return {"total": total, "parts": parts, "electricity_share": parts["electricity"] / total}


def electricity_share_by_market(c: Cluster, utilization: float, cost_of_capital: float, tariffs: dict) -> dict:
    """Electricity as a share of total cost per billed hour, for each market's business tariff."""
    return {country: cost_per_billed_hour(replace(c, electricity_usd_per_kwh=t["usd_per_kwh"]),
                                          utilization, cost_of_capital)["electricity_share"]
            for country, t in tariffs.items()}


def cost_per_useful_hour(cost_billed: float, goodput: float) -> float:
    """If only `goodput` of paid hours do useful work, each useful hour costs this much."""
    return cost_billed / goodput
