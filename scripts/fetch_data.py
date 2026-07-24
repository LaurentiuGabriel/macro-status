#!/usr/bin/env python3
"""
Fetch the high-impact and notable US macro indicators that head the
Investing.com economic calendar, and emit a single static JSON file.

Investing.com does not offer free bulk historical downloads and blocks scraping,
but its calendar events ARE the official BLS / BEA / Census / Federal Reserve
releases, which the St. Louis Fed republishes on FRED. We pull the identical
series from FRED (public, no API key needed) so the page can be fully static.

Each indicator carries a calendar-style impact tier ("high" = 3-bar /
high-volatility, "medium" = 2-bar) and a category, and is transformed to mirror
how the figure is actually *reported* on the calendar:
  - Inflation / Core PCE            -> year-over-year % change
  - Nonfarm Payrolls                -> month-over-month change (thousands)
  - Retail Sales / IP / Durables    -> month-over-month % change
  - Productivity / Unit Labor Costs -> quarter-over-quarter annualized % change
  - Building Permits / Housing Starts -> level in millions (SAAR)
  - Fed funds / GDP / U-rate / claims / capacity util -> as published
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
FETCH_FROM = "2014-01-01"
# Display window: strictly no more than 10 years back from today.
DISPLAY_FROM = date(date.today().year - 10, date.today().month, 1).isoformat()

# Category order here == display order on the page.
INDICATORS = [
    # ---- Labor Market ------------------------------------------------------
    {
        "id": "nfp", "fred": "PAYEMS", "transform": "diff",
        "cat": "Labor Market", "impact": "high",
        "name": "Nonfarm Payrolls",
        "blurb": "Net new jobs added outside farming, government-adjacent. The single most market-moving US release.",
        "unit": "K jobs", "decimals": 0, "freq": "Monthly",
        "source": "U.S. Bureau of Labor Statistics", "good": "up",
    },
    {
        "id": "unrate", "fred": "UNRATE", "transform": "asis",
        "cat": "Labor Market", "impact": "high",
        "name": "Unemployment Rate",
        "blurb": "Share of the labor force without a job and looking. Released alongside Nonfarm Payrolls.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "U.S. Bureau of Labor Statistics", "good": "down",
    },
    {
        "id": "claims", "fred": "ICSA", "transform": "to_thousands",
        "cat": "Labor Market", "impact": "high",
        "name": "Initial Jobless Claims",
        "blurb": "New unemployment-benefit filings each week. The highest-frequency labor-market signal on the calendar.",
        "unit": "K", "decimals": 0, "freq": "Weekly",
        "source": "U.S. Department of Labor", "good": "down",
    },
    # ---- Inflation & Rates -------------------------------------------------
    {
        "id": "cpi", "fred": "CPIAUCSL", "transform": "yoy",
        "cat": "Inflation & Rates", "impact": "high",
        "name": "Inflation Rate (CPI, YoY)",
        "blurb": "Consumer Price Index, year-over-year. Drives rate-cut/hike expectations more than any other print.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "U.S. Bureau of Labor Statistics", "good": "down",
    },
    {
        "id": "corepce", "fred": "PCEPILFE", "transform": "yoy",
        "cat": "Inflation & Rates", "impact": "high",
        "name": "Core PCE Price Index (YoY)",
        "blurb": "Personal consumption inflation ex-food & energy — the Fed's preferred inflation gauge and 2% target.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "U.S. Bureau of Economic Analysis", "good": "down",
    },
    {
        "id": "fedfunds", "fred": "DFEDTARU", "transform": "monthly_last",
        "cat": "Inflation & Rates", "impact": "high",
        "name": "Fed Funds Target Rate",
        "blurb": "Upper bound of the FOMC's target range. The Fed Interest Rate Decision is the calendar's top-tier event.",
        "unit": "%", "decimals": 2, "freq": "Per FOMC meeting",
        "source": "Federal Reserve (FOMC)", "good": "neutral",
    },
    # ---- Growth & Consumer -------------------------------------------------
    {
        "id": "gdp", "fred": "A191RL1Q225SBEA", "transform": "asis",
        "cat": "Growth & Consumer", "impact": "high",
        "name": "GDP Growth Rate (QoQ, annualized)",
        "blurb": "Real GDP, quarterly change at an annual rate. The broadest gauge of the economy's direction.",
        "unit": "%", "decimals": 1, "freq": "Quarterly",
        "source": "U.S. Bureau of Economic Analysis", "good": "up",
    },
    {
        "id": "retail", "fred": "RSAFS", "transform": "mom_pct",
        "cat": "Growth & Consumer", "impact": "high",
        "name": "Retail Sales (MoM)",
        "blurb": "Month-over-month change in retail & food-services sales. A real-time read on consumer demand.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "U.S. Census Bureau", "good": "up",
    },
    # ---- Housing -----------------------------------------------------------
    {
        "id": "permits", "fred": "PERMIT", "transform": "to_millions",
        "cat": "Housing", "impact": "medium",
        "name": "Building Permits",
        "blurb": "Permits issued to build new homes (annualized). A forward-looking read on housing supply and construction.",
        "unit": "M", "decimals": 2, "freq": "Monthly",
        "source": "U.S. Census Bureau", "good": "up",
    },
    {
        "id": "starts", "fred": "HOUST", "transform": "to_millions",
        "cat": "Housing", "impact": "medium",
        "name": "Housing Starts",
        "blurb": "Ground broken on new homes (annualized). A core gauge of the housing cycle and construction demand.",
        "unit": "M", "decimals": 2, "freq": "Monthly",
        "source": "U.S. Census Bureau", "good": "up",
    },
    # ---- Industry & Output -------------------------------------------------
    {
        "id": "indpro", "fred": "INDPRO", "transform": "mom_pct",
        "cat": "Industry & Output", "impact": "medium",
        "name": "Industrial Production (MoM)",
        "blurb": "Month-over-month change in factory, mine and utility output — the pulse of the industrial economy.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "Federal Reserve", "good": "up",
    },
    {
        "id": "durables", "fred": "DGORDER", "transform": "mom_pct",
        "cat": "Industry & Output", "impact": "medium",
        "name": "Durable Goods Orders (MoM)",
        "blurb": "Month-over-month change in new orders for long-lasting goods; a leading signal for business investment.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "U.S. Census Bureau", "good": "up",
    },
    {
        "id": "caputil", "fred": "TCU", "transform": "asis",
        "cat": "Industry & Output", "impact": "medium",
        "name": "Capacity Utilization",
        "blurb": "Share of industrial capacity actually in use. Tightening capacity can foreshadow inflation pressure.",
        "unit": "%", "decimals": 1, "freq": "Monthly",
        "source": "Federal Reserve", "good": "up",
    },
    # ---- Productivity & Costs ---------------------------------------------
    {
        "id": "productivity", "fred": "OPHNFB", "transform": "qoq_annualized",
        "cat": "Productivity & Costs", "impact": "medium",
        "name": "Nonfarm Productivity (QoQ, annualized)",
        "blurb": "Nonfarm business output per hour worked. The long-run driver of growth and non-inflationary wage gains.",
        "unit": "%", "decimals": 1, "freq": "Quarterly",
        "source": "U.S. Bureau of Labor Statistics", "good": "up",
    },
    {
        "id": "ulc", "fred": "ULCNFB", "transform": "qoq_annualized",
        "cat": "Productivity & Costs", "impact": "medium",
        "name": "Unit Labor Costs (QoQ, annualized)",
        "blurb": "Labor cost per unit of output. Rising unit labor costs feed into inflation and squeeze profit margins.",
        "unit": "%", "decimals": 1, "freq": "Quarterly",
        "source": "U.S. Bureau of Labor Statistics", "good": "neutral",
    },
]


def fetch_series(fred_id):
    url = FRED_CSV.format(id=fred_id, cosd=FETCH_FROM)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    out = []
    for r in rows[1:]:
        if len(r) < 2:
            continue
        d, v = r[0].strip(), r[1].strip()
        out.append((d, None if v in ("", ".") else float(v)))
    return out


def transform(series, kind):
    """series: list[(date_str, value|None)] -> list[(date_str, value)]"""
    out = []
    if kind in ("asis", "monthly_last"):
        pts = [(d, v) for d, v in series if v is not None]
        if kind == "monthly_last":
            by_month = {}
            for d, v in pts:
                by_month[d[:7]] = (d, v)   # collapse daily -> last obs per month
            pts = [by_month[k] for k in sorted(by_month)]
        out = pts
    elif kind == "to_thousands":
        out = [(d, v / 1000.0) for d, v in series if v is not None]
    elif kind == "to_millions":
        out = [(d, v / 1000.0) for d, v in series if v is not None]  # thousands -> millions
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
    elif kind == "qoq_annualized":
        prev = None
        for d, v in series:
            if v is None:
                continue
            if prev not in (None, 0):
                out.append((d, ((v / prev) ** 4 - 1.0) * 100.0))
            prev = v
    elif kind == "yoy":
        vals = [(d, v) for d, v in series if v is not None]
        month_vals = {d[:7]: v for d, v in vals}
        for d, v in vals:
            y, m = int(d[:4]), int(d[5:7])
            base = month_vals.get(f"{y-1:04d}-{m:02d}")
            if base:
                out.append((d, (v / base - 1.0) * 100.0))
    return out


def main():
    dataset = {
        "generated": date.today().isoformat(),
        "display_from": DISPLAY_FROM,
        "source_note": "Data: Federal Reserve Economic Data (FRED), St. Louis Fed. "
                       "Series mirror the US releases on the Investing.com economic calendar.",
        "indicators": [],
    }
    failures = []
    for ind in INDICATORS:
        sys.stderr.write(f"fetching {ind['fred']:16s} ({ind['name'][:34]:34s}) ... ")
        try:
            raw = fetch_series(ind["fred"])
        except Exception as e:
            sys.stderr.write(f"FAILED: {e}\n")
            failures.append(ind["fred"])
            continue
        pts = transform(raw, ind["transform"])
        pts = [(d, round(v, ind["decimals"] + 2)) for d, v in pts if d >= DISPLAY_FROM]
        if not pts:
            sys.stderr.write("no points!\n")
            failures.append(ind["fred"])
            continue
        latest_d, latest_v = pts[-1]
        dataset["indicators"].append({
            "id": ind["id"], "name": ind["name"], "blurb": ind["blurb"],
            "cat": ind["cat"], "impact": ind["impact"],
            "unit": ind["unit"], "decimals": ind["decimals"], "freq": ind["freq"],
            "source": ind["source"], "fred_label": ind["fred"], "good": ind["good"],
            "latest": {"date": latest_d, "value": latest_v},
            "prev": pts[-2][1] if len(pts) > 1 else None,
            "range": {"from": pts[0][0], "to": latest_d},
            "points": [{"d": d, "v": v} for d, v in pts],
        })
        sys.stderr.write(f"{len(pts):4d} pts, {pts[0][0]} -> {latest_d}\n")

    out_path = __file__.rsplit("scripts", 1)[0] + "data/macro-data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, separators=(",", ":"))
    sys.stderr.write(f"\nwrote {out_path} with {len(dataset['indicators'])} indicators\n")
    if failures:
        sys.stderr.write(f"WARNING: skipped {len(failures)} series: {failures}\n")


if __name__ == "__main__":
    main()
