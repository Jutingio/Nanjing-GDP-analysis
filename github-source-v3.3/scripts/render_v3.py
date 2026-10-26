"""Render independent frames; never reuse a moving FX frame based on camera state."""
import bpy,sys,json,argparse,time,hashlib,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_config import script_config,input_path,output_path,read_json,validate_inputs,camera_samples,input_fingerprints,validate_scene_config,validate_hud_cache,validate_particle_sequence,sha256
CFG=script_config()
from png_check import valid_png
p=argparse.ArgumentParser();p.add_argument('--frames');p.add_argument('--start',type=int,default=1);p.add_argument('--end',type=int,default=1800);p.add_argument('--scale',type=int,default=CFG['render']['scale']);p.add_argument('--samples',type=int,default=CFG['render']['samples'])
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
config={'width':1920*a.scale//100,'height':1080*a.scale//100,'samples':a.samples,'fps':30,'frames':a.end,'start_frame':a.start,'config':CFG,'blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
dest=output_path(CFG,'previews') if a.frames else output_path(CFG,'render')/hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()[:12]
images=dest if a.frames else dest/'frames';images.mkdir(parents=True,exist_ok=True)
(dest/'settings.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
geo=bpy.data.scenes['GEO_WORLD']
if not 1<=a.scale<=100 or a.samples<1 or not 1<=a.start<=a.end<=1801:raise ValueError('Invalid render arguments')
validate_scene_config(geo.get('project_config','null'),CFG)
if json.loads(geo.get('project_inputs','null'))!=input_fingerprints(CFG):raise ValueError('Scene inputs changed; rebuild first')
for s in bpy.data.scenes:
    s.render.resolution_percentage=a.scale;s.eevee.taa_render_samples=a.samples if s==geo else CFG['render']['hud_samples'];s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8'
started=time.monotonic();timings=[]
for f in map(int,a.frames.split(',')) if a.frames else range(a.start,a.end+1):
    path=images/(f'frame-{f:04d}.png' if a.frames else f'frame_{f:06d}.png')
    if not a.frames and valid_png(path,config['width'],config['height']):continue
    then=time.monotonic()
    for s in bpy.data.scenes:bpy.context.window.scene=s;s.frame_set(f)
    bpy.context.window.scene=geo;temp=path.with_name(path.stem+'.partial.png');geo.render.filepath=str(temp)
    bpy.ops.render.render(scene=geo.name,write_still=True)
    if not valid_png(temp,config['width'],config['height']):raise RuntimeError(f'Invalid frame {f}')
    os.replace(temp,path);row={'frame':f,'seconds':round(time.monotonic()-then,3)};timings.append(row)
    with (dest/'timings.jsonl').open('a') as log:log.write(json.dumps(row)+'\n')
    if a.frames or f%30==0:print('V3_PROGRESS',f,round(time.monotonic()-started,1),str(dest),flush=True)
print('V3_RENDER_COMPLETE',json.dumps({'directory':str(dest),'seconds':round(time.monotonic()-started,1),'rendered':len(timings)}),flush=True)
