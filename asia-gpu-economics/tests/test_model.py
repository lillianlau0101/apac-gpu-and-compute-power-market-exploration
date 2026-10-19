import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gpuecon import cashflow, cluster, data, depreciation, stress  # noqa: E402
from gpuecon.assumptions import HOURS_PER_YEAR, Cluster, Market, Scenario  # noqa: E402


def test_loan_fully_amortises():
    bal = cashflow.loan_balances(1_000_000, 0.08, 36)
    assert bal[0] == 1_000_000
    assert bal[-1] == pytest.approx(0, abs=1e-6)
    assert all(a > b for a, b in zip(bal, bal[1:]))


def test_monthly_payment_matches_annuity_formula():
    # 100k at 12%/yr over 12 months: textbook payment 8,884.88
    assert cashflow.monthly_payment(100_000, 0.12, 12) == pytest.approx(8884.88, abs=0.01)


def test_depreciation_fit_recovers_known_half_life():
    v0 = 10_000
    points = [(t, v0 * 0.5 ** (t / 3.0)) for t in (1, 2, 4)]
    assert depreciation.half_life(depreciation.fit_rate(points, v0)) == pytest.approx(3.0)


def test_value_fraction_halves_at_half_life():
    assert depreciation.value_fraction(24, 2.0) == pytest.approx(0.5)


def test_cost_parts_sum_to_total_and_scale_with_utilisation():
    c = Cluster()
    hi, lo = cluster.cost_per_billed_hour(c, 0.9, 0.08), cluster.cost_per_billed_hour(c, 0.5, 0.08)
    assert sum(hi["parts"].values()) == pytest.approx(hi["total"])
    assert lo["total"] > hi["total"]  # fixed costs spread over fewer billed hours


def test_electricity_cost_matches_hand_calculation():
    c = Cluster(electricity_usd_per_kwh=0.10, pue=1.0, idle_power_frac=0.0)
    opex = cluster.annual_opex_per_gpu(c, 1.0)
    assert opex["electricity"] == pytest.approx(c.kw_per_gpu * HOURS_PER_YEAR * 0.10)


def test_dscr_moves_the_right_way():
    base = Scenario(market=Market(rent_usd_per_gpu_hr=3.0))
    assert cashflow.min_dscr(stress.with_market(base, rent_usd_per_gpu_hr=2.0)) < cashflow.min_dscr(base)
    assert cashflow.min_dscr(stress.with_market(base, utilization=0.5)) < cashflow.min_dscr(base)
    assert cashflow.min_dscr(stress.with_financing(base, ltv=0.5)) > cashflow.min_dscr(base)


def test_required_rent_hits_target_dscr():
    base = Scenario()
    rent = stress.required_rent(base, 1.25)
    assert cashflow.min_dscr(stress.with_market(base, rent_usd_per_gpu_hr=rent)) == pytest.approx(1.25, abs=1e-3)


def test_underwater_month_and_safe_ltv_agree():
    hl = 1.0  # very fast depreciation
    safe = stress.max_safe_ltv(0.08, 60, hl)
    assert stress.underwater_month(safe * 0.99, 0.08, 60, hl) is None
    assert stress.underwater_month(min(safe * 1.05, 1.0), 0.08, 60, hl) is not None


def test_data_files_load_and_have_sources():
    rows = data.rental_prices()
    assert rows and all(r["source_url"].startswith("http") for r in rows)
    assert all(r["usd_per_gpu_hr"] > 0 for r in rows)
    assert all(r["source_url"].startswith("http") for r in data.hardware_prices())
    assert all(0 < t["usd_per_kwh"] < 1 for t in data.electricity_prices().values())


def test_market_summary_hyperscalers_cost_more():
    m = data.market_summary(data.rental_prices())
    assert m["asia_hyperscaler_median"] > m["asia_non_hyperscaler_median"]
    assert all(v > 1 for v in m["asia_vs_us_same_instance"].values())
