#!/usr/bin/env python3
"""Optional, best-effort EOD market prices from unofficial Yahoo Finance access.
Never infer post-time trades from daily prices. No fabricated numbers.
"""
import json, re, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "site/data/tracker.json"

def mention_date(v):
    if not v: return None
    v = str(v)
    # Only unambiguous ISO dates: display text without timezone can't be converted reliably.
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", v)
    if m:
        try: return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError: return None
    # Archive may display dates like 'Sep 24, 2025, 11:36 PM'.
    # The original timezone is unknown: use only the displayed calendar date.
    try:
        from dateutil import parser
        dt = parser.parse(v, fuzzy=False)
        if dt.year < 2000 or dt.date() > datetime.now(timezone.utc).date():return None
        return dt.date()
    except (ValueError, OverflowError, TypeError):return None

def fetch_price(symbol, first_date):
    import yfinance as yf
    from pandas import Timestamp
    ticker = yf.Ticker(symbol)
    # Retrieve maximum 10 years. Missing date or unavailable instrument -> return blank.
    start = (first_date - timedelta(days=7)) if first_date else (datetime.now(timezone.utc).date() - timedelta(days=30))
    end = datetime.now(timezone.utc).date() + timedelta(days=2)
    df = ticker.history(start=start.isoformat(),end=end.isoformat(),interval="1d",auto_adjust=False,actions=False,timeout=12)
    if df is None or df.empty or 'Close' not in df: return None
    closes = []
    for dt, row in df.iterrows():
        val = row['Close']
        try:
            px = float(val)
            if not (px > 0 and px < float('inf')):continue
            closes.append((dt.date(),px))
        except (ValueError, TypeError):pass
    if not closes: return None
    latest_date,latest = closes[-1]
    first = next(((d,p) for d,p in closes if first_date and d >= first_date),None)
    # If first mention precedes availability, don't substitute later stock price without warning.
    pct = round((latest / first[1] - 1)*100,2) if first and first[1] else None
    currency = 'KRW' if symbol.endswith(('.KS','.KQ')) else 'USD'
    return {'latest_close': round(latest,4),'latest_date':latest_date.isoformat(),
            'first_close':round(first[1],4) if first else None,
            'first_price_date':first[0].isoformat() if first else None,
            'return_pct':pct,'currency':currency,'basis':'unadjusted_daily_close',
            'provider':'Yahoo Finance (unofficial via yfinance)',
            'fetched_utc':datetime.now(timezone.utc).isoformat(timespec='seconds')}

def main():
    if not DATA.exists():
        print('No tracking JSON yet, price task skipped');return
    doc=json.loads(DATA.read_text(encoding='utf-8'))
    success=0; errors=[]
    for stock in doc.get('stocks',[]):
        symbol = str(stock.get('ticker',''))
        if not re.fullmatch(r'(?:[A-Z][A-Z0-9.\-]{0,19}|[0-9]{6}\.(?:KS|KQ))',symbol):continue
        first_date=mention_date(stock.get('first_mention'))
        old=stock.get('price') or {}
        today=datetime.now(timezone.utc).date().isoformat()
        if old.get('fetched_utc','').startswith(today) and old.get('first_price_date') and first_date:
            continue
        try:
            price=fetch_price(symbol,first_date)
            if price:
                stock['price']=price;success+=1
            else:
                errors.append(symbol+': no EOD records')
        except Exception as ex:
            errors.append(symbol+': '+str(ex)[:110])
        time.sleep(0.15)
    DATA.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Price lookup completed: {success} refreshed; {len(errors)} unavailable')
    for e in errors[:12]:print('Unavailable:',e)

if __name__ == '__main__':main()
