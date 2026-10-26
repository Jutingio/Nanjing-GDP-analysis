"""Build Nanjing intro and three districts from the preserved V1 globe/camera."""
import bpy,sys,json,math,random,hashlib,time
from pathlib import Path
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_config import script_config,input_path,output_path,read_json,validate_inputs,camera_samples,input_fingerprints,validate_scene_config,validate_hud_cache,validate_particle_sequence,sha256
CFG=script_config()
import core
validate_inputs(CFG)
if Path(bpy.data.filepath).resolve()!=input_path(CFG,'base_blend'):
    bpy.ops.wm.open_mainfile(filepath=str(input_path(CFG,'base_blend')),load_ui=False,use_scripts=False)
output_path(CFG,'build').mkdir(parents=True,exist_ok=True)
from v3_core import stage,validate_snapshot,share_pct
DATA=json.loads((input_path(CFG,'snapshot')).read_text(encoding='utf-8'));validate_snapshot(DATA)
CULTURE=json.loads((input_path(CFG,'culture')).read_text(encoding='utf-8'))
G=json.loads((input_path(CFG,'prepared_geo')).read_text(encoding='utf-8'))
EN=CULTURE.get('uiLanguage')=='en'
def tr(text):
    return {'城市概览':'City overview','历史沿革':'History','著名景点':'Sights','区域定位':'Region location'}.get(text,text) if EN else text
SELECTED=DATA['selection']['codes'];ROWS={r['code']:r for r in DATA['regions']}
geo=bpy.data.scenes['GEO_WORLD'];bpy.context.window.scene=geo

def baseline():
    result={'camera':[],'earth':{}}
    for f in [1,91,181,361,541,751,1381,1681,1801]:
        geo.frame_set(f);c=geo.camera
        result['camera'].append([f,list(c.location),list(c.rotation_quaternion),c.data.lens,c.data.clip_start,c.data.clip_end])
    for name in ['EARTH','EARTH_LOCAL_REFINEMENT']:
        ob=bpy.data.objects[name]
        result['earth'][name]={'vertices':len(ob.data.vertices),'polygons':len(ob.data.polygons),'location':list(ob.location),'materials':[m.name for m in ob.data.materials]}
    return result
source_baseline=baseline()
# Preserve mode checks all frames against the external camera record.
samples=camera_samples(CFG)
camera=geo.camera
if camera.constraints:raise ValueError('Camera constraints need a city-specific adapter')
if CFG['camera']['mode']=='preserve':
    for sample in samples:
        geo.frame_set(sample['frame'])
        actual=[*camera.location,*camera.rotation_quaternion,camera.data.lens,camera.data.clip_start,camera.data.clip_end]
        expected=[*sample['location'],*sample['rotation_quaternion'],sample['lens'],sample['clip_start'],sample['clip_end']]
        if any(abs(a-b)>1e-5 for a,b in zip(actual,expected)):raise ValueError('Camera track does not match base scene')
else:
    camera.animation_data_clear();camera.data.animation_data_clear();camera.rotation_mode='QUATERNION'
    for sample in samples:
        frame=sample['frame']
        for key in ['location','rotation_quaternion']:
            setattr(camera,key,sample[key]);camera.keyframe_insert(key,frame=frame)
        for key in ['lens','clip_start','clip_end']:
            setattr(camera.data,key,sample[key]);camera.data.keyframe_insert(key,frame=frame)
before=baseline()
for d in G['districts']:
    ob=bpy.data.objects.get('district_'+d['code'])
    if ob is None or len(ob.data.vertices)!=len(d['vertices']):raise ValueError('Base scene geometry mismatch: '+d['code'])
    if any((v.co-Vector(p)).length>0.001 for v,p in zip(ob.data.vertices,d['vertices'])):raise ValueError('Base scene coordinates mismatch: '+d['code'])
earth_image=bpy.data.images.load(str(input_path(CFG,'earth_texture')),check_existing=False);earth_image.pack()
for obname in ['EARTH','EARTH_LOCAL_REFINEMENT']:
    for material in bpy.data.objects[obname].data.materials:
        if material.node_tree:
            for node in material.node_tree.nodes:
                if node.type=='TEX_IMAGE':node.image=earth_image

