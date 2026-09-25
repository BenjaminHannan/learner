#!/usr/bin/env python3
"""slp-369: PUT THE MAIN NOTEBOOK BACK after a night that changed it (Fix-sleep thread, 2026-09-25).

slp-368 blocks every write that goes through Notebook._append while the sleeper runs, but code that opens the log
file itself can still append to it (slp-364c, case slp364c-05: a RETRACT line written with its own open()). The
gate saw it and rejected the night, yet nothing put the file back (slp-364c registered FAIL, P364c.4).

ONE CHANGE: install_restore369(loop) wraps loop.sleeper.sleep (install it AFTER slp-368, so it sits outside the lock).
Before the sleeper runs it keeps the bytes of every file in the notebook folder and a copy of the notebook objects'
state. After the sleeper returns, if any notebook file's bytes differ, it
  1. moves the changed files aside to <state>/undo361/main369-NNN/ (never deleted),
  2. writes the kept bytes back,
  3. restores the notebook objects IN PLACE (every dict, list and set attribute is cleared and refilled, so other
     parts of the loop that hold these containers see the restored contents), and the outer notebook keeps pointing
     at the SAME inner notebook object (a plain deep copy would swap in a copy of the inner notebook, which other
     parts of the loop do not see: found while testing this file, and the likely cause of slp-364b's damage),
  4. reports the night as not accepted ("slp-369: main notebook restored"), so the gate and slp-361 undo the rest.
Honest nights never change the notebook (slp-360 sends sleep's own rows to the scrap layer), so they are untouched.
"""
from __future__ import annotations

import copy
import functools
import hashlib
from pathlib import Path

DIR369 = "main369"


def _objs(loop) -> list:
    out, seen = [], set()
    for o in (loop.nb, getattr(loop.nb, "nb", None)):
        if o is not None and id(o) not in seen:
            out.append(o)
            seen.add(id(o))
    return out


def _restore_in_place(obj, saved: dict) -> None:
    cur = obj.__dict__
    for k in list(cur):
        if k not in saved and not callable(cur[k]):
            del cur[k]
    for k, v in saved.items():
        now = cur.get(k)
        if isinstance(now, dict) and isinstance(v, dict) and now is not v:
            now.clear()
            now.update(v)
        elif isinstance(now, list) and isinstance(v, list) and now is not v:
            now[:] = v
        elif isinstance(now, set) and isinstance(v, set) and now is not v:
            now.clear()
            now.update(v)
        else:
            cur[k] = v


def install_restore369(loop) -> dict:
    st = {"nights": 0, "restored": 0, "last": None}
    loop.restore369 = st
    inner_sleep = loop.sleeper.sleep

    @functools.wraps(inner_sleep)
    def sleep369(experience, notebook):
        nbdir = Path(loop.dir) / "notebook"
        files = {p.relative_to(nbdir).as_posix(): p.read_bytes() for p in nbdir.rglob("*") if p.is_file()}
        objs = _objs(loop)
        keep = {id(o): o for o in objs}            # the outer notebook's .nb must stay the SAME inner object
        mem = [(o, copy.deepcopy({k: v for k, v in o.__dict__.items() if not callable(v)}, dict(keep)))
               for o in objs]
        st["nights"] += 1
        out = inner_sleep(experience, notebook)
        changed = []
        for p in list(nbdir.rglob("*")):
            if p.is_file():
                rel = p.relative_to(nbdir).as_posix()
                if files.get(rel) != p.read_bytes():
                    changed.append(rel)
        gone = [rel for rel in files if not (nbdir / rel).exists()]
        st["last"] = {"changed": changed, "gone": gone}
        if not changed and not gone:
            return out
        st["restored"] += 1
        dest_root = Path(loop.dir) / "undo361" / f"{DIR369}-{st['nights']:03d}"
        for rel in changed:
            dest = dest_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            (nbdir / rel).replace(dest)
        for rel, data in files.items():
            if rel in changed or rel in gone:
                (nbdir / rel).parent.mkdir(parents=True, exist_ok=True)
                (nbdir / rel).write_bytes(data)
        for o, saved in mem:
            _restore_in_place(o, saved)
        log = nbdir / "events.jsonl"
        st["last"]["log_back"] = (hashlib.sha256(log.read_bytes()).hexdigest()
                                  == hashlib.sha256(files.get("events.jsonl", b"")).hexdigest()) if log.exists() else None
        why = f"slp-369: main notebook restored ({len(changed)} changed, {len(gone)} removed file(s))"
        base = dict(out) if isinstance(out, dict) else {}
        base.update({"accepted": False, "reason": why, "restore369": dict(st["last"])})
        rec = base.get("recipe") if isinstance(base.get("recipe"), dict) else {}
        base["recipe"] = dict(rec, attempted=False, reason=why)
        return base

    loop.sleeper.sleep = sleep369
    loop.notes.append("slp-369: a night that changes the main notebook is put back and not accepted")
    return st
