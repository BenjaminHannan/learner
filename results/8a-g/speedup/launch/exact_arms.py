"""exact_arms: two small candidate-EXACT arms of the launch-bound study, as prof_train.py variants for the B3G2 arm (custom_io at 74d6e92c75, the code of GPU-RUN-3).

  kvcat      cache the per-block concatenation of the memory K/V and the prompt K/V that ledger.CBlock.forward redoes every round.
  fastteach  build ByteWriter.teacher's tensors for the G2f writer (no copy path) with numpy, with no device read and no zero tensor copied from the host.

Both are meant to give the SAME numbers as train.py bit for bit (fp32 on the CPU at 1 thread: test_exact_arms.py shows it, comparing the int bit patterns so that -0.0 and +0.0 are told apart; at 2 or more CPU threads
the UNMODIFIED code is itself not run-to-run bitwise (embedding gradient), so no arm can be bit-identical there; CUDA and bf16 on CUDA: untested). Neither edits custom_io: a method is rebuilt from its own
source with one exact text edit (prof_train.patched_fn) or replaced on the model INSTANCE, and teardown() puts every attribute back (identity-checked by test_exact_arms.py).
Registered for prof_launch.py through NEW_VARIANTS.

----------------------------------------------------------------------------------------------------------------------------------------------------------------------
kvcat
----------------------------------------------------------------------------------------------------------------------------------------------------------------------
CBlock.forward starts with  k, v = torch.cat([kvs[0], kvx[0]], 2), torch.cat([kvs[1], kvx[1]], 2)  at every round and every block, where kvs is the memory K/V (the tape's, kvt, computed
once per tape; for G2f there are no slots) and kvx the prompt's K/V (computed once per micro-batch). In a teacher-forced micro-batch both are the same tensor objects for every round, so the
17 concatenations of a block are the same values. This variant builds them once per block and hands the same k, v to every round.

KEY. The first idea, "the identity of kvs[0], kvs[1], kvx[0], kvx[1]", cannot work: indexing a tensor makes a NEW view object each time (probe: ids differ on every call). The identity that
IS stable across rounds is the identity of the two parent tensors kvs and kvx ([2, B, heads, keys, dk], what Tool.think passes as ks / kx). The key is therefore (kvs is, kvx is) plus their
`_version` counters (an in-place write to either invalidates) plus (grad enabled, autocast flags) at the call. One entry per block, strong references to the last key only. A free run, where
kvt is rebuilt after a call (new tensors), misses and replaces the entry; the old tensors are held until then, so a freed tensor's address can never be mistaken for a new one.

SCOPE. The entry points loss, run, talk, loop, trace_loss (those the model has) are wrapped: the cache is cleared when each returns or raises (and when it starts), so nothing outlives the
micro-batch it was made for, and teardown() clears it too. Inside the autograd engine (torch._C._current_graph_task_id() != -1: the non-reentrant checkpoint of ToolH1.think recomputes the
block forward there, for rounds t >= n_loops) the cache is NOT consulted and nothing is stored: the recompute makes its own plain torch.cat, as the original does (the saved tensors the
checkpoint compares are the same shapes, dtypes and counts either way: a cat saves no tensor). stats() counts hits, misses, bypasses.

WHY IT SHOULD BE BIT-EXACT. Forward: a cat is a copy; the same inputs give the same bytes, and every round's SDPA gets a tensor with the same values, shape and strides (contiguous) as before.
Backward: the original's 17 per-round gradient slices (grad_k of each round, narrowed out of that round's cat-backward, then select_backward'ed into a zero 5-D tensor, then accumulated) are,
element for element, the same additions in the same (reverse-round) order as accumulating the 17 full grad_k tensors in the ONE cached cat's gradient and splitting once: each element is
the sum over rounds of that element's gradient, added in the same order; the zeros that select_backward pads with add exactly (x + 0 = x). test_exact_arms.py checks this (fp32, bf16 autocast).

WHAT IT DOES NOT DO: it does not change the SDPA, the masks, the reader, or anything else. Memory (suggested, not measured): the saved tensors of the SDPA calls of a block now share ONE k and
ONE v instead of one pair per non-checkpointed round, so the forward should hold less; the backward builds one full-size gradient for the cat instead of per-round zero-padded ones.

----------------------------------------------------------------------------------------------------------------------------------------------------------------------
fastteach
----------------------------------------------------------------------------------------------------------------------------------------------------------------------
B3G2.answer_teacher(Z, ids) = ByteWriter.teacher(ids, cids, cmask, WCAP, BOS, EOS) over line_context(Z): cids zeros [B, 1], cmask all False [B, 1] (made on the device), so teacher
(1) reads both back with .cpu() (two syncs on CUDA), (2) runs a per-row, per-target-byte python loop of small CPU tensor ops (select, eq, and, any) that can never hit (cmask is all False), so
fb is all zero, and (3) copies inp, tgt, fb, over to the device with four blocking .to(dev). With writer.copy False (G2f) the writer ignores fb (ByteWriter.run: fbs None; head: no copy path).
Called once per round t >= 1 of the loop and once for the answers: about 17 times per micro-batch on the real pool.

The variant replaces answer_teacher on the model instance ONLY when model.writer.copy is False (else Skip), with: teacher_np (a vectorised numpy build of inp, tgt, over; fb never built on the
host), inp / tgt / over to the device through prof_train.to_device_async (pinned + non_blocking on CUDA, plain .to on the CPU), fb = torch.zeros(B, L, 1, device=dev) (a device fill, no
host-to-device copy). No device read. The context width is 1 by line_context's definition (its source hash is checked, as is answer_teacher's and ByteWriter.teacher's: another source is a
Skip, never a guess).

Exactness by construction: teacher_np follows teacher's rules line for line (ok = target not None and len + 1 <= cap; over = target not None and len + 1 > cap; L = the longest ok row + 1, at
least 1; inp = BOS then the target then EOS fill; tgt = the target then EOS then -100; a not-ok row: inp BOS then EOS fill, tgt all -100), and fb is zero because cmask is all False; the test
asserts torch.equal (and dtype, shape) of all four tensors against the real ByteWriter.teacher for thousands of random target lists.

Composes with nosync (which also replaces answer_teacher: the later setup wins, and teardown restores in reverse) and kvcat (both shown equal together). With defer it is a no-op: defer's deferred _loss builds its own
teacher_np and calls answer_teacher only on its fallback path (untested together).

CUDA side effect (suggested, untested): fastteach also skips line_context's three device zeros (Xc, cmask, cids) and adds one device fill (fb): about 2 fewer fill launches, 1 fewer host-to-device copy (4 blocking -> 3
non-blocking) and 2 fewer device-to-host copies per call. The ~10,000 ATen ops it removes on the CPU run are almost all ops on HOST tensors (the per-byte loop): on CUDA they are CPU time, not launches.

HOST TIME OF fastteach on the CPU is a LOWER bound for the box: prof_train.to_device_async is a plain .to there, so the pinned staging, the 3 cudaMemcpyAsync calls and the one fill launch it adds per call on CUDA are not in
the measured time (the saving is an upper bound).

WHAT IS MEASURED HERE: CPU, fp32 (and a bf16-autocast kvcat check): values, ATen dispatches, host-sync call sites per micro-batch (test_exact_arms.py). WHAT IS NOT: any CUDA time, launches
or memory, the GPU kernel selection for the cached cat, bf16 on CUDA.
"""
import hashlib, inspect, os, sys, types
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
PROFDIR = os.path.normpath(os.path.join(HERE, '..', 'prof'))
if PROFDIR not in sys.path:
    sys.path.insert(0, PROFDIR)
