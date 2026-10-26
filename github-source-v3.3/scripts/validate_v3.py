"""Read a saved V3 scene and validate the user's changed display contract."""
import bpy,sys,json,math,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_config import script_config,input_path,output_path,read_json,validate_inputs,camera_samples,input_fingerprints,validate_scene_config,validate_hud_cache,validate_particle_sequence,sha256
CFG=script_config()
validate_inputs(CFG)
validate_scene_config(bpy.data.scenes['GEO_WORLD'].get('project_config','null'),CFG)
if json.loads(bpy.data.scenes['GEO_WORLD'].get('project_inputs','null'))!=input_fingerprints(CFG):raise ValueError('Scene input fingerprints differ; rebuild')
preservation=read_json(output_path(CFG,'build/preservation-check.json'))
if preservation.get('blendSha256')!=sha256(Path(bpy.data.filepath)):raise ValueError('Preservation report belongs to another scene')
from v3_core import share_pct,stage,validate_snapshot
data=json.loads((input_path(CFG,'snapshot')).read_text(encoding='utf-8'));validate_snapshot(data)
hud=bpy.data.scenes['HUD'];geo=bpy.data.scenes['GEO_WORLD'];checks={}
def active_names(frame):
    bpy.context.window.scene=hud;hud.frame_set(frame)
    result=[]
    for o in hud.objects:
        if not o.name.startswith('V3_NAME_') or not o.get('text') or o.hide_render:continue
        m=o.data.materials[0];mix=next(n for n in m.node_tree.nodes if n.type=='MIX_SHADER')
        if mix.inputs[0].default_value>.01:result.append(o.name)
    return result
assert active_names(601)==[],active_names(601)
assert all(data['selection']['codes'][0] in n for n in active_names(751)) and active_names(751)
checks['intro_has_no_district_names']=True;checks['first_focus_only']=True
for frame,code in zip([751,1021,1261],data['selection']['codes']):
    names=active_names(frame)
    assert len(names)==1 and code in names[0],(frame,names)
checks['each_of_three_districts_shows_alone']=True
assert active_names(1501)==[] and active_names(1801)==[]
checks['no_district_names_on_return']=True
assert bpy.data.objects.get('V3_TITLE_PANEL_GLASS') is not None
assert bpy.data.objects.get('V3_TITLE_PANEL_MASK') is not None
checks['title_has_glass_and_blur_mask']=True
photo=bpy.data.objects['V3_CITY_PHOTO']
im=next(n.image for n in photo.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE')
assert im.packed_file and all(v>0 for v in im.size[:])
assert hashlib.sha256(bytes(im.packed_file.data)).hexdigest()==sha256(input_path(CFG,'photo'))
checks['real_city_photo_is_packed']=True
texts=[o.get('text','') for o in hud.objects]
en=read_json(input_path(CFG,'culture')).get('uiLanguage')=='en'
assert ('History' if en else '历史沿革') in texts and ('Sights' if en else '著名景点') in texts
assert not any('以经济、人口与消费' in t for t in texts)
assert not any(o.name.startswith('V3_CITY_VALUE_') for o in hud.objects)
checks['culture_replaces_economic_intro']=True
bars=[]
rows={r['code']:r for r in data['regions']}
for o in hud.objects:
    if not o.name.startswith('V3_BAR_VALUE_'):continue
    code=o['district_code'];metric=o['metric_id'];want=share_pct(rows[code]['values'][metric],data['cityTotals'][metric]['value'])
    xs=[v.co.x for v in o.data.vertices];actual=(max(xs)-min(xs))/o['track_width']*100
    assert abs(actual-want)<.001,(o.name,actual,want)
    assert min(xs)>=1433.9 and max(xs)<=1824.1
    bars.append({'region':code,'metric':metric,'percentage':want,'mesh_percentage':actual})
checks['all_bars_match_city_share']=len(bars)==9
checks['baseline_preserved']=json.loads((output_path(CFG,'build/preservation-check.json')).read_text())['passed']
positions=[]
for frame in [91,121]:
    bpy.context.window.scene=geo;geo.frame_set(frame);bpy.context.view_layer.update()
    positions.append(list(bpy.data.objects['V3_HERO_0_0'].matrix_world.translation))
assert positions[0]!=positions[1];checks['orbital_particle_moves']=True
positions=[]
for frame in [751,781]:
    bpy.context.window.scene=hud;hud.frame_set(frame);bpy.context.view_layer.update()
    positions.append(list(bpy.data.objects['V3_REGION_SPARK_0'].matrix_world.translation))
assert positions[0]!=positions[1];checks['city_particle_moves']=True
bpy.context.window.scene=geo;geo.frame_set(751)
assert all(o.hide_render for o in geo.objects if o.name.startswith(('V3_HERO_','V3_TAIL_','V3_SPECK_')))
checks['globe_fx_culled_in_city']=True
assert all(abs(o.location.z-CFG['geometry']['presentationOffsetM']/1000)<1e-6 for o in geo.objects if o.name.startswith('district_'))
checks['map_depth_offset_applied']=True
checks['sources_exist']=all((ROOT/s['rawFile']).is_file() for s in data['sources'])
assert all(checks.values()),checks
report={'checks':checks,'bars':bars,'sourceLimitation':('Synthetic example; no official statistical claim' if data.get('dataMode')=='synthetic_example' else 'Source provenance and acquisition limits are recorded in snapshot.sources'),'boundaryYear':CFG['geometry']['boundaryYear'],'stage':'60-second-three-district-review','notTested':['native 4K','onsite playback']}
report['blendSha256']=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
report['dataSha256']=hashlib.sha256((input_path(CFG,'snapshot')).read_bytes()).hexdigest()
report['blenderVersion']=bpy.app.version_string
(output_path(CFG,'build/validation.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('V3_VALIDATION_PASSED',checks,flush=True)
