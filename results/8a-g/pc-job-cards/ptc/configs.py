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
from custom_io.data import ByteVocab, CharVocab
from custom_io.models import build

VOCAB = None
B2_ARM, PT_ARM, LLM_ARM = 'B2', 'PT', 'LLM'
B3_ARM = 'B3'
B3G2_ARM = 'B3G2'
PTS_ARM = 'PTS'         # B3 steps-for-all: the PT arm with all_steps on, eg_embed on, caps_b3s.json (asked for by name; not in ARMS)
PTC_ARM = 'PTC'         # PTS + calc_train (addendum AG): the plain model trained with the calculator (asked for by name; not in ARMS)
ARMS = (B2_ARM, PT_ARM, LLM_ARM)                      # the 8a arms (job.py's default); B3 is asked for by name
ALL_ARMS = ARMS + (B3_ARM, B3G2_ARM, PTS_ARM, PTC_ARM)
MODEL_OF = {B2_ARM: 'ledger', PT_ARM: 'plain_tf_steps_g', LLM_ARM: 'plain_lm', B3_ARM: 'b3', B3G2_ARM: 'b3g2', PTS_ARM: 'plain_tf_steps_g', PTC_ARM: 'plain_tf_steps_g'}
LADDER = ('3M', '10M', '30M')                          # the rungs of the 8a table (B2 / PT / LLM); B3 also has '100M'
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
    # B3's top rung (B3-GROUP1-BUILD sec. 6): the PLAN's 97.1M thinker shape, width 512, 8 heads, mlp 4.8, 21 blocks, no band. Its pool (the 600M pool) is not built
    # (the data thread's, waits for a GO), so the pool fields say so; lr = the 30M rule (1e-3 * 256 / width).
    '100M': dict(width=512, heads=8, mlp=4.8, blocks=21, target=None, band=None, pool='not built', seen='not built', lr=1e-3 * 256 / 512, own_rung=None, web=None),
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

# ---- the no-plug front (Ben, 4:12 PM ET: "can you remove the converter plug and just have our model match gemma's"; NO-PLUG-BUILD-SPEC-2026-10-11 sec. 2.4) ----
# {"noplug": true} in the extras (--b2-extra / the `extra` of b2_cfg, b3_cfg, plain_cfg, sizes, pts_cfg) switches the 30M and 100M rungs to width 512, 8 heads, eg_embed + eg_pre +
# eg_adapter 'none': our model reads Gemma's own 512 numbers (after its final norm, before its 512 -> 768 projection), no learned plug. The key itself never reaches a model:
# it becomes the cfg keys d / n_heads / eg_embed / eg_pre / eg_adapter. {"blocks": N} beside it overrides the default depth (mlp is solved again). Every arm that has a Gemma
# front takes it the same way (B2, B3, B3G2, PT / PTS; B3AT must extend the group-to-model mapping (`'b3g2' if group == 2 else 'b3'`) in b3_cfg, noplug_target, check_b3, MODEL_OF and ALL_ARMS). 3M and 10M raise.
NOPLUG = 'noplug'
NOPLUG_WIDTH, NOPLUG_HEADS = 512, 8
NOPLUG_BLOCKS = {'30M': 9, '100M': 21}      # default depth; mlp is solved to the target (30M: about 1.253; 100M: about 4.835)


def noplug_split(rung, extra):
    """extra -> (extra without the noplug key and without a `blocks` override, blocks or None, noplug on?). Raises for 3M and 10M."""
    ex = dict(extra or {})
    if not ex.pop(NOPLUG, False):
        return ex, None, False
    if rung not in NOPLUG_BLOCKS:
        raise ValueError(f"noplug is for the 30M and 100M rungs only: Gemma's own 512 numbers need a 512-wide model, and {rung} stays at width {RUNGS[rung]['width']} with the plug (3M and 10M are test scaffolding)")
    return ex, ex.pop('blocks', None), True


def rung_lr(rung, b2_extra=None):
    """The rung's lr. No plug at 30M: the model is 512 wide, so the width rule 1e-3 * 256 / width gives 5e-4 (the 100M rule), not the 384-wide 30M value. Disclosed default."""
    return 1e-3 * 256 / NOPLUG_WIDTH if (b2_extra or {}).get(NOPLUG) else RUNGS[rung]['lr']


