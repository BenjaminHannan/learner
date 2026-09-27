import sys
from pathlib import Path
S = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames21-20260920/audit-scratch')
sys.path.insert(0, str(S))
import postc1_newnames21 as M
torch = M.torch
print('CODE_SCALE_INIT = %.8f  (.02*sqrt(48))' % M.CODE_SCALE_INIT)
m = M.new_treatment_model(2100)
c = M.new_control_model(2100)
print('trainable: treatment', M.trainable_parameters(m), ' control', M.trainable_parameters(c))
named = {n: (tuple(p.shape), p.requires_grad) for n, p in m.named_parameters()}
print('treatment parameters:', named)
print('buffers:', {n: tuple(b.shape) for n, b in m.named_buffers()})
print('code_scale value', float(m.code_scale), 'requires_grad', m.code_scale.requires_grad)
print('entity_output_bias value', float(m.entity_output_bias), 'numel', m.entity_output_bias.numel())
opt = M.A.T.optimizer_for(m)
ids = {id(p) for g in opt.param_groups for p in g['params']}
print('code_scale in optimizer:', id(m.code_scale) in ids,
      '| entity_output_bias in optimizer:', id(m.entity_output_bias) in ids)
print('weight_decay per group:', [(g.get('weight_decay'), len(g['params'])) for g in opt.param_groups])
print('base_embedding rows (structure/relations/values/filler):', tuple(m.base_embedding.shape),
      '-> value rows are ordinary parameters, independent of code_scale')
# candidate-set width
codes = torch.randn(2, 16, 48); codes = codes/codes.norm(dim=2, keepdim=True)
w = m.world_weight(codes)
print('gated world_weight (candidates per world):', tuple(w.shape), '-> logits width', w.shape[1])
wide = torch.randn(2, 64, 48); wide = wide/wide.norm(dim=2, keepdim=True)
print('wide64 world_weight:', tuple(m.world_weight(wide).shape))
# code_scale gradient does not flow into base rows / codes
codes.requires_grad_(False)
loss = m.world_weight(codes).sum()
g = torch.autograd.grad(loss, [m.code_scale, m.base_embedding], allow_unused=True)
print('d(sum world_weight)/d code_scale =', float(g[0]), '(= sum of codes; codes never get a grad)')
print('A.ENTITY_MIN, A.ENTITY_MAX after everything:', M.A.ENTITY_MIN, M.A.ENTITY_MAX)
