import unittest
from scripts.update import extract_cards
HTML='''<html><body><main><div class="card"><div>$MU NasdaqGS</div><div>bullish</div><p>Micron benefits from memory demand but $217.70 is a price.</p><div>Mentions</div><div>202</div><div>First mention</div><div>Sep 25, 2025, 04:25 PM</div><div>Last seen</div><div>Oct 27, 2026, 12:20 PM</div><a href="/stocks/mu">Details</a><a href="https://x.com/aleabitoreddit/status/123">View on X</a></div></main></body></html>'''
class TestParser(unittest.TestCase):
 def test_card(self):
  rows=extract_cards(HTML)
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['ticker'],'MU')
  self.assertEqual(rows[0]['stance'],'bullish')
  self.assertEqual(rows[0]['mentions'],202)
  self.assertEqual(rows[0]['post_url'],'https://x.com/aleabitoreddit/status/123')
if __name__=='__main__':unittest.main()

class TestTickerPrice(unittest.TestCase):
 def test_price_before_symbol_in_summary_does_not_replace_ticker(self):
  html=HTML.replace('$MU NasdaqGS','$NVDA NasdaqGS').replace('Micron benefits', 'Mentions at $2.5 and $217.70. Nvidia benefits')
  self.assertEqual(extract_cards(html)[0]['ticker'],'NVDA')

from scripts.update import extract_stocks

class TestTableParser(unittest.TestCase):
 def test_realistic_table_and_prices(self):
  html = """<table><thead><tr><th>Ticker</th><th>Latest stance</th><th>Mentions</th><th>First Mention Date</th><th>Latest price</th><th>Since mention</th><th>Last seen</th><th>Latest summary</th><th>Post</th></tr></thead><tbody>
  <tr><td><a href='/stocks/te'>$TE NYSE</a></td><td>watchlist</td><td>29</td><td>Oct 19</td><td>$2.49</td><td>+1.2%</td><td>Oct 27</td><td>Mentions TE at $2.5 in a portfolio.</td><td><a href='https://x.com/user/status/111'>Post</a></td></tr>
  <tr><td><a href='/stocks/nvda'>$NVDA NasdaqGS</a></td><td>bullish</td><td>414</td><td>Aug 25</td><td>$217.70</td><td>+2.6%</td><td>Oct 26</td><td>AI infrastructure GPU demand.</td><td><a href='https://x.com/user/status/222'>Post</a></td></tr>
  <tr><td><a href='/stocks/000660.ks'>$000660.KS KSE</a></td><td>bullish</td><td>120</td><td>Nov 04</td><td>₩1,341,000</td><td>-27.8%</td><td>Oct 27</td><td>Memory demand.</td><td><a href='https://x.com/user/status/333'>Post</a></td></tr>
  </tbody></table>"""
  rows=extract_stocks(html)
  self.assertEqual([r['ticker'] for r in rows], ['TE','NVDA','000660.KS'])
  self.assertEqual(rows[0]['mentions'],29)
  self.assertEqual(rows[1]['post_url'],'https://x.com/user/status/222')
  self.assertTrue(all(r['ticker'] not in ('2.5','217.70') for r in rows))

class TestActualLinkBasedTicker(unittest.TestCase):
 def test_concatenated_exchange_text(self):
  html = '''<table><thead><tr><th>Ticker</th><th>Latest stance</th><th>Mentions</th><th>First Mention Date</th><th>Latest price</th><th>Since mention</th><th>Last seen</th><th>Latest summary</th><th>Post</th></tr></thead><tbody>
  <tr><td><a href='/stocks/NMS/ASTS'>$ASTSNasdaqGS</a></td><td>watchlist</td><td>27</td><td>Sep 24</td><td>$41.92</td><td>-0.1%</td><td>Oct 27</td><td>Lists ASTS at $39.</td><td><a href='https://x.com/a/status/1'>Post</a></td></tr>
  <tr><td><a href='/stocks/NYQ/TE'>$TENYSE</a></td><td>watchlist</td><td>29</td><td>Oct 19</td><td>$2.49</td><td>+1.2%</td><td>Oct 27</td><td>Mentions TE at $2.5.</td><td><a href='https://x.com/a/status/2'>Post</a></td></tr>
  <tr><td><a href='/stocks/000660.KS'>$000660.KSKSE</a></td><td>bullish</td><td>120</td><td>Nov 04</td><td>₩1,341,000</td><td>-27.8%</td><td>Oct 27</td><td>Memory demand.</td><td><a href='https://x.com/a/status/3'>Post</a></td></tr>
  </tbody></table>'''
  self.assertEqual([x['ticker'] for x in extract_stocks(html)],['ASTS','TE','000660.KS'])
