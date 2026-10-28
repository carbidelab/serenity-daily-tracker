import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from archive_expand import discover_performance, detail_fields

HTML='''<table><thead><tr><th>#</th><th>Ticker</th><th>Company</th><th>First mentioned</th><th>Price when mentioned</th><th>Current price</th><th>Return since first</th><th>Mentions</th><th>Stance</th></tr></thead><tbody>
<tr><td>1</td><td><a href="/stocks/NMS/MU">$MUNasdaqGS</a></td><td>Micron Technology, Inc.</td><td>Sep 25, 2025</td><td>$156.83</td><td>$932.36</td><td>+494.5%</td><td>202</td><td>bullish</td></tr>
<tr><td>2</td><td><a href="/stocks/KSC/000660.KS">$000660.KSKSE</a></td><td>SK hynix</td><td>Nov 04, 2025</td><td>₩586,000</td><td>₩1,449,000</td><td>147.27%</td><td>120</td><td>bullish</td></tr>
<tr><td>3</td><td>$217.70</td><td>Not a ticker</td><td>Oct 01, 2026</td><td>$1</td><td>$2</td><td>+100%</td><td>1</td><td>neutral</td></tr>
</tbody></table>'''

def test_ranking():
    result=discover_performance(HTML)
    assert len(result)==2, result
    assert result[0]['ticker']=='MU' and result[1]['ticker']=='000660.KS'
    assert result[0]['company_name']=='Micron Technology, Inc.'
    assert '217.70' not in str(result)

def test_detail():
    html='''<h1>MU</h1><p>bullish</p><p>Memory demand stays strong according to commentary</p><div>Mentions</div><div>202</div><div>First mention</div><div>Sep 25, 2025, 04:25 PM</div><div>Last seen</div><div>Oct 27, 2026, 12:20 PM</div><a href="https://x.com/aleabitoreddit/status/123">View on X</a>'''
    item=detail_fields(html,'MU','https://serenitystock.com/stocks/NMS/MU')
    assert item and item['mentions']==202 and item['post_url'].endswith('/123')

if __name__=='__main__':
    test_ranking();test_detail();print('2 parser tests passed')
