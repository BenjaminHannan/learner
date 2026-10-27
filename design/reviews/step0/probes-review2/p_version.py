import copy, torch
from torch import nn
m = nn.Linear(4, 1)
v0 = {n: p._version for n, p in m.named_parameters()}
saved = copy.deepcopy(m.state_dict())
opt = torch.optim.SGD(m.parameters(), lr=0.1)
m(torch.randn(8, 4)).pow(2).mean().backward(); opt.step()
m.load_state_dict(saved)
v1 = {n: p._version for n, p in m.named_parameters()}
print("values restored:", torch.equal(m.weight, saved["weight"]), "| _version before/after:", v0, v1)
