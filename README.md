# Macro Impact Dashboard

A **fully static** web page that plots the macro indicators the
[Investing.com economic calendar](https://www.investing.com/economic-calendar/)
flags as **high impact** — its three-bar / high-volatility ("bull") rating — over
the last **10 years**.

Open `index.html` in any browser. No build step, no server, no internet, no
dependencies — the data is embedded in the page.

![charts](.)

## The eight high-impact indicators

| Indicator | Reported as | FRED series | Source |
|---|---|---|---|
| Nonfarm Payrolls | Monthly change (K jobs) | `PAYEMS` | BLS |
| Inflation Rate (CPI) | Year-over-year % | `CPIAUCSL` | BLS |
| Fed Funds Target Rate | Upper bound % | `DFEDTARU` | Federal Reserve |
| GDP Growth Rate | QoQ annualized % | `A191RL1Q225SBEA` | BEA |
| Unemployment Rate | % | `UNRATE` | BLS |
| Core PCE Price Index | Year-over-year % | `PCEPILFE` | BEA |
| Retail Sales | Month-over-month % | `RSAFS` | Census Bureau |
| Initial Jobless Claims | Weekly (K) | `ICSA` | Dept. of Labor |

## Where the data comes from

Investing.com does not publish free bulk historical downloads and blocks
scraping. However, its high-impact events **are** the official U.S. government /
Federal Reserve releases, which the St. Louis Fed republishes on
[FRED](https://fred.stlouisfed.org/) (public, no API key). This project pulls the
identical series from FRED and applies the same transform each figure is
*reported* with on the calendar (YoY for inflation, MoM change for payrolls and
retail sales, as-published for the rest), then trims to the most recent 10 years.

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
