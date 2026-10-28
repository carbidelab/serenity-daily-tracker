#!/usr/bin/env python3
"""Best-effort archive snapshots, not an official X API or a complete tweet feed."""
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'site' / 'data' / 'tracker.json'
SOURCE = 'https://serenitystock.com/'
TICKER_RE = re.compile(r'^\$([A-Za-z0-9][A-Za-z0-9.\-]{0,14})(?=\s|$)')
COMPANIES = {'NVDA':'엔비디아 (NVIDIA)', 'MU':'마이크론 (Micron)', 'COHR':'코히런트 (Coherent)', 'AAOI':'어플라이드 옵토일렉트로닉스 (Applied Optoelectronics)', 'ALMU':'에일루마 (Aeluma)', '000660.KS':'SK하이닉스', 'ASTS':'AST 스페이스모바일', 'TE':'TE'}
STANCE = {'bullish': '긍정', 'bearish': '부정', 'neutral': '중립', 'unclear': '판단 보류', 'watchlist': '관심 목록'}


def valid_ticker(ticker):
    return bool(re.fullmatch(r'(?:[A-Z][A-Z0-9.\-]{0,19}|[0-9]{6}\.(?:KS|KQ))', str(ticker or '')))


def normalize(s):
    return ' '.join(str(s or '').split())


def extract_cards(html):
    soup = BeautifulSoup(html, 'html.parser')
    found = {}
    for a in soup.find_all('a', href=True):
        if normalize(a.get_text(' ', strip=True)).lower() != 'details':
            continue
        node = a.parent
        chosen = None
        for _ in range(7):
            if not node or node.name in ('body', 'html'):
                break
            text = node.get_text('\n', strip=True)
            headings = [TICKER_RE.match(normalize(v)) for v in node.stripped_strings]
            headings = [m for m in headings if m and not m.group(1)[0].isdigit()]
            if headings and 'Last seen' in text and 'Mentions' in text and len(text) < 3000:
                # Avoid accidentally combining multiple sibling cards.
                if len(re.findall(r'\bLast seen\b', text)) == 1:
                    chosen = node
                    break
            node = node.parent
        if chosen is None:
            continue
        lines = [normalize(t) for t in chosen.stripped_strings]
        # Restrict to text from this detail link's card.
        all_text = '\n'.join(lines)
        # Stock ticker must be the first $SYMBOL heading in the card, never a $price in its summary.
        head = next((TICKER_RE.match(line) for line in lines if TICKER_RE.match(line) and not TICKER_RE.match(line).group(1)[0].isdigit()), None)
        if not head:
            continue
        ticker = head.group(1).upper()
        stance = next((k for k in STANCE if re.search(r'(?im)^'+k+r'$',all_text)), 'unclear')
        def after(label):
            for i, line in enumerate(lines[:-1]):
                if line.lower() == label.lower():
                    return lines[i+1]
            return ''
        summary = ''
        for i, line in enumerate(lines):
            if line.lower() == stance:
                for nextline in lines[i+1:]:
                    if nextline.lower() == 'mentions':
                        break
                    if len(nextline) >= 20 and nextline.lower() not in ('first mention','last seen'):
                        summary = nextline
                        break
                break
        xlink = next((urljoin(SOURCE, l['href']) for l in chosen.find_all('a',href=True)
                      if 'x.com/' in l['href'] or 'twitter.com/' in l['href']), '')
        if not xlink:
            # Detail link sometimes has link on sibling outside chosen card.
            xlink = ''
        detail = urljoin(SOURCE, a.get('href',''))
        if not detail.startswith('https://serenitystock.com/'):
            detail = SOURCE
        raw_mentions = after('Mentions').replace(',','')
        mentions = int(raw_mentions) if raw_mentions.isdigit() else None
        item = {'ticker':ticker,'stance':stance,'summary_en':summary[:850],
                'mentions':mentions,'last_seen':after('Last seen'),
                'first_mention':after('First mention'), 'detail_url':detail, 'post_url':xlink}
        if ticker not in found:
            found[ticker] = item
    return [x for x in found.values() if valid_ticker(x['ticker'])]


