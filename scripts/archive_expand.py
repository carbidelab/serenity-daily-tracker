"""Bounded discovery from the public /performance stock table.

This is a third-party archive, not the original author's complete X history.
Rows from the public ranking are admitted with only explicitly present metadata.
Missing last-mentioned dates, original posts, and summaries stay unknown; no guessed prices.
"""
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

RANKING_URL = 'https://serenitystock.com/performance'
ROOT = 'https://serenitystock.com'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; SerenityPersonalDashboard/2.4; personal research)'}
DETAIL_PATH = re.compile(r'^/stocks/([^/?#]+)/([^/?#]+)$', re.I)
VALID_TICKER = re.compile(r'(?:[A-Z][A-Z0-9.\-]{0,19}|[0-9]{6}\.(?:KS|KQ))$')
STANCE = {'bullish', 'bearish', 'neutral', 'watchlist', 'unclear', 'conditional_call'}


def _clean(value):
    return ' '.join(str(value or '').split())


def _detail_link(cell):
    for a in cell.find_all('a', href=True):
        url = urljoin(ROOT, a['href'])
        parsed = urlparse(url)
        if parsed.netloc.lower() not in {'serenitystock.com', 'www.serenitystock.com'}:
            continue
        hit = DETAIL_PATH.match(parsed.path.rstrip('/'))
        if hit and VALID_TICKER.fullmatch(hit.group(2).upper()):
            return hit.group(2).upper(), url
    return None


def discover_performance(html):
    """Return verified ticker/detail URL candidates from ranking rows.

    Requires a row-level /stocks/MARKET/TICKER anchor. Does not guess ticker
    by stripping an exchange suffix from concatenated visible text.
    """
    soup = BeautifulSoup(html, 'html.parser')
    seen = {}
    for table in soup.find_all('table'):
        header = table.find('thead')
        cols = [ _clean(t.get_text(' ', strip=True)).lower() for t in header.find_all('th') ] if header else []
        if not cols:
            first = table.find('tr')
            cols = [_clean(t.get_text(' ', strip=True)).lower() for t in first.find_all('th')] if first else []
        ticker_i = next((i for i, h in enumerate(cols) if 'ticker' in h or 'symbol' in h), None)
        if ticker_i is None:
            continue
        for row in table.find_all('tr'):
            cells = row.find_all('td', recursive=False)
            if len(cells) <= ticker_i:
                continue
            pair = _detail_link(cells[ticker_i])
            if not pair:
                # Some layouts wrap the entire row in the detail hyperlink.
                pair = _detail_link(row)
            if not pair:
                continue
            ticker, url = pair
            def col_part(term):
                idx = next((i for i, h in enumerate(cols) if term in h), None)
                return _clean(cells[idx].get_text(' ',strip=True)) if idx is not None and idx < len(cells) else ''
            first_date = col_part('first mentioned') or col_part('first mention')
            company = col_part('company')
            stance_raw = col_part('stance').lower().replace(' ', '_')
            stance = stance_raw if stance_raw in STANCE else 'unclear'
            raw_mentions = col_part('mentions').replace(',', '')
            mentions = int(raw_mentions) if raw_mentions.isdigit() else None
            last_seen = col_part('last seen') or col_part('last mentioned')
            seen[ticker] = {'ticker':ticker, 'detail_url':url,
                            'first_mention_preview': first_date, 'company_name':company,
                            'stance': stance, 'mentions':mentions, 'last_seen_preview':last_seen}

    return list(seen.values())


def detail_fields(html, ticker, detail_url):
    soup = BeautifulSoup(html, 'html.parser')
    lines = [_clean(s) for s in soup.stripped_strings]
    def after(label):
        for i, line in enumerate(lines[:-1]):
            if line.casefold() == label.casefold():
                return lines[i+1]
        return ''
    stance = next((line.lower() for line in lines if line.lower() in STANCE), 'unclear')
    mentions = after('Mentions').replace(',', '')
    first = after('First mention')
    last = after('Last seen')
    if not (first and last and mentions.isdigit()):
        return None
    summary = ''
    for i, line in enumerate(lines):
        if line.lower() == stance:
            for candidate in lines[i+1:i+8]:
                if len(candidate)>35 and not candidate.startswith('http') and candidate.lower() != 'mentions':
                    summary = candidate[:850]
                    break
            break
    post = ''
    for a in soup.select('a[href]'):
        url = urljoin(detail_url, a.get('href',''))
        if urlparse(url).netloc.lower() in ('x.com','www.x.com','twitter.com','www.twitter.com'):
            post = url
            break
    return {'ticker': ticker, 'stance': stance if stance!='conditional_call' else 'unclear',
            'summary_en': summary, 'mentions':int(mentions), 'first_mention':first,
            'last_seen':last, 'detail_url':detail_url, 'post_url':post}


def _sort_key(item):
    # Prefer more recently first-mentioned tickers among candidates. Detail
    # last-seen timestamps are collected later; ranking order is by returns.
    value = item.get('first_mention_preview','')
    for fmt in ('%b %d, %Y', '%B %d, %Y'):
        try: return datetime.strptime(value, fmt).timestamp()
        except ValueError: pass
    return 0


def collect(old_tickers, max_new=50):
    """Add rows verified by the ranking table itself, without fragile detail requests.

    This is a bounded best-effort process. No detail metadata or authored date
    is fabricated when the source ranking does not provide it.
    """
    session=requests.Session()
    session.headers.update(HEADERS)
    try:
        response=session.get(RANKING_URL,timeout=55)
        response.raise_for_status()
        if len(response.content)>24_000_000:
            raise ValueError('Ranking page exceeds 24 MB safety limit')
    except (requests.RequestException, ValueError) as exc:
        print('Performance listing unavailable:',str(exc)[:180])
        return []
    candidates=discover_performance(response.text)
    print(f'Performance discovery: {len(candidates)} ticker detail links found')
    if not candidates:
        print('Performance listing empty; existing snapshot retained')
        return []
    pending=[c for c in candidates if c['ticker'] not in old_tickers]
    pending.sort(key=_sort_key,reverse=True)
    items=[]
    for candidate in pending[:max_new]:
        items.append({
            'ticker':candidate['ticker'],
            'stance':candidate['stance'],
            'summary_en':'',
            'mentions':candidate['mentions'],
            'first_mention':candidate['first_mention_preview'],
            'last_seen':candidate['last_seen_preview'],
            'detail_url':candidate['detail_url'],
            'post_url':'',
            'company_name':candidate['company_name'],
            'data_coverage':'performance_table_only',
        })
    print(f'Archive enrichment: {len(items)} new ranking-verified entries (no detail requests)')
    print(f'Archive remaining candidates: {max(0,len(pending)-len(items))}')
    return items
