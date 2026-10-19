"""Monthly cash flow of a debt-financed GPU cluster, and how well it covers the loan."""
from .assumptions import HOURS_PER_MONTH, Scenario
from .cluster import annual_opex_per_gpu


def loan_amount(s: Scenario) -> float:
    return s.financing.ltv * s.cluster.hardware_per_gpu * s.cluster.gpus


def monthly_payment(principal: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 12
    return principal * r / (1 - (1 + r) ** -months)


def loan_balances(principal: float, annual_rate: float, months: int):
    """Outstanding balance at the end of each month, month 0 = drawdown."""
    r, pay, bal = annual_rate / 12, monthly_payment(principal, annual_rate, months), principal
    out = [bal]
    for _ in range(months):
        bal = bal * (1 + r) - pay
        out.append(max(bal, 0.0))
    return out


def monthly_cashflows(s: Scenario):
    """List of dicts for each month of the loan: revenue, opex, CFADS, debt service."""
    c, m, f = s.cluster, s.market, s.financing
    opex = sum(annual_opex_per_gpu(c, m.utilization).values()) * c.gpus / 12
    service = monthly_payment(loan_amount(s), f.rate, f.term_months)
    rows = []
    for month in range(1, f.term_months + 1):
        rent = m.rent_usd_per_gpu_hr * (1 - m.rent_decline_per_year) ** ((month - 1) / 12)
        revenue = c.gpus * rent * HOURS_PER_MONTH * m.utilization
        rows.append({"month": month, "rent": rent, "revenue": revenue, "opex": opex,
                     "cfads": revenue - opex, "debt_service": service})
    return rows


def dscr_by_year(s: Scenario):
    """Debt service coverage ratio for each loan year: cash available for debt service / debt service."""
    rows = monthly_cashflows(s)
    years = []
    for start in range(0, len(rows), 12):
        chunk = rows[start:start + 12]
        years.append(sum(r["cfads"] for r in chunk) / sum(r["debt_service"] for r in chunk))
    return years


def min_dscr(s: Scenario) -> float:
    """The lender's test: the weakest year. With rents falling, that is the last year of the loan."""
    return min(dscr_by_year(s))