for name in ['HUD','PANEL_MASK']:
    if name in bpy.data.scenes:
        s=bpy.data.scenes[name]
        for ob in list(s.objects):bpy.data.objects.remove(ob,do_unlink=True)
        bpy.data.scenes.remove(s)
hud=bpy.data.scenes.new('HUD');mask=bpy.data.scenes.new('PANEL_MASK')
for s in [hud,mask]:
    s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
    s.render.fps=30;s.frame_start=1;s.frame_end=1800;s.render.film_transparent=True;s.render.use_motion_blur=False
    s.view_settings.view_transform='Standard';s.view_settings.look='None';s.eevee.taa_render_samples=CFG['render']['hud_samples']
    s.eevee.use_raytracing=False;s.eevee.use_shadows=False
    cam=bpy.data.objects.new('V3_CAM_'+s.name,bpy.data.cameras.new('V3_CAM_'+s.name));s.collection.objects.link(cam);s.camera=cam
    cam.data.type='ORTHO';cam.data.ortho_scale=1920;cam.data.clip_start=.1;cam.data.clip_end=5000;cam.location=(960,540,2000)

def rgba(h):
    nums=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in nums)+(1,)
tracks=[];mats={};nodecolors=[];objects_by_group={}
def mat(color,group='always',alpha=1,energy=1):
    key=(color,group,alpha,energy)
    if key in mats:return mats[key]
    m=bpy.data.materials.new('V3_'+group+'_'+color+'_'+str(alpha));m.use_nodes=True
    n=m.node_tree.nodes;n.clear();l=m.node_tree.links
    out=n.new('ShaderNodeOutputMaterial');e=n.new('ShaderNodeEmission');e.inputs[0].default_value=rgba(color);e.inputs[1].default_value=energy
    tr=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');mix.inputs[0].default_value=alpha
    l.new(tr.outputs[0],mix.inputs[1]);l.new(e.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs[0])
    m.surface_render_method='BLENDED';m.use_transparency_overlap=False
    if group!='always':tracks.append((mix.inputs[0],group,alpha))
    mats[key]=m;return m
def mesh(name,verts,faces,m,scene=hud,group='always'):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();me.materials.append(m)
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);ob['v3_group']=group
    objects_by_group.setdefault(group,[]).append(ob);return ob
def poly(name,pts,m,z=0,scene=hud,group='always'):
    return mesh(name,[(x,1080-y,z) for x,y in pts],[tuple(range(len(pts)))],m,scene,group)
def rect(name,x,y,w,h,m,z=0,scene=hud,group='always'):
    return poly(name,[(x,y),(x+w,y),(x+w,y+h),(x,y+h)],m,z,scene,group)
def line2(name,pts,width,m,z=4,group='always'):
    verts=[];faces=[]
    for (x,y),(xx,yy) in zip(pts,pts[1:]):
        dx,dy=xx-x,yy-y;norm=max(.001,math.hypot(dx,dy));a,b=-dy/norm*width/2,dx/norm*width/2
        k=len(verts);verts.extend([(x+a,1080-y-b,z),(xx+a,1080-yy-b,z),(xx-a,1080-yy+b,z),(x-a,1080-y+b,z)]);faces.append((k,k+1,k+2,k+3))
    return mesh(name,verts,faces,m,hud,group)
def dot(name,x,y,r,m,z=5,group='always'):
    return poly(name,[(x+math.cos(i*math.tau/20)*r,y+math.sin(i*math.tau/20)*r) for i in range(20)],m,z,group=group)

builtin_font=input_path(CFG,'font').suffix=='.json' and read_json(input_path(CFG,'font')).get('type')=='blender_builtin'
font=bpy.data.fonts.get('Bfont') if builtin_font else bpy.data.fonts.load(str(input_path(CFG,'font')))
if font is None:
    temporary=bpy.data.curves.new('FONT_BOOTSTRAP','FONT');font=temporary.font;bpy.data.curves.remove(temporary)
