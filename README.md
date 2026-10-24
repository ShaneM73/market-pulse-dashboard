# Market Pulse — S&P 500 / Dow / Nasdaq-100 dashboard

An interactive market dashboard built as a single HTML page with d3. Snapshot data is for the
**October 21, 2026** close.

## What's in it

- Index tiles (S&P 500, Dow, Nasdaq, Russell 2000, VIX, 10-year yield) and a one-line takeaway
- **Heat map** of the S&P 500 (463 constituents), Dow 30 or Nasdaq-100 — boxes sized by market value,
  colored by the day's move, grouped by sector; hover for a mini price chart (~10 weeks of daily closes for 93 names)
- **3-D headquarters map** — each state raised by the total market value (or today's ±% change) of the
  index companies headquartered there; drag to pan, scroll to zoom, Shift-drag to rotate and tilt;
  losses sink below the base plane in the ±% view; **Change, past 30 days** replays each trading day's
  change as an animation (play/pause, scrub, speed), computed from `data/history.csv`
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

## Daily refresh

`.github/workflows/refresh.yml` runs `scripts/refresh_data.py` **every weekday at 22:40 UTC**
(5:40 pm Central, after the 4 pm Eastern close) and commits the regenerated `data/` files when they
change. It can also be run by hand from the Actions tab ("Run workflow").

- Quotes and ~3 months of daily closes for all 478 constituents come from Yahoo Finance's chart
  endpoint, with Stooq as a fallback; sector ETFs, indices, yields, VIX, oil, gold, bitcoin and the
  dollar come the same way.
- Market value = shares outstanding (`data/constituents_meta.csv`, `shares_m`) x latest price.
  Update `shares_m` after large buybacks, issuance or splits.
- Sector multi-period returns are **price** returns after the first refresh (the original snapshot
  used total returns); the dividend-yield column stays blank until a source is added.
- Hand-maintained: `constituents_meta.csv` (membership, sectors, HQs), `sectors_meta.csv`,
  `macro_manual.csv` (CPI, Fed odds, breadth), `calendar.csv`, and the notes in `stocks.csv`.
  The "themes to consider" prose on the page was written for Oct 21, 2026; the numbers inside it refresh, the wording does not.
- Enable GitHub Pages on `main` (root) and the page at `shanem73.github.io/market-pulse-dashboard`
  updates itself after each run.

## Caveats

- Headquarters location is a proxy for where a company's employees, plants and taxes sit.
- ~36 of the smallest S&P 500 members are missing from the constituent fetch.
- Not investment advice.
