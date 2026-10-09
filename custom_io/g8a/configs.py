"""Rung shapes, parameter counter and the train.py command of every arm (8A spec sections 2, 3, 5).

  python3 -m custom_io.g8a.configs                 # table of all rungs and arms, asserts every band
  python3 -m custom_io.g8a.configs --rung 10M --arm B2 --seed 400 --steps 40000 --data /job/pool   # one train.py command line

Trained parameters = every weight that gets gradients (n_params()). B2: width and depth (`blocks`) per rung; if the nearest block count is
outside the +-5% band with today's feed-forward ratio, the ratio `mlp` is trimmed until the count lands on target (disclosed in the table).
Plain arms (plain_tf_steps_g, plain_lm): layers and feed-forward width chosen so the count is within +-2% of B2's (nearest layer count, then
`hidden` trimmed to land within 0.3%).
"""
import argparse, functools, json, shlex, sys
import torch
from custom_io.data import CharVocab
from custom_io.models import build

VOCAB = None
B2_ARM, PT_ARM, LLM_ARM = 'B2', 'PT', 'LLM'
ARMS = (B2_ARM, PT_ARM, LLM_ARM)
MODEL_OF = {B2_ARM: 'ledger', PT_ARM: 'plain_tf_steps_g', LLM_ARM: 'plain_lm'}
B2_S = dict(d=256, n_heads=4, reader_layers=2, blocks=2, n_loops=8, mlp=4.8, copy=True)       # today's S, 3,302,481 trained params (q33)
B2_S_PARAMS = 3_302_481
# rung -> width, heads, today's mlp ratio at that width, target trained params, band as a fraction, pool word pieces, seen word pieces (20 per trained
# param), lr, and which nested pieces of the data pool it reads (addendum B1: 3M and 10M share the 60M pool, so they see the same rows in the same order)
# web: the slice file the pool reads (slice_<web>.jsonl). 3M and 10M read slice_rung30.jsonl, whose first documents ARE slice_rung10.jsonl (prefix, checked byte for
# byte) because the rung10 slice yields only 35.46M cloze pieces against the pool's 37.2M budget; the builder stops at the budget, so the rows are the rung10 ones plus the
# few documents needed to fill it.
RUNGS = {
    '3M': dict(width=256, heads=4, mlp=4.8, target=B2_S_PARAMS, band=0.0, pool=60e6, seen=66e6, lr=1e-3, own_rung=10, web='rung30'),
    '10M': dict(width=256, heads=4, mlp=4.8, target=10.0e6, band=0.05, pool=60e6, seen=200e6, lr=1e-3, own_rung=10, web='rung30'),
    '30M': dict(width=384, heads=6, mlp=6.0, target=30.0e6, band=0.05, pool=190e6, seen=600e6, lr=1e-3 * 256 / 384, own_rung=30, web='rung30'),
}
UPDATE_FLOOR = 24000        # addendum B1: every arm at every rung trains at least q33's 24,000 updates of 256 rows
OWN_SHARE, WEB_SHARE = 0.38, 0.62
PUB_ARM = 'PUB'
# 8A spec addendum A2 / A4: the public model of mark 5 (30M rung only), pinned by hub revision (resolved 2026-10-07 via huggingface.co/api/models/<id>).
# letter reader at every rung (addendum F) -> pythia-31m only (SmolLM2-360M stays a report-only 8-shot on the Mac). Fine-tuned on the same question rows (no web fill-in rows), default lr 1e-4, batch 256, no calculator
# (the `calc` variant is the same weights with exact results forced in, reported beside).
PUBLIC = {
    'pythia31m': dict(hf_id='EleutherAI/pythia-31m', revision='e556ace21b489575e94e9d50b6dad2fcc7419679', lr=1e-4, batch=256),
}
BATCH, PLAIN_BAND, PLAIN_TRIM = 256, 0.02, 0.003


