#!/usr/bin/env python3
"""Adapter for the sealed few-example harness; no data generation or scoring.

Environment: CLAUDE_PATCH_CORE=patch|loop, CLAUDE_PATCH_INIT=pre|fresh,
CLAUDE_PATCH_DEVICE=auto|cpu|mps|cuda; optional CLAUDE_PATCH_TELEMETRY=JSONL path.
Optional CLAUDE_PATCH_RAW_PREDICTIONS=.jsonl.gz audit log requires
CLAUDE_PATCH_FIXED_DEPTH=1 for plain or 8/16/32/48 for recurrent models.
Net('plain') always uses the sealed
patch project's plain core. Device selection is the declared hardware addendum.

Call reset_adapt_sequence() before each adapt_job in a reused process. The seven
Learner creation ordinals name harness phases, never puzzle kinds. Export describe()
and audit_records() alongside harness JSON. Import/source export does not consume
an ordinal. No example memory is retained by this module.
"""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
import hashlib
import gzip
import itertools
import json
import math
import os
from pathlib import Path
import random
import sys
import time

import torch
from torch import nn
from torch.nn import functional as F

try:
    from . import claude_patch_net as C
except ImportError:
    import claude_patch_net as C

TRAIN_ROUNDS, GRAD_ROUNDS, MAX_ROUNDS = 16, 6, 48
SLEEP_STEPS, UPDATES = 512, 4
PHASES = ('few1', 'few4', 'few16', 'few64', 'sleep64', 'stream', 'sleep64k')
HOLDOUT_PHASES = ('k0', 'k1', 'k4', 'k16', 'k64', 'k256', 'k1024', 'k4096',
                  'k16384', 'k65536', 'sleep64', 'sleep64k')
_next_ordinal = 0
_sequence = 0
_audit = []
_event_hook = None
_model_ids = itertools.count(1)


def set_event_hook(callback):
    """Optional callback(event_dict); events contain configuration/counters, no puzzles."""
    global _event_hook
    _event_hook = callback


def _emit(event):
    path = os.environ.get('CLAUDE_PATCH_TELEMETRY')
    if path:
        destination = Path(path).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(event, sort_keys=True) + '\n')
    if _event_hook is not None:
        _event_hook(event)


def reset_adapt_sequence():
    """Explicit parent boundary between adapt_job calls; no silent phase rollover."""
    global _next_ordinal, _sequence
    _next_ordinal = 0
    _sequence += 1


def audit_records():
    """JSON-ready snapshots of controller phases and their evolving work counters."""
    return [{**r, 'counters': dict(r['counters'])} for r in _audit]


def recursive_python_bytes(root):
    """sys.getsizeof object graph, deduplicated by identity within this root.

    Includes dict keys/values, containers, instance dictionaries and inherited
    slots. Excludes allocator overhead and external/native allocations.
    """
    visited = set()

    def visit(obj):
        identity = id(obj)
        if identity in visited:
            return 0
        visited.add(identity)
        size = sys.getsizeof(obj)
        if isinstance(obj, dict):
            size += sum(visit(k) + visit(v) for k, v in obj.items())
        elif isinstance(obj, (list, tuple, set, frozenset)):
            size += sum(visit(v) for v in obj)
        if hasattr(obj, '__dict__'):
            size += visit(vars(obj))
        for cls in type(obj).__mro__:
            slots = cls.__dict__.get('__slots__', ())
            if isinstance(slots, str):
                slots = (slots,)
            for name in slots:
                if name in ('__dict__', '__weakref__'):
                    continue
                if name.startswith('__') and not name.endswith('__'):
                    name = '_' + cls.__name__.lstrip('_') + name
                if hasattr(obj, name):
                    size += visit(getattr(obj, name))
        return size

    return visit(root)


