"""CPU-only weight inspection of the real checkpoints (no LM, no GPU).

bootstrap0.pt: the original English decoder adapter (StatePrefix) the parents started from.
parent0.pt:    pilot parent seed 0 (update 5120), sha 49a35023...
main2.pt:      skills main2 (the parent of every current screen run).
"""
import json
import sys
import torch

D = sys.argv[1]
boot = torch.load(D + '/bootstrap0.pt', map_location='cpu', weights_only=True)
par = torch.load(D + '/parent0.pt', map_location='cpu', weights_only=True)
m2 = torch.load(D + '/main2.pt', map_location='cpu', weights_only=True)
out = {}


def prefix_stats(sd):
    w2, b2 = sd['project.2.weight'], sd['project.2.bias']
    w1, b1 = sd['project.0.weight'], sd['project.0.bias']
    s = torch.linalg.svdvals(w2)
    return {'scale_norm': round(float(sd['scale'].norm()), 3), 'bias_in_norm': round(float(sd['bias'].norm()), 3),
            'W1_fro': round(float(w1.norm()), 2), 'b1_norm': round(float(b1.norm()), 2),
            'W2_fro': round(float(w2.norm()), 2), 'W2_top_sv': [round(float(x), 2) for x in s[:4]],
            'b2_norm': round(float(b2.norm()), 2), 'W2_rank_le': int(w2.shape[1])}


out['prefix'] = {'bootstrap': prefix_stats(boot['adapter_state']), 'parent0': prefix_stats(par['prefix']),
                 'main2': prefix_stats(m2['prefix'])}
out['update'] = {'parent0': par.get('update'), 'main2': m2.get('update')}


def moe_stats(core):
    rows = []
    for b in range(2):
        pre = 'blocks.%d.mlp.' % b
        rw, rb = core[pre + 'router.weight'], core[pre + 'router.bias']
        ex = [{k[len(pre + 'experts.%d.' % e):]: v for k, v in core.items() if k.startswith(pre + 'experts.%d.' % e)}
              for e in range(8)]

        def same(a, c):
            return all(torch.equal(a[k], c[k]) for k in a)

        def diff(a, c):
            return max(float((a[k] - c[k]).abs().max()) for k in a)
        rows.append({'block': b, 'router_nonzero': int(rw.count_nonzero() + rb.count_nonzero()),
                     'expert0_eq_expert1': same(ex[0], ex[1]), 'max_abs_diff_e0_e1': diff(ex[0], ex[1]),
                     'experts2to7_all_equal': all(same(ex[2], ex[e]) for e in range(3, 8)),
                     'max_abs_diff_e0_e2': diff(ex[0], ex[2]),
                     'params_per_expert': sum(v.numel() for v in ex[0].values())})
    stored = sum(v.numel() for v in core.values() if v.is_floating_point())
    return rows, stored


for name, sd in (('parent0', par['core']), ('main2', m2['core'])):
    rows, stored = moe_stats(sd)
    out['moe_' + name] = rows
    out['core_stored_params_' + name] = stored
pe = out['moe_main2'][0]['params_per_expert']
non_expert = out['core_stored_params_main2'] - 2 * 8 * pe - 2 * (256 * 8 + 8)
unused_heads = sum(v.numel() for k, v in m2['core'].items() if k.split('.')[0] in ('tok', 'slot', 'head', 'ln_out', 'halt'))
out['core_live_estimate'] = {'one_distinct_expert_per_block': 2 * pe, 'non_expert_params': non_expert,
                             'of_which_unused_puzzle_heads': unused_heads,
                             'live_distinct_trainable': 2 * pe + non_expert - unused_heads,
                             'stored': out['core_stored_params_main2']}

# reader 2048 -> 32 -> 256
for name, sd in (('parent0', par['reader']), ('main2', m2['reader'])):
    w = sd['proj.1.weight']
    s = torch.linalg.svdvals(w)
    out['reader_' + name] = {'W1_shape': list(w.shape), 'sv_top': [round(float(x), 3) for x in s[:4]],
                             'sv_last': [round(float(x), 3) for x in s[-4:]],
                             'effective_rank_99': int((s.cumsum(0) / s.sum() < 0.99).sum()) + 1}
print(json.dumps(out, indent=1))
