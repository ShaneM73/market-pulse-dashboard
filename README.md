# Market Pulse — S&P 500 / Dow / Nasdaq-100 dashboard

An interactive market dashboard built as a single HTML page with d3. Snapshot data is for the
**October 21, 2026** close.

## What's in it

- Index tiles (S&P 500, Dow, Nasdaq, Russell 2000, VIX, 10-year yield) and a one-line takeaway
- **Heat map** of the S&P 500 (463 constituents), Dow 30 or Nasdaq-100 — boxes sized by market value,
  colored by the day's move, grouped by sector; hover for a mini price chart (~10 weeks of daily closes for 93 names)
- **3-D headquarters map** — each state raised by the total market value (or today's ±% change) of the
  index companies headquartered there; drag to pan, scroll to zoom, Shift-drag to rotate and tilt;
  losses sink below the base plane in the ±% view
- Sector bar charts and scorecard, state scorecard, top gainers/losers, notable movers with reasons,
  macro backdrop (rates, inflation, oil, gold, breadth), themes to consider, upcoming catalysts

## Run it

Browsers block `fetch` from `file://`, so serve the folder:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

`index.html` is the standalone page (loads d3 from cdnjs and the files in `data/`).
`dashboard.html` is the same page body as published to the Claude dashboard runtime, without the shim.

## Data

| File | Contents | Source |
|---|---|---|
| `data/sp500.csv` | 463 constituents: market value, close, % change, sector, HQ | StockAnalysis.com list; sectors + HQ from Wikipedia's S&P 500 list |
| `data/dow30.csv`, `data/ndx100.csv` | Dow 30 and Nasdaq-100 members with the same columns | Kiplinger (Dow), StockAnalysis (Nasdaq-100 + quotes for non-S&P names) |
| `data/sectors.csv` | 11 sector ETFs: weight, 1D/5D/1M/3M/YTD/1Y, yield | ChartRow, CappNotes |
| `data/history.csv` | Daily closes, ~Aug 11–Oct 21, 93 tickers | TipRanks historical-price pages |
| `data/indices.csv`, `data/macro.csv`, `data/stocks.csv`, `data/calendar.csv` | Index closes, macro figures, notable movers, catalysts | Reuters/AP via STL.News, CappNotes, TradingView, Yahoo Finance |
| `data/states_geo.json` | Simplified state outlines (Albers USA, 975×610) | us-atlas (U.S. Census); rebuilt with `scripts/build_states_geo.mjs` |

All figures are a saved snapshot, not a live feed. The natural next step is a small backend
(e.g. Rust/Axum) that regenerates these files from a quote API on a schedule.

## Caveats

- Headquarters location is a proxy for where a company's employees, plants and taxes sit.
- ~36 of the smallest S&P 500 members are missing from the constituent fetch.
- Not investment advice.
