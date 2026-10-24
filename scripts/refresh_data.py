#!/usr/bin/env python3
"""Regenerate the data/ files from free quote sources.

Run on weekdays after the US close (see .github/workflows/refresh.yml).

Static inputs (maintained by hand):
  data/constituents_meta.csv  ticker, name, sector, HQ, shares outstanding (millions), index membership
  data/sectors_meta.csv       sector, ETF proxy, approximate index weight
  data/macro_manual.csv       figures no free API provides (Fed odds, CPI, breadth) - edit as needed
  data/calendar.csv           upcoming catalysts - edit as needed
  data/stocks.csv             notable movers: the numeric columns are refreshed, the notes are editorial

Generated outputs:
  data/sp500.csv data/dow30.csv data/ndx100.csv   quotes, market value (= shares x price), % change
  data/history.csv                                 daily closes, last ~3 months, every constituent
  data/sectors.csv                                 ETF price returns over 1D/5D/1M/3M/YTD/1Y
  data/indices.csv                                 index closes with day, week-to-date and YTD change
  data/macro.csv                                   yields, VIX, oil, gold, bitcoin, dollar + manual rows

Primary source: Yahoo Finance chart endpoint (no key). Fallback: Stooq daily CSV.
Market value is shares outstanding x latest price; update shares_m in constituents_meta.csv
after large buybacks, issuance or splits.
"""
import csv, json, os, sys, time, datetime as dt, urllib.request, urllib.error

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
UA = {'User-Agent': 'Mozilla/5.0 (compatible; market-pulse-dashboard refresh)'}
SLEEP = float(os.environ.get('REFRESH_SLEEP', '0.25'))


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def read_csv(name):
    with open(os.path.join(ROOT, name), newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_csv(name, rows, fields):
    with open(os.path.join(ROOT, name), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def yahoo_series(symbol, rng='1y'):
    """Return list of (date, close) sorted by date, from Yahoo's chart endpoint."""
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(symbol)}?range={rng}&interval=1d'
    data = json.loads(get(url))
    res = data['chart']['result'][0]
    ts = res.get('timestamp') or []
    q = res['indicators']['quote'][0].get('close') or []
    out = []
    for t, c in zip(ts, q):
        if c is None:
            continue
        d = dt.datetime.fromtimestamp(t, dt.timezone(dt.timedelta(hours=-4))).date()  # US/Eastern-ish; exact tz is irrelevant for a date
        out.append((d.isoformat(), float(c)))
    # Yahoo may append today's live/last bar with the same date as the last close; dedupe keeping the last
    dedup = {}
    for d, c in out:
        dedup[d] = c
    return sorted(dedup.items())


def stooq_series(symbol):
    s = symbol.lower().replace('.', '-')
    if symbol.startswith('^'):
        s = {'^GSPC': '^spx', '^DJI': '^dji', '^IXIC': '^ndq', '^RUT': '^rut'}.get(symbol, s)
    else:
        s += '.us'
    txt = get(f'https://stooq.com/q/d/l/?s={s}&i=d').decode('utf-8', 'replace')
    rows = list(csv.DictReader(txt.splitlines()))
    out = [(r['Date'], float(r['Close'])) for r in rows if r.get('Close') not in (None, '', 'N/D')]
    return sorted(out)[-260:]


def series(symbol, rng='1y'):
    try:
        s = yahoo_series(symbol, rng)
        if len(s) >= 2:
            return s
        log(f'  {symbol}: yahoo returned {len(s)} points, trying stooq')
    except Exception as e:
        log(f'  {symbol}: yahoo failed ({e}), trying stooq')
    try:
        return stooq_series(symbol)
    except Exception as e:
        log(f'  {symbol}: stooq failed ({e})')
        return []


def pct(a, b):
    return round((a / b - 1) * 100, 2) if a and b else ''


def close_on_or_before(s, date_iso):
    v = None
    for d, c in s:
        if d <= date_iso:
            v = c
        else:
            break
    return v


def main():
    meta = read_csv('constituents_meta.csv')
    today = None
    quotes = {}
    history = []
    log(f'fetching {len(meta)} constituents')
    for i, m in enumerate(meta):
        t = m['ticker']
        s = series(t.replace('.', '-'), '3mo')
        time.sleep(SLEEP)
        if len(s) < 2:
            log(f'  {t}: no data, keeping blank')
            quotes[t] = None
            continue
        (d1, c1), (d0, c0) = s[-1], s[-2]
        quotes[t] = {'date': d1, 'price': c1, 'prev': c0}
        today = max(today or d1, d1)
        for d, c in s:
            history.append({'ticker': t, 'date': d, 'close': round(c, 4)})
        if (i + 1) % 50 == 0:
            log(f'  {i + 1} done')
    if not today:
        log('no quotes at all; aborting without writing')
        sys.exit(1)
    log(f'latest close date: {today}')

    def row(m):
        q = quotes.get(m['ticker'])
        if not q or q['date'] != today:
            # stale or missing: keep price if we have one, blank the change so the page shows "no quote"
            price = q['price'] if q else ''
            chg = ''
        else:
            price, chg = q['price'], pct(q['price'], q['prev'])
        shares = float(m['shares_m'] or 0)
        cap = round(shares * price / 1000, 2) if price != '' and shares else ''
        return {'ticker': m['ticker'], 'name': m['name'], 'sector': m['sector'], 'cap_b': cap, 'price': round(price, 2) if price != '' else '',
                'chg_pct': chg, 'hq_city': m['hq_city'], 'hq_state': m['hq_state'], 'hq_country': m['hq_country']}

    fields = ['ticker', 'name', 'sector', 'cap_b', 'price', 'chg_pct', 'hq_city', 'hq_state', 'hq_country']
    rows = [row(m) for m in meta]
    by = {r['ticker']: r for r in rows}
    write_csv('sp500.csv', [r for r, m in zip(rows, meta) if m['in_sp500'] == '1'], fields)
    write_csv('dow30.csv', [r for r, m in zip(rows, meta) if m['in_dow30'] == '1'], fields)
    write_csv('ndx100.csv', [r for r, m in zip(rows, meta) if m['in_ndx100'] == '1'], fields)
    write_csv('history.csv', sorted(history, key=lambda r: (r['ticker'], r['date'])), ['ticker', 'date', 'close'])

    # notable movers: refresh numbers, keep the editorial note
    stocks = read_csv('stocks.csv')
    for s in stocks:
        r = by.get(s['ticker'])
        if r and r['chg_pct'] != '':
            s['cap_b'], s['cap_basis'], s['chg_pct'] = r['cap_b'], 'reported', r['chg_pct']
    write_csv('stocks.csv', stocks, ['ticker', 'name', 'sector', 'cap_b', 'cap_basis', 'chg_pct', 'note'])

    # sector ETFs
    log('fetching sector ETFs')
    year_start = f'{today[:4]}-01-01'
    t_today = dt.date.fromisoformat(today)
    out = []
    for m in read_csv('sectors_meta.csv'):
        s = series(m['etf'], '1y')
        time.sleep(SLEEP)
        last = s[-1][1] if s else None
        ref = lambda days: close_on_or_before(s, (t_today - dt.timedelta(days=days)).isoformat())
        out.append({'sector': m['sector'], 'etf': m['etf'], 'weight_pct': m['weight_pct'],
                    'd1_pct': pct(last, s[-2][1]) if len(s) > 1 else '', 'd5_pct': pct(last, ref(7)), 'm1_pct': pct(last, ref(30)),
                    'm3_pct': pct(last, ref(91)), 'ytd_pct': pct(last, close_on_or_before(s, year_start) or (s[0][1] if s else None)),
                    'y1_pct': pct(last, s[0][1] if s else None), 'div_yield_pct': ''})
    write_csv('sectors.csv', out, ['sector', 'etf', 'weight_pct', 'd1_pct', 'd5_pct', 'm1_pct', 'm3_pct', 'ytd_pct', 'y1_pct', 'div_yield_pct'])

    # indices
    log('fetching indices')
    idx = [('S&P 500', '^GSPC'), ('Dow Jones Industrial Average', '^DJI'), ('Nasdaq Composite', '^IXIC'), ('Russell 2000', '^RUT'), ('Philadelphia Semiconductor', '^SOX')]
    out = []
    monday = t_today - dt.timedelta(days=t_today.weekday())
    sp_series = None
    for name, sym in idx:
        s = series(sym, '1y')
        time.sleep(SLEEP)
        if sym == '^GSPC':
            sp_series = s
        if len(s) < 2:
            out.append({'index': name}); continue
        last, prev = s[-1][1], s[-2][1]
        prev_fri = close_on_or_before(s, (monday - dt.timedelta(days=1)).isoformat())
        out.append({'index': name, 'close': round(last, 2), 'chg_pts': round(last - prev, 2), 'chg_pct': pct(last, prev),
                    'wtd_pct': pct(last, prev_fri), 'ytd_pct': pct(last, close_on_or_before(s, year_start) or s[0][1]), 'as_of': s[-1][0]})
    write_csv('indices.csv', out, ['index', 'close', 'chg_pts', 'chg_pct', 'wtd_pct', 'ytd_pct', 'as_of'])

    # macro
    log('fetching macro')
    mac = [('10-year Treasury yield', '^TNX', '%', 'bp'), ('30-year Treasury yield', '^TYX', '%', 'bp'), ('13-week T-bill yield', '^IRX', '%', 'bp'),
           ('VIX', '^VIX', '', '%'), ('Brent crude', 'BZ=F', '$/bbl', '%'), ('WTI crude', 'CL=F', '$/bbl', '%'),
           ('Gold (front month)', 'GC=F', '$/oz', '%'), ('Bitcoin', 'BTC-USD', '$', '%'), ('Dollar index (DXY)', 'DX-Y.NYB', '', '%')]
    out = []
    for name, sym, unit, kind in mac:
        s = series(sym, '1mo')
        time.sleep(SLEEP)
        if len(s) < 2:
            continue
        last, prev = s[-1][1], s[-2][1]
        if kind == 'bp':
            d = round((last - prev) * 100); change = f'{d:+d} bp'
        else:
            change = f'{(last / prev - 1) * 100:+.2f}%'
        out.append({'metric': name, 'value': round(last, 2), 'unit': unit, 'change': change, 'note': f'as of {s[-1][0]}'})
    if sp_series:
        hi = max(c for _, c in sp_series)
        out.append({'metric': 'S&P 500 distance from record', 'value': round((sp_series[-1][1] / hi - 1) * 100, 2), 'unit': '%', 'change': '',
                    'note': f'52-week closing high {hi:,.2f}'})
    out += read_csv('macro_manual.csv')
    write_csv('macro.csv', out, ['metric', 'value', 'unit', 'change', 'note'])
    log('done')


if __name__ == '__main__':
    main()
