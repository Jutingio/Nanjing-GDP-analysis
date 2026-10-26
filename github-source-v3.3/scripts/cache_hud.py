"""Export immutable Blender HUD layers; the original scene stays unchanged."""
import bpy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_config import script_config,input_path,output_path,read_json,validate_inputs,camera_samples,input_fingerprints,validate_scene_config,validate_hud_cache,validate_particle_sequence,sha256
CFG=script_config()
if '--always-only' in sys.argv:raise ValueError('Regenerate all HUD layers together; partial updates cannot certify provenance')
if json.loads(bpy.data.scenes['GEO_WORLD'].get('project_inputs','null'))!=input_fingerprints(CFG):raise ValueError('Scene inputs changed; rebuild first')
if CFG['render']['scale']!=50:raise ValueError('Cached renderer requires scale=50; use render_v3.py for other sizes')
dest=output_path(CFG,'render/hud-cache');dest.mkdir(parents=True,exist_ok=True)
if json.loads(bpy.data.scenes['GEO_WORLD'].get('project_config','null'))!=CFG:raise ValueError('Build and cache configs differ')
hud=bpy.data.scenes['HUD'];data=json.loads((input_path(CFG,'snapshot')).read_text(encoding='utf-8'));code=data['selection']['codes'][0]
hud.render.resolution_percentage=50;hud.eevee.taa_render_samples=CFG['render']['hud_samples'];hud.render.image_settings.file_format='PNG';hud.render.image_settings.color_mode='RGBA';hud.render.use_compositing=False
bpy.context.window.scene=hud
for ob in hud.objects:
    ob.animation_data_clear()
layers=[('always','always',91),('intro','intro',91)]+[(f'focus_{code}',f'focus_{code}',frame) for code,frame in zip(data['selection']['codes'],[751,1021,1261])]
for name,group,f in layers:
    if '--always-only' in sys.argv and name!='always':continue
    hud.frame_set(f)
    for o in hud.objects:
        if o.type=='CAMERA':continue
        o.hide_render=o.get('v3_group')!=group
    hud.render.filepath=str(dest/(name+'.png'));bpy.ops.render.render(scene=hud.name,write_still=True)
    print('HUD_CACHE',name,flush=True)
particles=[{'xy':list(o.location)[:2],'radius':float(o.data.vertices[0].co.x)} for o in hud.objects if o.name.startswith('V3_REGION_SPARK_')]
(dest/'particles.json').write_text(json.dumps(particles),encoding='utf-8')
manifest={'sourceBlendSha256':sha256(Path(bpy.data.filepath)),'config':CFG,'layers':{name:sha256(dest/name) for name in [x[0]+'.png' for x in layers]+['particles.json']}}
(dest/'hud-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('HUD_CACHE_COMPLETE',flush=True)
