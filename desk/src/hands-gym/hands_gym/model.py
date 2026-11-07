"""Windows-safe copy of HANDS NativeActionPolicy, with categorical RL positions.

Encoder/overview/detail/GRU and original action heads match pixel_model.py.
No DOM, task kind, target coordinates, spec, or reward enter policy inputs.
Spatial categorical heads replace deterministic sigmoid coordinates for RL
exploration; original heads remain checkpoint-compatible via load_native().
"""
import hashlib
import re
import torch
from torch import nn
from torch.nn import functional as F
from torch.distributions import Categorical
from .actions import CELL_COUNT, GYM_KEY_CODES, decode_action


def intent_vector(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('intent text required')
    vector = torch.zeros(64)
    for token in re.findall(r'\w+', text.casefold())[:256]:
        digest = hashlib.sha256(token.encode()).digest()
        vector[int.from_bytes(digest[:4], 'big') % 64] += 1 if digest[4] & 1 else -1
    return F.normalize(vector, dim=0)


class GymPolicy(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(nn.Conv2d(3,24,5,2,2),nn.ReLU(),
            nn.Conv2d(24,48,3,2,1),nn.ReLU(),nn.Conv2d(48,96,3,2,1),nn.ReLU(),
            nn.Conv2d(96,128,3,2,1),nn.ReLU())
        self.overview = nn.Sequential(nn.Flatten(),nn.Linear(128*6*10,512),nn.ReLU())
        self.detail = nn.Sequential(nn.Flatten(),nn.Linear(128*3*3,128),nn.ReLU())
        self.memory = nn.GRUCell(512+128+64+12,512)
        self.kind = nn.Linear(512,4)
        self.position = nn.Linear(512,4)
        self.key = nn.Linear(512,256)
        self.scroll = nn.Linear(512,2)
        self.start_grid = nn.Linear(512,CELL_COUNT)
        self.end_grid = nn.Linear(512,CELL_COUNT)
        self.value = nn.Linear(512,1)

    def load_native(self, path):
        state = torch.load(path, map_location='cpu', weights_only=True)
        expected = {k:v for k,v in self.state_dict().items()
                    if not k.startswith(('start_grid.','end_grid.','value.'))}
        if set(state) != set(expected):
            raise ValueError('checkpoint must be NativeActionPolicy state_dict')
        self.load_state_dict(state, strict=False)

    def forward(self, image, crop, intent, own):
        a=self.overview(F.adaptive_avg_pool2d(self.encoder(image),(6,10)))
        b=self.detail(F.adaptive_avg_pool2d(self.encoder(crop),(3,3)))
        # Single-frame memory reset is explicit for this first RL experiment.
        h=self.memory(torch.cat((a,b,intent,own),1))
        logits=(self.kind(h),self.start_grid(h),self.end_grid(h),
                self.key(h)[:,list(GYM_KEY_CODES)])
        return logits, self.value(h).squeeze(-1)

    def act(self, inputs, actions=None, greedy=False):
        logits, value = self(*inputs)
        distributions=[Categorical(logits=x) for x in logits]
        if actions is None:
            actions=torch.stack([d.logits.argmax(-1) if greedy else d.sample()
                                 for d in distributions],-1)
        kind=actions[:,0]
        masks=[torch.ones_like(kind),((kind==0)|(kind==1)),kind==1,kind==2]
        logp=sum(d.log_prob(actions[:,i])*m for i,(d,m) in enumerate(zip(distributions,masks)))
        entropy=sum(d.entropy()*m for d,m in zip(distributions,masks))
        return actions,logp,entropy,value


def batch(observations,instructions,device):
    import numpy as np
    def images(key):
        return torch.from_numpy(np.stack([o[key] for o in observations])).permute(0,3,1,2).to(device).float()/255
    return (images('overview'),images('detail'),
            torch.stack([intent_vector(t) for t in instructions]).to(device),
            torch.zeros(len(observations),12,device=device))


def native_actions(actions):
    # Scroll amplitude is fixed for now; all click/drag/key choices are learned.
    return [decode_action(*row,scroll=(0,0.2)) for row in actions.cpu().tolist()]
