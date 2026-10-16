"""attrib.py: where do the ~76,000 kernel launches of one B3G2 3M update (accum 4) come from?  A launch-attribution instrument, run on the CPU.

WHAT IT DOES (shown by running it, see ATTRIB-CPU-2026-10-16.md)
  It replays train.py's update (split_batch -> per micro-batch model.loss -> (l / k).backward() -> clip_grad_norm_(1.0) -> AdamW step, zero_grad) on the real
  model (custom_io at commit 74d6e92c75, built through prof_train.World, so the weights, caps and rows are the harness's) with a torch dispatch mode that counts
  EVERY ATen op the update runs, and files each one under  phase x region x thinker round x op :
    phase   prep / forward / backward / recompute (checkpoint re-run of a forward function inside backward) / clip / optimizer
    region  thinker, call_writer, answer_writer, teacher_host, loop_bookkeeping, loss_tail, reader_gemma_tape, train_loop, optimizer, grad_accumulate, other
    round   t of the thinker loop (None = once per micro-batch: reader, tape, teacher of the answer, loss tail ...)
    kind    view (no kernel on any device), nolaunch (allocation / host scalar), kernel
  Forward ops get their region from the python stack (the custom_io functions on it) and their round from the loop (the two loops of B3G2.loop and B3G2._loss are
  re-compiled from their own source with exact text edits, the harness's patched_fn trick: the line numbers do not move).  Backward ops cannot be filed by stack
  (the autograd engine has no python frames), so a TorchFunctionMode runs during forward, finds the autograd nodes each torch call created (a dispatch mode sits BELOW
  autograd, where outputs have no grad_fn yet) and hangs a pre-hook and a post-hook on each node; a backward op takes the region / round of the node whose apply
  dispatched it, and an op between two nodes (the engine adding two gradients, AccumulateGrad) is filed under 'grad_accumulate'.  A backward op with a custom_io
  function on its stack is checkpoint recompute: phase 'recompute', region from that stack, round from the node whose saved tensors asked for it.
  Host syncs: torch.Tensor.tolist/item/__bool__/__int__/__float__/__index__/cpu/numpy/nonzero, torch.nonzero, Tensor.to / .cuda / torch.tensor / torch.as_tensor
  with a device target are wrapped and counted by call site (file:line), phase and round; the dispatch mode adds the index / index_put calls with tensor indices
  (implicit syncs on CUDA when the index is a boolean mask, and where the GPU record flags b3g2.py:375/376).

WHAT IT DOES NOT DO
  There is no GPU here.  Everything is counted on the CPU: the ATen op sequence is the one CUDA would see for the composite ops (linear -> t + addmm, ...), but
  (1) SDPA is a different kernel on CPU (flash-for-cpu) than on CUDA (efficient / flash with a bool-mask conversion and padding around it), (2) CUDA's bf16 autocast
  adds casts that a plain CPU run does not (a second configuration, torch.autocast('cpu', bfloat16), counts the casts CPU autocast makes, which is a different cast
  list from CUDA's), (3) the Gemma front is a tiny stub here (its ops are filed under reader_gemma_tape and marked stub; the real EmbeddingGemma 2 has none of these
  ops), (4) the CUDA launch numbers come from a small documented table (KERNEL_TABLE below) that maps one ATen op to the launches CUDA makes for it; it is an
  estimate, not a measurement, and the report shows a low and a high version.  A count of ops is shown; a launch count is suggested.

USE
  python attrib.py natural --out RUN.json                        # real 3M shape, seed 400, one warm-up update then one instrumented update (natural K draws)
  python attrib.py pinned --ks 4,8,12,16,24,32 --out RUN.json    # one micro-batch per K (forward + backward), K pinned; for the fit  ops = a + b n
  python attrib.py rows --out RUN.json                           # batch 64 vs 256 at accum 4, K pinned: does the per-round count depend on the rows?
  python attrib.py report RUN1.json RUN2.json ... --md OUT.md --json OUT.json
  (--tiny for the d 48 smoke shape, --pkg-root for the folder that contains custom_io/, default /home/user/src-g2f)
"""
import argparse, collections, contextlib, json, math, os, re, sys, time, types
import numpy as np
import torch
from torch.overrides import TorchFunctionMode
from torch.utils._python_dispatch import TorchDispatchMode

HERE = os.path.dirname(os.path.abspath(__file__))
PROFDIR = os.path.normpath(os.path.join(HERE, '..', 'prof'))
DEFAULT_PKG = os.environ.get('PROF_PKG_ROOT') or '/home/user/src-g2f'
THIS_FILE = os.path.abspath(__file__)

prof = None                  # the harness module (load)
PK = None                    # the custom_io modules (harness load_pkg)


def load(pkg_root=None):
    """Import the harness and the package once; returns the harness module."""
    global prof, PK
    if prof is None:
        if PROFDIR not in sys.path:
            sys.path.insert(0, PROFDIR)
        import prof_train
        prof = prof_train
    if PK is None:
        PK = prof.load_pkg(pkg_root or DEFAULT_PKG)
    return prof


# ---------------------------------------------------------------------------------------------------------------------------------- taxonomy
REGIONS = ('thinker', 'call_writer', 'answer_writer', 'teacher_host', 'loop_bookkeeping', 'loss_tail', 'reader_gemma_tape', 'train_loop', 'optimizer', 'grad_accumulate', 'other')
PHASES = ('prep', 'forward', 'backward', 'recompute', 'clip', 'optimizer')
WRITER_REGIONS = ('call_writer', 'answer_writer')
THINKER_KEYS = {'ledger.py:forward', 'tool.py:think', 'tool_h1.py:think'}                  # CBlock.forward, Tool.think, ToolH1.think
READER_KEYS = {'ledger.py:read', 'ledger.py:eg_term', 'ledger.py:tok_spots', 'ledger.py:tokenize', 'ledger.py:kv_of', 'tool.py:read_texts', 'tool.py:tape_of', 'tool.py:join_kv',
               'tool.py:num_memory', 'tool.py:slot_kv', 'tool.py:kv_of'}
LOSS_KEYS = {'b3g2.py:_loss', 'b3g2.py:loss', 'b3g2.py:plan', 'b3g2.py:train_golds', 'b3g2.py:trace_of', 'b3g2.py:build_trace', 'b3g2.py:keep_round'}
STUB_FUNCS = {'_compute', 'encode', 'encode_texts', 'align'}                               # prof_train.StubEG: the stand-in for the Gemma front


def key_of_code(co):
    """The taxonomy key of a code object: 'file.py:func' for a function of custom_io, 'stub:func' for the harness's stub Gemma, 'reader.py:...' etc.; None = not ours."""
    fn = co.co_filename
    if PK_DIR and fn.startswith(PK_DIR):
        return os.path.basename(fn) + ':' + co.co_name
    if fn == PROF_FILE and (co.co_name in STUB_FUNCS or co.co_qualname.startswith('_StubGemma')):
        return 'stub:' + co.co_name
    return None


PK_DIR = None                # '.../custom_io/' (set by Instrument)
PROF_FILE = None

_REGION_MEMO = {}


def region_of_keys(keys):
    """The taxonomy region of a python stack (tuple of keys, innermost first), or None if the stack has no custom_io function.  First rule that matches anywhere on the
    stack wins; the order puts the most specific work first (the teacher builds CPU tensors, the passes are the writer, CBlock is the thinker, ...)."""
    hit = _REGION_MEMO.get(keys)
    if hit is not None:
        return hit or None
    ks = set(keys)
    if not ks:
        r = ''
    elif 'writer.py:teacher' in ks:
        r = 'teacher_host'
    elif 'b3g2.py:call_pass' in ks:
        r = 'call_writer'
    elif 'b3g2.py:ans_pass' in ks:
        r = 'answer_writer'
    elif 'b3g2.py:answer_teacher' in ks or 'b3g2.py:line_context' in ks:
        r = 'call_writer' if 'b3g2.py:loop' in ks else 'answer_writer'
    elif ks & THINKER_KEYS:
        r = 'thinker'
    elif ks & READER_KEYS or any(k.startswith('stub:') or k.startswith('reader.py:') or k.startswith('eg.py:') for k in ks):
        r = 'reader_gemma_tape'
    elif 'b3g2.py:loop' in ks:
        r = 'loop_bookkeeping'
    elif ks & LOSS_KEYS:
        r = 'loss_tail'
    elif all(k.startswith(('data.py:', 'train.py:')) for k in ks):
        r = 'train_loop'                       # to_device / collate / split_batch called by the replica
    else:
        r = 'other'
    _REGION_MEMO[keys] = r
    return r or None


