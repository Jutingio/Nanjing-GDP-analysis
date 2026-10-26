"""Verify the delivered sample and package the reproducible project without frame caches."""
import argparse,hashlib,io,json,sys,unittest,zipfile
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from png_check import valid_png
p=argparse.ArgumentParser();p.add_argument('--job',required=True);a=p.parse_args()
job=Path(a.job);job=job if job.is_absolute() else ROOT/job
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
blend=ROOT/'build/nanjing-v3.blend';settings=read(job/'settings.json')
assert settings['blend_sha256']==sha(blend)
assert settings['renderer_sha256']==sha(ROOT/'scripts/render_layer_cache.py')
scene=read(ROOT/'build/validation.json')
editable=read(ROOT/'build/editable-validation.json')
assert editable['passed'] and editable['blendSha256']==sha(ROOT/'build/nanjing-v3-editable.blend')
assert scene['blendSha256']==sha(blend)
assert scene['dataSha256']==sha(ROOT/'data/snapshot.json')
assert all(scene['checks'].values())
capture=io.StringIO()
result=unittest.TextTestRunner(stream=capture,verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
assert result.wasSuccessful(),capture.getvalue()
hashes=[]
for frame in range(1,1802):
    path=job/'frames'/f'frame_{frame:06d}.png'
    assert valid_png(path,960,540),path
    hashes.append(sha(path))
assert hashes[750]!=hashes[780],'City holding segment has no visible motion'
assert hashes[1020]!=hashes[1050] and hashes[1260]!=hashes[1290]
def pixels(frame):return np.array(Image.open(job/'frames'/f'frame_{frame:06d}.png').convert('RGB'),dtype=np.float32)
def delta(first,second):return float(np.abs(first-second).mean())
first,last,control=pixels(1),pixels(1800),pixels(1801)
control_delta=delta(first,control);join_delta=delta(last,first)
neighbor_delta=max(delta(pixels(1799),last),delta(first,pixels(2)))
assert control_delta<=.6,('Loop control frame mismatch',control_delta)
assert join_delta<=max(.6,neighbor_delta*2),('Abnormal frame change at loop join',join_delta,neighbor_delta)
manifest=read(ROOT/'render/particle-sequence/manifest.json');digest=hashlib.sha256()
assert manifest==settings['layer_manifest']
for frame in range(1,1802):
    path=ROOT/'render/particle-sequence'/f'particle_{frame:06d}.png'
    assert valid_png(path,960,540),path
    digest.update(hashlib.sha256(path.read_bytes()).digest())
assert digest.hexdigest()==manifest['sequenceSha256']
for name,digest in manifest['layers'].items():assert sha(ROOT/'render/hud-cache'/name)==digest
for frame in [91,601,751,1021,1261]:assert valid_png(ROOT/'previews'/f'frame-{frame:04d}.png',1920,1080)
culture=read(ROOT/'data/culture-sources.json');assert culture['photo']['sha256']==sha(ROOT/culture['photo']['file'])
movie=ROOT/'deliverables/nanjing-culture-three-districts-60s-540p.mp4';video=read(movie.with_suffix('.json'))
assert video['sha256']==sha(movie) and video['fullDecodePassed'] and video['decodedFrames']==1800 and video['seconds']==60
assert video['blend_sha256']==sha(blend)
qa=read(ROOT/'deliverables/visual-review.json');assert qa['passed'] and qa['videoSha256']==sha(movie)
times=[json.loads(line) for line in (job/'timings.jsonl').read_text().splitlines()]
report={'completedAt':datetime.now(timezone.utc).isoformat(),'scope':'60-second Nanjing culture introduction, Yuhuatai, Xuanwu, Gulou, return to globe',
        'unitTests':{'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'output':capture.getvalue()},
        'officialSourceValuesChecked':30,'sceneValidation':scene,'editableDelivery':editable,
        'render':{'job':job.name,'framesChecked':1801,'encodedFrames':1800,'uniquePngHashes':len(set(hashes[:1800])),'allThreeCityHoldsShowMotion':True,'particleSequenceHashVerified':True,'cachedLayerHashesVerified':True,'summedRenderSeconds':round(sum(t['seconds'] for t in times),3)},
        'loop':{'firstToControlFrameMeanAbsoluteError255':control_delta,'lastToFirstFrameMeanAbsoluteError255':join_delta,'neighborFrameMeanAbsoluteError255':neighbor_delta,'controlAndJoinPassed':True,'playerAndOnsiteLoopTested':False},
        'culture':{'file':'data/culture-sources.json','sha256':sha(ROOT/'data/culture-sources.json'),'photoHashVerified':True,'photoPacked':scene['checks']['real_city_photo_is_packed']},
        'video':video,'visualReview':qa,
        'limitations':['540p silent review movie; separate native 1080p stills; native 4K pending','Boundary vintage 2017, geographic overview only','Statistical web source text saved; direct statistical HTML fetch returned HTTP 403','Onsite large-screen legibility, player buffering and long-duration playback not tested']}
(ROOT/'VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
for source in [job/'settings.json',job/'timings.jsonl',job/'visual-review-passed.txt']:
    (evidence/source.name).write_bytes(source.read_bytes())
for name in ['NANJING-UI-UX-V3-SPEC.md','NANJING-UI-UX-V3.1-SPEC.md','NANJING-UI-UX-V3.2-SPEC.md']:
    (ROOT/name).write_bytes((ROOT.parent/name).read_bytes())
allowed_scripts={'prepare_data.py','build_v3.py','validate_v3.py','render_v3.py','cache_hud.py','prepare_particle_sequence.py','render_layer_cache.py','encode_v3.py','inspect_video.py','make_review.py','check_editable.py','finalize_preview.py','fix_fx_visibility.py','fix_map_depth.py'}
files=[]
for path in ROOT.rglob('*'):
    if not path.is_file():continue
    rel=path.relative_to(ROOT);first=rel.parts[0]
    if '__pycache__' in rel.parts or path.suffix=='.blend1':continue
    if len(rel.parts)==1:
        if path.name not in {'README.md','requirements.txt','VALIDATION.json','NANJING-UI-UX-V3-SPEC.md','NANJING-UI-UX-V3.1-SPEC.md','NANJING-UI-UX-V3.2-SPEC.md'}:continue
    elif first=='scripts':
        if path.name not in allowed_scripts:continue
    elif first=='render':
        if rel.parts[1]!='hud-cache':continue
    elif first=='previews':
        if path.name not in {'frame-0091.png','frame-0601.png','frame-0751.png','frame-1021.png','frame-1261.png','settings.json','timings.jsonl'}:continue
    elif first not in {'src','tests','assets','data','inputs','build','deliverables','evidence'}:continue
    files.append(path)
file_manifest={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(files)}
(ROOT/'PACKAGE-MANIFEST.json').write_text(json.dumps(file_manifest,ensure_ascii=False,indent=2),encoding='utf-8');files.append(ROOT/'PACKAGE-MANIFEST.json')
archive=ROOT.parent/'Nanjing-Blender-v3.2-full.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in sorted(files):z.write(path,'nanjing-film-v3.2/'+path.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for rel,digest in file_manifest.items():assert hashlib.sha256(z.read('nanjing-film-v3.2/'+rel)).hexdigest()==digest
print(json.dumps({'status':'FULL_FILM_VERIFIED','archive':str(archive),'files':len(files),'bytes':archive.stat().st_size,'sha256':sha(archive),'unitTests':result.testsRun,'decodedFrames':1800,'loopControlMAE':control_delta,'loopJoinMAE':join_delta},ensure_ascii=False),flush=True)
