"""Train quarantined HANDS candidates from already verified frame/action examples.

No promotion or recording deletion happens here. Production training refuses to
start or continue outside the local 01:00–07:00 window or while Ben is active.
"""
import ctypes
import datetime
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
import pixel_model

torch.set_num_threads(1)


def idle_seconds():
    if sys.platform != 'darwin':
        raise RuntimeError('Mac idle check unavailable')
    cg = ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
    cg.CGEventSourceSecondsSinceLastEventType.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
    cg.CGEventSourceSecondsSinceLastEventType.restype = ctypes.c_double
    return cg.CGEventSourceSecondsSinceLastEventType(1, 0xffffffff)


def production_gate():
    now = datetime.datetime.now().astimezone()
    idle = idle_seconds()
    if not 1 <= now.hour < 7 or not math.isfinite(idle) or idle < 1200:
        raise RuntimeError('training deferred: requires 01:00–07:00 and 20 minutes of Mac idle')
    if (Path.home() / 'learner-ops/aon-notes/hands-20261106/STOP-TRAINING').exists():
        raise RuntimeError('training stopped')


def partition(rows, start, end):
    if type(start) is not int or type(end) is not int or start < 0 or end <= start:
        raise ValueError('bad day bounds')
    cutoff = start + (end-start)*0.8
    ids = set()
    for r in rows:
        if not isinstance(r.get('id'), str) or not r['id'] or r['id'] in ids or type(r.get('timeMs')) is not int or not start <= r['timeMs'] <= end:
            raise ValueError('invalid example identity or time')
        ids.add(r['id'])
    train = [r for r in rows if r['timeMs'] < cutoff]
    held = [r for r in rows if r['timeMs'] >= cutoff]
    if not train or not held:
        raise ValueError('both time slices need examples')
    return train, held, cutoff


def load_example(row, no_intent=False):
    # Dataset producers must establish these flags and bind image/action evidence.
    if row.get('verified') is not True:
        raise ValueError('unverified example')
    action = row['action']; kind = action['kind']
    if kind not in pixel_model.KINDS or not isinstance(row['intent'], str) or not row['intent'].strip():
        raise ValueError('invalid action or intent')
    if row.get('frameFileSha256') and hash_file(row['frame']) != row['frameFileSha256']:
        raise ValueError('frame file changed')
    img = Image.open(row['frame']).convert('RGB')
    width, height = img.size
    if width <= 0 or height <= 0:
        raise ValueError('empty image')
    overview = img.resize((320,180))
    # The old HANDS encoder takes a 192x192 detail image as well.
    cx, cy = width // 2, height // 2
    detail = img.crop((cx-96,cy-96,cx+96,cy+96)).resize((192,192))
    def tensor(image):
        return torch.from_numpy(np.asarray(image, dtype=np.uint8).copy()).permute(2,0,1).float().div(255).unsqueeze(0)
    points = [0.,0.,0.,0.]
    if kind in ('click','drag'):
        coords = [action['x'], action['y']]
        if kind == 'drag': coords += [action['endX'],action['endY']]
        for i, value in enumerate(coords):
            size = width if i % 2 == 0 else height
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not 0 <= value < size:
                raise ValueError('point outside frame')
            points[i] = value / size
    key = action.get('keyCode', 0) if kind == 'key' else 0
    if type(key) is not int or not 0 <= key < pixel_model.KEY_COUNT:
        raise ValueError('invalid key code')
    scroll = [action.get('dx',0),action.get('dy',0)] if kind == 'scroll' else [0,0]
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not np.isfinite(x) for x in scroll):
        raise ValueError('invalid scroll')
    weight = row.get('weight',1)
    if weight not in (1,3) or (weight == 3 and row.get('verifiedCorrection') is not True):
        raise ValueError('unverified correction weight')
    labels = {'kind':torch.tensor([pixel_model.KINDS.index(kind)]), 'position':torch.tensor([points]),
              'key':torch.tensor([key]), 'scroll':torch.tensor([scroll],dtype=torch.float32)}
    intent = torch.zeros(1,64) if no_intent else pixel_model.intent_vector(row['intent']).unsqueeze(0)
    return tensor(overview), tensor(detail), intent, torch.zeros(1,12), labels, torch.tensor([float(weight)])


def model_prediction(net, row, no_intent=False):
    image, crop, intent, own, _, _ = load_example(row, no_intent)
    with torch.no_grad():
        out, _ = net(image,crop,intent,own)
    action = row['action']
    if action['kind'] == 'key':
        return {'key':str(int(out['key'].argmax(dim=1)[0]))}
    with Image.open(row['frame']) as frame:
        w,h = frame.size
    x,y=float(out['position'][0,0])*w,float(out['position'][0,1])*h
    display = row.get('display')
    if display:
        bounds=display['bounds']; scale=min(w/bounds['width'],h/bounds['height'])
        x=(x-(w-bounds['width']*scale)/2)/scale*display['scaleX']
        y=(y-(h-bounds['height']*scale)/2)/scale*display['scaleY']
    return {'x':x,'y':y}