if not builtin_font:font.pack()
bpy.context.window.scene=hud
cal=bpy.data.curves.new('V3_FONT_CALIBRATION','FONT');cal.body='H' if builtin_font else '南京';cal.font=font;cal.size=1;cal.resolution_u=10
co=bpy.data.objects.new('V3_FONT_CALIBRATION',cal);hud.collection.objects.link(co);bpy.context.view_layer.update()
bb=[v[1] for v in co.bound_box];unit=max(bb)-min(bb);base=min(bb)
if unit<=0:raise RuntimeError('Font metrics unavailable')
bpy.data.objects.remove(co,do_unlink=True)
print('FONT_METRICS',unit,base,flush=True)
def txt(name,body,x,top,size,color='EAF8FF',group='always',align='LEFT'):
    c=bpy.data.curves.new(name,'FONT');c.body=tr(body);c.font=font;c.size=size/unit;c.align_x=align;c.align_y='BOTTOM_BASELINE';c.resolution_u=10
    c.materials.append(mat(color,group));c.space_character=1.0
    ob=bpy.data.objects.new(name,c);hud.collection.objects.link(ob)
    ob.location=(x,1080-top-size-base*c.size,12);ob['text']=tr(body);ob['v3_group']=group;ob['font_px']=size
    objects_by_group.setdefault(group,[]).append(ob);return ob

def panel(name,x,y,w,h,group):
    shape=[(x+14,y),(x+w-28,y),(x+w,y+28),(x+w,y+h-14),(x+w-14,y+h),(x,y+h),(x,y+14)]
    poly(name+'_MASK',shape,mat('FFFFFF',group),0,mask,group)
    poly(name+'_GLASS',shape,mat('0B314A',group,.38),0,group=group)
    rect(name+'_TITLE_WASH',x+2,y+2,w-30,66,mat('206382',group,.11),.5,group=group)
    rect(name+'_READING_WASH',x+18,y+84,w-36,h-104,mat('04111F',group,.13),.6,group=group)
    line2(name+'_OUTLINE',shape+[shape[0]],1.6,mat('53B6CF',group,.62),2,group)
    line2(name+'_INNER',[(x+8,y+20),(x+8,y+h-8),(x+w-24,y+h-8)],.7,mat('6DE7FF',group,.24),3,group)
    line2(name+'_CORNER',[(x,y+72),(x,y+14),(x+14,y),(x+76,y)],2.8,mat('67E4FA',group,.9),4,group)
    line2(name+'_TOP_SHORT',[(x+w-146,y),(x+w-28,y),(x+w,y+28)],2,mat('238BFF',group,.9),4,group)
    line2(name+'_TITLE_RULE',[(x+24,y+72),(x+w-24,y+72)],.8,mat('40D9F3',group,.32),3,group)
    for i in range(12):
        for j in range(3):dot(name+f'_TEXTURE_{i}_{j}',x+w-70+i*4,y+h-50+j*7,0.8,mat('78E7FF',group,.16),3,group)
    for k in range(9):rect(name+'_TICK_'+str(k),x+26+k*12,y+h-14,6,1.1,mat('67E4FA',group,.3),3,group=group)

panel('V3_TITLE_PANEL',60,38,280,124,'always')
txt('V3_TITLE',CFG['city']['name'],84,54,50)
txt('V3_KICKER',CFG['city']['kicker'],84,128,16,'8CC5DB')
line2('V3_TITLE_ACCENT',[(72,176),(148,176)],3,mat('40D9F3'))
line2('V3_HEADER_RULE',[(166,176),(1848,176)],.7,mat('366A82',alpha=.5))
txt('V3_YEAR',('Year ' if EN else '统计年度 ')+CFG['city']['period'],1848,76,25,'A9C8D7',align='RIGHT')
txt('V3_FOOTER',CFG['credits']['footer'],72,982,19,'8DADBD')
txt('V3_CREDITS',CFG['credits']['assets'],72,1013,17,'7695A9')
line2('V3_FOOT_RULE',[(72,958),(1848,958)],.8,mat('366A82',alpha=.45))

