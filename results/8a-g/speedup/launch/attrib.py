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
  python attrib.py natural --n-updates 5 --out RUN.json          # real 3M shape, seed 400, one warm-up update then 5 instrumented updates (natural K draws)
  python attrib.py pinned --ks 4,8,12,16,24,32 --out RUN.json    # one micro-batch (forward + backward) per K, K pinned; for the fit  ops = a + b n
  python attrib.py rows --batches 64,256 --k 16 --out RUN.json   # batch 64 vs 256 at accum 4, K pinned: does the per-round count depend on the rows?
  python attrib.py multi --ks 16,32 --out RUN.json               # same on rows with 3 to 9 calls (the synthetic rows have 0 or 2)
  add --autocast for torch.autocast('cpu', bfloat16); --tiny for the d 48 smoke shape; --synth-letters N for the longest synthetic prompt (default: the caps' 2000, ~13 GB of RAM at
  batch 256 / accum 4; every op count is independent of the width, shown by the report's width check); --pkg-root for the folder that contains custom_io/ (default /home/user/src-g2f)
  python attrib.py report --natural N.json --pinned P.json --rows-json R.json [--autocast-json A.json --width W.json --multi M.json] --md OUT.md --json OUT.json
  python test_attrib.py                                           # 17 tests, about a minute
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
    # normalisation: forward is one kernel; backward = grad_input kernel + gamma/beta kernel
    'native_layer_norm': 1, 'native_layer_norm_backward': 2,           # grad_input + one gamma/beta kernel: the PTC profile shows one GammaBetaBackward per layer-norm forward (480 and 480)
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


NOSYNC_LINES = {'writer.py:138', 'writer.py:121', 'b3g2.py:350', 'b3g2.py:374'}       # removed by the harness's `nosync` variant (prof_train.NoSync doc); GPU-RUN-3: -0.1 % to +1.2 % speed


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
        self.run_loss = 0.0
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
            loss, ns, aux = 0.0, [], {}
            for mb in parts:
                l_i, a_i = self.micro(mb, len(parts), inst)
                loss = loss + l_i.detach() / len(parts)
                for k_, v_ in a_i.items():                               # train.py's aux averaging (a few tiny ops per micro-batch)
                    aux[k_] = aux.get(k_, 0.0) + v_.detach() / len(parts) if torch.is_tensor(v_) else aux.get(k_, 0.0) + v_ / len(parts)
                ns.append(a_i.get('rounds') if isinstance(a_i, dict) else None)
            if inst is not None:
                inst.phase = 'clip'
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            if inst is not None:
                inst.phase = 'optimizer'
            self.opt.step()
            self.opt.zero_grad(set_to_none=True)
            if inst is not None:
                inst.phase = 'forward'
            self.run_loss = self.run_loss + loss.detach()                  # train.py: run_loss += loss.detach(); run_n += 1
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
    # clip_grad_norm_ (foreach): _foreach_norm (multi-tensor launches + 1 cleanup), then stack, linalg_vector_norm, add, reciprocal, mul, clamp (6 single launches), then _foreach_mul_ (multi-tensor launches)
    return dict(n_param_tensors=len(ps), n_params=sum(gn), groups=[len(g) for g in groups], fused_adamw_launches=adam, step_counter_launches=len(groups),
                clip_norm_launches=multi_tensor_launches(gn, 1) + 1 + 6, clip_mul_launches=multi_tensor_launches(gn, 1))


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


def run_update(world, accum=4, seed=None, warmup=1, autocast=False, ks=None, extra=None, n_updates=1, on_each=None):
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
            if on_each is not None:
                on_each(outs[-1])                                  # a long run keeps what it has finished if the box kills it
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


def k_stream(world, n_updates=12, accum=4, seed=None):
    """The loop-length draws K = KS[torch.randint] of the first n_updates updates of a trainer seeded like the harness's (torch seed, model built, then one draw per micro-batch): [[K x accum] per update]."""
    seed = world.a.seed if seed is None else seed
    prof.seed_all(seed)
    world.new_model(seed)
    KS = PK.models.b3g2.KS
    return [[KS[int(torch.randint(len(KS), (1,)))] for _ in range(accum)] for _ in range(n_updates)]


def cmd_natural(args):
    w = get_world(args.tiny, args.batch, args.accum, args.rows, args.seed, args.pkg_root, args.synth_letters)
    out = dict(meta=meta_of(w, args), runs=[], k_stream=k_stream(w, 12, args.accum))
    t = time.time()

    def each(r):
        r['wall_s_total'] = time.time() - t
        out['runs'].append(r)
        json.dump(out, open(args.out, 'w'))
        prof.log(f"natural update {r['update_index']}: rounds per micro-batch {r['update_result']['rounds']}")
    run_update(w, args.accum, warmup=args.warmup, autocast=args.autocast, extra=dict(tag='natural'), n_updates=args.n_updates, on_each=each)
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
PROFILED_N = (32, 16, 16, 7, 16, 16, 16, 32)             # the micro-batch round counts of the GPU profile's two updates, inferred (see estimate_tables)
GPU_GEMMA_PER_MB_BOUND = GEMMA_CALLS_PER_MB * PTC_KERNELS_PER_UPDATE / PTC_ACCUM        # upper bound: Gemma launches per micro-batch
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


def sync_table(runs, gpu, gpu_rounds=75.5, gpu_mbs=4):
    """Sync census of natural update runs: per site: count per update, per round (rounds-tagged), per micro-batch (not round-tagged), the same scaled to the GPU profile's rounds and
    micro-batches, kind, class, and the GPU record's count.  Implicit index sites that are the two halves of one source line (index + index_put_) are one line: the larger count."""
    agg = collections.defaultdict(lambda: dict(total=0, rounds=0, fixed=0, kinds=set(), regions=collections.Counter(), phases=collections.Counter()))
    n_up, tot_rounds, tot_mb = 0, 0.0, 0
    for run in runs:
        n_up += 1
        for m in run['mbs']:
            tot_rounds += m['n']; tot_mb += 1
            for x in m['sync']:
                kind, site, ph, rnd = x[:4]
                reg, c = (x[4], x[5]) if len(x) == 6 else ('n/a', x[4])
                a = agg[site]
                a['total'] += c; a['kinds'].add(kind); a['regions'][reg] += c; a['phases'][ph] += c
                a['rounds' if rnd is not None else 'fixed'] += c
            for kind, site, ph, rnd, c in m['implicit']:
                a = agg[site + ' [' + kind + ']']
                a['total'] += c; a['kinds'].add('implicit'); a['regions']['n/a'] += c; a['phases'][ph] += c
                a['rounds' if rnd is not None else 'fixed'] += c
        for x in run.get('update', {}).get('sync', []):
            kind, site, ph, rnd = x[:4]
            reg, c = (x[4], x[5]) if len(x) == 6 else ('n/a', x[4])
            a = agg[site]
            a['total'] += c; a['kinds'].add(kind); a['phases'][ph] += c; a['fixed'] += c
    # merge the index / index_put halves of one line
    merged = {}
    for site, a in agg.items():
        key = site.split(' ')[0] if '[' in site else site
        if key in merged and '[' in site and '[' in merged[key][0]:
            if a['total'] > merged[key][1]['total']:
                merged[key] = (site, a)
        else:
            merged[key] = (site, a)
    rows = []
    for key, (site, a) in merged.items():
        base = site.split(' ')[0]
        cls, txt = site_class(site, a, gpu)
        per_round = a['rounds'] / tot_rounds if tot_rounds else 0.0
        per_mb = a['fixed'] / tot_mb if tot_mb else 0.0
        label = base + (' (index / index_put_)' if '[' in site else '')
        rows.append(dict(site=label, kind='/'.join(sorted(a['kinds'])), per_update=a['total'] / n_up, per_round=per_round, per_mb=per_mb, scaled=per_round * gpu_rounds + per_mb * gpu_mbs,
                         per_round_equiv=a['total'] / tot_rounds if tot_rounds else 0.0, cls=cls, note=txt, gpu_per_update=(gpu or {}).get('sites', {}).get(base), phases=dict(a['phases'])))
    seen = {r['site'].split(' ')[0] for r in rows}
    for base, g in ((gpu or {}).get('sites') or {}).items():
        if base not in seen:
            rows.append(dict(site=base, kind='?', per_update=0.0, per_round=0.0, per_mb=0.0, scaled=0.0, per_round_equiv=0.0, cls='gpu-only',
                             note='in the GPU record only: the real Gemma front (eg.py / transformers masking_utils); this CPU run has a stub there', gpu_per_update=g, phases={}))
    order = {'sync': 0, 'gpu-only': 1, 'stub': 2, 'noop': 3, 'host': 4, 'no-sync': 5, 'unclassified': 6}
    rows.sort(key=lambda r: (order.get(r['cls'], 9), -r['per_update'], -(r['gpu_per_update'] or 0)))
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
    """GPU profiler CPU-op call counts per update vs the CPU dispatch-level counts evaluated at the profiled updates' rounds.  Only ops that are one launch each are compared
    (mm, addmm, layer norm, add + add_, mul, sum, pow, _to_copy); view ops are not launches and the profiler counts them at every nesting level."""
    rows = []
    for gname, gops, cops in (('aten::mm', ['aten::mm'], ['mm']), ('aten::addmm', ['aten::addmm'], ['addmm']), ('aten::native_layer_norm', ['aten::native_layer_norm'], ['native_layer_norm']),
                              ('aten::add + aten::add_', ['aten::add', 'aten::add_'], ['add', 'add_']), ('aten::mul', ['aten::mul'], ['mul']), ('aten::sum', ['aten::sum'], ['sum']),
                              ('aten::pow', ['aten::pow'], ['pow']), ('aten::_to_copy', ['aten::_to_copy'], ['_to_copy'])):
        g = sum((gpu or {}).get('ops', {}).get(n, 0.0) for n in gops) or None
        pred = sum(fits_by_op.get(o, 0.0) for o in cops)
        rows.append(dict(op=gname, gpu_per_update=g, cpu_pred_per_update=pred, ratio=(pred / g) if g else None, gpu_minus_cpu=(g - pred) if g else None))
    return rows


FILL_OPS = ('zeros', 'new_zeros', 'zeros_like', 'ones', 'ones_like', 'full', 'full_like', 'fill_', 'fill', 'new_ones', 'new_full')


def groups_of(r):
    """Names an op row is counted under in the cross-checks: its base name, plus 'fill-type' for the zero / one fills and 'index_put_acc' for the sort-based accumulating scatter."""
    b = base_name(r[3])
    g = [b]
    if b in FILL_OPS:
        g.append('fill-type')
    if b in ('index_put_', 'index_put') and '|acc' in r[3]:
        g.append('index_put_acc')
    if b.startswith('_scaled_dot_product') and not b.endswith('backward'):
        g.append('sdpa_fwd')
    return g


def op_fits(pinned, n_mb, accum=4):
    """Per op group (see groups_of; all overloads, regions, phases; device rows): a + b n fit over the pinned runs, evaluated per update at n_mb rounds per micro-batch."""
    names = set()
    per_run = []
    for run in pinned:
        m = run['mbs'][0]
        c = collections.Counter()
        for r in m['T']:
            if dev(r):
                for g in groups_of(r):
                    c[g] += r[5]
        per_run.append((m['n'], c))
        names |= set(c)
    out = {}
    for nm in names:
        f = lstsq([n for n, _ in per_run], [c.get(nm, 0) for _, c in per_run])
        out[nm] = accum * (f['a'] + f['b'] * n_mb)
    return out


def kernel_name_checks(fo, gpu):
    """GPU profile kernels (top 25 by time, counts over 2 profiled updates) against the CPU op counts that should launch them one for one, at the same rounds."""
    if not gpu:
        return []
    ks = (gpu.get('cuda') or {}).get('top_kernels') or []
    def cnt(sub):
        return sum(k['count'] for k in ks if sub in k['name']) / 2.0
    rows = []
    for label, sub, key in (('layer-norm forward kernel', 'vectorized_layer_norm_kernel', 'native_layer_norm'), ('memory-efficient attention forward (two tile variants listed)', 'fmha_cutlassF', 'sdpa_fwd'),
                            ('torch.cat kernel', 'CatArrayBatchedCopy', 'cat'), ('bf16 fill kernel (zeros / ones / new_zeros)', 'FillFunctor<c10::BFloat16>', 'fill-type'),
                            ('indexing_backward_kernel (sort-based index_put_ accumulate)', 'indexing_backward_kernel', 'index_put_acc')):
        g = cnt(sub)
        if g:
            rows.append(dict(kernel=label, gpu_kernel=sub, gpu_per_update=g, cpu_op=key, cpu_per_update=fo.get(key, 0.0), ratio=fo.get(key, 0.0) / g))
    return rows


def gemma_bound():
    return dict(ptc_kernels_per_mb=PTC_KERNELS_PER_UPDATE / PTC_ACCUM, calls_per_mb=GEMMA_CALLS_PER_MB, upper_per_update_accum4=4 * GEMMA_CALLS_PER_MB * PTC_KERNELS_PER_UPDATE / PTC_ACCUM)


def md_table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '|'.join('---' for _ in head) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    return '\n'.join(out)


def f0(x):
    return f'{x:,.0f}'


def f1(x, nd=1):
    return f'{x:,.{nd}f}'


def pct(x, nd=1):
    return f'{100 * x:.{nd}f} %'


def rng_(lo, hi):
    return f0(lo) if round(lo) == round(hi) else f'{f0(lo)} to {f0(hi)}'


def update_launches(run, opt, which='lo'):
    """Estimated CUDA launches of one natural update: device rows of the micro-batches and the train loop, clip + optimizer from the multi-tensor model (stub Gemma and CPU-tensor teacher excluded)."""
    rows = all_rows(run)
    k = 6 if which == 'lo' else 7
    base = sum(r[k] for r in rows if dev(r) and r[0] not in ('clip', 'optimizer'))
    return base + opt['clip_norm_launches'] + opt['clip_mul_launches'] + opt['fused_adamw_launches'] + opt['step_counter_launches']


def predict_cum(pt, n, key):
    """fixed + sum of per-round totals for a (possibly fractional) number of rounds n, from the reference per-round table pt (round n - 1 is the reference's last round)."""
    nref = max(t for t in pt if t is not None) + 1

    def cum(m):
        m = int(m)
        return pt[None][key] + sum(pt[min(t, nref - 2)][key] for t in range(m - 1)) + pt[nref - 1][key]       # beyond the reference's length: its steady round
    lo = math.floor(n)
    return cum(lo) + (n - lo) * (cum(lo + 1) - cum(lo)) if n != lo else cum(lo)


def build_report(inp, gpu):
    res = dict(inputs={k: len(v) for k, v in inp.items() if isinstance(v, list)})
    nat, pin = inp.get('natural') or [], inp.get('pinned') or []
    res['meta'] = inp.get('meta')
    res['k_stream'] = inp.get('k_stream')
    # ---- the pinned reference run: per-round table, fixed part, fit, additivity
    ref = max(pin, key=lambda r: r['mbs'][0]['n'])
    rm = ref['mbs'][0]
    nref = int(rm['n'])
    n_loops = (inp.get('meta') or {}).get('n_loops') or 12
    pt = per_t(rm['T'])
    res['reference'] = dict(n=nref, K=rm['K'], rows=rm['rows'], n_loops=n_loops, ckpt_from=8)
    cls = []
    for name, ts in classes_of(nref, n_loops, 8):
        cells = region_phase_cells(rm['T'], rnds=set(ts))
        per = {f'{p}|{r}': [v[0] / len(ts), v[1] / len(ts), v[2] / len(ts), v[3] / len(ts)] for (p, r), v in cells.items()}
        tot = {k: sum(pt[t][k] for t in ts) / len(ts) for k in ('ops', 'kernel', 'view', 'lo', 'hi')}
        cls.append(dict(name=name, ts=[ts[0], ts[-1]], per_round=tot, cells=per))
    res['classes'] = cls
    fixed_cells = region_phase_cells(rm['T'], keep_none=True)
    res['fixed'] = dict(totals=pt[None], cells={f'{p}|{r}': v for (p, r), v in fixed_cells.items()})
    fits, pts = fit_table(pin)
    res['fits'], res['fit_points'] = fits, pts
    add, _ = additivity(pin)
    res['additivity'] = add
    res['per_t'] = {str(t): v for t, v in pt.items()}
    # engine adds by producer region (needs runs recorded after the '@producer' suffix existed)
    prod = collections.Counter()
    for r in rm['T']:
        if r[1] == 'grad_accumulate' and r[4] == 'kernel' and '@' in r[3] and r[2] is not None and 4 <= r[2] <= nref - 3:
            prod[r[3].split('@')[1]] += r[5]
    res['engine_by_producer_per_round'] = {k: v / (nref - 6) for k, v in prod.items()}
    ops_engine = collections.Counter()
    for r in rm['T']:
        if r[1] == 'grad_accumulate' and r[4] == 'kernel' and r[2] is not None and 4 <= r[2] <= nref - 3:
            ops_engine[base_name(r[3])] += r[5]
    res['engine_ops_per_round'] = {k: v / (nref - 6) for k, v in ops_engine.most_common(8)}
    # ---- which ops fill a steady round
    ts = [t for t in range(n_loops, nref - 1)] or [t for t in range(1, nref - 1)]
    byop = collections.defaultdict(lambda: [0.0, collections.Counter()])
    totk = 0.0
    for r in rm['T']:
        if r[2] in set(ts) and dev(r) and r[4] == 'kernel':
            b = base_name(r[3])
            byop[b][0] += r[5] / len(ts)
            byop[b][1][f'{r[1]}/{r[0]}'] += r[5] / len(ts)
            totk += r[5] / len(ts)
    res['top_ops'] = dict(rounds=[ts[0], ts[-1]], total=totk, ops=[dict(op=k, per_round=v[0], share=v[0] / totk, where=[(w, c) for w, c in v[1].most_common(3)]) for k, v in sorted(byop.items(), key=lambda kv: -kv[1][0])[:16]])
    # ---- C2
    c2 = []
    for c in cls:
        rows_c = [r for r in rm['T'] if r[2] is not None and c['ts'][0] <= r[2] <= c['ts'][1] and dev(r)]
        entry = dict(name=c['name'])
        for label, pred in (('kernel', None), ('lo', None), ('hi', None)):
            k = {'kernel': 5, 'lo': 6, 'hi': 7}[label]
            tot = sum(r[k] for r in rows_c if r[4] == 'kernel')
            wr = sum(r[k] for r in rows_c if r[4] == 'kernel' and r[1] in WRITER_REGIONS)
            eng_w = sum(r[k] for r in rows_c if r[4] == 'kernel' and r[1] == 'grad_accumulate' and r[3].endswith(('@call_writer', '@answer_writer')))
            eng = sum(r[k] for r in rows_c if r[4] == 'kernel' and r[1] == 'grad_accumulate')
            entry[label] = dict(total=tot, writer=wr, share=wr / tot if tot else None, engine=eng, share_folded=(wr + eng_w) / tot if tot and any('@' in r[3] for r in rows_c) else None,
                                share_no_engine=wr / (tot - eng) if tot - eng else None)
        wph = {}
        for ph in ('forward', 'backward', 'recompute'):
            t_ph = sum(r[5] for r in rows_c if r[4] == 'kernel' and r[0] == ph)
            w_ph = sum(r[5] for r in rows_c if r[4] == 'kernel' and r[0] == ph and r[1] in WRITER_REGIONS)
            wph[ph] = dict(total=t_ph, writer=w_ph, share=w_ph / t_ph if t_ph else None)
        entry['by_phase'] = wph
        incl_host = sum(r[5] for r in rm['T'] if r[2] is not None and c['ts'][0] <= r[2] <= c['ts'][1] and r[4] == 'kernel' and not is_stub(r))
        entry['share_incl_cpu_teacher_ops'] = (sum(r[5] for r in rm['T'] if r[2] is not None and c['ts'][0] <= r[2] <= c['ts'][1] and r[4] == 'kernel' and r[1] in WRITER_REGIONS + ('teacher_host',) and not is_stub(r)) / incl_host) if incl_host else None
        c2.append(entry)
    res['c2'] = c2
    # ---- natural updates
    nat_out = []
    opt = nat[0]['optimizer'] if nat else None
    for run in nat:
        ns = [m['n'] for m in run['mbs']]
        rows = all_rows(run)
        dev_kernel = sum(r[5] for r in rows if dev(r) and r[4] == 'kernel' and r[0] not in ('clip', 'optimizer'))
        pred = sum(predict_cum(pt, n, 'kernel') for n in ns) + sum(r[5] for r in run.get('update', {}).get('T', []) if dev(r) and r[4] == 'kernel' and r[0] not in ('clip', 'optimizer'))
        host = sum(r[5] for r in rows if r[1] == 'teacher_host' and r[4] == 'kernel')
        wr = sum(r[5] for r in rows if r[1] in WRITER_REGIONS and r[4] == 'kernel' and dev(r))
        nat_out.append(dict(update=run.get('update_index'), rounds_per_mb=ns, K_per_mb=[m['K'] for m in run['mbs']], rounds=sum(ns), phase_table=phase_table(run, run['optimizer']),
                            kernel_ops_device=dev_kernel, predicted_from_per_round=pred, pred_err=(pred - dev_kernel) / dev_kernel if dev_kernel else None, host_ops=host,
                            launches_lo=update_launches(run, run['optimizer'], 'lo'), launches_hi=update_launches(run, run['optimizer'], 'hi'), writer_share_update=wr / dev_kernel if dev_kernel else None,
                            nodes={k: sum(m['nodes'].get(k, 0) for m in run['mbs']) for k in ('tagged', 'reachable', 'untagged')},
                            think_check={k: sum(m['think_mismatch'].get(k, 0) for m in run['mbs']) for k in ('equal', 'differ')}))
    res['natural'] = nat_out
    # ---- C3
    rr = inp.get('rows') or []
    if len(rr) >= 2:
        def per_round_ops(run, ts):
            c = collections.Counter()
            m = run['mbs'][0]
            for r in m['T']:
                if r[2] in ts:
                    c[(r[0], r[1], r[3], r[4])] += r[5]
            return {k: v / len(ts) for k, v in c.items()}, m
        a_run, b_run = sorted(rr, key=lambda r: r['mbs'][0]['rows'])[:2]
        nn = int(min(a_run['mbs'][0]['n'], b_run['mbs'][0]['n']))
        ts = set(range(3, nn - 1))
        a, ma = per_round_ops(a_run, ts)
        b, mb = per_round_ops(b_run, ts)
        keys = set(a) | set(b)
        diff = sorted(((k, a.get(k, 0), b.get(k, 0)) for k in keys if abs(a.get(k, 0) - b.get(k, 0)) > 1e-9), key=lambda t: -abs(t[1] - t[2]))
        dk = lambda d: sum(v for k, v in d.items() if k[3] == 'kernel' and k[1] != 'teacher_host' and '|gemma_stub' not in k[2])
        hk = lambda d: sum(v for k, v in d.items() if k[3] == 'kernel' and k[1] == 'teacher_host')
        dev_diff = [d for d in diff if d[0][1] != 'teacher_host']
        res['c3'] = dict(rows=(ma['rows'], mb['rows']), n=(ma['n'], mb['n']), rounds_compared=sorted(ts), device_kernel_ops_per_round=(dk(a), dk(b)), host_cpu_ops_per_round=(hk(a), hk(b)),
                         n_op_keys=len(keys), n_differ=len(diff), n_differ_device=len(dev_diff), device_diffs=[(list(k), x, y) for k, x, y in dev_diff[:15]],
                         host_diffs_top=[(list(k), x, y) for k, x, y in diff if k[1] == 'teacher_host'][:8],
                         fixed_device_kernel=(tally(ma['T'], lambda r: dev(r) and r[2] is None)['kernel'], tally(mb['T'], lambda r: dev(r) and r[2] is None)['kernel']),
                         fixed_host=(tally(ma['T'], lambda r: r[1] == 'teacher_host' and r[2] is None)['kernel'], tally(mb['T'], lambda r: r[1] == 'teacher_host' and r[2] is None)['kernel']))
    # ---- width check (op counts do not depend on the padded width)
    wr_ = inp.get('width') or []
    if wr_ and len(rr) >= 2:
        ref_b64 = sorted(rr, key=lambda r: r['mbs'][0]['rows'])[0]
        wm = wr_[0]['mbs'][0]
        m0 = ref_b64['mbs'][0]
        ts = set(range(3, int(min(wm['n'], m0['n'])) - 1))
        def pr(m):
            c = collections.Counter()
            for r in m['T']:
                if r[2] in ts and r[1] != 'teacher_host':
                    c[(r[0], r[1], r[3], r[4])] += r[5]
            return {k: v / len(ts) for k, v in c.items()}
        x, y = pr(m0), pr(wm)
        res['width'] = dict(n=(m0['n'], wm['n']), rows=(m0['rows'], wm['rows']), device_ops_300=sum(v for k, v in x.items() if k[3] == 'kernel'), device_ops_2000=sum(v for k, v in y.items() if k[3] == 'kernel'),
                            n_differ=sum(1 for k in set(x) | set(y) if abs(x.get(k, 0) - y.get(k, 0)) > 1e-9),
                            fixed=(tally(m0['T'], lambda r: dev(r) and r[2] is None)['kernel'], tally(wm['T'], lambda r: dev(r) and r[2] is None)['kernel']))
    # ---- C4: syncs
    if nat:
        st, tot = sync_table(nat, gpu, (gpu or {}).get('rounds_per_update') or 75.5)
        res['sync'] = dict(rows=st, totals=tot)
        sync_rows = [r for r in st if r['cls'] == 'sync']
        by_kind = collections.defaultdict(float)
        for r in sync_rows:
            by_kind[r['kind'].split('/')[0] if r['kind'] in ('D2H', 'H2D', 'implicit') else r['kind']] += r['per_round_equiv']
        res['sync']['per_round_equiv_sync_lines'] = sum(r['per_round_equiv'] for r in sync_rows)
        res['sync']['per_round_by_kind'] = dict(by_kind)
        res['sync']['scaled_total_sync_lines'] = sum(r['scaled'] for r in sync_rows)
        res['sync']['gpu_same_lines'] = sum(r['gpu_per_update'] or 0 for r in sync_rows)
        res['sync']['gpu_only_lines'] = sum(r['gpu_per_update'] or 0 for r in st if r['cls'] == 'gpu-only')
        res['sync']['n_sync_lines'] = len(sync_rows)
    # ---- kernel estimate
    est = {}
    if nat:
        opt = nat[0]['optimizer']
        loops = [sum(r[6] for r in run.get('update', {}).get('T', []) if dev(r) and r[0] in ('prep', 'forward')) for run in nat]
        loop_launches = sum(loops) / len(loops) if loops else 8
        upd_extra = opt['clip_norm_launches'] + opt['clip_mul_launches'] + opt['fused_adamw_launches'] + opt['step_counter_launches'] + loop_launches
        est['update_parts_launches'] = dict(clip=opt['clip_norm_launches'] + opt['clip_mul_launches'], adamw=opt['fused_adamw_launches'] + opt['step_counter_launches'], loss_average=loop_launches, optimizer_info=opt)
        gr = (gpu or {}).get('rounds_per_update') or 75.5
        measured = collections.defaultdict(list)                     # exact micro-batch totals of the pinned runs, by n
        for run in pin:
            m = run['mbs'][0]
            t = tally(m['T'], dev)
            measured[int(m['n'])].append(dict(kernel=t['kernel'], lo=t['lo'], hi=t['hi']))

        def mb_cost(n, key):
            if float(n).is_integer() and int(n) in measured:
                return sum(x[key] for x in measured[int(n)]) / len(measured[int(n)])
            return predict_cum(pt, n, key)
        cases = {}
        for name, per_mb_ns in (('population mean (17.28 rounds per micro-batch, assumed mix n = 10.56, 10.56, 16, 32)', [10.56, 10.56, 16.0, 32.0]),
                                (f'the two profiled updates ({gr:g} rounds per update): n = 32, 16, 16, 7 and 16, 16, 16, 32 (inferred, see the text)', None),
                                ('4 micro-batches of 17.28 rounds (linear fit)', [17.28] * 4)):
            row = {}
            for key in ('lo', 'hi', 'kernel'):
                if per_mb_ns is None:
                    piece = sum(mb_cost(n, key) for n in PROFILED_N) / 2.0
                    lin = sum(fits['launches_' + key]['a'] + fits['launches_' + key]['b'] * n for n in PROFILED_N) / 2.0 if key != 'kernel' else sum(fits['kernel_ops_device']['a'] + fits['kernel_ops_device']['b'] * n for n in PROFILED_N) / 2.0
                else:
                    piece = sum(predict_cum(pt, n, key) for n in per_mb_ns)
                    lin = sum(fits['launches_' + key]['a'] + fits['launches_' + key]['b'] * n for n in per_mb_ns) if key != 'kernel' else sum(fits['kernel_ops_device']['a'] + fits['kernel_ops_device']['b'] * n for n in per_mb_ns)
                row[key] = dict(piecewise=piece + (upd_extra if key != 'kernel' else 0), linear=lin + (upd_extra if key != 'kernel' else 0))
            row['rounds'] = sum(PROFILED_N) / 2.0 if per_mb_ns is None else sum(per_mb_ns)
            cases[name] = row
        est['cases'] = cases
        est['gpu'] = dict(GPU)
        gm = gemma_bound()
        est['gemma_bound'] = gm
    ac = inp.get('autocast') or []
    if ac:
        k16 = [r for r in pin if r['mbs'][0]['K'] == ac[0]['mbs'][0]['K']]
        if k16:
            a_, b_ = ac[0]['mbs'][0], k16[0]['mbs'][0]
            n = a_['n']
            ta, tb = tally(a_['T'], dev), tally(b_['T'], dev)
            casts = collections.Counter()
            for r in a_['T']:
                if dev(r) and r[4] == 'kernel' and '_to_copy' in r[3] and '|cast' in r[3]:
                    casts[(r[0], r[1])] += r[5]
            ct = collections.Counter()
            for r in b_['T']:
                if dev(r) and r[4] == 'kernel' and '_to_copy' in r[3] and '|cast' in r[3]:
                    ct[(r[0], r[1])] += r[5]
            est['autocast'] = dict(K=a_['K'], n=n, kernel_ops=(tb['kernel'], ta['kernel']), launches_lo=(tb['lo'], ta['lo']), launches_hi=(tb['hi'], ta['hi']),
                                   cast_ops_autocast={f'{k[0]}|{k[1]}': v for k, v in casts.items()}, cast_ops_plain={f'{k[0]}|{k[1]}': v for k, v in ct.items()},
                                   casts_per_mb=sum(casts.values()), casts_per_round=sum(casts.values()) / n,
                                   gpu_to_copy_per_update=(gpu or {}).get('ops', {}).get('aten::_to_copy'), gpu_to_copy_per_round=((gpu or {}).get('ops', {}).get('aten::_to_copy') or 0) / ((gpu or {}).get('rounds_per_update') or 75.5))
    res['estimate'] = est
    # ---- op-level cross-check with the GPU profile's CPU-op call counts
    if gpu and pin:
        gr = gpu.get('rounds_per_update') or 75.5
        fo = op_fits(pin, gr / 4.0)
        # the engine and update-level ops are not in the single-mb fits; add the update-level rows
        upd = collections.Counter()
        for run in nat[:1]:
            for r in run.get('update', {}).get('T', []):
                if dev(r) or r[0] in ('clip', 'optimizer'):
                    upd[base_name(r[3])] += r[5]
        for k, v in upd.items():
            fo[k] = fo.get(k, 0) + v
        res['cross_check'] = cross_check(fo, gpu, gr)
        res['cross_check_rounds'] = gr
        res['kernel_name_checks'] = kernel_name_checks(fo, gpu)
    # ---- multi-call rows (compared with the harness rows at the same K over the same rounds)
    mr = inp.get('multi') or []
    if mr:
        pk = {r['mbs'][0]['K']: r for r in pin}
        mm, rr_ = [], []
        for run in mr:
            m = run['mbs'][0]
            if m['K'] not in pk:
                continue
            m0 = pk[m['K']]['mbs'][0]
            n, n0 = int(m['n']), int(m0['n'])
            ts = set(range(3, min(n, n0) - 1))

            def stat(mb):
                rows_t = [r for r in mb['T'] if r[2] in ts and dev(r) and r[4] == 'kernel']
                tot = sum(r[5] for r in rows_t) / len(ts)
                wr = sum(r[5] for r in rows_t if r[1] in WRITER_REGIONS) / len(ts)
                return dict(n=int(mb['n']), K=mb['K'], per_round_kernel_ops=tot, writer_per_round=wr, share=wr / tot if tot else None,
                            host_ops_per_round=sum(r[5] for r in mb['T'] if r[2] in ts and r[1] == 'teacher_host' and r[4] == 'kernel') / len(ts),
                            early_rounds=[tally([r for r in mb['T'] if r[2] == t and dev(r)])['kernel'] for t in range(min(int(mb['n']), 12))])
            e, r = stat(m), stat(m0)
            e['rounds_compared'] = [min(ts), max(ts)]
            mm.append(e); rr_.append(r)
        res['multi'], res['multi_ref'] = mm, rr_
    # ---- validation numbers
    allk = [r for run in nat + pin for r in all_rows(run) if r[4] == 'kernel']
    tot = sum(r[5] for r in allk)
    oth = sum(r[5] for r in allk if r[1] == 'other')
    bw = [r for run in nat + pin for r in all_rows(run) if r[4] == 'kernel' and r[0] in ('backward', 'recompute') and r[1] != 'grad_accumulate']
    bwt = sum(r[5] for r in bw)
    bwo = sum(r[5] for r in bw if r[1] == 'other')
    eng = sum(r[5] for run in nat + pin for r in all_rows(run) if r[4] == 'kernel' and r[1] == 'grad_accumulate')
    bwall = sum(r[5] for run in nat + pin for r in all_rows(run) if r[4] == 'kernel' and r[0] in ('backward', 'recompute'))
    srcs = collections.Counter()
    for run in pin + nat:
        for r in all_rows(run):
            if r[1] == 'grad_accumulate' and r[4] == 'kernel' and '@' in r[3]:
                srcs[r[3].split('@')[1]] += r[5]
    res['engine_sources'] = dict(srcs)
    chk = inp.get('natural_check') or []
    if chk and nat:
        def strip(rows):
            d = collections.Counter()
            for r in rows:
                d[(r[0], r[1], r[2], r[3].split('@')[0], r[4])] += r[5]
            return d
        pairs = [(a_, b_) for a_, b_ in zip(nat, chk) if [m['n'] for m in a_['mbs']] == [m['n'] for m in b_['mbs']]]
        same = 0
        tot_ops = 0
        for a_, b_ in pairs:
            ok_ = all(strip(x['T']) == strip(y['T']) for x, y in zip(a_['mbs'], b_['mbs']))
            same += ok_
            tot_ops += sum(r[5] for x in a_['mbs'] for r in x['T'])
        res['determinism_real_shape'] = dict(updates_compared=len(pairs), identical=same, ops_compared=tot_ops)
    res['validation'] = dict(kernel_ops_total=tot, kernel_ops_other=oth, share_not_other=1 - oth / tot if tot else None, backward_kernel_ops_excl_engine=bwt, backward_other=bwo,
                             share_backward_forward_region=1 - bwo / bwt if bwt else None, engine_share_of_backward=eng / bwall if bwall else None,
                             untagged_nodes=sum(m['nodes'].get('untagged', 0) for run in nat + pin for m in run['mbs']), reachable_nodes=sum(m['nodes'].get('reachable', 0) for run in nat + pin for m in run['mbs']),
                             think_round_check={k: sum(m['think_mismatch'].get(k, 0) for run in nat + pin for m in run['mbs']) for k in ('equal', 'differ')})
    return res


def verdicts(res):
    """The four claims, decided by rules fixed here: -> {claim: (label, one-line numbers)}."""
    out = {}
    f = res['fits']['kernel_ops_device']
    fl = res['fits']['launches_lo']
    nbar = GPU['rounds_per_mb']
    a_share = abs(f['a']) / (f['a'] + f['b'] * nbar) if (f['a'] + f['b'] * nbar) else None
    fixed = res['fixed']['totals']
    fixed_share = fixed['kernel'] / (fixed['kernel'] + f['b'] * nbar)
    ok = f['r2'] > 0.99 and f['max_rel_resid'] < 0.05 and fixed_share < 0.10
    cl = res['classes']
    steady = [c['per_round']['kernel'] for c in cl if c['name'].startswith('t = 1') or 'recomputed' in c['name']]
    gm = GPU_GEMMA_PER_MB_BOUND
    out['C1'] = ('shown for the model side (a line to within ' + pct(f['max_rel_resid']) + '); the Gemma front\'s fixed part is untested' if ok else 'unclear',
                 f"device kernel ops per micro-batch: a straight line {f['a']:.0f} + {f['b']:.0f} n (R2 {f['r2']:.4f}, worst point {pct(f['max_rel_resid'])} off) over n = {int(res['fit_points'][0]['n'])}..{int(res['fit_points'][-1]['n'])}. "
                 f"The honest form is fixed part + sum of per-round costs: the model-side fixed part is {fixed['kernel']} ops ({pct(fixed_share)} of a 17.28-round micro-batch, small), and a round costs "
                 f"{', '.join(f'{x:.0f}' for x in steady)} ops in the successive round classes (t 1..7, 8..11, 12 and later): it steps up when the answer pass, then the thinker, start being recomputed, which is why the line's intercept is negative. "
                 f"The real run also calls the Gemma front about twice per micro-batch whatever n is (stub here, so uncounted); the PTC profile bounds that at {gm:,.0f} launches per micro-batch, so \"small fixed part\" is untested for the whole micro-batch")
    # C2
    sh = [c['kernel']['share'] for c in res['c2']]
    steady_c2 = [c for c in res['c2'] if not c['name'].startswith('t = 0') and not c['name'].startswith('last')]
    lo_sh = min(c['kernel']['share'] for c in steady_c2)
    hi_sh = max(c['kernel']['share'] for c in steady_c2)
    folded = [c['kernel']['share_folded'] for c in steady_c2 if c['kernel'].get('share_folded') is not None]
    lab2 = 'shown' if lo_sh >= 0.5 else ('killed' if hi_sh < 0.5 and not (folded and min(folded) >= 0.5) else 'unclear')
    if lo_sh < 0.5 <= hi_sh or (folded and min(folded) >= 0.5 > lo_sh):
        lab2 = f"unclear: {pct(lo_sh, 0)} to {pct(hi_sh, 0)} by region" + (f", {pct(min(folded), 0)} to {pct(max(folded), 0)} with the writers' share of gradient accumulation" if folded else '')
    out['C2'] = (lab2, f"writer passes (call + answer, forward + backward + recompute) are {pct(lo_sh)} to {pct(hi_sh)} of the per-round device kernel ops of the steady rounds"
                       + (f"; {pct(min(folded))} to {pct(max(folded))} when the engine's gradient additions are attributed to the region that produced the gradient" if folded else ''))
    c3 = res.get('c3')
    if c3:
        a, b = c3['device_kernel_ops_per_round']
        ok3 = abs(a - b) / max(a, b) < 0.01
        out['C3'] = ('shown' if ok3 else 'killed', f"device kernel ops per steady round: {a:.2f} at {c3['rows'][0]} rows, {b:.2f} at {c3['rows'][1]} rows ({pct(abs(a - b) / max(a, b), 3)} apart); "
                                                  f"{c3['n_differ_device']} of {c3['n_op_keys']} (phase, region, op) cells differ on the device side; the CPU-tensor teacher does depend on the rows: {c3['host_cpu_ops_per_round'][0]:.0f} vs {c3['host_cpu_ops_per_round'][1]:.0f} CPU ops per round")
    sy = res.get('sync')
    if sy:
        per = sy['per_round_equiv_sync_lines']
        gpu_per = GPU['stream_syncs'] / (4 * GPU['rounds_per_mb'])
        out['C4'] = (f'shown: {per:.0f} per round at the profiled updates\' 75.5 rounds, from named lines (the 19 divides by 69.1 rounds)' if 15 <= per <= 21 else 'unclear',
                     f"{per:.1f} blocking host-device calls per round at {sy['n_sync_lines']} named lines ({sy['per_round_by_kind'].get('D2H', 0):.1f} device-to-host, {sy['per_round_by_kind'].get('H2D', 0):.1f} host-to-device, "
                     f"{sy['per_round_by_kind'].get('implicit', 0):.1f} implicit via two-index assignment); scaled to the GPU profile's 75.5 rounds and 4 micro-batches these lines give {f0(sy['scaled_total_sync_lines'])} per update against "
                     f"{f0(sy['gpu_same_lines'])} at the same lines in the GPU record (the record's total 1,319.5 also has {sy['gpu_only_lines']:.0f} in the real Gemma front). The GPU profile's 1,305 / (4 x 17.28) = {gpu_per:.1f} per round, and 1,319.5 / 75.5 = {1319.5 / 75.5:.1f} on the profiled updates")
    return out


def render_md(res, gpu):
    v = verdicts(res)
    L = []
    A = L.append
    meta = res.get('meta') or {}
    A('# Launch attribution of one B3G2 3M update (accum 4), counted on the CPU (2026-10-16)')
    A('')
    A('Instrument: `launch/attrib.py` (tests `test_attrib.py`). Trainer code: custom_io at commit 74d6e92c75, built through the profiling harness (`prof/prof_train.py` World, so the model, caps and rows are the real ones). '
      'Everything here was counted on a 4-core CPU box with torch 2.11.0+cpu, **no GPU**. Labels: **shown** = I ran it and it is in the tables below; **suggested** = read from code or a documented table, not measured here; **untested** = not run.')
    A('')
    A('## Verdicts on the four claims')
    A('')
    A(md_table(['claim', 'verdict', 'numbers (this CPU run unless it says GPU)'], [[k, f'**{lab}**', txt] for k, (lab, txt) in v.items()]))
    A('')
    A(summary_text(res, gpu, v))
    # ---- setup
    A('## What was run')
    A('')
    A(md_table(['run', 'what', 'size'], setup_rows(res)))
    A('')
    A(setup_notes(res))
    # ---- per-update totals
    A('## Per-update totals by phase (natural K draws, seed 400, one update after one warm-up update)')
    A('')
    A(natural_tables(res))
    # ---- per round
    A('## Per-round table: region x phase (kernel ops per thinker round)')
    A('')
    A(round_tables(res))
    # ---- fixed
    A('## The part that does not depend on the number of rounds (once per micro-batch)')
    A('')
    A(fixed_table(res))
    # ---- fit
    A('## C1: ops per micro-batch against the number of rounds n')
    A('')
    A(fit_tables(res))
    # ---- C2
    A('## C2: the writer passes against everything else')
    A('')
    A(c2_tables(res))
    # ---- C3
    A('## C3: do the per-round counts depend on the rows of the micro-batch?')
    A('')
    A(c3_tables(res))
    # ---- C4
    A('## C4: host syncs by call site')
    A('')
    A(sync_tables(res, gpu))
    # ---- kernel estimate
    A('## Kernel estimate against the GPU profile (75,966 kernels per update)')
    A('')
    A(estimate_tables(res, gpu))
    A('## What this points at (suggested, untested)')
    A('')
    A(points_text(res))
    A('')
    # ---- bias
    A('## How the synthetic rows bias this')
    A('')
    A(bias_text(res))
    # ---- validation
    A('## Does the instrument itself hold?')
    A('')
    A(validation_text(res))
    A('## Not claimed')
    A('')
    A(not_claimed_text(res))
    return '\n'.join(L) + '\n'


def setup_rows(res):
    ins = res['inputs']
    ref = res['reference']
    rows = []
    nat = res['natural']
    if nat:
        rows.append(['natural', f"{len(nat)} full update(s) after 1 warm-up update: real 3M shape, batch 256, accum 4, seed 400, synthetic rows, K drawn by torch.randint as in training; rounds per micro-batch "
                                + '; '.join(str([int(x) for x in u['rounds_per_mb']]) for u in nat), 'whole update incl. clip + AdamW'])
    rows.append(['pinned', f"one micro-batch (64 rows) forward + backward per K, K pinned in custom_io.models.b3g2.KS; n = {', '.join(str(int(p['n'])) for p in res['fit_points'])}", 'for C1, per-round table, C2'])
    if 'c3' in res:
        rows.append(['rows', f"K = 16, batch 64 vs 256 at accum 4: {res['c3']['rows'][0]} vs {res['c3']['rows'][1]} rows per micro-batch", 'for C3'])
    if 'width' in res:
        rows.append(['width', 'batch 64, K = 16, synthetic prompts up to 2000 letters instead of 300', 'shape-independence check'])
    if 'autocast' in res['estimate']:
        rows.append(['autocast', 'K = 16 one micro-batch under torch.autocast("cpu", bfloat16)', 'counts the casts CPU autocast makes'])
    if 'multi' in res:
        rows.append(['multi-call rows', 'K = 16, 32 on rows with 3 to 9 calls (37 % of rows) instead of 0 or 2', 'bias of the synthetic rows'])
    return rows


def natural_tables(res):
    out = []
    nat = res['natural']
    if not nat:
        return 'not run'
    u = nat[0]
    out.append(f"**Update 0 (the first instrumented update, right after the warm-up update)**: rounds per micro-batch {[int(x) for x in u['rounds_per_mb']]} (K {u['K_per_mb']}), {int(u['rounds'])} rounds, device kernel ops {f0(u['kernel_ops_device'])}, "
               f"estimated CUDA launches {rng_(u['launches_lo'], u['launches_hi'])} (stub Gemma and CPU-tensor teacher excluded); CPU-tensor teacher ops {f0(u['host_ops'])}.")
    out.append('')
    pt = u['phase_table']
    rows = [[p['phase'], f0(p['ops']), f0(p['view']), f0(p['nolaunch']), f0(p['kernel']), '0 (CPU tensors)' if p['phase'].startswith('host') else ('n/a (stub)' if 'stub' in p['phase'] else rng_(p['lo'], p['hi']))] for p in pt]
    dv = [p for p in pt if not p['phase'].startswith('host') and 'stub' not in p['phase']]
    rows.append(['**device total**', f0(sum(p['ops'] for p in dv)), f0(sum(p['view'] for p in dv)), f0(sum(p['nolaunch'] for p in dv)), f"**{f0(sum(p['kernel'] for p in dv))}**", f"**{rng_(sum(p['lo'] for p in dv), sum(p['hi'] for p in dv))}**"])
    out.append(md_table(['phase', 'all ops', 'views (no kernel)', 'host-scalar / alloc', 'kernel ops', 'est. CUDA launches'], rows))
    out.append('')
    if len(nat) > 1:
        out.append('All natural updates (the same replica, successive batches; each has its own K draws):')
        out.append('')
        rr = []
        for x in nat:
            ph = {p['phase']: p for p in x['phase_table']}
            rr.append([x['update'], str([int(n) for n in x['rounds_per_mb']]), int(x['rounds']), f0(x['kernel_ops_device']), rng_(x['launches_lo'], x['launches_hi']), f"{x['launches_lo'] / x['rounds']:.0f} to {x['launches_hi'] / x['rounds']:.0f}",
                       f0(x['host_ops']), pct(abs(x['pred_err']), 2) + (' over' if x['pred_err'] > 0 else ' under')])
        out.append(md_table(['update', 'rounds per micro-batch', 'rounds', 'device kernel ops', 'est. CUDA launches', 'launches per round (all-in)', 'CPU teacher ops', 'per-round model predicts kernel ops to'], rr))
        out.append('')
    out.append('"Forward" excludes the train-loop ops and the stub Gemma; "backward" includes the autograd engine\'s own gradient additions (region grad_accumulate); "recompute" is the checkpoint re-forward '
               'the engine triggers inside backward (answer pass from round 8, thinker from round 12; the non-reentrant checkpoint stops re-running a function once the saved tensors backward needs are rebuilt, so a recompute is shorter than the forward). '
               'The clip and AdamW launch numbers come from the multi-tensor-apply model (`multi_tensor_launches`), not from the CPU op list (which shows the same ops: one `_foreach_norm`, one `_foreach_mul_`, two `_fused_adamw_`).')
    return '\n'.join(out)


def round_tables(res):
    out = []
    ref = res['reference']
    out.append(f"From the pinned run with n = {ref['n']} rounds (64 rows, K = {ref['K']}); per-round values are means over the rounds of each class. Device kernel ops; in brackets the estimated CUDA launches (low to high). "
               f"The thinker is checkpointed from round {ref['n_loops']} (`t >= n_loops`), the answer pass from round {ref['ckpt_from']} (`CKPT_FROM`), the call pass never.")
    out.append('')
    regions = [r for r in REGIONS if r not in ('teacher_host', 'train_loop', 'optimizer')]
    for c in res['classes']:
        cells = c['cells']
        rows = []
        for reg in regions:
            f = cells.get(f'forward|{reg}', [0, 0, 0, 0]); b = cells.get(f'backward|{reg}', [0, 0, 0, 0]); rc = cells.get(f'recompute|{reg}', [0, 0, 0, 0])
            tot = [f[i] + b[i] + rc[i] for i in range(3)]
            if sum(tot) == 0:
                continue
            rows.append([reg, f1(f[0]), f1(b[0]), f1(rc[0]), f1(tot[0]), f'{f1(tot[1])} to {f1(tot[2])}'])
        pr = c['per_round']
        rows.append(['**all regions**', '', '', '', f"**{f1(pr['kernel'])}**", f"**{f1(pr['lo'])} to {f1(pr['hi'])}**"])
        out.append(f"**{c['name']}**  (views, which launch nothing: {f1(pr['view'])} per round)")
        out.append('')
        out.append(md_table(['region', 'forward', 'backward', 'recompute', 'total kernel ops', 'est. CUDA launches'], rows))
        out.append('')
    to = res.get('top_ops')
    if to:
        out.append(f"**Which ATen ops fill a steady round** (rounds {to['rounds'][0]} to {to['rounds'][1]} of the n = {ref['n']} run; {to['total']:.0f} device kernel ops per round; one row per op name, all overloads):")
        out.append('')
        out.append(md_table(['op', 'per round', 'share', 'where (region/phase: per round)'], [[x['op'], f1(x['per_round']), pct(x['share'], 1), ', '.join(f'{w} {c:.1f}' for w, c in x['where'])] for x in to['ops']]))
        out.append('')
    eb = res.get('engine_ops_per_round')
    if eb:
        out.append('The engine\'s gradient additions (region grad_accumulate) are real kernel launches on CUDA (the GPU profile\'s most frequent kernel is the bf16 `add`, 5,844 per update): every parameter used in each round and every '
                   'activation read by more than one op gets one add per use. Per round, by op: ' + ', '.join(f'{k} {v:.1f}' for k, v in eb.items()) + '.')
        pb = res.get('engine_by_producer_per_round')
        if pb:
            out.append('')
            out.append('By the region whose backward produced the gradient being added (per steady round): ' + ', '.join(f'{k} {v:.1f}' for k, v in sorted(pb.items(), key=lambda kv: -kv[1])) + '.')
    return '\n'.join(out)


def fixed_table(res):
    fx = res['fixed']
    rows = []
    for key, v in sorted(fx['cells'].items()):
        ph, reg = key.split('|')
        rows.append([reg, ph, f0(v[0]), f'{f0(v[1])} to {f0(v[2])}', f0(v[3])])
    t = fx['totals']
    rows.append(['**total**', '', f"**{f0(t['kernel'])}**", f"**{f0(t['lo'])} to {f0(t['hi'])}**", f0(t['view'])])
    return ("Ops with no round tag in the n = 32 run: the reader and tape (the stub Gemma front excluded), the answer teacher's device zeros, the loss tail (`ln_z` / stop head over all rounds at once), "
            "the engine's AccumulateGrad of the parameters. The CPU-tensor teacher has its own fixed part, see the fit table.\n\n" + md_table(['region', 'phase', 'kernel ops', 'est. CUDA launches', 'views'], rows))


def fit_tables(res):
    out = []
    pts = res['fit_points']
    out.append(md_table(['n', 'K', 'all ops (dev)', 'device kernel ops', 'est. launches (low)', 'est. launches (high)', 'writer kernel ops', 'CPU teacher ops (host)'],
                        [[int(p['n']), p['K'], f0(p['all_ops']), f0(p['kernel_ops_device']), f0(p['launches_lo']), f0(p['launches_hi']), f0(p['writer_kernel']), f0(p['kernel_teacher_host'])] for p in pts]))
    out.append('')
    rows = []
    names = dict(all_ops='all ops incl. views (device)', kernel_ops_device='kernel ops (device)', kernel_ops_incl_host='kernel ops incl. CPU teacher', launches_lo='est. launches, low', launches_hi='est. launches, high',
                 writer_kernel='writer passes: kernel ops')
    for k, f in res['fits'].items():
        label = names.get(k, k.replace('kernel_', 'kernel ops: '))
        rows.append([label, f1(f['a']), f1(f['b']), f"{f['r2']:.4f}", pct(f['max_rel_resid']), f1(f['b_n_ge_12']) if f['b_n_ge_12'] is not None else ''])
    out.append(md_table(['quantity per micro-batch', 'a', 'b (per round)', 'R2', 'worst point', 'b using n >= 12 only'], rows))
    out.append('')
    ad = [x for x in res['additivity'] if x['metric'] == 'kernel']
    out.append('Additivity (the structure behind the line): the reference run\'s fixed part plus its per-round totals reproduce every other pinned run: ' + '; '.join(f"n = {x['n']}: {x['rel_err'] * 100:+.2f} %" for x in ad)
               + '. The error is 0 from n = 14 on and small for n < 14 because the first rounds of a run depend on where its rows\' calls fall (the schedule is random per run); the per-round cost of round t does not depend on n.')
    return '\n'.join(out)


def c2_tables(res):
    out = []
    rows = []
    for c in res['c2']:
        k, lo, hi = c['kernel'], c['lo'], c['hi']
        rows.append([c['name'], f1(k['total'] / 1), pct(k['share']) if k['share'] is not None else '', pct(k['share_no_engine']) if k['share_no_engine'] else '', pct(k['share_folded']) if k['share_folded'] is not None else 'n/a',
                     pct(lo['share']) + ' to ' + pct(hi['share']), pct(c['share_incl_cpu_teacher_ops']) if c['share_incl_cpu_teacher_ops'] else '',
                     ' / '.join(pct(c['by_phase'][p]['share'], 0) if c['by_phase'][p]['share'] is not None else '-' for p in ('forward', 'backward', 'recompute'))])
    out.append('Rows are totals over the rounds of each class (not per round), so only the shares matter.')
    out.append('')
    out.append(md_table(['round class', 'kernel ops (sum over the class)', 'writer share of kernel ops', 'same, engine adds left out of the denominator', 'engine adds folded into their producer', 'writer share of est. launches (low to high)',
                         'writer share counting the CPU teacher ops', 'writer share within forward / backward / recompute'], rows))
    out.append('')
    out.append('Writer = region call_writer + answer_writer (B3G2.call_pass inside B3G2.loop, B3G2.ans_pass inside B3G2._loss, and `answer_teacher`\'s device zeros); the CPU-tensor teacher (ByteWriter.teacher internals) is not a launch and is counted separately.')
    return '\n'.join(out)


def c3_tables(res):
    c3 = res.get('c3')
    if not c3:
        return 'not run'
    out = []
    out.append(f"K = 16, rounds {c3['rounds_compared'][0]}..{c3['rounds_compared'][-1]} (all steady), {c3['rows'][0]} rows (batch 64 / accum 4) against {c3['rows'][1]} rows (batch 256 / accum 4); n = {c3['n'][0]}, {c3['n'][1]}.")
    out.append('')
    out.append(md_table(['', f"{c3['rows'][0]} rows", f"{c3['rows'][1]} rows"],
                        [['device kernel ops per steady round', f"{c3['device_kernel_ops_per_round'][0]:.2f}", f"{c3['device_kernel_ops_per_round'][1]:.2f}"],
                         ['CPU-tensor teacher ops per round (not launches)', f"{c3['host_cpu_ops_per_round'][0]:.1f}", f"{c3['host_cpu_ops_per_round'][1]:.1f}"],
                         ['device kernel ops, once per micro-batch', c3['fixed_device_kernel'][0], c3['fixed_device_kernel'][1]],
                         ['CPU teacher ops, once per micro-batch', c3['fixed_host'][0], c3['fixed_host'][1]]]))
    out.append('')
    out.append(f"(phase, region, op) cells with a different per-round count on the device side: {c3['n_differ_device']} of {c3['n_op_keys']}" + ('. They are:' if c3['device_diffs'] else '.'))
    if c3['device_diffs']:
        out.append('')
        out.append(md_table(['phase', 'region', 'op', 'kind', f"per round at {c3['rows'][0]} rows", f"per round at {c3['rows'][1]} rows"], [[*k, f'{x:.3f}', f'{y:.3f}'] for k, x, y in c3['device_diffs']]))
    out.append('')
    out.append('Teacher cells that depend on the rows (CPU tensors; python loops over rows and bytes, no launch): ' + ', '.join(f"{k[2]} {x:.0f} -> {y:.0f}" for k, x, y in c3['host_diffs_top'][:6]) + '.')
    w = res.get('width')
    if w:
        out.append('')
        out.append(f"Width check: the same {w['rows'][0]}-row micro-batch with prompts up to 300 letters and up to 2,000 letters: device kernel ops per steady round {w['device_ops_300']:.2f} vs {w['device_ops_2000']:.2f}, "
                   f"{w['n_differ']} differing cells, once-per-micro-batch ops {w['fixed'][0]} vs {w['fixed'][1]}. So running at width 300 (13 GB of RAM at 2,000) changes no op count.")
    return '\n'.join(out)


def sync_tables(res, gpu):
    sy = res.get('sync')
    if not sy:
        return 'not run'
    out = []
    tot = sy['totals']
    gr = (gpu or {}).get('rounds_per_update') or 75.5
    out.append(f"Counted over {tot['updates']} natural update(s), {int(tot['rounds'])} rounds, {tot['mbs']} micro-batches. Class (read from the source, suggested): **sync** = a device tensor in the real run, so on CUDA the call waits for the stream "
               f"(a device-to-host read, or a pageable host-to-device copy with non_blocking=False, which ends in a stream synchronise); **host** = a CPU tensor in the real run (counted here only because a CPU run cannot tell); "
               f"**noop** = `.to(dev)` of a tensor already there; **stub** = this harness's stand-in for the Gemma front; **no-sync** = a tensor-index call the GPU record does not flag; **gpu-only** = lines of the real Gemma front. "
               f"\"Scaled\" = per-round count x {gr:g} rounds + per-micro-batch count x 4, i.e. what this code would do in the GPU record's two profiled updates; the GPU column is that record (`set_sync_debug_mode('warn')`).")
    out.append('')
    rows = []
    for r in sy['rows']:
        g = r['gpu_per_update']
        rows.append([r['site'], r['kind'], r['cls'], f1(r['per_update']), f1(r['scaled']) if r['cls'] != 'gpu-only' else '', f1(g) if g is not None else '',
                     f"{r['scaled'] / g:.2f}" if (g and r['scaled']) else '', r['note']])
    for rr_, r in zip(rows, sy['rows']):
        rr_.insert(3, 'yes' if r['site'].split(' ')[0] in NOSYNC_LINES else '')
    out.append(md_table(['call site', 'kind', 'class', 'removed by the harness\'s nosync', 'per update (this run)', 'scaled to the GPU rounds', 'GPU per update', 'CPU / GPU', 'what it is'], rows))
    out.append('')
    ns = [r for r in sy['rows'] if r['cls'] == 'sync' and r['site'].split(' ')[0] in NOSYNC_LINES]
    out.append(f"The harness's `nosync` variant (GPU-RUN-3: -0.1 % to +1.2 % speed, i.e. nothing) removed the four lines marked: {sum(r['per_round_equiv'] for r in ns):.1f} of the {sy['per_round_equiv_sync_lines']:.1f} syncs per round; "
               f"the other {sy['per_round_equiv_sync_lines'] - sum(r['per_round_equiv'] for r in ns):.1f} per round read values computed on the device (`ok`, the answer-loop masks) or are the two index assignments and stay.")
    out.append('')
    out.append(f"**Sum over the {sy['n_sync_lines']} sync lines**: {sy['per_round_equiv_sync_lines']:.2f} per round (per update / rounds: device-to-host {sy['per_round_by_kind'].get('D2H', 0):.2f}, host-to-device {sy['per_round_by_kind'].get('H2D', 0):.2f}, "
               f"implicit via two-index assignment {sy['per_round_by_kind'].get('implicit', 0):.2f}); scaled: {f0(sy['scaled_total_sync_lines'])} per update; the same lines in the GPU record: {f0(sy['gpu_same_lines'])}; "
               f"GPU lines this run cannot reproduce (real Gemma front): {sy['gpu_only_lines']:.0f}.")
    if gpu:
        out.append('')
        out.append(md_table(['', 'per update', f'per round (at {gr:g} rounds)', 'per round (at 69.1 rounds = 4 x 17.28)'],
                            [['GPU cudaStreamSynchronize (profiler)', '1,305', f'{1305 / gr:.2f}', f'{1305 / 69.12:.2f}'],
                             ['GPU sync-debug warnings summed over lines', '1,319.5', f'{1319.5 / gr:.2f}', f'{1319.5 / 69.12:.2f}'],
                             ['GPU device-to-host copies (profiler)', '745', f'{745 / gr:.2f}', f'{745 / 69.12:.2f}'],
                             ['GPU host-to-device copies (profiler)', '561.5', f'{561.5 / gr:.2f}', f'{561.5 / 69.12:.2f}'],
                             ['this CPU census, the sync lines, scaled', f0(sy['scaled_total_sync_lines']), f"{sy['scaled_total_sync_lines'] / gr:.2f}", f"{(sy['per_round_equiv_sync_lines'] * 69.12):.0f} / 69.12 = {sy['per_round_equiv_sync_lines']:.2f}"]]))
        out.append('')
        out.append('The claim "about 19 per round" is the profiler\'s 1,305 divided by 4 x 17.28 rounds; the profiled updates had 75.5 rounds (b3g2.py:551 runs once per round), which gives 17.3. Either way the syncs scale with rounds, 4 teacher-copy waits + 2 teacher `.cpu()` + 3 schedule `tolist` + 1 `torch.tensor(sel)` + 1 `ok.tolist` + 1 `nonzero` + 3 reads in the answer loop + 2 two-index assignments = 17 per round. '
                   'Device-to-host copies per round in the GPU profile (9.9) equal the number of D2H lines here (2 + 3 + 1 + 1 + 3 = 10).')
    return '\n'.join(out)


def kstream_text(res):
    ks = res.get('k_stream')
    if not ks:
        return 'update 1: K 4, 16, 8, 8; update 2: 32, 4, 16, 16; update 3: 32, 16, 16, 8; update 4: 16, 8, 32, 4; update 5: 32, 32, 16, 16; update 6: 16, 16, 16, 4; update 7: 32, 16, 16, 4; update 8: 16, 16, 16, 32'
    return '; '.join(f'update {u}: K {", ".join(str(k) for k in kk)}' for u, kk in enumerate(ks) if 1 <= u <= 8)


def estimate_tables(res, gpu):
    e = res['estimate']
    if not e or 'update_parts_launches' not in e:
        return 'not run (needs a natural update)'
    out = []
    up = e['update_parts_launches']
    out.append(f"How the estimate is built (suggested, not measured): per micro-batch the per-round table gives the estimated launches (CUDA launches per ATen op from `KERNEL_TABLE` in attrib.py: one per kernel op by default, "
               f"with overrides for SDPA with a bool mask, the layer-norm backward, index_put with accumulate, embedding backward, select / slice backward; a same-dtype contiguous copy is a memcpy, not a launch); "
               f"per update add clip_grad_norm_ ({up['clip']} launches by the multi-tensor-apply model), fused AdamW ({up['adamw']}) and the train loop's loss and aux averaging ({up['loss_average']:.0f}). `low` and `high` are the two ends of the override brackets. "
               f"The micro-batch round counts of the real pool are not measured here. Case 1 takes the GPU record's mean of 17.28 with K from (4, 8, 16, 32) and n = max(K, last + 2): last + 2 = 10.56 for the two small K gives the mix (10.56, 10.56, 16, 32). "
               f"Case 2 is the GPU profile's own two updates, whose rounds are known: b3g2.py:551 runs once per round and the record has 75.5 per update, i.e. 151 over the two. The loop length is K = KS[torch.randint] and the K stream of seed 400 is the same here "
               f"(the K lists of my natural updates are the stream; counting stream updates from 0, my natural update 0 is stream update 1 because the warm-up update came first: {kstream_text(res)}), so the profiled updates were two consecutive updates of that stream with K sums of 148 ((32,32,16,16) and (16,16,16,4) = updates 5 and 6, or (32,16,16,4) and (16,16,16,32) = updates 7 and 8, "
               f"the profiler's default warm-up), and 151 = 148 + 3 means the one K = 4 draw ran n = 7 (7 is also what the harness rows give for that draw). Either way the micro-batch round counts are {{7, 16, 16, 16, 16, 16, 32, 32}}, "
               f"and case 2 is the estimate for exactly that mix, using the measured totals of the pinned runs with those n.")
    out.append('')
    rows = []
    for name, c in e['cases'].items():
        rows.append([name, f1(c['rounds'], 1), f"{f0(c['lo']['piecewise'])} to {f0(c['hi']['piecewise'])}", f"{f0(c['lo']['linear'])} to {f0(c['hi']['linear'])}",
                     f"{pct(c['lo']['piecewise'] / GPU['kernels'])} to {pct(c['hi']['piecewise'] / GPU['kernels'])}"])
    out.append(md_table(['rounds assumed', 'rounds per update', 'est. launches (per-round table)', 'est. launches (linear fit)', 'ratio to 75,966 (per-round table)'], rows))
    out.append('')
    gm = e['gemma_bound']
    c2 = list(e['cases'].values())[1]
    est_lo, est_hi = c2['lo']['piecewise'], c2['hi']['piecewise']
    gap_lo, gap_hi = GPU['kernels_profile'] - est_hi, GPU['kernels_profile'] - est_lo
    out.append(f"**Ratio.** The model-side estimate (no Gemma front, no bf16 casts) at the profiled updates' rounds is {rng_(est_lo, est_hi)} launches, **{pct(est_lo / GPU['kernels'], 0)} to {pct(est_hi / GPU['kernels'], 0)} of the 75,966 kernels** "
               f"the GPU profile counted (per round, all-in: {est_lo / 75.5:.0f} to {est_hi / 75.5:.0f} against the profile's {GPU['kernels'] / 75.5:.0f}). The gap is {rng_(gap_lo, gap_hi)} launches per update.")
    out.append('')
    cc = res.get('cross_check')
    if cc:
        out.append(f"**What the GPU profile itself says about the gap.** The profile lists the 25 CPU ops with the most self time, with call counts. For the ops that are one launch each, the CPU dispatch count at the same rounds ({res['cross_check_rounds']:g}) "
                   f"is compared with the GPU's call count per update:")
        out.append('')
        out.append(md_table(['aten op', 'GPU calls per update', 'CPU dispatch count at the same rounds', 'CPU / GPU', 'GPU minus CPU'],
                            [[x['op'], f0(x['gpu_per_update']) if x['gpu_per_update'] else 'not in the top 25', f0(x['cpu_pred_per_update']), f"{x['ratio']:.2f}" if x['ratio'] else '', f0(x['gpu_minus_cpu']) if x['gpu_minus_cpu'] is not None else ''] for x in cc]))
        out.append('')
        extra = [x for x in cc if x['gpu_minus_cpu'] and x['gpu_minus_cpu'] > 0 and x['op'] in ('aten::mm', 'aten::add + aten::add_', 'aten::mul', 'aten::pow', 'aten::_to_copy')]
        tot = sum(x['gpu_minus_cpu'] for x in extra)
        res['estimate']['gpu_only_launching_ops'] = dict(ops={x['op']: x['gpu_minus_cpu'] for x in extra}, total=tot)
        out.append(f"`addmm`, layer norm and `sum` agree to within 1 % (ratio 0.99 to 1.01): the CPU run sees the op sequence the GPU ran for the model. The ops that the GPU has and the CPU run does not are "
                   + ', '.join(f"{x['op']} +{f0(x['gpu_minus_cpu'])}" for x in extra) + f" per update, {f0(tot)} calls in all, each about one launch. That is {pct(tot / gap_hi if gap_hi else 0, 0)} to {pct(tot / gap_lo if gap_lo else 0, 0)} of the gap "
                   f"(suggested: `_to_copy` is the bf16 autocast casts, which a plain CPU run does not make; `pow` appears nowhere in this model's CPU op stream, and the extra `mul` and `mm` are what a Gemma front looks like: RMSNorm pow / mean / rsqrt / mul, and bias-free q/k/v/o/gate/up/down linears). "
                   f"The profile counts calls at every dispatcher nesting level, so these numbers are indications, not launch counts.")
        out.append('')
        kn = res.get('kernel_name_checks')
        if kn:
            out.append('Kernel-name sanity checks of the launch table (the GPU profile\'s top-25 kernels by time, counts per update, against the CPU op that should launch each one for one):')
            out.append('')
            out.append(md_table(['GPU kernel', 'GPU launches per update', 'CPU op at the same rounds', 'CPU ops per update', 'CPU / GPU'],
                                [[x['kernel'], f0(x['gpu_per_update']), x['cpu_op'], f0(x['cpu_per_update']), f"{x['ratio']:.2f}"] for x in kn]))
            out.append('')
            out.append('The layer-norm, attention-forward, cat and fill kernels are launched about once per CPU op, as the table assumes. What the top 25 cannot confirm is the kernels around them: the bool-mask conversion and padding before the attention kernel (the table says 3 to 5 extra '
                       'launches per masked SDPA forward) and the sort kernels of the scatter (6 to 9 per accumulating index_put_ in total); those two brackets are untested.')
            out.append('')
    ac = e.get('autocast')
    if ac:
        per_round_cast = (ac['kernel_ops'][1] - ac['kernel_ops'][0]) / ac['n']
        out.append(f"**Casts under CPU autocast** (shown for CPU's cast list; CUDA's list is longer): one micro-batch with n = {int(ac['n'])} under `torch.autocast('cpu', bfloat16)` makes {ac['casts_per_mb']} dtype-changing `_to_copy` calls ({ac['casts_per_round']:.1f} per round) "
                   f"and changes the device kernel ops from {f0(ac['kernel_ops'][0])} to {f0(ac['kernel_ops'][1])} ({per_round_cast:+.1f} per round, {pct((ac['kernel_ops'][1] - ac['kernel_ops'][0]) / ac['kernel_ops'][0], 0)}). "
                   f"The GPU profile has {f0(ac['gpu_to_copy_per_update'] or 0)} `aten::_to_copy` per update = {ac['gpu_to_copy_per_round']:.0f} per round, so CUDA autocast (casts before every linear, fp32 islands for layer norm / softmax / pow, grad casts in backward, and the Gemma front's own) "
                   f"makes several times as many casts as CPU autocast: the CPU number is a floor.")
        out.append('')
    out.append(f"**The real Gemma front** (untested here: only a stub runs on this box). The GPU PTC profile at accum 16 has {PTC_KERNELS_PER_UPDATE:,} kernels per update for one Gemma call per micro-batch plus the small PTC transformer, so one Gemma call plus one PTC micro-batch is at most "
               f"{PTC_KERNELS_PER_UPDATE / PTC_ACCUM:,.0f} launches; B3G2 calls the front {gm['calls_per_mb']:.2f} times per micro-batch (question and tape strings: 63.4 calls per 32 micro-batches in the accum-32 profile), so at most {f0(gm['upper_per_update_accum4'])} launches per update "
               f"({pct(gm['upper_per_update_accum4'] / GPU['kernels'], 0)} of the total) can be Gemma (suggested, an upper bound only).")
    out.append('')
    out.append("**Other things a CPU run cannot see** (untested): cuBLAS split-K reduce kernels, allocator zero fills, the `cuLaunchKernel` path (5,318 per update) that cutlass / flash kernels use, and any table entry that is wrong: the low-to-high bracket covers the SDPA mask conversion / pad (4 to 6 launches forward) and the sort-based scatter (6 to 9), "
               "so a wrong SDPA backend moves the estimate by a few hundred launches, not thousands (suggested).")
    return '\n'.join(out)


def summary_text(res, gpu, v):
    """The plain-language lead, built from the result so it cannot drift from the tables."""
    est = res['estimate']
    out = ['### In plain words', '']
    f = res['fits']['kernel_ops_device']
    fx = res['fixed']['totals']
    cl = res['classes']
    c17 = next(c for c in cl if c['name'].startswith('t = 1'))
    top = max(cl, key=lambda c: c['per_round']['kernel'])
    eng = sum(c['kernel']['engine'] for c in res['c2']) / sum(c['kernel']['total'] for c in res['c2'])
    out.append(f"- **Shown (CPU op counts):** the launches of this training are a per-round story. A micro-batch costs a fixed {fx['kernel']} device kernel ops (reader, tape, loss tail, parameter grads: {pct(fx['kernel'] / (fx['kernel'] + f['b'] * 17.28), 1)} of a 17.28-round micro-batch) "
               f"plus about {c17['per_round']['kernel']:.0f} per round in rounds 1 to 7, rising to {top['per_round']['kernel']:.0f} per round once the answer pass and the thinker are being recomputed. In estimated CUDA launches a round is "
               f"{c17['per_round']['lo']:.0f} to {c17['per_round']['hi']:.0f}, later {top['per_round']['lo']:.0f} to {top['per_round']['hi']:.0f}.")
    wr = [c['kernel']['share'] for c in res['c2'] if c['name'].startswith('t = 1') or 'recomputed' in c['name']]
    fd = [c['kernel']['share_folded'] for c in res['c2'] if (c['name'].startswith('t = 1') or 'recomputed' in c['name']) and c['kernel'].get('share_folded') is not None]
    out.append(f"- **Shown:** the two writer passes (call_pass, ans_pass; forward, backward and recompute) are {pct(min(wr))} to {pct(max(wr))} of the per-round device kernel ops: about half, not clearly over it. "
               f"The thinker is {pct(sum(res['classes'][1]['cells'].get(f'{p}|thinker', [0])[0] for p in ('forward', 'backward', 'recompute')) / res['classes'][1]['per_round']['kernel'], 0)} to "
               f"{pct(sum(res['classes'][-2]['cells'].get(f'{p}|thinker', [0])[0] for p in ('forward', 'backward', 'recompute')) / res['classes'][-2]['per_round']['kernel'], 0)} of a round. "
               f"The autograd engine's own gradient additions (one add for every extra use of a shared weight or activation, every round) are {pct(eng, 0)} of the per-round ops and sit in neither."
               + (f" Attributed to the pass that produced the gradient they would lift the writers to {pct(min(fd))} to {pct(max(fd))}." if fd else ''))
    if 'c3' in res:
        a, b = res['c3']['device_kernel_ops_per_round']
        out.append(f"- **Shown:** the per-round device op count does not depend on the rows ({a:.1f} at {res['c3']['rows'][0]} rows, {b:.1f} at {res['c3']['rows'][1]}). The CPU-tensor teacher does ({res['c3']['host_cpu_ops_per_round'][0]:.0f} vs {res['c3']['host_cpu_ops_per_round'][1]:.0f} CPU ops per round): "
                   f"that is host python time, not launches.")
    sy = res.get('sync')
    if sy:
        out.append(f"- **Shown (the call sites and counts), suggested (that CUDA waits at each):** {sy['per_round_equiv_sync_lines']:.1f} blocking host-device calls per round at {sy['n_sync_lines']} named lines (all in `ByteWriter.teacher`, `B3G2.loop` and the answer loop of `B3G2._loss`), "
                   f"{sy['per_round_by_kind'].get('D2H', 0):.0f} of them device-to-host reads. They scale with the rounds. The \"about 19\" is 1,305 / (4 x 17.28); at the profiled updates' own 75.5 rounds the GPU record gives 17.3 and this census 17.")
    if est and est.get('cases'):
        c = list(est['cases'].values())[1]
        g = est.get('gpu_only_launching_ops')
        out.append(f"- **Suggested (an estimate, not a measurement):** the model-side launch estimate is {pct(c['lo']['piecewise'] / GPU['kernels'], 0)} to {pct(c['hi']['piecewise'] / GPU['kernels'], 0)} of the 75,966 kernels per update. "
                   + (f"The ops the GPU profile lists beyond what this CPU run has (bf16 casts, the Gemma front's matmuls and RMSNorm-style `pow` / `mul`) come to about {f0(g['total'])} calls per update, which is the size of the gap." if g else '')
                   + " The model code itself, with `addmm` and layer norm matching the GPU's counts to 1 %, is not where the missing launches are.")
    out.append('')
    return '\n'.join(out)


COMMANDS = '''cd launch; export OMP_NUM_THREADS=1
python attrib.py natural --threads 1 --synth-letters 300 --n-updates 5 --out natural5b.json         # seed 400, 1 warm-up update, then 5 instrumented updates (final code)
python attrib.py pinned  --threads 1 --synth-letters 300 --ks 4,6,8,10,12,14,16,20,24,32 --out pinned.json      # one micro-batch (64 rows) per K, fwd + backward
python attrib.py rows    --threads 1 --synth-letters 300 --batches 64,256 --k 16 --out rows.json                # 16 vs 64 rows per micro-batch
python attrib.py rows    --threads 1 --synth-letters 2000 --batches 64 --k 16 --out width2000_b64.json         # the width check
python attrib.py pinned  --threads 1 --synth-letters 300 --ks 16 --autocast --out autocast16.json             # CPU autocast bf16 casts
python attrib.py multi   --threads 1 --synth-letters 300 --ks 16,32 --out multi.json                          # rows with 3 to 9 calls
python attrib.py report --natural natural5b.json --natural-check natural5.json --pinned pinned.json --rows-json rows.json --autocast-json autocast16.json --width width2000_b64.json --multi multi.json --md ATTRIB-CPU-2026-10-16.md --json ATTRIB-CPU-2026-10-16.json'''
# natural5.json is the same five updates counted by an earlier revision of the instrument (before the train loop's aux averaging and the producer tags were added); it is only compared with natural5b.json.


def setup_notes(res):
    m = res.get('meta') or {}
    return ('Commands (every number below is regenerated from the raw runs by the last one):\n\n```\n' + COMMANDS + '\n```\n\n' + _setup_notes(res))


def _setup_notes(res):
    m = res.get('meta') or {}
    return ('Common to every run: arm B3G2, rung 3M (4,023,302 trained parameters), caps `caps_b3g2.json`, stub Gemma front, device cpu, torch ' + str(m.get('torch', '2.11.0+cpu')) + ', seed 400, rows from `prof_train.synth_rows` '
            '(half skills-shaped rows with two worked steps, half cloze rows with none), `n_loops` = ' + str(m.get('n_loops')) + '. One CPU thread per run. '
            '**Deviation from the brief:** the synthetic prompts are at most 300 letters, not the caps\' 2,000, because the 2,000-letter shape needs 13 GB of RAM on this shared box; every op count is independent of the padded width '
            '(shown by the width check below). The update is replicated, not called: `Replica.update` does split_batch, `model.loss(mb)` under the (here empty) autocast, `(l / k).backward()`, `clip_grad_norm_(1.0)`, fused AdamW step and `zero_grad(set_to_none=True)` '
            'as train.py does; the optimizer is built `fused=True` even on CPU so that its op sequence is the CUDA one (the harness builds it fused only on CUDA).')


def points_text(res):
    cl = res['classes']
    c17 = next(c for c in cl if c['name'].startswith('t = 1'))
    top = max(cl, key=lambda c: c['per_round']['kernel'])
    eng = res.get('engine_by_producer_per_round') or {}
    to = res.get('top_ops') or {}
    add = next((x for x in to.get('ops', []) if x['op'] == 'add'), None)
    return ('- Launch count is set by rounds, not by rows: about ' + f"{c17['per_round']['lo']:.0f} to {top['per_round']['hi']:.0f}" + f" model-side launches per round (about {17.28 * c17['per_round']['lo']:,.0f} to {17.28 * top['per_round']['hi']:,.0f} in a 17.28-round micro-batch), the same at 16 or 64 rows (C3). "
            'Bigger micro-batches change how many micro-batches (and fixed parts, and K draws) there are, not the ops per round; removing syncs removes waits, not launches.\n'
            + (f"- The single biggest op is `add` ({add['share'] * 100:.0f} % of a steady round's kernel ops), and most of it is the autograd engine adding gradients of shared weights and activations once per use per round " + f"({sum(eng.values()):.0f} per round: thinker {eng.get('thinker', 0):.0f}, call writer {eng.get('call_writer', 0):.0f}, answer writer {eng.get('answer_writer', 0):.0f}). A change that accumulates those gradients in fewer launches (or shares fewer weights per round) removes more launches than any single forward op can (untested).\n" if add and eng else '')
            + (lambda a, b, c: f"- Checkpointing adds to the per-round count: {a:.0f} kernel ops in rounds 1 to 7, {b:.0f} from round 8 (answer pass recomputed, +{100 * (b / a - 1):.0f} %), {c:.0f} from round 12 (thinker too, +{100 * (c / b - 1):.0f} %), so the checkpoint start is a launch lever as well as a memory one (untested).\n")(
                c17['per_round']['kernel'], cl[2]['per_round']['kernel'], cl[3]['per_round']['kernel'])
            + '- The two things this CPU run cannot count are the bf16 casts (the GPU profile has 13k `_to_copy` per update) and the Gemma front (at most 24k launches per update by the PTC bound, fixed per micro-batch): together they are about as many launches as the model-side ops. A GPU run with the profiler\'s per-kernel names grouped by region would settle both (untested).')


def host_share_text(res):
    sh = []
    for u in res['natural']:
        pt = {p['phase']: p for p in u['phase_table']}
        h = [p for p in u['phase_table'] if p['phase'].startswith('host')][0]['ops']
        d = sum(p['ops'] for p in u['phase_table'] if not p['phase'].startswith('host') and 'stub' not in p['phase'])
        sh.append(h / (h + d))
    return f"the teacher is {pct(min(sh), 0)} to {pct(max(sh), 0)} of all dispatched ops of the natural updates, views included" if sh else 'n/a'


def bias_text(res):
    out = []
    out.append('The harness\'s synthetic rows have 0 calls (cloze rows) or 2 calls (skills rows), so `last + 2` is about 4 to 7 and K decides n; the real pool has more calls per row: 37 % of rows have calls (GPU-RUN-1 padding section), and the GPU record\'s mean of 17.28 rounds per micro-batch with K drawn '
               'from (4, 8, 16, 32) needs n = max(K, last + 2) to be about 10 for the two small K, i.e. the longest program in a 64-row micro-batch is several calls long. What that changes and what it does not:')
    out.append('')
    out.append('- **Per-round op counts of the writer passes: nothing**, because `call_pass` and `ans_pass` run once per round whatever the call text length (the length L only changes tensor sizes, not the number of ops). Shown by the per-round tables above (they repeat from round to round) and by the multi-call run below.')
    mr, ref = res.get('multi'), res.get('multi_ref')
    if mr and ref:
        rows = []
        for e in mr:
            r = next((x for x in ref if x['K'] == e['K']), None)
            if r:
                rows.append([e['K'], f"{int(r['n'])} / {int(e['n'])}", f"{e['rounds_compared'][0]} to {e['rounds_compared'][1]}", f"{r['per_round_kernel_ops']:.1f}", f"{e['per_round_kernel_ops']:.1f}", f"{100 * (e['per_round_kernel_ops'] / r['per_round_kernel_ops'] - 1):+.1f} %", pct(r['share']), pct(e['share']), f"{e['host_ops_per_round']:.0f}"])
        out.append('')
        out.append(md_table(['K', 'n (harness rows / multi-call rows)', 'rounds compared', 'device kernel ops per round, harness rows', 'same, multi-call rows', 'change', 'writer share, harness rows', 'writer share, multi-call rows', 'CPU teacher ops per round, multi-call rows'], rows))
        out.append('')
        e0 = mr[0]
        r0 = next((x for x in ref if x['K'] == e0['K']), None)
        dif = [e - r for e, r in zip(e0['early_rounds'], r0['early_rounds'])] if r0 else []
        out.append(f"- **Subset indexing: about +{max(dif) if dif else 0} kernel ops per round ({100 * max(dif) / r0['per_round_kernel_ops']:.0f} %) in the rounds where some rows are still \"inside\" their program.** While round <= the longest call round the loop and `_loss` select rows "
                   f"(`pk(x) = x[si]`: four index ops per round for the answer pass, one `torch.tensor(sel)` and the call-pass rows). Device kernel ops of rounds 0 to 11 on the multi-call rows at K = {e0['K']}: {', '.join(str(x) for x in e0['early_rounds'])}"
                   + (f"; on the harness rows: {', '.join(str(x) for x in r0['early_rounds'])}" if r0 else '') + '.')
        dsh = [100 * (e['share'] - next(x for x in ref if x['K'] == e['K'])['share']) for e in mr if any(x['K'] == e['K'] for x in ref)]
        out.append(f"- **Writer share: {', '.join(f'{d:+.1f}' for d in dsh)} points on the multi-call rows** (the extra ops are index ops of the loop and the loss tail, not writer ops), so the harness rows slightly overstate the writer share against a pool with more calls per row; "
                   "that is a shift of under one point against a 45 to 51 % share and does not change any verdict. The multi-call rows are a stress case (their longest program with gaps needs 24 rounds at K = 16, while the GPU profile's own K = 4 draw ran only 7 rounds, see the estimate section), so this is an upper bound on the effect.")
    out.append('- **The CPU-tensor teacher: a lot more host work**, because `ByteWriter.teacher` loops over rows and bytes in python (about 8 CPU ops per byte of a row with a call text); that is host time (no launch), and it grows with the calls per row and with the rows. Its share of the dispatched ops is large here (' + host_share_text(res) + ') and it is not part of any launch figure.')
    out.append('- **The tape**: K = the longest call list in the micro-batch sets the tape width (K x le), so the thinker\'s keys and values per round are longer with the real pool; that is tensor size, not op count.')
    return '\n'.join(out)


def engine_text(res):
    e = res.get('engine_sources') or {}
    tot = sum(e.values())
    if not tot:
        return 'the producer split needs the pinned runs'
    fwd = sum(v for k, v in e.items() if k not in ('param', 'engine'))
    return f"{pct(fwd / tot, 1)} are additions of a gradient that a named forward region's backward produced (tagged with that region), {pct(e.get('param', 0) / tot, 1)} are the parameters' own AccumulateGrad, {pct(e.get('engine', 0) / tot, 1)} have no producer"


def validation_text(res):
    v = res['validation']
    nat = res['natural']
    lines = [f"- Region coverage (shown): {pct(v['share_not_other'], 3)} of {f0(v['kernel_ops_total'])} kernel ops over all runs have a region other than 'other' (brief: >= 99 %).",
             f"- Backward attribution (shown): {pct(v['share_backward_forward_region'], 3)} of {f0(v['backward_kernel_ops_excl_engine'])} backward + recompute kernel ops (the engine's own additions excepted) carry the region of a forward op (brief: >= 95 %); "
             f"{v['untagged_nodes']} of {f0(v['reachable_nodes'])} autograd nodes reachable from the losses were not found by the forward tagger. The engine's own additions are {pct(v['engine_share_of_backward'])} of all backward + recompute kernel ops and are filed under grad_accumulate, "
             f"by design not a forward region; of those, {engine_text(res)}.",
             f"- Thinker recompute round check (shown): the round the think wrapper saw agrees with the round of the node that asked for the recompute in {f0(v['think_round_check']['equal'])} ops, disagrees in {v['think_round_check']['differ']}.",
             "- Counts identical across two runs, the sync wrapper restoring torch exactly, and the instrument leaving loss and weights bit-identical are unit tests (`test_attrib.py`, 17 tests, all pass)."]
    dr = res.get('determinism_real_shape')
    if dr:
        lines.append(f"- Determinism at the real shape (shown): {dr['identical']} of {dr['updates_compared']} natural updates counted in a second, separate process (an earlier revision of the engine tagging, so op names are compared without the producer suffix) give identical micro-batch tallies, cell for cell ({f0(dr['ops_compared'])} ops).")
    if nat:
        err = [abs(u['pred_err']) for u in nat if u['pred_err'] is not None]
        lines.append(f"- Out-of-sample check of the per-round model (shown): the fixed part plus per-round totals of the n = {res['reference']['n']} reference run predict the device kernel ops of {len(nat)} complete natural update(s) to within {pct(max(err))} (their row mixes, plan and gap draws are not the reference's).")
    return '\n'.join(lines)


def not_claimed_text(res):
    return ('- No CUDA time, no CUDA launch, no real profiler: the launch numbers are an ATen-op-to-launch table applied to a CPU op stream. The 75,966 figure is the GPU-RUN-3 profile\'s, not mine.\n'
            '- The real Gemma front and the real row pool were not available. The stub front\'s ops are excluded from every launch figure; the real front is bounded from above only.\n'
            '- bf16 autocast on CUDA was not reproduced; CPU autocast has a different cast list. The cast counts are a floor.\n'
            '- One seed (400), one synthetic row set (plus one multi-call set), one 3M shape. The K draws of the natural updates are whatever seed 400 gave after a warm-up update; the 17.28-round population mean is the GPU record\'s, not recomputed here.\n'
            '- Why CUDA waits at b3g2.py:375 / :376 (index_put with two tensor indices) is not explained; the call counts are shown, the wait is taken from the GPU record.\n'
            '- Host python time of the teacher loops was not measured on a device-attached run.')


def compact_run(run):
    """A natural update without its per-round tags (they are only needed for the pinned runs): rows merged over the rounds, round -> 'r' or None."""
    out = dict(run)
    out['mbs'] = []
    for m in run['mbs']:
        agg = {}
        for r in m['T']:
            k = (r[0], r[1], None if r[2] is None else 'r', r[3], r[4])
            v = agg.setdefault(k, [0, 0, 0, 0])
            for i in range(4):
                v[i] += r[5 + i]
        mm = dict(m)
        mm['T'] = [[*k, *v] for k, v in agg.items()]
        out['mbs'].append(mm)
    return out


def load_inputs(a):
    def get(path):
        return json.load(open(path)) if path and os.path.exists(path) else None
    nat, pin, rows, ac, width, multi = (get(getattr(a, k, None)) for k in ('natural', 'pinned', 'rows_json', 'autocast_json', 'width', 'multi'))
    inp = dict(natural=[], pinned=[], rows=[], autocast=[], width=[], multi=[])
    for k, d in (('natural', nat), ('pinned', pin), ('rows', rows), ('autocast', ac), ('width', width), ('multi', multi)):
        for path_d in (d if isinstance(d, list) else [d]):
            if path_d:
                inp[k] += path_d['runs']
    inp['meta'] = (pin or nat or {}).get('meta')
    inp['k_stream'] = (nat or {}).get('k_stream') if isinstance(nat, dict) else None
    chk = get(getattr(a, 'natural_check', None))
    inp['natural_check'] = chk['runs'] if chk else []
    return inp


def report_main(a):
    inp = load_inputs(a)
    gpu = load_gpu()
    res = build_report(inp, gpu)
    md = render_md(res, gpu)
    if a.md:
        open(a.md, 'w').write(md)
    if a.json:
        raw = dict(inp)
        raw['natural'] = [compact_run(r) for r in inp['natural']]
        raw.pop('natural_check', None)                       # only its comparison with the natural run is kept (report.determinism_real_shape)
        out = dict(report=res, gpu_facts=GPU, gpu_profile=dict(rounds_per_update=(gpu or {}).get('rounds_per_update'), sync_sites=(gpu or {}).get('sites'), top_cpu_ops_per_update=(gpu or {}).get('ops')),
                   kernel_table=dict(KERNEL_TABLE={k: v for k, v in KERNEL_TABLE.items()}, SDPA_FWD=SDPA_FWD, SDPA_BWD=SDPA_BWD, INDEX_PUT_ACC=INDEX_PUT_ACC),
                   site_notes={k: list(v) for k, v in SITE_NOTES.items()},
                   raw_note=('raw = the packed tallies of every run, rows [phase, region, round, op, kind, count, launches_low, launches_high, memcpy]; the natural updates keep a round only as "r" (some round) or null (once per micro-batch) '
                             'to keep the file small, the per-round data are in the pinned runs; sync rows [kind, site, phase, round, region, count]'),
                   raw=raw)
        json.dump(out, open(a.json, 'w'), separators=(',', ':'), default=lambda o: list(o) if isinstance(o, (set, tuple)) else str(o))
    print(md if not a.md else f'wrote {a.md}')
    return res


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
    ap.add_argument('--natural')
    ap.add_argument('--natural-check', dest='natural_check', help='an earlier natural run of the same updates: compared cell by cell (determinism at the real shape)')
    ap.add_argument('--pinned')
    ap.add_argument('--rows-json', dest='rows_json')
    ap.add_argument('--autocast-json', dest='autocast_json')
    ap.add_argument('--width')
    ap.add_argument('--multi')
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    if a.cmd == 'report':
        return report_main(a)
    load(a.pkg_root)
    {'natural': cmd_natural, 'pinned': cmd_pinned, 'rows': cmd_rows, 'multi': cmd_multi}[a.cmd](a)


if __name__ == '__main__':
    main()
