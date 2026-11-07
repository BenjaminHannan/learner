"""Deterministic synthetic recording fixture, never represented as Ben's data.

Writes real MP4 + event indices for the same compiler used by the nightly run.
No desktop events are posted. Every row has the same fixed nonzero intent.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw

INTENT = 'Click the blue save button to save the document'


def fixture(root):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGB', (1280, 720), 'white')
    d = ImageDraw.Draw(image); d.rectangle((80,80,140,120), fill='blue'); d.text((85,90), 'Save', fill='white')
    png = root/'fixture.png'; image.save(png)
    clips = {}
    bounds = dict(x=0,y=0,width=1280,height=720)
    for n in range(2):
        name = 'synthetic-'+str(n)
        video = root/(name+'.mp4')
        subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-loop','1','-i',str(png),'-frames:v','600','-r','20','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-y',str(video)], check=True)
        first = 1000+n*30000
        wall = 1794013200000
        frames = [dict(type='frame',frameId=i+1,generation=1,receiveMonotonicMs=first+i*50,transform=dict(sourceBounds=bounds)) for i in range(600)]
        events=[]
        for i in range(200):
            t=first+85+i*150
            x=90+((i*17+n*13)%41); y=85+((i*11+n*7)%31)
            common=dict(source='physical_unverified',t=t,eventTimestampNs=t*1000000)
            if i%5==4:
                events.append(dict(common,type='key',kind='key_down',keyCode=36))
            else:
                events.extend([dict(common,type='mouse',kind='mouse_down',x=x,y=y,button=0),dict(type='mouse',kind='mouse_up',x=x,y=y,button=0,eventTimestampNs=(t+3)*1000000)])
        rows=[dict(type='clock_anchor',t=0,wallTimeMs=wall),*frames,*events]
        ledger=root/(name+'.events.jsonl'); ledger.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        clips[name]=dict(id=name,session=name,app='whole-display',createdMs=wall+first,files=[video.name,ledger.name],
                         videoClock=dict(clock='dispatch_uptime_ms',frameEvents='ordinal',nominalFrameMs=50,offsetMs=0,firstFrameMonotonicMs=first,calibration=dict(measured=True,uncertaintyMs=1)),synthetic=True)
    (root/'clip-index.json').write_text(json.dumps(dict(version=1,clips=clips,daily={})))
    return dict(examples=400,source='synthetic fixture; fabricated clock metadata',intent=INTENT)

if __name__ == '__main__': print(json.dumps(fixture(sys.argv[1])))
