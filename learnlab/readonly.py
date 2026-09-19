"""Read-only evaluation: testing must never train the model.

`read_only` snapshots everything an evaluation could write, runs the block in
eval mode under `torch.no_grad()`, and verifies on exit (also when the block
raised) that nothing changed:

- every parameter and buffer slot: object identity, class, dtype, shape,
  stride, storage pointer, device, layout, requires_grad, version counter,
  content digest, `.grad` (or None) and, for buffers, persistence;
- the module tree (identity of every submodule) and a shallow fingerprint of
  every module's other Python attributes, hook tables included;
- each optimizer's (or LR scheduler's) `state_dict()`, plus the identity of
  the parameters it steps;
- each store's `fingerprint()`.

Training flags are saved per module and restored exactly (the guard never
calls `train()`/`eval()`, so a frozen submodule stays frozen). RNG state
(python, numpy if already imported, torch CPU, CUDA and MPS when available,
plus any `torch.Generator`/`random.Random` a module holds) is restored, so
evaluation cannot perturb training randomness. Tensors held in plain module
attributes are invisible to checkpoints and are refused unless allowlisted.

Known blind spot: an in-place write through `.data` that is reverted before
the block exits (`.data` bypasses the version counter). Objects that are not
primitives, containers or tensors are compared by type and identity only;
give anything with deeper state a `fingerprint()` and pass it as a store.
"""
from __future__ import annotations

import collections
from contextlib import AbstractContextManager
from dataclasses import dataclass, fields
import enum
import fnmatch
import hashlib
import random
import sys
import types
from typing import Any, Callable, Iterable, Iterator, Optional, Sequence
import weakref

import torch
from torch import nn

# Module internals covered by the per-tensor, per-module and mode records.
_STRUCTURAL = frozenset(
    {"_parameters", "_buffers", "_modules", "_non_persistent_buffers_set", "training"}
)
_PRIMITIVES = (
    type(None), bool, int, float, complex,
    torch.dtype, torch.device, torch.layout, torch.memory_format, enum.Enum,
)
_MAX_DEPTH = 8
_MAX_REPORTED = 12


