import torch
from torch import nn
from learnlab.readonly import read_only, ReadOnlyViolation
class Rotary(nn.Module):
    def __init__(self):
        super().__init__(); self.register_buffer("cos_cached", torch.ones(8), persistent=False)
    def forward(self, x):
        if x.shape[0] > self.cos_cached.shape[0]:        # grow cache for a longer eval sequence (harmless, derived)
            self.cos_cached = torch.cos(torch.arange(x.shape[0]).float())
        return x
m = Rotary()
try:
    with read_only(m): m(torch.randn(32))
    print("no violation")
except ReadOnlyViolation as e: print("FALSE POSITIVE on derived cache growth:", e)