def noplug_front():
    return dict(d=NOPLUG_WIDTH, n_heads=NOPLUG_HEADS, eg_embed=True, eg_pre=True, eg_adapter='none')


def solve_mlp(model, cfg, target):
    """cfg with the feed-forward ratio `mlp` set so the trained count of `model` lands as near `target` as one hidden unit allows (hidden = int(mlp * d), 2d + 1 params per
    hidden unit per block, mlp = (hidden + 0.5) / d, as b2_cfg's trim)."""
    d, c, best = cfg['d'], dict(cfg), None
    for _ in range(4):
        cur = n(model, c)
        if best is None or abs(cur - target) < abs(best[0] - target):
            best = (cur, c)
        if cur == target:
            break
        hid = int(c['mlp'] * d) + round((target - cur) / (c['blocks'] * (2 * d + 1)))
        c = dict(c, mlp=round((hid + 0.5) / d, 5))
    h0 = int(best[1]['mlp'] * d)
    for h in (h0 - 1, h0 + 1):      # the neighbours, in case the solve stopped one unit off
        c = dict(best[1], mlp=round((h + 0.5) / d, 5))
        if abs(n(model, c) - target) < abs(best[0] - target):
            best = (n(model, c), c)
    return best[1]


def noplug_target(rung, extra=None, group=2):
    """The count the no-plug arms are solved to: 30M = the rung's 30.0M; 100M = today's (plugged, 21 x 512, mlp 4.8) B3 group `group` count under the caps in force and the same
    other extras (102,641,692 for B3G2 under caps_b3g2.json)."""
    if rung == '30M':
        return RUNGS[rung]['target']
    ex, _, _ = noplug_split(rung, extra)
    return n('b3g2' if group == 2 else 'b3', b3_cfg(rung, ex, group))


def noplug_breakdown(model, cfg):
    """{piece: params} of a built model by top-level module: thinker ('core'), reader, writer, stop, ln_eg, other; no plug line (asserts there is no eg_proj / eg_hid)."""
    torch.manual_seed(0)
    m = build(model, vocab(cfg.get('bytes', False)), **cfg)
    out = {}
    for k, p in m.named_parameters():
        out[k.split('.')[0]] = out.get(k.split('.')[0], 0) + p.numel()
    assert 'eg_proj' not in out and 'eg_hid' not in out, 'no plug: the model must have no eg_proj / eg_hid'
    names = {'core': 'thinker', 'reader': 'reader', 'writer': 'writer', 'stop': 'stop', 'ln_eg': 'ln_eg'}
    res = {}
    for k, v in out.items():
        res[names.get(k, 'other')] = res.get(names.get(k, 'other'), 0) + v
    res['total'] = sum(out.values())
    return res


def vocab(bytes=False):
    """The vocab every count / size is built with: the 108-id CharVocab, or (V1 cfg {"bytes": true}) the 269-id ByteVocab."""
    global VOCAB
    if bytes:
        return ByteVocab()
    if VOCAB is None:
        VOCAB = CharVocab.build([])     # all printable ASCII + specials = 108 ids, the vocabulary every q33 run used
    return VOCAB


@functools.lru_cache(maxsize=None)
def count(model, cfg_json):
    """Trained parameter count of `model` built with cfg (a JSON string, for caching). Frozen borrowed parts are not in it."""
    torch.manual_seed(0)
    cfg = json.loads(cfg_json)
    return build(model, vocab(cfg.get('bytes', False)), **cfg).n_params()


def n(model, cfg):
    return count(model, json.dumps(cfg, sort_keys=True))


def _per_unit(model, cfg, key, base_v):
    """Parameters added by one more unit of `key` (blocks / n_layers): count(base_v + 1) - count(base_v). Exactly linear for these models."""
    return n(model, dict(cfg, **{key: base_v + 1})) - n(model, dict(cfg, **{key: base_v}))