class ReadOnlyViolation(RuntimeError):
    """Evaluation changed, or could silently change, model, optimizer or store state."""

    def __init__(self, message: str, changes: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.changes = tuple(changes)


def _try(read: Callable[[], Any]) -> Any:
    try:
        return read()
    except (RuntimeError, NotImplementedError, ValueError):
        return None


def _uninitialized(tensor: torch.Tensor) -> bool:
    return isinstance(tensor, nn.parameter.UninitializedTensorMixin)


def tensor_digest(tensor: torch.Tensor) -> str:
    """SHA-256 of dtype, shape and values (metadata only for meta or uninitialized tensors)."""
    digest = hashlib.sha256()
    if _uninitialized(tensor):
        digest.update(b"uninitialized")
        return digest.hexdigest()
    digest.update(f"{tensor.dtype}|{tuple(tensor.shape)}".encode())
    if tensor.device.type == "meta":
        return digest.hexdigest()
    data = tensor.detach()
    if data.layout != torch.strided:
        data = data.to_dense()
    if data.is_quantized:
        data = data.int_repr()
    data = data.to("cpu").contiguous()
    if data.numel():
        # Flatten first: a 0-d tensor cannot be viewed as bytes directly.
        raw = data.reshape(-1).view(torch.uint8)
        try:
            digest.update(raw.numpy())
        except RuntimeError:  # torch built without numpy
            digest.update(bytes(raw.tolist()))
    return digest.hexdigest()


@dataclass(frozen=True)
class TensorRecord:
    """Everything evaluation could change about one tensor."""

    identity: int
    cls: str
    dtype: str
    shape: Optional[tuple[int, ...]]
    stride: Optional[tuple[int, ...]]
    storage: Optional[tuple[int, int]]      # (data_ptr, storage_offset)
    device: str
    layout: str
    requires_grad: bool
    version: Optional[int]
    content: str
    grad: Optional[tuple[Any, ...]]         # (identity, dtype, shape, version, digest) or None
    persistent: Optional[bool]              # buffers only


def _grad_of(tensor: torch.Tensor) -> Optional[torch.Tensor]:
    # Reading .grad of a non-leaf that does not retain it only warns.
    return tensor.grad if (tensor.is_leaf or tensor.retains_grad) else None


def tensor_record(tensor: torch.Tensor, persistent: Optional[bool] = None) -> TensorRecord:
    """Record one tensor's identity, metadata, version, content and `.grad`."""
    uninitialized = _uninitialized(tensor)
    grad = _grad_of(tensor)
    grad_record = None
    if grad is not None:
        grad_record = (
            id(grad), str(grad.dtype), tuple(grad.shape), _try(lambda: grad._version),
            tensor_digest(grad),
        )
    return TensorRecord(
        identity=id(tensor),
        cls=type(tensor).__qualname__,
        dtype=str(tensor.dtype),
        shape=None if uninitialized else tuple(tensor.shape),
        stride=None if uninitialized else _try(lambda: tuple(tensor.stride())),
        storage=None if uninitialized else _try(lambda: (tensor.data_ptr(), tensor.storage_offset())),
        device=str(tensor.device),
        layout=str(tensor.layout),
        requires_grad=bool(tensor.requires_grad),
        version=_try(lambda: tensor._version),
        content=tensor_digest(tensor),
        grad=grad_record,
        persistent=persistent,
    )


def _differing(old: TensorRecord, new: TensorRecord) -> list[str]:
    return [f.name for f in fields(TensorRecord) if getattr(old, f.name) != getattr(new, f.name)]


class _Fingerprint:
    """Streams a shallow fingerprint of Python values into a hash.

    Primitives go by value; containers (list, tuple, dict, set, deque,
    bytearray) by content; weakrefs and bound methods by what they point to;
    tensors by identity (or by full record when `by_value`); anything else by
    type and identity. Every object whose identity is used is kept alive in
    `refs` so its id cannot be recycled. Generators found on the way are
    collected so the guard can restore them.
    """

    def __init__(self, refs: list[Any], *, registered: Optional[set[int]] = None,
                 by_value: bool = False) -> None:
        self.refs = refs
        self.registered = registered if registered is not None else set()
        self.by_value = by_value
        self.loose: set[str] = set()   # owners holding tensors not registered on the model
        self.generators: dict[int, Any] = {}

    def digest(self, value: Any, owner: str = "") -> str:
        digest = hashlib.sha256()
        self._feed(digest, value, _MAX_DEPTH, owner)
        return digest.hexdigest()

    def _feed(self, digest: Any, value: Any, depth: int, owner: str) -> None:
        def put(text: str) -> None:
            digest.update(text.encode("utf-8", "surrogatepass"))

        if isinstance(value, torch.Tensor):
            self.refs.append(value)
            if self.by_value:
                put(f"tensor{tensor_record(value)!r};")
            else:
                if id(value) not in self.registered:
                    self.loose.add(owner)
                put(f"tensor#{id(value)};")
            return
        if isinstance(value, (str, bytes, bytearray)):
            raw = value.encode("utf-8", "surrogatepass") if isinstance(value, str) else bytes(value)
            put(f"{type(value).__qualname__}{len(raw)}:")
            digest.update(raw)
            return
        if isinstance(value, _PRIMITIVES):
            put(f"{type(value).__qualname__}:{value!r};")
            return
        if isinstance(value, types.MethodType):
            # Bound methods are recreated on every attribute access and WeakMethod call.
            self.refs.extend((value.__self__, value.__func__))
            put(f"method#{id(value.__self__)}.{id(value.__func__)};")
            return
        if isinstance(value, weakref.ref) and depth > 0:
            target = value()
            put(f"{type(value).__qualname__}(")
            if target is None:
                put("dead")
            else:
                self._feed(digest, target, depth - 1, owner)
            put(");")
            return
        if isinstance(value, (torch.Generator, random.Random)):
            self.generators[id(value)] = value
        container = isinstance(value, (list, tuple, dict, set, frozenset, collections.deque))
        if depth <= 0 or not container:
            self.refs.append(value)
            put(f"{type(value).__qualname__}#{id(value)};")
            return
        put(type(value).__qualname__)
        if isinstance(value, dict):
            put("{")
            for key, item in list(value.items()):
                self._feed(digest, key, depth - 1, owner)
                put("=")
                self._feed(digest, item, depth - 1, owner)
            put("}")
        elif isinstance(value, (set, frozenset)):
            parts = []
            for item in list(value):
                sub = hashlib.sha256()
                self._feed(sub, item, depth - 1, owner)
                parts.append(sub.hexdigest())
            put("{" + ",".join(sorted(parts)) + "}")
        else:
            put("[")
            for item in list(value):
                self._feed(digest, item, depth - 1, owner)
            put("]")


def _join(prefix: str, name: str) -> str:
    return f"{prefix}.{name}" if prefix else name


def _walk(module: nn.Module, prefix: str = "",
          ancestors: frozenset[int] = frozenset()) -> Iterator[tuple[str, nn.Module]]:
    """Every (path, module), shared modules at each of their paths, cycles cut."""
    yield prefix, module
    inside = ancestors | {id(module)}
    for name, child in module._modules.items():
        if child is not None and id(child) not in inside:
            yield from _walk(child, _join(prefix, name), inside)


@dataclass
class _ModelSnapshot:
    modules: dict[str, tuple[str, int]]
    tensors: dict[str, tuple[str, Optional[TensorRecord]]]   # name -> (kind, record or None)
    attributes: dict[str, str]
    loose: set[str]
    generators: dict[int, Any]      # torch.Generator / random.Random held by modules
    refs: list[Any]


def _snapshot(model: Optional[nn.Module]) -> _ModelSnapshot:
    snap = _ModelSnapshot({}, {}, {}, set(), {}, [])
    if model is None:
        return snap
    walked = list(_walk(model))
    registered: set[int] = set()
    for path, module in walked:
        snap.refs.append(module)
        snap.modules[path] = (type(module).__qualname__, id(module))
        for name, child in module._modules.items():
            if child is None:
                snap.modules[_join(path, name)] = ("None", 0)
        slots = [("parameter", name, t, None) for name, t in module._parameters.items()]
        slots += [
            ("buffer", name, t, name not in module._non_persistent_buffers_set)
            for name, t in module._buffers.items()
        ]
        for kind, name, tensor, persistent in slots:
            record = None
            if tensor is not None:
                snap.refs.extend((tensor, _grad_of(tensor)))
                registered.add(id(tensor))
                record = tensor_record(tensor, persistent)
            snap.tensors[_join(path, name)] = (kind, record)
    printer = _Fingerprint(snap.refs, registered=registered)
    for path, module in walked:
        for name, value in list(vars(module).items()):
            if name not in _STRUCTURAL:
                qualified = _join(path, name)
                snap.attributes[qualified] = printer.digest(value, qualified)
    snap.loose, snap.generators = printer.loose, printer.generators
    return snap


def _state_digest(holder: Any, refs: list[Any]) -> str:
    """Digest of an optimizer's or scheduler's state_dict() and the parameters it steps."""
    digest = _Fingerprint(refs, by_value=True).digest(holder.state_dict())
    params = [p for group in getattr(holder, "param_groups", ()) for p in group.get("params", ())]
    refs.extend(params)
    return hashlib.sha256(f"{digest}|{[id(p) for p in params]}".encode()).hexdigest()


def _mps_ready() -> bool:
    mps = getattr(torch, "mps", None)
    return mps is not None and hasattr(mps, "get_rng_state") and torch.backends.mps.is_available()


def rng_state() -> dict[str, Any]:
    """Capture python, numpy (if already imported), torch CPU, CUDA and MPS generator states."""
    state: dict[str, Any] = {"python": random.getstate(), "torch": torch.get_rng_state()}
    np_random = sys.modules.get("numpy.random")
    if np_random is not None:
        state["numpy"] = np_random.get_state()
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    if _mps_ready():
        state["mps"] = torch.mps.get_rng_state()
    return state


def set_rng_state(state: dict[str, Any]) -> None:
    """Restore generator states captured by `rng_state()`."""
    random.setstate(state["python"])
    torch.set_rng_state(state["torch"])
    if "numpy" in state:
        sys.modules["numpy.random"].set_state(state["numpy"])
    if "cuda" in state:
        torch.cuda.set_rng_state_all(state["cuda"])
    if "mps" in state:
        torch.mps.set_rng_state(state["mps"])


def _generator_state(generator: Any) -> Any:
    if isinstance(generator, torch.Generator):
        return generator.get_state()
    return _try(generator.getstate)  # None for SystemRandom, which has no state


def _set_generator_state(generator: Any, state: Any) -> None:
    if isinstance(generator, torch.Generator):
        generator.set_state(state)
    elif state is not None:
        generator.setstate(state)


def _changed(old: Any, new: Any) -> str:
    if old is None:
        return "added"
    if new is None:
        return "removed"
    if isinstance(old, tuple) and isinstance(new, tuple) and old[1] == new[1]:
        return "class changed"
    return "replaced"


class _ReadOnlyGuard(AbstractContextManager):
    """Context manager behind `read_only` (a class, so the exception path is exact)."""

    def __init__(self, model: Optional[nn.Module], stores: Iterable[Any],
                 optimizers: Iterable[Any], allow_changes: Iterable[str],
                 restore_rng: bool) -> None:
        if model is not None and not isinstance(model, nn.Module):
            raise TypeError(f"read_only needs an nn.Module or None, got {type(model).__name__}")
        self.model = model
        self.stores = list(stores)
        for index, store in enumerate(self.stores):
            if not callable(getattr(store, "fingerprint", None)):
                raise TypeError(
                    f"store[{index}] ({type(store).__name__}) has no fingerprint() method"
                )
        self.optimizers = list(optimizers)
        for index, holder in enumerate(self.optimizers):
            if not callable(getattr(holder, "state_dict", None)):
                raise TypeError(
                    f"optimizers[{index}] ({type(holder).__name__}) has no state_dict() method"
                )
        if isinstance(allow_changes, (str, bytes)):
            raise TypeError("allow_changes must be an iterable of names, not a single string")
        self.allow = tuple(allow_changes)
        for pattern in self.allow:
            if not isinstance(pattern, str):
                raise TypeError(f"allow_changes entries must be str, got {type(pattern).__name__}")
        self.restore_rng = bool(restore_rng)
        self._active = False

    def _allowed(self, name: str) -> bool:
        return any(fnmatch.fnmatchcase(name, pattern) for pattern in self.allow)

    def __enter__(self) -> None:
        if self._active:
            raise RuntimeError("a read_only guard cannot be re-entered while active")
        # Read and validate everything before touching any state.
        before = _snapshot(self.model)
        covered = sorted(
            name for name, (kind, _) in before.tensors.items()
            if kind == "parameter" and self._allowed(name)
        )
        if covered:
            raise ValueError(f"allow_changes may not cover parameters: {covered[:_MAX_REPORTED]}")
        loose = sorted(name for name in before.loose if not self._allowed(name))
        if loose:
            raise ReadOnlyViolation(
                f"unregistered tensor attributes {loose[:_MAX_REPORTED]}: register them as "
                "buffers or list them in allow_changes",
                [f"unregistered tensor attribute {name}" for name in loose],
            )
        refs: list[Any] = []
        self._optimizer_digests = [_state_digest(holder, refs) for holder in self.optimizers]
        self._store_prints = [store.fingerprint() for store in self.stores]
        self._rng = rng_state() if self.restore_rng else None
        self._generators = [
            (generator, _generator_state(generator)) for generator in before.generators.values()
        ] if self.restore_rng else []
        self._before, self._refs = before, refs
        seen: set[int] = set()
        self._modes: list[tuple[nn.Module, bool]] = []
        if self.model is not None:
            for _, module in _walk(self.model):
                if id(module) not in seen:
                    seen.add(id(module))
                    self._modes.append((module, module.training))
        self._grad_enabled = torch.is_grad_enabled()
        for module, _ in self._modes:
            module.training = False
        torch.set_grad_enabled(False)
        self._active = True

    def _restore(self) -> None:
        try:
            torch.set_grad_enabled(self._grad_enabled)
            for module, training in self._modes:
                module.training = training
        finally:
            if self._rng is not None:
                set_rng_state(self._rng)
            for generator, state in self._generators:
                _set_generator_state(generator, state)

    def _changes(self) -> list[str]:
        before, after = self._before, _snapshot(self.model)
        changes = []
        for path in sorted(before.modules.keys() | after.modules.keys()):
            old, new = before.modules.get(path), after.modules.get(path)
            if old != new:
                changes.append(f"module {path or '<root>'}: {_changed(old, new)}")
        for name in sorted(before.tensors.keys() | after.tensors.keys()):
            old, new = before.tensors.get(name), after.tensors.get(name)
            kinds = sorted({slot[0] for slot in (old, new) if slot is not None})
            if old == new or ("parameter" not in kinds and self._allowed(name)):
                continue
            if old is None or new is None or old[0] != new[0]:
                detail = _changed(old, new) if old is None or new is None else "kind changed"
            elif old[1] is None or new[1] is None:
                detail = "set to None" if new[1] is None else "set from None"
            else:
                detail = ", ".join(_differing(old[1], new[1]))
            changes.append(f"{'/'.join(kinds)} {name}: {detail}")
        for name in sorted(before.attributes.keys() | after.attributes.keys()):
            old, new = before.attributes.get(name), after.attributes.get(name)
            if old != new and not self._allowed(name):
                detail = "changed" if old is not None and new is not None else _changed(old, new)
                changes.append(f"attribute {name}: {detail}")
        changes += [
            f"unregistered tensor attribute {name}"
            for name in sorted(after.loose) if not self._allowed(name)
        ]
        refs: list[Any] = []
        for index, holder in enumerate(self.optimizers):
            if _state_digest(holder, refs) != self._optimizer_digests[index]:
                changes.append(f"optimizers[{index}] {type(holder).__name__}: state changed")
        for index, store in enumerate(self.stores):
            if store.fingerprint() != self._store_prints[index]:
                changes.append(f"store[{index}] {type(store).__name__}: fingerprint changed")
        return changes

    def __exit__(self, exc_type: Optional[type[BaseException]], exc: Optional[BaseException],
                 traceback: Optional[types.TracebackType]) -> bool:
        try:
            self._restore()
            if exc is not None and not isinstance(exc, Exception):
                return False  # KeyboardInterrupt and friends: restore, never mask
            changes = self._changes()
        finally:
            self._active = False
            self._before = self._refs = self._rng = None  # type: ignore[assignment]
            self._modes, self._generators = [], []
        if changes:
            shown = changes[:_MAX_REPORTED]
            more = f" (+{len(changes) - len(shown)} more)" if len(changes) > len(shown) else ""
            violation = ReadOnlyViolation(f"evaluation modified: {shown}{more}", changes)
            if exc is not None:
                raise violation from exc
            raise violation
        return False


def read_only(model: Optional[nn.Module], stores: Iterable[Any] = (), *,
              optimizers: Iterable[torch.optim.Optimizer] = (),
              allow_changes: Iterable[str] = (),
              restore_rng: bool = True) -> AbstractContextManager[None]:
    """Guard an evaluation block; raise ReadOnlyViolation if it changed any state.

    `stores` need a `fingerprint()` method (TypeError otherwise). `optimizers`
    accepts anything with `state_dict()`, LR schedulers included.
    `allow_changes` names derived buffers or attributes (e.g. a rotary cache)
    that may change, as qualified names like `named_buffers()` gives them;
    fnmatch patterns such as `"*.cos_cached"` are accepted. Parameters can
    never be allowlisted. If the block raises and state changed, the violation
    is chained from the original exception; otherwise the original propagates.
    """
    return _ReadOnlyGuard(model, stores, optimizers, allow_changes, restore_rng)


def module_digests(module: nn.Module) -> dict[str, str]:
    """Digest of every parameter and buffer record (identity and metadata included)."""
    snap = _snapshot(module)
    return {
        f"{'param' if kind == 'parameter' else 'buffer'}:{name}":
            hashlib.sha256(repr(record).encode()).hexdigest()
        for name, (kind, record) in snap.tensors.items()
    }


__all__ = [
    "ReadOnlyViolation",
    "TensorRecord",
    "module_digests",
    "read_only",
    "rng_state",
    "set_rng_state",
    "tensor_digest",
    "tensor_record",
]
