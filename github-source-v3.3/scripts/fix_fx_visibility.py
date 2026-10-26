"""Cull distant globe FX when their opacity reaches zero in the city segment."""
import bpy
from pathlib import Path
root=Path(__file__).resolve().parents[1];geo=bpy.data.scenes['GEO_WORLD']
count=0
for ob in geo.objects:
    if ob.name.startswith(('V3_ORBIT_','V3_HERO_','V3_TAIL_','V3_SPECK_')):
        for f,hidden in [(1,False),(361,True),(1621,False),(1801,False)]:
            ob.hide_render=hidden;ob.keyframe_insert('hide_render',frame=f)
        count+=1
for scene in bpy.data.scenes:bpy.context.window.scene=scene;scene.frame_set(751)
bpy.context.window.scene=geo
bpy.ops.wm.save_as_mainfile(filepath=str(root/'build/nanjing-v3.blend'))
print('WORLD_FX_CULLED_IN_CITY',count,flush=True)