def vocab():
    global VOCAB
    if VOCAB is None:
        VOCAB = CharVocab.build([])     # all printable ASCII + specials = 108 ids, the vocabulary every q33 run used
    return VOCAB


@functools.lru_cache(maxsize=None)
def count(model, cfg_json):
    """Trained parameter count of `model` built with cfg (a JSON string, for caching). Frozen borrowed parts are not in it."""
    torch.manual_seed(0)
    return build(model, vocab(), **json.loads(cfg_json)).n_params()


def n(model, cfg):
    return count(model, json.dumps(cfg, sort_keys=True))


def _per_unit(model, cfg, key, base_v):
    """Parameters added by one more unit of `key` (blocks / n_layers): count(base_v + 1) - count(base_v). Exactly linear for these models."""
    return n(model, dict(cfg, **{key: base_v + 1})) - n(model, dict(cfg, **{key: base_v}))


def b2_cfg(rung, extra=None):
    """B2 config for a rung (copy talker on, 8 rounds). `extra` = reader switches, e.g. {"eg_embed": true} once stage 2b picks EGE."""
    r = RUNGS[rung]
    if rung == '3M':
        cfg = dict(B2_S)
    else:
        base = dict(dict(d=r['width'], n_heads=r['heads'], reader_layers=2, n_loops=8, mlp=r['mlp'], copy=True), **(extra or {}))      # extras (eg_embed: the adapter) are counted in the block choice
        c1, per = n('ledger', dict(base, blocks=1)), _per_unit('ledger', base, 'blocks', 1)
        best = min(range(1, 41), key=lambda b: abs(c1 + (b - 1) * per - r['target']))
        cfg = dict(base, blocks=best)
        if abs(n('ledger', cfg) / r['target'] - 1) > r['band']:
            d = r['width']                           # trim the feed-forward ratio: hidden = int(mlp * d), 2d + 1 params per hidden unit per block
            hid = int(r['mlp'] * d) + round((r['target'] - n('ledger', cfg)) / (best * (2 * d + 1)))
            cfg['mlp'] = round((hid + 0.5) / d, 5)
    return dict(cfg, **(extra or {}))


def plain_cfg(rung, b2=None, extra=None):
    """Plain arm config matched to B2's trained size (+-2%): width as B2, nearest layer count with today's 4x feed-forward; only if that is
    outside the band is the feed-forward width trimmed (3M therefore stays plain_tf_steps' own 4 layers x 1024)."""
    r = RUNGS[rung]
    b2 = b2 or b2_cfg(rung)
    target = n('ledger', b2)
    d, h = r['width'], r['heads']
    base = dict(d_model=d, n_heads=h, **({'eg_embed': True} if b2.get('eg_embed') else {}))      # test 8a-G: the plain step arm gets the same frozen-Gemma front (its adapter counts)
    c1, per = n('plain_tf_steps_g', dict(base, n_layers=1)), _per_unit('plain_tf_steps_g', base, 'n_layers', 1)
    best = min(range(1, 61), key=lambda L: abs(c1 + (L - 1) * per - target))
    cfg = dict(base, n_layers=best)
    if abs(n('plain_tf_steps_g', cfg) / target - 1) > PLAIN_BAND - 0.005:
        cfg['hidden'] = 4 * d + round((target - n('plain_tf_steps_g', cfg)) / (best * (2 * d + 1)))
    return dict(cfg, **(extra or {}))


