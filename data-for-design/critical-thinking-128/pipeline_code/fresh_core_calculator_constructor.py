"""Fresh matched shallow/deep sparse ordered cores; no checkpoint reuse.

Construction only. Shared repository attention, geometry, residuals, expert
cloning, and zero-router initialization are retained exactly.
"""
ARMS = {'shallow': {'blocks': 2, 'hidden': 1024, 'stored': 9007790},
        'deep': {'blocks': 16, 'hidden': 64, 'stored': 8563454}}
FAMILY = 'fresh-core-calculator-compare-D256-v1'


def build_fresh_core(arm, seed, device='cpu'):
    if arm not in ARMS or seed not in (0, 1):
        raise ValueError('exact matched shallow/deep seeds0/1 required')
    import torch
    from torch import nn
    import claude_fewex_net as base
    from sol_spatial_attention_core import UpcycledMLP
    from sol_spatial_poc_ordered_v2 import OrderedAttentionReasoner
    specification = ARMS[arm]

    class FreshComparisonCore(OrderedAttentionReasoner):
        def __init__(self):
            super().__init__(base.Net('loop'), experts=8, active=2)
            if arm == 'deep':
                blocks = []
                for _ in range(specification['blocks']):
                    block = base.Block(256, 8)
                    mlp = nn.Sequential(nn.Linear(256, specification['hidden']), nn.GELU(),
                                        nn.Linear(specification['hidden'], 256))
                    block.mlp = UpcycledMLP(mlp, 256, 8, 2)
                    blocks.append(block)
                self.blocks = nn.ModuleList(blocks)
            self.halt.requires_grad_(False)

        def constructor(self):
            return {**super().constructor(), 'family': FAMILY, 'arm': arm,
                'distinct_blocks_per_loop': specification['blocks'],
                'expert_hidden': specification['hidden'], 'fixed_latent_loops': 4,
                'whole_block_list_reused_each_loop': True, 'extra_stabilizer': False,
                'fresh_core': True, 'core_initialization_seed': seed}

    # All construction occurs on CPU in an isolated seed scope. No model call.
    with torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(seed)
        model = FreshComparisonCore()
    if sum(p.numel() for p in model.parameters()) != specification['stored']:
        raise ValueError('source-derived stored core parameter count differs')
    if len({id(block) for block in model.blocks}) != specification['blocks']:
        raise ValueError('physical blocks must have distinct parameter storage')
    for block in model.blocks:
        if (len(block.mlp.experts) != 8 or block.mlp.active != 2
                or tuple(block.mlp.experts[0][0].weight.shape) != (specification['hidden'], 256)
                or tuple(block.mlp.experts[0][2].weight.shape) != (256, specification['hidden'])
                or bool(block.mlp.router.weight.detach().count_nonzero())
                or bool(block.mlp.router.bias.detach().count_nonzero())):
            raise ValueError('exact8/top2/equal-clone/zero-router architecture required')
        if any(not torch.equal(a, b) for expert in block.mlp.experts[1:]
               for a, b in zip(block.mlp.experts[0].parameters(), expert.parameters())):
            raise ValueError('current equal-cloned expert initialization differs')
    if any(p.dtype != torch.float32 for p in model.parameters()):
        raise ValueError('fullFP32 constructor required')
    return model.to(device)