def b2_cfg(rung, extra=None):
    """B2 config for a rung (copy talker on, 8 rounds). `extra` = reader switches, e.g. {"eg_embed": true} once stage 2b picks EGE."""
    r = RUNGS[rung]
    extra, nb, np_ = noplug_split(rung, extra)
    if np_:         # no plug: width 512 on Gemma's own numbers; default depth, mlp solved to the target (see noplug_target)
        base = dict(dict(noplug_front(), reader_layers=2, n_loops=8, mlp=r['mlp'], copy=True), **extra)
        return solve_mlp('ledger', dict(base, blocks=nb or NOPLUG_BLOCKS[rung]), noplug_target(rung, extra))
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


B3_G1 = dict(label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.25, eg_embed=True, any_round=True, gap_p=0.25)      # B3 group 1 (sec. 6)


B3_G2 = dict(B3_G1, no_slots=True, no_place=True, bytes=True, as_written=True)      # B3 group 2 (sec. 1): all switches on; the writer is always on in 'b3g2'
G2C3 = 4_022_440            # the plain 3M control at caps_b3 (g2c3): the plain arms' and test_pts' reference (4,022,440)
G2C3S = 4_023_976           # the plain 3M control with worked steps at caps_b3s (g2c3s; PLAN addendum 10-10 8:55 AM ET): group 2's partner since the 2:35 PM ET addendum and AT-0 (viii)'s reference; b3g2's 3M count sits within PLAIN_BAND of it


def b3g2_cfg(rung, extra=None):
    """B3 group 2 config for a rung: b3_cfg's path with B3_G2 and model 'b3g2'. 3M: the thinker is B2's S shape; since G2f the writer has no copy path and the freed parameters go to its MLP: writer_mlp
    (1/16 steps, 1/16 to 12) is the value whose trained count is closest to g2c3s (G2C3S; ties: the smaller); only if the count is then outside PLAIN_BAND of G2C3S is the thinker's feed-forward ratio mlp
    (hidden units) trimmed as before. 10M / 30M: block count to the rung's band (as
    b3_cfg); 100M: 21 x 512, no band. Call after caps.apply (the counts depend on the caps in force)."""
    return b3_cfg(rung, extra, group=2)


def b3_cfg(rung, extra=None, group=1):
    """B3 config for a rung, from the same code path as b2_cfg: 3M = B2's S shape; 10M / 30M = B2's rung widths with the block count chosen to the target (the
    feed-forward ratio trimmed only if the nearest count is outside the band); 100M = width 512, 8 heads, mlp 4.8, 21 blocks, no band. n_loops = max(8, n_res + 1)
    under the caps in force (call after caps.apply). `extra` = more switches (e.g. {"tok_think": true}, or n_loops from job.py), counted in the block choice."""
    from custom_io.models import ledger as L
    r = RUNGS[rung]
    loops = max(8, L.N_RES + 1)
    mod = 'b3g2' if group == 2 else 'b3'
    extra, nb, np_ = noplug_split(rung, extra)
    if np_:         # no plug; model-generic (any arm built on Ledger takes eg_pre: B3AT adds its group / model name here after the merge)
        base = dict(dict(noplug_front(), reader_layers=2, n_loops=loops, mlp=r['mlp']), **(B3_G2 if group == 2 else B3_G1))
        base.update(extra)
        return solve_mlp(mod, dict(base, blocks=nb or NOPLUG_BLOCKS[rung]), noplug_target(rung, extra, group))
    base = dict(dict(d=r['width'], n_heads=r['heads'], reader_layers=2, n_loops=loops, mlp=r['mlp']), **(B3_G2 if group == 2 else B3_G1))
    base.update(extra or {})
    n = lambda model, cfg: globals()['n']('b3g2' if group == 2 else model, cfg)
    if rung == '3M':
        cfg = dict(base, blocks=B2_S['blocks'])
        if group == 2:
            # the writer's MLP: the 1/16 step (1/16 .. 12) whose count is closest to g2c3s (ties: the smaller)
            cfg['writer_mlp'] = min(range(1, 193), key=lambda w: (abs(n('b3', dict(cfg, writer_mlp=w / 16)) - G2C3S), w)) / 16
            if abs(n('b3', cfg) / G2C3S - 1) > PLAIN_BAND:       # then the thinker's feed-forward ratio
                d = r['width']
                hid = int(cfg['mlp'] * d) + round((G2C3S - n('b3', cfg)) / (cfg['blocks'] * (2 * d + 1)))
                cfg['mlp'] = round((hid + 0.5) / d, 5)
    elif rung == '100M':
        cfg = dict(base, blocks=r['blocks'])
    else:
        c1, per = n('b3', dict(base, blocks=1)), _per_unit(mod, base, 'blocks', 1)
        best = min(range(1, 41), key=lambda b: abs(c1 + (b - 1) * per - r['target']))
        cfg = dict(base, blocks=best)
        if abs(n('b3', cfg) / r['target'] - 1) > r['band']:
            d = r['width']
            hid = int(r['mlp'] * d) + round((r['target'] - n('b3', cfg)) / (best * (2 * d + 1)))
            cfg['mlp'] = round((hid + 0.5) / d, 5)
    return cfg


