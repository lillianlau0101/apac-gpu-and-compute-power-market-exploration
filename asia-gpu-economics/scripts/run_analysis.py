"""Run every analysis in the README: prints the numbers, writes outputs/results.json and the charts.

Usage:  python scripts/run_analysis.py
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gpuecon import cashflow, cluster, data, depreciation, stress  # noqa: E402
from gpuecon.assumptions import ASIA, GOODPUT, H100_NEW_PRICE, Market, Scenario  # noqa: E402

OUT = ROOT / "outputs"

# Chart style: validated categorical slots 1-3, recessive hairline grid, text in ink tokens
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
})
COUNTRY = {"JP": "Tokyo", "KR": "Seoul", "SG": "Singapore", "IN": "India", "ID": "Jakarta", "AU": "Sydney",
           "TH": "Thailand", "US": "US", "GLOBAL": "global", "HK": "Hong Kong"}


def chart_prices(rows, path):
    pts = [r for r in rows if r["gpu"] == "H100 SXM" and r["contract"] == "on-demand"
           and (r["country"] in ASIA or r["country"] in {"US", "GLOBAL"})]
    groups = {"hyperscaler": ("Hyperscaler", SERIES[0]),
              "other": ("Neocloud, marketplace, Asian cloud", SERIES[1]),
              "index": ("Silicon Data H100 index", SERIES[2])}
    latest_index = max((r for r in pts if r["provider_type"] == "index"), key=lambda r: r["date"])
    pts = [r for r in pts if r["provider_type"] != "index"] + [latest_index]
    pts.sort(key=lambda r: r["usd_per_gpu_hr"])
    fig, ax = plt.subplots(figsize=(8, 0.32 * len(pts) + 1.4))
    for i, r in enumerate(pts):
        g = r["provider_type"] if r["provider_type"] in ("hyperscaler", "index") else "other"
        ax.plot([0, r["usd_per_gpu_hr"]], [i, i], color=GRID, lw=1, zorder=1)
        ax.scatter(r["usd_per_gpu_hr"], i, s=46, color=groups[g][1], edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.text(r["usd_per_gpu_hr"] + 0.25, i, f'${r["usd_per_gpu_hr"]:.2f}', va="center", fontsize=8.5, color=INK_2)
    labels = [f'{r["provider"]} · {COUNTRY.get(r["country"], r["country"])}'
              + (" (US ref.)" if r["country"] == "US" else "")
              + (f' ({r["date"][:7]})' if r["date"][:7] != pts[-1]["date"][:7] and r["provider_type"] != "hyperscaler" else "")
              for r in pts]
    ax.set_yticks(range(len(pts)), labels, fontsize=8.5)
    ax.set_xlim(0, max(r["usd_per_gpu_hr"] for r in pts) * 1.12)
    ax.set_xlabel("USD per GPU-hour, on-demand")
    ax.grid(axis="y", visible=False)
    fig.suptitle("H100 SXM rental prices: Asia vs. global benchmarks", x=0.02, ha="left", fontweight="bold", fontsize=12)
    for g, (name, col) in groups.items():
        ax.scatter([], [], s=46, color=col, label=name)
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def chart_depreciation(hw, fits, path):
    pts = depreciation.h100_points(hw)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ages = [i / 20 for i in range(0, 141)]
    for (g, hl), col in zip(fits.items(), SERIES):
        ax.plot(ages, [100 * depreciation.value_fraction(a * 12, hl) for a in ages], color=col, lw=2,
                label=f"{g}: half-life {hl:.1f} yrs")
        ax.scatter([t for t, _ in pts[g]], [100 * v / H100_NEW_PRICE for _, v in pts[g]], s=46, color=col,
                   edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.set_xlim(0, 7)
    ax.set_ylim(0, 105)
    ax.set_xlabel("Years since H100 launch (Mar 2023)")
    ax.set_ylabel("% of USD 33,750 reference new price")
    ax.set_title("H100 value: three price sources, three depreciation curves")
    ax.legend(frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def chart_stress(results, path):
    names = list(results)[::-1]
    vals = [results[n] for n in names]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.barh(names, vals, height=0.5, color=SERIES[0])
    ax.axvline(1.0, color=INK, lw=1)
    ax.set_ylim(-1.0, len(names) - 0.5)
    ax.text(0.98, -0.75, "DSCR 1.0 = cash flow just covers payments", fontsize=8.5, color=INK_2, va="center", ha="right")
    for i, v in enumerate(vals):
        ax.text(v + (0.03 if v >= 0 else -0.03), i, f"{v:.2f}", va="center", ha="left" if v >= 0 else "right",
                fontsize=9, color=INK)
    ax.set_xlim(min(-0.2, min(vals) - 0.25), max(1.5, max(vals) + 0.25))
    ax.set_xlabel("Weakest-year debt service coverage ratio (DSCR)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Stress tests: 1,024 H100s, 70% LTV, 8%, 3-year loan")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def chart_collateral(fits, rate, path):
    months = list(range(0, 61))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for (g, hl), col in zip(fits.items(), SERIES):
        ax.plot(months, [100 * depreciation.value_fraction(m, hl) for m in months], color=col, lw=2,
                label=f"GPU value, {g} ({hl:.1f}-yr half-life)")
    for term, style in ((36, "-"), (60, "--")):
        bal = cashflow.loan_balances(0.70, rate, term)
        ax.plot(range(len(bal)), [100 * b for b in bal], color=INK, lw=1.5, ls=style,
                label=f"Loan balance, 70% LTV, {term}-month term")
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 105)
    ax.set_xlabel("Months after purchase")
    ax.set_ylabel("% of hardware purchase price")
    ax.set_title("Is the loan still covered by the GPUs?")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    rows = data.rental_prices()
    hw = data.hardware_prices()
    tariffs = data.electricity_prices()
    market = data.market_summary(rows)

    base = Scenario(market=Market(rent_usd_per_gpu_hr=market["asia_non_hyperscaler_median"]))
    fits = depreciation.fit_groups(hw)
    rate = base.financing.rate

    cost = cluster.cost_per_billed_hour(base.cluster, base.market.utilization, rate)
    shares = cluster.electricity_share_by_market(base.cluster, base.market.utilization, rate, tariffs)
    useful = {q: cluster.cost_per_useful_hour(cost["total"], g) for q, g in GOODPUT.items()}
    stress_results = stress.run(base)
    grid = stress.dscr_grid(base)
    underwater = {g: {t: stress.underwater_month(0.70, rate, t, hl) for t in (36, 48, 60)} for g, hl in fits.items()}
    safe_ltv = {g: {t: stress.max_safe_ltv(rate, t, hl) for t in (36, 48, 60)} for g, hl in fits.items()}

    results = {
        "market": market,
        "depreciation_half_life_years": fits,
        "base_case": {
            "rent_usd_per_gpu_hr": base.market.rent_usd_per_gpu_hr,
            "utilization": base.market.utilization,
            "rent_decline_per_year": base.market.rent_decline_per_year,
            "dscr_by_year": cashflow.dscr_by_year(base),
            "min_dscr": cashflow.min_dscr(base),
            "required_rent_dscr_1.0": stress.required_rent(base, 1.0),
            "required_rent_dscr_1.25": stress.required_rent(base, 1.25),
            "breakeven_utilization": stress.breakeven_utilization(base),
        },
        "cost_per_billed_hour": cost,
        "electricity_share_by_market": shares,
        "cost_per_useful_hour": useful,
        "stress_min_dscr": stress_results,
        "dscr_grid_ltv_term": {f"{int(l * 100)}% LTV, {t} mo": v for (l, t), v in grid.items()},
        "underwater_month_70ltv": underwater,
        "max_safe_ltv": safe_ltv,
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=float))

    chart_prices(rows, OUT / "h100_prices.png")
    chart_depreciation(hw, fits, OUT / "depreciation.png")
    chart_stress(stress_results, OUT / "stress_dscr.png")
    chart_collateral(fits, rate, OUT / "collateral.png")

    b = results["base_case"]
    print(f"""
