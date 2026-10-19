"""Every number the model needs, in one place.

Each value is tagged:
  [DATA]        taken from a file in data/ (source URL in that file)
  [SPEC]        published hardware specification
  [ASSUMPTION]  my own estimate; replace with operator data (see docs/operator_questions.md)
"""
from dataclasses import dataclass, field

HOURS_PER_YEAR = 8760
HOURS_PER_MONTH = HOURS_PER_YEAR / 12

# Reference new price for an H100 SXM: SemiAnalysis estimate of USD 270k per 8-GPU DGX, Mar 2023. [DATA]
H100_NEW_PRICE = 33_750
H100_NEW_DATE = "2023-03-01"

ASIA = {"JP", "KR", "SG", "HK", "TW", "IN", "ID", "MY", "TH", "VN", "PH", "AU", "CN"}


@dataclass(frozen=True)
class Cluster:
    gpus: int = 1024
    # Used HGX H100 node, realized sale, Aug 2026: USD 195k / 8 GPUs. Buying a cluster today means buying at this price. [DATA]
    hardware_per_gpu: float = 24_375
    infra_pct: float = 0.15            # network fabric, storage, installation, as % of hardware [ASSUMPTION]
    kw_per_gpu: float = 1.275          # DGX H100 max system power 10.2 kW / 8 GPUs [SPEC]
    pue: float = 1.30                  # data-centre overhead for cooling etc. [ASSUMPTION]
    idle_power_frac: float = 0.35      # power drawn by an idle GPU-server, as % of full load [ASSUMPTION]
    colo_usd_per_kw_month: float = 150 # colocation space and power capacity, per IT kW [ASSUMPTION]
    ops_usd_per_gpu_hr: float = 0.10   # staff, support, software, insurance, per installed GPU-hour [ASSUMPTION]
    electricity_usd_per_kwh: float = 0.178  # Japan business tariff, Mar 2026 [DATA]
    useful_life_years: float = 5       # economic life used to annualise capex [ASSUMPTION]

    @property
    def capex_per_gpu(self) -> float:
        return self.hardware_per_gpu * (1 + self.infra_pct)


@dataclass(frozen=True)
class Market:
    rent_usd_per_gpu_hr: float = 2.16  # overwritten at run time by the Asian non-hyperscaler median [DATA]
    utilization: float = 0.70          # share of hours billed [ASSUMPTION]
    rent_decline_per_year: float = 0.15  # Silicon Data H100 index fell ~27% Sep 2024 - Aug 2025; assume about half that ahead [ASSUMPTION]


@dataclass(frozen=True)
class Financing:
    ltv: float = 0.70                  # loan as % of hardware value [ASSUMPTION, typical quoted range]
    rate: float = 0.08                 # annual interest [ASSUMPTION]
    term_months: int = 36              # fully amortising [ASSUMPTION]


@dataclass(frozen=True)
class Scenario:
    cluster: Cluster = field(default_factory=Cluster)
    market: Market = field(default_factory=Market)
    financing: Financing = field(default_factory=Financing)


# Share of paid GPU-hours that turn into useful work. Failures, restarts, slow interconnect
# and poor scheduling all eat into it. [ASSUMPTION: ask operators]
GOODPUT = {"well-built cluster": 0.95, "average cluster": 0.85, "poorly built cluster": 0.70}