def replay_memory(net, old_replay, branch):
    """Measure the supplied stores; no generation, model execution or retained copy."""
    def packed(items):
        return sum(sum(len(row) for row in it.tokens) * 3 * 8 for it in items)

    old_count = sum(len(items) for items in old_replay.values())
    old_packed = sum(packed(items) for items in old_replay.values())
    branch_packed = packed(branch)
    shapes = {(len(it.tokens), len(it.tokens[0])) for it in branch}
    working = {f'{h}x{w}': 32*h*w*net.core.width*4 for h, w in sorted(shapes)}
    return dict(old_example_count=old_count, expected_locked_old_example_count=256,
                branch_count=len(branch), packed_tensor_bytes=old_packed+branch_packed,
                old_packed_tensor_bytes=old_packed, branch_packed_tensor_bytes=branch_packed,
                packed_tensor_bytes_definition='tokens + slot + target, int64: sum(H*W*3*8); excludes metadata',
                old_python_objectgraph_bytes=recursive_python_bytes(old_replay),
                branch_python_objectgraph_bytes=recursive_python_bytes(branch),
                python_bytes_definition='recursive sys.getsizeof, visited identities per store; includes metadata; excludes allocator overhead and external/native allocations; stores measured separately',
                working_state_bytes=max(working.values(), default=0),
                working_state_bytes_by_shape=working,
                working_state_definition='one fp32 branch hidden-state tensor: 32*H*W*d*4; maximum shape reported; excludes other activations',
                fast_state_bytes=16384 if net.is_patch else 0,
                fast_state_definition='persistent A/B fp32 buffers only, separate from replay and working state',
                peak_training_memory='not measured')


def _device():
    requested = os.environ.get('CLAUDE_PATCH_DEVICE', 'auto')
    if requested not in ('auto', 'cpu', 'mps', 'cuda'):
        raise ValueError('CLAUDE_PATCH_DEVICE must be auto, cpu, mps, or cuda')
    if requested == 'auto':
        requested = 'cuda' if torch.cuda.is_available() else (
            'mps' if torch.backends.mps.is_available() else 'cpu')
    return torch.device(requested)


def _stats():
    return dict(writes=0, differentiable_writes=0, support_predictions=0,
                support_rounds=0, optimizer_steps=0, forward_round_examples=0,
                gradient_round_examples=0, forward_macs_estimate=0,
                training_matrix_macs=0, inference_matrix_macs=0,
                inference_seconds=0., training_seconds=0., support_seconds=0.,
                sleep_examples=0, sleep_sums=0, sleep_grids=0, sleep_branch=0)


def describe(net=None):
    result = dict(
        environment={k: v for k, v in os.environ.items() if k.startswith('CLAUDE_PATCH_')},
        default_environment=dict(CLAUDE_PATCH_CORE='patch', CLAUDE_PATCH_INIT='pre',
                                 CLAUDE_PATCH_DEVICE='auto'),
        torch=torch.__version__, dtype='float32', autocast=False,
        phase_order=list(PHASES), next_learner_ordinal=_next_ordinal, sequence=_sequence,
        telemetry='controller creation/batch/sleep snapshots, sleep-entry replay_memory, and per-inference-batch deltas; cumulative totals span this process',
        telemetry_aggregation='sum seconds_delta and forward_macs_delta only on inference_batch events; do not add cumulative snapshots',
        timing_accounting='training_seconds includes support_seconds; support_seconds is a breakdown, not an additional cost',
        raw_predictions=dict(path_env='CLAUDE_PATCH_RAW_PREDICTIONS', format='gzip append JSONL, one row per puzzle',
                             fixed_depth_env='CLAUDE_PATCH_FIXED_DEPTH',
                             fixed_depth='required when logging; 1 for plain, otherwise 8/16/32/48',
                             predictions='flattened row-major; selected_pred and fixed_pred; no targets',
                             model_id='process-local increasing construction ID; deepcopy retains ID; not loaded from checkpoints',
                             phase='CLAUDE_PATCH_COMMAND=adapt starts k0; holdout maps construction IDs 1..12 to holdout_phase_order in a fresh process; unset command is unassigned',
                             holdout_phase_order=list(HOLDOUT_PHASES),
                             timing='selection, CPU transfer, serialization and gzip I/O occur after inference timing'),
        adaptation=dict(updates_per_batch=4, free_rounds=3, grad_rounds=2,
                        optimizer_warmup='50 updates: min(1, (i+1)/50); scheduler after optimizer',
                        carry_detached_state=True, stop_loss=False,
                        pre_patch_few='writer only; ordinary weights frozen',
                        pre_patch_stream='sequential corrected writes then four ordinary updates',
                        fresh_patch='zero patch; ordinary core gradients only; writer never called'),
        sleep=dict(updates=512, sums=4, grids=4, branch_examples=8,
                   optimizer_warmup_updates=50, replay_rng_seed='9262700 + seed',
                   round_rng_seed='9282700 + seed',
                   loss_weights=[.25, .25, .5], stop_loss=False,
                   patch='fixed during sleep; zeroed only after update 512'),
        gradient_check_recipe=dict(support_items=2, query_items='remaining, distinct from supports',
                                   query_rounds='random 2..16 for patch; 1..16 for controls',
                                   support_depth='own learned halt, minimum 3, cap 48',
                                   grad_rounds='last 1..6; last two writes'),
        raw_example_memory_bytes=0,
        raw_example_memory_note='module retains no replay; replay_memory events measure caller-owned stores at sleep entry',
        operations='forward MAC estimate only; gradient round examples and optimizer steps counted separately; no backward FLOP claim',
        fixed_depth='parent selects 8/16/32/48 on old dev; infer_rounds preserves every depth',
        hashes={Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                for p in (__file__, C.__file__)})
    if net is not None:
        result.update(arm=net.arm, core=net.core.arm, init=net.init,
                      model_id=net.model_id, phase=net.phase,
                      environment_at_creation=dict(net.environment),
                      device=str(net.device), weights=net.weight_count(),
                      ordinary_parameters=sum(p.numel() for p in net.parameters()),
                      patch_coefficients=4096 if net.is_patch else 0,
                      counters=dict(net.counters))
    return result


