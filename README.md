# Macro Impact Dashboard

A **fully static** web page that plots the macro indicators from the
[Investing.com economic calendar](https://www.investing.com/economic-calendar/),
grouped by theme and tagged with the calendar's volatility rating — **high impact**
(three-bar) and **medium impact** (two-bar) — plus the **bond-market rates** that
price in what comes next, over the last **10 years**.

Open `index.html` in any browser. No build step, no server, no internet, no
dependencies — the data is embedded in the page.

![charts](.)

## The 19 indicators

| Category | Indicator | Impact | Reported as | FRED series | Source |
|---|---|---|---|---|---|
| Labor Market | Nonfarm Payrolls | High | Monthly change (K jobs) | `PAYEMS` | BLS |
| Labor Market | Unemployment Rate | High | % | `UNRATE` | BLS |
| Labor Market | Initial Jobless Claims | High | Weekly (K) | `ICSA` | Dept. of Labor |
| Inflation & Rates | Inflation Rate (CPI) | High | Year-over-year % | `CPIAUCSL` | BLS |
| Inflation & Rates | Core PCE Price Index | High | Year-over-year % | `PCEPILFE` | BEA |
| Inflation & Rates | Fed Funds Target Rate | High | Upper bound % | `DFEDTARU` | Federal Reserve |
| Growth & Consumer | GDP Growth Rate | High | QoQ annualized % | `A191RL1Q225SBEA` | BEA |
| Growth & Consumer | Retail Sales | High | Month-over-month % | `RSAFS` | Census Bureau |
| Housing | Building Permits | Medium | Level, millions SAAR | `PERMIT` | Census Bureau |
| Housing | Housing Starts | Medium | Level, millions SAAR | `HOUST` | Census Bureau |
| Industry & Output | Industrial Production | Medium | Month-over-month % | `INDPRO` | Federal Reserve |
| Industry & Output | Durable Goods Orders | Medium | Month-over-month % | `DGORDER` | Census Bureau |
| Industry & Output | Capacity Utilization | Medium | % of capacity | `TCU` | Federal Reserve |
| Bond Market & Yields | 10-Year Treasury Yield | Market | % (month-end) | `DGS10` | U.S. Treasury |
| Bond Market & Yields | 2-Year Treasury Yield | Market | % (month-end) | `DGS2` | U.S. Treasury |
| Bond Market & Yields | Yield Curve (10Y − 2Y) | Market | pp (month-end) | `T10Y2Y` | Federal Reserve |
| Bond Market & Yields | Credit Spread (Baa − 10Y) | Market | pp (month-end) | `BAA10Y` | Moody's / Fed |
| Productivity & Costs | Nonfarm Productivity | Medium | QoQ annualized % | `OPHNFB` | BLS |
| Productivity & Costs | Unit Labor Costs | Medium | QoQ annualized % | `ULCNFB` | BLS |

### What the bond yields predict

Every other series reports what the economy *did*. Bond yields price what
investors think it *will do*, continuously:

- **2-Year yield** — the market's forecast of Fed policy over the next two years;
  it often moves before the Fed does.
- **10-Year yield** — sets mortgage and corporate borrowing costs; reflects
  long-run growth and inflation expectations.
- **Yield curve (10Y − 2Y)** — the best-known recession indicator. Negative
  ("inverted") means investors expect the Fed to be cutting into a slowdown.
  Every US recession since the 1970s was preceded by an inversion, typically by
  6–18 months — though it has also produced false alarms, and the 2022–24
  inversion (visible in the data here) was the longest on record.
- **Credit spread (Baa − 10Y)** — what medium-grade corporate borrowers pay over
  Treasuries. Widening = investors demanding more for default risk; an early
  read on credit stress and tightening financial conditions.

These are continuously traded market rates rather than scheduled releases, so
they carry a **Market rate** tag instead of a calendar impact rating.

## Where the data comes from

Investing.com does not publish free bulk historical downloads and blocks
scraping. However, its calendar events **are** the official U.S. government /
Federal Reserve releases, which the St. Louis Fed republishes on
[FRED](https://fred.stlouisfed.org/) (public, no API key). This project pulls the
identical series from FRED and applies the same transform each figure is
*reported* with on the calendar (YoY for inflation, MoM change for payrolls /
retail / industrial production, QoQ-annualized for productivity, levels for
housing, as-published for the rest), then trims to the most recent 10 years.

## Features

- One clean line chart per indicator with hover crosshair + tooltip
- Latest value and change-vs-previous, colored by whether the move is favorable
- **Table view** toggle (accessible alternative to the charts)
- **Theme** toggle: Auto / Light / Dark
- Responsive grid; works offline

## Project layout

```
macro-impact-dashboard/
├── index.html              # the page
├── assets/
│   ├── styles.css          # theme-aware styling
│   ├── app.js              # dependency-free SVG chart renderer
│   └── data.js             # embedded dataset (window.MACRO_DATA)
├── data/
│   └── macro-data.json     # same dataset as plain JSON
└── scripts/
    └── fetch_data.py       # regenerates the dataset from FRED
```

## Refreshing the data

Requires Python 3 (standard library only):

```bash
python scripts/fetch_data.py                       # writes data/macro-data.json
python -c "d=open('data/macro-data.json',encoding='utf-8').read(); \
open('assets/data.js','w',encoding='utf-8').write('window.MACRO_DATA = '+d+';')"
```

The display window is always the most recent 10 years (never more), computed at
fetch time.

---
*For information only — not investment advice. The 2020 spikes across most series
are the genuine COVID-19 shock, not data errors.*
