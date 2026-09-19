import torch
from torch import nn
from learnlab.readonly import read_only
m = nn.Sequential(nn.Linear(3, 3), nn.BatchNorm1d(3))
m.train(); m[1].eval()          # frozen retriever / frozen BN kept in eval inside a training model
with read_only(m): m(torch.randn(4, 3))
print("frozen BN submodule training flag after read_only:", m[1].training, "(was False)")
rm0 = m[1].running_mean.clone(); m(torch.randn(4, 3))
print("next training forward now updates the frozen BN stats:", not torch.equal(rm0, m[1].running_mean))
