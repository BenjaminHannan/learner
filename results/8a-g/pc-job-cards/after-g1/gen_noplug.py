# gen_noplug.py SRC_TREE CARDS_DIR SHA (spec addendum Z): writes 8aFC2-noplug-pc.txt and 8aC30S-noplug-pc.txt from the plugged 8aFC2-pc.txt and 8aC30S-pc.txt, configs built by the custom_io in SRC_TREE (the group 2 commit SHA). Run it again on the group 2 install commit; the files must not change.
import sys, json, shlex, re
src, cards, sha = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, src)
from custom_io.g8a import caps as CP, configs as C
CP.apply(json.load(open(f'{src}/custom_io/g8a/caps_b3g2.json')))
out, counts = [], {}
for ln in open(f'{cards}/8aFC2-pc.txt').read().splitlines():
    if ln.startswith('8aFC2-') and '--cfg' in ln:
        name, rest = ln.split(' ', 1)
        old = json.loads(shlex.split(rest)[shlex.split(rest).index('--cfg') + 1])
        n = old['blocks']
        cfg = C.b3_cfg('100M', {'eg_embed': True, 'noplug': True, 'blocks': n}, group=2)
        assert {k: v for k, v in cfg.items() if k not in ('mlp', 'eg_pre', 'eg_adapter')} == {k: v for k, v in old.items() if k != 'mlp'}, (n, cfg, old)
        t = C.b3_sizes(cfg, 'b3g2')['trained']
        counts[n] = (cfg['mlp'], t)
        i0, i1 = ln.index("--cfg '") + 7, None
        i1 = ln.index("'", i0)
        ln = ln[:i0] + json.dumps(cfg, sort_keys=True) + ln[i1:]
        assert out[-1].startswith('# %d x 512' % n), out[-1]
        out[-1] = '# %d x 512, mlp %s: %s trained (b3g2, caps_b3g2, NO PLUG: Gemma\'s own 512 numbers through a zero-start LayerNorm(512); configs.b3_cfg 100M noplug blocks %d at %s)' % (n, cfg['mlp'], '{:,}'.format(t), n, sha)
    out.append(ln)
h = out[0]
assert 'with today\'s Gemma plug (395,264 of it;' in h, h
h = h.replace("trained count about 102.64M with today's Gemma plug (395,264 of it; it runs here so that Gemma's time and memory are included)",
              "trained count about 102.63M with NO PLUG (Ben, 4:12 PM ET 11 Oct: \"can you remove the converter plug and just have our model match gemma's\"): "
              "Gemma's own 512 numbers go through a zero-start LayerNorm(512) (1,024 trained), Gemma runs here so its time and memory are included")
h = h.replace("the settled 21 x 512 (mlp 4.8) and four deeper shapes at the same count: 26 (mlp 3.10449), 30 (2.15723), 34 (1.43066), 37 (0.98926) (architecture/fc100-512/fc100-512-shapes.json); config = configs.b3_cfg('100M', group 2) with blocks and mlp changed",
              "21 x 512 (mlp %s) and four deeper shapes at the same count: %s; config = configs.b3_cfg('100M', {\"eg_embed\": true, \"noplug\": true, \"blocks\": N}, group 2) at %s (the architecture thread's no-plug front, 7:20 PM ET)"
              % (counts[21][0], ', '.join('%d (mlp %s)' % (n, counts[n][0]) for n in (26, 30, 34, 37)), sha))
assert 'NO PLUG' in h and 'noplug' in h, h
out[0] = h
open(f'{cards}/8aFC2-noplug-pc.txt', 'w').write('\n'.join(out) + '\n')
for n in sorted(counts): print(n, counts[n][0], '{:,}'.format(counts[n][1]))
# c30s
q = open(f'{cards}/8aC30S-pc.txt').read().splitlines()
CP.apply(json.load(open(f'{src}/custom_io/g8a/caps_b3s.json')))
a = C.train_args('30M', 'PTS', 400, 100, 'x', caps='caps_b3s.json', b2_extra={'eg_embed': True, 'noplug': True})
pc = json.loads(a[a.index('--cfg') + 1]); lr = a[a.index('--lr') + 1]
cfgs, cn = C.sizes('30M', {'eg_embed': True, 'noplug': True}); C.add_pts('30M', cfgs, cn, {'eg_embed': True, 'noplug': True})
assert pc['eg_pre'] and pc['d_model'] == 512, pc
q[0] = q[0].replace("Size check on CPU at 1acfde9a73: 30M B2 28,934,585, PTS 28,841,088 (within the plain band). Code src-b3g2 = custom_io of claude/learner-new-g2 at 1acfde9a73.",
    "NO PLUG (Ben, 4:12 PM ET 11 Oct; job.py --noplug, the architecture thread's no-plug front): width 512, 8 heads, Gemma's own 512 numbers through a zero-start LayerNorm(512); "
    "size check on CPU at %s under caps_b3s.json: 30M B2 %s, PTS %d layers, hidden %d, %s trained (within the plain band); lr %s (1e-3 x 256 / 512, every arm at this rung). Code src-b3g2 = the group 2 reader-rule commit installed by install_rr.ps1."
    % (sha, '{:,}'.format(cn['B2']), pc['n_layers'], pc['hidden'], '{:,}'.format(cn['PTS']), lr))
assert 'NO PLUG' in q[0], q[0]
i = [k for k, l in enumerate(q) if l.startswith('g8a: 8aC30S-30M-s400 ')]
assert len(i) == 1 and '--noplug' not in q[i[0]]
q[i[0]] += ' --noplug'
open(f'{cards}/8aC30S-noplug-pc.txt', 'w').write('\n'.join(q) + '\n')
print('c30s', pc, lr, cn)