panel('V3_CITY_PANEL',72,214,550,710,'intro')
txt('V3_CITY_HEAD','城市概览',98,237,27,'C4EFF7','intro')
photo=bpy.data.images.load(str(input_path(CFG,'photo')));photo.pack()
photo_mat=mat('FFFFFF','intro',1)
texture=photo_mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=photo
photo_mat.node_tree.links.new(texture.outputs['Color'],next(n for n in photo_mat.node_tree.nodes if n.type=='EMISSION').inputs[0])
photo_ob=rect('V3_CITY_PHOTO',98,298,498,250,photo_mat,5,group='intro')
photo_ob['source_file']=CFG['paths']['photo'];photo_ob['image_year']=CULTURE['photo']['capturedOn'][:4]
uv=photo_ob.data.uv_layers.new(name='PhotoUV');span=(photo.size[0]/photo.size[1])/(498/250)
for loop,value in zip(photo_ob.data.loops,[(0,1),(1,1),(1,1-span),(0,1-span)]):uv.data[loop.index].uv=value
rect('V3_PHOTO_CAPTION_BG',98,516,498,32,mat('04111F','intro',.68),6,group='intro')
txt('V3_PHOTO_CAPTION',CULTURE['photo']['caption'],110,523,18,'D8F1F7','intro')
txt('V3_HISTORY_HEAD','历史沿革',98,571,26,'6AE5FA','intro')
for i,row in enumerate(CULTURE['history']):
    y=612+i*34
    txt('V3_HISTORY_YEAR_'+str(i),row['year'],98,y,24,'C4EFF7','intro')
    txt('V3_HISTORY_BODY_'+str(i),row['text'],194,y,23,'D8F1F7','intro')
line2('V3_HISTORY_RULE',[(98,721),(596,721)],.7,mat('50BFDE','intro',.28),3,'intro')
txt('V3_SIGHTS_HEAD','著名景点',98,737,26,'6AE5FA','intro')
for i,row in enumerate(CULTURE['sights']):
    y=779+i*35
    txt('V3_SIGHT_NAME_'+str(i),row['name'],98,y,23,'D8F1F7','intro')
    txt('V3_SIGHT_BODY_'+str(i),row['text'],270,y,21,'A9C8D7','intro')
labels={'gdp':'地区生产总值','resident_population':'年末常住人口','retail_sales':'社会消费品零售总额'}
units={'gdp':'亿元','resident_population':'万人','retail_sales':'亿元'}
if EN:
    labels={'gdp':'GDP','resident_population':'Population','retail_sales':'Retail sales'}
    units={'gdp':'source units','resident_population':'source units','retail_sales':'source units'}

bpy.context.window.scene=geo;geo.frame_set(751)
for code in SELECTED:
    idx=SELECTED.index(code);group='focus_'+code;row=ROWS[code]
    panel('V3_DISTRICT_PANEL_'+code,1288,310,560,440,group)
    txt('V3_DISTRICT_HEADER_'+code,('Share of '+CFG['city']['name']+' / ' if EN else '占'+CFG['city']['name']+'市比重 / ')+CFG['city']['period'],1312,332,25,'C4EFF7',group)
    txt('V3_DISTRICT_NUMBER_'+code,f'0{idx+1}',1312,420,20,'55D8F1',group)
    txt('V3_NAME_'+code+'_0',row['name'],1312,474,26,'EAF8FF',group)
    txt('V3_DISTRICT_TAG_'+code,'区域定位',1312,620,18,'7FB3C8',group)
    line2('V3_NAME_DIVIDER_'+code,[(1434,406),(1434,705)],.7,mat('50BFDE',group,.33),3,group)
    for i,k in enumerate(labels):
        y=405+i*102;percentage=share_pct(row['values'][k],DATA['cityTotals'][k]['value'])
        txt('V3_METRIC_'+code+'_'+k,labels[k],1458,y,20,'A9C8D7',group)
        txt('V3_PERCENT_'+code+'_'+k,f'{percentage:.2f}%',1824,y+3,27,'6AE5FA',group,align='RIGHT')
        rect('V3_BAR_TRACK_'+code+'_'+k,1458,y+43,366,10,mat('28617C',group,.5),4,group=group)
        bar=rect('V3_BAR_VALUE_'+code+'_'+k,1458,y+43,366*percentage/100,10,mat('47DDF3',group),5,group=group)
        bar['share_pct']=percentage;bar['track_width']=366;bar['metric_id']=k;bar['district_code']=code
        txt('V3_RAW_'+code+'_'+k,f"{row['values'][k]:,.2f} {units[k]}",1458,y+66,20,'9DC1D0',group)
    txt('V3_SCALE_ZERO_'+code,'0%',1458,722,15,'73A6BB',group)
    txt('V3_SCALE_FULL_'+code,'100%',1824,722,15,'73A6BB',group,align='RIGHT')
    d=next(d for d in G['districts'] if d['code']==code)
    p=world_to_camera_view(geo,geo.camera,Vector(d['anchor']));x,y=p.x*1920,1080-p.y*1080
    route=[(x,y),(1218,y),(1256,498),(1288,498),(1300,498)]
    line2('V3_LEADER_GLOW_'+code,route,5,mat('238BFF',group,.1),5,group)
    line2('V3_LEADER_'+code,route,1.8,mat('57DFF5',group,.85),6,group)
    dot('V3_PIN_'+code,x,y,3,mat('9AEDFF',group),7,group)
    line2('V3_PIN_RING_'+code,[(x+math.cos(i*math.tau/40)*10,y+math.sin(i*math.tau/40)*10) for i in range(41)],1,mat('3ACAF1',group,.7),6,group)

