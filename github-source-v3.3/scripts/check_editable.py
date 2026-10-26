"""Reopen the editable delivery and check fonts, packed media and actual visible labels."""
import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];hud=bpy.data.scenes['HUD']
texts=[ob for ob in hud.objects if ob.type=='FONT']
assert len(texts)>=60
assert all(ob.data.font.packed_file for ob in texts),'A used CJK font is not packed'
assert bpy.data.objects['V3_TITLE'].data.body=='南京'
assert all(any(ob.data.body==name for ob in texts) for name in ['历史沿革','著名景点','雨花台区','玄武区','鼓楼区'])
photo=bpy.data.objects['V3_CITY_PHOTO']
im=next(n.image for n in photo.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE')
assert im.packed_file
visible=[]
for frame,want in [(91,None),(751,'雨花台区'),(1021,'玄武区'),(1261,'鼓楼区'),(1501,None)]:
    bpy.context.window.scene=hud;hud.frame_set(frame)
    names=[]
    for ob in texts:
        if not ob.name.startswith('V3_NAME_') or ob.hide_render:continue
        mix=next(n for n in ob.data.materials[0].node_tree.nodes if n.type=='MIX_SHADER')
        if mix.inputs[0].default_value>.01:names.append(ob.data.body)
    assert names==([] if want is None else [want]),(frame,names)
    visible.append({'frame':frame,'names':names})
report={'passed':True,'editableTextObjects':len(texts),'allUsedFontsPacked':True,'cityPhotoPacked':True,'visibleDistricts':visible,'blendSha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'reopenedFromWorkingDirectory':str(Path.cwd())}
(ROOT/'build/editable-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('EDITABLE_DELIVERY_VERIFIED',len(texts),flush=True)
