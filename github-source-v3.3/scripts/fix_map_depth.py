"""Separate presentation overlays from the ellipsoid; source coordinates are unchanged."""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];geo=bpy.data.scenes['GEO_WORLD'];count=0
for o in geo.objects:
    if o.name.startswith(('district_','boundary_','NANJING_CITY_','YANGTZE_')):
        o.location.z=.15;o['presentation_offset_m']=150;count+=1
for s in bpy.data.scenes:bpy.context.window.scene=s;s.frame_set(751)
bpy.context.window.scene=geo
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'build/nanjing-v3.blend'))
print('MAP_PRESENTATION_OFFSET',count,150,flush=True)
