"""Rasterize decorative particle positions; all layer compositing stays in Blender."""
import sys,json,math,hashlib,time
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_config import script_config,input_path,output_path,read_json,validate_inputs,camera_samples,input_fingerprints,validate_scene_config,validate_hud_cache,validate_particle_sequence,sha256
CFG=script_config()
if CFG['render']['scale']!=50:raise ValueError('Cached renderer requires scale=50; use render_v3.py for other sizes')
from v3_core import stage
cache=output_path(CFG,'render/hud-cache');dest=output_path(CFG,'render/particle-sequence');dest.mkdir(parents=True,exist_ok=True)
validate_hud_cache(cache,output_path(CFG,'build/nanjing-v3.blend'),CFG)
data=json.loads((input_path(CFG,'snapshot')).read_text(encoding='utf-8'));ps=json.loads((cache/'particles.json').read_text())
def polygon(x,y,w,h):return [(x+14,y),(x+w-28,y),(x+w,y+28),(x+w,y+h-14),(x+w-14,y+h),(x,y+h),(x,y+14)]
for role,coords in [('always',(60,38,280,124)),('intro',(72,214,550,710)),('focus',(1288,310,560,440))]:
    m=Image.new('L',(1920,1080));ImageDraw.Draw(m).polygon(polygon(*coords),fill=255)
    m.resize((960,540),Image.Resampling.LANCZOS).save(cache/f'mask-{role}.png')
started=time.monotonic();digest=hashlib.sha256();empty=Image.new('RGBA',(960,540),(0,0,0,0))
for frame in range(1,1802):
    s=stage((frame-1)/30,data['selection']['codes']);im=empty.copy()
    if s['region']>0:
        m=Image.new('L',(1920,1080));d=ImageDraw.Draw(m);theta=s['phase']*math.tau;c,n=math.cos(theta),math.sin(theta)
        for p in ps:
            lx,ly=p['xy'];x=1000+c*lx-n*ly;y=540-.72*(n*lx+c*ly);r=p['radius']
            d.ellipse((x-r,y-r*.72,x+r,y+r*.72),fill=255)
        m=m.resize((960,540),Image.Resampling.LANCZOS).point([round(i*.38*s['region']) for i in range(256)])
        im=Image.new('RGBA',(960,540),(87,200,231,0));im.putalpha(m)
    path=dest/f'particle_{frame:06d}.png';im.save(path,compress_level=1);digest.update(hashlib.sha256(path.read_bytes()).digest())
    if frame%180==0:print('PARTICLES',frame,round(time.monotonic()-started,1),flush=True)
layer_names=['always.png','intro.png','mask-always.png','mask-intro.png','mask-focus.png','particles.json']+[f'focus_{code}.png' for code in data['selection']['codes']]
manifest={'frames':1801,'encodedFrames':1800,'width':960,'height':540,'sourceBlendSha256':hashlib.sha256((output_path(CFG,'build/nanjing-v3.blend')).read_bytes()).hexdigest(),'sequenceSha256':digest.hexdigest(),'generatorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'config':CFG,'hudManifestSha256':sha256(cache/'hud-manifest.json'),'layers':{name:hashlib.sha256((cache/name).read_bytes()).hexdigest() for name in layer_names}}
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print('PARTICLES_COMPLETE',flush=True)