# Replace only administrative presentation materials, keeping globe and camera intact.
for d in G['districts']:
    code=d['code'];ob=bpy.data.objects['district_'+code]
    m=mat('113B53','region_'+code,1);ob.data.materials.clear();ob.data.materials.append(m)
    emission=next(n for n in m.node_tree.nodes if n.type=='EMISSION')
    nodecolors.append((emission.inputs['Color'],code))
    for o in geo.objects:
        if o.name.startswith('boundary_'+code+'_'):
            o.data.materials.clear();o.data.materials.append(mat('4BA2BD','region',.46))
            o.data.bevel_depth=.11
for o in geo.objects:
    if o.name.startswith('NANJING_CITY_'):
        o.data.materials.clear();o.data.materials.append(mat('5DE0F0','region',.8));o.data.bevel_depth=.16
    if o.name.startswith(('district_','boundary_','NANJING_CITY_','YANGTZE_')):
        o.location.z=CFG['geometry']['presentationOffsetM']/1000;o['presentation_offset_m']=CFG['geometry']['presentationOffsetM']

# Spatial light orbits. Parent rotations are analytic integer turns over 60 seconds.
bpy.context.window.scene=geo;geo.frame_set(91)
C=Vector(bpy.data.objects['EARTH'].location);R=6378.137
view=(geo.camera.location-C).normalized();right=geo.camera.rotation_quaternion@Vector((1,0,0));up=view.cross(right).normalized()
def empty(name,parent=None):
    o=bpy.data.objects.new(name,None);geo.collection.objects.link(o)
    if parent:o.parent=parent
    return o
def line3(name,points,width,m,parent):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=1;c.bevel_depth=width;c.bevel_resolution=1
    sp=c.splines.new('POLY');sp.points.add(len(points)-1)
    for p,v in zip(sp.points,points):p.co=(*v,1)
    c.materials.append(m);o=bpy.data.objects.new(name,c);geo.collection.objects.link(o);o.parent=parent;return o
octverts=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
octfaces=[(0,2,4),(2,1,4),(1,3,4),(3,0,4),(2,0,5),(1,2,5),(3,1,5),(0,3,5)]
particle_meshes={}
def particle(name,position,size,m,parent):
    if m.name not in particle_meshes:
        me=bpy.data.meshes.new('V3_PARTICLE_'+m.name);me.from_pydata(octverts,[],octfaces);me.materials.append(m);particle_meshes[m.name]=me
    o=bpy.data.objects.new(name,particle_meshes[m.name]);geo.collection.objects.link(o);o.parent=parent;o.location=position;o.scale=(size,)*3;return o