def fit(net, rows, gate, *, steps=50, no_intent=False):
    opt = torch.optim.AdamW(net.parameters(),lr=0.0003)
    rng = random.Random(101)
    for _ in range(steps):
        gate()
        row = rng.choices(rows, weights=[r.get('weight',1) for r in rows], k=1)[0]
        image,crop,intent,own,labels,weights = load_example(row, no_intent)
        weights.fill_(1.0)  # Sampling supplies the 3x correction weight.
        net.train(); out,_ = net(image,crop,intent,own)
        loss = pixel_model.action_loss(out,labels,weights)
        opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(),1); opt.step()
    gate(); net.eval()


def hash_file(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def train(dataset, output, gate=production_gate, steps=50, previous=None):
    # Caller supplies a provenance-checked manifest; never consume the held slice while fitting.
    gate()
    rows = dataset['examples']
    if dataset.get('allowSparse') and (len(rows)<2 or len({r['timeMs'] for r in rows})<2):
        train_rows, held_rows, cutoff = rows, [], dataset['endMs']
    else:
        train_rows, held_rows, cutoff = partition(rows,dataset['startMs'],dataset['endMs'])
    score_rows = [r for r in held_rows if r['action']['kind'] in ('click','key')]
    # Missing action classes are reported as unmeasured, not a first-night gate.
    # Scroll/drag-only nights still produce quarantined weights.
    for r in rows: load_example(r)
    torch.manual_seed(101)
    initial = pixel_model.NativeActionPolicy().eval()
    baseline_warning = None
    if previous is not None:
        try:
            initial.load_state_dict(torch.load(previous,map_location='cpu',weights_only=True),strict=True)
        except Exception as error:
            baseline_warning = str(error)
            previous = None
            torch.manual_seed(101)
            initial = pixel_model.NativeActionPolicy().eval()
    old = pixel_model.NativeActionPolicy().eval(); old.load_state_dict(initial.state_dict())
    candidate = pixel_model.NativeActionPolicy(); candidate.load_state_dict(initial.state_dict())
    no_intent = pixel_model.NativeActionPolicy(); no_intent.load_state_dict(initial.state_dict())
    if train_rows:
        fit(candidate,train_rows,gate,steps=steps)
        fit(no_intent,train_rows,gate,steps=steps,no_intent=True)
    predictions = {name:{r['id']:model_prediction(net,r,zero) for r in score_rows} for name,net,zero in [('old',old,False),('candidate',candidate,False),('noIntent',no_intent,True)]}
    gate()
    output.mkdir(parents=True,exist_ok=True,mode=0o700)
    for name,net in [('old',old),('candidate',candidate),('no-intent',no_intent)]:
        tmp=output/(name+'.tmp'); final=output/(name+'.pt')
        torch.save(net.state_dict(),tmp); os.replace(tmp,final)
    return {'cutoffMs':cutoff,'train':train_rows,'held':score_rows,'predictions':predictions,
            'modelSha256':{n:hash_file(output/(n+'.pt')) for n in ('old','candidate','no-intent')},
            'oldModel': 'previous native-action model' if previous is not None else 'initial untrained native-action head; no published compatible model loaded',
            'hasPreviousModel': previous is not None, 'baselineWarning':baseline_warning,
            'trainingStepsPerArm':steps if train_rows else 0,
            'intentPolicy':{'candidate':'fixed hash64 of supplied intent', 'noIntent':'all-zero vector', 'trainIntentCount':len({r['intent'] for r in train_rows})},
            'status':'quarantine; not promoted'}


def main():
    dry_run = '--dry-run' in sys.argv
    if dry_run: sys.argv.remove('--dry-run')
    if len(sys.argv) != 3:
        raise SystemExit('usage: trainer.py <verified-dataset.json> <quarantine-dir>')
    guard = (lambda: None) if dry_run else production_gate
    guard()
    with open(sys.argv[1],encoding='utf8') as f: dataset=json.load(f)
    previous = dataset.get('preSleepWeights')
    result=train(dataset,Path(sys.argv[2]),previous=Path(previous) if previous else None, gate=guard, steps=dataset.get('trainingSteps', 100))
    def score_row(r):
        a=r['action']; row={'id':r['id'],'timeMs':r['timeMs'],'kind':a['kind']}
        if a['kind']=='click': row.update(x=a.get('screenX',a['x']),y=a.get('screenY',a['y']))
        elif a['kind']=='key': row['key']=str(a['keyCode'])
        return row
    result['train']=[score_row(r) for r in result['train']]
    result['held']=[score_row(r) for r in result['held']]
    print(json.dumps(result))

if __name__ == '__main__': main()
