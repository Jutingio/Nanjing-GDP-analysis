"""One EEVEE world pass with native Blender composition of separately cached HUD layers."""
import bpy,sys,json,hashlib,time,os,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_config import script_config,input_path,output_path,read_json,validate_inputs,camera_samples,input_fingerprints,validate_scene_config,validate_hud_cache,validate_particle_sequence,sha256
CFG=script_config()
if CFG['render']['scale']!=50:raise ValueError('Cached renderer requires scale=50; use render_v3.py for other sizes')
from v3_core import cache_state
from png_check import valid_png
p=argparse.ArgumentParser();p.add_argument('--frames');p.add_argument('--start',type=int,default=1);p.add_argument('--end',type=int,default=1801);p.add_argument('--review-first',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
cache=output_path(CFG,'render/hud-cache');seq=output_path(CFG,'render/particle-sequence');manifest=json.loads((seq/'manifest.json').read_text())
validate_hud_cache(cache,Path(bpy.data.filepath),CFG)
validate_particle_sequence(seq,manifest)
if manifest.get('config')!=CFG or manifest.get('hudManifestSha256')!=sha256(cache/'hud-manifest.json'):raise ValueError('Particle cache config/HUD manifest mismatch')
assert manifest['sourceBlendSha256']==hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
for name,digest in manifest['layers'].items():assert hashlib.sha256((cache/name).read_bytes()).hexdigest()==digest
selected=json.loads((input_path(CFG,'snapshot')).read_text(encoding='utf-8'))['selection']['codes']
geo=bpy.data.scenes['GEO_WORLD']
if json.loads(geo.get('project_inputs','null'))!=input_fingerprints(CFG):raise ValueError('Scene inputs changed; rebuild first')
if json.loads(geo.get('project_config','null'))!=CFG:raise ValueError('Build and render configs differ')
ng=geo.compositing_node_group;n=ng.nodes;l=ng.links
worldmix=next(x for x in n if x.bl_idname=='ShaderNodeMix');out=next(x for x in n if x.bl_idname=='NodeGroupOutput')
for node in list(n):
    if (node.bl_idname=='CompositorNodeRLayers' and node.scene!=geo) or node.bl_idname=='CompositorNodeAlphaOver':n.remove(node)
def image_node(path,noncolor=False):
    node=n.new('CompositorNodeImage');node.image=bpy.data.images.load(str(path))
    if noncolor:node.image.colorspace_settings.name='Non-Color'
    return node
controls={}
for role in ['intro','focus']:
    im=image_node(cache/f'mask-{role}.png',True);mult=n.new('ShaderNodeMath');mult.operation='MULTIPLY';l.new(im.outputs['Image'],mult.inputs[0]);controls['mask_'+role]=mult.inputs[1]
    controls['mask_output_'+role]=mult.outputs[0]
mx=n.new('ShaderNodeMath');mx.operation='MAXIMUM';l.new(controls['mask_output_intro'],mx.inputs[0]);l.new(controls['mask_output_focus'],mx.inputs[1]);l.new(mx.outputs[0],worldmix.inputs[0])
fixed_mask=image_node(cache/'mask-always.png',True);all_masks=n.new('ShaderNodeMath');all_masks.operation='MAXIMUM';l.new(mx.outputs[0],all_masks.inputs[0]);l.new(fixed_mask.outputs['Image'],all_masks.inputs[1]);l.new(all_masks.outputs[0],worldmix.inputs[0])
last=worldmix.outputs[2]
for role,path in [('particles',seq/'particle_000001.png'),('intro',cache/'intro.png'),('focus',cache/f'focus_{selected[0]}.png'),('always',cache/'always.png')]:
    im=image_node(path);over=n.new('CompositorNodeAlphaOver');over.inputs['Factor'].default_value=1
    l.new(last,over.inputs['Background']);l.new(im.outputs['Image'],over.inputs['Foreground']);last=over.outputs[0]
    if role=='particles':particle=im
    if role=='focus':focus_image=im;focus_path=path.name
    if role in ['intro','focus']:controls[role]=over.inputs['Factor']
l.new(last,out.inputs[0])
geo.render.resolution_percentage=50;geo.eevee.taa_render_samples=CFG['render']['samples'];geo.render.image_settings.file_format='PNG';geo.render.image_settings.color_mode='RGBA';geo.render.image_settings.color_depth='8'
bpy.context.window.scene=geo
settings={'frames':1800,'controlFrame':1801,'width':960,'height':540,'fps':30,'samples':CFG['render']['samples'],'config':CFG,'method':'one EEVEE world pass; three native district HUD caches; Blender alpha, local blur and glow','blend_sha256':manifest['sourceBlendSha256'],'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'layer_manifest':manifest}
job=output_path(CFG,'render')/hashlib.sha256(json.dumps(settings,sort_keys=True).encode()).hexdigest()[:12];frames=job/'frames';frames.mkdir(parents=True,exist_ok=True)
(job/'settings.json').write_text(json.dumps(settings,indent=2),encoding='utf-8');print('LAYER_JOB',str(job),flush=True);started=time.monotonic()
order=list(map(int,a.frames.split(','))) if a.frames else list(range(a.start,a.end+1))
review_frames=[91,601,751,1021,1261,1681,1,1801]
if a.review_first:order=list(dict.fromkeys(review_frames+order))
for index,frame in enumerate(order):
    path=frames/f'frame_{frame:06d}.png'
    if valid_png(path,960,540):continue
    then=time.monotonic();geo.frame_set(frame);s=cache_state((frame-1)/30,selected)
    if s['focusFile'] and s['focusFile']!=focus_path:
        focus_image.image.filepath=str(cache/s['focusFile']);focus_image.image.reload();focus_path=s['focusFile']
    for role,value in [('intro',s['intro']),('focus',s['detail'])]:
        controls[role].default_value=value;controls['mask_'+role].default_value=value
    particle.image.filepath=str(seq/f'particle_{frame:06d}.png');particle.image.reload()
    temp=path.with_name(path.stem+'.partial.png');geo.render.filepath=str(temp);bpy.ops.render.render(scene=geo.name,write_still=True)
    if not valid_png(temp,960,540):raise RuntimeError('Invalid rendered frame')
    os.replace(temp,path)
    with (job/'timings.jsonl').open('a') as log:log.write(json.dumps({'frame':frame,'seconds':round(time.monotonic()-then,3)})+'\n')
    if frame%30==0 or a.frames:print('LAYER_PROGRESS',frame,round(time.monotonic()-started,1),flush=True)
    if a.review_first and index==len(review_frames)-1:
        print('REVIEW_READY',str(job),flush=True);deadline=time.monotonic()+300
        while not (job/'visual-review-passed.txt').exists():
            if time.monotonic()>deadline:raise RuntimeError('Visual review checkpoint expired; rendered frames retained')
            time.sleep(1)
print('LAYER_RENDER_COMPLETE',str(job),round(time.monotonic()-started,1),flush=True)
