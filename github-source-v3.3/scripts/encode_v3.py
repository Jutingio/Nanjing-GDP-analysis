"""Encode and fully decode the 1800-frame full narrative; exclude the loop control frame."""
import sys,json,argparse,hashlib,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_config import script_config,input_path,output_path,read_json,validate_inputs,camera_samples
CFG=script_config()
from png_check import valid_png
p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--ffmpeg',required=True);a=p.parse_args()
job=Path(a.job);job=job if job.is_absolute() else ROOT/job
settings=json.loads((job/'settings.json').read_text())
if settings.get('config')!=CFG:raise ValueError('Build and encoding configs differ')
if settings.get('start_frame',1)!=1 or settings['frames']!=1800:raise ValueError('Encode requires a complete frame 1..1800 job')
for f in range(1,settings['frames']+1):
    if not valid_png(job/'frames'/f'frame_{f:06d}.png',settings['width'],settings['height']):raise RuntimeError(f'Invalid frame {f}')
out=output_path(CFG,'deliverables/'+CFG['city']['id']+'-60s.mp4');out.parent.mkdir(parents=True,exist_ok=True);partial=out.with_suffix('.partial.mp4')
ff=Path(a.ffmpeg).resolve()
subprocess.run([str(ff),'-hide_banner','-y','-framerate',str(settings['fps']),'-start_number','1','-i',str(job/'frames/frame_%06d.png'),'-frames:v',str(settings['frames']),'-vf','scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv444p,colorspace=all=bt709:iall=bt709:itrc=iec61966-2-1:irange=tv:range=tv:format=yuv420p','-c:v','libx264','-preset','medium','-crf','18','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart','-an',str(partial)],check=True)
decoded=subprocess.run([str(ff),'-hide_banner','-v','error','-xerror','-i',str(partial),'-map','0:v:0','-f','null','-','-progress','pipe:1'],check=True,capture_output=True,text=True)
info=dict(line.split('=',1) for line in decoded.stdout.splitlines() if '=' in line)
assert int(info['frame'])==settings['frames'];assert abs(float(info['out_time_us'])/1e6-settings['frames']/settings['fps'])<.1
os.replace(partial,out)
report=dict(settings,video=out.name,seconds=settings['frames']/settings['fps'],decodedFrames=int(info['frame']),fullDecodePassed=True,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),codec='H264',pixelFormat='yuv420p',colorSpace='BT709',dataMode=read_json(input_path(CFG,'snapshot')).get('dataMode','unspecified'),boundaryYear=CFG['geometry']['boundaryYear'],loopDesigned=True,onsiteLoopTested=False)
out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('V3_VIDEO_COMPLETE',str(out),flush=True)
