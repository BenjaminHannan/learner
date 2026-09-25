#!/usr/bin/env python3
"""slp-361: STAGED COMMIT + UNDO for a whole sleep (Fix-sleep thread, 2026-09-25; plan 360-sleep-plan.md).

Today a sleep cannot be undone: `accepted` in fable_agent_loop._sleep_tick (lines 383-392) is read after the
sleeper has already written its word routes, and it only decides whether the experience log is cleared.

ONE CHANGE: install_undo361(loop, judge) wraps loop._sleep_tick. Before the sleep it takes a snapshot of
  - every file under the state dir except the main notebook folder (word routes, scrap layer, agenda, ...),
  - the plain in-memory state of the loop, reasoner (and its inner reasoner) and sleeper
    (dicts, lists, numbers, strings, tensors; object references are left alone),
  - a hash of the main notebook's event log.
After the sleep, judge(loop, event) -> bool decides. On False the night is undone: changed files are written
back byte for byte, files the sleep created are MOVED to <state_dir>/undo361/<n>/ (never deleted), the
in-memory state is put back, and the experience log is kept for a later sleep. The default judge accepts,
so installing 361 alone changes nothing. Jobs 362-364 plug their checks in as the judge.

The main notebook is never restored by copying: with slp-360 installed sleep cannot write to it. If its hash
changed anyway, the undo reports main_notebook_changed=True and the caller must treat the night as failed.
"""
from __future__ import annotations

import copy
import hashlib
import os
import shutil
from pathlib import Path

UNDO_DIR361 = "undo361"
MAX_SNAPSHOT_BYTES361 = 64 * 1024 * 1024
_PRIMS = (int, float, str, bool, type(None), bytes)
_LOOP_KEEP361 = {"tick", "mode", "notes", "undo361_stats"}   # time moves on; these are not undone


def _plain(v, depth: int = 0) -> bool:
    if depth > 8:
        return False
    if isinstance(v, _PRIMS):
        return True
    if type(v).__name__ in ("Tensor", "Parameter"):
        return True
    if isinstance(v, (list, tuple, set, frozenset)):
        return all(_plain(x, depth + 1) for x in v)
    if isinstance(v, dict):
        return all(_plain(k, depth + 1) and _plain(x, depth + 1) for k, x in v.items())
    return False


def _clone(v):
    if type(v).__name__ in ("Tensor", "Parameter"):
        return v.detach().clone()
    return copy.deepcopy(v)


def _objects(loop) -> dict:
    objs = {"loop": loop, "reasoner": getattr(loop, "reasoner", None),
            "sleeper": getattr(loop, "sleeper", None)}
    inner = getattr(objs["reasoner"], "inner", None)
    if inner is not None:
        objs["reasoner.inner"] = inner
    return {k: o for k, o in objs.items() if o is not None}


def _mem_snapshot(loop) -> dict:
    snap = {}
    for key, obj in _objects(loop).items():
        state = {}
        for name, val in vars(obj).items():
            if callable(val) or name.startswith("__"):
                continue
            if key == "loop" and name in _LOOP_KEEP361:
                continue
            if _plain(val):
                try:
                    state[name] = _clone(val)
                except Exception:          # noqa: BLE001  (unclonable: leave it, report it)
                    state[name] = None
        snap[key] = state
    return snap


def _mem_restore(loop, snap: dict) -> None:
    objs = _objects(loop)
    for key, state in snap.items():
        obj = objs.get(key)
        if obj is None:
            continue
        for name, val in state.items():
            setattr(obj, name, _clone(val))


def _files(root: Path, skip: set[str]) -> dict:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        if rel_dir.parts and rel_dir.parts[0] in skip:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not (not rel_dir.parts and d in skip)]
        for name in filenames:
            p = Path(dirpath) / name
            out[str(p.relative_to(root))] = p
    return out


def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def accept_all(loop, event) -> bool:
    return True


def install_undo361(loop, judge=None, notebook_dir: str = "notebook"):
    root = Path(loop.dir)
    skip = {notebook_dir, UNDO_DIR361}
    loop.undo361_judge = judge or accept_all
    loop.undo361_stats = {"sleeps": 0, "undone": 0, "last": None}
    main_log = root / notebook_dir / "events.jsonl"
    inner_sleep = loop._sleep_tick

    def sleep361():
        files = _files(root, skip)
        saved = {}
        too_big = []
        for rel, p in files.items():
            size = p.stat().st_size
            if size > MAX_SNAPSHOT_BYTES361:
                too_big.append(rel)
                saved[rel] = (None, _digest(p))
            else:
                data = p.read_bytes()
                saved[rel] = (data, hashlib.sha256(data).hexdigest())
        mem = _mem_snapshot(loop)
        experience = copy.deepcopy(loop.experience)
        counters = copy.deepcopy(loop.counters)
        main_before = _digest(main_log)

        event = inner_sleep()
        loop.undo361_stats["sleeps"] += 1
        keep = bool(loop.undo361_judge(loop, event))
        info = {"kept": keep}
        if not keep:
            n = loop.undo361_stats["undone"] + 1
            stash = root / UNDO_DIR361 / f"night{n:03d}"
            after = _files(root, skip)
            moved, restored, lost = [], [], []
            for rel, p in after.items():
                if rel not in saved:
                    dest = stash / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(p), str(dest))
                    moved.append(rel)
            for rel, (data, digest) in saved.items():
                p = root / rel
                if _digest(p) == digest:
                    continue
                if data is None:
                    lost.append(rel)
                    continue
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_name(p.name + ".undo361tmp")
                tmp.write_bytes(data)
                os.replace(tmp, p)
                restored.append(rel)
            _mem_restore(loop, mem)
            loop.experience = experience
            loop.sleep_mark = len(experience)       # keep the log; don't retry until it grows
            loop.counters = counters
            loop.counters["sleeps_undone361"] = loop.counters.get("sleeps_undone361", 0) + 1
            loop.undo361_stats["undone"] = n
            info.update({"moved": moved, "restored": restored, "not_restorable": lost + too_big,
                         "main_notebook_changed": _digest(main_log) != main_before})
            event = dict(event)
            event["detail"] = dict(event.get("detail", {}), accepted=False, undone361=True)
        loop.undo361_stats["last"] = info
        return event

    loop._sleep_tick = sleep361
    loop.notes.append("slp-361: staged sleep; a rejected night is undone (files, memory, log kept)")
    return loop
