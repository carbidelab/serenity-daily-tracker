import unittest
from scripts.update import extract_cards
HTML='''<html><body><main><div class="card"><div>$MU NasdaqGS</div><div>bullish</div><p>Micron benefits from memory demand.</p><div>Mentions</div><div>202</div><div>First mention</div><div>Sep 25, 2025, 04:25 PM</div><div>Last seen</div><div>Oct 27, 2026, 12:20 PM</div><a href="/stocks/mu">Details</a><a href="https://x.com/aleabitoreddit/status/123">View on X</a></div></main></body></html>'''
class TestParser(unittest.TestCase):
 def test_card(self):
  rows=extract_cards(HTML)
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['ticker'],'MU')
  self.assertEqual(rows[0]['stance'],'bullish')
  self.assertEqual(rows[0]['mentions'],202)
  self.assertEqual(rows[0]['post_url'],'https://x.com/aleabitoreddit/status/123')
if __name__=='__main__':unittest.main()
