"""Produce separate editable-text and packed-preview copies without altering render source."""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];hud=bpy.data.scenes['HUD'];geo=bpy.data.scenes['GEO_WORLD']
for s in bpy.data.scenes:bpy.context.window.scene=s;s.frame_set(91)
bpy.context.window.scene=geo
preview=bpy.data.images.load(str(ROOT/'previews/frame-0091.png'));preview.name='南京 · 图文城市概览';preview.pack()
window=bpy.context.window;window.workspace=bpy.data.workspaces.get('Rendering') or window.workspace
areas=[a for a in window.screen.areas if a.type=='IMAGE_EDITOR']
if not areas:
    area=max(window.screen.areas,key=lambda a:a.width*a.height);area.type='IMAGE_EDITOR';areas=[area]
for area in areas:
    area.spaces.active.image=preview
    region=next((r for r in area.regions if r.type=='WINDOW'),None)
    if region:
        with bpy.context.temp_override(window=window,area=area,region=region):bpy.ops.image.view_all(fit_view=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'build/nanjing-v3-review.blend'))
count=0
for ob in list(hud.objects):
    key=ob.get('editable_text_data')
    if not key:continue
    curve=bpy.data.curves[key].copy();replacement=bpy.data.objects.new(ob.name+'_text',curve)
    replacement.matrix_world=ob.matrix_world.copy();replacement.hide_render=ob.hide_render
    if ob.animation_data:
        replacement.animation_data_create();replacement.animation_data.action=ob.animation_data.action;replacement.animation_data.action_slot=ob.animation_data.action_slot
    for prop in ob.keys():replacement[prop]=ob[prop]
    name=ob.name;hud.collection.objects.link(replacement);bpy.data.objects.remove(ob,do_unlink=True);replacement.name=name;count+=1
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'build/nanjing-v3-editable.blend'))
print('V3_REVIEW_AND_EDITABLE_SAVED',count,flush=True)