def b3_sizes(cfg, model='b3'):
    """{'trained', 'frozen_gemma', 'whole'} of a B3 config (the frozen EmbeddingGemma 2 text part counts in the whole)."""
    torch.manual_seed(0)
    s = build(model, vocab(cfg.get('bytes', False)), **cfg).size()
    return dict(trained=s['trainable'], frozen_gemma=s['frozen_borrowed'], whole=s['whole'])


def b3g2_breakdown(cfg):
    """Trained parameters of a b3g2 config by part (G2f's printout): reader (without its place table), place (the reader's), thinker blocks (core), ctrl, step_emb, tape_emb, stop, the Gemma
    adapter (ln_eg + eg_proj), writer (its MLP fc1 + fc2 apart) and other (src, ln_z). The parts add up to the trained count."""
    torch.manual_seed(0)
    m = build('b3g2', vocab(cfg.get('bytes', False)), **cfg)
    c = lambda *ms: sum(p.numel() for x in ms for p in x.parameters() if p.requires_grad)
    out = dict(reader=c(m.reader) - c(m.reader.place), place=c(m.reader.place), thinker_blocks=c(m.core), ctrl=c(m.ctrl), step_emb=c(m.step_emb), tape_emb=c(m.tape_emb), stop=c(m.stop),
               gemma_adapter=c(m.ln_eg, m.eg_proj), writer=c(m.writer), writer_mlp=c(m.writer.fc1, m.writer.fc2), other=c(m.src, m.ln_z))
    out['total'] = m.n_params()
    assert out['total'] == sum(v for k, v in out.items() if k not in ('total', 'writer_mlp')), out       # writer_mlp is inside writer
    return out


def format_b3g2_breakdown(bd, cfg):
    """The 3M printout of b3g2_breakdown: the parts as a comma list, the writer's MLP shown INSIDE the writer ('writer 1,234 [of which mlp 567]'), so the listed top-level parts add up to the
    trained count (the old line listed writer and writer_mlp side by side and its parts summed to more than the total)."""
    parts = ', '.join(f'{k} {v:,}' + (f' [of which mlp {bd["writer_mlp"]:,}]' if k == 'writer' else '') for k, v in bd.items() if k not in ('total', 'writer_mlp'))
    return f'3M B3G2 trained {bd["total"]:,} ({100 * (bd["total"] / G2C3S - 1):+.2f}% from g2c3s {G2C3S:,}; writer_mlp {cfg["writer_mlp"]}): ' + parts


def check_b3(rung, cfg, group=1):
    """Group 2 (b3g2): 3M within PLAIN_BAND of g2c3s (4,023,976), 10M / 30M in the rung band, 100M no band. Group 1: 10M / 30M: trained count within the rung's band of its target; 3M: within 12% of G-B2 (EGE) under the same caps (the tool, its tape and the stop head add about 8%);
    100M: no band."""
    c = n('b3g2' if group == 2 else 'b3', cfg)
    if cfg.get('eg_pre'):       # no plug: 30M in its band, 100M within 1% of today's count (under the same other extras)
        assert rung in NOPLUG_BLOCKS, f'noplug at {rung}'
        drop = ('d', 'n_heads', 'eg_embed', 'eg_pre', 'eg_adapter', 'blocks', 'mlp', 'reader_layers')
        keep = {k: v for k, v in cfg.items() if k not in drop and k not in (B3_G2 if group == 2 else B3_G1)}
        tgt = noplug_target(rung, keep, group)
        band = RUNGS[rung]['band'] if RUNGS[rung]['band'] is not None else 0.01
        assert abs(c / tgt - 1) <= band, f'{rung} no-plug {c:,} outside {tgt:,.0f} +-{100 * band:.1f}%'
        return c
    if group == 2 and rung == '3M':
        assert abs(c / G2C3S - 1) <= PLAIN_BAND, f'3M B3G2 {c:,} is more than {100 * PLAIN_BAND:.0f}% from g2c3s {G2C3S:,}'
    elif rung in ('10M', '30M'):
        assert abs(c / RUNGS[rung]['target'] - 1) <= RUNGS[rung]['band'], f'{rung} B3 {c:,} outside {RUNGS[rung]["target"]:,.0f} +-{100 * RUNGS[rung]["band"]:.0f}%'
    elif rung == '3M' and group == 1:
        ref = n('ledger', b2_cfg('3M', dict(eg_embed=True, n_loops=cfg['n_loops'])))      # G-B2 (EGE) under the same caps
        assert abs(c / ref - 1) <= 0.12, f'3M B3 {c:,} is more than 12% from G-B2 {ref:,}'
    return c