# ---------------------------------------------------------------------------------------------------------------------------------- op kinds and the CUDA table
EXTRA_VIEW = {'_unsafe_view'}
NOLAUNCH = {'empty', 'empty_strided', 'empty_like', 'new_empty', 'new_empty_strided', 'scalar_tensor', '_local_scalar_dense', 'resize_', 'set_', 'is_same_size', 'item',
            'lift_fresh_copy', 'is_nonzero', 'equal', '_record_function_enter_new', '_record_function_exit'}
_KIND = {}
_NAME = {}


def op_name(func):
    n = _NAME.get(func)
    if n is None:
        try:
            n = func._schema.name.split('::')[-1] + ('.' + func._schema.overload_name if func._schema.overload_name else '')
        except AttributeError:
            n = str(func)
        _NAME[func] = n
    return n


def op_kind(func):
    """'view' (no device kernel: the output aliases the input), 'nolaunch' (allocation or a host scalar), 'kernel'."""
    k = _KIND.get(func)
    if k is None:
        try:
            sch = func._schema
            base = sch.name.split('::')[-1]
            if base in EXTRA_VIEW or any(r.alias_info is not None and not r.alias_info.is_write for r in sch.returns):
                k = 'view'
            elif base in NOLAUNCH:
                k = 'nolaunch'
            else:
                k = 'kernel'
        except AttributeError:
            k = 'kernel'
        _KIND[func] = k
    return k


# CUDA kernel launches per ATen op (torch 2.11, sm_89).  Default for a 'kernel' op: 1.  A tuple (low, high) is an uncertainty bracket (the report shows both).
# Sources: read from the ATen CUDA kernels in memory (not re-verified here); the GPU-RUN-3 profile's top-kernel list was used only as a sanity check.  Every entry is
# SUGGESTED, none is measured.  CPU-only work (region teacher_host) is 0 whatever the op.
KERNEL_TABLE = {
    # matmuls: one cuBLAS / cutlass call (a split-K reduce kernel is ignored)
    'mm': 1, 'addmm': 1, 'bmm': 1, 'baddbmm': 1,
    # normalisation: forward is one kernel; backward = grad_input kernel + gamma/beta kernel(s)
    'native_layer_norm': 1, 'native_layer_norm_backward': (2, 3),
    # composite-explicit backward ops the dispatch mode sees as ONE op that CUDA runs as zeros + copy
    'select_backward': 2, 'slice_backward': 2, 'diagonal_backward': 2,
    # sorting-based scatter: embedding_dense_backward and index_put_ with accumulate=True sort the indices (cub radix sort) before the segmented add
    'embedding_dense_backward': (5, 9),
    'nonzero': (3, 4),
    'masked_select': 4,
}
# SDPA: CPU runs _scaled_dot_product_flash_attention_for_cpu (with or without attn_mask).  On CUDA a bool attn_mask makes the dispatcher pick the memory-efficient kernel
# after converting the mask: logical_not + scalar_tensor + where (3 launches) and, when the key length is not 16-aligned, a bias pad (2 launches); the attention itself is
# 1 launch forward and 1 (+ a zeros workspace) backward.  Without a mask it is flash: 1 forward, 3 backward (dot_do_o, dq_dk_dv, convert_dq) + a zeros fill.
SDPA_FWD = {'mask': (4, 6), 'nomask': (1, 1)}
SDPA_BWD = {'mask': (1, 2), 'nomask': (3, 4)}
INDEX_PUT_ACC = (6, 9)                  # index_put_(accumulate=True): index linearisation (2) + sort (3-4) + indexing_backward_kernel (1) + zeros
MEMCPY_OPS = {'copy_', '_to_copy', 'clone'}


def _same_layout(a, b):
    return a.dtype == b.dtype and a.is_contiguous() and b.is_contiguous()


def launches_of(name, func, args, kwargs, out):
    """-> (variant name, (low, high) launches, memcpys).  Same dtype + both contiguous copy = a cudaMemcpyAsync (not a kernel launch); a cast or a strided copy = 1 kernel."""
    base = name.split('.')[0]
    if base in MEMCPY_OPS:
        try:
            src, dst = (args[1], args[0]) if base == 'copy_' else (args[0], out)
            if isinstance(src, torch.Tensor) and isinstance(dst, torch.Tensor):
                if _same_layout(src, dst):
                    return name + '|memcpy', (0, 0), 1
                return name + ('|cast' if src.dtype != dst.dtype else '|strided'), (1, 1), 0
        except Exception:
            pass
        return name, (1, 1), 0
    if base.startswith('_scaled_dot_product_flash_attention_for_cpu') or base.startswith('_scaled_dot_product_efficient_attention') or base.startswith('_scaled_dot_product_flash_attention'):
        masked = kwargs.get('attn_mask') is not None
        if not masked and base.startswith('_scaled_dot_product_efficient_attention'):
            masked = args[3] is not None if len(args) > 3 else False
        bw = base.endswith('backward')
        v = (SDPA_BWD if bw else SDPA_FWD)['mask' if masked else 'nomask']
        return name + ('|mask' if masked else '|nomask'), v, 0
    if base in ('index_put_', 'index_put'):
        acc = args[3] if len(args) > 3 else kwargs.get('accumulate', False)
        return (name + '|acc', INDEX_PUT_ACC, 0) if acc else (name, (1, 1), 0)
    v = KERNEL_TABLE.get(base, 1)
    return name, (v, v) if isinstance(v, int) else v, 0