for k,tilt in enumerate([1.08,-.9]):
    root=empty('V3_ORBIT_PLANE_'+str(k));root.location=C
    e1=(right*math.cos(k*.55)+up*math.sin(k*.55)).normalized()
    vv=view.cross(e1).normalized();e2=(vv*math.cos(tilt)+view*math.sin(tilt)).normalized();normal=e1.cross(e2).normalized()
    root.rotation_mode='QUATERNION';root.rotation_quaternion=Matrix((e1,e2,normal)).transposed().to_quaternion()
    rotor=empty('V3_ORBIT_SPIN_'+str(k),root)
    rotor.rotation_euler.z=0;rotor.keyframe_insert('rotation_euler',frame=1)
    rotor.rotation_euler.z=math.tau*(1 if k==0 else -1);rotor.keyframe_insert('rotation_euler',frame=1801)
    radius=R*(1.2+k*.14)
    for j,(a,b) in enumerate([(.15,2.1),(3.1,5.8)]):
        points=[(radius*math.cos(a+(b-a)*i/100),radius*math.sin(a+(b-a)*i/100),0) for i in range(101)]
        line3(f'V3_ORBIT_{k}_{j}',points,7,mat('238BFF','orbit',.62,2.4),rotor)
    for j in range(6):
        angle=j*math.tau/6+k*.31
        particle(f'V3_HERO_{k}_{j}',(radius*math.cos(angle),radius*math.sin(angle),0),38,mat('85EFFF','orbit',1,3.6),rotor)
        for tail in range(8):
            a=angle-.016*(tail+1)
            particle(f'V3_TAIL_{k}_{j}_{tail}',(radius*math.cos(a),radius*math.sin(a),0),max(8,25-tail*2),mat('40D9F3','orbit',(1-tail/9)*.8,2.4),rotor)
    rng=random.Random(450+k)
    for j in range(110):
        a=rng.uniform(0,math.tau);r=radius+rng.uniform(-R*.11,R*.17);z=rng.uniform(-R*.06,R*.06)
        particle(f'V3_SPECK_{k}_{j}',(r*math.cos(a),r*math.sin(a),z),rng.uniform(5,16),mat('32B6EC','orbit',.65,2.2),rotor)

# Decorative regional particles, behind the HUD glass, without implying geolocated data.
region_root=bpy.data.objects.new('V3_REGION_PARTICLE_ROOT',None);hud.collection.objects.link(region_root);region_root.location=(1000,540,-12);region_root.scale=(1,.72,1)
region_spin=bpy.data.objects.new('V3_REGION_PARTICLE_SPIN',None);hud.collection.objects.link(region_spin);region_spin.parent=region_root
region_spin.rotation_euler.z=0;region_spin.keyframe_insert('rotation_euler',frame=1)
region_spin.rotation_euler.z=math.tau;region_spin.keyframe_insert('rotation_euler',frame=1801)
rng=random.Random(805)
for j in range(48):
    ang=rng.uniform(0,math.tau);radius=rng.uniform(330,590);size=rng.uniform(.8,1.6)
    pts=[(math.cos(k*math.tau/12)*size,math.sin(k*math.tau/12)*size,0) for k in range(12)]
    o=mesh('V3_REGION_SPARK_'+str(j),pts,[tuple(range(12))],mat('57C8E7','region',.38),hud,'region')
    o.parent=region_spin;o.location=(radius*math.cos(ang),radius*math.sin(ang),0)

# Compositor: effect-only highlights, local world blur through panel masks, sharp HUD last.
ng=bpy.data.node_groups.new('V3_COMPOSITE','CompositorNodeTree');ng.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor');geo.compositing_node_group=ng
n=ng.nodes;l=ng.links
world=n.new('CompositorNodeRLayers');world.scene=geo
glare=n.new('CompositorNodeGlare');glare.inputs['Type'].default_value='Fog Glow';glare.inputs['Threshold'].default_value=1.25;glare.inputs['Size'].default_value=.25;glare.inputs['Strength'].default_value=.55
l.new(world.outputs['Image'],glare.inputs['Image'])
bl=n.new('CompositorNodeBlur');bl.inputs['Size'].default_value=(8,8);l.new(glare.outputs['Image'],bl.inputs['Image'])
ms=n.new('CompositorNodeRLayers');ms.scene=mask
mix=n.new('ShaderNodeMix');mix.data_type='RGBA';l.new(ms.outputs['Alpha'],mix.inputs[0]);l.new(glare.outputs['Image'],mix.inputs[6]);l.new(bl.outputs['Image'],mix.inputs[7])
hr=n.new('CompositorNodeRLayers');hr.scene=hud
over=n.new('CompositorNodeAlphaOver');over.inputs['Factor'].default_value=1;l.new(mix.outputs[2],over.inputs['Background']);l.new(hr.outputs['Image'],over.inputs['Foreground'])
out=n.new('NodeGroupOutput');l.new(over.outputs['Image'],out.inputs[0])