MARKET (H100 SXM on-demand, USD/GPU-hr, {market['n_quotes']} quotes)
  Asian hyperscaler median        {market['asia_hyperscaler_median']:.2f}  (range {market['asia_hyperscaler_range'][0]:.2f}-{market['asia_hyperscaler_range'][1]:.2f})
  Asian non-hyperscaler median    {market['asia_non_hyperscaler_median']:.2f}  (n={market['asia_non_hyperscaler_n']})
  Hyperscaler / non-hyperscaler   {market['hyperscaler_to_non_hyperscaler']}x
  Asia vs US, same instance       {market['asia_vs_us_same_instance']}
  Silicon Data index (latest)     {market['silicon_data_latest']}

DEPRECIATION (half-life, years)   {', '.join(f'{g} {v:.1f}' for g, v in fits.items())}

BASE CASE  rent {b['rent_usd_per_gpu_hr']:.2f}, utilisation {b['utilization']:.0%}, rents -{b['rent_decline_per_year']:.0%}/yr, 70% LTV, 8%, 36 mo
  DSCR by loan year               {', '.join(f'{x:.2f}' for x in b['dscr_by_year'])}
  Rent needed for DSCR 1.0 / 1.25 {b['required_rent_dscr_1.0']:.2f} / {b['required_rent_dscr_1.25']:.2f}
  Break-even utilisation          {b['breakeven_utilization']:.0%}

COST PER BILLED GPU-HOUR          {cost['total']:.2f}  ({', '.join(f'{k} {v:.2f}' for k, v in cost['parts'].items())})
  Electricity share by market     {', '.join(f'{k} {v:.0%}' for k, v in shares.items())}
  Cost per useful hour            {', '.join(f'{k} {v:.2f}' for k, v in useful.items())}

STRESS (weakest-year DSCR)        {', '.join(f'{k} {v:.2f}' for k, v in stress_results.items())}
DSCR GRID                         {', '.join(f'{k}: {v:.2f}' for k, v in results['dscr_grid_ltv_term'].items())}
UNDERWATER MONTH @70% LTV         {underwater}
MAX SAFE LTV                      {json.dumps({g: {t: round(v, 2) for t, v in d.items()} for g, d in safe_ltv.items()})}

Charts and results.json written to outputs/""")


if __name__ == "__main__":
    main()
