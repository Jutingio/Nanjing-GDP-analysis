"""Generate the V3 base contract for another city; preserves existing Nanjing files."""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_config import script_config,input_path,read_json,sha256,output_path
from city_geometry import LocalFrame,camera_state
import core

# Keep the config's pathname before script_config consumes its argument.
config_arg=sys.argv[sys.argv.index('--config')+1] if '--config' in sys.argv else None
if config_arg is None:raise ValueError('Explicit --config is required for city adaptation')
config_file=Path(config_arg);config_file=config_file if config_file.is_absolute() else ROOT/config_file
cfg=script_config()
if cfg['city']['id']=='nanjing':raise ValueError('Use the preserved Nanjing workflow for the original film')
dest=input_path(cfg,'base_blend');track_path=input_path(cfg,'camera_track')
if dest.exists() or track_path.exists():raise FileExistsError('Base/track already exists; select new paths instead of replacing originals')
g=read_json(input_path(cfg,'prepared_geo'))
for key in ['originLonLat','sceneUnit','boundaryYear']:
    if g['project'][key]!=cfg['geometry'][key]:raise ValueError('Geometry/config mismatch: '+key)
local=LocalFrame(*cfg['geometry']['originLonLat'])
bpy.ops.wm.read_factory_settings(use_empty=True)
geo=bpy.context.scene;geo.name='GEO_WORLD';geo.render.engine='BLENDER_EEVEE'
geo.render.resolution_x=1920;geo.render.resolution_y=1080;geo.render.resolution_percentage=100
geo.render.fps=30;geo.frame_start=1;geo.frame_end=1800
geo.eevee.taa_render_samples=cfg['render']['samples'];geo.eevee.use_raytracing=False;geo.eevee.use_shadows=False
geo.view_settings.view_transform='Standard';geo.view_settings.look='None'
world=bpy.data.worlds.new('CITY_WORLD');world.use_nodes=True;geo.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.0015,.006,.018,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.3

def rgb(color):
    a=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in a)+(1,)

alpha=[]
def material(name,color,fade=True):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.surface_render_method='BLENDED';m.use_transparency_overlap=False
    n=m.node_tree.nodes;n.clear();links=m.node_tree.links
    out=n.new('ShaderNodeOutputMaterial');em=n.new('ShaderNodeEmission');em.inputs[0].default_value=rgb(color)
    transparent=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');mix.inputs[0].default_value=1
    links.new(transparent.outputs[0],mix.inputs[1]);links.new(em.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],out.inputs[0])
    if fade:alpha.append(mix.inputs[0])
    return m,em

def mesh(name,vertices,faces,mat):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update();data.materials.append(mat)
    ob=bpy.data.objects.new(name,data);geo.collection.objects.link(ob);return ob

earth_material,em=material('EARTH_CITY_ADAPTER','FFFFFF',False)
texture=earth_material.node_tree.nodes.new('ShaderNodeTexImage')
texture.image=bpy.data.images.load(str(input_path(cfg,'earth_texture')));texture.image.pack()
earth_material.node_tree.links.new(texture.outputs['Color'],em.inputs[0])
earth_center=Vector(tuple(-v/1000 for v in local.rotate(local.origin)))
def globe(name,lons,lats):
    vertices=[];uv=[];faces=[];ny=len(lats)
    for lon in lons:
        for lat in lats:
            vertices.append(tuple(v/1000 for v in local.rotate(core.geodetic_to_ecef(lon,lat))))
            uv.append(((lon+180)/360,(lat+90)/180))
    for i in range(len(lons)-1):
        for j in range(ny-1):
            k=i*ny+j;faces.append((k,k+ny,k+ny+1,k+1))
    ob=mesh(name,vertices,faces,earth_material);ob.location=earth_center
    layer=ob.data.uv_layers.new(name='GeographicUV')
    for polygon in ob.data.polygons:
        polygon.use_smooth=True
        for loop in polygon.loop_indices:layer.data[loop].uv=uv[ob.data.loops[loop].vertex_index]
    return ob

