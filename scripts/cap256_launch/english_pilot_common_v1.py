"""Shared stdlib helpers for the English paraphrase pilot (G1-G12).

Import is stdlib-only. Torch is always passed in by the caller so that the
config checks, schedule and scorer stay runnable without Torch. Device helpers
work on CPU (tests) and CUDA (native run) without assuming CUDA exists.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time

MIB = 1024 ** 2
BOS_ID, EOS_ID, PAD_ID = 1, 7, 0
INPUT_CAP_WITH_EOS = 64
TARGET_CAP_WITH_EOS = 48
COMPONENTS = ('core', 'reader', 'prefix', 'tool')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(MIB), b''):
            h.update(block)
    return h.hexdigest()


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def canonical(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes())


def pinned(root, pin):
    """Resolve a {'path','sha256'} pin inside root and verify its bytes."""
    if type(pin) is not dict or set(pin) - {'path', 'sha256', 'bytes'} or 'path' not in pin or 'sha256' not in pin:
        raise ValueError('exact {path, sha256} pin required')
    base = Path(root).resolve()
    path = (base / pin['path']).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise ValueError('pinned file missing or outside root: ' + str(pin['path']))
    if digest(path) != pin['sha256']:
        raise ValueError('pinned file bytes differ: ' + str(pin['path']))
    return path


def write_new_json(path, value):
    """Exclusive create + fsync; never replaces existing evidence."""
    path = Path(path)
    data = canonical_bytes(value) + b'\n'
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(data).hexdigest()


def append_jsonl(path, value):
    data = canonical_bytes(value) + b'\n'
    with Path(path).open('ab') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def cuda_available(torch):
    return bool(torch.cuda.is_available())


def synchronize(torch):
    if cuda_available(torch):
        torch.cuda.synchronize()


def timed_call(function, torch):
    synchronize(torch)
    started = time.perf_counter()
    result = function()
    synchronize(torch)
    return result, time.perf_counter() - started


def tree_digest(value, torch):
    """Exact typed digest of nested tensors/dicts/lists (model, Adam, RNG)."""
    h = hashlib.sha256()

    def visit(v):
        if torch.is_tensor(v):
            h.update(('tensor:' + str(v.dtype) + ':' + str(tuple(v.shape))).encode())
            h.update(v.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
        elif isinstance(v, dict):
            h.update(b'dict{')
            for k in sorted(v, key=lambda x: (type(x).__name__, repr(x))):
                visit(k)
                visit(v[k])
            h.update(b'}')
        elif isinstance(v, (list, tuple)):
            h.update(type(v).__name__.encode() + b'[')
            for x in v:
                visit(x)
            h.update(b']')
        else:
            h.update((type(v).__name__ + ':' + repr(v) + ';').encode())
    visit(value)
    return h.hexdigest()


def rng_snapshot(torch):
    return {'torch_rng': torch.get_rng_state().clone(),
            'cuda_rng': [s.clone() for s in torch.cuda.get_rng_state_all()] if cuda_available(torch) else [],
            'python_rng': random.getstate()}


def restore_rng(state, torch):
    if set(state) != {'torch_rng', 'cuda_rng', 'python_rng'}:
        raise ValueError('exact three-part RNG state required')
    torch.set_rng_state(state['torch_rng'])
    if cuda_available(torch):
        torch.cuda.set_rng_state_all(state['cuda_rng'])
    elif state['cuda_rng']:
        raise ValueError('saved CUDA RNG cannot be restored without CUDA')
    random.setstate(state['python_rng'])
    if tree_digest(state, torch) != tree_digest(rng_snapshot(torch), torch):
        raise ValueError('exact RNG restoration failed')


def state_equal(left, right, torch):
    if torch.is_tensor(left):
        return (torch.is_tensor(right) and left.dtype == right.dtype
                and torch.equal(left.detach().cpu(), right.detach().cpu()))
    if isinstance(left, dict):
        return (isinstance(right, dict) and left.keys() == right.keys()
                and all(state_equal(left[k], right[k], torch) for k in left))
    if isinstance(left, (list, tuple)):
        return (type(left) is type(right) and len(left) == len(right)
                and all(state_equal(a, b, torch) for a, b in zip(left, right)))
    return left == right


def gradient_receipt(module, torch):
    norm2 = 0.0
    present = nonzero = elements = 0
    finite = True
    for p in module.parameters():
        if p.grad is None:
            continue
        grad = p.grad.detach()
        present += 1
        elements += grad.numel()
        finite = finite and bool(torch.isfinite(grad).all())
        n = float(grad.double().square().sum().item())
        norm2 += n
        if n > 0:
            nonzero += 1
    return {'finite': finite, 'norm': math.sqrt(norm2), 'parameters_with_grad': present,
            'parameters_with_nonzero_grad': nonzero, 'gradient_elements': elements}


def module_fingerprint(module, torch):
    return tree_digest(module.state_dict(), torch)


class WallBudget:
    def __init__(self, seconds, clock=time.monotonic):
        if type(seconds) is not int or seconds <= 0:
            raise ValueError('positive integer wall budget required')
        self.seconds, self.clock, self.started = seconds, clock, clock()

    def elapsed(self):
        return self.clock() - self.started

    def check(self):
        if self.elapsed() > self.seconds:
            raise RuntimeError('wall-clock cap exceeded; preserve evidence')