def tkn_mlp(rung, tk_extra, tol=0.005):
    """Test TKN (TOKENS-EXPERIMENT-2026-10-09.md sec. 3b): TK with reader_layers 0; raise `mlp` until the trained count is within `tol` of TK's. Same trimming
    arithmetic as b2_cfg: hidden = int(mlp * d), 2d + 1 params per hidden unit per block, mlp = (hidden + 0.5) / d. Counts depend on the caps in force: call
    after caps.apply (job.py does) -> (mlp, TKN --b2-extra dict, TK count, TKN count)."""
    tk = b2_cfg(rung, tk_extra)
    target, d = n('ledger', tk), tk['d']
    ex = {k: v for k, v in dict(tk_extra, reader_layers=0).items() if k != 'mlp'}
    c0 = b2_cfg(rung, ex)
    hid = int(c0['mlp'] * d) + round((target - n('ledger', c0)) / (c0['blocks'] * (2 * d + 1)))
    best = min((dict(c0, mlp=round((h + 0.5) / d, 5)) for h in (hid - 1, hid, hid + 1)), key=lambda c: abs(n('ledger', c) - target))
    assert abs(n('ledger', best) / target - 1) <= tol, (n('ledger', best), target)
    return best['mlp'], dict(ex, mlp=best['mlp']), target, n('ledger', best)


def eg_adapter_params(d):
    """Trained parameters of the frozen-Gemma front's adapter: LayerNorm(768) + Linear(768, d)."""
    return 2 * 768 + 768 * d + d


def sizes(rung, b2_extra=None):
    """{'B2': cfg, 'PT': cfg, 'LLM': cfg} and the counts."""
    b2 = b2_cfg(rung, b2_extra)
    pc = plain_cfg(rung, b2)           # matched to B2's actual count (n_loops raised by the caps included), within 2%
    cfgs = {B2_ARM: b2, PT_ARM: pc}
    if not b2.get('eg_embed'):          # plain_lm has no Gemma front: with eg_embed (test 8a-G) the arms are B2 and PT only
        cfgs[LLM_ARM] = dict(pc)
    return cfgs, {a: n(MODEL_OF[a], c) for a, c in cfgs.items()}


def check_bands(rung, cfgs=None, counts=None, exact_3m=True):
    """Assert section 2's bands. Returns the counts. A run outside its band does not count (the launcher refuses it)."""
    cfgs, counts = (cfgs, counts) if cfgs else sizes(rung)
    r, b2 = RUNGS[rung], counts[B2_ARM]
    eg = bool(cfgs[B2_ARM].get('eg_embed'))
    ref = B2_S_PARAMS + (eg_adapter_params(r['width']) if eg else 0)      # test 8a-G: B2_S + the adapter (EGE-3M, 3,500,881 at the old caps)
    if rung == '3M':
        if exact_3m:
            assert b2 == ref, f'3M B2 must be today\'s {ref:,}, got {b2:,}'
        else:           # caps sized from the data (addendum E) grow the position / place tables: allowed, within 3% of today's, disclosed in box.json
            assert abs(b2 / ref - 1) <= 0.03, f'3M B2 {b2:,} is more than 3% from today\'s {ref:,}'
    else:
        assert abs(b2 / r['target'] - 1) <= r['band'], f'{rung} B2 {b2:,} outside {r["target"]:,.0f} +-{100 * r["band"]:.0f}%'
    for a in (PT_ARM, LLM_ARM):
        if a not in counts:
            continue
        assert abs(counts[a] / b2 - 1) <= PLAIN_BAND, f'{rung} {a} {counts[a]:,} is not within {100 * PLAIN_BAND:.0f}% of B2 {b2:,}'
    return counts


def train_args(rung, arm, seed, steps, data, out=None, minutes=None, lr=None, b2_extra=None, bf16=True, big_data=None, caps=None, max_ans=8):
    """The train.py argument list of one arm (q33 flags: AdamW, bf16, batch 256, final eval with chain-5 and every lesion)."""
    cfgs, counts = sizes(rung, b2_extra)
    check_bands(rung, cfgs, counts, exact_3m=not caps)
    a = ['--model', MODEL_OF[arm], '--cfg', json.dumps(cfgs[arm], sort_keys=True), '--data', data, '--steps', str(int(steps)), '--batch', str(BATCH),
         '--lr', repr(lr if lr is not None else RUNGS[rung]['lr']), '--seed', str(seed), '--log-every', '500', '--final-eval', '--max-ans', str(max_ans)]
    if caps:
        a += ['--caps', caps]
    if bf16:
        a.append('--bf16')
    if big_data:
        a += ['--big-data', big_data]
    if out:
        a += ['--out', out]
    if minutes:
        a += ['--minutes', repr(float(minutes))]
    return a