def extract_table(html):
    """Read the public Latest Mentioned Stocks table rather than page layout cards."""
    soup = BeautifulSoup(html, 'html.parser')
    results = {}
    for table in soup.find_all('table'):
        heads = [normalize(x.get_text(' ', strip=True)).lower() for x in table.select('thead th')]
        if not heads:
            first = table.find('tr')
            heads = [normalize(x.get_text(' ', strip=True)).lower() for x in first.find_all(['th','td'], recursive=False)] if first else []
        def column(word):
            return next((i for i, h in enumerate(heads) if word in h), None)
        tcol, scol, mcol, lcol = column('ticker'), column('stance'), column('mentions'), column('last seen')
        if None in (tcol, scol, mcol, lcol):
            continue
        firstcol=column('first mention')
        summarycol=column('summary')
        postcol=column('post')
        for tr in table.find_all('tr'):
            cells = tr.find_all('td', recursive=False)
            if len(cells) < len(heads):
                continue
            ticker_cell = cells[tcol]
            # Stock symbol occurs at the beginning of the ticker cell, before exchange.
            raw = normalize(ticker_cell.get_text(' ', strip=True))
            # Prefer the unambiguous /stocks/<market>/<ticker> link over visible
            # text: production tables concatenate the symbol and exchange
            # (e.g. '$ASTSNasdaqGS'), so a whitespace-based regex finds zero.
            ticker = ''
            for anchor in ticker_cell.find_all('a', href=True):
                path = urlparse(urljoin(SOURCE, anchor['href'])).path
                hit = re.match(r'^/stocks/(?:[^/]+/)?([^/]+)/?$', path, re.I)
                if hit:
                    candidate = hit.group(1).upper()
                    if re.fullmatch(r'(?:[A-Z][A-Z0-9.\-]{0,19}|[0-9]{6}\.[A-Z]{1,3})', candidate):
                        ticker = candidate
                        break
            if not ticker:
                # Only accept a symbol with a delimiter. Never guess a
                # ticker from concatenated stock + exchange text.
                match = re.match(r'^\$([A-Za-z][A-Za-z0-9.\-]{0,19}|[0-9]{6}\.[A-Za-z]{1,3})(?=\s|$)', raw)
                if match:
                    ticker = match.group(1).upper()
            if not ticker:
                continue
            stance = normalize(cells[scol].get_text(' ',strip=True)).lower()
            if stance not in STANCE:
                stance = 'unclear'
            mt = normalize(cells[mcol].get_text(' ',strip=True)).replace(',','')
            mentions = int(mt) if mt.isdigit() else None
            summary = normalize(cells[summarycol].get_text(' ',strip=True))[:850] if summarycol is not None else ''
            def coltext(i):
                return normalize(cells[i].get_text(' ',strip=True)) if i is not None else ''
            def href_from(cell, pred):
                for a in cell.find_all('a', href=True):
                    absolute = urljoin(SOURCE, a['href'])
                    if pred(absolute): return absolute
                return ''
            detail = href_from(ticker_cell, lambda u: u.startswith('https://serenitystock.com/')) or SOURCE
            post = href_from(cells[postcol], lambda u: urlparse(u).netloc.lower() in ('x.com','www.x.com','twitter.com','www.twitter.com')) if postcol is not None else ''
            results[ticker]={'ticker':ticker,'stance':stance,'summary_en':summary,'mentions':mentions,
                             'last_seen':coltext(lcol),'first_mention':coltext(firstcol),
                             'detail_url':detail,'post_url':post}
        if results:
            break
    return [x for x in results.values() if valid_ticker(x['ticker'])]


def extract_stocks(html):
    items = extract_table(html)
    return items if len(items) >= 3 else extract_cards(html)


def fetch():
    headers={'User-Agent':'Mozilla/5.0 (compatible; SerenityPersonalDashboard/1.0; +https://github.com/)'}
    resp=requests.get(SOURCE,headers=headers,timeout=25)
    resp.raise_for_status()
    if len(resp.content)>4_000_000: raise ValueError('Unexpectedly large page')
    return resp.text


def main():
    now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    previous={}
    if OUT.exists():
        try: previous=json.loads(OUT.read_text(encoding='utf-8'))
        except (ValueError,OSError): pass
    try:
        items=[x for x in extract_stocks(fetch()) if valid_ticker(x['ticker'])]
        if len(items)<3:
            raise RuntimeError(f'Only {len(items)} stock cards parsed; page may have changed')
    except Exception as e:
        print(f'Source fetch/parse failed: {e}', file=sys.stderr)
        if previous:
            # Fail without overwriting last successful results.
            sys.exit(1)
        raise
    for x in items:
        x['company_name'] = COMPANIES.get(x['ticker'], '')
    old_by_ticker={x['ticker']:x for x in previous.get('stocks',[]) if valid_ticker(x.get('ticker'))}
    old_history=previous.get('history',[])
    for x in items:
        old=old_by_ticker.get(x['ticker'])
        x['stance_changed'] = bool(old and old.get('stance') != x['stance'])
        x['new_mention_since_previous'] = bool(old and (x.get('mentions') or 0) > (old.get('mentions') or 0))
        x['changed_since_previous'] = bool(old and (x['stance_changed'] or x['new_mention_since_previous'] or old.get('last_seen') != x['last_seen']))
        x['new_since_previous'] = not bool(old)
        x['previous_stance'] = old.get('stance') if old and x['stance_changed'] else None
        x['mentions_delta'] = max(0,(x.get('mentions') or 0) - (old.get('mentions') or 0)) if old else None
        # Observable stance changes only; earlier unseen changes cannot be reconstructed.
        transitions = list(old.get('stance_history', [])) if old else []
        if old and old.get('stance') != x['stance']:
            transitions.append({'observed_at_utc': now, 'from': old['stance'], 'to': x['stance']})
        x['stance_history'] = transitions[-100:]
        # Preserve previously verified pricing when refreshing the archive snapshot.
        if old and isinstance(old.get('price'), dict):
            x['price'] = old['price']
    # Rebuild from corrected tickers: previous data may contain mistakenly parsed prices.
    if old_by_ticker and not any(old_by_ticker.get(x['ticker']) for x in items):
        print('Previous snapshot appears to use price-as-ticker; resetting comparison baseline')
    counts=Counter(x['stance'] for x in items)
    history=old_history
    day=now[:10]
    record={'date':day,'stocks':len(items),'bullish':counts['bullish'], 'bearish':counts['bearish'], 'neutral':counts['neutral'], 'unclear':counts['unclear'], 'watchlist':counts['watchlist']}
    if history and history[-1]['date']==day:history[-1]=record
    else: history.append(record)
    doc={'source':SOURCE,'source_type':'third_party_archive_snapshot','last_successful_sync_utc':now,
         'disclaimer':'Not an official or complete X feed. Changes are between observed archive snapshots, not the date a post was authored.',
         'stocks':sorted(items,key=lambda x:(not x['changed_since_previous'],not x['new_since_previous'],x['ticker'])),
         'history':history[-365:]}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Saved {len(items)} tickers at {now}')

if __name__=='__main__':main()
