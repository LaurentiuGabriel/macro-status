#!/usr/bin/env python3
"""
Fetch the highest-impact ("3-bull" / high-volatility) US macro indicators that
head the Investing.com economic calendar, and emit a single static JSON file.

Investing.com does not offer free bulk historical downloads and blocks scraping,
but its high-impact events ARE the official BLS / BEA / Federal Reserve releases,
which the St. Louis Fed republishes on FRED. We pull the identical series from
FRED (public, no API key needed) so the resulting page can be fully static.

Transforms mirror how each figure is actually *reported* on the calendar:
  - Inflation / Core PCE  -> year-over-year % change
  - Nonfarm Payrolls      -> month-over-month change (thousands of jobs)
  - Retail Sales          -> month-over-month % change
  - Fed funds / GDP / U-rate / Jobless claims -> as published
"""

import csv
import io
import json
import sys
import urllib.request
from datetime import date

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}&cosd={cosd}"

# Fetch a bit of extra history (base period) so YoY/MoM transforms are defined
# from the very start of the 10-year display window.
FETCH_FROM = "2014-06-01"
# Display window: strictly no more than 10 years back from today.
DISPLAY_FROM = date(date.today().year - 10, date.today().month, 1).isoformat()

INDICATORS = [
    {
        "id": "nfp", "fred": "PAYEMS", "transform": "diff",
        "name": "Nonfarm Payrolls",
        "blurb": "Net new jobs added outside farming, government-adjacent. The single most market-moving US release.",
        "unit": "K jobs", "decimals": 0, "freq": "Monthly",
        "source": "U.S. Bureau of Labor Statistics", "fred_label": "PAYEMS",
        "good": "up",
    },
    {
        "id": "cpi", "fred": "CPIAUCSL", "transform": "yoy",
        "name": "Inflation Rate (CPI, YoY)",
        "blurb": "Consumer Price Index, year-over-year. Drives rate-cut/hike expectations more than any other print.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "U.S. Bureau of Labor Statistics", "fred_label": "CPIAUCSL",
        "good": "down",
    },
    {
        "id": "fedfunds", "fred": "DFEDTARU", "transform": "monthly_last",
        "name": "Fed Funds Target Rate",
        "blurb": "Upper bound of the FOMC's target range. The Fed Interest Rate Decision is the calendar's top-tier event.",
        "unit": "%", "decimals": 2, "freq": "Per FOMC meeting",
        "source": "Federal Reserve (FOMC)", "fred_label": "DFEDTARU",
        "good": "neutral",
    },
    {
        "id": "gdp", "fred": "A191RL1Q225SBEA", "transform": "asis",
        "name": "GDP Growth Rate (QoQ, annualized)",
        "blurb": "Real GDP, quarterly change at an annual rate. The broadest gauge of the economy's direction.",
        "unit": "%", "decimals": 1, "freq": "Quarterly",
        "source": "U.S. Bureau of Economic Analysis", "fred_label": "A191RL1Q225SBEA",
        "good": "up",
    },
    {
        "id": "unrate", "fred": "UNRATE", "transform": "asis",
        "name": "Unemployment Rate",
        "blurb": "Share of the labor force without a job and looking. Released alongside Nonfarm Payrolls.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "U.S. Bureau of Labor Statistics", "fred_label": "UNRATE",
        "good": "down",
    },
    {
        "id": "corepce", "fred": "PCEPILFE", "transform": "yoy",
        "name": "Core PCE Price Index (YoY)",
        "blurb": "Personal consumption inflation ex-food & energy — the Fed's preferred inflation gauge and 2% target.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "U.S. Bureau of Economic Analysis", "fred_label": "PCEPILFE",
        "good": "down",
    },
    {
        "id": "retail", "fred": "RSAFS", "transform": "mom_pct",
        "name": "Retail Sales (MoM)",
        "blurb": "Month-over-month change in retail & food-services sales. A real-time read on consumer demand.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "U.S. Census Bureau", "fred_label": "RSAFS",
        "good": "up",
    },
    {
        "id": "claims", "fred": "ICSA", "transform": "to_thousands",
        "name": "Initial Jobless Claims",
        "blurb": "New unemployment-benefit filings each week. The highest-frequency labor-market signal on the calendar.",
        "unit": "K", "decimals": 0, "freq": "Weekly",
        "source": "U.S. Department of Labor", "fred_label": "ICSA",
        "good": "down",
    },
]


