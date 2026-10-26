"""Extract exact review frames from the encoded BT.709 movie in display sRGB."""
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--ffmpeg',required=True);a=p.parse_args()
frames=[1,91,601,751,901,1021,1141,1261,1381,1681,1800];dest=ROOT/'deliverables/review-frames';dest.mkdir(exist_ok=True)
select='+'.join(f'eq(n,{f-1})' for f in frames)
subprocess.run([str(Path(a.ffmpeg).resolve()),'-hide_banner','-v','error','-y','-i',str(ROOT/'deliverables/nanjing-culture-three-districts-60s-540p.mp4'),'-vf',f"select='{select}',colorspace=all=bt709:trc=iec61966-2-1:format=yuv444p,format=rgb24",'-fps_mode','vfr','-frames:v',str(len(frames)),str(dest/'decoded-%02d.png')],check=True)
(dest/'index.json').write_text(json.dumps([{'file':f'decoded-{i:02d}.png','sourceFrame':f,'seconds':(f-1)/30} for i,f in enumerate(frames,1)],indent=2),encoding='utf-8')
print('DECODED_REVIEW_FRAMES',dest,flush=True)
