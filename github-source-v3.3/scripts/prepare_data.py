"""Prepare same-year data from official HTML or bundled verified source extracts."""
import sys,json,re,hashlib,urllib.request,shutil
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from v3_core import select_regions,validate_snapshot,share_pct
class TableParser(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=[];self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in ('td','th'):self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(re.sub(r'\s+','',''.join(self.cell)));self.cell=None
        if tag=='tr' and self.row:self.rows.append(self.row);self.row=[]

def fetch(key,url):
    if '--verified-extract' in sys.argv:
        path=ROOT/'data/sources'/f'{key}.web-extract.txt'
        raw=path.read_bytes()
        return '',{'id':key,'publisher':'南京市统计局','url':url,'accessedOn':'2026-09-11','rawFile':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'acquisition':'web tool source text; values independently transcribed from first 2024 measure column','originalHtmlAvailable':False,'limitation':'Direct local download returned HTTP 403'}
    path=ROOT/'data/sources'/f'{key}.html';path.parent.mkdir(parents=True,exist_ok=True)
    raw=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=35).read()
    path.write_bytes(raw)
    match=re.search(br'charset\s*=\s*["\x27]?([\w-]+)',raw[:4096],re.I)
    enc=match.group(1).decode() if match else 'utf-8'
    page=raw.decode(enc if enc.lower() not in ('gb2312','gbk') else 'gb18030')
    return page,{'id':key,'publisher':'南京市统计局','url':url,'accessedOn':'2026-09-11','rawFile':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest()}

sources=[];tables={}
base='https://tjj.nanjing.gov.cn/material/njnj_2025/'
for key,table in [('gdp','17-6'),('resident_population','17-3'),('retail_sales','17-13')]:
    page,source=fetch(key,base+'quxian/'+table+'.html');sources.append(source)
    if '--verified-extract' in sys.argv:
        tables[key]=json.loads((ROOT/'data/verified-table-values.json').read_text(encoding='utf-8'))[key]
        continue
    p=TableParser();p.feed(page);values={}
    for row in p.rows:
        if not row:continue
        name=row[0]
        if name=='全市' or name.endswith('区'):
            # First numeric cell is the requested 2024 measure, not the component columns.
            numeric=[cell for cell in row[1:] if re.fullmatch(r'\d+(?:\.\d+)?',cell)]
            if numeric:values[name]=float(numeric[0])
    tables[key]=values
    print(key,json.dumps(values,ensure_ascii=False),flush=True)
_,scope=fetch('scope-notes',base+'shouye/bzsm.html');sources.append(scope)
codes={'320102':'玄武区','320104':'秦淮区','320105':'建邺区','320106':'鼓楼区','320113':'栖霞区','320114':'雨花台区','320115':'江宁区','320117':'溧水区','320118':'高淳区'}
data={'schemaVersion':31,'period':'2024','dataMode':'official_design_preview','sources':sources,
      'cityTotals':{k:{'period':'2024','value':v['全市'],'sourceId':k} for k,v in tables.items()},
      'regions':[{'code':code,'name':name,'period':'2024','values':{k:v[name] for k,v in tables.items()},'scopeNote':'年鉴同名区条目；地图采用2017概览边界'} for code,name in codes.items()],
      'selection':{'seed':20260911,'codes':select_regions(list(codes),20260911),'method':'Python Random.sample without replacement from sorted eligible administrative codes','excluded':{'320111':'浦口统计范围剔除江北直管区','320116':'六合统计范围剔除江北直管区'}},
      'boundaryYear':2017,'geometryStatus':'overview_only'}
validate_snapshot(data)
for row in data['regions']:row['shares']={k:share_pct(v,data['cityTotals'][k]['value']) for k,v in row['values'].items()}
(ROOT/'data/snapshot.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
# Inputs must be prepared explicitly inside this project; no sibling-project fallback.
if not (ROOT/'inputs/nanjing-base.blend').is_file():
    raise FileNotFoundError('Prepare inputs/nanjing-base.blend; see docs/resources.md')
base_hash=hashlib.sha256((ROOT/'inputs/nanjing-base.blend').read_bytes()).hexdigest()
base_manifest=ROOT/'inputs/base-manifest.json'
if base_manifest.exists():
    assert json.loads(base_manifest.read_text(encoding='utf-8'))['sha256']==base_hash,'Base input changed'
else:
    base_manifest.write_text(json.dumps({'source':'bundled inputs/nanjing-base.blend, originally V1','sha256':base_hash},indent=2),encoding='utf-8')
print('SELECTED',[(c,codes[c]) for c in data['selection']['codes']],flush=True)