def fetch_series(fred_id):
    url = FRED_CSV.format(id=fred_id, cosd=FETCH_FROM)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    header = rows[0]
    out = []
    for r in rows[1:]:
        if len(r) < 2:
            continue
        d, v = r[0].strip(), r[1].strip()
        if v in ("", "."):
            out.append((d, None))
        else:
            out.append((d, float(v)))
    return out


def transform(series, kind):
    """series: list[(date_str, value|None)] -> list[(date_str, value)]"""
    out = []
    if kind == "asis" or kind == "monthly_last":
        pts = [(d, v) for d, v in series if v is not None]
        if kind == "monthly_last":
            # collapse daily -> last observation of each calendar month
            by_month = {}
            for d, v in pts:
                by_month[d[:7]] = (d, v)
            pts = [by_month[k] for k in sorted(by_month)]
        out = pts
    elif kind == "to_thousands":
        out = [(d, v / 1000.0) for d, v in series if v is not None]
    elif kind == "diff":
        prev = None
        for d, v in series:
            if v is None:
                continue
            if prev is not None:
                out.append((d, round(v - prev, 1)))
            prev = v
    elif kind == "mom_pct":
        prev = None
        for d, v in series:
            if v is None:
                continue
            if prev not in (None, 0):
                out.append((d, (v / prev - 1.0) * 100.0))
            prev = v
    elif kind == "yoy":
        vals = [(d, v) for d, v in series if v is not None]
        idx = {d: v for d, v in vals}
        # month-keyed lookup 12 months back
        month_vals = {d[:7]: v for d, v in vals}
        for d, v in vals:
            y, m = int(d[:4]), int(d[5:7])
            key = f"{y-1:04d}-{m:02d}"
            base = month_vals.get(key)
            if base:
                out.append((d, (v / base - 1.0) * 100.0))
    return out


def main():
    dataset = {
        "generated": date.today().isoformat(),
        "display_from": DISPLAY_FROM,
        "source_note": "Data: Federal Reserve Economic Data (FRED), St. Louis Fed. "
                       "Series mirror the high-impact US releases that top the "
                       "Investing.com economic calendar.",
        "indicators": [],
    }
    for ind in INDICATORS:
        sys.stderr.write(f"fetching {ind['fred']} ({ind['name']}) ... ")
        try:
            raw = fetch_series(ind["fred"])
        except Exception as e:
            sys.stderr.write(f"FAILED: {e}\n")
            raise
        pts = transform(raw, ind["transform"])
        pts = [(d, round(v, ind["decimals"] + 2)) for d, v in pts if d >= DISPLAY_FROM]
        if not pts:
            sys.stderr.write("no points!\n")
            continue
        latest_d, latest_v = pts[-1]
        prev_v = pts[-2][1] if len(pts) > 1 else None
        earliest_d = pts[0][0]
        dataset["indicators"].append({
            "id": ind["id"], "name": ind["name"], "blurb": ind["blurb"],
            "unit": ind["unit"], "decimals": ind["decimals"], "freq": ind["freq"],
            "source": ind["source"], "fred_label": ind["fred_label"], "good": ind["good"],
            "latest": {"date": latest_d, "value": latest_v},
            "prev": prev_v,
            "range": {"from": earliest_d, "to": latest_d},
            "points": [{"d": d, "v": v} for d, v in pts],
        })
        sys.stderr.write(f"{len(pts)} pts, from {earliest_d} to {latest_d}\n")

    out_path = __file__.rsplit("scripts", 1)[0] + "data/macro-data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, separators=(",", ":"))
    sys.stderr.write(f"\nwrote {out_path} with {len(dataset['indicators'])} indicators\n")


if __name__ == "__main__":
    main()
