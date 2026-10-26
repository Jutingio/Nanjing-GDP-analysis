"""Create original, synthetic demo inputs offline. No private Nanjing assets are required."""
import json,sys,hashlib,argparse,re
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_config import load_config

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--id',default='demo');parser.add_argument('--origin',default='12.17,45.05')
    args=parser.parse_args()
    if not re.fullmatch(r'demo(?:-[a-z0-9]+)*',args.id):raise ValueError('Synthetic id must be demo or demo-<slug>')
    lon,lat=map(float,args.origin.split(','))
    if not -170<lon<170 or not -70<lat<70:raise ValueError('Invalid demo origin')
    folder=ROOT/('data/generated-'+args.id);prefix=folder.relative_to(ROOT).as_posix()
    config=ROOT/('config/'+args.id+'.local.json')
    if folder.exists() or config.exists():raise FileExistsError('Demo already exists; preserve it or choose a fresh checkout')
    folder.mkdir(parents=True)
    def dump(name,data):(folder/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    features=[]
    for i,code in enumerate(['A','B','C']):
        x=lon-.17+i*.12;y=lat-.05
        features.append({'type':'Feature','properties':{'regionCode':code,'name':code+' District'},
                         'geometry':{'type':'Polygon','coordinates':[[[x,y],[x+.1,y],[x+.1,y+.1],[x,y+.1],[x,y]]]}})
    dump('districts.geojson',{'type':'FeatureCollection','features':features})
    snapshot=json.loads((ROOT/'data/examples/snapshot.json').read_text(encoding='utf-8'))
    for row in snapshot['regions']:row['name']=row['code']+' District'
    dump('snapshot.json',snapshot)
    image=Image.new('RGB',(1024,512),'#164369');draw=ImageDraw.Draw(image)
    for i in range(0,1024,64):draw.line((i,0,i,512),fill='#245377',width=2)
    for j in range(0,512,64):draw.line((0,j,1024,j),fill='#245377',width=2)
    for xy in [(100,120,300,300),(460,70,620,220),(730,260,890,410)]:draw.ellipse(xy,fill='#759377')
    image.save(folder/'earth.png')
    photo=Image.new('RGB',(640,360),'#18394D');d=ImageDraw.Draw(photo)
    for i in range(8):
        x=40+i*75;height=60+(i*47)%180;d.rectangle((x,320-height,x+48,320),fill='#3D7C95')
    d.text((25,20),'SYNTHETIC CITY - NOT A REAL MAP OR STATISTIC',fill='white')
    photo.save(folder/'photo.png')
    dump('builtin-font.json',{'type':'blender_builtin','limitation':'Latin demo only; use a licensed CJK font for Chinese cities'})
    dump('culture.json',{'uiLanguage':'en','history':[{'year':'DEMO','text':'Original synthetic content'}],
        'sights':[{'name':'Example','text':'Not an actual destination'}],
        'photo':{'file':prefix+'/photo.png','caption':'Synthetic illustration','capturedOn':'2026-01-01',
                 'sha256':hashlib.sha256((folder/'photo.png').read_bytes()).hexdigest(),
                 'author':'Project contributors','license':'Original procedural example; project code license decision applies'}})
    cfg=load_config('config/example.json');cfg['template']=True
    cfg['city']={'id':args.id,'name':'Demo City','kicker':'S Y N T H E T I C','period':'2024'}
    names={'snapshot':'snapshot.json','culture':'culture.json','prepared_geo':'prepared.json','district_geojson':'districts.geojson',
           'city_geojson':'city.geojson','base_blend':'base.blend','font':'builtin-font.json','earth_texture':'earth.png','photo':'photo.png','camera_track':'camera.json'}
    cfg['paths']={k:prefix+'/'+v for k,v in names.items()};cfg['paths']['output']='output/'+args.id
    cfg['geometry'].update(originLonLat=[lon,lat],boundaryYear=2024)
    cfg['credits']={'footer':'SYNTHETIC geometry and statistics / not real city data','assets':'Original procedural textures / Blender built-in font'}
    config.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DEMO_INPUTS_READY',config.relative_to(ROOT).as_posix())

if __name__=='__main__':main()
