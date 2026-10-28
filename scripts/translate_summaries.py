#!/usr/bin/env python3
"""Translate public English archive summaries to Korean using MyMemory's free endpoint.

No API key. Respect anonymous usage limits and do not fabricate translations.
Existing successful summary_ko fields are preserved; no output means unavailable.
"""
import json
import re
import time
from pathlib import Path

import requests

FILE = Path(__file__).resolve().parents[1] / 'site' / 'data' / 'tracker.json'
ENDPOINT = 'https://api.mymemory.translated.net/get'
MAX_BYTES_PER_REQUEST = 450  # public endpoint limit is 500 bytes
MAX_CHARS_PER_RUN = 4200      # below anonymous daily 5000 character quota
REQUEST_INTERVAL = 1.5


def chunk_text(text):
    """Split by words into UTF-8 safe pieces; never drop source characters."""
    words = text.split()
    chunks, current = [], ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if len(candidate.encode('utf-8')) > MAX_BYTES_PER_REQUEST:
            if current:
                chunks.append(current)
                current = ''
            if len(word.encode('utf-8')) > MAX_BYTES_PER_REQUEST:
                raise ValueError('single word exceeds request limit')
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def translate_text(text, session, throttle):
    pieces = []
    for chunk in chunk_text(text):
        if throttle['used'] + len(chunk) > MAX_CHARS_PER_RUN:
            raise RuntimeError('local anonymous request quota safeguard reached')
        # After the last completed request, wait to avoid bursts.
        if throttle['sent']:
            time.sleep(REQUEST_INTERVAL)
        throttle['sent'] += 1
        throttle['used'] += len(chunk)
        response = session.get(ENDPOINT, params={'q': chunk, 'langpair': 'en|ko'}, timeout=25,
                               headers={'User-Agent': 'SerenityDailyTracker/1.10 (public summary translation)'})
        if response.status_code in (429, 403):
            raise RuntimeError(f'provider blocked requests (HTTP {response.status_code})')
        response.raise_for_status()
        data = response.json()
        if int(data.get('responseStatus', 0)) != 200:
            raise RuntimeError(f"provider response: {str(data.get('responseDetails', 'error'))[:90]}")
        result = str((data.get('responseData') or {}).get('translatedText') or '').strip()
        if not re.search(r'[가-힣]', result):
            raise ValueError('service did not return Korean text')
        pieces.append(result)
    return ' '.join(pieces)


def translate_inplace(doc, translate):
    new = cached = unavailable = 0
    cache = {}
    blocked = False
    for stock in doc.get('stocks', []):
        english = str(stock.get('summary_en') or '').strip()
        if not english:
            continue
        if stock.get('summary_ko'):
            cache[english] = stock['summary_ko']
            cached += 1
            continue
        if english in cache:
            stock['summary_ko'] = cache[english]
            cached += 1
            continue
        if blocked:
            unavailable += 1
            continue
        try:
            korean = translate(english)
            stock['summary_ko'] = korean
            cache[english] = korean
            new += 1
        except Exception as exc:
            unavailable += 1
            msg = str(exc)
            print(f"Translation unavailable for {stock.get('ticker', '?')}: {type(exc).__name__}: {msg[:130]}")
            # If provider blocks all queries, stop instead of sending another 21 requests.
            if any(term in msg.lower() for term in ('429', '403', 'quota', 'blocked', 'limit exceeded', 'daily limit')):
                blocked = True
                print('Provider limit reached; skipping the remaining untranslated rows this run.')
    return new, cached, unavailable


def main():
    if not FILE.is_file():
        raise SystemExit('tracker.json not found')
    doc = json.loads(FILE.read_text(encoding='utf-8'))
    with requests.Session() as session:
        throttle = {'used': 0, 'sent': 0}
        result = translate_inplace(doc, lambda text: translate_text(text, session, throttle))
    FILE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Korean summary translation: %d new; %d cached; %d unavailable' % result)
    print('Translation service: MyMemory free public API; %d characters requested.' % throttle['used'])


if __name__ == '__main__':
    main()
