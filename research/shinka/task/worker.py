"""Child process that hosts one candidate CardWriter (research/shinka/CARD.md section 2).

The child imports the candidate and nothing from the harness. It never sees token
ids, facts, questions or answers: only reader states, with lines shuffled across
visits by the parent on every call. It runs the writer's forward pass, receives
the gradient of the parent's loss with respect to the keys and values, and steps
its own optimizer. Everything that decides the score (the answerer, the loss, the
metrics and the writer checks) runs in the parent.

Protocol (multiprocessing Pipe). The parent sends pickled tuples holding numpy
arrays, which are copied by value with no shared memory. The child replies with
raw bytes only, so the parent never unpickles anything the child produced:
  ("init", path, cls_name, seed, d, dk, lr, trusted) -> b"I" + int64 n_numbers
  ("fwd", states, mask, train, roles)                -> b"F" + keys float32 + values float32
  ("step", dkeys, dvalues)                           -> b"S"
  ("count",)                                         -> b"I" + int64 n_numbers
  ("stop",)
  any failure                                        -> b"E" + utf-8 message
"""

from __future__ import annotations

import importlib.util
import struct
import traceback
import types


def _die_with_parent() -> None:
    """Linux: SIGKILL this process when the parent dies, so no orphan keeps running."""
    try:
        import ctypes
        import signal
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, int(signal.SIGKILL))  # PR_SET_PDEATHSIG
    except (OSError, AttributeError):
        pass


class _TooDeep(Exception):
    pass


