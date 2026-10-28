import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from archive_expand import discover_performance,collect
from unittest.mock import patch

HTML = """<table><thead><tr><th>Ticker</th><th>Company</th><th>First mentioned</th><th>Mentions</th><th>Stance</th></tr></thead><tbody>
<tr><td><a href='/stocks/NMS/MU'>MU</a></td><td>Micron</td><td>Sep 25, 2025</td><td>202</td><td>bullish</td></tr>
<tr><td><a href='/stocks/NMS/AAOI'>AAOI</a></td><td>Applied Optoelectronics</td><td>Oct 20, 2025</td><td>401</td><td>neutral</td></tr></tbody></table>"""
class Response:
    content=HTML.encode()
    text=HTML
    def raise_for_status(self):pass
class Session:
    headers={}
    def get(self,*a,**k):return Response()

def test_rows():
    entries=discover_performance(HTML)
    assert len(entries)==2
    assert entries[0]['stance']=='bullish' and entries[0]['mentions']==202
    assert entries[1]['ticker']=='AAOI' and entries[1]['last_seen_preview']==''

def test_collection():
    with patch('archive_expand.requests.Session',return_value=Session()):
        data=collect(set(),max_new=50)
    assert len(data)==2
    assert all(not v['post_url'] and not v['summary_en'] and not v['last_seen'] for v in data)
    assert data[0]['data_coverage']=='performance_table_only'

if __name__=='__main__':test_rows();test_collection();print('PASS')
