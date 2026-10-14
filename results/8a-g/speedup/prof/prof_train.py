#!/usr/bin/env python3
"""prof_train.py - where does the run time of a custom_io training job go, and which exact speedups are worth having?

It replays custom_io/train.py's update loop (bf16 autocast, fused AdamW, split_batch -> loss/len(parts) -> backward per micro-batch, clip_grad_norm_, step) at
the real rung shapes on the real pool, and measures it. Nothing under custom_io is edited: variants are monkeypatches / wrappers made here.

  python prof_train.py --arm PTS --rung 3M --accum 16 --data POOL_DIR --pkg-root SRC_DIR --out out/pts.json
  python prof_train.py --arm B3G2 --rung 3M --accum 32 --data POOL_DIR --pkg-root SRC_DIR --out out/b3g2.json
  (--pkg-root = the folder that CONTAINS custom_io/, e.g. the PC job's src-b3g2 / src-ptc; PTC needs src-ptc. EmbeddingGemma 2 is found as in job.py:
   $CUSTOM_IO_EG2 (a folder) or the hub revision; PYTHONPATH must give transformers >= 5.19.)

Sections (--sections, comma list; default breakdown,throughput,profiler,padding,sweep,syncs):
  breakdown   per-update times, mean / median / p90 over --updates after --warmup: fetch, prep+split, h2d, forward (per module and per python method, exclusive),
              backward, clip, optimizer, other. Every timed region is bracketed by torch.cuda.synchronize(), so it is true GPU+CPU time of that region but the syncs
              themselves slow the update; `throughput` is the same loop with no inner syncs.
  throughput  free-running seconds per update (one sync at each end of a chunk of updates) and peak memory: the number to compare variants with.
  profiler    torch.profiler (wait/warmup/active): top-25 CUDA kernels, top-25 CPU ops, kernel launches per update, mean kernel time, GPU busy fraction.
  padding     real-token fraction of the padded positions on the real batches: now (full batch width), micro-batch own widest, sorted + own widest.
  sweep       seconds per update and peak memory for accum in 1 2 4 8 16 32 (same rows; OOM caught).
  syncs       CUDA only: every host-device synchronisation in an update, by python file:line (torch.cuda.set_sync_debug_mode).
  bench       --bench-list "baseline;sortpad;sortpad,bigmb": A/B/A/B free-running seconds per update of each variant spec.
  equiv       (--equiv-check) each variant vs baseline on the same seed and the same 256 rows: loss diff, gradient cosine / relative L2 in fp32 and bf16 autocast,
              then --curve-updates updates of loss curve.
Variants (--variant a,b composes; see --list-variants): sortpad sortpad_tokw oldw bigmb tf32 sdpa compile compile_ro eg_sorted eg_once prefetch.
The equiv section implements the fixed checks of PREREG-eg-once.md: E1 / E2 (Gemma vectors, eg_once vs the old path), E3 (loss + gradient of one update, with a per-token
weighting report), E4 (300-update loss trace).
"""
import argparse, collections, contextlib, datetime, gc, importlib, json, math, os, platform, queue, random, sys, threading, time, types, warnings, zlib
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

T0 = time.time()
PK = None                       # the custom_io modules (load_pkg)
SECTION_ORDER = ('breakdown', 'throughput', 'profiler', 'padding', 'sweep', 'syncs', 'bench', 'equiv')
DEFAULT_SECTIONS = 'breakdown,throughput,profiler,padding,sweep,syncs'
ACCUMS = (1, 2, 4, 8, 16, 32)
# the accum each PC queue line uses (8aG2C3S / 8aPTC3S: PTS=16, PTC=16; 8aB3G2s400: B3G2=32); PT / B2 are guesses, override with --accum
ARM_INFO = {
    'PTS': dict(accum=16, caps='caps_b3s.json'), 'PTC': dict(accum=16, caps='caps_b3s.json'), 'PT': dict(accum=16, caps='caps_g.json'),
    'B2': dict(accum=16, caps='caps_g.json'), 'B3G2': dict(accum=32, caps='caps_b3g2.json'),
}


def log(*a):
    print('[%7.1fs]' % (time.time() - T0), *a, flush=True)


class Skip(Exception):
    """A variant / section that cannot run here (no CUDA, no compiler, no EG front ...): recorded, never fatal."""


def load_pkg(pkg_root=None):
    """Import custom_io from pkg_root (the folder that contains custom_io/) or from sys.path. Fills PK."""
    global PK
    if pkg_root:
        sys.path.insert(0, os.path.abspath(pkg_root))
    ns = types.SimpleNamespace()
    ns.D = importlib.import_module('custom_io.data')
    ns.TR = importlib.import_module('custom_io.train')
    ns.CP = importlib.import_module('custom_io.g8a.caps')
    ns.C = importlib.import_module('custom_io.g8a.configs')
    ns.models = importlib.import_module('custom_io.models')
    ns.root = os.path.dirname(os.path.dirname(os.path.abspath(ns.D.__file__)))
    PK = ns
    return ns