import prof_train as prof                                                    # noqa: E402

COMMIT = '74d6e92c75'
# sha1 (first 12 hex) of each original source this file replaces or relies on, trailing blanks stripped (same recipe as defer.py). Another source: Skip.
SRC_HASH = dict(CBlock_forward='98a4ea944325', answer_teacher='a33b2f2ef2b7', line_context='ee62580e169e', teacher='c6d7f0df92ca')
CAT_LINE = 'k, v = torch.cat([kvs[0], kvx[0]], 2), torch.cat([kvs[1], kvx[1]], 2)'
ENTRY_POINTS = ('loss', 'run', 'talk', 'loop', 'trace_loss')


def src_hash(fn):
    return hashlib.sha1('\n'.join(ln.rstrip() for ln in inspect.getsource(inspect.unwrap(fn)).splitlines()).encode()).hexdigest()[:12]


def check_src(name, fn):
    got = src_hash(fn)
    if got != SRC_HASH[name]:
        raise prof.Skip(f'{name}: source hash {got}, written against {SRC_HASH[name]} ({COMMIT}): this is not the custom_io this arm was written against')


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# kvcat
# ------------------------------------------------------------------------------------------------------------------------------------------------------
def _parts(x):
    """The tensors a K/V argument is made of (a tensor [2, ...] is itself; a pair/list is its elements) and their in-place version counters."""
    xs = (x,) if torch.is_tensor(x) else tuple(x)
    return xs, tuple(getattr(e, '_version', None) for e in xs)


