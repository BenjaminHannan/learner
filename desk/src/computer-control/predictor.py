"""Inference only for the existing toy pixel policy; never fits weights."""
import sys, json, base64, io
import numpy as np
from PIL import Image
import torch

torch.set_num_threads(1)
request = json.load(sys.stdin)
model = torch.jit.load(request['model'], map_location='cpu').eval()
image = Image.open(io.BytesIO(base64.b64decode(request['png']))).convert('RGB').resize((320, 180))
cursor = request['cursor']
cx = max(0, min(319, int(cursor[0] * 320)))
cy = max(0, min(179, int(cursor[1] * 180)))
detail = Image.new('RGB', (192, 192))
detail.paste(image, (96-cx, 96-cy))
def tensor(im):
    return torch.from_numpy(np.array(im, dtype=np.uint8).copy()).permute(2, 0, 1).float().div_(255).unsqueeze(0)
own = torch.zeros(1, 12)
own[0, 0], own[0, 1] = cx / 320, cy / 180
intent = torch.tensor([{'click':0, 'drag':1}.get(request['action'], 0)])
with torch.inference_mode():
    prediction, _ = model(tensor(image), tensor(detail), intent, own, torch.zeros(1, 512))
    values = prediction[0].tolist()
print(json.dumps({'dx':max(-24, min(24, values[0]*24)), 'dy':max(-24, min(24, values[1]*24))}))
