# Macro Impact Dashboard

A **fully static** web page that plots the macro indicators from the
[Investing.com economic calendar](https://www.investing.com/economic-calendar/),
grouped by theme and tagged with the calendar's volatility rating — **high impact**
(three-bar) and **medium impact** (two-bar) — over the last **10 years**.

Open `index.html` in any browser. No build step, no server, no internet, no
dependencies — the data is embedded in the page.

![charts](.)

## The 15 indicators

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
| Productivity & Costs | Nonfarm Productivity | Medium | QoQ annualized % | `OPHNFB` | BLS |
| Productivity & Costs | Unit Labor Costs | Medium | QoQ annualized % | `ULCNFB` | BLS |

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