globe('EARTH',[-180+i*360/384 for i in range(385)],[-90+j*180/192 for j in range(193)])
w,s,e,n=g['bounds'];w=max(-180,w-.4);e=min(180,e+.4);s=max(-89,s-.4);n=min(89,n+.4)
globe('EARTH_LOCAL_REFINEMENT',[w+(e-w)*i/100 for i in range(101)],[s+(n-s)*j/100 for j in range(101)])
camera=bpy.data.objects.new('CAM_MAIN',bpy.data.cameras.new('CAM_MAIN'));geo.collection.objects.link(camera);geo.camera=camera
camera.rotation_mode='QUATERNION';camera.data.sensor_fit='VERTICAL';camera.data.sensor_height=24
camera.data.lens=12/math.tan(math.radians(22.5));camera.data.clip_start=.05;camera.data.clip_end=60000

def pose(state):
    target=Vector(local.to_scene(state['lon'],state['lat']))
    east,north,up=[Vector(local.rotate(row)) for row in core.basis(state['lon'],state['lat'])]
    h,p=math.radians(state['heading']),math.radians(state['pitch'])
    forward=(east*math.sin(h)+north*math.cos(h))*math.cos(p)+up*math.sin(p)
    right=east*math.cos(h)-north*math.sin(h);up=right.cross(forward).normalized()
    camera.location=target-forward*state['range_m']/1000
    camera.rotation_quaternion=Matrix((right,up,-forward)).transposed().to_quaternion()

fit=80000
all_vertices=[v for d in g['districts'] for v in d['vertices']]
for attempt in range(200):
    pose(camera_state(25,g['center'],fit));bpy.context.view_layer.update()
    points=[world_to_camera_view(geo,camera,Vector(v)) for v in all_vertices]
    if all(.25<p.x<.65 and .18<p.y<.79 and p.z>0 for p in points):break
    fit*=1.05
else:raise ValueError('Cannot fit compact city within the existing HUD; check geometry')
fit*=1.04
line_material,_=material('CITY_BOUNDARY','4BA2BD')
def line(name,points,width):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.bevel_depth=width;curve.bevel_resolution=1
    spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
    for point,xyz in zip(spline.points,points):point.co=(*xyz,1)
    curve.materials.append(line_material);ob=bpy.data.objects.new(name,curve);geo.collection.objects.link(ob)

for d in g['districts']:
    m,_=material('FILL_'+d['code'],'113B53');mesh('district_'+d['code'],d['vertices'],d['faces'],m)
    for i,points in enumerate(d['lines']):line(f"boundary_{d['code']}_{i}",points,.11)
# Object prefixes are retained as compatibility identifiers; no city name is displayed from them.
for i,points in enumerate(g['city_lines']):line('NANJING_CITY_'+str(i),points,.16)
for i,points in enumerate(g['river_lines']):line('YANGTZE_'+str(i),points,.55)
samples=[];previous=None
for frame in range(1,1802):
    t=(frame-1)/30;state=camera_state(t,g['center'],fit);pose(state)
    if previous is not None and camera.rotation_quaternion.dot(previous)<0:camera.rotation_quaternion.negate()
    previous=camera.rotation_quaternion.copy()
    camera.data.clip_start=max(.1,state['range_m']/1000*.05);camera.data.clip_end=state['range_m']/1000+26000
    for key in ['location','rotation_quaternion']:camera.keyframe_insert(key,frame=frame)
    for key in ['clip_start','clip_end']:camera.data.keyframe_insert(key,frame=frame)
    value=core.fade(t,12,18)*(1-core.fade(t,46,53))
    for socket in alpha:socket.default_value=value;socket.keyframe_insert('default_value',frame=frame)
    samples.append({'frame':frame,'location':list(camera.location),'rotation_quaternion':list(camera.rotation_quaternion),
                    'lens':camera.data.lens,'clip_start':camera.data.clip_start,'clip_end':camera.data.clip_end})
for action in bpy.data.actions:
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for point in fc.keyframe_points:point.interpolation='LINEAR'
dest.parent.mkdir(parents=True,exist_ok=True);track_path.parent.mkdir(parents=True,exist_ok=True)
geo.frame_set(751);bpy.ops.wm.save_as_mainfile(filepath=str(dest))
track_path.write_text(json.dumps({'rotation_mode':'QUATERNION','samples':samples}),encoding='utf-8')
cfg['baseSha256']=sha256(dest);cfg['template']=False
config_file.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CITY_BASE_READY',cfg['city']['id'],'fit_m',round(fit),'blender',bpy.app.version_string)