def _owned_numbers(m, mod=None) -> int:
    """Count every number the writer can reach, using torch's own methods (never the
    object's, which the candidate could override):
      - tensors count their whole underlying storage (a view of a big tensor counts big);
      - parameters, buffers, attributes, containers, helper objects;
      - class attributes along the whole MRO (torch's own classes included), attributes
        set on tensors, method defaults and closures;
      - the .grad of any tensor that is not an nn.Parameter;
      - Python numbers in containers (1 each), and the candidate module's own namespace.
    Raises if the structure is nested too deeply to walk."""
    import torch
    seen_obj, seen_storage, total = set(), set(), 0

    def walk(v, depth=0):
        nonlocal total
        if depth > 40:
            raise _TooDeep()
        if id(v) in seen_obj:
            return
        seen_obj.add(id(v))
        if isinstance(v, torch.Tensor):
            st = torch.Tensor.untyped_storage(v)
            key = st.data_ptr() if st.nbytes() else id(v)
            if key not in seen_storage:
                seen_storage.add(key)
                total += max(st.nbytes() // max(torch.Tensor.element_size(v), 1),
                             torch.Tensor.numel(v))
            g = torch.Tensor.grad.__get__(v)
            if g is not None and not isinstance(v, torch.nn.Parameter):
                walk(g, depth + 1)
            for x in object.__getattribute__(v, "__dict__").values():  # attributes set on a tensor
                walk(x, depth + 1)
            walk(type(v), depth + 1)
            return
        if isinstance(v, torch.nn.Module):
            for t in list(torch.nn.Module.parameters(v)) + list(torch.nn.Module.buffers(v)):
                walk(t, depth + 1)
            for x in vars(v).values():
                walk(x, depth + 1)
            walk(type(v), depth + 1)
            return
        if isinstance(v, int) and not isinstance(v, bool):
            total += max(1, int.bit_length(v) // 64)
            return
        if isinstance(v, (bool, float, complex)):
            total += 1
            return
        if isinstance(v, (str, bytes, bytearray)):
            total += max(1, len(v) // 8)
            return
        if isinstance(v, type):
            for klass in type.mro(v):
                if klass is not object:
                    for k, x in vars(klass).items():
                        if k not in ("__doc__", "__module__", "__qualname__", "__dict__",
                                     "__weakref__", "__annotations__"):
                            walk(x, depth + 1)
            return
        if isinstance(v, (staticmethod, classmethod)):
            walk(v.__func__, depth + 1)
            return
        if isinstance(v, property):
            for f in (v.fget, v.fset, v.fdel):
                if f is not None:
                    walk(f, depth + 1)
            return
        if isinstance(v, types.MethodType):
            walk(v.__func__, depth + 1)
            walk(v.__self__, depth + 1)
            return
        if isinstance(v, (types.BuiltinMethodType, types.MethodWrapperType)):
            walk(getattr(v, "__self__", None), depth + 1)  # e.g. a stored tensor.matmul
            return
        if isinstance(v, types.FunctionType):
            for x in vars(v).values():
                walk(x, depth + 1)
            for x in (v.__defaults__ or ()):
                walk(x, depth + 1)
            for x in (v.__kwdefaults__ or {}).values():
                walk(x, depth + 1)
            for cell in (v.__closure__ or ()):
                try:
                    walk(cell.cell_contents, depth + 1)
                except ValueError:
                    pass
            return
        if isinstance(v, (list, tuple, set, frozenset)):
            total += len(v)  # each slot can carry information even if it repeats an object
            for x in v:
                walk(x, depth + 1)
        elif isinstance(v, dict):
            total += len(v)
            for k2, x in v.items():
                walk(k2, depth + 1)
                walk(x, depth + 1)
        elif hasattr(v, "__dict__") and not isinstance(v, type(importlib)):
            for x in vars(v).values():
                walk(x, depth + 1)
            walk(type(v), depth + 1)

    try:
        walk(m)
        if mod is not None:
            for k, x in vars(mod).items():
                if not k.startswith("__") and not isinstance(x, type(importlib)):
                    walk(x)
    except _TooDeep:
        raise ValueError("writer state is nested too deeply to count") from None
    return total


def serve(conn) -> None:
    _die_with_parent()
    import numpy as np
    import torch
    torch.set_num_threads(1)
    writer = opt = mod = None
    last = None
    trusted = False
    while True:
        msg = conn.recv()
        kind = msg[0]
        try:
            if kind == "stop":
                return
            if kind == "init":
                _, path, cls_name, seed, d, dk, lr, trusted = msg
                spec = importlib.util.spec_from_file_location("candidate", path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                torch.manual_seed(seed)
                writer = getattr(mod, cls_name)(d, dk)
                params = [p for p in writer.parameters() if p.requires_grad]
                opt = torch.optim.Adam(params, lr=lr) if params else None
                conn.send_bytes(b"I" + struct.pack("<q", _owned_numbers(writer, mod)))
            elif kind == "count":
                conn.send_bytes(b"I" + struct.pack("<q", _owned_numbers(writer, mod)))
            elif kind == "fwd":
                _, states, mask, train, roles = msg
                states, mask = torch.from_numpy(states), torch.from_numpy(mask)
                if trusted and roles is not None:  # only the calibration oracle uses roles
                    mod.ROLES = torch.from_numpy(roles)
                writer.train(train)
                if train:
                    keys, values = writer(states, mask)
                    last = (keys, values)
                else:
                    with torch.no_grad():
                        keys, values = writer(states, mask)
                k = np.ascontiguousarray(keys.detach().float().numpy())
                v = np.ascontiguousarray(values.detach().float().numpy())
                conn.send_bytes(b"F" + struct.pack("<qq", k.size, v.size) + k.tobytes() + v.tobytes())
            elif kind == "step":
                _, dk_, dv_ = msg
                outs, grads = [], []
                for t, g in zip(last, (dk_, dv_)):
                    if t.requires_grad:  # a writer may have no learnable path to one output
                        outs.append(t)
                        grads.append(torch.from_numpy(g).to(t.dtype))
                if opt is not None and outs:
                    opt.zero_grad()
                    torch.autograd.backward(outs, grads)
                    opt.step()
                last = None
                conn.send_bytes(b"S")
        except Exception as exc:  # noqa: BLE001 - report to the parent, which scores 0
            err = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-1500:]}"
            conn.send_bytes(b"E" + err.encode("utf-8", "replace"))
