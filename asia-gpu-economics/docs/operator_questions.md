# Questions for GPU operators · GPU 运营方访谈问题

Each question replaces one assumption in [`gpuecon/assumptions.py`](../gpuecon/assumptions.py). Ask the first block first: those are the assumptions the results are most sensitive to.

每个问题对应 [`gpuecon/assumptions.py`](../gpuecon/assumptions.py) 里的一个假设。先问第一组：结果对这几个假设最敏感。

## 1. Revenue · 收入（most sensitive · 最敏感）

| # | Question | 问题 | Replaces |
|---|---|---|---|
| 1 | What share of your H100 hours are billed over a typical quarter? How does it differ between on-demand and reserved capacity? | 一个季度里，H100 的可用小时中有多少是计费的？按需和预留容量的利用率差多少？ | `Market.utilization` (70%) |
| 2 | How much of your capacity is under contracts of a year or more, and at what discount to your on-demand price? | 有多少容量签了一年以上的合同？相对按需价格折扣多少？ | Base rent; contracted vs spot mix |
| 3 | How have your H100 prices moved over the past 12 months, on-demand and contracted? What do you expect over the next 12? | 过去 12 个月，按需价和合同价分别怎么变的？未来 12 个月预期如何？ | `Market.rent_decline_per_year` (15%) |
| 4 | Do Asian customers pay more than US customers for the same GPU? Why: latency, data residency, local support, currency? | 亚洲客户是否比美国客户为同一张卡付更多钱？原因是延迟、数据本地化、本地支持，还是汇率？ | Asia price premium |

## 2. Cluster quality · 集群质量

| # | Question | 问题 | Replaces |
|---|---|---|---|
| 5 | Of the hours a customer pays for, how many deliver useful work? What eats the rest: hardware failures, restarts, network stalls, scheduling? | 客户付费的小时中，有多少是有效计算？其余被什么消耗：硬件故障、任务重启、网络拥塞、调度？ | `GOODPUT` (70–95%) |
| 6 | What is your annualised GPU failure rate, and how long does a failed node take to return to service? | GPU 年化故障率是多少？一个故障节点平均多久恢复？ | `GOODPUT` |
| 7 | What interconnect do you run (InfiniBand, RoCE, Ethernet), and how much more do customers pay for it? | 用什么互联（InfiniBand、RoCE、以太网）？客户愿意为此多付多少？ | Price by cluster type |

## 3. Costs · 成本

| # | Question | 问题 | Replaces |
|---|---|---|---|
| 8 | What do you pay per kW per month for colocation, and is power included? | 机房托管每 kW 每月多少钱？是否含电费？ | `Cluster.colo_usd_per_kw_month` (USD 150) |
| 9 | What PUE do your sites run at, in tropical vs temperate climates? Liquid or air cooling? | 各机房 PUE 是多少？热带和温带地区差多少？液冷还是风冷？ | `Cluster.pue` (1.30) |
| 10 | Do you buy power at the published business tariff, or under a negotiated contract? At what price? | 电价按公开工商业电价，还是签了协议电价？多少钱？ | `Cluster.electricity_usd_per_kwh` |
| 11 | Network, storage and installation: what do they add on top of the GPU servers? | 网络、存储和安装，在 GPU 服务器之外还要加多少比例？ | `Cluster.infra_pct` (15%) |
| 12 | Staff, support, software licences and insurance: what do they cost per GPU per year? | 人员、客户支持、软件授权和保险，每张卡每年多少钱？ | `Cluster.ops_usd_per_gpu_hr` (USD 0.10) |

## 4. Financing and residual value · 融资与残值

| # | Question | 问题 | Replaces |
|---|---|---|---|
| 13 | What loan-to-value, rate and term do lenders offer on GPU collateral today? Do they require customer contracts as security? | 现在放贷方对 GPU 抵押给多少成数、什么利率和期限？是否要求以客户合同作担保？ | `Financing` (70%, 8%, 36 mo) |
| 14 | What did you get when you last sold or traded in used GPUs, and to whom? | 上一次出售或置换旧 GPU 卖了多少钱？卖给了谁？ | Depreciation curve |
| 15 | Over how many years do you depreciate GPUs in your accounts, and how long do you expect them to stay rentable? | 账面上 GPU 按几年折旧？预计能出租多少年？ | `Cluster.useful_life_years` (5) |
