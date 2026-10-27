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
TICKER_RE = re.compile(r'(?<![\w.])\$([A-Za-z0-9][A-Za-z0-9.\-]{0,14})(?![\w.])')
STANCE = {'bullish': '긍정', 'bearish': '부정', 'neutral': '중립', 'unclear': '판단 보류', 'watchlist': '관심 목록'}


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
            match = TICKER_RE.search(text)
            if match and 'Last seen' in text and 'Mentions' in text and len(text) < 3000:
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
        m = TICKER_RE.search(all_text)
        if not m:
            continue
        ticker = m.group(1).upper()
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
    return list(found.values())


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
        items=extract_cards(fetch())
        if len(items)<3:
            raise RuntimeError(f'Only {len(items)} stock cards parsed; page may have changed')
    except Exception as e:
        print(f'Source fetch/parse failed: {e}', file=sys.stderr)
        if previous:
            # Fail without overwriting last successful results.
            sys.exit(1)
        raise
    old_by_ticker={x['ticker']:x for x in previous.get('stocks',[])}
    old_history=previous.get('history',[])
    for x in items:
        old=old_by_ticker.get(x['ticker'])
        x['changed_since_previous'] = bool(old and (old.get('stance')!=x['stance'] or old.get('last_seen')!=x['last_seen']))
        x['new_since_previous'] = not bool(old)
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
