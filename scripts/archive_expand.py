"""Find publicly available archive detail links; keep requests bounded and fail safely.
This does not claim to retrieve all archived stocks. Site may render client-side only.
"""
import re
import time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

ARCHIVE_URL = 'https://serenitystock.com/stocks'
DETAIL_PATH = re.compile(r'^/stocks/([^/?#]+)/([^/?#]+)$', re.I)
HEADERS = {'User-Agent': 'SerenityPersonalDashboard/2.3 (public archive reader)'}


def discover(html):
    soup=BeautifulSoup(html,'html.parser')
    links={}
    for a in soup.find_all('a',href=True):
        href=urljoin(ARCHIVE_URL,a['href'])
        parsed=urlparse(href)
        if parsed.netloc.lower()!='serenitystock.com':continue
        match=DETAIL_PATH.match(parsed.path.rstrip('/'))
        if not match:continue
        market,ticker=match.groups();ticker=ticker.upper()
        if not re.fullmatch(r'(?:[A-Z][A-Z0-9.\-]{0,19}|[0-9]{6}\.(?:KS|KQ))',ticker):continue
        links[ticker]=urljoin('https://serenitystock.com',parsed.path)
    return links


def detail_fields(html, ticker, detail_url):
    soup=BeautifulSoup(html,'html.parser')
    lines=[' '.join(s.split()) for s in soup.stripped_strings]
    def after(label):
        for i,line in enumerate(lines[:-1]):
            if line.casefold()==label.casefold():return lines[i+1]
        return ''
    stance='unclear'
    for line in lines:
        if line.lower() in {'bullish','bearish','neutral','watchlist','unclear'}:
            stance=line.lower();break
    mentions=after('Mentions').replace(',','')
    first=after('First mention');last=after('Last seen')
    # Never synthesize an archive record from an unverified detail page.
    if not (first and last and mentions.isdigit()):return None
    summary=''
    for i,line in enumerate(lines):
        if line.lower()==stance:
            for candidate in lines[i+1:i+6]:
                if len(candidate)>35 and not candidate.startswith('http'):
                    summary=candidate[:850];break
            break
    post=''
    for a in soup.select('a[href]'):
        u=urljoin(detail_url,a.get('href',''))
        if urlparse(u).netloc.lower() in ('x.com','www.x.com','twitter.com','www.twitter.com'):
            post=u;break
    return dict(ticker=ticker,stance=stance,summary_en=summary,mentions=int(mentions),
                first_mention=first,last_seen=last,detail_url=detail_url,post_url=post)


def collect(old_tickers, max_new=25):
    session=requests.Session();session.headers.update(HEADERS)
    try:
        r=session.get(ARCHIVE_URL,timeout=25);r.raise_for_status()
        if len(r.content)>4_000_000:raise ValueError('Archive HTML unexpectedly large')
    except (requests.RequestException,ValueError) as exc:
        print('Archive listing unavailable:',str(exc)[:180]);return []
    links=discover(r.text)
    print(f'Archive discovery: {len(links)} public detail links discovered (site may be JS-rendered)')
    items=[]
    for ticker,url in links.items():
        if ticker in old_tickers or len(items)>=max_new:continue
        try:
            time.sleep(0.6)
            resp=session.get(url,timeout=15);resp.raise_for_status()
            if len(resp.content)>2_000_000:continue
            item=detail_fields(resp.text,ticker,url)
            if item:items.append(item)
        except requests.RequestException as exc:
            print('Detail unavailable:',ticker,str(exc)[:110])
    print(f'Archive enrichment: {len(items)} new verified entries')
    return items