print('BAKING',len(tracks),'material channels',flush=True)
for frame in range(1,1802):
    t=(frame-1)/30;st=stage(t,SELECTED)
    for socket,group,alpha in tracks:
        v=st['detail'] if group=='focus_'+str(st['focus']) else (0 if group.startswith('focus_') else st['region'] if group.startswith('region') else st.get(group,1))
        socket.default_value=v*alpha;socket.keyframe_insert('default_value',frame=frame)
    for socket,code in nodecolors:
        f=st['detail'] if st['focus']==code else 0
        c1=rgba('113B53');c2=rgba('38C3DB');socket.default_value=tuple(a+(b-a)*f for a,b in zip(c1,c2));socket.keyframe_insert('default_value',frame=frame)
for group,objs in objects_by_group.items():
    if group in ['always'] or group.startswith('region'):continue
    spans={'intro':[(1,False),(301,True)],'focus_'+SELECTED[0]:[(1,True),(631,False),(901,True)],'focus_'+SELECTED[1]:[(1,True),(901,False),(1141,True)],'focus_'+SELECTED[2]:[(1,True),(1141,False),(1381,True)]}
    if group in spans:
        for o in objs:
            for f,hidden in spans[group]:o.hide_render=hidden;o.keyframe_insert('hide_render',frame=f)

# Skip fully faded globe effects during the city segment to avoid unnecessary depth work.
for ob in geo.objects:
    if ob.name.startswith(('V3_ORBIT_','V3_HERO_','V3_TAIL_','V3_SPECK_')):
        for f,hidden in [(1,False),(361,True),(1621,False),(1801,False)]:
            ob.hide_render=hidden;ob.keyframe_insert('hide_render',frame=f)

# High-resolution cached contours preserve editable source text without slow live font evaluation.
bpy.context.window.scene=hud;hud.frame_set(751);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
for ob in list(hud.objects):
    if ob.type!='FONT':continue
    source=ob.data;source.use_fake_user=True
    cached=bpy.data.meshes.new_from_object(ob.evaluated_get(deps),depsgraph=deps)
    new=bpy.data.objects.new(ob.name+'_cache',cached);hud.collection.objects.link(new);new.matrix_world=ob.matrix_world.copy();new.hide_render=ob.hide_render
    for key in ob.keys():new[key]=ob[key]
    if ob.animation_data:
        new.animation_data_create();new.animation_data.action=ob.animation_data.action;new.animation_data.action_slot=ob.animation_data.action_slot
    new['editable_text_data']=source.name
    name=ob.name;bpy.data.objects.remove(ob,do_unlink=True);new.name=name
for action in bpy.data.actions:
    if not action.name.startswith('V3_'):continue
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='CONSTANT' if 'hide_' in fc.data_path else 'LINEAR'
bpy.context.window.scene=geo
after=baseline()
if before!=after:raise RuntimeError('Globe or camera preservation check failed')
geo['v3_data_period']=CFG['city']['period'];geo['v3_selected']=json.dumps(SELECTED);geo['v3_preview_duration']=60
geo['v3_spec']='NANJING-UI-UX-V3.2-SPEC.md'
for s in [geo,hud,mask]:bpy.context.window.scene=s;s.frame_set(751)
bpy.context.window.scene=geo
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
output_path(CFG,'config-used.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
geo['project_config']=json.dumps(CFG,ensure_ascii=False)
geo['project_inputs']=json.dumps(input_fingerprints(CFG),sort_keys=True)
bpy.ops.wm.save_as_mainfile(filepath=str(output_path(CFG,'build/nanjing-v3.blend')))
(output_path(CFG,'build/preservation-check.json')).write_text(json.dumps({'passed':True,'blendSha256':sha256(output_path(CFG,'build/nanjing-v3.blend')),'baseline':before,'dataSha256':hashlib.sha256((input_path(CFG,'snapshot')).read_bytes()).hexdigest()},indent=2),encoding='utf-8')
print('V3_BUILD_COMPLETE',flush=True)