# multi-tensor-apply launch count (ATen MultiTensorApply.cuh: chunk 65536 elements; at most depth_to_max_tensors tensors and 320 blocks per launch)
def multi_tensor_launches(numels, depth, chunk=65536):
    max_t = {1: 110, 2: 64, 3: 48, 4: 36, 5: 30}[depth]
    launches, tcount, blocks = 0, 0, 0
    for n in numels:
        tcount += 1
        nch = max(1, -(-n // chunk))
        left = nch
        while left > 0:
            take = min(left, 320 - blocks)
            blocks += take
            left -= take
            if blocks == 320 and left > 0:
                launches += 1; blocks = 0; tcount = 1
        if tcount == max_t:
            launches += 1; tcount = 0; blocks = 0
    if tcount or blocks:
        launches += 1
    return launches


# ---------------------------------------------------------------------------------------------------------------------------------- the sync census
SYNC_TENSOR_METHODS = ('tolist', 'item', '__bool__', '__int__', '__float__', '__index__', 'cpu', 'numpy', 'nonzero', 'cuda', 'to')
SYNC_TORCH_FUNCS = ('nonzero', 'tensor', 'as_tensor')
_MISSING = object()


class SyncCensus:
    """Wraps the host-sync-prone calls while active and restores torch exactly on exit.  kinds: D2H (tolist, item, bool/int/float/index of a tensor, cpu, numpy, nonzero: on
    CUDA each waits for the stream and copies back), H2D (Tensor.to / .cuda / torch.tensor / torch.as_tensor with a device target: a pageable host-to-device copy that
    waits for the stream when non_blocking is False).  On this CPU run nothing blocks; the point is WHICH LINE makes the call and how often, per phase and round.  A
    call is counted whatever the tensor's device here (see SITE_NOTES for which lines hold a device tensor in the real run)."""

    def __init__(self, inst):
        self.inst = inst
        self.saved_t, self.saved_f = {}, {}
        self.on = False

    def _site(self):
        f = sys._getframe(2)
        fb = None
        while f is not None:
            fn = f.f_code.co_filename
            if PK_DIR and fn.startswith(PK_DIR):
                return os.path.basename(fn) + ':' + str(f.f_lineno)
            if fn == PROF_FILE:
                return 'prof_train.py:' + str(f.f_lineno)
            if fn != THIS_FILE and fb is None and '/torch/' not in fn:
                fb = os.path.basename(fn) + ':' + str(f.f_lineno)
            f = f.f_back
        return fb or 'torch-internal'

    def _count(self, kind, extra=None):
        if self.on:
            self.on = False                      # no recursion from our own bookkeeping
            try:
                self.inst.on_sync(kind, self._site() if extra is None else extra)
            finally:
                self.on = True

    def _wrap_method(self, name, kind):
        orig = getattr(torch.Tensor, name)
        census = self

        def w(self_, *a, **k):
            if not census.on:
                return orig(self_, *a, **k)
            if name != 'to' or _has_device_target(a, k):
                census._count('H2D' if name == 'to' else kind)
            census.on = False                    # a wrapped call made by the original (int() -> item ...) is the same sync, not a second one
            try:
                return orig(self_, *a, **k)
            finally:
                census.on = True
        w.__name__ = name
        return w

    def _wrap_func(self, name):
        orig = getattr(torch, name)
        census = self

        def w(*a, **k):
            if not census.on:
                return orig(*a, **k)
            if name == 'nonzero':
                census._count('D2H')
            elif k.get('device') is not None:
                census._count('H2D')
            census.on = False
            try:
                return orig(*a, **k)
            finally:
                census.on = True
        w.__name__ = name
        return w

    def __enter__(self):
        for name in SYNC_TENSOR_METHODS:
            self.saved_t[name] = torch.Tensor.__dict__.get(name, _MISSING)
            setattr(torch.Tensor, name, self._wrap_method(name, 'H2D' if name == 'cuda' else 'D2H'))
        for name in SYNC_TORCH_FUNCS:
            self.saved_f[name] = torch.__dict__.get(name, _MISSING)
            setattr(torch, name, self._wrap_func(name))
        self.on = True
        return self

    def __exit__(self, *exc):
        self.on = False
        for name, orig in self.saved_t.items():
            if orig is _MISSING:
                delattr(torch.Tensor, name)
            else:
                setattr(torch.Tensor, name, orig)
        for name, orig in self.saved_f.items():
            if orig is _MISSING:
                delattr(torch, name)
            else:
                setattr(torch, name, orig)
        self.saved_t, self.saved_f = {}, {}
        return False


def _has_device_target(a, k):
    """Tensor.to(...) arguments that name a device (a device, a device string, another tensor, device=...), not a dtype-only conversion."""
    if k.get('device') is not None:
        return True
    for x in a:
        if isinstance(x, (torch.device, torch.Tensor)):
            return True
        if isinstance(x, str):
            return True
    return False


# Hand-read notes per sync site (SUGGESTED: from reading the source at 74d6e92c75, and for the 'sync' class cross-checked against the GPU record, gpu-run-3-box1/
# b3g2_profile.json 'syncs', which lists the same lines).  class: sync = a device tensor in the real run, so on CUDA the call waits for the stream (D2H) or is a blocking
# pageable copy that waits (H2D); host = a CPU tensor in the real run (no device involved); noop = .to(device) of a tensor that is already there; stub = the harness stub
# of the Gemma front (the real front is eg.py:108 / :128 and transformers' masking_utils.py:335, 16 per update each in the GPU record).
SITE_NOTES = {
    'writer.py:121': ('sync', 'D2H', 'cids.cpu(), cmask.cpu() in ByteWriter.teacher: two device zeros made by line_context, copied straight back (2 per teacher call)'),
    'writer.py:138': ('sync', 'H2D', 'inp / tgt / fb / over .to(dev) at the end of ByteWriter.teacher: four blocking host-to-device copies per teacher call'),
    'writer.py:135': ('host', 'D2H', 'hit.any() in the teacher\'s python loops over CPU tensors (no device in the real run)'),
    'b3g2.py:350': ('sync', 'D2H', 'call.tolist(), kk.tolist(), (t > last).tolist(): the schedule sits on the device and is read back (3 per round t >= 1)'),
    'b3g2.py:355': ('sync', 'H2D', 'torch.tensor(sel, device=dev): the row list to the device (1 per round t >= 1)'),
    'b3g2.py:361': ('sync', 'D2H', 'ok.tolist(): which rows the call_pass got right (1 per round t >= 1)'),
    'b3g2.py:374': ('sync', 'D2H', 'call.nonzero(): the rows with a call this round (1 per round t >= 1)'),
    'b3g2.py:375': ('sync', 'implicit', 'cround[rows, kk[rows]] = t: index / index_put_ with two tensor indices; the GPU record flags this line (why CUDA waits there is untested)'),
    'b3g2.py:376': ('sync', 'implicit', 'shown[rows, kk[rows]] = True: same shape as line 375; flagged by the GPU record'),
    'b3g2.py:551': ('sync', 'D2H', 'if not ok.any(): bool of a device tensor (1 per round)'),
    'b3g2.py:553': ('sync', 'D2H', 'ok.nonzero()[:, 0] (1 per round)'),
    'b3g2.py:554': ('sync', 'D2H', 'bool(ok.all()) (1 per round)'),
    'b3g2.py:224': ('sync', 'H2D', 'torch.from_numpy(sched).to(dev) in plan (1 per micro-batch)'),
    'b3g2.py:534': ('host', 'D2H', 'int(torch.randint(...)): the loop-length draw is a CPU tensor, no stream wait'),
    'b3g2.py:535': ('sync', 'D2H', 'int(last.max()): the longest call round, a device tensor read back (1 per micro-batch)'),
    'b3g2.py:536': ('sync', 'H2D', 'torch.tensor([bool(L) ...], device=dev) for g["has"] (1 per micro-batch)'),
    'b3g2.py:567': ('noop', 'H2D', 'right.to(dev): right was made on dev already (torch.zeros(..., device=dev)), a no-op'),
    'tool.py:175': ('sync', 'H2D', 'torch.from_numpy(ids).to(dev) in read_texts (1 per read_texts call, 1 per micro-batch here)'),
    'tool.py:180': ('sync', 'H2D', 'torch.tensor(full, device=dev) in read_texts'),
    'prof_train.py:331': ('stub', 'H2D', 'stub front: ids / mask to the device (real: eg.py:108)'),
    'prof_train.py:341': ('stub', 'H2D', 'stub front: char-to-token map to the device (real: eg.py:128)'),
    'data.py:211': ('noop', 'H2D', 'to_device of the batch in the replica (once per update; a CPU no-op here)'),
    'torch-internal': ('noop', 'H2D', 'torch.nn.utils.clip_grad_norm_: norm.to(first_device) on tensors already there (no copy)'),
}


# ---------------------------------------------------------------------------------------------------------------------------------- the instrument
ENGINE = ('grad_accumulate', None, 'engine')


class Tagger(TorchFunctionMode):
    """Runs during forward only.  After each top-level torch call, finds the autograd nodes that call created (walk next_functions from its outputs until a node already
    seen) and hangs the pre / post hooks on them with the call's region and round."""

    def __init__(self, inst):
        super().__init__()
        self.inst = inst

    def __torch_function__(self, func, types, args=(), kwargs=None):
        out = func(*args, **(kwargs or {}))
        inst = self.inst
        if inst.tag_on and torch.is_grad_enabled():
            name = getattr(func, '__name__', '')
            if name == '__get__':
                return out
            outs = out if isinstance(out, (tuple, list)) else (out,)
            for o in outs:
                if isinstance(o, torch.Tensor):
                    gf = o.grad_fn
                    if gf is not None and id(gf) not in inst.seen:
                        inst.walk(gf)
            if args and isinstance(args[0], torch.Tensor) and (name.endswith('_') or name in ('__setitem__',) or out is None):
                gf = args[0].grad_fn
                if gf is not None and id(gf) not in inst.seen:
                    inst.walk(gf)
        return out


class Counter(TorchDispatchMode):
    def __init__(self, inst):
        super().__init__()
        self.inst = inst

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):
        kwargs = kwargs or {}
        out = func(*args, **kwargs)
        self.inst.on_op(func, args, kwargs, out)
        return out


class Instrument:
    """Holds the tallies of one update.  Use through Replica; see the module docstring."""

    def __init__(self, model, autocast=False):
        load()
        global PK_DIR, PROF_FILE
        PK_DIR = os.path.join(PK.root, 'custom_io') + os.sep
        PROF_FILE = os.path.abspath(prof.__file__)
        self.model = model
        self.phase = 'prep'
        self.cur_round = None
        self.think_t = None
        self.bwd_tag = ENGINE
        self.bwd_round_for_recompute = None
        self.tag_on = False
        self.seen = {}
        self.keep = []
        self.hooks = {}
        self.in_mb = False
        self.T = {}                 # (phase, region, rnd, op, kind) -> [count, launches_low, launches_high, memcpy]; the micro-batch in progress
        self.sync = collections.Counter()           # (kind, site, phase, rnd, region) -> count
        self.implicit_c = collections.Counter()     # (kind, site, phase, rnd) -> count
        self.U = {}                 # the same three for everything outside a micro-batch (split, loss accumulation, clip, optimizer)
        self.usync = collections.Counter()
        self.uimplicit = collections.Counter()
        self.mbs = []               # one dict per finished micro-batch
        self.nodes = collections.Counter()          # tagged / untagged / total
        self.think_mismatch = collections.Counter()         # thinker recompute: the round the think wrapper saw vs the round of the node that asked for the recompute
        self.ks = []                # (K, n) per micro-batch
        self.t_start = time.time()
        self._code = {}
        self._undo_inst, self._undo_cls = [], []
        self._installed = False
        self.counter = Counter(self)
        self.tagger = Tagger(self)
        self.census = SyncCensus(self)

    # ---- installation: patched loop / _loss, think wrappers
    def install(self):
        m = self.model
        cls = type(m)
        loop = prof.patched_fn(cls.loop, [('for t in range(n):', 'for t in self._ax_rounds(range(n), 0):')])
        loss = prof.patched_fn(cls._loss, [('for t, Z, M in per:', 'for t, Z, M in self._ax_rounds(per, 1):'),
                                           ('K = KS[int(torch.randint(len(KS), (1,)))]', 'K = self._ax_k(KS[int(torch.randint(len(KS), (1,)))])')])
        inst = self

        def rounds(it, which):
            for x in it:
                inst.cur_round = x if which == 0 else x[0]
                yield x
            inst.cur_round = None

        def kdraw(K):
            inst._k_pending = K
            return K
        self._undo_inst, self._undo_cls = [], []
        for attr, val in (('loop', types.MethodType(loop, m)), ('_loss', types.MethodType(loss, m)), ('_ax_rounds', rounds), ('_ax_k', kdraw)):
            prof.set_attr(m, attr, val, self._undo_inst)
        for c in (PK.models.tool_h1.ToolH1, PK.models.tool.Tool):
            orig = c.__dict__['think']
            self._undo_cls.append((c, orig))

            def make(orig):
                def think(self_, Z, kvs, kvx, mask, t):
                    prev = inst.think_t
                    inst.think_t = t
                    try:
                        return orig(self_, Z, kvs, kvx, mask, t)
                    finally:
                        inst.think_t = prev
                return think
            c.think = make(orig)
        self._installed = True
        return self

    def uninstall(self):
        for c, orig in reversed(getattr(self, '_undo_cls', [])):
            c.think = orig
        prof.undo_attrs(getattr(self, '_undo_inst', []))
        self._undo_cls, self._undo_inst = [], []
        self._installed = False

    # ---- stack
    def chain(self, skip=3):
        f = sys._getframe(skip)
        keys, line = [], None
        code = self._code
        while f is not None:
            co = f.f_code
            k = code.get(co, _MISSING)
            if k is _MISSING:
                k = code[co] = key_of_code(co)
            if k is not None:
                if line is None:
                    line = f.f_lineno
                keys.append(k)
            f = f.f_back
        return tuple(keys), line

    # ---- forward node tagging
    def hooks_for(self, tag):
        """(pre, post) hook pair for a (region, round) tag.  pre: the node about to apply owns the ops until post.  post: ops from here to the next pre are the engine's
        (adding two gradients into one buffer, AccumulateGrad): region grad_accumulate, round of the node that just finished (it produced the gradient being added)."""
        hk = self.hooks.get(tag)
        if hk is None:
            inst = self
            eng = ('grad_accumulate', tag[1], tag[0])            # (region, round, the region of the node that just finished: who produced the gradient being added)
            ptag = tag if tag[0] != 'grad_accumulate' else ('grad_accumulate', None, 'param')

            def pre(grad_outputs):
                inst.bwd_tag = ptag

            def post(grad_inputs, grad_outputs):
                inst.bwd_tag = eng
            hk = self.hooks[tag] = (pre, post)
        return hk

    def walk(self, gf):
        keys, _ = self.chain(skip=3)
        region = region_of_keys(keys) or ('train_loop' if self.phase in ('prep', 'forward', 'clip') else 'optimizer')
        tag = (region, self.cur_round)
        hk = self.hooks_for(tag)
        acc = self.hooks_for(('grad_accumulate', None))         # AccumulateGrad (a parameter's .grad += ...): once per micro-batch
        stack = [gf]
        seen = self.seen
        while stack:
            n = stack.pop()
            if n is None or id(n) in seen:
                continue
            seen[id(n)] = tag
            self.keep.append(n)
            if type(n).__name__ == 'AccumulateGrad':
                n.register_prehook(acc[0])
                n.register_hook(acc[1])
                continue
            n.register_prehook(hk[0])
            n.register_hook(hk[1])
            for nf, _ in n.next_functions:
                stack.append(nf)
        self.nodes['tagged'] += 1

    def verify_graph(self, loss):
        """Before backward: every node reachable from the loss must carry a tag; the ones that do not (history rebased in place that the torch-function walk did not reach)
        get region 'other', counted as untagged."""
        stack, seen2 = [loss.grad_fn], set()
        miss = 0
        hk = self.hooks_for(('other', None))
        acc = self.hooks_for(('grad_accumulate', None))
        while stack:
            n = stack.pop()
            if n is None or id(n) in seen2:
                continue
            seen2.add(id(n))
            self.nodes['reachable'] += 1
            if id(n) not in self.seen:
                self.seen[id(n)] = ('other', None)
                self.keep.append(n)
                miss += 1
                h = acc if type(n).__name__ == 'AccumulateGrad' else hk
                n.register_prehook(h[0])
                n.register_hook(h[1])
            for nf, _ in n.next_functions:
                stack.append(nf)
        self.nodes['untagged'] += miss
        return miss

    # ---- tallies
    def add(self, phase, region, rnd, op, kind, lo, hi, mem):
        key = (phase, region, rnd, op, kind)
        T = self.T if self.in_mb else self.U
        v = T.get(key)
        if v is None:
            T[key] = [1, lo, hi, mem]
        else:
            v[0] += 1; v[1] += lo; v[2] += hi; v[3] += mem

    def on_op(self, func, args, kwargs, out):
        kind = op_kind(func)
        name = op_name(func)
        phase = self.phase
        keys, line = self.chain(skip=3)
        if phase == 'backward':
            if keys:
                phase, region, rnd = 'recompute', region_of_keys(keys), self.bwd_tag[1]
                if region == 'thinker' and self.think_t is not None:
                    self.think_mismatch['equal' if self.think_t == rnd else 'differ'] += 1
            else:
                region, rnd = self.bwd_tag[0], self.bwd_tag[1]
        else:
            region = region_of_keys(keys)
            if region is None:
                region = 'optimizer' if phase == 'optimizer' else 'train_loop'
            rnd = self.cur_round
        if kind == 'kernel':
            vname, (lo, hi), mem = launches_of(name, func, args, kwargs, out)
            if region == 'teacher_host':
                lo = hi = 0
        else:
            vname, lo, hi, mem = name, 0, 0, 0
        if region == 'reader_gemma_tape' and keys and any(k.startswith('stub:') for k in keys):
            vname = vname + '|gemma_stub'
        if region == 'grad_accumulate' and phase == 'backward':
            vname = vname + '@' + self.bwd_tag[2]              # the engine's own add / AccumulateGrad, by the region that produced the gradient
        self.add(phase, region, rnd, vname, kind, lo, hi, mem)
        base = name.split('.')[0]
        if base in ('index', 'index_put_', 'index_put') and keys:
            idx = args[1]
            ts = [x for x in idx if isinstance(x, torch.Tensor)] if isinstance(idx, (list, tuple)) else []
            if ts:
                mask = any(x.dtype in (torch.bool, torch.uint8) for x in ts)
                (self.implicit_c if self.in_mb else self.uimplicit)[(('index[bool]' if mask else 'index[long]') + ('' if base == 'index' else '/put'), keys[0].split(':')[0] + ':' + str(line), phase, rnd)] += 1

    def on_sync(self, kind, site):
        keys, _ = self.chain(skip=4)                       # on_sync <- SyncCensus._count <- the wrapper <- the caller
        region = region_of_keys(keys) or 'train_loop'
        (self.sync if self.in_mb else self.usync)[(kind, site, self.phase, self.cur_round, region)] += 1

    # ---- micro-batch bookkeeping
    def begin_mb(self):
        self.in_mb = True
        self.T = {}
        self.sync = collections.Counter()
        self.implicit_c = collections.Counter()
        self.seen, self.keep = {}, []
        self.cur_round, self.bwd_tag = None, ENGINE
        self._k_pending = None

    def end_mb(self, rows, n):
        self.mbs.append(dict(rows=rows, n=n, K=self._k_pending, T=self.T, sync=self.sync, implicit=self.implicit_c, nodes=dict(self.nodes),
                             think_mismatch=dict(self.think_mismatch)))
        self.nodes = collections.Counter()
        self.think_mismatch = collections.Counter()
        self.T, self.sync, self.implicit_c = {}, collections.Counter(), collections.Counter()
        self.seen, self.keep = {}, []
        self.in_mb = False


# ---------------------------------------------------------------------------------------------------------------------------------- the replica of train.py's update
class Replica:
    """train.py's update loop on the harness's world: split_batch, per micro-batch loss / backward, clip, AdamW.  update(inst) counts it; update(None) runs it plain.
    fused: the optimizer (the harness uses fused only on CUDA; the CPU build has the same fused AdamW op, so it is switched on here to count the op sequence CUDA runs)."""

    def __init__(self, world, accum=4, seed=None, batch_seed=None, autocast=False, fused=True):
        load()
        self.w, self.accum = world, accum
        seed = world.a.seed if seed is None else seed
        prof.seed_all(seed)
        self.model = world.new_model(seed)
        self.model.train()
        self.opt = prof.make_opt(self.model, world.lr, world.device, fused=fused)
        self.it = world.batches(seed if batch_seed is None else batch_seed)
        self.step = 0
        self.autocast = autocast
        self.amp = (lambda: torch.autocast('cpu', dtype=torch.bfloat16)) if autocast else contextlib.nullcontext

    def next_batch(self):
        return PK.D.to_device(next(self.it), self.w.device)

    def micro(self, mb, k, inst=None):
        """One micro-batch: forward under amp, scaled backward.  Returns (loss, aux)."""
        if inst is None:
            with self.amp():
                out = self.model.loss(mb)
            l_i, a_i = out if isinstance(out, tuple) else (out, {})
            (l_i / k).backward()
            return l_i, a_i
        inst.begin_mb()
        inst.phase = 'forward'
        inst.tag_on = True
        with inst.tagger:
            with self.amp():
                out = self.model.loss(mb)
            l_i, a_i = out if isinstance(out, tuple) else (out, {})
            scaled = l_i / k
        inst.tag_on = False
        inst.verify_graph(scaled)
        inst.phase = 'backward'
        scaled.backward()
        inst.phase = 'forward'
        inst.end_mb(len(mb['rows']), float(a_i.get('rounds', 0)) if isinstance(a_i, dict) else None)
        return l_i, a_i

    def update(self, inst=None):
        """One full update.  -> dict(loss, rounds per micro-batch, wall seconds).  With inst: the instrument must be installed on self.model (inst.install())."""
        t0 = time.time()
        lr = PK.TR.lr_at(self.step, self.w.a.lr_steps, self.w.a.lr_warmup, self.w.lr)
        for g in self.opt.param_groups:
            g['lr'] = lr
        ctx = contextlib.ExitStack()
        if inst is not None:
            ctx.enter_context(inst.counter)
            ctx.enter_context(inst.census)
            inst.phase = 'prep'
        with ctx:
            dev = self.next_batch()
            parts = PK.TR.split_batch(dev, self.accum)
            loss, ns = 0.0, []
            for mb in parts:
                l_i, a_i = self.micro(mb, len(parts), inst)
                loss = loss + l_i.detach() / len(parts)
                ns.append(a_i.get('rounds') if isinstance(a_i, dict) else None)
            if inst is not None:
                inst.phase = 'clip'
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            if inst is not None:
                inst.phase = 'optimizer'
            self.opt.step()
            self.opt.zero_grad(set_to_none=True)
            if inst is not None:
                inst.phase = 'prep'
        self.step += 1
        return dict(loss=float(loss), rounds=ns, wall_s=time.time() - t0)

    def single_mb(self, mb_index=0, k=None, inst=None):
        """Forward + backward of one micro-batch of the next batch (no clip, no optimizer): the cheap probe for the fit and the rows comparison."""
        dev = self.next_batch()
        parts = PK.TR.split_batch(dev, self.accum)
        return self.micro(parts[mb_index], len(parts) if k is None else k, inst)


@contextlib.contextmanager
def pin_ks(ks):
    """b3g2's training loop length is K = KS[randint]; replace the tuple in the module namespace (as prof_train.pin_stochastic does) for the duration."""
    mod = sys.modules['custom_io.models.b3g2']
    old = mod.KS
    mod.KS = tuple(ks)
    try:
        yield
    finally:
        mod.KS = old


# ---------------------------------------------------------------------------------------------------------------------------------- reduction
def pack_T(T):
    """tallies -> JSON rows [phase, region, rnd, op, kind, count, low, high, memcpy]"""
    return [[p, r, rnd, op, kind, v[0], v[1], v[2], v[3]] for (p, r, rnd, op, kind), v in sorted(T.items(), key=lambda kv: (kv[0][0], kv[0][1], -1 if kv[0][2] is None else kv[0][2], kv[0][3]))]


def pack_counter(c):
    return [[*k, v] for k, v in sorted(c.items(), key=lambda kv: tuple(str(x) for x in kv[0]))]


def pack_run(inst, replica, extra=None):
    m = []
    for r in inst.mbs:
        m.append(dict(rows=r['rows'], n=r['n'], K=r['K'], T=pack_T(r['T']), sync=pack_counter(r['sync']), implicit=pack_counter(r['implicit']), nodes=r['nodes'],
                      think_mismatch=r['think_mismatch']))
    out = dict(mbs=m)
    if inst.U or inst.usync:
        out['update'] = dict(T=pack_T(inst.U), sync=pack_counter(inst.usync), implicit=pack_counter(inst.uimplicit))
    out['optimizer'] = optimizer_info(replica)
    out.update(extra or {})
    return out


def optimizer_info(replica):
    ps = [p for p in replica.model.parameters() if p.requires_grad]
    groups = [[p.numel() for p in g['params']] for g in replica.opt.param_groups]
    adam = sum(multi_tensor_launches(g, 4) for g in groups)
    gn = [p.numel() for p in ps]
    return dict(n_param_tensors=len(ps), n_params=sum(gn), groups=[len(g) for g in groups], fused_adamw_launches=adam, step_counter_launches=len(groups),
                clip_norm_launches=multi_tensor_launches(gn, 1) + 3, clip_mul_launches=multi_tensor_launches(gn, 1))


def sums(rows, **flt):
    """Sum count / low / high over packed rows [phase, region, rnd, op, kind, count, low, high, mem] that match the filters (a value, a set or a callable)."""
    keys = ('phase', 'region', 'rnd', 'op', 'kind')
    out = [0, 0, 0, 0]
    for r in rows:
        ok = True
        for k, f in flt.items():
            v = r[keys.index(k)]
            if callable(f):
                ok = f(v)
            elif isinstance(f, (set, tuple, list, frozenset)):
                ok = v in f
            else:
                ok = v == f
            if not ok:
                break
        if ok:
            for i in range(4):
                out[i] += r[5 + i]
    return out


# ---------------------------------------------------------------------------------------------------------------------------------- drivers
def make_args(tiny=False, batch=256, accum=4, rows=2000, seed=400, caps=None, pkg_root=None, synth_letters=None):
    load(pkg_root)
    if tiny:
        argv = ['--arm', 'B3G2', '--tiny', '--data', 'synthetic', '--rows', str(rows or 600), '--batch', str(batch), '--accum', str(accum), '--eg', 'stub', '--device', 'cpu',
                '--seed', str(seed), '--out', os.devnull]
    else:
        argv = ['--arm', 'B3G2', '--rung', '3M', '--accum', str(accum), '--batch', str(batch), '--data', 'synthetic', '--rows', str(rows), '--eg', 'stub', '--device', 'cpu',
                '--seed', str(seed), '--caps', caps or os.path.join(PK.root, 'custom_io', 'g8a', 'caps_b3g2.json'), '--out', os.devnull]
    if synth_letters:
        argv += ['--synth-letters', str(synth_letters)]
    a = prof.build_parser().parse_args(argv)
    a.accum = a.accum or 4
    return a


_WORLDS = {}


def get_world(tiny=False, batch=256, accum=4, rows=2000, seed=400, pkg_root=None, synth_letters=None):
    key = (tiny, batch, accum, rows, seed, synth_letters)
    if key not in _WORLDS:
        a = make_args(tiny, batch, accum, rows, seed, pkg_root=pkg_root, synth_letters=synth_letters)
        _WORLDS[key] = prof.World(a)
    return _WORLDS[key]


def run_update(world, accum=4, seed=None, warmup=1, autocast=False, ks=None, extra=None, n_updates=1):
    """warm-up update(s) plain, then n_updates instrumented updates (each with its own Instrument).  ks: pin KS to this tuple.  -> (list of packed runs, last inst, replica)"""
    rep = Replica(world, accum=accum, seed=seed, autocast=autocast)
    cm = pin_ks(ks) if ks else contextlib.nullcontext()
    outs = []
    with cm:
        for _ in range(warmup):
            rep.update(None)
        for i in range(n_updates):
            inst = Instrument(rep.model, autocast).install()
            try:
                r = rep.update(inst)
            finally:
                inst.uninstall()
            outs.append(pack_run(inst, rep, dict(update_result=r, kind='update', autocast=autocast, ks=ks, accum=accum, update_index=i, **(extra or {}))))
    return outs, inst, rep


def run_single(world, accum=4, k=16, seed=None, autocast=False, mb_index=0, extra=None, batch_skip=0):
    """One micro-batch (forward + backward) with K pinned to k; the model is rebuilt so every k sees the same plan() random stream and the same rows."""
    rep = Replica(world, accum=accum, seed=seed, autocast=autocast)
    for _ in range(batch_skip):
        rep.next_batch()
    inst = Instrument(rep.model, autocast).install()
    try:
        with pin_ks((k,)), inst.counter, inst.census:
            rep.single_mb(mb_index, inst=inst)
    finally:
        inst.uninstall()
    return pack_run(inst, rep, dict(kind='single', autocast=autocast, K=k, accum=accum, mb_index=mb_index, **(extra or {}))), inst, rep


def multi_call_rows(n, seed=0, share_calls=0.37, kmin=3, kmax=9, max_letters=280):
    """Synthetic rows closer to the real pool's call mix (GPU-RUN-1 padding section: 37 % of the real rows have calls and the longest program in a 64-row micro-batch is
    about 9 calls: mean n = 17.28 with K from (4, 8, 16, 32) needs n = max(K, last + 2) of about 10 for the small K): share_calls of the rows are a chain of kmin..kmax
    add / sub steps, the rest are the harness's cloze rows (no calls).  Content is meaningless; only the number of calls per row matters here."""
    import random
    rng = random.Random(seed)
    pool = [r for r in prof.synth_rows(n * 3, max_letters, seed=seed) if not r['steps']]
    rows, ci = [], 0
    for i in range(n):
        if rng.random() < share_calls:
            k = rng.randint(kmin, kmax)
            a = rng.randint(10, 99); cur, nums, steps = a, [], []
            for _ in range(k):
                b = rng.randint(2, 50); nums.append(b)
                if rng.random() < 0.5:
                    steps.append(f'{cur} + {b} = {cur + b}'); cur += b
                else:
                    steps.append(f'{cur} - {b} = {cur - b}'); cur -= b
            prompt = f'Start with {a}, then ' + ', then '.join(('add ' if True else '') + str(x) for x in nums) + '. What is the result?'
            rows.append(dict(id=f'm{i}', prompt=prompt, answer=str(cur), accepted=[str(cur)], family='chain_story2', level=1, stage=1, variant='v', steps=steps))
        else:
            r = dict(pool[ci]); ci += 1
            r['id'] = f'c{i}'
            rows.append(r)
    return rows


def with_rows(world, rows):
    """A copy of the harness world whose dataset is `rows` (same model factory, caps, vocab, shared Gemma stub)."""
    import copy
    w = copy.copy(world)
    w.rows = rows
    w.ds = PK.D.Dataset(rows, world.vocab)
    w.data_desc = f'multi_call_rows({len(rows)})'
    return w


def meta_of(world, args):
    m = world.meta()
    m = {k: m[k] for k in ('arm', 'rung', 'accum', 'batch', 'device', 'torch', 'model', 'n_params', 'caps_file', 'data', 'rows_loaded', 'eg', 'tiny', 'seed', 'pkg_root')}
    m['n_loops'] = getattr(world.new_model(world.a.seed), 'n_loops', None)
    m['cmd'] = sys.argv[1:]
    m['threads'] = torch.get_num_threads()
    m['started'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    return m


def cmd_natural(args):
    w = get_world(args.tiny, args.batch, args.accum, args.rows, args.seed, args.pkg_root, args.synth_letters)
    out = dict(meta=meta_of(w, args), runs=[])
    t = time.time()
    runs, inst, rep = run_update(w, args.accum, warmup=args.warmup, autocast=args.autocast, extra=dict(tag='natural'), n_updates=args.n_updates)
    for r in runs:
        r['wall_s_total'] = time.time() - t
        out['runs'].append(r)
        prof.log(f"natural update {r['update_index']}: rounds per micro-batch {r['update_result']['rounds']}")
    json.dump(out, open(args.out, 'w'))
    prof.log(f"natural done, {time.time() - t:.0f} s total")


def cmd_pinned(args):
    w = get_world(args.tiny, args.batch, args.accum, args.rows, args.seed, args.pkg_root, args.synth_letters)
    out = dict(meta=meta_of(w, args), runs=[])
    for k in [int(x) for x in args.ks.split(',')]:
        t = time.time()
        res, inst, rep = run_single(w, args.accum, k, autocast=args.autocast, extra=dict(tag=f'pinned K={k}'))
        res['wall_s'] = time.time() - t
        out['runs'].append(res)
        json.dump(out, open(args.out, 'w'))
        prof.log(f"K={k}: n={res['mbs'][0]['n']} rows={res['mbs'][0]['rows']} {res['wall_s']:.0f} s")


def cmd_rows(args):
    out = dict(meta=None, runs=[])
    for batch in [int(x) for x in args.batches.split(',')]:
        w = get_world(args.tiny, batch, args.accum, args.rows, args.seed, args.pkg_root, args.synth_letters)
        if out['meta'] is None:
            out['meta'] = meta_of(w, args)
        t = time.time()
        res, inst, rep = run_single(w, args.accum, args.k, autocast=args.autocast, extra=dict(tag=f'rows batch={batch} K={args.k}', batch=batch))
        res['wall_s'] = time.time() - t
        out['runs'].append(res)
        json.dump(out, open(args.out, 'w'))
        prof.log(f"batch {batch}: rows/mb {res['mbs'][0]['rows']} n={res['mbs'][0]['n']} {res['wall_s']:.0f} s")


def cmd_multi(args):
    w0 = get_world(args.tiny, args.batch, args.accum, args.rows, args.seed, args.pkg_root, args.synth_letters)
    w = with_rows(w0, multi_call_rows(args.rows, seed=args.seed, max_letters=args.synth_letters or 280))
    out = dict(meta=meta_of(w, args), runs=[])
    for k in [int(x) for x in args.ks.split(',')]:
        t = time.time()
        res, inst, rep = run_single(w, args.accum, k, autocast=args.autocast, extra=dict(tag=f'multi-call rows K={k}'))
        res['wall_s'] = time.time() - t
        out['runs'].append(res)
        json.dump(out, open(args.out, 'w'))
        prof.log(f"multi-call rows K={k}: n={res['mbs'][0]['n']} {res['wall_s']:.0f} s")




# ---------------------------------------------------------------------------------------------------------------------------------- the report
GPU_DIR = os.path.normpath(os.path.join(HERE, '..', 'gpu-run-3-box1'))
GPU = dict(kernels=75966, kernels_profile=75967, cuda_launch=70618, cu_launch=5318, kernel_ms=1415, stream_syncs=1305, dtoh=745, htod=561.5, rounds_per_mb=17.28, step_s=2.24,
           sync_debug_per_update=1319.5)
PTC_KERNELS_PER_UPDATE, PTC_ACCUM = 47878, 16                    # gpu-run-1/profrun/profile.profiler.md: PTC 3M accum 16, one Gemma call per micro-batch
GEMMA_CALLS_PER_MB = 63.4 / 32                                    # gpu-run-1/profrun/b3g2_profile.md, accum 32: eg.gemma_forward calls per update / micro-batches
ROW = dict(phase=0, region=1, rnd=2, op=3, kind=4, count=5, lo=6, hi=7, mem=8)


def load_gpu():
    """The GPU-RUN-3 box 1 profile (shown by that run): syncs by line, top CPU ops, kernels per update."""
    try:
        d = json.load(open(os.path.join(GPU_DIR, 'b3g2_profile.json')))
    except (OSError, ValueError):
        return None
    sites = {x['where']: x['per_update'] for x in d['sections']['syncs']['sites']}
    ops = {x['name']: x['calls'] / 2 for x in d['sections']['profiler']['top_cpu_ops']}           # 2 profiled updates
    return dict(sites=sites, ops=ops, rounds_per_update=sites.get('b3g2.py:551'), cuda=d['sections']['profiler']['cuda'])


def tally(rows, pred=None):
    out = dict(ops=0, kernel=0, view=0, nolaunch=0, lo=0, hi=0, mem=0)
    for r in rows:
        if pred is not None and not pred(r):
            continue
        out['ops'] += r[5]
        out[r[4]] += r[5]
        out['lo'] += r[6]; out['hi'] += r[7]; out['mem'] += r[8]
    return out


def base_name(op):
    return re.split(r'[.|@]', op)[0]


def is_stub(r):
    return '|gemma_stub' in r[3]


def dev(r):
    """a row that is a CUDA-side op in the real run: not the CPU-tensor teacher, not the stub Gemma."""
    return r[1] != 'teacher_host' and not is_stub(r)


def mb_rows(run, i=None):
    ms = run['mbs'] if i is None else [run['mbs'][i]]
    return [r for m in ms for r in m['T']]


def all_rows(run):
    return mb_rows(run) + run.get('update', {}).get('T', [])


def lstsq(xs, ys):
    """y = a + b x by least squares -> a, b, r2, max |residual| / y."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    a = my - b * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    return dict(a=a, b=b, r2=1 - ss_res / ss_tot if ss_tot else 1.0, max_rel_resid=max(abs(y - (a + b * x)) / y for x, y in zip(xs, ys) if y), n_points=n)


def per_t(rows):
    """{rnd: {'ops','kernel','lo','hi'}} over the device rows with a round (rnd None -> key None)."""
    out = {}
    for r in rows:
        if not dev(r):
            continue
        d = out.setdefault(r[2], dict(ops=0, kernel=0, view=0, nolaunch=0, lo=0, hi=0))
        d['ops'] += r[5]; d[r[4]] += r[5]; d['lo'] += r[6]; d['hi'] += r[7]
    return out


def region_phase_cells(rows, rnds=None, keep_none=False):
    """{(phase, region): [kernel ops, lo, hi, views]} over device rows with round in rnds (None = every round-tagged row; keep_none: only the rnd-None rows)."""
    out = {}
    for r in rows:
        if not dev(r):
            continue
        if keep_none:
            if r[2] is not None:
                continue
        else:
            if r[2] is None or (rnds is not None and r[2] not in rnds):
                continue
        c = out.setdefault((r[0], r[1]), [0, 0, 0, 0])
        if r[4] == 'kernel':
            c[0] += r[5]; c[1] += r[6]; c[2] += r[7]
        elif r[4] == 'view':
            c[3] += r[5]
    return out


def classes_of(n, n_loops=12, ckpt=8):
    """Round classes of a run with n rounds: t = 0, 1..ckpt-1, ckpt..n_loops-1, n_loops..n-2, last (n - 1)."""
    cl = [('t = 0', [0]), (f't = 1..{ckpt - 1}', list(range(1, ckpt))), (f't = {ckpt}..{n_loops - 1} (answer pass recomputed)', list(range(ckpt, n_loops))),
          (f't = {n_loops}..{n - 2} (thinker + answer recomputed)', list(range(n_loops, n - 1))), (f'last round (t = {n - 1})', [n - 1])]
    return [(name, ts) for name, ts in cl if ts]


def phase_table(run, opt):
    """Per-update totals by phase for one natural update (device ops; the stub Gemma is its own line, the CPU-tensor teacher is 'host')."""
    rows = all_rows(run)

    def row(name, pred, launches=None):
        t = tally(rows, pred)
        lo, hi = (t['lo'], t['hi']) if launches is None else (launches, launches)
        return dict(phase=name, ops=t['ops'], view=t['view'], nolaunch=t['nolaunch'], kernel=t['kernel'], lo=lo, hi=hi)
    P = lambda *ph: (lambda r: r[0] in ph and dev(r))
    tab = [row('forward', lambda r: r[0] == 'forward' and dev(r) and r[1] != 'train_loop'),
           row('backward (engine adds included)', P('backward')),
           row('recompute (checkpoint re-forward)', P('recompute')),
           row('host: teacher_host (CPU tensors)', lambda r: r[1] == 'teacher_host'),
           row('train loop (split, loss average)', lambda r: r[0] in ('prep', 'forward') and r[1] == 'train_loop' and dev(r)),
           row('clip_grad_norm_', lambda r: r[0] == 'clip', launches=opt['clip_norm_launches'] + opt['clip_mul_launches']),
           row('AdamW step (fused)', lambda r: r[0] == 'optimizer', launches=opt['fused_adamw_launches'] + opt['step_counter_launches']),
           row('stub Gemma front (not a real op set; excluded)', is_stub)]
    return tab


def fit_table(pinned):
    """The a + b n fits of the pinned single-micro-batch runs.  pinned: list of runs.  -> (rows of fit results, points)"""
    pts = []
    for run in pinned:
        m = run['mbs'][0]
        rows = m['T']
        d = dict(n=m['n'], K=m['K'])
        d['all_ops'] = tally(rows, dev)['ops']
        d['kernel_ops_device'] = tally(rows, dev)['kernel']
        d['kernel_ops_incl_host'] = tally(rows, lambda r: not is_stub(r))['kernel']
        t = tally(rows, dev)
        d['launches_lo'], d['launches_hi'] = t['lo'], t['hi']
        for reg in REGIONS:
            d['kernel_' + reg] = tally(rows, lambda r, reg=reg: r[1] == reg and not is_stub(r))['kernel']
        d['writer_kernel'] = d['kernel_call_writer'] + d['kernel_answer_writer']
        pts.append(d)
    pts.sort(key=lambda d: d['n'])
    cats = ['all_ops', 'kernel_ops_device', 'kernel_ops_incl_host', 'launches_lo', 'launches_hi', 'writer_kernel'] + ['kernel_' + r for r in REGIONS if any(p['kernel_' + r] for p in pts)]
    fits = {}
    for c in cats:
        xs, ys = [p['n'] for p in pts], [p[c] for p in pts]
        f = lstsq(xs, ys)
        hi = [(x, y) for x, y in zip(xs, ys) if x >= 12]
        f['b_n_ge_12'] = lstsq([x for x, _ in hi], [y for _, y in hi])['b'] if len(hi) >= 2 else None
        f['a_n_ge_12'] = lstsq([x for x, _ in hi], [y for _, y in hi])['a'] if len(hi) >= 2 else None
        fits[c] = f
    return fits, pts


def additivity(pinned):
    """Predict every pinned run from the reference run (largest n): fixed part + the reference's per-round totals (the last round of a run is the reference's last round).
    -> list of (n, measured, predicted, rel err) for the device kernel ops and the low launch estimate."""
    ref = max(pinned, key=lambda r: r['mbs'][0]['n'])
    rm = ref['mbs'][0]
    pt = per_t(rm['T'])
    nref = int(rm['n'])
    out = []
    for run in pinned:
        m = run['mbs'][0]
        n = int(m['n'])
        meas = per_t(m['T'])
        for key in ('kernel', 'lo'):
            tot = sum(v[key] for v in meas.values())
            pred = pt[None][key] + sum(pt[t][key] for t in range(n - 1)) + pt[nref - 1][key]
            out.append(dict(n=n, K=m['K'], metric=key, measured=tot, predicted=pred, rel_err=(pred - tot) / tot if tot else 0.0))
    return out, ref


def sync_table(runs, gpu):
    """Sync census of natural update runs: per site: count per update, per round, per micro-batch, kind, class, GPU per update."""
    agg = collections.defaultdict(lambda: dict(total=0, rounds=0, fixed=0, kinds=set(), regions=collections.Counter(), phases=collections.Counter()))
    n_up, tot_rounds, tot_mb = 0, 0.0, 0
    for run in runs:
        n_up += 1
        for m in run['mbs']:
            tot_rounds += m['n']; tot_mb += 1
            for kind, site, ph, rnd, reg, c in [(*x[:4], x[4], x[5]) if len(x) == 6 else (*x[:4], 'n/a', x[4]) for x in m['sync']]:
                a = agg[site]
                a['total'] += c; a['kinds'].add(kind); a['regions'][reg] += c; a['phases'][ph] += c
                a['rounds' if rnd is not None else 'fixed'] += c
            for kind, site, ph, rnd, c in m['implicit']:
                a = agg[site + ' [' + kind + ']']
                a['total'] += c; a['kinds'].add('implicit'); a['regions']['n/a'] += c; a['phases'][ph] += c
                a['rounds' if rnd is not None else 'fixed'] += c
        for x in run.get('update', {}).get('sync', []):
            kind, site, ph, rnd, reg, c = (*x[:4], x[4], x[5]) if len(x) == 6 else (*x[:4], 'n/a', x[4])
            a = agg[site]
            a['total'] += c; a['kinds'].add(kind); a['phases'][ph] += c; a['fixed'] += c
    rows = []
    for site, a in agg.items():
        base = site.split(' ')[0]
        cls, txt = site_class(site, a, gpu)
        rows.append(dict(site=site, kind='/'.join(sorted(a['kinds'])), per_update=a['total'] / n_up, per_round=a['rounds'] / tot_rounds if tot_rounds else 0.0,
                         per_mb=a['fixed'] / tot_mb if tot_mb else 0.0, cls=cls, note=txt,
                         gpu_per_update=(gpu or {}).get('sites', {}).get(base), phases=dict(a['phases'])))
    rows.sort(key=lambda r: (-r['per_update']))
    return rows, dict(updates=n_up, rounds=tot_rounds, mbs=tot_mb)


def site_class(site, a, gpu=None):
    """-> (class, note).  See SITE_NOTES; implicit index sites count as 'sync' only where the GPU record flags the line."""
    base = site.split(' ')[0]
    if base in SITE_NOTES:
        cls, kind, txt = SITE_NOTES[base]
        return cls, txt
    if '[' in site:                                   # an implicit index / index_put_ site not in SITE_NOTES
        flagged = base in ((gpu or {}).get('sites') or {})
        return ('sync' if flagged else 'no-sync'), ('flagged by the GPU record' if flagged else 'tensor-index call the GPU record does not flag (a gather / scatter, no wait)')
    if a['regions'].get('teacher_host', 0) >= 0.5 * a['total']:
        return 'host', 'inside ByteWriter.teacher: lists and CPU tensors in the real run'
    return 'unclassified', ''


def cross_check(fits_by_op, gpu, mb_rounds_per_update):
    """GPU profiler CPU-op call counts per update vs the CPU dispatch-level counts evaluated at the profiled updates' rounds."""
    rows = []
    for gname, ops in (('aten::mm', ['mm']), ('aten::addmm', ['addmm']), ('aten::native_layer_norm', ['native_layer_norm']), ('aten::add', ['add']), ('aten::add_', ['add_']),
                       ('aten::mul', ['mul']), ('aten::sum', ['sum']), ('aten::pow', ['pow']), ('aten::_to_copy', ['_to_copy']), ('aten::select', ['select']),
                       ('aten::view', ['view']), ('aten::transpose', ['transpose']), ('aten::slice', ['slice'])):
        g = (gpu or {}).get('ops', {}).get(gname)
        pred = sum(fits_by_op.get(o, 0.0) for o in ops)
        rows.append(dict(op=gname, gpu_per_update=g, cpu_pred_per_update=pred, ratio=(pred / g) if g else None))
    return rows


def op_fits(pinned, n_mb, accum=4):
    """Per base op name (all overloads, regions, phases; device rows): a + b n fit over the pinned runs, evaluated per update at n_mb rounds per micro-batch."""
    names = set()
    per_run = []
    for run in pinned:
        m = run['mbs'][0]
        c = collections.Counter()
        for r in m['T']:
            if dev(r):
                c[base_name(r[3])] += r[5]
        per_run.append((m['n'], c))
        names |= set(c)
    out = {}
    for nm in names:
        f = lstsq([n for n, _ in per_run], [c.get(nm, 0) for _, c in per_run])
        out[nm] = accum * (f['a'] + f['b'] * n_mb)
    return out


def gemma_bound():
    return dict(ptc_kernels_per_mb=PTC_KERNELS_PER_UPDATE / PTC_ACCUM, calls_per_mb=GEMMA_CALLS_PER_MB, upper_per_update_accum4=4 * GEMMA_CALLS_PER_MB * PTC_KERNELS_PER_UPDATE / PTC_ACCUM)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['natural', 'pinned', 'rows', 'multi', 'report'])
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--out')
    ap.add_argument('--tiny', action='store_true')
    ap.add_argument('--batch', type=int, default=256)
    ap.add_argument('--accum', type=int, default=4)
    ap.add_argument('--rows', type=int, default=2000)
    ap.add_argument('--seed', type=int, default=400)
    ap.add_argument('--synth-letters', type=int, default=None, help='longest synthetic prompt (default: the caps max_prompt, 2000: about 13 GB peak on CPU at batch 256 / accum 4; op counts do not depend on the width)')
    ap.add_argument('--warmup', type=int, default=1)
    ap.add_argument('--n-updates', type=int, default=1, help='natural: instrumented updates after the warm-up')
    ap.add_argument('--ks', default='4,8,12,16,24,32')
    ap.add_argument('--k', type=int, default=16)
    ap.add_argument('--batches', default='64,256')
    ap.add_argument('--autocast', action='store_true', help="torch.autocast('cpu', bfloat16) around the forward (counts CPU autocast's casts)")
    ap.add_argument('--threads', type=int, default=1)
    ap.add_argument('--pkg-root', default=DEFAULT_PKG)
    ap.add_argument('--md')
    ap.add_argument('--json')
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    if a.cmd == 'report':
        import attrib_report
        return attrib_report.main(a)
    load(a.pkg_root)
    {'natural': cmd_natural, 'pinned': cmd_pinned, 'rows': cmd_rows, 'multi': cmd_multi}[a.cmd](a)


if __name__ == '__main__':
    main()