def plain_cfg(rung, b2=None, extra=None):
    """Plain arm config matched to B2's trained size (+-2%): width as B2, nearest layer count with today's 4x feed-forward; only if that is
    outside the band is the feed-forward width trimmed (3M therefore stays plain_tf_steps' own 4 layers x 1024)."""
    r = RUNGS[rung]
    extra, nb, np_ = noplug_split(rung, extra)
    b2 = b2 or b2_cfg(rung, dict(extra, **{NOPLUG: True}, **({'blocks': nb} if nb else {})) if np_ else None)      # no plug and no b2 given: B2 is built with the rest of the extras and the blocks override too
    target = n('ledger', b2)
    d, h = (b2['d'], b2['n_heads']) if b2.get('eg_pre') else (r['width'], r['heads'])      # no plug: B2's 512 / 8 (eg_pre is the cfg key b2_cfg wrote)
    base = dict(d_model=d, n_heads=h, **({'eg_embed': True} if b2.get('eg_embed') else {}), **({'eg_pre': True} if b2.get('eg_pre') else {}))      # test 8a-G: the plain step arm gets the same frozen-Gemma front (its adapter counts)
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


def pts_cfg(rung, b2_extra=None):
    """PTS config (B3 steps-for-all): the PT arm's config with all_steps on. eg_embed is forced on (the G2C3 control's front), so PTS and its PT control
    differ only by the target; the switch adds no weights, so PTS's count equals PT's under the same caps: 4,022,440 at 3M under caps_b3 (= G2C3). The arm itself
    pins caps_b3s.json (plain_target 115, not 109): MAX_NEW and MAX_POS grow by 6 and the position table by 6 x d_model parameters, so under its own caps PTS and
    a PT in the same job count the same, 6 x d_model above G2C3 (tests/test_pts.py measures both)."""
    cfgs, _ = sizes(rung, dict(b2_extra or {}, eg_embed=True))
    return dict(cfgs[PT_ARM], all_steps=True)


def add_pts(rung, cfgs, counts, b2_extra=None):
    """Adds the PTS entry to cfgs and counts (in place) and returns them."""
    cfgs[PTS_ARM] = pts_cfg(rung, b2_extra)
    counts[PTS_ARM] = n(MODEL_OF[PTS_ARM], cfgs[PTS_ARM])
    return cfgs, counts


def ptc_cfg(rung, b2_extra=None):
    """PTC config (addendum AG): PTS's config plus calc_train. The switch adds no weights, so PTC's count equals PTS's."""
    return dict(pts_cfg(rung, b2_extra), calc_train=True)


