"""Fetch live GPU rental prices from public sources and rebuild data/rental_prices.csv.

Sources (no login or API key needed):
  - Azure Retail Prices API      https://prices.azure.com/api/retail/prices
  - AWS public EC2 price files    (the JSON behind aws.amazon.com/ec2/pricing/on-demand)
  - Vast.ai marketplace offers    https://console.vast.ai/api/v0/bundles/
Hand-collected quotes (indices, neoclouds, Japanese clouds) live in data/manual_rental_prices.csv
and are appended unchanged.

Usage:  python scripts/fetch_prices.py            # fetch live, then rebuild the CSV
        python scripts/fetch_prices.py --offline  # rebuild from the saved snapshots in data/raw/
"""
import csv
import gzip
import json
import statistics
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "rental_prices.csv"
MANUAL = ROOT / "data" / "manual_rental_prices.csv"
UA = {"User-Agent": "Mozilla/5.0 (asia-gpu-economics research script)"}

FIELDS = ["date", "provider", "provider_type", "country", "region", "gpu", "contract",
          "gpus_per_unit", "unit_price_usd", "usd_per_gpu_hr", "method", "source_url", "note"]

AZURE_REGIONS = {"japaneast": "JP", "koreacentral": "KR", "southeastasia": "SG", "eastasia": "HK",
                 "centralindia": "IN", "australiaeast": "AU", "eastus": "US"}
# Azure SKU -> (GPU, GPUs per VM)
AZURE_SKUS = {"Standard_ND96isr_H100_v5": ("H100 SXM", 8), "Standard_NC40ads_H100_v5": ("H100 NVL", 1)}

AWS_REGIONS = {"Asia Pacific (Tokyo)": "JP", "Asia Pacific (Seoul)": "KR", "Asia Pacific (Singapore)": "SG",
               "Asia Pacific (Hong Kong)": "HK", "Asia Pacific (Mumbai)": "IN", "Asia Pacific (Jakarta)": "ID",
               "Asia Pacific (Sydney)": "AU", "US East (N. Virginia)": "US"}
AWS_SKUS = {"p5.48xlarge": ("H100 SXM", 8), "p5en.48xlarge": ("H200", 8), "p6-b200.48xlarge": ("B200", 8)}

VAST_GPUS = {"H100 SXM": "H100 SXM", "H100 NVL": "H100 NVL", "H200": "H200", "B200": "B200"}
ASIA = {"JP", "KR", "SG", "HK", "TW", "IN", "ID", "MY", "TH", "VN", "PH", "AU", "CN"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        body = r.read()
    return json.loads(gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body)


def fetch_live():
    RAW.mkdir(parents=True, exist_ok=True)
    for region in AZURE_REGIONS:
        f = (f"serviceName eq 'Virtual Machines' and armRegionName eq '{region}' "
             f"and contains(armSkuName,'H100') and priceType eq 'Consumption'")
        data = get("https://prices.azure.com/api/retail/prices?" + urllib.parse.urlencode({"$filter": f}))
        (RAW / f"azure_{region}.json").write_text(json.dumps(data))
    for name in AWS_REGIONS:
        url = ("https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/"
               f"ec2-ondemand-without-sec-sel/{urllib.parse.quote(name)}/Linux/index.json")
        try:
            data = get(url)
        except Exception as e:  # region without GPU instances, or file moved
            data = {"error": str(e)}
        keep = {k: v for grp in data.get("regions", {}).values() for k, v in grp.items()
                if v.get("Instance Type") in AWS_SKUS}
        (RAW / f"aws_{AWS_REGIONS[name]}.json").write_text(json.dumps(keep))
    for gpu in VAST_GPUS:
        q = {"gpu_name": {"eq": gpu}, "rentable": {"eq": True}, "type": "on-demand", "limit": 1000}
        data = get("https://console.vast.ai/api/v0/bundles/?" + urllib.parse.urlencode({"q": json.dumps(q)}))
        (RAW / f"vast_{gpu.replace(' ', '_')}.json").write_text(json.dumps(data))
    (RAW / "fetched_at.txt").write_text(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"))


def build_rows():
    date = (RAW / "fetched_at.txt").read_text().strip()[:10]
    rows = []
    for region, country in AZURE_REGIONS.items():
        items = json.loads((RAW / f"azure_{region}.json").read_text()).get("Items", [])
        for i in items:
            sku = i["armSkuName"]
            if sku not in AZURE_SKUS or "Windows" in i["productName"] or "Spot" in i["skuName"] or "Low Priority" in i["skuName"]:
                continue
            gpu, n = AZURE_SKUS[sku]
            rows.append([date, "Azure", "hyperscaler", country, region, gpu, "on-demand", n, i["retailPrice"],
                         round(i["retailPrice"] / n, 3), "api", "https://prices.azure.com/api/retail/prices", sku])
    for name, country in AWS_REGIONS.items():
        path = RAW / f"aws_{country}.json"
        if not path.exists():
            continue
        for v in json.loads(path.read_text()).values():
            gpu, n = AWS_SKUS[v["Instance Type"]]
            price = float(v["price"])
            rows.append([date, "AWS", "hyperscaler", country, name, gpu, "on-demand", n, price,
                         round(price / n, 3), "api", "https://aws.amazon.com/ec2/pricing/on-demand/", v["Instance Type"]])
    for gpu, label in VAST_GPUS.items():
        offers = json.loads((RAW / f"vast_{gpu.replace(' ', '_')}.json").read_text()).get("offers", [])
        by_country = {}
        for o in offers:
            c = (o.get("geolocation") or "").split(", ")[-1]
            if c in ASIA or c == "US":
                by_country.setdefault(c, []).append(o["dph_total"] / o["num_gpus"])
        for c, prices in sorted(by_country.items()):
            rows.append([date, "Vast.ai", "marketplace", c, "", label, "on-demand", 1, "",
                         round(statistics.median(prices), 3), "api", "https://vast.ai/",
                         f"median of {len(prices)} live offers"])
    rows.sort(key=lambda r: (r[5], r[3], r[1]))
    return rows


def main():
    if "--offline" not in sys.argv:
        fetch_live()
    rows = build_rows()
    with MANUAL.open(encoding="utf-8") as f:
        manual = list(csv.reader(f))[1:]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(rows + manual)
    print(f"{len(rows)} live rows + {len(manual)} manual rows -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
