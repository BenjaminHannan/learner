#!/usr/bin/env python3
"""Exp 241 M3 + M2(b)/(c) suite driver (harness only; nothing edited).

Runs scripts/fable_suitediff218.py in-process (imported read-only) with
two passive hooks and nothing else changed:
  * shutil.rmtree is wrapped: before any directory is removed, every
    notebook/events.jsonl under it is copied to <capture>/ (named by its
    path relative to the suitediff work dir, plus a running index when a
    path is reused). The removal itself still happens exactly as before.
  * fable_suitediff218's own tempfile.mkdtemp call returns <capture>/work so
    the relative paths are the same for the base and the 241 run.
  * MOUTH241_LOG=<mouthlog> (241 only: Mouth241Mixin logs every line).

Usage (after the seal):
  uv ... python -B scripts/claude_mouth241_suites.py --capture DIR \
     [--mouthlog FILE] -- <fable_suitediff218 args>
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import types
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        raise SystemExit("usage: --capture DIR [--mouthlog F] -- <218 args>")
    k = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", required=True)
    ap.add_argument("--mouthlog", default=None)
    a = ap.parse_args(argv[:k])
    rest = argv[k + 1:]
    cap = Path(a.capture).resolve()
    if cap.exists():
        shutil.rmtree(cap)
    (cap / "events").mkdir(parents=True)
    work = cap / "work"
    if a.mouthlog:
        os.environ["MOUTH241_LOG"] = str(Path(a.mouthlog).resolve())
        Path(a.mouthlog).unlink(missing_ok=True)
    seen: dict[str, int] = {}
    real_rmtree = shutil.rmtree

    def capturing_rmtree(path, *args, **kw):
        p = Path(path)
        try:
            rp = p.resolve()
            if rp == work or work in rp.parents:
                for ev in sorted(rp.rglob("events.jsonl")):
                    rel = str(ev.relative_to(work)).replace("/", "__")
                    n = seen.get(rel, 0)
                    seen[rel] = n + 1
                    shutil.copyfile(ev, cap / "events" / f"{rel}.{n}")
        except Exception as e:  # noqa: BLE001 -- capture must not change runs
            print(f"[capture warning] {e}", flush=True)
        return real_rmtree(path, *args, **kw)

    shutil.rmtree = capturing_rmtree
    import fable_suitediff218 as S218  # read-only import

    def fixed_mkdtemp(*_a, **_k):
        work.mkdir(parents=True, exist_ok=True)
        return str(work)

    # only fable_suitediff218's own mkdtemp call sees the fixed dir
    S218.tempfile = types.SimpleNamespace(mkdtemp=fixed_mkdtemp)
    rc = S218.main(rest)
    if work.exists():
        capturing_rmtree(work, ignore_errors=True)
    print(f"captured {sum(seen.values())} event logs in {cap / 'events'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