def add_ptc(rung, cfgs, counts, b2_extra=None):
    """Adds the PTC entry to cfgs and counts (in place) and returns them."""
    cfgs[PTC_ARM] = ptc_cfg(rung, b2_extra)
    counts[PTC_ARM] = n(MODEL_OF[PTC_ARM], cfgs[PTC_ARM])
    return cfgs, counts


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
    if cfgs[B2_ARM].get('eg_pre'):      # no plug (30M / 100M): B2 solved to the target, the plain arms within PLAIN_BAND of B2
        keep = {k: v for k, v in cfgs[B2_ARM].items() if k in ('n_loops',)}
        tgt = noplug_target(rung, keep)
        assert abs(b2 / tgt - 1) <= (r['band'] or 0.01), f'{rung} no-plug B2 {b2:,} outside {tgt:,.0f}'
        for a in (PT_ARM, PTS_ARM, PTC_ARM):
            if a in counts:
                assert abs(counts[a] / b2 - 1) <= PLAIN_BAND, f'{rung} {a} {counts[a]:,} is not within {100 * PLAIN_BAND:.0f}% of B2 {b2:,}'
        return counts
    eg = bool(cfgs[B2_ARM].get('eg_embed'))
    ref = B2_S_PARAMS + (eg_adapter_params(r['width']) if eg else 0)      # test 8a-G: B2_S + the adapter (EGE-3M, 3,500,881 at the old caps)
    if rung == '3M':
        if exact_3m:
            assert b2 == ref, f'3M B2 must be today\'s {ref:,}, got {b2:,}'
        else:           # caps sized from the data (addendum E) grow the position / place / workspace tables: the 3M rung is then the architecture AT those caps (G1's caps: +1.3%;
                        # B3's caps_b3, 2,000-letter inputs: +15%), a matched pair with its plain control (checked below, within PLAIN_BAND of each other); nothing is shrunk
                        # to hit today's count. Only a runaway (+50%) is refused. The count and its distance from today's go to box.json.
            assert b2 / ref - 1 <= 0.5, f'3M B2 {b2:,} is more than 50% above today\'s {ref:,}: the caps are out of range'
    else:
        assert abs(b2 / r['target'] - 1) <= r['band'], f'{rung} B2 {b2:,} outside {r["target"]:,.0f} +-{100 * r["band"]:.0f}%'
    for a in (PT_ARM, LLM_ARM, PTS_ARM, PTC_ARM):
        if a not in counts:
            continue
        assert abs(counts[a] / b2 - 1) <= PLAIN_BAND, f'{rung} {a} {counts[a]:,} is not within {100 * PLAIN_BAND:.0f}% of B2 {b2:,}'
    return counts


def train_args(rung, arm, seed, steps, data, out=None, minutes=None, lr=None, b2_extra=None, bf16=True, big_data=None, caps=None, max_ans=8):
    """The train.py argument list of one arm (q33 flags: AdamW, bf16, batch 256, final eval with chain-5 and every lesion)."""
    if arm in (B3_ARM, B3G2_ARM):           # B3: its own config; b2_extra carries its extra switches / n_loops, the PT and LLM arms are not built
        g = 2 if arm == B3G2_ARM else 1
        cfgs = {arm: b3_cfg(rung, b2_extra, g)}
        check_b3(rung, cfgs[arm], g)
    else:
        cfgs, counts = sizes(rung, b2_extra)
        if arm == PTS_ARM:              # PTS: its own entry (PT's config + all_steps), checked against B2 like PT
            assert caps, 'PTS needs --caps (caps_b3s.json applied by train.py): without them MAX_NEW / MAX_POS are the default 76 / 288 and a long target is cut at decoding'
            add_pts(rung, cfgs, counts, b2_extra)
        if arm == PTC_ARM:              # PTC: PTS's entry + calc_train, the same caps pin
            assert caps, 'PTC needs --caps (caps_b3s.json applied by train.py): without them MAX_NEW / MAX_POS are the default 76 / 288 and a long target is cut at decoding'
            add_ptc(rung, cfgs, counts, b2_extra)
        check_bands(rung, cfgs, counts, exact_3m=not caps)
    a = ['--model', MODEL_OF[arm], '--cfg', json.dumps(cfgs[arm], sort_keys=True), '--data', data, '--steps', str(int(steps)), '--batch', str(BATCH),
         '--lr', repr(lr if lr is not None else rung_lr(rung, b2_extra)), '--seed', str(seed), '--log-every', '500', '--final-eval', '--max-ans', str(max_ans)]
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


def b3_table():
    """One row per rung: trained / frozen Gemma / whole of B3 under the caps in force."""
    rows = []
    for rung in RUNGS:
        cfg = b3_cfg(rung)
        check_b3(rung, cfg)
        rows.append(dict(rung=rung, cfg=cfg, **b3_sizes(cfg)))
    return rows


