"""Exp 243 (diagnosis only): trace which ears stage claims a question and
where it falls through to the decline.

Usage: python -B scripts/claude_diag243_trace.py <workdir> <probe.json>
Uses scripts/claude_loop228_agent.py (138i + the 228 src guard) -- nothing
is edited; hear/_act functions are wrapped in-process only for logging.
"""
from __future__ import annotations

import functools
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "scripts")
import claude_loop228_agent as A228  # noqa: E402 (installs the 228 guard)
import fable_marks123_all as M  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402

A228.install_srcguard228()
LOG: list[str] = []
DEPTH = [0]


def _short(x, n=220):
    s = repr(x)
    return s if len(s) <= n else s[:n] + "..."


def wrap(cls, meth):
    fn = cls.__dict__.get(meth)
    if fn is None or getattr(fn, "_d243", False):
        return
    @functools.wraps(fn)
    def w(self, *a, **k):
        DEPTH[0] += 1
        try:
            out = fn(self, *a, **k)
        finally:
            DEPTH[0] -= 1
        LOG.append(f"{'  ' * DEPTH[0]}{cls.__module__}.{cls.__name__}.{meth}"
                   f"({_short(a[0] if a else '', 80)}) -> {_short(out)}")
        return out
    w._d243 = True
    setattr(cls, meth, w)


def instrument(d):
    loop = d.loop
    seen = set()
    for obj in (loop.ears, getattr(loop.ears, "inner", None),
                getattr(loop.ears, "ears", None)):
        if obj is None:
            continue
        for cls in type(obj).__mro__:
            if cls in seen:
                continue
            seen.add(cls)
            wrap(cls, "hear")
    if "--deep" in sys.argv:  # every hear-like method in loaded fable_* modules
        for mname, mod in list(sys.modules.items()):
            if not mname.startswith(("fable_", "claude_")) or mod is None:
                continue
            for obj in list(vars(mod).values()):
                if isinstance(obj, type) and obj.__module__ == mname:
                    for m in ("hear", "hear_question", "hear_turn", "parse",
                              "parse_question"):
                        wrap(obj, m)
    for cls in type(loop).__mro__:
        for m in ("_act", "_answer_ask", "turn"):
            wrap(cls, m)


def main():
    S = Path(sys.argv[1]); dialogs = json.load(open(sys.argv[2]))
    base = M.load_base_cfg(
        "artifacts/fable-agent138i-20260922/loop138i-config.json")
    for i, msgs in enumerate(dialogs):
        root = S / f"d{i:02d}"; shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = M.make_daemon(A228.Loop228Daemon, base, root)
        instrument(d)
        for j, t in enumerate(msgs):
            LOG.clear()
            f = root / "inbox" / f"m{j:02d}.txt"; f.write_text(t)
            d.process_file(f)
            rep = (root / "outbox" / f"m{j:02d}.txt").read_text().strip()
            print(f"{i:02d} {t!r} -> {rep!r}")
            if t.rstrip().endswith("?") or "--trace-all" in sys.argv:
                if "--full" in sys.argv:
                    for line in LOG:
                        print("      | " + line)
                else:  # compact: only hear stages where the output changed
                    prev = None
                    for line in LOG:
                        if ".hear" not in line and ".parse" not in line:
                            continue
                        who, out = line.strip().split("(", 1)
                        out = out.split(") -> ", 1)[1]
                        if out != prev:
                            print(f"      | {'.'.join(who.split('.')[-2:]):40s} -> {out[:150]}")
                            prev = out
        print(f"{i:02d}   STORED {[tuple(x) for x in L90.notebook_triples(d.loop.nb)]}")


if __name__ == "__main__":
    main()