def seed_all(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# clocks and section recorders
# ------------------------------------------------------------------------------------------------------------------------------------------------------
class Clock:
    """perf_counter after a CUDA sync (CPU: plain perf_counter). Every timed region starts and ends on one, so the number is that region's own time."""

    def __init__(self, device):
        self.cuda = device.type == 'cuda'

    def now(self):
        if self.cuda:
            torch.cuda.synchronize()
        return time.perf_counter()


@contextlib.contextmanager
def stage(clock, acc, name):
    t0 = clock.now()
    try:
        yield
    finally:
        acc[name] += clock.now() - t0


class Recorder:
    """Exclusive / inclusive time of nested sections (forward hooks and wrapped methods). enter() / exit() are the only API.
    Forward phase: times each section between two syncs, exclusive = inclusive - children. Backward phase (phase 'bwd'): only counts the calls, which is how
    gradient-checkpoint recomputation shows up (a forward hook firing during backward)."""

    def __init__(self, clock):
        self.clock, self.active, self.phase = clock, False, 'fwd'
        self.excl, self.incl, self.calls = collections.defaultdict(float), collections.defaultdict(float), collections.defaultdict(int)
        self.bwd_calls = collections.defaultdict(int)
        self.stack = []

    def reset(self):
        self.excl.clear(); self.incl.clear(); self.calls.clear(); self.bwd_calls.clear(); self.stack.clear(); self.phase = 'fwd'

    def enter(self, name):
        if not self.active:
            return None
        if self.phase != 'fwd':
            self.bwd_calls[name] += 1
            return None
        self.stack.append([name, self.clock.now(), 0.0])
        return True

    def exit(self, tok):
        if tok is None or not self.stack:
            return
        name, t0, child = self.stack.pop()
        dur = self.clock.now() - t0
        self.excl[name] += dur - child
        self.incl[name] += dur
        self.calls[name] += 1
        if self.stack:
            self.stack[-1][2] += dur


METHODS = ('read', 'tokenize', 'num_memory', 'slot_kv', 'tape_of', 'read_texts', 'eg_term', 'tok_spots', 'think', 'train_golds', 'plan', 'answer_teacher', 'call_pass',
           'ans_pass', '_targets', '_set_front', '_calc_loss_mask', 'loop', '_loss', 'word_keys', 'word_content', 'memory',
           'run', 'gold', 'round_loss', 'span_loss', 'talk', 'gen_copy')      # run .. gen_copy: ledger.py (B2)
EG_METHODS = ('encode', 'encode_texts', '_compute', 'align')
_MISSING = object()


class Instrument:
    """Forward hooks on the top-level children of the model (ModuleLists one level down: core.0, blocks.3 ...) and timing wrappers on the python-side methods that
    forward hooks cannot see (tokenize, tape_of, EG front, ByteWriter.teacher ...). level 'top' = that; 'deep' adds every module at depth 2. remove() restores all."""

    def __init__(self, model, rec, level='top', methods=True):
        self.model, self.rec, self.level, self.methods = model, rec, level, methods
        self.handles, self.patches, self.names = [], [], []

    def _hook(self, mod, name):
        toks = []
        self.handles.append(mod.register_forward_pre_hook(lambda m, i: toks.append(self.rec.enter(name))))
        self.handles.append(mod.register_forward_hook(lambda m, i, o: self.rec.exit(toks.pop() if toks else None)))
        self.names.append(name)

    def _wrap(self, obj, attr, name, static_cls=False):
        if static_cls:
            prev = obj.__dict__[attr]
            fn = prev.__func__
        else:
            fn = getattr(obj, attr)
            prev = obj.__dict__.get(attr, _MISSING)
        rec = self.rec

        def w(*a, **k):
            tok = rec.enter(name)
            try:
                return fn(*a, **k)
            finally:
                rec.exit(tok)
        setattr(obj, attr, staticmethod(w) if static_cls else w)
        self.patches.append((obj, attr, prev, static_cls))
        self.names.append(name)

    def install(self):
        containers = (nn.ModuleList, nn.Sequential, nn.ModuleDict)
        for name, ch in self.model.named_children():
            if isinstance(ch, containers):
                for n2, c2 in ch.named_children():
                    self._hook(c2, f'{name}.{n2}')
            else:
                self._hook(ch, name)
                if self.level == 'deep':
                    for n2, c2 in ch.named_children():
                        if not isinstance(c2, containers):
                            self._hook(c2, f'{name}.{n2}')
        if not self.methods:
            return self
        for n in METHODS:
            if callable(getattr(self.model, n, None)):
                self._wrap(self.model, n, 'm/' + n)
        eg = self.model.eg() if hasattr(self.model, 'eg') and getattr(self.model, 'eg_embed', False) else None
        if eg is not None:
            for n in EG_METHODS:
                if callable(getattr(eg, n, None)):
                    self._wrap(eg, n, 'm/eg.' + n)
            if hasattr(eg, 'load') and hasattr(eg, 'm'):
                self._wrap_load(eg)
        if hasattr(self.model, 'writer'):
            wmod = importlib.import_module('custom_io.models.writer')
            if isinstance(wmod.ByteWriter.__dict__.get('teacher'), staticmethod):
                self._wrap(wmod.ByteWriter, 'teacher', 'm/writer.teacher', static_cls=True)
        return self

    def _wrap_load(self, eg):
        """The frozen Gemma's own forward (eg.m), hooked once it is loaded."""
        fn, inst = eg.load, self
        prev = eg.__dict__.get('load', _MISSING)

        def load(device):
            r = fn(device)
            if getattr(eg, 'm', None) is not None and not getattr(eg, '_prof_hooked', False):
                eg._prof_hooked = True
                inst._hook(eg.m, 'eg.gemma_forward')
            return r
        eg.load = load
        self.patches.append((eg, 'load', prev, False))

    def remove(self):
        for h in self.handles:
            h.remove()
        for obj, attr, prev, static_cls in reversed(self.patches):
            if static_cls:
                setattr(obj, attr, prev)
            elif prev is _MISSING:
                obj.__dict__.pop(attr, None)
            else:
                setattr(obj, attr, prev)
        self.handles, self.patches = [], []


ROLLUP = [      # (group, name test): first match wins; unmatched sections go to 'other_modules'
    ('eg_front', lambda n: n.startswith('m/eg') or n.startswith('eg.') or n in ('ln_eg', 'eg_proj', 'eg_hid', 'm/eg_term', 'm/_set_front', 'm/tok_spots')),
    ('reader', lambda n: n in ('reader', 'm/read')),
    ('thinker_blocks', lambda n: n.startswith('core.') or n.startswith('blocks.') or n in ('m/think', 'step_emb', 'ctrl')),
    ('writer', lambda n: n in ('writer', 'm/answer_teacher', 'm/writer.teacher', 'm/call_pass', 'm/ans_pass')),
    ('tape_read', lambda n: n in ('m/tape_of', 'm/read_texts')),
    ('host_prep', lambda n: n in ('m/oldw.precompute', 'm/train_golds', 'm/plan', 'm/_targets', 'm/tokenize', 'm/_calc_loss_mask', 'm/num_memory', 'm/slot_kv', 'm/word_keys', 'm/word_content', 'm/memory', 'm/gold')),
    ('loop_glue', lambda n: n in ('m/loop', 'm/_loss', 'm/run', 'm/talk', 'm/round_loss', 'm/span_loss', 'm/gen_copy')),
    ('embed_norm', lambda n: n in ('tok', 'pos', 'ln_f', 'place')),
]


def rollup_group(name):
    for g, test in ROLLUP:
        if test(name):
            return g
    return 'other_modules'


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# stub Gemma and synthetic rows (CPU smoke tests only)
# ------------------------------------------------------------------------------------------------------------------------------------------------------
class _StubGemma(nn.Module):
    """Tiny causal stand-in for FrozenEG.m: last_hidden_state = emb + 0.5 * running mean of emb over the real tokens, zero on padding. Like the real one it only
    depends on the REAL tokens of a row, not on how long the padded batch is (up to float rounding of the real thing, which this stub does not have)."""

    def __init__(self, seed=0):
        super().__init__()
        self.register_buffer('table', torch.randn(997, 768, generator=torch.Generator().manual_seed(seed)))
        self.norm = nn.Identity()

    def forward(self, input_ids, attention_mask):
        m = attention_mask[..., None].to(self.table.dtype)
        e = self.table[input_ids % 997] * m
        ctx = e.cumsum(1) / m.cumsum(1).clamp(min=1)
        return types.SimpleNamespace(last_hidden_state=(e + 0.5 * ctx) * m)


class StubEG:
    """Stand-in for models/eg.FrozenEG on CPU, with the same surface (load / m / tok / align / encode with the last-call memo / encode_texts / _compute): a token is 4
    characters, the 'Gemma' is _StubGemma. _compute follows eg.py's, so everything that works on the stub (eg_once, eg_sorted, the hooks) exercises the same code paths
    as on the real front. Not a cost model."""
    pre = False
    by_bytes = False

    def __init__(self, seed=0):
        self.seed, self.m, self.tok = seed, None, types.SimpleNamespace(pad_token_id=0)
        self._align, self._last = {}, None
        self.passes, self.text_passes = 0, 0

    def load(self, device):
        if self.m is None:
            self.m = _StubGemma(self.seed).eval()
        if self.m.table.device != torch.device(device):
            self.m.to(device)
        return self

    def align(self, prompt):
        hit = self._align.get(prompt)
        if hit is None:
            n = len(prompt)
            ntok = max(1, -(-n // 4))
            ids = np.array([1 + zlib.crc32(prompt[4 * j:4 * j + 4].encode('utf-8', errors='replace')) % 996 for j in range(ntok)], np.int32)
            hit = self._align[prompt] = (ids, (np.arange(n) // 4).astype(np.int16))
        return hit

    def encode(self, prompts, T, device, chars=True):
        key = (tuple(prompts), T, str(device))
        if self._last is not None and self._last[0] == key and (self._last[1][0] is not None or not chars):
            return self._last[1]
        out = self._compute(prompts, T, device, chars)
        self._last = (key, out)
        return out

    @torch.no_grad()
    def encode_texts(self, texts, T, device):
        self.text_passes += 1
        return self._compute(texts, T, device, True)[0]

    @torch.no_grad()
    def _compute(self, prompts, T, device, chars):
        self.load(device)
        self.passes += 1
        al = [self.align(p) for p in prompts]
        B, L = len(al), max(len(a[0]) for a in al)
        ids = np.full((B, L), self.tok.pad_token_id, np.int64)
        am = np.zeros((B, L), np.int64)
        for b, (t, _) in enumerate(al):
            ids[b, :len(t)], am[b, :len(t)] = t, 1
        ids, am = torch.from_numpy(ids).to(device), torch.from_numpy(am).to(device)
        Ht = self.m(input_ids=ids, attention_mask=am).last_hidden_state
        w = am[..., None].float()
        pooled = (Ht.float() * w).sum(1) / w.sum(1)
        H = None
        if chars:
            c2t, cm = np.zeros((B, T), np.int64), np.zeros((B, T), bool)
            for b, (_, c) in enumerate(al):
                n = min(len(c), T)
                c2t[b, :n], cm[b, :n] = c[:n], True
            c2t, cm = torch.from_numpy(c2t).to(device), torch.from_numpy(cm).to(device)
            H = Ht.gather(1, c2t[..., None].expand(-1, -1, Ht.shape[-1])) * cm[..., None].to(Ht.dtype)
        return (H, pooled)


_WORDS = ('apple river stone lamp cloud garden window music paper silver forest table orange bridge candle pocket winter thunder ladder button mirror basket').split()


def synth_rows(n, max_letters=280, seed=0):
    """Skills-shaped rows (half: a two-step story with worked steps) and cloze-shaped rows (half: web-like text with one ____ blank, no steps), lengths skewed
    short with a long tail up to max_letters. Content is meaningless; only for CPU smoke tests and unit tests."""
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        if i % 2 == 0:
            a, b, c = rng.randint(10, 900), rng.randint(10, 900), rng.randint(1, 9)
            pad = ' '.join(rng.choice(_WORDS) for _ in range(rng.randint(0, 20)))
            q = f'Tom has {a} apples and buys {b} more, then gives {c} away. How many apples now?'
            rows.append(dict(id=f's{i}', prompt=(pad + '. ' + q) if pad else q, answer=str(a + b - c), accepted=[str(a + b - c)], family='chain_story2', level=1, stage=1,
                             variant='v', steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}']))
        else:
            target = int(60 + (max_letters - 60) * rng.random() ** 2)
            words = []
            while sum(len(w) + 1 for w in words) < target:
                words.append(rng.choice(_WORDS))
            k = rng.randrange(len(words))
            ans = words[k]
            words[k] = '____'
            rows.append(dict(id=f'c{i}', prompt=' '.join(words)[:max_letters], answer=ans, accepted=[ans], family='cloze', level=0, stage=0, variant='cloze', steps=[]))
    for r in rows:
        if '____' not in r['prompt'] and r['family'] == 'cloze':
            r['prompt'] = r['prompt'][:max_letters - 5] + ' ____'
    return rows


def sample_jsonl(path, n, seed=0):
    """n rows drawn uniformly from a jsonl file without parsing the rest (two passes: count lines, then parse the chosen ones); n <= 0 = all."""
    keep = PK.D.KEEP
    total = 0
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 24), b''):
            total += chunk.count(b'\n')
    if n <= 0 or n >= total:
        return PK.D.load_rows(path)
    pick = set(np.random.RandomState(seed).choice(total, n, replace=False).tolist())
    rows = []
    with open(path, encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i in pick:
                r = json.loads(line)
                rows.append({k: r[k] for k in keep if k in r})
    return rows


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# the world: caps, config, rows, vocab, model factory
# ------------------------------------------------------------------------------------------------------------------------------------------------------
def tiny_cfg(arm, caps):
    """The CPU smoke shapes of g8a/speed.py / b3_cost.py (d 48, 1 block)."""
    C = PK.C
    if arm == 'B3G2':
        return 'b3g2', dict(dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0), n_loops=PK.CP.n_loops_needed(caps), **C.B3_G2)
    if arm in ('PTS', 'PTC', 'PT'):
        cfg = dict(d_model=48, n_heads=2, n_layers=1, eg_embed=True)
        if arm in ('PTS', 'PTC'):
            cfg['all_steps'] = True
        if arm == 'PTC':
            cfg['calc_train'] = True
        return 'plain_tf_steps_g', cfg
    if arm == 'B2':
        return 'ledger', dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0, n_loops=PK.CP.n_loops_needed(caps), copy=True, eg_embed=True)
    raise SystemExit(f'--tiny: no tiny shape for arm {arm}')


class World:
    """Everything one job fixes before training: caps applied, cfg, rows + vocab, a model factory (every model built here starts from the same seeded init and
    shares ONE EG front object, so the Gemma is loaded once)."""

    def __init__(self, args):
        a, self.a = args, args
        self.device = torch.device('cuda' if a.device == 'auto' and torch.cuda.is_available() else 'cpu' if a.device == 'auto' else a.device)
        self.amp = (lambda: torch.autocast(self.device.type, dtype=torch.bfloat16)) if a.bf16 and self.device.type == 'cuda' else contextlib.nullcontext
        info = ARM_INFO[a.arm]
        self.synthetic = a.data == 'synthetic'
        if not self.synthetic and not os.path.exists(os.path.join(a.data, 'train.jsonl')):
            raise SystemExit(f'--data {a.data}: no train.jsonl there (pass the pool dir, or --data synthetic)')
        caps_name = a.caps or ('caps_g.json' if self.synthetic and a.tiny else info['caps'])
        caps_path = caps_name if os.path.isabs(caps_name) or os.path.exists(caps_name) else os.path.join(PK.root, 'custom_io', 'g8a', caps_name)
        self.caps_path = caps_path
        self.caps = PK.CP.apply(json.load(open(caps_path)))
        self.ex = {'eg_embed': True}
        if PK.CP.n_loops_needed(self.caps) > 8:
            self.ex['n_loops'] = PK.CP.n_loops_needed(self.caps)
        self.ex.update(json.loads(a.b2_extra))
        self.model_name, self.cfg = self._config()
        self.lr = PK.C.rung_lr(a.rung, self.ex)
        self.bytes = bool(self.cfg.get('bytes'))
        if self.synthetic:
            max_letters = min(a.synth_letters or self.caps['max_prompt'], self.caps['max_prompt'])
            self.rows = synth_rows(a.rows or 4000, max_letters, seed=a.seed)
            self.data_desc = f'synthetic(max_letters={max_letters})'
        else:
            self.rows = sample_jsonl(os.path.join(a.data, 'train.jsonl'), 200000 if a.rows is None else a.rows, a.seed)
            self.data_desc = a.data
        D = PK.D
        if self.bytes:
            self.vocab = D.ByteVocab()
        elif not self.synthetic and os.path.exists(os.path.join(a.data, 'charvocab.json')):
            self.vocab = D.CharVocab.load(os.path.join(a.data, 'charvocab.json'))
        elif not self.synthetic:
            self.vocab = D.CharVocab.build(self.rows)       # train.py: CharVocab.get -> printable ASCII + the characters of the rows
        else:
            self.vocab = D.CharVocab.build([])
        self.ds = D.Dataset(self.rows, self.vocab)
        self.eg_mode = a.eg if a.eg != 'auto' else ('stub' if (a.tiny or self.device.type != 'cuda') else 'real')
        self.eg = None
        self.n_params = None
        self.new_model(a.seed)          # validates the config and fills n_params / the shared EG object (the Gemma itself loads on first use)
        log(f'world: arm {a.arm} model {self.model_name} ({self.n_params:,} trained params) rows {len(self.rows)} data {self.data_desc} caps {os.path.basename(caps_path)} device {self.device} eg {self.eg_mode}')

    def _config(self):
        a, C = self.a, PK.C
        if a.tiny:
            return tiny_cfg(a.arm, self.caps)
        if a.arm == 'B3G2':
            cfg = C.b3_cfg(a.rung, self.ex, 2)
            C.check_b3(a.rung, cfg, 2)
            return 'b3g2', cfg
        cfgs, counts = C.sizes(a.rung, self.ex)
        if a.arm == 'PTS':
            C.add_pts(a.rung, cfgs, counts, self.ex)
        elif a.arm == 'PTC':
            if not hasattr(C, 'add_ptc'):
                raise SystemExit('arm PTC needs the PTC overlay (src-ptc): pass --pkg-root <src-ptc>')
            C.add_ptc(a.rung, cfgs, counts, self.ex)
        return C.MODEL_OF[a.arm], cfgs[a.arm]

    def new_model(self, seed):
        torch.manual_seed(seed)
        m = PK.models.build(self.model_name, self.vocab, **self.cfg).to(self.device)
        if getattr(m, 'eg_embed', False) and hasattr(m, '_eg'):
            if self.eg is None:
                self.eg = StubEG() if self.eg_mode == 'stub' else m.eg()
            m._eg = [self.eg]
        if self.n_params is None:
            self.n_params = m.n_params()
        return m

    def batches(self, seed):
        return PK.D.train_batches(self.ds, self.a.batch, 'shuffled', seed)

    def meta(self):
        a = self.a
        return dict(arm=a.arm, rung=a.rung, accum=a.accum, batch=a.batch, device=str(self.device), device_name=torch.cuda.get_device_name(0) if self.device.type == 'cuda' else platform.processor() or 'cpu',
                    torch=torch.__version__, cuda=torch.version.cuda, python=platform.python_version(), variant=a.variant, bf16_autocast=bool(a.bf16 and self.device.type == 'cuda'),
                    model=self.model_name, cfg=self.cfg, n_params=self.n_params, caps_file=self.caps_path, caps=self.caps, data=self.data_desc, rows_loaded=len(self.rows),
                    eg=self.eg_mode, tiny=bool(a.tiny), seed=a.seed, pkg_root=PK.root, lr=self.lr, argv=sys.argv[1:], started=datetime.datetime.now().isoformat(timespec='seconds'))

    def tag(self, **kw):
        a = self.a
        return dict(arm=a.arm, rung=a.rung, accum=kw.pop('accum', a.accum), batch=a.batch, device=str(self.device), torch=torch.__version__, **kw)


def make_opt(model, lr, device):
    """train.py's optimizer: AdamW(betas 0.9 / 0.95, fused on cuda), no weight decay on biases, norms, embedding tables."""
    emb = {id(m.weight) for m in model.modules() if isinstance(m, nn.Embedding)}
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in model.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    return torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': no_decay, 'weight_decay': 0.0}], lr=lr, betas=(0.9, 0.95), fused=device.type == 'cuda')


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# variants (all change as little as possible; none edits custom_io)
# ------------------------------------------------------------------------------------------------------------------------------------------------------
class Variant:
    name, doc = 'baseline', 'train.py as it is'

    def __init__(self, tr):
        self.tr = tr

    def setup(self):
        pass

    def teardown(self):
        pass

    def prep(self, b):
        return b

    def split(self, b, k):
        return None             # None = not mine: split_batch

    def fwd_ctx(self):
        return contextlib.nullcontext()

    def before_micro(self, dev):
        """Called once per update on the whole device batch, before the micro-batch loop (eg_once, oldw). Default: nothing."""

    def stats(self):
        return {}


class SortPad(Variant):
    name = 'sortpad'
    doc = ('sort the update\'s rows by prompt length, cut micro-batches in that order, trim each to its own widest row (columns of prompt_ids / prompt_mask). The gradient of a row-sum '
           'loss is the sum over rows, so only rounding changes. If the model\'s loss is a TOKEN MEAN per micro-batch (plain_tf_steps / PTS / PTC: F.cross_entropy over the micro-batch) '
           'train.py\'s loss/len(parts) weights every micro-batch equally, so sorting changes which rows/tokens share a weight (sortpad_tokw undoes that). b3g2 averages per row but '
           'its rounds n, K draw, gap/drill draws and stop-loss mean depend on the micro-batch mix (see README).')

    def setup(self):
        self.mult = self.tr.a.pad_multiple or (16 if any(n.startswith('compile') for n in self.tr.var_names) else 1)

    def prep(self, b):
        lens = b['prompt_mask'].sum(1)
        order = torch.argsort(lens, stable=True)
        o, n = order.tolist(), len(order)
        out = {}
        for k, v in b.items():
            if torch.is_tensor(v) and v.shape[:1] == (n,):
                out[k] = v.index_select(0, order)
            elif isinstance(v, list) and len(v) == n:
                out[k] = [v[i] for i in o]
            else:
                out[k] = v
        out['_len'] = lens.index_select(0, order).tolist()
        out['_orig'] = o                         # position of each sorted row in the update's original order (oldw needs it)
        return out

    def split(self, b, k):
        L, T = b['_len'], b['prompt_ids'].shape[1]
        n = len(L)
        cuts = [round(i * n / k) for i in range(k + 1)]
        parts = []
        for lo, hi in zip(cuts, cuts[1:]):
            if hi <= lo:
                continue
            w = min(T, -(-max(L[lo:hi]) // self.mult) * self.mult)
            parts.append({key: (v[lo:hi, :w].contiguous() if key in ('prompt_ids', 'prompt_mask') else v[lo:hi] if (torch.is_tensor(v) or isinstance(v, list)) else v)
                          for key, v in b.items()})
        return parts


class SortPadTokW(SortPad):
    name = 'sortpad_tokw'
    doc = ('sortpad + each micro-batch loss is weighted by its share of the update\'s supervised tokens (sum_k loss_k * n_k / sum n_k = the FULL-batch token mean, i.e. accum=1\'s loss). '
           'Needs a model whose loss is one F.cross_entropy per micro-batch (plain_tf_steps_g family).')

    def setup(self):
        super().setup()
        self.tr.tokw = True


class BigMB(Variant):
    name = 'bigmb'
    doc = 'fewer, larger micro-batches: accum = --bigmb-accum (default accum // 2). Same rows, same update; use with sortpad.'

    def setup(self):
        a = self.tr.a
        self.tr.accum = a.bigmb_accum or max(1, self.tr.accum // 2)


class TF32(Variant):
    name = 'tf32'
    doc = 'torch.backends.cuda.matmul.allow_tf32 / cudnn.allow_tf32 = True. Under bf16 autocast almost every matmul is already bf16; only fp32 islands (heads, losses) change.'

    def setup(self):
        self.saved = (torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32, torch.get_float32_matmul_precision())
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.set_float32_matmul_precision('high')

    def teardown(self):
        torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32 = self.saved[:2]
        torch.set_float32_matmul_precision(self.saved[2])


class SDPA(Variant):
    name = 'sdpa'
    doc = ('the models already use F.scaled_dot_product_attention (ledger.py CBlock, plain_lm.py FlexBlock, plain_tf.py Block, writer.py): nothing to switch. With --sdpa-backend '
           'flash|efficient|math|cudnn the variant restricts torch\'s SDPA dispatch to that backend (a bool attn_mask rules flash out, so the controller blocks use efficient / math).')

    def setup(self):
        self.backend = self.tr.a.sdpa_backend

    def fwd_ctx(self):
        if self.backend == 'auto':
            return contextlib.nullcontext()
        try:
            from torch.nn.attention import SDPBackend, sdpa_kernel
        except Exception as e:                                           # pragma: no cover
            raise Skip(f'torch.nn.attention.sdpa_kernel missing: {e!r}')
        return sdpa_kernel({'flash': SDPBackend.FLASH_ATTENTION, 'efficient': SDPBackend.EFFICIENT_ATTENTION, 'math': SDPBackend.MATH, 'cudnn': SDPBackend.CUDNN_ATTENTION}[self.backend])


class Compile(Variant):
    name, mode = 'compile', 'default'
    doc = ('torch.compile(dynamic=True) on each controller block (model.core[i] for b3g2 / ledger, model.blocks[i] for the plain arms), by replacing the block\'s forward; skipped '
           'on CPU (--compile-cpu forces) and when the compile fails. dynamic=True and --pad-multiple (sortpad rounds widths up to 16 when a compile variant is on) keep the '
           'number of recompiles down; compile_stats in the result counts them.')

    def setup(self):
        a, tr = self.tr.a, self.tr
        if not hasattr(torch, 'compile'):
            raise Skip('torch.compile not available')
        if tr.device.type != 'cuda' and not (a.compile_cpu or a.compile_backend != 'inductor'):
            raise Skip('torch.compile skipped on CPU (--compile-cpu, or --compile-backend aot_eager for a plumbing check)')
        blocks = []
        for lst in ('core', 'blocks'):
            ml = getattr(tr.model, lst, None)
            if isinstance(ml, nn.ModuleList):
                blocks += list(ml)
        if not blocks:
            raise Skip('no controller / transformer blocks to compile')
        try:
            dyn = importlib.import_module('torch._dynamo')
            dyn.config.cache_size_limit = max(64, dyn.config.cache_size_limit)
        except Exception:
            pass
        self.saved = []
        kw = dict(dynamic=True, backend=a.compile_backend)
        if self.mode != 'default' and a.compile_backend == 'inductor':
            kw['mode'] = self.mode
        for blk in blocks:
            self.saved.append(blk)
            blk.forward = torch.compile(blk.forward, **kw)

    def teardown(self):
        for blk in getattr(self, 'saved', []):
            blk.__dict__.pop('forward', None)


class CompileRO(Compile):
    name, mode = 'compile_ro', 'reduce-overhead'
    doc = 'compile with mode="reduce-overhead" (CUDA graphs; every new input shape records a new graph, so use with --pad-multiple 16).'


def compile_stats():
    try:
        from torch._dynamo.utils import counters
        return {k: dict(v) for k, v in counters.items() if k in ('stats', 'frames', 'graph_break', 'recompiles')}
    except Exception:
        return {}


class EGSorted(Variant):
    name = 'eg_sorted'
    doc = ('the frozen-Gemma front (FrozenEG.encode / encode_texts, a plain object called inside model.loss) runs on the micro-batch\'s prompts sorted by length, in --eg-chunks sorted '
           'chunks, each trimmed to its own widest prompt; the result is scattered back to the original row order and zero-padded to the same [B, T, 768]. Same values up to '
           'kernel-shape rounding. Mostly useful WITHOUT sortpad (with sortpad the micro-batch is already sorted).')

    def setup(self):
        tr = self.tr
        m = tr.model
        eg = m.eg() if hasattr(m, 'eg') and getattr(m, 'eg_embed', False) else None
        if eg is None:
            raise Skip('model has no EG front')
        self.eg, self.orig = eg, (eg.encode, eg.encode_texts)
        chunks, length, memo = max(1, tr.a.eg_chunks), m.vocab.length, {}

        def run(fn, prompts, T, device, chars=True, texts=False):
            B = len(prompts)
            lens = [length(p) for p in prompts]
            order = sorted(range(B), key=lens.__getitem__)
            cuts = [round(i * B / chunks) for i in range(chunks + 1)]
            Hs, Ps = [], []
            for lo, hi in zip(cuts, cuts[1:]):
                if hi <= lo:
                    continue
                idx = order[lo:hi]
                Tc = max(1, min(T, max(lens[i] for i in idx)))
                out = fn([prompts[i] for i in idx], Tc, device) if texts else fn([prompts[i] for i in idx], Tc, device, chars)
                H, P = (out, None) if texts else out
                if H is not None:
                    Hs.append(F.pad(H, (0, 0, 0, T - Tc)))
                if P is not None:
                    Ps.append(P)
            inv = torch.empty(B, dtype=torch.long)
            inv[torch.tensor(order)] = torch.arange(B)
            H = torch.cat(Hs)[inv.to(Hs[0].device)] if Hs else None
            P = torch.cat(Ps)[inv.to(Ps[0].device)] if Ps else None
            return H if texts else (H, P)

        def encode(prompts, T, device, chars=True):
            key = (tuple(prompts), T, str(device))
            if memo.get('k') == key and (memo['v'][0] is not None or not chars):
                return memo['v']
            out = run(self.orig[0], prompts, T, device, chars)
            memo['k'], memo['v'] = key, out
            return out

        eg.encode = encode
        eg.encode_texts = lambda texts, T, device: run(self.orig[1], texts, T, device, texts=True)

    def teardown(self):
        self.eg.__dict__.pop('encode', None)
        self.eg.__dict__.pop('encode_texts', None)


class Prefetcher:
    """One background thread that pulls the next batch from the (single-consumer) generator, applies the CPU prep, pins it and copies it to the device on a side
    stream; the queue is FIFO, so batch order and content are exactly the generator's. The GIL limits the gain when collate is Python-bound (it is: Dataset.__getitem__ and
    collate loop over rows in Python); a process pool (DataLoader workers) is the stronger fix."""

    def __init__(self, it, prep, device, depth=2):
        self.it, self.prep, self.device = it, prep, device
        self.q = queue.Queue(depth)
        self.cuda = device.type == 'cuda'
        self.stream = torch.cuda.Stream() if self.cuda else None
        self.stop = threading.Event()
        self.produce_s = []
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()

    def _run(self):
        try:
            while not self.stop.is_set():
                t0 = time.perf_counter()
                b = self.prep(next(self.it))
                ev = None
                if self.cuda:
                    with torch.cuda.stream(self.stream):
                        b = {k: (v.pin_memory().to(self.device, non_blocking=True) if torch.is_tensor(v) else v) for k, v in b.items()}
                        ev = torch.cuda.Event()
                        ev.record(self.stream)
                self.produce_s.append(time.perf_counter() - t0)
                while not self.stop.is_set():
                    try:
                        self.q.put((b, ev), timeout=0.2)
                        break
                    except queue.Full:
                        continue
        except BaseException as e:                                       # noqa: B902
            self.q.put(e)

    def __iter__(self):
        return self

    def __next__(self):
        item = self.q.get()
        if isinstance(item, BaseException):
            raise item
        b, ev = item
        if ev is not None:
            cur = torch.cuda.current_stream()
            cur.wait_event(ev)
            for v in b.values():
                if torch.is_tensor(v):
                    v.record_stream(cur)
        return b

    def close(self):
        self.stop.set()
        try:
            while True:
                self.q.get_nowait()
        except queue.Empty:
            pass
        self.t.join(timeout=2)


class Prefetch(Variant):
    name = 'prefetch'
    doc = 'a background thread (threading + queue) collates the next batch, applies the CPU prep, pins it and copies it to the device on a side stream while the GPU works. Same order, same content.'

    def setup(self):
        tr = self.tr
        tr.prefetcher = Prefetcher(tr.it, tr._prep, tr.device, tr.a.prefetch_depth)

    def teardown(self):
        if getattr(self.tr, 'prefetcher', None) is not None:
            self.tr.prefetcher.close()
            self.tr.prefetcher = None


class OnceCache:
    """eg_once's engine, usable on its own (E1 / E2): runs the frozen Gemma ONCE over a list of prompts (sorted by token length, chunked under a token budget of padded
    tokens), keeps per-prompt token states, pooled vector and char->token map, and replaces eg.encode so a micro-batch's [B, T, 768] is gathered from that cache (the same
    tensor, dtype and zero padding as FrozenEG._compute builds). A prompt that is not cached sends the whole call down the old path. eg.encode_texts is not touched."""

    def __init__(self, eg, budget=16384):
        self.eg, self.budget = eg, max(64, int(budget))
        self.cache, self.memo = {}, None
        self.hits = self.misses = self.chunks = self.prompts = 0
        self.orig_encode, self.orig_compute = eg.encode, eg._compute            # bound methods of the old path
        self.cache_device = None
        self.installed = False

    def install(self):
        eg, me = self.eg, self

        def encode(prompts, T, device, chars=True):
            key = (tuple(prompts), T, str(device))
            if me.memo is not None and me.memo[0] == key and (me.memo[1][0] is not None or not chars):
                return me.memo[1]
            if prompts and str(device) == me.cache_device and all(p in me.cache for p in prompts):
                me.hits += 1
                out = me.serve(prompts, T, device, chars)
                me.memo = (key, out)
                return out
            me.misses += 1
            return me.orig_encode(prompts, T, device, chars)
        eg.encode = encode
        self.installed = True
        return self

    def uninstall(self):
        if self.installed:
            self.eg.__dict__.pop('encode', None)
            self.installed = False
        self.cache.clear(); self.memo = None

    def precompute(self, prompts, device):
        """Encode every distinct prompt once. Chunks: ascending token length, each chunk's padded size (rows x its longest) <= budget (one row alone may exceed it)."""
        eg = self.eg
        self.cache, self.memo = {}, None
        uniq = list(dict.fromkeys(prompts))
        eg.load(device)
        al = {p: eg.align(p) for p in uniq}
        order = sorted(uniq, key=lambda p: len(al[p][0]))
        chunks, cur = [], []
        for p in order:
            if cur and (len(cur) + 1) * len(al[p][0]) > self.budget:
                chunks.append(cur); cur = []
            cur.append(p)
        if cur:
            chunks.append(cur)
        for ch in chunks:
            grab = []
            tgt = eg.m.norm if getattr(eg, 'pre', False) else eg.m
            hook = tgt.register_forward_hook(lambda mod, i, o: grab.append(o if getattr(eg, 'pre', False) else o.last_hidden_state))
            try:
                _, pooled = self.orig_compute(ch, 1, device, False)
            finally:
                hook.remove()
            if len(grab) != 1:
                raise RuntimeError(f'eg_once: expected one Gemma call per chunk, saw {len(grab)}')
            Ht = grab[0]
            for b, p in enumerate(ch):
                self.cache[p] = (Ht[b, :len(al[p][0])], pooled[b], al[p][1])
        self.cache_device = str(device)
        self.chunks += len(chunks); self.prompts += len(uniq)

    def encode_cached(self, prompts, T, device):
        """H [B, T, 768] through the installed encode (counts a hit; a miss would be visible in .misses)."""
        return self.eg.encode(prompts, T, device)[0]

    def serve(self, prompts, T, device, chars=True):
        ent = [self.cache[p] for p in prompts]
        pooled = torch.stack([e[1] for e in ent])
        if not chars:
            return (None, pooled)
        Ht = torch.nn.utils.rnn.pad_sequence([e[0] for e in ent], batch_first=True)
        B = len(ent)
        c2t, cm = np.zeros((B, T), np.int64), np.zeros((B, T), bool)
        for b, e in enumerate(ent):
            n = min(len(e[2]), T)
            c2t[b, :n], cm[b, :n] = e[2][:n], True
        c2t, cm = torch.from_numpy(c2t).to(device), torch.from_numpy(cm).to(device)
        H = Ht.gather(1, c2t[..., None].expand(-1, -1, Ht.shape[-1])) * cm[..., None].to(Ht.dtype)
        return (H, pooled)


class EGOnce(Variant):
    name = 'eg_once'
    doc = ('PREREG-eg-once.md: before the micro-batch loop the frozen Gemma runs ONCE on all rows of the update (distinct prompts sorted by token length, chunks of at most '
           '--eg-once-budget padded tokens, default 16384); per-prompt token states, pooled vector and char->token map are cached; FrozenEG.encode then builds each micro-batch\'s '
           '[B, T, 768] (same dtype, same zero padding) from the cache, and any call with an uncached prompt takes the old path. Gemma is frozen and no_grad, so no training signal '
           'changes; the numbers change only by kernel rounding (batch shape). encode_texts (tape strings) is untouched.')

    def setup(self):
        m = self.tr.model
        eg = m.eg() if hasattr(m, 'eg') and getattr(m, 'eg_embed', False) else None
        if eg is None:
            raise Skip('model has no EG front')
        self.once = OnceCache(eg, self.tr.a.eg_once_budget).install()

    def before_micro(self, dev):
        self.once.precompute([r['prompt'] for r in dev['rows']], dev['prompt_ids'].device)

    def teardown(self):
        if getattr(self, 'once', None) is not None:
            self.once.uninstall()

    def stats(self):
        o = self.once
        return dict(encode_calls_from_cache=o.hits, encode_calls_old_path=o.misses, gemma_chunks=o.chunks, prompts_encoded=o.prompts)


@contextlib.contextmanager
def weighted_ce(w):
    """Inside: F.cross_entropy(logits [B*W, V], target [B*W]) returns sum_t w[row(t)] * ce_t (default 'mean' reduction replaced by per-row weights; ignore_index respected)."""
    orig = F.cross_entropy

    def ce(input, target, *a, **k):
        if a or k.get('reduction', 'mean') != 'mean' or k.get('weight') is not None or k.get('label_smoothing', 0.0):
            raise Skip('oldw: this model\'s cross_entropy call is not a plain mean')
        l = orig(input, target, reduction='none', ignore_index=k.get('ignore_index', -100))
        return (l.view(w.shape[0], -1) * w[:, None]).sum()
    F.cross_entropy = ce
    try:
        yield
    finally:
        F.cross_entropy = orig


def count_pass(model, mb):
    """Per-row supervised-token counts of a micro-batch, WITHOUT running the network: model.loss(mb) with the front, the transformer and the head replaced by zeros, and
    F.cross_entropy only recording its target. -> (counts int64 [B] cpu, reduction str) or None if the model's loss has no single cross_entropy call (b3g2 ...)."""
    if not (hasattr(model, 'hidden_upto') and hasattr(model, 'logits') and hasattr(model, '_targets')):
        return None
    V, seen, orig = len(model.vocab), [], F.cross_entropy
    saved = {k: model.__dict__.get(k, _MISSING) for k in ('_set_front', 'hidden_upto', 'logits')}
    model._set_front = lambda batch, width: None
    model.hidden_upto = lambda seq, n, loops=None, pl=None: seq.new_zeros((seq.shape[0], n, 1), dtype=torch.float32)
    model.logits = lambda h: h.new_zeros(h.shape[0], h.shape[1], V)

    def ce(input, target, *a, **k):
        seen.append(((target != k.get('ignore_index', -100)).cpu(), k.get('reduction', 'mean')))
        return input.sum() * 0.0
    F.cross_entropy = ce
    try:
        with torch.no_grad():
            model.loss({k: v for k, v in mb.items() if not k.startswith('_')})
    finally:
        F.cross_entropy = orig
        for k, v in saved.items():
            if v is _MISSING:
                model.__dict__.pop(k, None)
            else:
                model.__dict__[k] = v
    if len(seen) != 1:
        return None
    mask, red = seen[0]
    return mask.view(len(mb['rows']), -1).sum(1).long(), red


class OldW(Variant):
    name = 'oldw'
    doc = ('keeps the OLD path\'s per-token weights when a variant changes the micro-batch partition (sortpad, bigmb). The old loss is (1/K) sum_k mean-over-the-tokens-of-micro-batch-k, '
           'so a token of old micro-batch k weighs 1/(K n_k). oldw counts every row\'s supervised tokens first (count_pass: no network run), finds each row\'s OLD micro-batch '
           '(cuts of the original row order into --accum parts), and weights each token 1/(K n_k(row)) inside whatever micro-batches the other variants cut: the update\'s loss and gradient '
           'are the old ones up to rounding. Plain arms (one token-mean cross_entropy per micro-batch) only. Costs one extra host-side _targets pass per update.')

    def setup(self):
        tr = self.tr
        if not (hasattr(tr.model, '_targets') and hasattr(tr.model, 'hidden_upto')):
            raise Skip('oldw: needs a plain-arm model (one token-mean cross_entropy per micro-batch)')
        tr.oldw = True

    def teardown(self):
        self.tr.oldw = False

    def before_micro(self, dev):
        tr = self.tr
        n = len(dev['rows'])
        cnt = torch.zeros(n, dtype=torch.long)
        for lo in range(0, n, 16):
            hi = min(n, lo + 16)
            mb = {k: (v[lo:hi] if torch.is_tensor(v) or isinstance(v, list) else v) for k, v in dev.items() if not k.startswith('_')}
            r = count_pass(tr.model, mb)
            if r is None:
                raise Skip('oldw: this model\'s loss is not one cross_entropy call')
            if r[1] != 'mean':
                raise Skip('oldw: cross_entropy is not a mean')
            cnt[lo:hi] = r[0]
        K0 = tr.a.accum                                           # the OLD path's number of micro-batches
        cuts = [round(i * n / K0) for i in range(K0 + 1)]
        orig = dev.get('_orig') or list(range(n))
        bucket = np.searchsorted(np.asarray(cuts[1:]), np.asarray(orig), side='right')
        n_old = np.bincount(bucket, weights=cnt.numpy().astype(np.float64), minlength=K0)
        w = np.where(n_old[bucket] > 0, 1.0 / (K0 * np.maximum(n_old[bucket], 1)), 0.0)
        tr.row_w = torch.tensor(w, dtype=torch.float32, device=dev['prompt_ids'].device)

    def fwd_ctx(self):
        tr = self.tr
        return weighted_ce(tr.part_w) if getattr(tr, 'part_w', None) is not None else contextlib.nullcontext()


VARIANTS = {c.name: c for c in (Variant, SortPad, SortPadTokW, OldW, BigMB, TF32, SDPA, Compile, CompileRO, EGSorted, EGOnce, Prefetch)}
SETUP_ORDER = ('bigmb', 'tf32', 'sdpa', 'baseline', 'sortpad', 'sortpad_tokw', 'oldw', 'compile', 'compile_ro', 'eg_sorted', 'eg_once', 'prefetch')       # prefetch last: it needs the final prep chain


def parse_variants(spec):
    names = [s.strip() for s in (spec or '').replace('+', ',').split(',') if s.strip() and s.strip() != 'baseline']
    bad = [n for n in names if n not in VARIANTS]
    if bad:
        raise SystemExit(f'unknown variant(s) {bad}; known: {sorted(VARIANTS)}')
    if sum(n in ('sortpad', 'sortpad_tokw') for n in names) > 1:
        raise SystemExit('sortpad and sortpad_tokw are alternatives')
    if sum(n.startswith('compile') for n in names) > 1:
        raise SystemExit('compile and compile_ro are alternatives')
    if 'eg_sorted' in names and 'eg_once' in names:
        raise SystemExit('eg_sorted and eg_once are alternatives (both replace FrozenEG.encode)')
    if 'oldw' in names and 'sortpad_tokw' in names:
        raise SystemExit('oldw and sortpad_tokw are alternatives (old per-token weights vs the full-batch token mean)')
    return sorted(names, key=SETUP_ORDER.index)


@contextlib.contextmanager
def count_ce_tokens(box):
    """Record, for every F.cross_entropy call inside, the number of supervised targets (a device tensor: no sync)."""
    orig = F.cross_entropy

    def ce(input, target, *a, **k):
        box.append((target != k.get('ignore_index', -100)).sum())
        return orig(input, target, *a, **k)
    F.cross_entropy = ce
    try:
        yield
    finally:
        F.cross_entropy = orig


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# the trainer: train.py's update loop, parametrised
# ------------------------------------------------------------------------------------------------------------------------------------------------------
class Trainer:
    def __init__(self, world, args, variants=(), accum=None, seed=None, batch_seed=None):
        self.w, self.a, self.device = world, args, world.device
        self.clock = Clock(self.device)
        self.var_names = list(variants)
        self.accum = accum or args.accum
        seed = args.seed if seed is None else seed
        seed_all(seed)
        self.model = world.new_model(seed)
        self.model.train()
        self.opt = make_opt(self.model, world.lr, self.device)
        self.amp = world.amp
        self.it = world.batches(seed if batch_seed is None else batch_seed)
        self.prefetcher = None
        self.tokw = False
        self.oldw, self.row_w, self.part_w = False, None, None
        self.step = 0
        self.lr_steps, self.lr_warmup = args.lr_steps, args.lr_warmup
        self.rec = Recorder(self.clock)
        self.instr = None
        self.variants = []
        try:
            for n in self.var_names:
                v = VARIANTS[n](self)
                v.setup()
                self.variants.append(v)
        except BaseException:
            self.close()
            raise

    # ---- variant plumbing
    def _prep(self, b):
        for v in self.variants:
            b = v.prep(b)
        return b

    def _split(self, b):
        for v in self.variants:
            parts = v.split(b, self.accum)
            if parts is not None:
                return parts
        return PK.TR.split_batch(b, self.accum) if self.accum > 1 else [b]

    def _fwd_ctx(self, box):
        st = contextlib.ExitStack()
        for v in self.variants:
            st.enter_context(v.fwd_ctx())
        if self.tokw:
            st.enter_context(count_ce_tokens(box))
        st.enter_context(self.amp())
        return st

    def variant_stats(self):
        return {v.name: st for v in self.variants for st in [v.stats()] if st}

    def instrument(self, level='top', methods=True):
        self.instr = Instrument(self.model, self.rec, level, methods).install()
        self.rec.active = True
        return self.instr

    def close(self):
        if self.instr is not None:
            self.instr.remove(); self.instr = None
        self.rec.active = False
        for v in reversed(self.variants):
            try:
                v.teardown()
            except Exception:
                pass
        self.variants = []

    # ---- one update
    def update(self, timed=False):
        """One train.py update. timed=True: sync + time every stage -> (loss, stages dict, sections dict). Else -> (loss, None, None) with no extra syncs."""
        st = collections.defaultdict(float) if timed else None
        T = (lambda n: stage(self.clock, st, n)) if timed else (lambda n: contextlib.nullcontext())
        if timed:
            self.rec.reset()
            self.rec.active = self.instr is not None
            w0 = self.clock.now()
        lr = PK.TR.lr_at(self.step, self.lr_steps, self.lr_warmup, self.w.lr)
        for g in self.opt.param_groups:
            g['lr'] = lr
        if self.prefetcher is not None:
            with T('fetch'):
                dev = next(self.prefetcher)
        else:
            with T('fetch'):
                cpu = next(self.it)
            with T('prep'):
                cpu = self._prep(cpu)
            with T('h2d'):
                dev = PK.D.to_device(cpu, self.device)
        with T('split'):
            parts = self._split(dev)
        loss = self._micro(parts, T, dev)
        with T('clip'):
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        with T('opt'):
            self.opt.step(); self.opt.zero_grad(set_to_none=True)
        self.step += 1
        if not timed:
            return loss, None, None
        wall = self.clock.now() - w0
        self.rec.active = False
        st['wall'] = wall
        st['other'] = max(0.0, wall - sum(v for k, v in st.items() if k != 'wall'))
        sec = {k: dict(excl=self.rec.excl[k], incl=self.rec.incl[k], calls=self.rec.calls[k]) for k in self.rec.calls}
        for k, c in self.rec.bwd_calls.items():
            sec.setdefault(k, dict(excl=0.0, incl=0.0, calls=0))['bwd_calls'] = c
        return loss, dict(st), sec

    def _micro(self, parts, T, dev=None):
        """The micro-batch loop of train.py (forward, backward per micro-batch, loss / aux accumulated without a sync). tokw: weights n_k / sum n instead of 1 / k.
        oldw: each token weighs what it weighed in the OLD partition (the model's loss then returns the weighted sum). dev = the whole device batch, for before_micro."""
        k, loss, aux, n_tot = len(parts), 0.0, {}, None
        if dev is not None:
            for v in self.variants:
                if type(v).before_micro is not Variant.before_micro:
                    with T('forward'):
                        self.rec.phase = 'fwd'
                        tok = self.rec.enter(f'm/{v.name}.precompute')
                        try:
                            v.before_micro(dev)
                        finally:
                            self.rec.exit(tok)
        off = 0
        for i, mb in enumerate(parts):
            nrow = len(mb['rows'])
            self.part_w = self.row_w[off:off + nrow] if self.oldw else None
            off += nrow
            mb = {key: v for key, v in mb.items() if not key.startswith('_')}
            box = []
            with T('forward'):
                self.rec.phase = 'fwd'
                with self._fwd_ctx(box):
                    out = self.model.loss(mb)
            l_i, a_i = out if isinstance(out, tuple) else (out, {})
            if self.tokw:
                if not box:
                    raise Skip('sortpad_tokw: this model\'s loss made no F.cross_entropy call')
                n_i = sum(box).float()
                n_tot = n_i if n_tot is None else n_tot + n_i
                scaled = l_i * n_i
            elif self.oldw:
                scaled = l_i
            else:
                scaled = l_i / k
            with T('backward'):
                self.rec.phase = 'bwd'
                scaled.backward()
                self.rec.phase = 'fwd'
            if self.tokw:
                loss = loss + scaled.detach()
            elif self.oldw:
                loss = loss + l_i.detach()
            else:
                loss = loss + l_i.detach() / k
                for k_, v_ in a_i.items():
                    aux[k_] = aux.get(k_, 0.0) + v_.detach() / k if torch.is_tensor(v_) else aux.get(k_, 0.0) + v_ / k
        if self.tokw:
            inv = 1.0 / n_tot
            gs = [p.grad for p in self.model.parameters() if p.grad is not None]
            try:
                torch._foreach_mul_(gs, inv)
            except Exception:
                for g in gs:
                    g.mul_(inv)
            loss = loss * inv
        return loss

    def loss_and_grad(self, cpu_batch, amp=None):
        """The same prep -> h2d -> split -> micro-batch loop as update(), without clip / optimizer: (loss float, flat float64 gradient vector). For --equiv-check."""
        if amp is not None:
            self.amp = amp
        self.model.zero_grad(set_to_none=True)
        torch.manual_seed(self.a.seed + 12345)
        dev = PK.D.to_device(self._prep(cpu_batch), self.device)
        loss = self._micro(self._split(dev), lambda n: contextlib.nullcontext(), dev)
        g = torch.cat([(p.grad if p.grad is not None else torch.zeros_like(p)).detach().double().flatten().cpu() for p in self.model.parameters() if p.requires_grad])
        return float(loss), g


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# statistics helpers
# ------------------------------------------------------------------------------------------------------------------------------------------------------
def stats(xs):
    xs = np.asarray(xs, dtype=float)
    if xs.size == 0:
        return dict(mean=0.0, median=0.0, p90=0.0, n=0)
    return dict(mean=float(xs.mean()), median=float(np.median(xs)), p90=float(np.percentile(xs, 90)), n=int(xs.size))


def peak_mem(device):
    if device.type != 'cuda':
        return dict(allocated_gb=None, reserved_gb=None)
    return dict(allocated_gb=torch.cuda.max_memory_allocated() / 2 ** 30, reserved_gb=torch.cuda.max_memory_reserved() / 2 ** 30)


def cleanup(device):
    gc.collect()
    if device.type == 'cuda':
        torch.cuda.empty_cache()


def is_oom(e):
    return (hasattr(torch.cuda, 'OutOfMemoryError') and isinstance(e, torch.cuda.OutOfMemoryError)) or (isinstance(e, RuntimeError) and 'out of memory' in str(e).lower())


def section_overhead_us(clock, n=2000):
    """Cost of one enter/exit pair of a timed section (two clock reads; on CUDA two synchronize calls on an idle device), microseconds."""
    r = Recorder(clock)
    r.active = True
    t0 = time.perf_counter()
    for _ in range(n):
        r.exit(r.enter('x'))
    return (time.perf_counter() - t0) / n * 1e6


def cold_eg(world):
    """Real EG only: drop the tokenizer-alignment cache so a timed section pays the first-pass tokenisation the 1.1-epoch job pays."""
    if world.eg is not None and hasattr(world.eg, '_align'):
        world.eg._align.clear()
        world.eg._last = None


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# sections
# ------------------------------------------------------------------------------------------------------------------------------------------------------
def sec_breakdown(world, args):
    tr = Trainer(world, args, parse_variants(args.variant), batch_seed=args.seed + 101)
    try:
        cold_eg(world)
        log(f'breakdown: {args.warmup} warmup + {args.updates} timed updates (variant {args.variant or "baseline"}, accum {tr.accum}, hooks {args.hook_level})')
        for _ in range(args.warmup):
            tr.update()
        tr.instrument(args.hook_level, args.methods == 'all')
        if world.device.type == 'cuda':
            torch.cuda.reset_peak_memory_stats()
        hist, secs, losses = collections.defaultdict(list), collections.defaultdict(lambda: collections.defaultdict(list)), []
        for i in range(args.updates):
            loss, st, sec = tr.update(timed=True)
            losses.append(loss)
            for k, v in st.items():
                hist[k].append(v)
            for k, d in sec.items():
                for f, v in d.items():
                    secs[k][f].append(v)
            if (i + 1) % max(1, args.updates // 5) == 0 or i == 0:
                log(f'  breakdown update {i + 1}/{args.updates}: wall {st["wall"] * 1e3:.0f} ms  fetch {st.get("fetch", 0) * 1e3:.0f} h2d {st.get("h2d", 0) * 1e3:.0f} fwd {st.get("forward", 0) * 1e3:.0f} '
                    f'bwd {st.get("backward", 0) * 1e3:.0f} opt {st.get("opt", 0) * 1e3:.0f}')
        n = len(hist['wall'])
        fill = lambda xs: list(xs) + [0.0] * (n - len(xs))
        total = {k: stats(fill(v)) for k, v in hist.items()}
        total['split_total'] = stats([a + b for a, b in zip(fill(hist.get('prep', [])), fill(hist.get('split', [])))])
        wall_mean = total['wall']['mean']
        excl = {k: stats(fill(v['excl'])) | dict(calls_per_update=float(np.mean(fill(v['calls']))), bwd_calls_per_update=float(np.mean(fill(v.get('bwd_calls', [])))) if v.get('bwd_calls') else 0.0,
                                                  incl_mean=float(np.mean(fill(v['incl'])))) for k, v in secs.items()}
        groups = collections.defaultdict(float)
        for k, s in excl.items():
            groups[rollup_group(k)] += s['mean']
        fwd = total['forward']['mean']
        groups['heads_loss_and_glue'] = max(0.0, fwd - sum(groups.values()))
        groups = dict(groups)
        n_hook_calls = float(sum(s['calls_per_update'] for s in excl.values()))
        ovh_us = section_overhead_us(tr.clock)
        out = dict(tag=world.tag(accum=tr.accum, variant=args.variant), updates=n, warmup=args.warmup, hook_level=args.hook_level,
                   stages_ms={k: {f: (v * 1e3 if f != 'n' else v) for f, v in s.items()} for k, s in total.items()},
                   share_of_wall={k: s['mean'] / wall_mean for k, s in total.items()} if wall_mean else {},
                   forward_sections_ms={k: {f: (v * 1e3 if f in ('mean', 'median', 'p90', 'incl_mean') else v) for f, v in s.items()} for k, s in sorted(excl.items(), key=lambda kv: -kv[1]['mean'])},
                   forward_rollup_ms={k: v * 1e3 for k, v in sorted(groups.items(), key=lambda kv: -kv[1])},
                   hook_calls_per_update=n_hook_calls, section_overhead_us=ovh_us, instrumentation_overhead_ms_est=n_hook_calls * ovh_us / 1e3, methods=args.methods,
                   loss_first_last=[float(losses[0]), float(losses[-1])], peak_mem=peak_mem(world.device),
                   note='stage times are bracketed by cuda syncs, so wall here is longer than free-running (see throughput); forward sections are EXCLUSIVE of nested sections; '
                       'bwd_calls = forward-hook calls seen during backward = gradient-checkpoint recomputation')
        out['compile_stats'] = compile_stats() if any(v.startswith('compile') for v in tr.var_names) else {}
        out['variant_stats_total'] = tr.variant_stats()
        return out
    finally:
        tr.close(); cleanup(world.device)


def free_run(tr, n, chunk):
    """n updates in chunks of `chunk`, one sync at each end of a chunk: -> list of seconds per update (one entry per chunk) and the mean."""
    per = []
    for c0 in range(0, n, chunk):
        m = min(chunk, n - c0)
        t0 = tr.clock.now()
        for _ in range(m):
            tr.update()
        per.append((tr.clock.now() - t0) / m)
    return per


def sec_throughput(world, args, variants=None, accum=None, tag_extra=None):
    names = parse_variants(args.variant) if variants is None else variants
    tr = Trainer(world, args, names, accum=accum, batch_seed=args.seed + 202)
    try:
        cold_eg(world)
        for _ in range(args.warmup):
            tr.update()
        if world.device.type == 'cuda':
            torch.cuda.reset_peak_memory_stats()
        per = free_run(tr, args.updates, args.chunk)
        s = stats(per)
        out = dict(tag=world.tag(accum=tr.accum, variant=','.join(names) or 'baseline', **(tag_extra or {})), updates=args.updates, chunk=args.chunk, s_per_update=s['mean'], median_chunk=s['median'],
                   p90_chunk=s['p90'], chunk_values=per, updates_per_s=1.0 / s['mean'] if s['mean'] else None, peak_mem=peak_mem(world.device))
        if tr.prefetcher is not None and tr.prefetcher.produce_s:
            out['prefetch_thread_ms_per_batch'] = float(np.mean(tr.prefetcher.produce_s)) * 1e3
        if any(v.startswith('compile') for v in names):
            out['compile_stats'] = compile_stats()
        if tr.variant_stats():
            out['variant_stats_total'] = tr.variant_stats()
        log(f'throughput: {s["mean"]:.4f} s/update ({1 / s["mean"]:.2f} updates/s), accum {tr.accum}, variant {out["tag"]["variant"]}')
        return out
    finally:
        tr.close(); cleanup(world.device)


def analyze_events(evs, n_updates, wall_s, is_cuda):
    """Pure function over profiler FunctionEvent-like objects (name, device_type, time_range or *_time attrs, self_cpu_time_total) -> the kernel / launch statistics."""
    def dur(e):
        tr = getattr(e, 'time_range', None)
        if tr is not None:
            try:
                return float(tr.end - tr.start)
            except Exception:
                pass
        for a in ('device_time_total', 'cuda_time_total', 'device_time', 'cuda_time'):
            v = getattr(e, a, None)
            if v:
                return float(v)
        return 0.0
    kern, ctrl = [], collections.Counter()
    cpu_self = 0.0
    for e in evs:
        dt = str(getattr(e, 'device_type', '')).upper()
        nm = getattr(e, 'name', '') or getattr(e, 'key', '')
        if 'CUDA' in dt:
            kern.append(e)
        else:
            cpu_self += float(getattr(e, 'self_cpu_time_total', 0.0) or 0.0)
            if nm in ('cudaStreamSynchronize', 'cudaDeviceSynchronize', 'cudaEventSynchronize', 'cudaLaunchKernel', 'cudaMemcpyAsync', 'cudaMemcpy', 'cudaGraphLaunch'):
                ctrl[nm] += 1
    out = dict(updates=n_updates, cpu_op_self_time_ms_per_update=cpu_self / 1e3 / n_updates, wall_ms_per_update=wall_s * 1e3 / n_updates)
    if is_cuda and not kern:                  # some torch versions only attach kernels to their launching CPU op (FunctionEvent.kernels): durations and counts, no intervals
        for e in evs:
            for kk in getattr(e, 'kernels', None) or []:
                kern.append(types.SimpleNamespace(name=getattr(kk, 'name', '?'), device_type='DeviceType.CUDA', time_range=None, device_time_total=float(getattr(kk, 'duration', 0.0))))
        if kern:
            out['warning'] = 'no stand-alone CUDA events in profiler.events(): kernel durations come from the CPU ops\' kernel lists, so there are no intervals and no GPU-busy fraction'
        else:
            out['warning'] = 'CUDA run but the profiler returned no CUDA kernels (CUPTI missing? torch version?): look at the chrome trace (--trace)'
    if not is_cuda or not kern:
        out.update(cuda=None)
        return out
    names = collections.defaultdict(lambda: [0, 0.0])
    ivs, memcpy = [], collections.Counter()
    tot = 0.0
    for e in kern:
        d = dur(e)
        nm = getattr(e, 'name', '')
        names[nm][0] += 1
        names[nm][1] += d
        tot += d
        tr = getattr(e, 'time_range', None)
        if tr is not None:
            ivs.append((float(tr.start), float(tr.end)))
        if 'Memcpy' in nm or 'Memset' in nm:
            memcpy[nm] += 1
    ivs.sort()
    busy, cur_s, cur_e = 0.0, None, None
    for s, e_ in ivs:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                busy += cur_e - cur_s
            cur_s, cur_e = s, e_
        else:
            cur_e = max(cur_e, e_)
    if cur_e is not None:
        busy += cur_e - cur_s
    n_kern = sum(v[0] for k, v in names.items() if 'Memcpy' not in k and 'Memset' not in k)
    top = sorted(names.items(), key=lambda kv: -kv[1][1])[:25]
    window = (ivs[-1][1] if ivs else 0) - (ivs[0][0] if ivs else 0)
    out['cuda'] = dict(
        kernel_time_ms_per_update=tot / 1e3 / n_updates, kernels_per_update=n_kern / n_updates, cuda_events_per_update=len(kern) / n_updates,
        mean_kernel_us=(sum(v[1] for k, v in names.items() if 'Memcpy' not in k and 'Memset' not in k) / max(n_kern, 1)),
        gpu_busy_ms_per_update=busy / 1e3 / n_updates if ivs else None, gpu_busy_fraction_of_wall=busy / 1e6 / wall_s if (wall_s and ivs) else None,
        gpu_busy_fraction_of_profiler_window=busy / window if window else None, idle_gap_fraction_of_wall=1 - busy / 1e6 / wall_s if (wall_s and ivs) else None,
        sum_kernel_over_wall=tot / 1e6 / wall_s if wall_s else None,
        cuda_launch_calls_per_update=ctrl.get('cudaLaunchKernel', 0) / n_updates, graph_launches_per_update=ctrl.get('cudaGraphLaunch', 0) / n_updates,
        stream_syncs_per_update=(ctrl.get('cudaStreamSynchronize', 0) + ctrl.get('cudaDeviceSynchronize', 0) + ctrl.get('cudaEventSynchronize', 0)) / n_updates,
        dtoh_copies_per_update=sum(v for k, v in memcpy.items() if 'DtoH' in k) / n_updates, htod_copies_per_update=sum(v for k, v in memcpy.items() if 'HtoD' in k) / n_updates,
        top_kernels=[dict(name=k, count=v[0], total_ms=v[1] / 1e3, avg_us=v[1] / v[0], share=v[1] / tot if tot else 0.0) for k, v in top])
    c = out['cuda']
    out['launch_bound'] = dict(
        cpu_op_time_over_cuda_kernel_time=out['cpu_op_self_time_ms_per_update'] / c['kernel_time_ms_per_update'] if c['kernel_time_ms_per_update'] else None,
        wall_over_cuda_kernel_time=out['wall_ms_per_update'] / c['kernel_time_ms_per_update'] if c['kernel_time_ms_per_update'] else None,
        verdict=(lambda f: 'GPU mostly idle: CPU / launch / sync bound' if f < 0.6 else 'GPU busy >= 60% of wall' if f < 0.85 else 'GPU-bound')(
            c['gpu_busy_fraction_of_wall'] if c['gpu_busy_fraction_of_wall'] is not None else min(1.0, c['sum_kernel_over_wall'] or 0.0)),
        note='heuristic: busy fraction = union of kernel intervals / measured wall of the active updates (profiler overhead inflates wall)')
    return out


def sec_profiler(world, args):
    from torch.profiler import ProfilerActivity, profile, schedule
    tr = Trainer(world, args, parse_variants(args.variant), batch_seed=args.seed + 303)
    try:
        cold_eg(world)
        for _ in range(args.warmup):
            tr.update()
        acts = [ProfilerActivity.CPU] + ([ProfilerActivity.CUDA] if world.device.type == 'cuda' else [])
        w, wu = args.prof_wait, args.prof_warmup
        act = args.prof_active or (2 if world.model_name in ('b3g2', 'ledger') else 3)
        holder = {}

        def ready(p):
            try:
                holder['events'] = list(p.events())
                holder['avgs'] = p.key_averages()
            except Exception as e:                                       # pragma: no cover
                holder['error'] = repr(e)
        log(f'profiler: schedule wait {w} warmup {wu} active {act}')
        wall = 0.0
        with profile(activities=acts, schedule=schedule(wait=w, warmup=wu, active=act, repeat=1), on_trace_ready=ready, record_shapes=False, with_stack=False) as prof:
            for i in range(w + wu + act):
                t0 = tr.clock.now()
                tr.update()
                dt = tr.clock.now() - t0
                if i >= w + wu:
                    wall += dt
                prof.step()
        if args.trace:
            try:
                prof.export_chrome_trace(args.trace)
            except Exception as e:
                log('trace export failed', repr(e))
        if 'events' not in holder:
            raise Skip('profiler produced no events: ' + holder.get('error', 'unknown'))
        log(f'profiler: {len(holder["events"]):,} events collected, analysing ...')
        out = analyze_events(holder['events'], act, wall, world.device.type == 'cuda')
        cpu_rows = []
        for e in holder['avgs']:
            if 'CUDA' in str(getattr(e, 'device_type', '')).upper() or str(getattr(e, 'key', '')).startswith('ProfilerStep'):
                continue
            cpu_rows.append((float(getattr(e, 'self_cpu_time_total', 0.0) or 0.0), e))
        cpu_rows.sort(key=lambda t: -t[0])
        tot_self = sum(t for t, _ in cpu_rows) or 1.0
        out['top_cpu_ops'] = [dict(name=getattr(e, 'key', getattr(e, 'name', '?')), self_cpu_ms=t / 1e3, self_cpu_ms_per_update=t / 1e3 / act, calls=int(getattr(e, 'count', 0)), share=t / tot_self)
                              for t, e in cpu_rows[:25]]
        out['tag'] = world.tag(accum=tr.accum, variant=args.variant)
        out['schedule'] = dict(wait=w, warmup=wu, active=act)
        log(f'profiler: ' + (out['launch_bound']['verdict'] if 'launch_bound' in out else 'CPU-only run (no CUDA kernels)'))
        return out
    finally:
        tr.close(); cleanup(world.device)


def pad_counts(lens, width, k):
    """One update, one quantity: padded positions if every micro-batch of k keeps `width` (full), is trimmed to its own widest row in the given (random) order (own), or
    is cut from the length-sorted rows and trimmed (sorted); also the same for width^2 and the per-micro-batch real fractions."""
    n = len(lens)
    cuts = [round(i * n / k) for i in range(k + 1)]
    srt = sorted(lens)
    mbs = [(c - a, max(lens[a:c]), sum(lens[a:c]), max(srt[a:c]), sum(srt[a:c])) for a, c in zip(cuts, cuts[1:]) if c > a]
    out = dict(real=sum(lens), full=n * width, own=sum(m * w for m, w, _, _, _ in mbs), sorted=sum(m * w for m, _, _, w, _ in mbs), real2=sum(x * x for x in lens),
               full2=n * width * width, own2=sum(m * w * w for m, w, _, _, _ in mbs), sorted2=sum(m * w * w for m, _, _, w, _ in mbs))
    out['mb_frac'] = dict(full=[r / (m * width) for m, _, r, _, _ in mbs], own=[r / (m * w) for m, w, r, _, _ in mbs], sorted=[r / (m * w) for m, _, _, w, r in mbs])
    return out


def rounds_stats(model, batches_lens_calls, ks):
    """b3g2 / tool_h1 run n = max(K, longest program in the micro-batch + 2) rounds, K drawn from KS per micro-batch (gap_p ignored: last call round = number of calls).
    Expected rounds per row under the random partition and under the length-sorted one."""
    out = {}
    for name in ('random', 'sorted'):
        tot = {'rows': 0, 'rows_calls': 0, 'rows_nocalls': 0, 'n_rows': 0.0, 'n_rows_calls': 0.0, 'n_rows_nocalls': 0.0}
        for lens, calls in batches_lens_calls:
            order = list(range(len(lens))) if name == 'random' else sorted(range(len(lens)), key=lens.__getitem__)
            cuts = [round(i * len(lens) / ks[0]) for i in range(ks[0] + 1)]
            for a, c in zip(cuts, cuts[1:]):
                idx = order[a:c]
                if not idx:
                    continue
                m = max(calls[i] for i in idx)
                e_n = sum(max(K, m + 2) for K in model_KS()) / len(model_KS())
                for i in idx:
                    tot['rows'] += 1; tot['n_rows'] += e_n
                    key = 'rows_calls' if calls[i] else 'rows_nocalls'
                    tot[key] += 1; tot['n_' + key] += e_n
        out[name] = dict(mean_rounds_per_row=tot['n_rows'] / max(tot['rows'], 1), mean_rounds_rows_with_calls=tot['n_rows_calls'] / max(tot['rows_calls'], 1),
                         mean_rounds_rows_without_calls=tot['n_rows_nocalls'] / max(tot['rows_nocalls'], 1), share_rows_with_calls=tot['rows_calls'] / max(tot['rows'], 1))
    return out


def model_KS():
    mod = sys.modules.get('custom_io.models.b3g2') or sys.modules.get('custom_io.models.tool_h1')
    return tuple(getattr(mod, 'KS', (4, 8, 16, 32)))


def sec_padding(world, args):
    """Real-token fractions on the real shuffled batches (the iterator train.py would use for this seed). Units = the vocab's (chars, or bytes for b3g2)."""
    it = world.batches(args.seed)
    plain = world.model_name.startswith('plain_tf_steps')
    pts = importlib.import_module('custom_io.models.plain_tf_steps') if plain else None
    all_steps = bool(world.cfg.get('all_steps'))
    m0 = world.new_model(args.seed) if hasattr(PK.models.get_class(world.model_name), 'trace_of') else None
    acc = {k: collections.defaultdict(float) for k in ACCUMS}
    fr = {k: collections.defaultdict(list) for k in ACCUMS}
    Ws, all_len, per_update, lc = [], [], [], []
    for u in range(args.pad_updates):
        b = next(it)
        L = [int(x) for x in b['prompt_mask'].sum(1).tolist()]
        W = int(b['prompt_ids'].shape[1])
        Ws.append(W); all_len += L
        S = None
        if plain:
            tl = [len(world.vocab.encode(pts.target_text_all(r) if all_steps else pts.target_text(r))[:(None if all_steps else pts.CAP + 12)]) + 1 for r in b['rows']]
            S = [2 + l + t for l, t in zip(L, tl)]
        if m0 is not None and u < args.pad_rounds_updates:
            lc.append((L, [len(m0.trace_of(r)['gold']['texts']) for r in b['rows']]))
        for k in ACCUMS:
            for key, lens, width in (('prompt', L, W),) + ((('seq', S, max(S)),) if S else ()):
                c = pad_counts(lens, width, k)
                for nm in ('real', 'full', 'own', 'sorted', 'real2', 'full2', 'own2', 'sorted2'):
                    acc[k][f'{key}_{nm}'] += c[nm]
                for nm, tag in (('full', 'full'), ('own', 'own'), ('sorted', 'sorted')):
                    fr[k][f'{key}_frac_real_{tag}'].append(c['real'] / c[nm])
                if k == args.accum and key == 'prompt':
                    per_update.append(dict(update=u, W=W, rows=len(L), row_len_mean=float(np.mean(L)), row_len_max=max(L), micro_batches=len(c['mb_frac']['full']),
                                           frac_real_per_micro_batch={t: [round(x, 4) for x in v] for t, v in c['mb_frac'].items()},
                                           **({'row_lengths': L} if args.pad_dump_lengths else {})))
    A = np.asarray(all_len)
    out = dict(tag=world.tag(), updates=args.pad_updates, units='bytes' if world.bytes else 'chars', model=world.model_name,
               row_length=dict(mean=float(A.mean()), p50=float(np.percentile(A, 50)), p90=float(np.percentile(A, 90)), p99=float(np.percentile(A, 99)), max=int(A.max()), share_over_280=float((A > 280).mean())),
               padded_width_W=dict(mean=float(np.mean(Ws)), p10=float(np.percentile(Ws, 10)), p50=float(np.percentile(Ws, 50)), p90=float(np.percentile(Ws, 90)), max=int(max(Ws)), cap=int(world.caps['max_prompt'])),
               by_accum={}, per_update_at_configured_accum=per_update)
    for k in ACCUMS:
        a_, d = acc[k], {}
        for key in ('prompt',) + (('seq',) if plain else ()):
            today = 'full' if key == 'prompt' else 'own'              # what the code does now: split_batch keeps the full width; the plain transformer trims to the micro-batch's widest (own)
            d[key] = dict(
                today=today, frac_real_full_width=a_[f'{key}_real'] / a_[f'{key}_full'], frac_real_own_widest=a_[f'{key}_real'] / a_[f'{key}_own'], frac_real_sorted_own_widest=a_[f'{key}_real'] / a_[f'{key}_sorted'],
                mean_of_updates=dict(full=float(np.mean(fr[k][f'{key}_frac_real_full'])), own=float(np.mean(fr[k][f'{key}_frac_real_own'])), sorted=float(np.mean(fr[k][f'{key}_frac_real_sorted']))),
                p10_of_updates=dict(full=float(np.percentile(fr[k][f'{key}_frac_real_full'], 10)), own=float(np.percentile(fr[k][f'{key}_frac_real_own'], 10)), sorted=float(np.percentile(fr[k][f'{key}_frac_real_sorted'], 10))),
                cost_ratio_linear_today_over_sorted=a_[f'{key}_{today}'] / a_[f'{key}_sorted'],
                cost_ratio_quadratic_today_over_sorted=a_[f'{key}_{today}2'] / a_[f'{key}_sorted2'])
        out['by_accum'][str(k)] = d
    if lc:
        out['b3g2_rounds'] = dict(updates=len(lc), accum=args.accum, **rounds_stats(m0, lc, (args.accum,)),
                                  note='expected thinker rounds per row, n = max(K, longest program in the micro-batch + 2), K uniform on KS, gap_p ignored; sortpad changes which rows share n')
    out['note'] = ('prompt = the columns of prompt_ids that split_batch hands every micro-batch: today the full batch width W (this is what the reader / Gemma-front adapter / b3g2 thinker '
                   'see). For the plain arms the transformer itself already trims to the micro-batch\'s widest row (plain_tf_steps.py loss: W = max(2 + len + target)), so for "seq" (= prompt + '
                   '2 + target) today is "own widest". Cost ratios are rows x width (linear) and rows x width^2 (attention-like) of today over sorted + own widest, not seconds.')
    return out


def sec_sweep(world, args):
    out = dict(tag=world.tag(variant=args.variant), points=[])
    names = parse_variants(args.variant)
    for k in ACCUMS:
        pt = dict(accum=k, micro_batch_rows=-(-args.batch // k))
        tr = None
        try:
            log(f'sweep: accum {k} ...')
            tr = Trainer(world, args, names, accum=k, batch_seed=args.seed + 404)
            cold_eg(world)                       # every point replays the same rows from a cold tokenizer cache, so none is helped by an earlier point
            if world.device.type == 'cuda':
                torch.cuda.reset_peak_memory_stats()
            for _ in range(args.sweep_warmup):
                tr.update()
            per = free_run(tr, args.sweep_updates, max(1, args.sweep_updates))
            pt.update(s_per_update=per[0], peak_mem=peak_mem(world.device), oom=False)
        except Exception as e:
            if is_oom(e):
                pt.update(s_per_update=None, oom=True, peak_mem=peak_mem(world.device))
            elif isinstance(e, Skip):
                pt.update(skipped=str(e))
            else:
                raise
        finally:
            if tr is not None:
                tr.close()
            tr = None
            cleanup(world.device)
        log('  ->', json.dumps({k_: (round(v, 4) if isinstance(v, float) else v) for k_, v in pt.items() if k_ != 'peak_mem'}), 'peak_gb', pt.get('peak_mem', {}).get('allocated_gb'))
        out['points'].append(pt)
    return out


def aggregate_sync_warnings(records, n_updates):
    """[(filename, lineno, message)] -> [{where, per_update}] sorted by count: the python lines that forced a host-device sync."""
    c = collections.Counter((fn, ln) for fn, ln, _ in records)
    return [dict(where=f'{os.path.basename(fn)}:{ln}', file=fn, line=ln, per_update=n / n_updates) for (fn, ln), n in c.most_common()]


def sec_syncs(world, args):
    if world.device.type != 'cuda' or not hasattr(torch.cuda, 'set_sync_debug_mode'):
        raise Skip('sync audit needs CUDA (torch.cuda.set_sync_debug_mode)')
    tr = Trainer(world, args, parse_variants(args.variant), batch_seed=args.seed + 505)
    try:
        for _ in range(args.warmup):
            tr.update()
        n = args.sync_updates
        torch.cuda.synchronize()
        torch.cuda.set_sync_debug_mode('warn')
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always')
            for _ in range(n):
                tr.update()
        torch.cuda.set_sync_debug_mode(0)
        recs = [(w.filename, w.lineno, str(w.message)) for w in ws if 'synchroniz' in str(w.message).lower()]
        rows = aggregate_sync_warnings(recs, n)
        return dict(tag=world.tag(variant=args.variant), updates=n, syncs_per_update=len(recs) / n, sites=rows[:40],
                    note='each entry is a python line that called a synchronising CUDA op (.item(), .tolist(), .cpu(), nonzero, bool(tensor) ...)')
    finally:
        try:
            torch.cuda.set_sync_debug_mode(0)
        except Exception:
            pass
        tr.close(); cleanup(world.device)


def sec_bench(world, args):
    specs = [s.strip() for s in args.bench_list.split(';') if s.strip()]
    res = {s: [] for s in specs}
    for r in range(args.bench_rounds):
        for s in specs:
            log(f'bench round {r + 1}/{args.bench_rounds}: {s}')
            try:
                o = sec_throughput(world, args, variants=parse_variants(s))
                res[s].append(dict(s_per_update=o['s_per_update'], peak_gb=o['peak_mem']['allocated_gb'], accum=o['tag']['accum'], **({'compile_stats': o['compile_stats']} if 'compile_stats' in o else {})))
            except Skip as e:
                res[s].append(dict(skipped=str(e)))
            except Exception as e:
                if is_oom(e):
                    res[s].append(dict(oom=True))
                    cleanup(world.device)
                else:
                    raise
    out = dict(tag=world.tag(), rounds=args.bench_rounds, specs={})
    base = None
    for s in specs:
        ok = [x['s_per_update'] for x in res[s] if x.get('s_per_update')]
        d = dict(runs=res[s], s_per_update_median=float(np.median(ok)) if ok else None, s_per_update_min=min(ok) if ok else None,
                 peak_gb=max([x['peak_gb'] for x in res[s] if x.get('peak_gb')] or [None]) if any(x.get('peak_gb') for x in res[s]) else None)
        if s == 'baseline' or (base is None and s == specs[0]):
            base = d['s_per_update_median']
        out['specs'][s] = d
    for s in specs:
        d = out['specs'][s]
        d['speed_vs_baseline'] = (base / d['s_per_update_median']) if (base and d['s_per_update_median']) else None
    return out


# ---- equivalence check
def pin_stochastic(tr, k0):
    """Make the model's stochastic parts the same for any partition of the rows: gap_p = 0, ans_drill = 0, one fixed round count K0 (b3g2 draws K from KS per micro-batch
    and runs n = max(K, longest program + 2) rounds, which depends on the micro-batch mix). Returns a restore function."""
    m, undo = tr.model, []
    for attr, val in (('gap_p', 0.0), ('ans_drill', 0.0)):
        if hasattr(m, attr):
            undo.append((attr, getattr(m, attr)))
            setattr(m, attr, val)
    mods = []
    for name in ('custom_io.models.b3g2', 'custom_io.models.tool_h1'):
        mod = sys.modules.get(name)
        if mod is not None and hasattr(mod, 'KS') and hasattr(m, 'writer' if name.endswith('b3g2') else 'stop'):
            mods.append((mod, mod.KS))
            mod.KS = (k0,)

    def restore():
        for attr, val in undo:
            setattr(m, attr, val)
        for mod, ks in mods:
            mod.KS = ks
    return restore


def rounds_needed(world, batches):
    """K0 for pin_stochastic: 2 + the longest gold program (calls) among these batches' rows, at least 8."""
    m = world.new_model(world.a.seed)
    if not hasattr(m, 'trace_of'):
        return 8
    k = 0
    for b in batches:
        for r in b['rows']:
            k = max(k, len(m.trace_of(r)['gold']['texts']))
    return max(8, k + 2)


def grad_compare(gb, gv):
    nb, nv = gb.norm().item(), gv.norm().item()
    return dict(grad_cos=float((gb @ gv) / max(nb * nv, 1e-300)), grad_rel_l2=float((gv - gb).norm() / max(nb, 1e-300)), grad_max_abs=float((gv - gb).abs().max()), grad_norm_base=nb, grad_norm_var=nv)


# Fixed tolerances, PREREG-eg-once.md (written before any GPU number; never changed after seeing numbers)
E1_POS_COS, E1_ROW_COS, E1_SPREAD_X = 0.998, 0.9995, 1.5       # E1: bf16 on the GPU, per valid char position / per-row mean / x the old path's own spread
E1_GAP_FLOOR = 1e-4                                            # E1 rule 3 floor (PREREG amendment, before any GPU number): a largest row gap (1 - mean cos) <= 1e-4 passes rule 3 whatever the old spread
E2_MAX_ABS = 1e-4                                              # E2: fp32 on CPU, 64 rows, max abs difference of H
E3_LOSS_REL, E3_GRAD_COS = 1e-5, 0.99999                       # E3: fp32 on CPU, one update
E4_MEAN_ABS, E4_MEAN_DIFF, E4_LO, E4_HI = 0.02, 0.01, 100, 300   # E4: mean |dloss| and |difference of means| over updates 101..300


def pos_cos(a, b, chunk=8192):
    """Cosine of the matching rows of two [P, D] tensors (float64 math: identical inputs give exactly 1 up to 1e-16)."""
    out = [F.cosine_similarity(a[i:i + chunk].double(), b[i:i + chunk].double(), dim=-1, eps=1e-300) for i in range(0, a.shape[0], chunk)]
    return torch.cat(out) if out else torch.zeros(0, dtype=torch.double)


def _row_stats(c, row_id, n_rows):
    cnt = torch.bincount(row_id, minlength=n_rows).clamp(min=1).double()
    rm = torch.zeros(n_rows, dtype=torch.double).index_add_(0, row_id, c.double()) / cnt
    return dict(n_positions=int(c.numel()), min_pos_cos=float(c.min()), mean_pos_cos=float(c.mean()), positions_below_limit=int((c < E1_POS_COS).sum()),
                min_row_mean_cos=float(rm.min()), rows_below_limit=int((rm < E1_ROW_COS).sum()), max_row_gap=max(0.0, float((1 - rm).max())), mean_row_gap=max(0.0, float((1 - rm).mean())))


def e1_metrics(old_a, old_b, once, row_id, n_rows):
    """E1 on packed [P, D] states of the SAME valid char positions (row-major): old_a = old path at the job's accum, old_b = old path at half the accum (its own spread),
    once = eg_once. Rules exactly as registered: (1) every position cos(once, old_a) >= 0.998; (2) every row's mean cos >= 0.9995; (3) the largest per-row mean-cosine gap of once
    vs old_a is <= 1.5 x the largest per-row mean-cosine gap of old_a vs old_b, or <= E1_GAP_FLOOR (1e-4, the PREREG amendment of 10-14 ~12:10 AM ET: the old spread can be
    ~0 when the kernels are batch-invariant, and a gap far below bf16 noise and rule 2's 5e-4 must not fail on that; the 1e-12 only absorbs float64 noise)."""
    spread = _row_stats(pos_cos(old_a, old_b), row_id, n_rows)
    gap = _row_stats(pos_cos(once, old_a), row_id, n_rows)
    r1, r2 = gap['min_pos_cos'] >= E1_POS_COS, gap['rows_below_limit'] == 0
    r3 = gap['max_row_gap'] <= max(E1_SPREAD_X * spread['max_row_gap'] + 1e-12, E1_GAP_FLOOR)
    return dict(once_vs_old=gap, old_vs_old_half_accum=spread, rule1_every_position_cos_ge_0_998=bool(r1), rule2_every_row_mean_cos_ge_0_9995=bool(r2),
                rule3_gap_le_1_5x_old_spread=bool(r3), gap_over_spread=(gap['max_row_gap'] / spread['max_row_gap']) if spread['max_row_gap'] > 0 else None, passed=bool(r1 and r2 and r3))


def e2_metrics(old, once):
    d = (old.double() - once.double()).abs()
    m = float(d.max()) if d.numel() else 0.0
    out = dict(max_abs_diff=m, limit=E2_MAX_ABS, passed=bool(m <= E2_MAX_ABS), n_values=int(d.numel()))
    if d.numel():        # scale diagnostics only (NOT pass marks): is 1e-4 absolute small or large against the values themselves?
        a = old.double().abs().reshape(-1)
        mx, i = float(a.max()), int(d.reshape(-1).argmax())
        sub = a[::max(1, a.numel() // 4_000_000)]
        out.update(max_abs_value=mx, mean_abs_value=float(a.mean()), p999_abs_value=float(sub.sort().values[int(0.999 * (sub.numel() - 1))]),
                   max_abs_diff_over_max_abs_value=m / max(mx, 1e-300), value_at_max_diff=float(old.double().reshape(-1)[i]),
                   rel_diff_at_max_diff=m / max(float(a[i]), 1e-300), position_of_max_diff_flat=i)
    return out


def e4_metrics(old, var, lo=E4_LO, hi=E4_HI):
    """E4 on two loss traces: mean over updates lo+1..hi of |var - old| (<= 0.02) and |mean(var) - mean(old)| over the same updates (<= 0.01). Fewer than hi updates = a
    shorter window, reported but NOT the registered check."""
    old, var = np.asarray(old, float), np.asarray(var, float)
    n = len(old)
    full = n >= hi
    a, b = (lo, hi) if full else (min(lo, n // 3), n)
    d = np.abs(var - old)[a:b]
    out = dict(window_updates=[a + 1, b], registered_window=bool(full), mean_abs_diff=float(d.mean()), diff_of_means=float(abs(var[a:b].mean() - old[a:b].mean())),
               mean_old=float(old[a:b].mean()), mean_variant=float(var[a:b].mean()), limit_mean_abs_diff=E4_MEAN_ABS, limit_diff_of_means=E4_MEAN_DIFF)
    out['passed'] = bool(full and out['mean_abs_diff'] <= E4_MEAN_ABS and out['diff_of_means'] <= E4_MEAN_DIFF)
    return out


def states_old(eg, prompts, mask, T, device, cuts):
    """Packed [P, 768] H of the valid char positions (row-major) with the OLD path: eg.encode on the row chunks `cuts` (a micro-batch each), no memo."""
    parts = []
    m = mask.to(device)
    for lo, hi in zip(cuts, cuts[1:]):
        if hi > lo:
            eg._last = None
            H = eg.encode(prompts[lo:hi], T, device)[0]
            parts.append(H[m[lo:hi]].cpu())
    eg._last = None
    return torch.cat(parts)


def states_once(eg, prompts, mask, T, device, cuts, budget):
    """The same packed states with eg_once: one Gemma pass over all prompts, each chunk of `cuts` served from the cache. -> (states, OnceCache stats)."""
    oc = OnceCache(eg, budget).install()
    try:
        oc.precompute(prompts, device)
        parts = []
        m = mask.to(device)
        for lo, hi in zip(cuts, cuts[1:]):
            if hi > lo:
                H = oc.encode_cached(prompts[lo:hi], T, device)
                parts.append(H[m[lo:hi]].cpu())
        return torch.cat(parts), dict(hits=oc.hits, misses=oc.misses, gemma_chunks=oc.chunks, prompts=oc.prompts)
    finally:
        oc.uninstall()


def run_e1(world, args, batch):
    eg, device = world.eg, world.device
    prompts, mask, T, n = [r['prompt'] for r in batch['rows']], batch['prompt_mask'].bool(), batch['prompt_ids'].shape[1], len(batch['rows'])
    A, B = args.accum, max(1, args.accum // 2)
    cuts = lambda k: [round(i * n / k) for i in range(k + 1)]
    cold_eg(world)
    old_a = states_old(eg, prompts, mask, T, device, cuts(A))
    old_b = states_old(eg, prompts, mask, T, device, cuts(B))
    once, st = states_once(eg, prompts, mask, T, device, cuts(A), args.eg_once_budget)
    row_id = torch.repeat_interleave(torch.arange(n), mask.sum(1))
    out = e1_metrics(old_a, old_b, once, row_id, n)
    out.update(rows=n, accum_old=A, accum_half=B, state_dtype=str(old_a.dtype), device=str(device), eg=world.eg_mode, eg_once_stats=st,
               registered_setting=bool(device.type == 'cuda' and old_a.dtype == torch.bfloat16 and world.eg_mode == 'real'),
               note='registered: bf16 on the GPU with the real Gemma; anything else is a plumbing check')
    log(f'E1 ({out["state_dtype"]}, {device}, eg {world.eg_mode}): min position cos {out["once_vs_old"]["min_pos_cos"]:.6f}, min row-mean cos {out["once_vs_old"]["min_row_mean_cos"]:.6f}, '
        f'max row gap once {out["once_vs_old"]["max_row_gap"]:.3e} vs old spread {out["old_vs_old_half_accum"]["max_row_gap"]:.3e} -> {"PASS" if out["passed"] else "FAIL"}')
    return out


def run_e2(world, args, batch):
    """fp32 on the CPU, 64 rows: eg_once vs the old path, max abs difference of H. On a GPU box a second (CPU, fp32) Gemma is loaded for it."""
    if world.eg_mode == 'stub':
        eg, setting = StubEG(), 'stub front (plumbing only)'
    elif world.device.type == 'cpu':
        eg, setting = world.eg, 'real Gemma, fp32, cpu'
    else:
        eg, setting = type(world.eg)(by_bytes=world.eg.by_bytes, pre=world.eg.pre), 'real Gemma, fp32, cpu (a second copy loaded for this)'
    dev = torch.device('cpu')
    rows = batch['rows'][:64]
    prompts, mask, T = [r['prompt'] for r in rows], batch['prompt_mask'][:64].bool(), batch['prompt_ids'].shape[1]
    per = -(-len(batch['rows']) // args.accum)                      # rows per micro-batch of the old path
    cuts = sorted(set(list(range(0, len(rows), per)) + [len(rows)]))
    old = states_old(eg, prompts, mask, T, dev, cuts)
    once, st = states_once(eg, prompts, mask, T, dev, cuts, args.eg_once_budget)
    out = e2_metrics(old, once)
    out.update(rows=len(rows), micro_batch_rows=per, dtype=str(old.dtype), setting=setting, eg_once_stats=st, registered_setting=bool(world.eg_mode == 'real' and old.dtype == torch.float32))
    log(f'E2 ({setting}): max abs diff {out["max_abs_diff"]:.3e} (limit {E2_MAX_ABS:g}) -> {"PASS" if out["passed"] else "FAIL"}')
    return out


def weighting_report(world, args, batch, spec):
    """Does the variant change how much each token counts? A model whose loss is ONE token-mean cross_entropy per micro-batch (the plain arms) is trained with each token
    weighing 1/(K n_k) (K micro-batches, n_k supervised tokens of the micro-batch holding it): a different partition gives different weights. Counted with count_pass (no network run)."""
    names = [n for n in parse_variants(spec) if n != 'prefetch']
    base, var = Trainer(world, args, [], accum=args.accum), Trainer(world, args, names, accum=args.accum)
    try:
        info = {}
        for key, tr in (('base', base), ('var', var)):
            dev = PK.D.to_device(tr._prep(batch), tr.device)
            ps = tr._split(dev)
            infos = [count_pass(tr.model, {k: v for k, v in mb.items() if not k.startswith('_')}) for mb in ps]
            info[key] = (ps, infos)
        if any(i is None or i[1] != 'mean' for i in info['base'][1] + info['var'][1]):
            return dict(token_mean_per_micro_batch=False, weighting_changes=None, verdict='not analysed: this model\'s loss is not one token-mean cross_entropy per micro-batch '
                        '(b3g2 / b3 average per row, b3.py:91 and b3g2.py:566; its stop loss averages over rounds x rows, b3g2.py:569, and the rounds n and the K / gap / drill draws depend on the micro-batch '
                        'mix: see --equiv-pin). Check by the numbers below.')
        def weights(ps, infos, mode):
            w, ns = {}, [int(i[0].sum()) for i in infos]
            tot = sum(ns)
            for mb, (cnt, _), n_k in zip(ps, infos, ns):
                for r in mb['rows']:
                    w[r['id']] = (1.0 / (len(ps) * max(n_k, 1))) if mode == 'mb' else 1.0 / max(tot, 1)
            return w, ns
        wb, nb = weights(*info['base'], 'mb')
        wv, nv = weights(*info['var'], 'full' if 'sortpad_tokw' in names else 'mb')
        if 'oldw' in names:
            wv = dict(wb)                                              # oldw's weights ARE the old ones, by construction (checked by the E3 numbers)
        ratios = [wv[i] / wb[i] for i in wb]
        lo, hi = min(ratios), max(ratios)
        changes = bool(max(abs(lo - 1.0), abs(hi - 1.0)) > 1e-9)
        return dict(token_mean_per_micro_batch=True, weighting_changes=changes, micro_batches_old=len(info['base'][0]), micro_batches_variant=len(info['var'][0]),
                    tokens_per_micro_batch_old=nb, tokens_per_micro_batch_variant=nv, weight_ratio_min=lo, weight_ratio_max=hi,
                    verdict=('NOT EXACT: the variant changes the per-token weights (token-mean loss per micro-batch, ratio of a row\'s weight variant/old from %.3f to %.3f)' % (lo, hi)) if changes
                    else ('per-token weights restored by oldw' if 'oldw' in names else 'weights unchanged'))
    finally:
        base.close(); var.close()


def sec_equiv(world, args):
    specs = [s.strip() for s in (args.equiv_list or args.variant or 'sortpad').split(';') if s.strip()]
    it = world.batches(args.seed)
    first = next(it)
    pin = args.equiv_pin != 0
    k0 = rounds_needed(world, [first]) if pin else None
    if pin:
        log(f'equiv: stochastic parts pinned (gap_p 0, ans_drill 0, rounds K0={k0} where the model has them)')
    bf16 = lambda: torch.autocast(world.device.type, dtype=torch.bfloat16)
    fp32 = contextlib.nullcontext
    accum = args.accum
    out = dict(tag=world.tag(), pinned=pin, K0=k0, on_cpu=world.device.type != 'cuda', rows=len(first['rows']), specs={},
               prereg='PREREG-eg-once.md: E1 vectors (bf16 GPU), E2 vectors (fp32 CPU, 64 rows), E3 loss + gradient (fp32 CPU), E4 loss trace (bf16 GPU, 300 updates)',
               limits=dict(E1_position_cos=E1_POS_COS, E1_row_mean_cos=E1_ROW_COS, E1_x_old_spread=E1_SPREAD_X, E2_max_abs=E2_MAX_ABS, E3_loss_rel=E3_LOSS_REL, E3_grad_cos=E3_GRAD_COS,
                           E4_mean_abs=E4_MEAN_ABS, E4_diff_of_means=E4_MEAN_DIFF, E4_window=[E4_LO + 1, E4_HI]),
               E3_setting=f'fp32 on {world.device} (registered: cpu)', E3_registered_setting=world.device.type == 'cpu')
    wants_vec = args.equiv_vectors == 'yes' or (args.equiv_vectors == 'auto' and any('eg_once' in sp for sp in specs))
    if wants_vec:
        if not hasattr(world.eg, '_compute'):
            out['E1'] = out['E2'] = dict(skipped='this model has no EG front')
        else:
            for key, fn in (('E1', run_e1), ('E2', run_e2)):
                try:
                    out[key] = fn(world, args, first)
                except Exception as e:                                   # noqa: BLE001
                    import traceback
                    out[key] = dict(error=repr(e), traceback=traceback.format_exc())
                    log(f'equiv {key} FAILED: {e!r}')
                cleanup(world.device)

    def lg(spec, acc, prec, restore_box):
        tr = Trainer(world, args, parse_variants(spec), accum=acc)
        try:
            if pin:
                restore_box.append(pin_stochastic(tr, k0))
            return tr.loss_and_grad(first, fp32 if prec == 'fp32' else bf16)
        finally:
            for r in restore_box:
                r()
            restore_box.clear()
            tr.close(); cleanup(world.device)

    refs = {}
    precs = [p for p in (args.equiv_precisions or ('fp32,bf16' if world.device.type == 'cuda' else 'fp32')).split(',') if p]
    do_a1 = args.equiv_accum1 == 'yes' or (args.equiv_accum1 == 'auto' and world.device.type == 'cuda')
    out['precisions'] = precs
    for prec in precs:
        lb, gb = lg('baseline', accum, prec, [])
        lb2, gb2 = lg('baseline', accum, prec, [])
        try:
            if not do_a1:
                raise Skip('accum=1 reference off (--equiv-accum1)')
            l1, g1 = lg('baseline', 1, prec, [])
            a1 = dict(accum=1, loss=l1, abs_loss=abs(l1 - lb), rel_loss=abs(l1 - lb) / max(abs(lb), 1e-300), **grad_compare(gb, g1))
        except Skip:
            a1 = dict(accum=1, skipped=True)
        except Exception as e:                                           # the whole batch as ONE micro-batch may not fit a 24 GB card
            if not is_oom(e):
                raise
            cleanup(world.device)
            a1 = dict(accum=1, oom=True)
        refs[prec] = (lb, gb)
        out.setdefault('reference', {})[prec] = dict(baseline_loss=lb, baseline_rerun=dict(abs_loss=abs(lb2 - lb), **grad_compare(gb, gb2)), baseline_accum1_fullbatch=a1)
        log(f'equiv {prec}: baseline loss {lb:.6f}; rerun cos {out["reference"][prec]["baseline_rerun"]["grad_cos"]:.8f}; accum=1 cos ' + ('OOM' if a1.get('oom') else 'not run' if a1.get('skipped') else f'{a1["grad_cos"]:.8f}'))
    curve_cache = {}
    for spec in specs:
        res = dict(spec=spec)
        names = parse_variants(spec)
        try:
            for prec in precs:
                lb, gb = refs[prec]
                names_eff = ','.join(n for n in names if n != 'prefetch') or 'baseline'
                lv, gv = lg(names_eff, args.accum, prec, [])
                res[prec] = dict(loss_base=lb, loss_var=lv, abs_loss_diff=abs(lv - lb), rel_loss_diff=abs(lv - lb) / max(abs(lb), 1e-300), **grad_compare(gb, gv))
                log(f'equiv {spec} {prec}: |dloss| {res[prec]["abs_loss_diff"]:.3e} rel {res[prec]["rel_loss_diff"]:.3e} grad cos {res[prec]["grad_cos"]:.8f} relL2 {res[prec]["grad_rel_l2"]:.3e}')
            res['weighting'] = weighting_report(world, args, first, spec)
            f = res['fp32']
            f['E3_loss_ok'], f['E3_grad_cos_ok'] = bool(f['rel_loss_diff'] <= E3_LOSS_REL), bool(f['grad_cos'] >= E3_GRAD_COS)
            res['E3_verdict'] = ('NOT EXACT (token-mean weighting changes)' if res['weighting'].get('weighting_changes') else 'PASS' if (f['E3_loss_ok'] and f['E3_grad_cos_ok']) else 'FAIL')
            log(f'E3 {spec}: loss rel {f["rel_loss_diff"]:.2e} (limit {E3_LOSS_REL:g}), grad cos {f["grad_cos"]:.8f} (limit {E3_GRAD_COS:g}), weighting: {res["weighting"]["verdict"][:60]} -> {res["E3_verdict"]}')
            if 'prefetch' in names:
                res['prefetch_batches_identical'] = check_prefetch_identical(world, args, 5)
            if args.curve_updates:
                res['curve'] = loss_curves(world, args, spec, k0 if pin else None, curve_cache)
        except Skip as e:
            res['skipped'] = str(e)
            log(f'equiv {spec}: skipped ({e})')
        except Exception as e:
            if not is_oom(e):
                raise
            res['skipped'] = 'OOM'
            log(f'equiv {spec}: OOM')
            cleanup(world.device)
        out['specs'][spec] = res
    return out


def check_prefetch_identical(world, args, n):
    """The prefetch thread must hand over exactly the generator's batches (same rows, same tensors, same order)."""
    plain = world.batches(args.seed)
    pf = Prefetcher(world.batches(args.seed), lambda b: b, torch.device('cpu') if world.device.type != 'cuda' else world.device, 2)
    ok = True
    try:
        for _ in range(n):
            a, b = next(plain), next(pf)
            ok &= [r['id'] for r in a['rows']] == [r['id'] for r in b['rows']]
            for k, v in a.items():
                if torch.is_tensor(v):
                    ok &= bool(torch.equal(v.cpu(), b[k].cpu()))
    finally:
        pf.close()
    return bool(ok)


def loss_curves(world, args, spec, k0, cache=None):
    """E4: the loss of every update of an --curve-updates run (seed = --seed, the same rows in the same order), variant vs the old path, under the job's real lr schedule
    (--curve-schedule real; short = a cosine over the curve only). The old path's trace is computed once per call chain (cache)."""
    names = parse_variants(spec)
    cache = {} if cache is None else cache
    curves = {}
    for label, nm in (('baseline', []), ('variant', names)):
        if label == 'baseline' and 'baseline' in cache:
            curves[label] = cache['baseline']
            continue
        tr = Trainer(world, args, [n for n in nm if n != 'prefetch'], batch_seed=args.seed)
        restore = pin_stochastic(tr, k0) if k0 else (lambda: None)
        if args.curve_schedule == 'short':
            tr.lr_steps, tr.lr_warmup = args.curve_updates, max(1, args.curve_updates // 5)
        try:
            ls = []
            for i in range(args.curve_updates):
                loss, _, _ = tr.update()
                ls.append(float(loss))
                if (i + 1) % 50 == 0:
                    log(f'  curve {label} {spec}: update {i + 1}/{args.curve_updates} loss {ls[-1]:.5f}')
            curves[label] = ls
            if label == 'baseline':
                cache['baseline'] = ls
        finally:
            restore(); tr.close(); cleanup(world.device)
    b, v = np.asarray(curves['baseline']), np.asarray(curves['variant'])
    d = np.abs(v - b)
    out = dict(updates=len(b), schedule=args.curve_schedule, baseline=curves['baseline'], variant=curves['variant'], max_abs_diff=float(d.max()), mean_abs_diff=float(d.mean()),
               max_rel_diff=float((d / np.maximum(np.abs(b), 1e-12)).max()), final_baseline=float(b[-1]), final_variant=float(v[-1]), mean_last10_baseline=float(b[-10:].mean()),
               mean_last10_variant=float(v[-10:].mean()), E4=e4_metrics(b, v))
    e4 = out['E4']
    log(f'E4 {spec}: updates {e4["window_updates"][0]}..{e4["window_updates"][1]}: mean |dloss| {e4["mean_abs_diff"]:.4f} (limit {E4_MEAN_ABS}), diff of means {e4["diff_of_means"]:.4f} (limit {E4_MEAN_DIFF}) -> '
        + ('PASS' if e4['passed'] else 'FAIL' if e4['registered_window'] else 'not the registered window'))
    return out


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# markdown
# ------------------------------------------------------------------------------------------------------------------------------------------------------
def label(tag):
    return f'arm {tag["arm"]} | rung {tag["rung"]} | accum {tag["accum"]} | batch {tag["batch"]} | device {tag["device"]} | torch {tag["torch"]}' + (f' | variant {tag["variant"]}' if tag.get('variant') else '')


def table(head, rows):
    return ['| ' + ' | '.join(head) + ' |', '|' + '|'.join(['---'] * len(head)) + '|'] + ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows] + ['']


def f1(x, nd=1):
    return '-' if x is None else f'{x:.{nd}f}'


def render_md(res):
    m, S, L = res['meta'], res['sections'], []
    L += [f'# Profile: {m["arm"]} {m["rung"]} accum {m["accum"]} batch {m["batch"]} on {m["device_name"]} ({m["device"]}), torch {m["torch"]}', '',
          f'model {m["model"]}, {m["n_params"]:,} trained params, data {m["data"]} ({m["rows_loaded"]:,} rows), EG front {m["eg"]}, bf16 autocast {m["bf16_autocast"]}, seed {m["seed"]}, caps {os.path.basename(m["caps_file"])}', '']
    for name in SECTION_ORDER:
        s = S.get(name)
        if s is None:
            continue
        L += [f'## {name}', '']
        if 'skipped' in s or 'error' in s:
            L += [f'skipped: {s["skipped"]}' if 'skipped' in s else f'FAILED: {s["error"]}', '']
            continue
        L += [label(s['tag']), ''] if 'tag' in s else []
        if name == 'breakdown':
            st, sh = s['stages_ms'], s['share_of_wall']
            rows = [(k, f1(st[k]['mean']), f1(st[k]['median']), f1(st[k]['p90']), f'{100 * sh.get(k, 0):.1f}%') for k in ('fetch', 'h2d', 'split_total', 'forward', 'backward', 'clip', 'opt', 'other', 'wall') if k in st]
            L += ['ms per update (mean / median / p90 over %d timed updates, every region synced):' % s['updates'], ''] + table(['stage', 'mean', 'median', 'p90', 'share of wall'], rows)
            L += ['forward by group (exclusive, mean ms):', ''] + table(['group', 'ms', 'share of forward'], [(k, f1(v), f'{100 * v / max(st["forward"]["mean"], 1e-9):.1f}%') for k, v in s['forward_rollup_ms'].items()])
            L += ['forward sections (exclusive ms, calls per update, forward-hook calls seen DURING backward = recomputation):', ''] + table(
                ['section', 'mean ms', 'median', 'p90', 'calls/update', 'bwd calls/update'], [(k, f1(v['mean']), f1(v['median']), f1(v['p90']), f1(v['calls_per_update']), f1(v.get('bwd_calls_per_update', 0))) for k, v in list(s['forward_sections_ms'].items())[:30]])
            L += [s['note'], f'section timing overhead: {s["section_overhead_us"]:.0f} us per timed section x {s["hook_calls_per_update"]:.0f} sections per update = about {s["instrumentation_overhead_ms_est"]:.0f} ms of the synced wall (methods: {s["methods"]})', '']
            thr = S.get('throughput')
            if thr and 's_per_update' in thr:
                L += [f'synced wall {st["wall"]["mean"]:.0f} ms per update vs free-running {1e3 * thr["s_per_update"]:.0f} ms per update (throughput section): the stage split is shares of the SYNCED time, scale to the free-running number with care.', '']
        elif name == 'throughput':
            L += table(['s/update', 'updates/s', 'median chunk', 'p90 chunk', 'peak alloc GB', 'peak reserved GB'], [(f'{s["s_per_update"]:.4f}', f'{s["updates_per_s"]:.2f}', f'{s["median_chunk"]:.4f}', f'{s["p90_chunk"]:.4f}',
                                                                                                                  f1(s['peak_mem']['allocated_gb'], 2), f1(s['peak_mem']['reserved_gb'], 2))])
            if s.get('variant_stats_total'):
                L += [f'variant counters (whole run incl. warmup): {json.dumps(s["variant_stats_total"])}', '']
        elif name == 'profiler':
            L += [f'CPU op self time per update {f1(s["cpu_op_self_time_ms_per_update"])} ms; wall per update {f1(s["wall_ms_per_update"])} ms (profiler overhead included)', '']
            c = s.get('cuda')
            if c:
                lb = s['launch_bound']
                L += [f'WARNING: {s["warning"]}', ''] if s.get('warning') else []
                L += table(['kernel ms/update', 'kernels/update', 'mean kernel us', 'GPU busy / wall', 'idle gap / wall', 'launch calls/update', 'stream syncs/update', 'DtoH copies/update', 'CPU op / kernel time', 'verdict'],
                           [(f1(c['kernel_time_ms_per_update']), f1(c['kernels_per_update'], 0), f1(c['mean_kernel_us']), f1(c['gpu_busy_fraction_of_wall'], 3), f1(c['idle_gap_fraction_of_wall'], 3), f1(c['cuda_launch_calls_per_update'], 0),
                             f1(c['stream_syncs_per_update'], 1), f1(c['dtoh_copies_per_update'], 1), f1(lb['cpu_op_time_over_cuda_kernel_time'], 2), lb['verdict'])])
                L += ['top 25 CUDA kernels by total time:', ''] + table(['kernel', 'total ms', 'count', 'avg us', 'share'], [(k['name'][:90].replace('|', '/'), f1(k['total_ms']), k['count'], f1(k['avg_us']), f'{100 * k["share"]:.1f}%') for k in c['top_kernels']])
            else:
                L += [s.get('warning') or '(no CUDA kernels: CPU run)', '']
            L += ['top 25 CPU ops by self time:', ''] + table(['op', 'self CPU ms (all active)', 'ms/update', 'calls', 'share'], [(k['name'][:70].replace('|', '/'), f1(k['self_cpu_ms']), f1(k['self_cpu_ms_per_update']), k['calls'], f'{100 * k["share"]:.1f}%') for k in s['top_cpu_ops']])
        elif name == 'padding':
            r, w = s['row_length'], s['padded_width_W']
            L += [f'row prompt length ({s["units"]}): mean {r["mean"]:.0f}, p50 {r["p50"]:.0f}, p90 {r["p90"]:.0f}, p99 {r["p99"]:.0f}, max {r["max"]}, share over 280: {100 * r["share_over_280"]:.1f}%; '
                  f'padded width W of a {m["batch"]}-row update: mean {w["mean"]:.0f}, p10 {w["p10"]:.0f}, p50 {w["p50"]:.0f}, p90 {w["p90"]:.0f}, max {w["max"]} (cap {w["cap"]}); {s["updates"]} updates', '']
            rows = []
            for k, d in s['by_accum'].items():
                for key, v in d.items():
                    rows.append((k, key, v['today'], f'{100 * v["frac_real_full_width"]:.1f}%', f'{100 * v["frac_real_own_widest"]:.1f}%', f'{100 * v["frac_real_sorted_own_widest"]:.1f}%',
                                 f'{v["cost_ratio_linear_today_over_sorted"]:.2f}', f'{v["cost_ratio_quadratic_today_over_sorted"]:.2f}'))
            L += ['fraction of padded positions that are real (ratio of sums over the updates):', ''] + table(
                ['accum', 'quantity', 'what the code does today', 'full width W', 'own widest, random rows', 'sorted + own widest', 'linear cost today/sorted', 'quadratic cost today/sorted'], rows)
            if 'b3g2_rounds' in s:
                br = s['b3g2_rounds']
                L += [f'thinker rounds per row (accum {br["accum"]}, {br["updates"]} updates): ' + '; '.join(
                    f'{nm}: mean {v["mean_rounds_per_row"]:.2f} (rows with calls {v["mean_rounds_rows_with_calls"]:.2f}, without {v["mean_rounds_rows_without_calls"]:.2f}, share with calls {100 * v["share_rows_with_calls"]:.0f}%)' for nm, v in br.items() if isinstance(v, dict)), '']
            L += [s['note'], '']
        elif name == 'sweep':
            L += table(['accum', 'rows/micro-batch', 's/update', 'peak alloc GB', 'peak reserved GB', 'note'], [(p['accum'], p['micro_batch_rows'], f1(p.get('s_per_update'), 4), f1(p['peak_mem']['allocated_gb'], 2), f1(p['peak_mem']['reserved_gb'], 2), 'OOM' if p.get('oom') else p.get('skipped', '')) for p in s['points']])
        elif name == 'syncs':
            L += [f'{s["syncs_per_update"]:.1f} synchronising calls per update', ''] + table(['python line', 'calls per update'], [(x['where'], f1(x['per_update'], 1)) for x in s['sites'][:25]])
        elif name == 'bench':
            L += table(['variant', 'median s/update', 'speed vs baseline', 'peak GB', 'runs'], [(k, f1(v['s_per_update_median'], 4), f1(v['speed_vs_baseline'], 3), f1(v['peak_gb'], 2), '; '.join('OOM' if r.get('oom') else r.get('skipped', f'{r.get("s_per_update", 0):.4f}') for r in v['runs'])) for k, v in s['specs'].items()])
        elif name == 'equiv':
            lim = s['limits']
            L += [f'pre-registration: {s["prereg"]}', f'stochastic parts pinned: {s["pinned"]} (K0 {s["K0"]}); rows {s["rows"]}; on CPU (fp32, no autocast): {s["on_cpu"]}; E3 setting: {s["E3_setting"]}', '']
            e1, e2 = s.get('E1'), s.get('E2')
            if e1 and 'once_vs_old' in e1:
                g, sp = e1['once_vs_old'], e1['old_vs_old_half_accum']
                L += [f'### E1: eg_once vs the old path, Gemma state H at every valid char position ({e1["rows"]} rows, {e1["state_dtype"]}, {e1["device"]}, eg {e1["eg"]}; registered setting met: {e1["registered_setting"]})', '']
                L += table(['comparison', 'min position cos', 'positions < 0.998', 'min row-mean cos', 'rows < 0.9995', 'largest per-row mean-cos gap'],
                           [(f'old accum {e1["accum_old"]} vs old accum {e1["accum_half"]} (the old path\'s own spread)', f'{sp["min_pos_cos"]:.6f}', f'{sp["positions_below_limit"]}', f'{sp["min_row_mean_cos"]:.6f}', f'{sp["rows_below_limit"]}', f'{sp["max_row_gap"]:.3e}'),
                            (f'eg_once vs old accum {e1["accum_old"]}', f'{g["min_pos_cos"]:.6f}', f'{g["positions_below_limit"]}', f'{g["min_row_mean_cos"]:.6f}', f'{g["rows_below_limit"]}', f'{g["max_row_gap"]:.3e}')])
                L += [f'rules as registered: (1) every position cos >= {lim["E1_position_cos"]}: {"PASS" if e1["rule1_every_position_cos_ge_0_998"] else "FAIL"}; (2) every row-mean cos >= {lim["E1_row_mean_cos"]}: '
                      f'{"PASS" if e1["rule2_every_row_mean_cos_ge_0_9995"] else "FAIL"}; (3) eg_once gap <= {lim["E1_x_old_spread"]} x the old spread (ratio {f1(e1["gap_over_spread"], 2)}): '
                      f'{"PASS" if e1["rule3_gap_le_1_5x_old_spread"] else "FAIL"}. **E1 overall: {"PASS" if e1["passed"] else "FAIL"}**', '']
            elif e1:
                L += [f'E1: {e1.get("skipped") or e1.get("error")}', '']
            if e2 and 'max_abs_diff' in e2:
                L += [f'### E2: eg_once vs the old path, {e2["rows"]} rows, {e2["setting"]} (registered setting met: {e2["registered_setting"]}): max abs diff of H {e2["max_abs_diff"]:.3e} (limit {e2["limit"]:g}). **E2: {"PASS" if e2["passed"] else "FAIL"}**', '']
                if 'max_abs_value' in e2:
                    L += [f'scale (diagnostic, not a mark): max |H| {e2["max_abs_value"]:.4g}, p99.9 |H| {e2["p999_abs_value"]:.4g}, mean |H| {e2["mean_abs_value"]:.4g}; max abs diff / max |H| {e2["max_abs_diff_over_max_abs_value"]:.3e}; '
                          f'the largest difference sits on a value of {e2["value_at_max_diff"]:.4g} (relative {e2["rel_diff_at_max_diff"]:.3e})', '']
            elif e2:
                L += [f'E2: {e2.get("skipped") or e2.get("error")}', '']
            L += ['### E3: loss and gradient of one update (rule: loss rel diff <= %g and gradient cosine >= %g; token-mean weighting changes = NOT EXACT)' % (lim['E3_loss_rel'], lim['E3_grad_cos']), '']
            rows = []
            for prec in s['precisions']:
                ref = s['reference'][prec]
                rows.append((f'baseline rerun ({prec})', f'{ref["baseline_rerun"]["abs_loss"]:.2e}', '-', f'{ref["baseline_rerun"]["grad_cos"]:.8f}', f'{ref["baseline_rerun"]["grad_rel_l2"]:.2e}', 'noise floor', ''))
                a1 = ref['baseline_accum1_fullbatch']
                rows.append((f'accum=1 full batch ({prec})', 'OOM' if a1.get('oom') else 'not run', '', '', '', '', '') if (a1.get('oom') or a1.get('skipped')) else (f'accum=1 full batch ({prec})', f'{a1["abs_loss"]:.2e}', f'{a1["rel_loss"]:.2e}', f'{a1["grad_cos"]:.8f}', f'{a1["grad_rel_l2"]:.2e}', 'reference only', ''))
            for spec, r in s['specs'].items():
                if 'skipped' in r:
                    rows.append((spec, 'skipped', r['skipped'], '', '', '', ''))
                    continue
                for prec in s['precisions']:
                    rows.append((f'{spec} ({prec})', f'{r[prec]["abs_loss_diff"]:.2e}', f'{r[prec]["rel_loss_diff"]:.2e}', f'{r[prec]["grad_cos"]:.8f}', f'{r[prec]["grad_rel_l2"]:.2e}',
                                 f'**{r["E3_verdict"]}**' if prec == 'fp32' else '', r['weighting']['verdict'][:110] if prec == 'fp32' else ''))
            L += table(['vs baseline', '|d loss|', 'rel d loss', 'grad cosine', 'grad rel L2', 'E3 (fp32 row)', 'per-token weighting'], rows)
            for spec, r in s['specs'].items():
                if 'curve' in r:
                    c, e4 = r['curve'], r['curve']['E4']
                    L += [f'### E4 {spec}: {c["updates"]}-update loss trace (schedule {c["schedule"]}): updates {e4["window_updates"][0]}..{e4["window_updates"][1]}: mean |loss_variant - loss_old| {e4["mean_abs_diff"]:.4f} '
                          f'(limit {e4["limit_mean_abs_diff"]}), difference of the two means {e4["diff_of_means"]:.4f} (limit {e4["limit_diff_of_means"]}; old {e4["mean_old"]:.4f}, variant {e4["mean_variant"]:.4f}). '
                          + ('**E4: PASS**' if e4['passed'] else '**E4: FAIL**' if e4['registered_window'] else '(shorter than the registered 300 updates: not the check)'), '']
                if 'prefetch_batches_identical' in r:
                    L += [f'prefetch batches identical to the plain iterator: {r["prefetch_batches_identical"]}', '']
    return '\n'.join(L) + '\n'


def write_profiler_files(res, out):
    """The profiler section on its own: <out>.profiler.json and <out>.profiler.md (top-25 CUDA kernels, top-25 CPU ops, launches per update, launch-bound indicator)."""
    base = os.path.splitext(out)[0] + '.profiler'
    one = dict(meta=res['meta'], sections=dict(profiler=res['sections']['profiler']))
    json.dump(one, open(base + '.json', 'w'), indent=1, default=str)
    open(base + '.md', 'w').write(render_md(one))


# ------------------------------------------------------------------------------------------------------------------------------------------------------
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--arm', choices=sorted(ARM_INFO), default='PTS')
    ap.add_argument('--rung', default='3M')
    ap.add_argument('--accum', type=int, help='default: the PC queue line of the arm (PTS/PTC 16, B3G2 32)')
    ap.add_argument('--batch', type=int, default=256)
    ap.add_argument('--data', default='synthetic', help='the pool dir with train.jsonl (job.py: WORK/pools/<key>/), or "synthetic"')
    ap.add_argument('--rows', type=int, help='rows sampled uniformly from train.jsonl (0 = all; default 200000); synthetic: how many to make (default 4000)')
    ap.add_argument('--pkg-root', help='folder that contains custom_io/ (e.g. the PC job\'s src-b3g2 / src-ptc)')
    ap.add_argument('--caps', help='caps json (default: the arm\'s pinned file in custom_io/g8a: PTS/PTC caps_b3s.json, B3G2 caps_b3g2.json, PT/B2 caps_g.json)')
    ap.add_argument('--b2-extra', default='{}', help='JSON merged into job.py\'s --b2-extra {"eg_embed": true}')
    ap.add_argument('--eg', choices=['auto', 'real', 'stub'], default='auto', help='auto: stub on CPU / --tiny, the real EmbeddingGemma 2 on CUDA')
    ap.add_argument('--tiny', action='store_true', help='CPU smoke shapes (d 48, 1 block) as g8a/speed.py and b3_cost.py')
    ap.add_argument('--synth-letters', type=int, help='synthetic data: longest prompt (default: the caps max_prompt)')
    ap.add_argument('--device', default='auto')
    ap.add_argument('--no-bf16', dest='bf16', action='store_false', help='fp32 (CUDA runs use bf16 autocast like train.py --bf16)')
    ap.add_argument('--seed', type=int, default=400)
    ap.add_argument('--out', required=True, help='result json; the markdown goes beside it')
    ap.add_argument('--sections', default=DEFAULT_SECTIONS)
    ap.add_argument('--variant', default='', help='comma list composed together, e.g. sortpad,bigmb,tf32 (see --list-variants)')
    ap.add_argument('--list-variants', action='store_true')
    ap.add_argument('--updates', type=int, default=30, help='timed updates (breakdown, throughput, bench)')
    ap.add_argument('--warmup', type=int, default=5)
    ap.add_argument('--chunk', type=int, default=5, help='throughput: updates per synced chunk')
    ap.add_argument('--hook-level', choices=['top', 'deep'], default='top')
    ap.add_argument('--methods', choices=['all', 'none'], default='all', help='breakdown: also time the model\'s python methods (tokenize, tape_of, EG front ...); none = module hooks only (less overhead)')
    ap.add_argument('--lr-steps', type=int, default=24000)
    ap.add_argument('--lr-warmup', type=int, default=300)
    ap.add_argument('--prof-wait', type=int, default=1)
    ap.add_argument('--prof-warmup', type=int, default=1)
    ap.add_argument('--prof-active', type=int, help='profiled updates (default 3; 2 for b3g2 / ledger, whose updates launch 10^5+ kernels each and the profiler\'s own post-processing is slow)')
    ap.add_argument('--trace', help='also write the profiler chrome trace here')
    ap.add_argument('--pad-updates', type=int, default=300)
    ap.add_argument('--pad-rounds-updates', type=int, default=60, help='padding, b3g2 only: how many of those updates also get the thinker-rounds estimate (needs a trace per row)')
    ap.add_argument('--pad-dump-lengths', action='store_true', help='padding: put every row length of the configured-accum updates in the json')
    ap.add_argument('--sweep-warmup', type=int, default=2)
    ap.add_argument('--sweep-updates', type=int, default=6)
    ap.add_argument('--sync-updates', type=int, default=2)
    ap.add_argument('--bench-list', default='baseline;sortpad;sortpad,bigmb;sortpad,bigmb,tf32;sortpad,bigmb,prefetch')
    ap.add_argument('--bench-rounds', type=int, default=2)
    ap.add_argument('--equiv-check', action='store_true')
    ap.add_argument('--equiv-list', help='semicolon list of variant specs (default: --variant, else sortpad)')
    ap.add_argument('--equiv-pin', type=int, default=1, help='1: pin gap_p / ans_drill / rounds K so the partition cannot change the stochastic parts (b3g2); 0: leave them')
    ap.add_argument('--equiv-precisions', help='comma list of fp32,bf16 (default: fp32,bf16 on CUDA; fp32 on CPU, the registered E3 setting)')
    ap.add_argument('--equiv-accum1', choices=['auto', 'yes', 'no'], default='auto', help='the whole batch as one micro-batch, as a reference (auto: CUDA only; on CPU it can need many GB)')
    ap.add_argument('--curve-updates', type=int, default=300, help='E4: updates of the loss trace per variant (300 = the registered check; 0 skips)')
    ap.add_argument('--curve-schedule', choices=['real', 'short'], default='real', help='E4 lr schedule: real = the job\'s (--lr-steps / --lr-warmup), short = cosine over the curve only')
    ap.add_argument('--equiv-vectors', choices=['auto', 'yes', 'no'], default='auto', help='E1 / E2 (Gemma vectors, eg_once vs old): auto = when an equiv spec contains eg_once')
    ap.add_argument('--bigmb-accum', type=int)
    ap.add_argument('--pad-multiple', type=int, default=0, help='sortpad: round trimmed widths up to a multiple (default 1; 16 when a compile variant is on)')
    ap.add_argument('--sdpa-backend', choices=['auto', 'flash', 'efficient', 'math', 'cudnn'], default='auto')
    ap.add_argument('--compile-backend', default='inductor')
    ap.add_argument('--compile-cpu', action='store_true')
    ap.add_argument('--eg-chunks', type=int, default=2)
    ap.add_argument('--eg-once-budget', type=int, default=16384, help='eg_once: padded tokens per Gemma chunk')
    ap.add_argument('--prefetch-depth', type=int, default=2)
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.list_variants:
        for n, c in VARIANTS.items():
            print(f'{n:14s} {c.doc}')
        return
    a.accum = a.accum or ARM_INFO[a.arm]['accum']
    secs = [s for s in a.sections.split(',') if s]
    if a.equiv_check and 'equiv' not in secs:
        secs.append('equiv')
    bad = [s for s in secs if s not in SECTION_ORDER]
    if bad:
        raise SystemExit(f'unknown section(s) {bad}; known: {SECTION_ORDER}')
    parse_variants(a.variant)
    load_pkg(a.pkg_root)
    world = World(a)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    res = dict(meta=world.meta(), sections={})
    runners = dict(breakdown=sec_breakdown, throughput=sec_throughput, profiler=sec_profiler, padding=sec_padding, sweep=sec_sweep, syncs=sec_syncs, bench=sec_bench, equiv=sec_equiv)

    def write():
        res['meta']['n_params'] = world.n_params
        res['meta']['finished'] = datetime.datetime.now().isoformat(timespec='seconds')
        json.dump(res, open(a.out, 'w'), indent=1, default=str)
        open(os.path.splitext(a.out)[0] + '.md', 'w').write(render_md(res))
    for s in SECTION_ORDER:
        if s not in secs:
            continue
        log(f'=== section {s}')
        t = time.time()
        try:
            res['sections'][s] = runners[s](world, a)
        except Skip as e:
            res['sections'][s] = dict(skipped=str(e))
            log(f'section {s} skipped: {e}')
        except Exception as e:                                          # a failed section must not cost the others
            import traceback
            res['sections'][s] = dict(error=repr(e), traceback=traceback.format_exc())
            log(f'section {s} FAILED: {e!r}')
            traceback.print_exc()
            cleanup(world.device)
        res['sections'][s]['wall_s'] = round(time.time() - t, 1)
        write()
        if s == 'profiler' and 'top_cpu_ops' in res['sections'][s]:
            write_profiler_files(res, a.out)
    log('done', a.out, os.path.splitext(a.out)[0] + '.md')
    return res


if __name__ == '__main__':
    main()