def b3g2_table():
    """One row per rung: trained / frozen Gemma / whole of B3 group 2 under the caps in force (use caps_b3g2.json: LE 95)."""
    rows = []
    for rung in RUNGS:
        cfg = b3g2_cfg(rung)
        check_b3(rung, cfg, 2)
        rows.append(dict(rung=rung, cfg=cfg, **b3_sizes(cfg, 'b3g2')))
    return rows


def table():
    rows = []
    for rung in LADDER:
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
    ap.add_argument('--arm', choices=ALL_ARMS)
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
    ap.add_argument('--group', type=int, choices=(1, 2), default=None, help='with --b3: the table of B3 group 1 (b3) or group 2 (b3g2; use g8a/caps_b3g2.json); default 1. With --noplug the default is 2 (the no-plug arms are B3G2 under caps_b3g2.json); an explicit --group 1 still gives group 1')
    ap.add_argument('--noplug', metavar='CAPS_JSON', help='print the no-plug 30M and 100M counts with their breakdown (thinker, reader, writer, stop, ln_eg) under these caps (g8a/caps_b3g2.json), for every blocks override, plus the plain step control; --group defaults to 2 here (B3G2)')
    ap.add_argument('--b3', metavar='CAPS_JSON', help='print the B3 rung table (trained / frozen Gemma / whole at 3M, 10M, 30M, 100M) under these caps (g8a/caps_g.json = G1\'s, g8a/caps_b3.json = 2,000 letters)')
    a = ap.parse_args(argv)
    a.group = a.group or (2 if a.noplug else 1)         # --group not given: 1, except --noplug (B3G2 caps) = 2
    if a.noplug:
        from custom_io.g8a import caps as CP
        CP.apply(json.load(open(a.noplug)))
        g, mod = a.group, 'b3g2' if a.group == 2 else 'b3'
        for rung, blocks in (('30M', (None,)), ('100M', (None, 26, 30, 34, 37))):
            for bl in blocks:
                ex = dict({NOPLUG: True}, **({'blocks': bl} if bl else {}))
                cfg = b3_cfg(rung, ex, g)
                c = check_b3(rung, cfg, g)
                bd = noplug_breakdown(mod, cfg)
                pt = plain_cfg(rung, b2_cfg(rung, ex))
                print(f'{rung} noplug {mod} blocks {cfg["blocks"]} mlp {cfg["mlp"]}: trained {c:,}  ' + '  '.join(f'{k} {v:,}' for k, v in bd.items()) + f'  | plain step control {n("plain_tf_steps_g", pt):,} ({pt["n_layers"]} layers, hidden {pt.get("hidden", 4 * pt["d_model"])}, {100 * (n("plain_tf_steps_g", pt) / c - 1):+.2f}% vs {mod})')
        return
    if a.b3:
        from custom_io.g8a import caps as CP
        caps = CP.apply(json.load(open(a.b3)))
        g2 = a.group == 2
        print(f'caps {a.b3}: le {caps["le"]}; max_prompt {caps["max_prompt"]}, n_num {caps["n_num"]}, w_max {caps["w_max"]}, n_res {caps["n_res"]}, n_reg {caps["n_reg"]}; n_loops {max(8, caps["n_res"] + 1)}; tape {max(16, caps["n_res"])}')
        print(f'{"rung":>5} {"trained":>13} {"frozen Gemma":>13} {"whole":>13}  shape')
        for r in (b3g2_table() if g2 else b3_table()):
            c = r['cfg']
            print(f'{r["rung"]:>5} {r["trained"]:>13,} {r["frozen_gemma"]:>13,} {r["whole"]:>13,}  d {c["d"]} heads {c["n_heads"]} blocks {c["blocks"]} mlp {c["mlp"]} n_loops {c["n_loops"]}'
                  + (f' writer_mlp {c["writer_mlp"]}' if 'writer_mlp' in c else '') + ('   (pool: ' + RUNGS[r['rung']]['pool'] + ')' if isinstance(RUNGS[r['rung']]['pool'], str) else ''))
        if g2:
            cfg = b3g2_cfg('3M')
            bd = b3g2_breakdown(cfg)
            print(format_b3g2_breakdown(bd, cfg))
        return
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
        assert a.arm != B3_ARM or a.rung in RUNGS
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