class KvCat(prof.Variant):
    name = 'kvcat'
    ab_cpu_rule = 'bit_exact'
    doc = ('CANDIDATE-EXACT (launch-bound study): ledger.CBlock.forward concatenates [memory K/V; prompt K/V] along the key axis at every round and block although, in a teacher-forced '
           'micro-batch, both are the same tensor objects every round. The concatenation is made once per block and reused (key: the identity of the parent tensors kvs and kvx, their '
           'in-place version counters, grad / autocast state; strong references to the last key only); a free run, where the tape K/V is rebuilt after a call, misses and rebuilds. The '
           'cache is cleared when loss / run / talk / loop / trace_loss return or raise, and is neither read nor written inside the autograd engine (the non-reentrant checkpoint of '
           'ToolH1.think recomputes the block there for rounds t >= n_loops). Forward and backward are expected bit-identical: the per-round gradient slices are summed into the one '
           'cached cat\'s gradient in the same order and split once. GPU effect: fewer CatArrayBatchedCopy launches and less GPU time, NOT fewer rounds; untested on CUDA.')

    def setup(self):
        tr = self.tr
        m = tr.model
        if type(m).__name__ != 'B3G2' or getattr(m, 'writer', None) is None:
            raise prof.Skip(f'kvcat: tested on the B3G2 model only (this one is {type(m).__name__}); B3, Tool and ToolH1 arms have the same cat but nothing here shows the arm exact there')
        core = getattr(m, 'core', None)
        if core is None or not len(core) or not all(callable(getattr(b, 'kv_of', None)) for b in core) or not callable(getattr(m, 'think', None)):
            raise prof.Skip('kvcat: needs a model with a core of CBlocks (B3G2)')
        cls = type(core[0])
        check_src('CBlock_forward', cls.forward)
        self.undo, self.cache = [], {}
        self.hits = self.misses = self.bypass = self.clears = 0
        fwd = prof.patched_fn(cls.forward, [(CAT_LINE, 'k, v = self._kvcat_get(kvs, kvx)')])
        for b in core:
            prof.set_attr(b, '_kvcat_get', self._getter(b), self.undo)
            prof.set_attr(b, 'forward', types.MethodType(fwd, b), self.undo)
        for name in ENTRY_POINTS:
            if callable(getattr(m, name, None)):
                prof.set_attr(m, name, self._scoped(getattr(m, name)), self.undo)

    def teardown(self):
        prof.undo_attrs(getattr(self, 'undo', []))
        self.cache = {}

    def _scoped(self, fn):
        def scoped(*a, **kw):
            self.cache.clear()
            try:
                return fn(*a, **kw)
            finally:
                if self.cache:
                    self.clears += 1
                self.cache.clear()                                           # nothing outlives the call it was made in
        scoped.__name__ = getattr(fn, '__name__', 'scoped')
        scoped.__wrapped_by_kvcat__ = fn
        return scoped

    def _getter(self, blk):
        key = id(blk)

        def get(kvs, kvx):
            if torch._C._current_graph_task_id() != -1:                     # inside backward: the checkpoint's recompute (or any hook): plain cat, no cache
                self.bypass += 1
                return torch.cat([kvs[0], kvx[0]], 2), torch.cat([kvs[1], kvx[1]], 2)
            ps, vs = _parts(kvs)
            px, vx = _parts(kvx)
            flags = (torch.is_grad_enabled(), torch.is_autocast_enabled('cpu'), torch.is_autocast_enabled('cuda'))
            e = self.cache.get(key)
            if e is not None and e[3] == flags and e[2] == (vs, vx) and len(e[0]) == len(ps) and len(e[1]) == len(px) \
                    and all(a is b for a, b in zip(e[0], ps)) and all(a is b for a, b in zip(e[1], px)):
                self.hits += 1
                return e[4], e[5]
            self.misses += 1
            k, v = torch.cat([kvs[0], kvx[0]], 2), torch.cat([kvs[1], kvx[1]], 2)
            self.cache[key] = (ps, px, (vs, vx), flags, k, v)         # strong references to the key's tensors and to the result; replaced on the next miss
            return k, v
        return get

    def stats(self):
        return dict(cat_cache_hits=self.hits, cat_cache_misses=self.misses, cat_cache_bypassed_in_backward=self.bypass, entries_cleared_at_call_end=self.clears,
                    exact='intended bit-exact (fp32 CPU, 1 thread: shown by test_exact_arms.py); CUDA and bf16-on-CUDA untested')


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# fastteach
# ------------------------------------------------------------------------------------------------------------------------------------------------------
def teacher_np(targets, cap, bos, eos, pad=-100):
    """ByteWriter.teacher without its feedback and without torch, for a context in which no position is visible (cmask all False): -> dict of numpy arrays inp [B, L] int64,
    tgt [B, L] int64, over [B] bool. The rules are the original's: ok = target is not None and len + 1 <= cap; over = target is not None and len + 1 > cap; L = the longest ok row + 1 (at
    least 1); row b ok: inp = BOS, target, then EOS fill; tgt = target, EOS, then pad; not ok: inp = BOS then EOS fill, tgt all pad. No loop over bytes: one python pass over the rows
    for the lengths, then numpy indexing."""
    B = len(targets)
    n = np.fromiter((len(t) if (t is not None and len(t) + 1 <= cap) else -1 for t in targets), dtype=np.int64, count=B)
    over = np.fromiter((t is not None and len(t) + 1 > cap for t in targets), dtype=np.bool_, count=B)
    ok = n >= 0
    L = int(n.max()) + 1 if ok.any() else 1
    inp = np.full((B, L), eos, dtype=np.int64)
    tgt = np.full((B, L), pad, dtype=np.int64)
    inp[:, 0] = bos
    cnt = np.where(ok, n, 0)
    tot = int(cnt.sum())
    if tot:
        flat = np.fromiter((x for t, o, c in zip(targets, ok, cnt) if c for x in t), dtype=np.int64, count=tot)
        rows = np.repeat(np.arange(B), cnt)
        cols = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        inp[rows, cols + 1] = flat
        tgt[rows, cols] = flat
    idx = np.nonzero(ok)[0]
    tgt[idx, n[idx]] = eos
    return dict(inp=inp, tgt=tgt, over=over)