def tensors(items, device=None):
    """CPU by default for the locked harness; training explicitly supplies net.device."""
    return tuple(torch.tensor([getattr(it, name) for it in items], dtype=torch.long,
                              device=device) for name in ('tokens', 'slot', 'target'))


def ce_and_exact(logits, s, y):
    s = s.to(logits.device).reshape(s.shape[0], -1).bool()
    y = y.to(logits.device).reshape(y.shape[0], -1)
    ce = F.cross_entropy(logits.float()[s], y[s])
    exact = ((logits.argmax(-1) == y) | ~s).all(1).float()
    return ce, exact


class Net(nn.Module):
    def __init__(self, arm):
        super().__init__()
        if arm not in ('loop', 'plain'):
            raise ValueError("harness arm must be 'loop' or 'plain'")
        chosen = os.environ.get('CLAUDE_PATCH_CORE', 'patch')
        self.init = os.environ.get('CLAUDE_PATCH_INIT', 'pre')
        if chosen not in ('patch', 'loop') or self.init not in ('pre', 'fresh'):
            raise ValueError('invalid CLAUDE_PATCH_CORE or CLAUDE_PATCH_INIT')
        self.arm = arm
        self._raw_settings()
        command = os.environ.get('CLAUDE_PATCH_COMMAND')
        if command not in (None, 'adapt', 'holdout'):
            raise ValueError('CLAUDE_PATCH_COMMAND must be adapt or holdout when set')
        self.model_id = next(_model_ids)
        if command == 'holdout':
            if not 1 <= self.model_id <= len(HOLDOUT_PHASES):
                raise RuntimeError('holdout requires a fresh process and exactly 12 Net constructions')
            self.phase = HOLDOUT_PHASES[self.model_id - 1]
        else:
            self.phase = 'k0' if command == 'adapt' else 'unassigned'
        self.environment = {k: v for k, v in os.environ.items() if k.startswith('CLAUDE_PATCH_')}
        self.core = C.Net('plain' if arm == 'plain' else chosen)
        self.is_patch = self.core.arm == 'patch'
        if self.is_patch:
            self.register_buffer('patch_A', torch.zeros(1, C.RANK, C.WIDTH))
            self.register_buffer('patch_B', torch.zeros(1, C.WIDTH, C.RANK))
        self.counters = _stats()
        self.to(device=_device(), dtype=torch.float32)
        if self.is_patch and self.init == 'fresh':
            self._freeze_writer()

    @property
    def device(self):
        return self.core.tok.weight.device

    def _sync(self):
        if self.device.type == 'mps':
            torch.mps.synchronize()
        elif self.device.type == 'cuda':
            torch.cuda.synchronize(self.device)

    @contextmanager
    def measured(self, name):
        self._sync()
        started = time.perf_counter()
        try:
            with torch.autocast(device_type=self.device.type, enabled=False):
                yield
        finally:
            self._sync()
            self.counters[name] += time.perf_counter() - started

    def _freeze_writer(self):
        for name, parameter in self.core.named_parameters():
            if name.startswith(('writer.', 'rank_slot.', 'gate.')):
                parameter.requires_grad_(False)

    def _raw_settings(self, rounds=None):
        path = os.environ.get('CLAUDE_PATCH_RAW_PREDICTIONS')
        value = os.environ.get('CLAUDE_PATCH_FIXED_DEPTH')
        allowed = (1,) if self.arm == 'plain' else (8, 16, 32, 48)
        if value is None:
            if path:
                raise ValueError('CLAUDE_PATCH_FIXED_DEPTH is required for raw prediction logging')
            depth = allowed[-1]
        else:
            try:
                depth = int(value)
            except ValueError as exc:
                raise ValueError('CLAUDE_PATCH_FIXED_DEPTH must be an integer') from exc
            if depth not in allowed:
                raise ValueError(f'CLAUDE_PATCH_FIXED_DEPTH must be one of {allowed} for {self.arm}')
        if path and not path.endswith('.jsonl.gz'):
            raise ValueError('CLAUDE_PATCH_RAW_PREDICTIONS must end in .jsonl.gz')
        if path and rounds is not None and depth > rounds:
            raise ValueError('requested inference rounds do not include the logged fixed depth')
        return path, depth

    def _log_predictions(self, settings, tokens, slot, predictions, stops):
        """Audit output only: no targets accepted, no scoring, no model re-execution."""
        path, fixed_depth = settings
        if not path:
            return
        # All transfers/selection/serialization are outside the model timing context.
        inputs, slots = tokens.detach().cpu().tolist(), slot.detach().cpu().tolist()
        ps = predictions.detach().cpu().tolist()
        qs = stops.detach().cpu().tolist() if stops is not None else None
        destination = Path(path).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(destination, 'at', encoding='utf-8') as handle:
            for i, p in enumerate(ps):
                depth = 1 if self.arm == 'plain' else next(
                    (r+1 for r in range(2, len(p)) if qs[i][r] > .5
                     and p[r] == p[r-1] == p[r-2]), len(p))
                row = dict(tokens=inputs[i], slot=slots[i], selected_pred=p[depth-1],
                           fixed_pred=p[fixed_depth-1], chosen_round=depth,
                           fixed_depth=fixed_depth, inference_rounds=1 if self.arm == 'plain' else len(p),
                           core=self.core.arm, init=self.init, model_id=self.model_id, phase=self.phase)
                handle.write(json.dumps(row, separators=(',', ':')) + '\n')

    @contextmanager
    def _inference_batch(self, batch_size, rounds):
        """Emit additive deltas after GPU synchronization, excluding telemetry I/O.

        These events work without a Learner, including holdout and post-sleep
        scoring. Sum their deltas, never the cumulative controller snapshots.
        training_seconds elsewhere already includes support_seconds.
        """
        seconds_before = self.counters['inference_seconds']
        macs_before = self.counters['inference_matrix_macs']
        with self.measured('inference_seconds'):
            yield
        _emit(dict(event='inference_batch',
                   seconds_delta=self.counters['inference_seconds'] - seconds_before,
                   forward_macs_delta=self.counters['inference_matrix_macs'] - macs_before,
                   batch_size=int(batch_size), rounds=int(rounds),
                   core=self.core.arm, init=self.init, device=str(self.device),
                   model_id=self.model_id, phase=self.phase))

    def weight_count(self):
        return sum(p.numel() for p in self.parameters()) + (4096 if self.is_patch else 0)

    def describe(self):
        return describe(self)

    def load_core_state(self, state):
        """Parent exports a sealed source core without renaming keys by hand."""
        self.core.load_state_dict(state, strict=True)
        self.remove_patch()

    def patch(self):
        if not self.is_patch or self.init == 'fresh':
            return None
        return C.PatchState(self.patch_A, self.patch_B)

    @property
    def patch_state(self):
        """Explicit stored state, including the zero state of a fresh patch arm."""
        return C.PatchState(self.patch_A, self.patch_B) if self.is_patch else None

    @torch.no_grad()
    def set_patch(self, state):
        """Copy a PatchState/(A,B)/{'A': A, 'B': B} onto the actual net device."""
        if state is None:
            self.remove_patch()
            return
        if not self.is_patch:
            raise ValueError('a loop/plain control cannot receive patch state')
        a, b = (state['A'], state['B']) if isinstance(state, dict) else state
        state = C.PatchState(a.detach().to(self.device, torch.float32), b.detach().to(self.device, torch.float32))
        if any(not bool(torch.isfinite(x).all()) or bool((x.abs() > C.SLOT_LIMIT + 1e-6).any()) for x in state):
            raise ValueError('patch state must be finite and obey the sealed factor bound')
        if self.init == 'fresh' and any(bool(torch.count_nonzero(x)) for x in state):
            raise ValueError('fresh patch arms must retain a zero patch')
        self._store_patch(state)

    @torch.no_grad()
    def remove_patch(self):
        if self.is_patch:
            self.patch_A.zero_()
            self.patch_B.zero_()

    @torch.no_grad()
    def _store_patch(self, patch):
        if patch.A.shape != self.patch_A.shape or patch.B.shape != self.patch_B.shape:
            raise ValueError('persistent patch must have batch size one')
        self.patch_A.copy_(patch.A.detach())
        self.patch_B.copy_(patch.B.detach())

    def _work(self, tokens, rounds, grad_rounds=0, *, reads=None, inference=False):
        b, h, w = tokens.shape
        t, d = h * w, self.core.width
        layers = len(self.core.blocks)
        m = self.core.blocks[0].mlp[0].out_features
        reads = rounds if reads is None else reads
        mac = b * rounds * layers * (t * (4*d*d + 2*d*m) + 2*t*t*d)
        mac += b * reads * (t*d*C.E.VOCAB + (d if self.arm != 'plain' else 0))
        if self.is_patch and self.init == 'pre':
            mac += b * rounds * t * (2*d*C.RANK + 2*d)
        self.counters['forward_macs_estimate'] += mac
        self.counters['inference_matrix_macs' if inference else 'training_matrix_macs'] += mac
        self.counters['forward_round_examples'] += b * rounds
        self.counters['gradient_round_examples'] += b * grad_rounds

    def plain_forward(self, tokens, slot):
        inference = not torch.is_grad_enabled()
        settings = self._raw_settings(1) if inference else None
        with self._inference_batch(tokens.shape[0], 1) if inference else nullcontext():
            tokens, slot = tokens.to(self.device), slot.to(self.device)
            self._work(tokens, 1, int(torch.is_grad_enabled()), inference=not torch.is_grad_enabled())
            logits = self.core.plain_forward(tokens, slot)
        if inference and settings[0]:
            self._log_predictions(settings, tokens, slot, logits.argmax(-1)[:, None, :], None)
        return logits

    def loop_train(self, tokens, slot, n_free, n_grad):
        tokens, slot = tokens.to(self.device), slot.to(self.device)
        self._work(tokens, n_free + n_grad, n_grad, reads=n_grad)
        return self.core.loop_train(tokens, slot, n_free, n_grad, self.patch())

    def forward(self, tokens, positions):
        if self.arm == 'plain' and not torch.is_grad_enabled():
            # plain_forward owns the timing/event; avoid a nested timer or duplicate event.
            return [self.plain_forward(tokens, positions)], []
        with self.measured('training_seconds' if torch.is_grad_enabled() else 'inference_seconds'):
            if self.arm == 'plain':
                return [self.plain_forward(tokens, positions)], []
            tokens, positions = tokens.to(self.device), positions.to(self.device)
            self._work(tokens, 48, 48 if torch.is_grad_enabled() else 0, inference=not torch.is_grad_enabled())
            e, (dr, dc) = self.core.embed(tokens, positions)
            h = torch.zeros_like(e)
            cells, stops = [], []
            patch = self.patch()
            for _ in range(48):
                h = self.core.step(h, e, dr, dc, patch)
                lg, q = self.core.read(h)
                cells.append(lg)
                stops.append(q)
            return cells, stops

    @torch.no_grad()
    def infer_rounds(self, tokens, positions, n=48):
        # Do not early-exit here: the harness needs true source-selected fixed-depth scores.
        if not 1 <= n <= 48:
            raise ValueError('n must be 1..48')
        settings = self._raw_settings(1 if self.arm == 'plain' else n)
        with self._inference_batch(tokens.shape[0], 1 if self.arm == 'plain' else n):
            tokens, positions = tokens.to(self.device), positions.to(self.device)
            self._work(tokens, 1 if self.arm == 'plain' else n, inference=True)
            predictions, stops = self.core.loop_rounds(tokens, positions, n, self.patch())
        self._log_predictions(settings, tokens, positions, predictions, stops)
        return predictions, stops

    loop_rounds = infer_rounds

    @torch.no_grad()
    def _support_answer(self, t, s, patch):
        """One support's own answer; no correction is available while selecting depth."""
        if t.shape[0] != 1:
            raise ValueError('supports must be processed one by one')
        e, (dr, dc) = self.core.embed(t, s)
        h = torch.zeros_like(e)
        previous = []
        for depth in range(1, 49):
            h = self.core.step(h, e, dr, dc, patch)
            lg, q = self.core.read(h)
            pred = lg.argmax(-1)
            previous.append(pred)
            previous = previous[-3:]
            if (depth >= 3 and bool(q.sigmoid().item() > .5)
                    and torch.equal(previous[0], previous[1]) and torch.equal(previous[1], previous[2])):
                break
        self._work(t, depth)
        self.counters['support_predictions'] += 1
        self.counters['support_rounds'] += depth
        return depth, h, lg

    def _proposal(self, h, logits, s, y, patch):
        """Exact sealed core write formula, reusing activations at the selected halt."""
        b, length, vocab = logits.shape
        mask = s.reshape(b, length).bool()
        target = torch.where(mask, y.reshape(b, length), 0).long()
        correction = (F.one_hot(target, vocab).to(logits.dtype) - logits.float().softmax(-1)) * mask.unsqueeze(-1)
        denom = mask.sum(1, keepdim=True).clamp_min(1)
        activity = (self.core.ln_out(h) * mask.unsqueeze(-1)).sum(1) / denom
        feedback = (correction @ self.core.head.weight).sum(1) / denom
        context = activity[:, None, :] + self.core.rank_slot.weight[None, :, :]
        features = torch.cat((context, feedback[:, None, :].expand(-1, C.RANK, -1)), -1)
        proposal = self.core.writer(features).tanh() * C.SLOT_LIMIT
        a, b_rows = proposal.split(C.WIDTH, -1)
        return C.PatchState((C.RHO * patch.A + (1-C.RHO)*a).clamp(-C.SLOT_LIMIT, C.SLOT_LIMIT),
                            (C.RHO * patch.B + (1-C.RHO)*b_rows.transpose(1, 2)).clamp(-C.SLOT_LIMIT, C.SLOT_LIMIT))

    def _write_cost(self, tokens):
        self.counters['writes'] += 1
        mac = C.RANK * 2 * (2*C.WIDTH) * (C.WIDTH//2) + tokens.numel()*C.E.VOCAB*C.WIDTH
        self.counters['forward_macs_estimate'] += mac
        self.counters['training_matrix_macs'] += mac

    @torch.no_grad()
    def write_supports(self, items):
        if not self.is_patch or self.init != 'pre':
            raise RuntimeError('only pretrained patch arms may invoke the writer')
        with self.measured('support_seconds'):
            for item in items:
                t, s, y = tensors([item], self.device)
                patch = self.patch()
                _, h, lg = self._support_answer(t, s, patch)
                self._store_patch(self._proposal(h, lg, s, y, patch))
                self._write_cost(t)


def train_loss(net, items, round_rng):
    """Harness/V2 loss. Patch learns only through different queries after two supports.

    Temporary differentiable writes never mutate checkpoint buffers. This is a
    smoke/source API, not the parent's sealed 18k+2k source-training orchestration.
    """
    with net.measured('training_seconds'):
        if net.arm == 'plain':
            t, s, y = tensors(items, net.device)
            return ce_and_exact(net.plain_forward(t, s), s, y)[0]
        patch = net.patch()
        use_writer = net.is_patch and net.init == 'pre'
        if use_writer:
            if len(items) < 3:
                raise ValueError('patch train_loss needs two supports and at least one different query')
            signature = lambda it: (tuple(map(tuple, it.tokens)), tuple(map(tuple, it.slot)))
            support_keys = {signature(it) for it in items[:2]}
            if any(signature(it) in support_keys for it in items[2:]):
                raise ValueError('support puzzle also appears among queries')
            patch = C.PatchState(patch.A.detach().clone(), patch.B.detach().clone())
            for item in items[:2]:
                t, s, y = tensors([item], net.device)
                depth, _, _ = net._support_answer(t, s, patch)
                grad = min(depth, GRAD_ROUNDS)
                patch = net.core.write_support(t, s, y, patch, depth-grad, grad)
                net._work(t, depth, grad, reads=grad)
                net._write_cost(t)
                net.counters['differentiable_writes'] += 1
            items = items[2:]
        t, s, y = tensors(items, net.device)
        total = round_rng.randint(2 if use_writer else 1, TRAIN_ROUNDS)
        grad = round_rng.randint(1, min(total, GRAD_ROUNDS))
        net._work(t, total, grad, reads=grad)
        outputs = net.core.loop_train(t, s, total-grad, grad, patch)
        losses = []
        for lg, q in outputs:
            ce, exact = ce_and_exact(lg, s, y)
            losses.append(ce + .5 * F.binary_cross_entropy_with_logits(q.float(), exact))
        return torch.stack(losses).mean()


class Practice:
    """Contract implementation; source experiment scheduling belongs to the parent."""
    def __init__(self, arm, seed, total_steps):
        torch.manual_seed(seed)
        self.net = Net(arm)
        self.opt = torch.optim.AdamW([p for p in self.net.parameters() if p.requires_grad],
                                    lr=1e-3, weight_decay=.1, betas=(.9, .95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(
            self.opt, lambda i: min(1., (i+1)/200) * .5 * (1+math.cos(math.pi*min(i, total_steps)/total_steps)))
        self.rng = random.Random(9000 + seed)

    def step(self, items):
        self.net.train()
        self.opt.zero_grad(set_to_none=True)
        loss = train_loss(self.net, items, self.rng)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.)
        self.opt.step()
        self.sched.step()
        self.net.counters['optimizer_steps'] += 1
        return loss.item()


class Learner:
    def __init__(self, net, lr):
        global _next_ordinal
        if not 0 <= _next_ordinal < len(PHASES):
            raise RuntimeError('expected seven Learners per adapt_job; call reset_adapt_sequence before another job')
        self.phase = PHASES[_next_ordinal]
        self.sequence = _sequence
        self.ordinal = _next_ordinal
        _next_ordinal += 1
        self.net, self.steps = net, 0
        self.stream_seen = 0
        net.phase = 'k0' if self.phase == 'stream' else self.phase
        self.net.counters = _stats()
        self.writer_only = net.is_patch and net.init == 'pre' and self.phase.startswith('few')
        for parameter in net.parameters():
            parameter.requires_grad_(not self.writer_only)
            parameter.grad = None
        if net.is_patch and net.init == 'fresh':
            net.remove_patch()
            net._freeze_writer()
        params = [p for p in net.parameters() if p.requires_grad]
        self.opt = torch.optim.AdamW(params, lr=lr, weight_decay=.1, betas=(.9, .95)) if params else None
        self.sched = (torch.optim.lr_scheduler.LambdaLR(self.opt, lambda i: min(1., (i+1)/50))
                      if self.opt is not None else None)
        record = dict(ordinal=self.ordinal, sequence=self.sequence, phase=self.phase, core=net.core.arm, init=net.init,
                      lr=lr, writer_only=self.writer_only, counters=net.counters)
        _audit.append(record)
        _emit({'event': 'learner_created', **record, 'config': net.describe()})

    def _report(self, event):
        cumulative = {key: sum(r['counters'][key] for r in _audit)
                      for key in ('writes', 'optimizer_steps', 'training_matrix_macs', 'inference_matrix_macs')}
        _emit(dict(event=event, phase=self.phase, ordinal=self.ordinal, sequence=self.sequence,
                   mode='writer_only' if self.writer_only else ('sleep' if self.phase.startswith('sleep') else 'ordinary_gradient'),
                   core=self.net.core.arm, init=self.net.init, steps=self.steps,
                   counters=dict(self.net.counters), cumulative=cumulative))

    def update(self, loss):
        if self.opt is None:
            raise RuntimeError('writer-only ladder has no ordinary-weight optimizer')
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.)
        self.opt.step()
        self.sched.step()
        self.steps += 1
        self.net.counters['optimizer_steps'] += 1

    def maze_batch(self, items):
        self._maze_batch(items)
        if self.phase == 'stream':
            self.stream_seen += len(items)
            self.net.phase = f'k{self.stream_seen}'
        self._report('batch_complete')

    def _maze_batch(self, items):
        if self.phase.startswith('sleep'):
            raise RuntimeError('sleep controller cannot adapt a batch')
        net = self.net
        net.train()
        with net.measured('training_seconds'):
            if net.is_patch and net.init == 'pre':
                net.write_supports(items)
            if self.writer_only:
                return
            t, s, y = tensors(items, net.device)
            if net.arm == 'plain':
                for _ in range(UPDATES):
                    self.update(ce_and_exact(net.plain_forward(t, s), s, y)[0])
                return
            h = None
            for _ in range(UPDATES):
                e, (dr, dc) = net.core.embed(t, s)
                if h is None:
                    h = torch.zeros_like(e)
                patch = net.patch()
                with torch.no_grad():
                    for _ in range(3):
                        h = net.core.step(h, e.detach(), dr, dc, patch)
                h = h.detach()
                ces = []
                for _ in range(2):
                    h = net.core.step(h, e, dr, dc, patch)
                    ces.append(ce_and_exact(net.core.read(h)[0], s, y)[0])
                net._work(t, 5, 2, reads=2)
                self.update(torch.stack(ces).mean())
                h = h.detach()

    def sleep(self, mazes, seed, old_replay):
        if self.phase not in ('sleep64', 'sleep64k') or self.steps:
            raise RuntimeError('sleep must run exactly once on a new sleep controller')
        if not mazes or len(old_replay['sums4']) < 4 or len(old_replay['grids5']) < 4:
            raise ValueError('sleep needs passed branch examples and both locked old replay stores')
        net = self.net
        _emit(dict(event='replay_memory', phase=self.phase, sequence=self.sequence,
                   ordinal=self.ordinal, core=net.core.arm, init=net.init,
                   model_id=net.model_id, **replay_memory(net, old_replay, mazes)))
        net.train()
        rng = random.Random(9262700 + seed)
        round_rng = random.Random(9282700 + seed)
        net._sync()
        start = time.perf_counter()
        with net.measured('training_seconds'):
            for _ in range(SLEEP_STEPS):
                groups = (rng.sample(old_replay['sums4'], 4), rng.sample(old_replay['grids5'], 4),
                          rng.choices(mazes, k=8))
                losses = []
                for items in groups:
                    t, s, y = tensors(items, net.device)
                    if net.arm == 'plain':
                        loss = ce_and_exact(net.plain_forward(t, s), s, y)[0]
                    else:
                        total = round_rng.randint(1, TRAIN_ROUNDS)
                        grad = round_rng.randint(1, min(total, GRAD_ROUNDS))
                        loss = torch.stack([ce_and_exact(lg, s, y)[0]
                                            for lg, _ in net.loop_train(t, s, total-grad, grad)]).mean()
                    losses.append(loss)
                self.update(.25*losses[0] + .25*losses[1] + .5*losses[2])
                for key, count in (('sleep_examples', 16), ('sleep_sums', 4), ('sleep_grids', 4), ('sleep_branch', 8)):
                    net.counters[key] += count
            if self.steps != 512:
                raise RuntimeError('locked sleep must perform exactly 512 updates')
            net.remove_patch()
        self._report('sleep_complete_patch_removed')
        return time.perf_counter() - start