def table():
    rows = []
    for rung in RUNGS:
        cfgs, counts = sizes(rung)
        check_bands(rung, cfgs, counts)
        for arm in ARMS:
            rows.append(dict(rung=rung, arm=arm, model=MODEL_OF[arm], cfg=cfgs[arm], params=counts[arm],
                             vs_b2_pct=round(100 * (counts[arm] / counts[B2_ARM] - 1), 2),
                             vs_target_pct=round(100 * (counts[arm] / RUNGS[rung]['target'] - 1), 2), lr=RUNGS[rung]['lr']))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--rung', choices=list(RUNGS))
    ap.add_argument('--arm', choices=ARMS)
    ap.add_argument('--seed', type=int, default=400)
    ap.add_argument('--steps', type=int)
    ap.add_argument('--data', default='/job/pool')
    ap.add_argument('--out')
    ap.add_argument('--big-data')
    ap.add_argument('--minutes', type=float)
    ap.add_argument('--lr-scale', type=float, default=1.0, help='1 = the rung\'s lr; 0.5 = the sealed non-finite re-run')
    ap.add_argument('--max-ans', type=int, default=8)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--tkn', metavar='CAPS_JSON', help='print the 3M rung\'s TK and TKN configs, counts and --b2-extra strings under these caps (e.g. g8a/caps_g.json)')
    a = ap.parse_args(argv)
    if a.tkn:
        from custom_io.g8a import caps as CP
        caps = CP.apply(json.load(open(a.tkn)))
        loops = dict(n_loops=CP.n_loops_needed(caps)) if CP.n_loops_needed(caps) > 8 else {}      # what job.py adds to --b2-extra
        tk_user = {'eg_embed': True, 'tok_think': True}
        mlp, tkn_user, c_tk, c_tkn = tkn_mlp('3M', dict(tk_user, **loops))
        tkn_user = {k: v for k, v in tkn_user.items() if k not in loops}
        base = n('ledger', b2_cfg('3M', dict({'eg_embed': True}, **loops)))
        print(f'caps {a.tkn}: n_loops {loops.get("n_loops", 8)}; EGE (G-B2) {base:,}')
        for nm, u, c in (('TK', tk_user, c_tk), ('TKN', tkn_user, c_tkn)):
            cfgs, cnt = sizes('3M', dict(u, **loops))
            check_bands('3M', cfgs, cnt, exact_3m=False)      # job.py's 3% band (and PT within 2%)
            print(f'{nm}: trained {c:,} ({100 * (c / c_tk - 1):+.3f}% vs TK)  mlp {cfgs[B2_ARM]["mlp"]}  hidden {int(cfgs[B2_ARM]["mlp"] * 256)}  bands ok (PT {cnt[PT_ARM]:,})')
            print(f"  --b2-extra '{json.dumps(u)}'")
        return
    if a.rung and a.arm:
        print('python -m custom_io.train ' + ' '.join(shlex.quote(x) for x in train_args(
            a.rung, a.arm, a.seed, a.steps or 1, a.data, out=a.out, minutes=a.minutes, lr=RUNGS[a.rung]['lr'] * a.lr_scale, max_ans=a.max_ans, big_data=a.big_data)))
        return
    rows = table()
    if a.json:
        print(json.dumps(rows, indent=1))
        return
    for r in rows:
        print(f"{r['rung']:>4} {r['arm']:<4} {r['model']:<17} {r['params']:>12,}  vs B2 {r['vs_b2_pct']:+6.2f}%  vs target {r['vs_target_pct']:+6.2f}%  lr {r['lr']:.2e}  {json.dumps(r['cfg'], sort_keys=True)}")


if __name__ == '__main__':
    main()