class FastTeach(prof.Variant):
    name = 'fastteach'
    ab_cpu_rule = 'bit_exact'
    doc = ('CANDIDATE-EXACT (launch-bound study), B3G2 with a writer that has no copy path (G2f): B3G2.answer_teacher is ByteWriter.teacher over line_context\'s zeros (cids zeros, cmask all '
           'False, one position), so its per-row, per-byte python loop of small CPU tensor ops can never hit and fb is all zero, yet it reads cids / cmask back with .cpu() (2 syncs on CUDA) '
           'and copies four tensors with blocking .to(dev). Replaced (on the model instance, only when writer.copy is False) by a vectorised numpy build of inp / tgt / over, fb = zeros '
           '[B, L, 1] made on the device, inp / tgt / over to the device pinned + non_blocking (plain on the CPU). No device read, no host loop over bytes. Exact by construction; the test '
           'asserts torch.equal of all four tensors against the real ByteWriter.teacher. GPU effect: host CPU time and 6 syncs per call (about 17 calls per micro-batch), not GPU time; untested on CUDA.')

    def setup(self):
        tr = self.tr
        m = tr.model
        wr = getattr(m, 'writer', None)
        if wr is None or not all(callable(getattr(m, n, None)) for n in ('answer_teacher', 'line_context')):
            raise prof.Skip('fastteach: needs the B3G2 writer (arm B3G2)')
        if getattr(wr, 'copy', True):
            raise prof.Skip('fastteach: the writer has a copy path, so the feedback fb is not zero: not applicable')
        cls = type(m)
        check_src('answer_teacher', cls.answer_teacher)
        check_src('line_context', cls.line_context)
        check_src('teacher', type(wr).teacher)
        g = cls.answer_teacher.__globals__
        bos, eos = g['BOS'], g['EOS']
        self.undo, self.calls = [], 0

        def answer_teacher(Z, ids):
            self.calls += 1
            te = teacher_np(ids, m.WCAP, bos, eos)
            dev = Z.device
            B, L = te['inp'].shape
            return dict(inp=prof.to_device_async(torch.from_numpy(te['inp']), dev), tgt=prof.to_device_async(torch.from_numpy(te['tgt']), dev),
                        fb=torch.zeros(B, L, 1, device=dev), over=prof.to_device_async(torch.from_numpy(te['over']), dev))
        prof.set_attr(m, 'answer_teacher', answer_teacher, self.undo)

    def teardown(self):
        prof.undo_attrs(getattr(self, 'undo', []))

    def stats(self):
        return dict(teacher_calls_numpy=self.calls, exact='by construction; asserted tensor-for-tensor against ByteWriter.teacher by test_exact_arms.py')


NEW_VARIANTS = [KvCat, FastTeach]
